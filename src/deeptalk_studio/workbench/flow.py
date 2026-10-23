"""Creator Workbench flow: topic → references → research → thesis → script.

Every stage reuses the canonical engines (``run_report_approval``,
``run_fact_check_review``, thesis card workflow, ``run_script_workflow``) —
no engine logic is re-implemented here.  LLM answers are schema-validated
before entering any engine; engine gate failures surface verbatim to the UI
(fail closed, no silent acceptance).

Fact-check hardening: every ``verified``/``partially_verified`` check must
carry a literal quote that the server finds inside the re-fetched source
text; otherwise it is downgraded to ``unverified`` with an honest note.
"""

import hashlib
import io
import json
import os
import re
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from ..content_director_profile import load_content_director_profile
from ..content_director_workflow import (
    confirm_content_thesis,
    prepare_codex_content_thesis,
    run_codex_content_thesis_review,
)
from ..models import ContentThesisCard, ResearchReport
from ..fact_check import normalize_fact_check_sources, validate_fact_check_artifact
from ..schema import (
    API_RESEARCH_DRAFT_JSON_SCHEMA,
    FACT_CHECK_JSON_SCHEMA,
)
from ..script_storage import load_script
from ..script_workflow import run_script_workflow
from .script_profile import load_workbench_script_profile
from ..sources import normalize_report_sources
from ..quality import calculate_quality_summary
from ..storage import save_report
from ..validation import ReportValidationError, validate_json_schema
from ..workflow import run_fact_check_review, run_report_approval
from . import acquisition
from .llm import WorkbenchLLM, WorkbenchLLMError, build_llm
from .deepseek_tools import DeepSeekSearchFetchClient, DeepSeekToolError
from .prompts import serialize_reference_insights
from .session import SessionStore
from .settings import (
    is_configured,
    load_settings,
    masked_view,
    resolve_downloads_dir,
    save_settings,
    apply_settings_update,
    effective_chat_endpoint,
)


class WorkbenchFlowError(ValueError):
    """Typed user-facing error (UI shows the message verbatim)."""

    def __init__(self, message: str, *, payload: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(message)
        self.payload = dict(payload or {})


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


DEEPSEEK_MAX_REQUESTS = 20
DEEPSEEK_DEFAULT_REQUESTS = 5
DEEPSEEK_MAX_QUERY_CHARS = 500
AUDIO_ORIGINS = {"owner_made", "external_voice_authorized", "unknown"}


# --- page fetcher (user-supplied URLs, public-internet-only; Issue #23 B2)----

# ``default_fetcher`` comes from netfetch: it resolves and validates every
# destination (A/AAAA, public unicast only), pins connections to the
# validated addresses (no DNS-rebinding window), only follows http(s)
# redirects (capped), and keeps the same result contract (ok/url/error or
# ok/title/text/sha256/...) so the paste-text fallback keeps working.
from .netfetch import fetch_public_source as default_fetcher  # noqa: E402


# ---------------------------------------------------------------------------


# --- topic-consistency guard (Issue #23 B1) -----------------------------------
#
# The browser E2E proved a real failure mode: a model can return a perfectly
# schema-valid but *off-topic* research/thesis/script payload (Moscow topic
# in, library script out) and the flow used to overwrite ``payload["topic"]``
# with the session topic, masking the mismatch.  ``ensure_topic_consistency``
# fails closed on that: it compares the session topic's signal tokens and
# distinctive anchors against the model/stage content and rejects obvious
# foreign-topic output *before* it can be saved, approved or delivered as
# Gate-passed.  Generic bridge words (for example 大学/留学生/事件) are not
# anchors, so an adjacent topic cannot pass merely by sharing those words.
# Semantic paraphrases stay allowed when they retain a distinctive entity
# (e.g. 莫斯科 or 旭日旗).

MIN_TOPIC_COVERAGE = 0.2

# These terms describe a topic's framing rather than its subject.  They are
# removed only while deriving anchors; they still contribute to the legacy
# coverage score so short or otherwise generic topics retain a useful fallback
# check.  Longest terms are consumed first to avoid ``留学生`` becoming
# ``留`` + ``学生``.
_TOPIC_GENERIC_TERMS = (
    "留学生",
    "本市",
    "当地",
    "相关",
    "大学",
    "学校",
    "学生",
    "留学",
    "事件",
    "问题",
    "现象",
    "话题",
    "情况",
    "报道",
    "新闻",
    "调查",
    "分析",
    "影响",
    "原因",
    "政策",
    "讨论",
    "争议",
    "试点",
    "措施",
    "方案",
    "通知",
    "安排",
    "机制",
)


def _topic_signal_tokens(topic: str) -> List[str]:
    tokens: List[str] = []
    for run in re.findall(r"[\u4e00-\u9fff]+", topic):
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i : i + 2] for i in range(len(run) - 1))
    tokens.extend(
        word.lower()
        for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-_.]{2,}", topic)
    )
    return tokens


def _topic_anchor_tokens(topic: str) -> List[str]:
    """Return distinctive subject phrases from a topic.

    The old bigram score is intentionally retained as a broad recall signal,
    but adjacent Chinese topics often share several generic bigrams.  Removing
    framing terms and keeping the remaining contiguous runs gives us a small,
    explainable precision check without pretending to perform semantic model
    inference in the server-side gate.
    """

    anchors: List[str] = []
    for run in re.findall(r"[\u4e00-\u9fff]+", str(topic or "")):
        residual = run
        for term in sorted(_TOPIC_GENERIC_TERMS, key=len, reverse=True):
            residual = residual.replace(term, " ")
        for chunk in re.findall(r"[\u4e00-\u9fff]{2,}", residual):
            # Keep the whole phrase and three-character windows.  A stage may
            # reasonably paraphrase “图书馆夜间开放” as just “夜间开放”,
            # while a three-character window still remains distinctive enough
            # to distinguish it from “大学留学生考试”.
            anchors.append(chunk)
            if len(chunk) > 3:
                anchors.extend(chunk[index : index + 3] for index in range(len(chunk) - 2))
    anchors.extend(
        word.lower()
        for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-_.]{2,}", str(topic or ""))
        if word.lower() not in {"the", "and", "for", "with", "from"}
    )
    # Preserve deterministic order while removing repeated fragments.
    return list(dict.fromkeys(anchor for anchor in anchors if anchor))


def ensure_topic_consistency(
    topic: str, texts: Sequence[Any], *, what: str
) -> float:
    """Fail closed unless ``texts`` cover the topic and a subject anchor."""

    subject = " ".join(str(text or "") for text in texts)
    tokens = _topic_signal_tokens(str(topic or ""))
    if not tokens:
        return 0.0  # degenerate topic: nothing comparable (session topics are 1–200 chars)
    covered = sum(1 for token in tokens if token and token in subject)
    coverage = covered / len(tokens)
    normalized_subject = re.sub(r"\s+", "", subject).lower()
    anchors = _topic_anchor_tokens(str(topic or ""))
    anchor_hits = [anchor for anchor in anchors if anchor.lower() in normalized_subject]
    if coverage < MIN_TOPIC_COVERAGE or (anchors and not anchor_hits):
        raise WorkbenchFlowError(
            f"{what}与选题主题明显不符（关键内容一致度约 {coverage:.0%}），已拒绝写入："
            "模型输出疑似偏离本集选题或缺少主题锚点；请检查模型输出或更换更贴合选题的来源后重试。"
        )
    return coverage


def _report_topic_texts(report: Mapping[str, Any]) -> List[str]:
    data = report.get("data", report) if isinstance(report, Mapping) else {}
    claims = data.get("claims", []) or []
    sources = data.get("sources", []) or []
    return [
        str(data.get("research_question", "")),
        str(data.get("scope_summary", "")),
        str(data.get("executive_summary", "")),
    ] + [
        str(claim.get("claim", ""))
        for claim in claims
        if isinstance(claim, Mapping)
    ] + [
        str(source.get("title", "")) + str(source.get("stance_summary", ""))
        for source in sources
        if isinstance(source, Mapping)
    ]


_THESIS_CONSISTENCY_KEYS = (
    "core_question",
    "one_sentence_answer",
    "core_thesis",
    "counterintuitive_point",
    "differentiated_angle",
    "hook_promise",
    "ending_question_or_judgment",
    "competitive_insight_notes",
)


def _card_topic_texts(data: Mapping[str, Any]) -> List[str]:
    return [
        str(data.get(key, ""))
        for key in _THESIS_CONSISTENCY_KEYS
    ] + [str(note) for note in (data.get("crowded_angles") or [])]


def _prune_dangling(content: Dict[str, Any]) -> Dict[str, Any]:
    """Drop evidence/claims whose referenced ids no longer exist after the
    known-source filter, then repair every cross-reference list so the engine
    schema never sees dangling ids."""

    source_ids = {source["id"] for source in content["sources"]}
    evidence = [link for link in content.get("evidence_links", []) if link["source_id"] in source_ids]
    evidence_ids = {link["id"] for link in evidence}
    referenced_claims = {link["claim_id"] for link in evidence}
    claim_ids = {
        claim["id"] for claim in content.get("claims", []) if claim["id"] in referenced_claims
    }
    content["claims"] = [claim for claim in content["claims"] if claim["id"] in claim_ids]
    content["evidence_links"] = [
        link for link in evidence if link["claim_id"] in claim_ids
    ]
    for item in content.get("timeline", []):
        item["claim_ids"] = [cid for cid in item.get("claim_ids", []) if cid in claim_ids]
        item["evidence_link_ids"] = [
            eid for eid in item.get("evidence_link_ids", []) if eid in evidence_ids
        ]
    for item in content.get("perspectives", []):
        item["claim_ids"] = [cid for cid in item.get("claim_ids", []) if cid in claim_ids]
        item["evidence_link_ids"] = [
            eid for eid in item.get("evidence_link_ids", []) if eid in evidence_ids
        ]
    for item in content.get("conflicts", []):
        item["claim_ids"] = [cid for cid in item.get("claim_ids", []) if cid in claim_ids]
        item["evidence_link_ids"] = [
            eid for eid in item.get("evidence_link_ids", []) if eid in evidence_ids
        ]
    for item in content.get("angles", []):
        item["required_claim_ids"] = [
            cid for cid in item.get("required_claim_ids", []) if cid in claim_ids
        ]
    handoff = content.get("handoff_to_script_agent") or {}
    handoff["must_keep_claim_ids"] = [
        cid for cid in handoff.get("must_keep_claim_ids", []) if cid in claim_ids
    ]
    handoff["avoid_claims"] = list(handoff.get("avoid_claims", []))
    return content


class WorkbenchFlow:
    def __init__(
        self,
        repo_root: Path,
        *,
        discovery_runner: Optional[Callable[[str, List[str]], Dict[str, Any]]] = None,
        provider_factory: Optional[Callable[[Mapping[str, Any]], WorkbenchLLM]] = None,
        deepseek_client_factory: Optional[Callable[[Mapping[str, Any]], Any]] = None,
        fetcher: Optional[Callable[[str], Dict[str, Any]]] = None,
        acquire_runner=None,
        audio_runner=None,
        audio_delivery_runner=None,
        audio_upload_limit_bytes: int = 512 * 1024 * 1024,
        whisper_runner=None,
        whisper_bootstrap=None,
        connection_kind: Optional[str] = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.store = SessionStore(self.repo_root / "workbench")
        self.provider_factory = provider_factory or (lambda settings: build_llm(settings))
        self.deepseek_client_factory = deepseek_client_factory or self._default_deepseek_client
        self.connection_kind = connection_kind or ("fixture" if provider_factory is not None else "real")
        self.fetcher = fetcher or default_fetcher
        self.acquire_runner = acquire_runner
        self.audio_runner = audio_runner
        self.audio_delivery_runner = audio_delivery_runner
        self.audio_upload_limit_bytes = int(audio_upload_limit_bytes)
        self.whisper_runner = whisper_runner
        self.whisper_bootstrap = whisper_bootstrap
        self.discovery_runner = discovery_runner

    @staticmethod
    def _default_deepseek_client(settings: Mapping[str, Any]) -> DeepSeekSearchFetchClient:
        """Build the paid Search/Fetch client only after the flow gates it.

        Settings stores a Chat-compatible base (normally
        ``https://api.deepseek.com``).  The tools API owns its ``/v1/tools``
        suffix, so remove a user-entered ``/v1`` or Chat endpoint suffix once
        here rather than ever composing ``/v1/v1``.
        """

        base = str(settings.get("chat_base_url", "") or "").strip().rstrip("/")
        for suffix in ("/chat/completions", "/v1"):
            if base.endswith(suffix):
                base = base[: -len(suffix)].rstrip("/")
        return DeepSeekSearchFetchClient(
            str(settings.get("api_key", "")),
            base_url=base or "https://api.deepseek.com",
            timeout=int(settings.get("timeout_seconds", 600) or 600),
        )

    # -- settings ------------------------------------------------------------

    def get_settings(self) -> Dict[str, Any]:
        data = load_settings(self.repo_root)
        return masked_view(data)

    def save_settings(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        from .settings import WorkbenchSettingsError

        current = load_settings(self.repo_root)
        try:
            updated = apply_settings_update(current, payload)
        except WorkbenchSettingsError as exc:
            raise WorkbenchFlowError(str(exc)) from None
        save_settings(self.repo_root, updated)
        return masked_view(updated)

    def test_settings(self) -> Dict[str, Any]:
        settings = load_settings(self.repo_root)
        endpoint = (
            effective_chat_endpoint(settings)
            if settings.get("provider_mode") in {"chat", "deepseek"}
            else settings.get("base_url", "")
        )
        observation = {
            "connection_provider": settings.get("provider_mode", ""),
            "connection_model": settings.get("model", ""),
            "connection_endpoint": endpoint,
            "connection_kind": self.connection_kind,
            "connection_tested_at": _now(),
        }
        if not is_configured(settings):
            self._record_connection_observation(
                {**observation, "connection_status": "waiting_for_api_key", "connection_error": "未配置模型、API Key 或服务地址"}
            )
            raise WorkbenchFlowError(
                "设置尚未完成（WAITING_FOR_OWNER_API_KEY）：请在设置中填写 API Key、模型和服务地址",
                payload={
                    "status": "waiting_for_api_key",
                    "connection_kind": self.connection_kind,
                },
            )
        try:
            LLM = self.provider_factory(settings)
            LLM.ping()
        except (WorkbenchLLMError, WorkbenchFlowError) as exc:
            self._record_connection_observation(
                {
                    **observation,
                    "connection_status": "failed",
                    "connection_error": str(exc),
                }
            )
            raise WorkbenchFlowError(
                str(exc),
                payload={
                    "status": "failed",
                    "connection_kind": self.connection_kind,
                    "error_category": getattr(exc, "category", "provider_error"),
                    "http_status": getattr(exc, "http_status", None),
                },
            ) from None
        self._record_connection_observation(
            {**observation, "connection_status": "passed", "connection_error": ""}
        )
        return {
            "ok": True,
            "message": "模型服务连接正常",
            "status": "passed",
            "connection_kind": self.connection_kind,
            "provider": settings.get("provider_mode", ""),
            "model": settings.get("model", ""),
            "endpoint": endpoint,
        }

    def _record_connection_observation(self, observation: Mapping[str, Any]) -> None:
        """Persist non-secret connection status without changing credentials."""

        current = load_settings(self.repo_root)
        updated = dict(current)
        for key in (
            "connection_status",
            "connection_kind",
            "connection_tested_at",
            "connection_error",
            "connection_provider",
            "connection_model",
            "connection_endpoint",
        ):
            if key in observation:
                updated[key] = observation[key]
        save_settings(self.repo_root, updated)

    def _llm(self) -> WorkbenchLLM:
        settings = load_settings(self.repo_root)
        if not is_configured(settings):
            raise WorkbenchFlowError("请先在「设置」中配置模型服务，再执行这一步")
        return self.provider_factory(settings)

    # -- session -------------------------------------------------------------

    def start_session(self, topic: str, urls: Sequence[str], discovery_json_path: Optional[Path] = None) -> Dict[str, Any]:
        if self.discovery_runner is None:
            from ..reference_discovery import build_reference_candidate_set

            artifact = build_reference_candidate_set(topic, list(urls))
        else:
            artifact = self.discovery_runner(topic, list(urls))
        candidates = artifact.get("candidates", [])
        session = self.store.create(topic, candidates, discovery_json_path)
        return self.view(session["session_id"])

    def view(self, session_id: str) -> Dict[str, Any]:
        session = self.store.load(session_id)
        search_budget = self._search_budget_view(session)
        audio = self._audio_view(session)
        audio_delivery = self._audio_delivery_view(session)
        references = []
        for reference in session["discovery"]["candidates"]:
            bvid = reference.get("bvid", "")
            state = session["references"].get(bvid, {})
            study = self._load_study(session, bvid)
            references.append(
                {
                    **reference,
                    "study_status": state.get("status", "not_analyzed"),
                    "study_error": state.get("failure_reason", "") or state.get("analysis_error", ""),
                    "failure_stage": state.get("failure_stage", ""),
                    "attempt_count": state.get("attempt_count", 0),
                    "study": self._study_summary(study),
                }
            )
        return {
            "session_id": session["session_id"],
            "topic": session["topic"],
            "created_at": session["created_at"],
            "status": session["status"],
            "references": references,
            "references_readiness": self._reference_readiness(session),
            "sources": session["sources"] and [
                {key: source.get(key, "") for key in (
                    "sid", "url", "title", "kind", "fetched_at",
                    "request_id", "retrieved_at", "published_at",
                    "provenance_method", "provenance_status", "sha256",
                )}
                for source in session["sources"]
            ],
            "search_budget": search_budget,
            "search_results": list(search_budget.get("results", [])),
            "audio": audio,
            "audio_delivery": audio_delivery,
            "research": session["research"],
            "thesis": session["thesis"],
            "script": session["script"],
        }

    @staticmethod
    def _audio_defaults() -> Dict[str, Any]:
        return {
            "status": "not_imported",
            "path": "",
            "filename": "",
            "origin": "",
            "byte_size": 0,
            "sha256": "",
            "imported_at": "",
        }

    def _audio_view(self, session: Mapping[str, Any]) -> Dict[str, Any]:
        value = self._audio_defaults()
        raw = session.get("audio") or {}
        for key in value:
            if key in raw:
                value[key] = raw[key]
        return value

    @staticmethod
    def _audio_delivery_defaults() -> Dict[str, Any]:
        return {
            "status": "not_started",
            "error": "",
            "runner_kind": "real",
            "started_at": "",
            "completed_at": "",
            "timeline": [],
            "gaps": [],
            "qa_status": "",
            "paths": {},
            "preview_path": "",
        }

    def _audio_delivery_view(self, session: Mapping[str, Any]) -> Dict[str, Any]:
        value = self._audio_delivery_defaults()
        raw = session.get("audio_delivery") or {}
        for key in value:
            if key in raw:
                value[key] = raw[key]
        value["timeline"] = [
            dict(item) for item in (value.get("timeline") or [])
            if isinstance(item, Mapping)
        ][-200:]
        value["gaps"] = [
            dict(item) for item in (value.get("gaps") or [])
            if isinstance(item, Mapping)
        ][-200:]
        value["paths"] = {
            str(key): str(path) for key, path in (value.get("paths") or {}).items()
            if path
        }
        return value

    @staticmethod
    def _search_budget_defaults() -> Dict[str, Any]:
        return {
            "opt_in": False,
            "max_requests": 0,
            "used": 0,
            "results": [],
            "records": [],
            "last_error": "",
        }

    def _search_budget_view(self, session: Mapping[str, Any]) -> Dict[str, Any]:
        """Return a redacted, backward-compatible budget snapshot."""

        raw = session.get("search_budget") or {}
        budget = self._search_budget_defaults()
        for key in budget:
            if key in raw:
                budget[key] = raw[key]
        # Keep the browser contract bounded even if an old/corrupt session was
        # edited by hand.  Search content is never stored in this view.
        budget["results"] = [
            dict(item) for item in (budget.get("results") or [])
            if isinstance(item, Mapping)
        ][-50:]
        budget["records"] = [
            {key: value for key, value in dict(item).items() if key != "token"}
            for item in (budget.get("records") or [])
            if isinstance(item, Mapping)
        ][-100:]
        return budget

    def _load_study(self, session: Mapping[str, Any], bvid: str) -> Optional[Dict[str, Any]]:
        state = session["references"].get(bvid, {})
        path = state.get("study_path", "")
        if not path or not Path(path).is_file():
            return None
        try:
            return self.store.load_json(Path(path))
        except (OSError, ValueError):
            return None

    @staticmethod
    def _study_summary(study: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not study:
            return None
        return {
            key: study.get(key)
            for key in (
                "title",
                "bvid",
                "url",
                "view_count",
                "duration_seconds",
                "cps",
                "segment_count",
                "question_count",
                "top_terms",
                "hook_text",
                "narrative_summary",
                "creator_viewpoint",
                "hook_style",
                "pacing",
                "struct_patterns",
                "takeaways",
                "media_path",
                "transcript_status",
                "transcript_provenance",
                "analysis_status",
                "analysis_error",
                "analysis_provenance",
                "transcript_segments",
            )
            if key in study
        }

    # -- reference acquisition & analysis ------------------------------------

    def acquire_references(
        self, session_id: str, bvids: Sequence[str], authorization_text: str
    ) -> Dict[str, Any]:
        session = self.store.load(session_id)
        candidates = {
            item.get("bvid"): item for item in session["discovery"]["candidates"]
        }
        downloads_dir = resolve_downloads_dir(load_settings(self.repo_root))
        if downloads_dir is None:
            raise WorkbenchFlowError(
                "请先在「设置」中配置参考视频下载文件夹（必须是已存在的目录）"
            )
        results = []
        for bvid in list(bvids)[:5]:
            reference = candidates.get(bvid)
            if not reference:
                results.append({"bvid": bvid, "ok": False, "error": "候选中不存在该参考"})
                continue
            # Do not turn a malformed authorization attempt into an eligible
            # reference.  Once this validation succeeds, however, every
            # acquisition outcome is durable (including failure).
            try:
                attestation = acquisition.authorize(authorization_text)
            except acquisition.WorkbenchAcquisitionError:
                attestation = ""
            # Idempotent skip: references already downloaded locally (with the
            # media file still on disk) are not downloaded again — the caller's
            # fresh authorization never silently re-archives a duplicate.
            prior = session.get("references", {}).get(bvid) or {}
            prior_media = str(prior.get("media_path", ""))
            if prior.get("status") == "downloaded" and prior_media and Path(prior_media).is_file():
                results.append({
                    "bvid": bvid,
                    "ok": True,
                    "media_path": prior_media,
                    "skipped": "already_downloaded",
                })
                continue
            try:
                record = acquisition.acquire_reference(
                    reference,
                    downloads_dir,
                    authorization_text,
                    runner=self.acquire_runner or acquisition.subprocess.run,
                )
            except acquisition.WorkbenchAcquisitionError as exc:
                reason = str(exc)
                if attestation:
                    prior_state = session.get("references", {}).get(bvid) or {}
                    attempt_count = int(prior_state.get("attempt_count", 0) or 0) + 1
                    attempted_at = _now()
                    ref_dir = self.store.references_dir(session_id) / bvid
                    ref_dir.mkdir(parents=True, exist_ok=True)
                    failure_record = {
                        "bvid": bvid,
                        "url": reference.get("url", ""),
                        "title": reference.get("title", bvid),
                        "authorization_text": attestation,
                        "authorized_at": prior_state.get("authorized_at", attempted_at),
                        "attempted_at": attempted_at,
                        "attempt_count": attempt_count,
                        "status": "failed",
                        "failure_stage": "acquisition",
                        "failure_reason": reason,
                        "tool": "yt-dlp",
                    }
                    (ref_dir / "acquisition.json").write_text(
                        json.dumps(failure_record, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )

                    def _mark_failed(
                        session_state,
                        ref_bvid=bvid,
                        ref=reference,
                        auth=attestation,
                        attempted=attempted_at,
                        attempts=attempt_count,
                        failure=reason,
                    ):
                        state = session_state["references"].setdefault(ref_bvid, {})
                        state.update({
                            "status": "failed",
                            "failure_stage": "acquisition",
                            "failure_reason": failure,
                            "authorization_text": auth,
                            "authorized_at": state.get("authorized_at", attempted),
                            "last_attempt_at": attempted,
                            "attempt_count": attempts,
                            "title": ref.get("title", ref_bvid),
                            "url": ref.get("url", ""),
                            "view_count": ref.get("view_count"),
                            "view_count_status": ref.get("view_count_status", ""),
                            "duration_sec": ref.get("duration_sec"),
                        })
                        state.pop("media_path", None)
                        state.pop("study_path", None)

                    session = self.store.update(session_id, _mark_failed)
                results.append({
                    "bvid": bvid,
                    "ok": False,
                    "error": reason,
                    "status": "failed" if attestation else "not_authorized",
                })
                continue
            ref_dir = self.store.references_dir(session_id) / bvid
            ref_dir.mkdir(parents=True, exist_ok=True)
            prior_state = session.get("references", {}).get(bvid) or {}
            attempt_count = int(prior_state.get("attempt_count", 0) or 0) + 1
            attempted_at = _now()
            (ref_dir / "acquisition.json").write_text(
                json.dumps(
                    {**record, "attempt_count": attempt_count, "attempted_at": attempted_at},
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )

            def _mark(
                session_state,
                ref_bvid=bvid,
                media=record["media_path"],
                ref=reference,
                status="downloaded",
            ):
                # SessionStore.update calls ``mutate(session)`` — the session
                # dict is passed as the first positional argument.
                state = session_state["references"].setdefault(ref_bvid, {})
                state["status"] = status
                state["media_path"] = media
                state["authorization_text"] = record.get("authorization_text", attestation)
                state["authorized_at"] = record.get("authorized_at", attempted_at)
                state["last_attempt_at"] = attempted_at
                state["attempt_count"] = attempt_count
                state["title"] = ref.get("title", ref_bvid)
                state["url"] = ref.get("url", "")
                state["view_count"] = ref.get("view_count")
                state["view_count_status"] = ref.get("view_count_status", "")
                state["duration_sec"] = ref.get("duration_sec")
                state.pop("failure_stage", None)
                state.pop("failure_reason", None)

            session = self.store.update(session_id, _mark)
            results.append({"bvid": bvid, "ok": True, "media_path": record["media_path"]})
        return {"results": results}

    def analyze_reference(self, session_id: str, bvid: str) -> Dict[str, Any]:
        session = self.store.load(session_id)
        state = session["references"].get(bvid, {})
        media_path = state.get("media_path", "")
        if not media_path or not Path(media_path).is_file():
            raise WorkbenchFlowError("请先完成该参考的授权下载，再执行分析")
        ref_dir = self.store.references_dir(session_id) / bvid
        ref_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = ref_dir / "transcript.json"

        def _mark_transcribing(session_state):
            refs_state = session_state["references"].setdefault(bvid, {})
            refs_state["status"] = "transcribing"
            refs_state["analysis_status"] = "transcribing"
            refs_state["analysis_error"] = ""

        self.store.update(session_id, _mark_transcribing)
        if transcript_path.is_file():
            try:
                transcript = self.store.load_json(transcript_path)
            except (OSError, ValueError):
                transcript = None
        else:
            transcript = None
        if not transcript:
            try:
                wav = acquisition.extract_audio(
                    Path(media_path), runner=self.audio_runner or acquisition.subprocess.run
                )
                try:
                    transcript = acquisition.transcribe_audio(
                        wav,
                        runner=self.whisper_runner or acquisition.subprocess.run,
                        bootstrap=self.whisper_bootstrap,
                    )
                finally:
                    wav.unlink(missing_ok=True)
            except acquisition.WorkbenchAcquisitionError as exc:
                self._mark_analysis_failure(session_id, bvid, str(exc), stage="transcription")
                raise WorkbenchFlowError(str(exc)) from None
            media_digest = self._file_sha256(Path(media_path))
            transcript = dict(transcript)
            transcript["transcript_status"] = "complete"
            transcript["transcript_provenance"] = {
                "source_media_path": str(media_path),
                "source_media_sha256": media_digest,
                "model": transcript.get("model", "large-v3"),
                "runtime_version": transcript.get("runtime_version", ""),
                "transcribed_at": transcript.get("transcribed_at", _now()),
                "provider": "local_whisper_cpp",
            }
            transcript_path.write_text(
                json.dumps(transcript, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        else:
            transcript = dict(transcript)
            transcript.setdefault("transcript_status", "complete")
            transcript.setdefault("transcript_provenance", {
                "source_media_path": str(media_path),
                "source_media_sha256": self._file_sha256(Path(media_path)),
                "model": transcript.get("model", "large-v3"),
                "runtime_version": transcript.get("runtime_version", ""),
                "transcribed_at": transcript.get("transcribed_at", ""),
                "provider": "local_whisper_cpp",
            })
            transcript_path.write_text(
                json.dumps(transcript, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        metadata = {
            "title": state.get("title", ""),
            "bvid": bvid,
            "url": state.get("url", ""),
            "view_count": state.get("view_count"),
            "view_count_status": state.get("view_count_status", ""),
            "duration_sec": state.get("duration_sec"),
        }
        metrics = acquisition.analyze_transcript(transcript, metadata)
        study = dict(metrics)
        study["transcript_status"] = transcript.get("transcript_status", "complete")
        study["transcript_provenance"] = transcript.get("transcript_provenance", {})
        study["transcript_segments"] = list(transcript.get("segments") or [])[:200]
        study["analysis_status"] = "unverified"
        study["analysis_error"] = ""
        study["analysis_provenance"] = {}
        try:
            llm = self._llm()
            result = llm.summarize_reference(
                transcript["text"], metrics, metadata
            )
            study.update(result.data)
            study["analysis_status"] = "analyzed"
            settings = load_settings(self.repo_root)
            study["analysis_provenance"] = {
                "provider": settings.get("provider_mode", ""),
                "model": settings.get("model", ""),
                "endpoint": settings.get("base_url", "")
                if settings.get("provider_mode") == "responses"
                else effective_chat_endpoint(settings),
                "analyzed_at": _now(),
            }
        except (WorkbenchLLMError, WorkbenchFlowError) as exc:
            study["narrative_summary"] = ""
            study["analysis_status"] = "unverified"
            study["analysis_error"] = str(exc)
            study["analysis_note"] = f"LLM 手法摘要不可用（{exc}）；仅保留本地转写与确定性指标，不能计入已分析。"
        study_path = ref_dir / "study.json"
        study_path.write_text(
            json.dumps(study, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        final_status = "analyzed" if study["analysis_status"] == "analyzed" else "unverified"

        def _mark(session_state, ref_bvid=bvid, status=final_status, path=str(study_path)):
            # SessionStore.update calls ``mutate(session)`` — the session dict
            # is passed as the first positional argument.
            refs_state = session_state["references"].setdefault(ref_bvid, {})
            refs_state["status"] = status
            refs_state["study_path"] = path
            refs_state["media_path"] = media_path
            refs_state["analysis_status"] = study["analysis_status"]
            refs_state["analysis_error"] = study.get("analysis_error", "")
            refs_state.setdefault("title", state.get("title", ref_bvid))

        self.store.update(session_id, _mark)
        return {"bvid": bvid, "study": self._study_summary(study)}

    def reanalyze_reference(self, session_id: str, bvid: str) -> Dict[str, Any]:
        """Retry only the LLM viewpoint stage using the saved transcript."""

        session = self.store.load(session_id)
        state = session["references"].get(bvid, {})
        study = self._load_study(session, bvid)
        transcript_path = self.store.references_dir(session_id) / bvid / "transcript.json"
        if not study or not transcript_path.is_file():
            raise WorkbenchFlowError("尚无可重试的本地转写，请先完成参考视频转写")
        transcript = self.store.load_json(transcript_path)
        metadata = {
            "title": state.get("title", study.get("title", "")),
            "bvid": bvid,
            "url": state.get("url", study.get("url", "")),
            "view_count": state.get("view_count", study.get("view_count")),
            "view_count_status": state.get("view_count_status", study.get("view_count_status", "")),
            "duration_sec": state.get("duration_sec", study.get("duration_seconds", 0)),
        }
        try:
            result = self._llm().summarize_reference(
                transcript.get("text", ""), study, metadata
            )
        except (WorkbenchLLMError, WorkbenchFlowError) as exc:
            study["analysis_status"] = "unverified"
            study["analysis_error"] = str(exc)
            study["analysis_note"] = f"重试仍不可用（{exc}）；请配置模型后再次重试。"
            self._write_study(study, self.store.references_dir(session_id) / bvid / "study.json")
            self._mark_analysis_state(session_id, bvid, "unverified", str(exc))
            return {"bvid": bvid, "study": self._study_summary(study)}
        study.update(result.data)
        study["analysis_status"] = "analyzed"
        study["analysis_error"] = ""
        settings = load_settings(self.repo_root)
        study["analysis_provenance"] = {
            "provider": settings.get("provider_mode", ""),
            "model": settings.get("model", ""),
            "endpoint": settings.get("base_url", "")
            if settings.get("provider_mode") == "responses"
            else effective_chat_endpoint(settings),
            "analyzed_at": _now(),
        }
        self._write_study(study, self.store.references_dir(session_id) / bvid / "study.json")
        self._mark_analysis_state(session_id, bvid, "analyzed", "")
        return {"bvid": bvid, "study": self._study_summary(study)}

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _write_study(study: Mapping[str, Any], path: Path) -> None:
        path.write_text(json.dumps(dict(study), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _mark_analysis_state(self, session_id: str, bvid: str, status: str, error: str) -> None:
        def _mutate(session_state):
            state = session_state["references"].setdefault(bvid, {})
            state["status"] = status
            state["analysis_status"] = status
            state["analysis_error"] = error
        self.store.update(session_id, _mutate)

    def _mark_analysis_failure(self, session_id: str, bvid: str, error: str, *, stage: str) -> None:
        def _mutate(session_state):
            state = session_state["references"].setdefault(bvid, {})
            state["status"] = "analysis_failed"
            state["analysis_status"] = "failed"
            state["analysis_error"] = error
            state["failure_stage"] = stage
            state["failure_reason"] = error
        self.store.update(session_id, _mutate)

    def _narrative_insights(self, session: Mapping[str, Any]) -> List[Dict[str, Any]]:
        studies = []
        for bvid, state in session.get("references", {}).items():
            study = self._load_study(session, bvid)
            if study and study.get("narrative_summary"):
                studies.append(study)
        return serialize_reference_insights(studies)

    # -- owner audio import and canonical delivery --------------------------

    @staticmethod
    def _audio_filename(filename: Any) -> str:
        from ..narration_media import AUDIO_EXTENSIONS, VIDEO_EXTENSIONS

        if not isinstance(filename, str):
            raise WorkbenchFlowError("音频文件名必须是文本")
        cleaned = filename.strip()
        path = Path(cleaned)
        if (
            not cleaned
            or len(cleaned) > 255
            or cleaned in {".", ".."}
            or path.name != cleaned
            or "/" in cleaned
            or "\\" in cleaned
            or cleaned.startswith(".")
            or any(ord(char) < 32 or ord(char) == 127 for char in cleaned)
        ):
            raise WorkbenchFlowError("音频文件名必须是当前会话内的普通文件名")
        if path.suffix.casefold() not in (AUDIO_EXTENSIONS | VIDEO_EXTENSIONS):
            raise WorkbenchFlowError("仅支持 WAV、MP3、M4A、AAC、FLAC、MP4 或 MOV 文件")
        return cleaned

    def import_audio(
        self,
        session_id: str,
        filename: str,
        data_stream: Any,
        origin: str,
    ) -> Dict[str, Any]:
        """Atomically import one owner-local narration file.

        The destination is the session root because the canonical edit-bridge
        resolver deliberately accepts exactly one direct audio/video input.
        A temporary file plus exclusive hard-link publish prevents a retry or
        a symlink from overwriting an existing user file.
        """

        filename = self._audio_filename(filename)
        origin = str(origin or "").strip()
        if origin not in AUDIO_ORIGINS:
            raise WorkbenchFlowError("音频来源必须选择 owner_made、external_voice_authorized 或 unknown")
        session_dir = self.store.session_dir(session_id)
        if not session_dir.is_dir() or session_dir.is_symlink():
            raise WorkbenchFlowError("会话目录不可用")
        target = session_dir / filename
        if target.exists() or target.is_symlink():
            raise WorkbenchFlowError("同名音频已存在，不覆盖已有文件；请改名后重新导入")
        if isinstance(data_stream, (bytes, bytearray, memoryview)):
            reader = io.BytesIO(bytes(data_stream))
        elif hasattr(data_stream, "read"):
            reader = data_stream
        else:
            raise WorkbenchFlowError("音频上传内容不可读取")
        limit = max(1, int(self.audio_upload_limit_bytes))
        temp_path = None
        digest = hashlib.sha256()
        total = 0
        try:
            fd, temp_path = tempfile.mkstemp(dir=str(session_dir), prefix=".audio-import-", suffix=".tmp")
            with os.fdopen(fd, "wb") as handle:
                while True:
                    chunk = reader.read(min(1024 * 1024, limit + 1 - total))
                    if chunk in (b"", ""):
                        break
                    if not isinstance(chunk, (bytes, bytearray, memoryview)):
                        raise WorkbenchFlowError("音频上传内容不是二进制")
                    chunk = bytes(chunk)
                    total += len(chunk)
                    if total > limit:
                        raise WorkbenchFlowError("音频文件超过本地上传上限，请先压缩或分段处理")
                    handle.write(chunk)
                    digest.update(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            if total == 0:
                raise WorkbenchFlowError("音频文件不能为空")
            # Same-directory hard-link publication is atomic and refuses to
            # replace a target that appeared during the upload.
            try:
                os.link(temp_path, target)
            except FileExistsError:
                raise WorkbenchFlowError("同名音频已存在，不覆盖已有文件；请改名后重新导入") from None
            os.unlink(temp_path)
            temp_path = None
            imported_at = _now()
            record = {
                "status": "imported",
                "path": str(target),
                "filename": filename,
                "origin": origin,
                "byte_size": total,
                "sha256": digest.hexdigest(),
                "imported_at": imported_at,
            }

            def _mutate(session_state):
                session_state["audio"] = dict(record)
                session_state["audio_delivery"] = self._audio_delivery_defaults()

            try:
                self.store.update(session_id, _mutate)
            except BaseException:
                target.unlink(missing_ok=True)
                raise
            return record
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    @staticmethod
    def _result_value(result: Any, key: str, default: Any = None) -> Any:
        if isinstance(result, Mapping):
            return result.get(key, default)
        return getattr(result, key, default)

    def _audio_result_view(self, result: Any, *, runner_kind: str) -> Dict[str, Any]:
        delivery = self._result_value(result, "delivery", {}) or {}
        if not isinstance(delivery, Mapping):
            delivery = {}
        timeline = delivery.get("timeline", {}) or {}
        if isinstance(timeline, Mapping):
            timeline_rows = list(timeline.get("spans", []) or [])
        else:
            timeline_rows = []
        gaps = list(delivery.get("gaps", []) or [])
        asset_pack = self._result_value(result, "asset_pack", {}) or {}
        machine_map = self._result_value(asset_pack, "machine_map", {}) or {}
        if not isinstance(machine_map, Mapping):
            machine_map = {}
        # Keep an explicit gap for every AUDIO_ONLY row even when a custom
        # runner omitted the richer delivery.gaps projection.
        if not gaps:
            for row in list(machine_map.get("rows", []) or []):
                if isinstance(row, Mapping) and row.get("decision") == "AUDIO_ONLY":
                    gaps.append({
                        "span_id": str(row.get("span_id", "")),
                        "reason": "AUDIO_ONLY",
                        "detail": str(row.get("why", row.get("placement_advice", "需要人工补画面"))),
                    })
        timeline_rows = [dict(item) for item in timeline_rows if isinstance(item, Mapping)][:200]
        gaps = [dict(item) for item in gaps if isinstance(item, Mapping)][:200]
        qa = self._result_value(result, "qa", {}) or {}
        if not isinstance(qa, Mapping):
            qa = {}
        qa_status = str(qa.get("package_gate_status", qa.get("status", "")) or "")
        raw_paths = self._result_value(result, "paths", {}) or {}
        if not isinstance(raw_paths, Mapping):
            raw_paths = {}
        path_keys = ("markdown", "csv", "json", "manifest", "qa", "narration", "alignment", "subtitle")
        paths = {
            key: str(raw_paths[key]) for key in path_keys
            if raw_paths.get(key)
        }
        preview = self._result_value(result, "preview_path", None)
        return {
            "status": "delivered" if qa_status in {"pass", "warnings", "accepted"} else "failed",
            "runner_kind": runner_kind,
            "timeline": timeline_rows,
            "gaps": gaps,
            "qa_status": qa_status,
            "paths": paths,
            "preview_path": str(preview) if preview else "",
            "timeline_count": len(timeline_rows),
            "gap_count": len(gaps),
        }

    def _set_audio_delivery_state(self, session_id: str, patch: Mapping[str, Any]) -> Dict[str, Any]:
        def _mutate(session_state):
            current = self._audio_delivery_defaults()
            current.update(session_state.get("audio_delivery") or {})
            current.update(dict(patch))
            session_state["audio_delivery"] = current

        session = self.store.update(session_id, _mutate)
        return self._audio_delivery_view(session)

    def run_audio_delivery(self, session_id: str) -> Dict[str, Any]:
        """Run the canonical local ASR/alignment/Edit Map chain once.

        Missing reviewed production/material inputs are a typed owner-review
        wait, not a fixture fallback.  An injected runner is used only by
        deterministic tests and is labeled ``fixture`` in session state.
        """

        session = self.store.load(session_id)
        audio = self._audio_view(session)
        media_path = Path(str(audio.get("path", ""))) if audio.get("path") else None
        if media_path is None or media_path.is_symlink() or not media_path.is_file():
            self._set_audio_delivery_state(session_id, {
                "status": "waiting_for_owner_audio",
                "error": "WAITING_FOR_OWNER_AUDIO：请先导入一份本地口播音频或视频",
                "completed_at": _now(),
            })
            raise WorkbenchFlowError(
                "WAITING_FOR_OWNER_AUDIO：请先导入一份本地口播音频或视频",
                payload={"status": "waiting_for_owner_audio"},
            )
        started_at = _now()
        runner_kind = "fixture" if self.audio_delivery_runner is not None else "real"
        self._set_audio_delivery_state(session_id, {
            "status": "running",
            "error": "",
            "runner_kind": runner_kind,
            "started_at": started_at,
            "completed_at": "",
        })
        try:
            if self.audio_delivery_runner is not None:
                result = self.audio_delivery_runner(self.store.session_dir(session_id), self.repo_root)
            else:
                from ..edit_bridge_session import (
                    resolve_real_edit_bridge_session,
                    run_real_edit_bridge_session,
                )
                from ..transcription.local_whisper_cpp import resolve_default_transcription_provider

                resolved = resolve_real_edit_bridge_session(
                    self.store.session_dir(session_id), repo_root=self.repo_root
                )
                result = run_real_edit_bridge_session(
                    resolved,
                    resolve_default_transcription_provider(),
                    clock=_now,
                    id_factory=lambda kind: f"{kind}-{uuid.uuid4().hex}",
                )
        except Exception as exc:
            from ..audio_delivery import AudioDeliveryError
            from ..edit_bridge_session import RealEditBridgeSessionError

            message = str(exc)[:500]
            if isinstance(exc, RealEditBridgeSessionError):
                status = "waiting_for_owner_review"
                message = f"WAITING_FOR_OWNER_REVIEW：{message}"
                payload_status = "waiting_for_owner_review"
            elif isinstance(exc, AudioDeliveryError):
                status = "failed"
                payload_status = "failed"
            else:
                status = "failed"
                payload_status = "failed"
            self._set_audio_delivery_state(session_id, {
                "status": status,
                "error": message,
                "runner_kind": runner_kind,
                "completed_at": _now(),
            })
            raise WorkbenchFlowError(message, payload={"status": payload_status}) from None
        summary = self._audio_result_view(result, runner_kind=runner_kind)
        summary["completed_at"] = _now()
        self._set_audio_delivery_state(session_id, summary)
        if summary["status"] != "delivered":
            raise WorkbenchFlowError(
                "Audio delivery QA 未通过，未交付可用 Edit Map",
                payload={"status": "failed", "qa_status": summary.get("qa_status", "")},
            )
        return summary

    # -- sources -------------------------------------------------------------

    def _next_sid(self, session: Mapping[str, Any]) -> str:
        used = {source["sid"] for source in session["sources"]}
        index = 1
        while f"S{index}" in used:
            index += 1
        return f"S{index}"

    def _store_source(
        self,
        session_id: str,
        *,
        url: str,
        title: str,
        text: str,
        kind: str,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        existing = None
        session = self.store.load(session_id)
        for source in session["sources"]:
            if source["url"] == url:
                existing = source
                break
        sid = existing["sid"] if existing else self._next_sid(session)
        filename = f"{sid}.json"
        path = self.store.sources_dir(session_id) / filename
        payload = {
            "sid": sid,
            "url": url,
            "title": title,
            "kind": kind,
            "text": text,
            "fetched_at": _now(),
            **(dict(extra) if extra else {}),
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        def _mutate(new_session):
            if existing is None:
                new_session["sources"].append({
                    key: payload.get(key, "") for key in (
                        "sid", "url", "title", "kind", "fetched_at",
                        "request_id", "retrieved_at", "published_at",
                        "provenance_method", "provenance_status", "sha256",
                    )
                })
            else:
                for source in new_session["sources"]:
                    if source["sid"] == sid:
                        source["title"] = title
                        source["kind"] = kind
                        source["fetched_at"] = payload["fetched_at"]
                        for key in (
                            "request_id", "retrieved_at", "published_at",
                            "provenance_method", "provenance_status", "sha256",
                        ):
                            if key in payload:
                                source[key] = payload[key]

        self.store.update(session_id, _mutate)
        return {key: payload[key] for key in ("sid", "url", "title", "kind", "fetched_at")}

    def add_source_url(self, session_id: str, url: str) -> Dict[str, Any]:
        if not isinstance(url, str):
            raise WorkbenchFlowError("来源链接必须是文本")
        cleaned = url.strip()
        if not cleaned.startswith(("http://", "https://")):
            raise WorkbenchFlowError("来源链接必须是 http(s) 地址")
        result = self.fetcher(cleaned)
        if not result.get("ok"):
            raise WorkbenchFlowError(f"来源抓取失败：{result.get('error', '未知错误')}")
        return self._store_source(
            session_id,
            url=cleaned,
            title=str(result.get("title", cleaned))[:200],
            text=str(result.get("text", "")),
            kind="fetched",
            extra={"sha256": result.get("sha256", ""), "final_url": result.get("final_url", cleaned)},
        )

    def add_source_text(
        self, session_id: str, title: str, text: str, url: str = ""
    ) -> Dict[str, Any]:
        if not isinstance(title, str) or not title.strip():
            raise WorkbenchFlowError("请给粘贴来源一个标题")
        if not isinstance(text, str) or len(text.strip()) < 50:
            raise WorkbenchFlowError("粘贴文本至少 50 字，太短无法支撑研究")
        clean_url = (url or "").strip()
        if clean_url and not clean_url.startswith(("http://", "https://")):
            raise WorkbenchFlowError("来源链接必须是 http(s) 地址")
        if not clean_url:
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
            clean_url = f"workbench://pasted/{digest}"
        return self._store_source(
            session_id,
            url=clean_url,
            title=title.strip()[:200],
            text=text.strip(),
            kind="pasted",
            extra={"user_pasted": True},
        )

    def _sources_payload(self, session: Mapping[str, Any]) -> List[Dict[str, Any]]:
        payload = []
        for source in session["sources"]:
            path = self.store.sources_dir(session["session_id"]) / f"{source['sid']}.json"
            data = self.store.load_json(path)
            payload.append(
                {
                    "sid": data["sid"],
                    "url": data["url"],
                    "title": data["title"],
                    "kind": data.get("kind", ""),
                    "text": data.get("text", ""),
                }
            )
        return payload

    # -- optional DeepSeek Search/Fetch tools -------------------------------

    def _deepseek_settings(self) -> Dict[str, Any]:
        settings = load_settings(self.repo_root)
        if settings.get("provider_mode") != "deepseek":
            raise WorkbenchFlowError(
                "DeepSeek Search/Fetch 仅在设置中选择 DeepSeek 提供方式后可用"
            )
        if not is_configured(settings):
            raise WorkbenchFlowError(
                "设置尚未完成（WAITING_FOR_OWNER_API_KEY）：请先在设置中填写 DeepSeek API Key、模型和服务地址",
                payload={"status": "waiting_for_api_key", "connection_kind": self.connection_kind},
            )
        return settings

    @staticmethod
    def _validate_search_opt_in(opt_in: Any) -> None:
        if opt_in is not True:
            raise WorkbenchFlowError(
                "DeepSeek Search/Fetch 可能产生计费；请先明确勾选并设置本次请求上限"
            )

    @staticmethod
    def _requested_search_cap(value: Any, current: int = 0) -> int:
        if value is None or value == "":
            value = current or DEEPSEEK_DEFAULT_REQUESTS
        if isinstance(value, bool) or not isinstance(value, int):
            raise WorkbenchFlowError(
                f"DeepSeek Search/Fetch 请求上限必须是 1–{DEEPSEEK_MAX_REQUESTS} 的整数"
            )
        if not 1 <= value <= DEEPSEEK_MAX_REQUESTS:
            raise WorkbenchFlowError(
                f"DeepSeek Search/Fetch 请求上限必须是 1–{DEEPSEEK_MAX_REQUESTS} 的整数"
            )
        if current and value > current:
            raise WorkbenchFlowError("本集请求上限只能保持或降低，不能在已开始后提高")
        return value

    def _reserve_deepseek_request(
        self,
        session_id: str,
        *,
        operation: str,
        opt_in: Any,
        max_requests: Any,
    ) -> Tuple[Dict[str, Any], str]:
        """Atomically record one billed-tool slot before the network call."""

        self._validate_search_opt_in(opt_in)
        settings = self._deepseek_settings()
        token = uuid.uuid4().hex[:16]

        def _mutate(session_state):
            raw = session_state.get("search_budget") or {}
            budget = self._search_budget_defaults()
            for key in budget:
                if key in raw:
                    budget[key] = raw[key]
            cap = self._requested_search_cap(max_requests, int(budget.get("max_requests", 0) or 0))
            used = int(budget.get("used", 0) or 0)
            if used >= cap:
                raise WorkbenchFlowError(
                    f"DeepSeek Search/Fetch 本集请求已达到上限（{cap} 次）；请降低范围或开启新会话"
                )
            budget.update({"opt_in": True, "max_requests": cap, "used": used + 1, "last_error": ""})
            records = list(budget.get("records") or [])
            records.append({
                "token": token,
                "operation": operation,
                "reserved_at": _now(),
                "status": "reserved",
            })
            budget["records"] = records[-100:]
            session_state["search_budget"] = budget

        self.store.update(session_id, _mutate)
        return settings, token

    @staticmethod
    def _safe_request_id(value: Any) -> str:
        clean = str(value or "")[:200]
        return clean if re.fullmatch(r"[A-Za-z0-9._:-]{0,200}", clean) else ""

    @staticmethod
    def _safe_tool_error(exc: BaseException, api_key: str = "") -> str:
        message = str(exc)[:500]
        if api_key:
            message = message.replace(api_key, "[已隐藏]")
        return message

    def _finish_deepseek_request(
        self,
        session_id: str,
        token: str,
        *,
        status: str,
        request_id: str = "",
        detail: Optional[Mapping[str, Any]] = None,
        error: str = "",
    ) -> Dict[str, Any]:
        def _mutate(session_state):
            budget = self._search_budget_defaults()
            raw = session_state.get("search_budget") or {}
            for key in budget:
                if key in raw:
                    budget[key] = raw[key]
            records = list(budget.get("records") or [])
            for record in reversed(records):
                if isinstance(record, dict) and record.get("token") == token:
                    record.update({
                        "status": status,
                        "request_id": self._safe_request_id(request_id),
                        "finished_at": _now(),
                    })
                    if detail:
                        record.update(dict(detail))
                    if error:
                        record["error"] = error[:500]
                    break
            budget["records"] = records[-100:]
            budget["last_error"] = error[:500] if error else ""
            session_state["search_budget"] = budget

        session = self.store.update(session_id, _mutate)
        return self._search_budget_view(session)

    def _deepseek_client(self, settings: Mapping[str, Any]):
        try:
            return self.deepseek_client_factory(settings)
        except DeepSeekToolError as exc:
            raise WorkbenchFlowError(
                self._safe_tool_error(exc, str(settings.get("api_key", ""))),
                payload={"status": "failed", "error_category": exc.category},
            ) from None

    def search_deepseek(
        self,
        session_id: str,
        query: str,
        *,
        opt_in: bool,
        max_requests: Optional[int] = None,
        count: int = 5,
        need_content: bool = False,
    ) -> Dict[str, Any]:
        query = str(query or "").strip()
        if not query or len(query) > DEEPSEEK_MAX_QUERY_CHARS:
            raise WorkbenchFlowError(
                f"DeepSeek Search 问题不能为空且不能超过 {DEEPSEEK_MAX_QUERY_CHARS} 字"
            )
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 50:
            raise WorkbenchFlowError("DeepSeek Search 返回数量必须是 1–50 的整数")
        settings, token = self._reserve_deepseek_request(
            session_id,
            operation="search",
            opt_in=opt_in,
            max_requests=max_requests,
        )
        try:
            client = self._deepseek_client(settings)
            result = client.search(query, count=count, need_content=bool(need_content))
            request_id = self._safe_request_id(result.get("request_id", ""))
            retrieved_at = _now()
            safe_results = []
            for item in result.get("results", [])[:50]:
                if not isinstance(item, Mapping):
                    continue
                url = str(item.get("url", "")).strip()
                if not url.startswith(("http://", "https://")):
                    continue
                safe_results.append({
                    "title": str(item.get("title", ""))[:300],
                    "url": url[:2000],
                    "published_at": str(item.get("published_at", ""))[:80],
                    "snippet": str(item.get("content", item.get("snippet", "")))[:800],
                    "request_id": request_id,
                    "retrieved_at": retrieved_at,
                    "provenance_status": "discovered_only",
                    "is_evidence": False,
                })
            budget = self._finish_deepseek_request(
                session_id,
                token,
                status="succeeded",
                request_id=request_id,
                detail={"query": query, "result_count": len(safe_results)},
            )

            def _store_results(session_state):
                raw = session_state.get("search_budget") or {}
                merged = self._search_budget_defaults()
                for key in merged:
                    if key in raw:
                        merged[key] = raw[key]
                merged["results"] = (list(merged.get("results") or []) + safe_results)[-50:]
                session_state["search_budget"] = merged

            session = self.store.update(session_id, _store_results)
            return {
                "query": query,
                "request_id": request_id,
                "results": safe_results,
                "search_budget": self._search_budget_view(session),
            }
        except Exception as exc:
            message = self._safe_tool_error(exc, str(settings.get("api_key", "")))
            category = getattr(exc, "category", "provider_error")
            budget = self._finish_deepseek_request(
                session_id,
                token,
                status="failed",
                error=message,
                detail={"error_category": category},
            )
            raise WorkbenchFlowError(
                message,
                payload={"status": "failed", "error_category": category, "search_budget": budget},
            ) from None

    def fetch_deepseek_source(
        self,
        session_id: str,
        url: str,
        *,
        opt_in: bool,
        max_requests: Optional[int] = None,
    ) -> Dict[str, Any]:
        cleaned = str(url or "").strip()
        if not cleaned.startswith(("http://", "https://")):
            raise WorkbenchFlowError("DeepSeek Fetch 只接受 http(s) 原文链接")
        session = self.store.load(session_id)
        budget = self._search_budget_view(session)
        selected = any(
            isinstance(item, Mapping) and item.get("url") == cleaned
            for item in budget.get("results", [])
        )
        if not selected:
            raise WorkbenchFlowError("请先在本集 DeepSeek Search 结果中选择要抓取的链接")
        settings, token = self._reserve_deepseek_request(
            session_id,
            operation="fetch",
            opt_in=opt_in,
            max_requests=max_requests,
        )
        try:
            client = self._deepseek_client(settings)
            result = client.fetch(cleaned)
            request_id = self._safe_request_id(result.get("request_id", ""))
            text = str(result.get("content", ""))
            retrieved_at = _now()
            source = self._store_source(
                session_id,
                url=cleaned,
                title=str(result.get("title", cleaned))[:200],
                text=text,
                kind="deepseek_fetched",
                extra={
                    "request_id": request_id,
                    "retrieved_at": retrieved_at,
                    "published_at": str(result.get("published_at", ""))[:80],
                    "provenance_method": "deepseek_fetch",
                    "provenance_status": "fetched",
                    "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                },
            )
            budget = self._finish_deepseek_request(
                session_id,
                token,
                status="succeeded",
                request_id=request_id,
                detail={"url": cleaned, "sid": source["sid"]},
            )
            return {
                **source,
                "request_id": request_id,
                "retrieved_at": retrieved_at,
                "search_budget": budget,
            }
        except Exception as exc:
            message = self._safe_tool_error(exc, str(settings.get("api_key", "")))
            category = getattr(exc, "category", "provider_error")
            budget = self._finish_deepseek_request(
                session_id,
                token,
                status="failed",
                error=message,
                detail={"url": cleaned, "error_category": category},
            )
            raise WorkbenchFlowError(
                message,
                payload={"status": "failed", "error_category": category, "search_budget": budget},
            ) from None

    # -- research ------------------------------------------------------------

    def _source_known(self, session: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
        known = {}
        for source in session["sources"]:
            path = self.store.sources_dir(session["session_id"]) / f"{source['sid']}.json"
            if path.is_file():
                data = self.store.load_json(path)
                known[data["url"]] = data
        return known

    def generate_research(
        self,
        session_id: str,
        research_question: str = "",
        *,
        allow_partial: bool = False,
        partial_reason: str = "",
    ) -> Dict[str, Any]:
        session = self.store.load(session_id)
        if not session["sources"]:
            raise WorkbenchFlowError("请先添加至少一条研究来源（网页链接或粘贴文本）")
        # Issue #23 B3: reference-analysis readiness.  Research must see
        # every *authorized* (downloaded) reference analyzed, or carry an
        # explicit, reason-bearing partial-analysis override — 1/5 must
        # never be silently labeled as full synthesis.
        readiness = self._reference_readiness(session)
        pending = readiness["pending_bvids"]
        if pending and not allow_partial:
            failure_note = (
                f"其中 {len(readiness['failed_bvids'])} 条下载失败，请先重试；"
                if readiness["failed_bvids"]
                else ""
            )
            if readiness.get("unverified_bvids"):
                failure_note += (
                    f"其中 {len(readiness['unverified_bvids'])} 条只有本地转写、尚未通过模型分析，请先重试；"
                )
            raise WorkbenchFlowError(
                f"参考分析尚未完成：已分析 {readiness['analyzed']}/{readiness['eligible']} 条已授权参考，"
                f"还有 {len(pending)} 条未完成（下载待分析或失败）。{failure_note}"
                "请先完成剩余参考的分析；"
                "若确认要基于部分参考继续（将如实记录为部分分析，不等同完整五方对比），"
                "请勾选「允许部分分析」并填写理由。"
            )
        if pending and allow_partial:
            reason = str(partial_reason or "").strip()
            if len(reason) < 10:
                raise WorkbenchFlowError(
                    "选择「允许部分分析」时必须填写不少于 10 字的理由（将逐字存档）"
                )
        llm = self._llm()
        sources_payload = self._sources_payload(session)
        insights = self._narrative_insights(session)
        try:
            result = llm.research(session["topic"], research_question or "", sources_payload, insights)
        except WorkbenchLLMError as exc:
            raise WorkbenchFlowError(str(exc)) from None
        try:
            validate_json_schema(result.data, API_RESEARCH_DRAFT_JSON_SCHEMA, "api_research_draft")
        except ReportValidationError as exc:
            raise WorkbenchFlowError(f"研究草稿结构不符合合同：{exc}") from None
        known = self._source_known(session)
        content = json.loads(json.dumps(result.data, ensure_ascii=False))
        invented = []
        for source in content["sources"]:
            source["normalized_url"] = source["url"]
            record = known.get(source["url"])
            if record is not None:
                source["inspection_method"] = "manual_open"
                source["provenance_method"] = "user_supplied"
                source["provenance_status"] = "matched"
                source["provenance_refs"] = [record["url"], record["fetched_at"]]
                source["stance_summary"] = source.get("stance_summary", "")
                source["credibility_notes"] = source.get(
                    "credibility_notes", "由工作台本地抓取/用户提供的原文材料。"
                )
            else:
                mode = load_settings(self.repo_root)["provider_mode"]
                if mode == "chat":
                    invented.append(source["url"])
                    continue
                source["inspection_method"] = "openai_web_search_tool"
                source["provenance_method"] = "web_search_action_source"
                source["provenance_status"] = "unmatched"
                source["provenance_refs"] = []
        for claim in content["claims"]:
            claim["verification_status"] = "not_checked"
        for link in content.get("evidence_links", []):
            link["independence_group"] = "pending"
            link["verified_in_review"] = False
        if invented:
            raise WorkbenchFlowError(
                "研究草稿引用了未提供的来源（chat 模式必须只用你添加的材料）："
                + "；".join(invented[:3])
            )
        content = _prune_dangling(content)
        # Issue #23 B1: fail closed on off-topic research before anything is
        # saved (the observed E2E mismatch: Moscow session, library payload).
        ensure_topic_consistency(
            session["topic"], _report_topic_texts(content),
            what="研究草稿",
        )
        report_id = f"RPT-{uuid.uuid4().hex}"
        created = _now()
        data = {
            "schema_version": "0.2",
            "report_id": report_id,
            "revision": 1,
            "previous_revision": 0,
            "created_at": created,
            "generated_at": created,
            "research_mode": "openai_api",
            "status": "fact_check_pending",
            "change_summary": "工作台 LLM 研究草稿完成，等待独立事实核查。",
            "corrections": [],
            **content,
            "topic": session["topic"],
            "fact_check": {
                "review_id": "",
                "reviewed_at": "",
                "status": "not_run",
                "checked_claim_ids": [],
                "unresolved_claim_ids": [],
            },
            "quality_summary": {},
            "approval_gate": {
                "status": "pending",
                "requires_user_confirmation": True,
                "high_risk_claim_ids": [
                    claim["id"] for claim in content["claims"]
                    if claim["risk_level"] in {"high", "critical"}
                ],
                "user_confirmation": "",
                "ready_for_script": False,
            },
        }
        data = normalize_report_sources(data)
        data["quality_summary"] = calculate_quality_summary(data)
        report = ResearchReport.from_dict(data)
        paths = save_report(report, self.repo_root / "reports")

        def _mutate(new_session):
            new_session["research"] = {
                "status": "fact_check_pending",
                "draft_path": str(paths.json),
                "reviewed_path": "",
                "approved_path": "",
                "report_id": report_id,
                "revision": report.revision,
                "reference_comparison": comparison,
            }
            new_session["status"] = "research"

        comparison = self._comparison_snapshot(
            session, readiness, partial_reason=partial_reason
        )
        self.store.update(session_id, _mutate)
        return {
            "report_id": report_id,
            "revision": report.revision,
            "status": report.status,
            "draft_path": str(paths.json),
            "gate_status": report.quality_summary.get("gate_status", ""),
            "gate_reasons": report.quality_summary.get("gate_reasons", []),
            "claim_count": len(content["claims"]),
            "source_count": len(content["sources"]),
            "reference_comparison": {
                "analyzed": comparison["analyzed"],
                "eligible": comparison["eligible"],
                "viewpoint_count": comparison["viewpoint_count"],
                "partial": comparison["partial"],
            },
        }

    def _reference_readiness(self, session: Mapping[str, Any]) -> Dict[str, Any]:
        """Issue #23 B3: analyzed-N / eligible-M readiness of authorized refs.

        Eligible = references the owner actually authorized (downloaded,
        analyzed, or a persisted failed attempt after valid authorization).
        Never-downloaded discovery candidates are not "pending" — they were
        never authorized — so choosing not to acquire a reference never blocks
        research.  A failed authorized attempt is unresolved and therefore
        blocks research until retry or an explicit partial-analysis override.
        Any persisted ``failed`` state remains fail-closed even if an older
        session lacks a failure-stage field.
        """
        references = session.get("references", {})
        analyzed: List[str] = []
        download_pending: List[str] = []
        failed: List[str] = []
        unverified: List[str] = []
        for bvid, state in references.items():
            status = (state or {}).get("status")
            if status == "analyzed":
                analyzed.append(bvid)
            elif status == "downloaded":
                download_pending.append(bvid)
            elif status == "failed":
                failed.append(bvid)
            elif status in {"unverified", "analysis_failed", "transcribing"}:
                unverified.append(bvid)
        pending = download_pending + failed + unverified
        return {
            "analyzed": len(analyzed),
            "eligible": len(analyzed) + len(download_pending) + len(failed),
            "download_pending": len(download_pending),
            "failed": len(failed),
            "unverified": len(unverified),
            "unresolved": len(pending),
            "pending_bvids": pending,
            "download_pending_bvids": download_pending,
            "failed_bvids": failed,
            "unverified_bvids": unverified,
        }

    def _comparison_snapshot(
        self, session: Mapping[str, Any], readiness: Mapping[str, Any],
        partial_reason: str = "",
    ) -> Dict[str, Any]:
        """Honest snapshot of what the reference comparison actually used."""
        insights = self._narrative_insights(session)
        return {
            "analyzed": readiness["analyzed"],
            "eligible": readiness["eligible"],
            "bvids": [str(insight.get("bvid", "")) for insight in insights if insight.get("bvid")],
            "viewpoint_count": sum(
                1 for insight in insights if insight.get("creator_viewpoint")
            ),
            "partial": bool(readiness["pending_bvids"]),
            "partial_reason": (
                str(partial_reason or "").strip() if readiness["pending_bvids"] else ""
            ),
            "pending_bvids": list(readiness["pending_bvids"]),
            "download_pending_bvids": list(readiness["download_pending_bvids"]),
            "failed_bvids": list(readiness["failed_bvids"]),
            "failure_reasons": {
                str(bvid): str((session.get("references", {}).get(bvid) or {}).get("failure_reason", ""))
                for bvid in readiness["failed_bvids"]
            },
            "recorded_at": _now(),
        }

    def run_fact_check(self, session_id: str) -> Dict[str, Any]:
        session = self.store.load(session_id)
        draft_path = session["research"].get("draft_path", "")
        if not draft_path:
            raise WorkbenchFlowError("请先生成研究草稿")
        draft = ResearchReport.from_dict(
            json.loads(Path(draft_path).read_text(encoding="utf-8"))
        )
        # independent re-fetch of every research source (real tool actions)
        sources_payload = []
        for source in session["sources"]:
            path = self.store.sources_dir(session_id) / f"{source['sid']}.json"
            data = self.store.load_json(path)
            entry = {"sid": data["sid"], "url": data["url"], "title": data["title"], "kind": data.get("kind", ""), "text": data.get("text", "")}
            if data.get("kind") == "fetched":
                fresh = self.fetcher(data["url"])
                if fresh.get("ok"):
                    entry["text"] = str(fresh.get("text", entry["text"]))
                    entry["refetched_at"] = fresh.get("fetched_at", _now())
            sources_payload.append(entry)
        consulted_urls = [entry["url"] for entry in sources_payload if entry["url"].startswith(("http://", "https://"))]
        if not consulted_urls:
            raise WorkbenchFlowError(
                "独立核查至少需要一条带 http(s) 原链接的来源：纯粘贴来源请在粘贴时附上原文链接，或另加一条可访问链接。"
            )
        llm = self._llm()
        try:
            result = llm.fact_check(draft.to_dict(), sources_payload)
        except WorkbenchLLMError as exc:
            raise WorkbenchFlowError(str(exc)) from None
        provider_search_calls = list(getattr(result.provenance, "search_calls", ()) or ())
        try:
            validate_json_schema(result.data, FACT_CHECK_JSON_SCHEMA, "fact_check_artifact")
        except ReportValidationError as exc:
            raise WorkbenchFlowError(f"事实核查结果结构不符合合同：{exc}") from None
        artifact = json.loads(json.dumps(result.data, ensure_ascii=False))
        artifact.update(
            {
                "artifact_version": "0.2",
                "review_id": f"FC-wb-{uuid.uuid4().hex}",
                "report_id": draft.report_id,
                "report_revision": draft.revision,
                "created_at": _now(),
                "research_mode": "openai_api",
            }
        )
        fetched_urls = consulted_urls
        call_ids = [
            "webui-fetch-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]
            for url in fetched_urls
        ]
        call_ids.extend(
            call.call_id for call in provider_search_calls if getattr(call, "call_id", "")
        )
        artifact["tool_provenance"] = {
            "search_call_ids": call_ids or ["webui-fetch-none"],
            "search_queries": list(
                dict.fromkeys(
                    query
                    for call in provider_search_calls
                    for query in getattr(call, "queries", ())
                )
            ),
            "consulted_urls": fetched_urls,
            "citation_urls": [],
        }
        artifact["new_sources"] = []
        artifact["evidence_links"] = []
        artifact["checks"] = self._apply_quote_verification(
            artifact.get("checks", []),
            draft,
            self._draft_source_texts(session, draft),
            provider_searched=bool(provider_search_calls),
        )
        artifact = normalize_fact_check_sources(artifact, draft)
        validate_fact_check_artifact(artifact, draft)
        downgraded = sum(
            1 for check in artifact["checks"]
            if "降级为 unverified" in str(check.get("verification_notes", ""))
        )
        review = run_fact_check_review(draft, artifact, self.repo_root / "reports")
        final = ResearchReport.from_dict(
            json.loads(Path(review.reviewed.json).read_text(encoding="utf-8"))
        )

        def _mutate(new_session):
            new_session["research"]["reviewed_path"] = str(review.reviewed.json)
            new_session["research"]["revision"] = final.revision
            new_session["research"]["status"] = final.status

        self.store.update(session_id, _mutate)
        return {
            "status": final.status,
            "revision": final.revision,
            "gate_status": final.quality_summary.get("gate_status", ""),
            "gate_reasons": final.quality_summary.get("gate_reasons", []),
            "checked_claims": len(artifact.get("checks", [])),
            "quote_downgraded_checks": downgraded,
            "unresolved_high_risk": final.quality_summary.get("unresolved_high_risk_count", 0),
            "reviewed_path": str(review.reviewed.json),
        }

    def _draft_source_texts(
        self, session: Mapping[str, Any], draft: ResearchReport
    ) -> Dict[str, str]:
        """Map DRAFT source ids to their cached texts (fetched or user-pasted)."""

        known = self._source_known(session)
        texts = {}
        for source in draft.data["sources"]:
            record = known.get(source.get("url", ""))
            if record is not None:
                texts[source["id"]] = str(record.get("text", ""))
        return texts

    @staticmethod
    def _apply_quote_verification(
        checks: List[Dict[str, Any]],
        draft: ResearchReport,
        texts_by_sid: Dict[str, str],
        provider_searched: bool,
    ) -> List[Dict[str, Any]]:
        claim_sources = {}
        for link in draft.data["evidence_links"]:
            claim_sources.setdefault(link["claim_id"], set()).add(link["source_id"])
        for check in checks:
            if check.get("outcome") not in ("verified", "partially_verified"):
                continue
            notes = str(check.get("verification_notes", ""))
            quotes = re.findall(r"[「“]([^「」“”]{12,200})[」”]", notes)
            if not quotes:
                check["outcome"] = "unverified"
                check["verification_notes"] = (
                    notes + "（服务器核对：未附原文引用，降级为 unverified）"
                ).strip()
                continue
            if provider_searched:
                # provider carried its own web-search provenance; trust its
                # quote record, but still require at least one quote to exist
                continue
            candidate_texts = []
            for source_id in check.get("source_ids", []) or claim_sources.get(
                check.get("claim_id", ""), set()
            ):
                candidate_texts.append(texts_by_sid.get(source_id, ""))
            normalized = [re.sub(r"\s+", "", text) for text in candidate_texts if text]
            grounded = any(
                re.sub(r"\s+", "", quote) in text for quote in quotes for text in normalized
            )
            if not grounded:
                check["outcome"] = "unverified"
                check["verification_notes"] = (
                    notes + "（服务器逐字核对未在来源原文中找到引用，降级为 unverified）"
                ).strip()
        return checks

    def approve_research(self, session_id: str, confirmation: str) -> Dict[str, Any]:
        session = self.store.load(session_id)
        reviewed_path = session["research"].get("reviewed_path", "")
        if not reviewed_path:
            raise WorkbenchFlowError("请先完成独立事实核查")
        report = ResearchReport.from_dict(
            json.loads(Path(reviewed_path).read_text(encoding="utf-8"))
        )
        # Issue #23 B1: an off-topic report can never be approved, even if a
        # draft slipped in through another path.
        ensure_topic_consistency(
            session["topic"], _report_topic_texts(report.to_dict()),
            what="待批准的研究报告",
        )
        if not str(confirmation).strip():
            raise WorkbenchFlowError("请填写明确的批准确认说明")
        paths = run_report_approval(
            report, confirmation.strip(), self.repo_root / "reports"
        )
        approved = ResearchReport.from_dict(
            json.loads(Path(paths.json).read_text(encoding="utf-8"))
        )

        def _mutate(new_session):
            new_session["research"]["approved_path"] = str(paths.json)
            new_session["research"]["status"] = approved.status
            new_session["research"]["revision"] = approved.revision
            new_session["status"] = "thesis"

        self.store.update(session_id, _mutate)
        return {
            "status": approved.status,
            "revision": approved.revision,
            "ready_for_script": approved.approval_gate.get("ready_for_script", False),
            "path": str(paths.json),
        }

    def _approved_report(self, session: Mapping[str, Any]) -> ResearchReport:
        path = session["research"].get("approved_path", "")
        if not path:
            raise WorkbenchFlowError("请先批准研究报告，再进行这一步")
        return ResearchReport.from_dict(
            json.loads(Path(path).read_text(encoding="utf-8"))
        )

    # -- thesis --------------------------------------------------------------

    def generate_thesis(self, session_id: str) -> Dict[str, Any]:
        session = self.store.load(session_id)
        report = self._approved_report(session)
        llm = self._llm()
        insights = self._narrative_insights(session)
        try:
            result = llm.write_thesis(report.to_dict(), insights)
        except WorkbenchLLMError as exc:
            raise WorkbenchFlowError(str(exc)) from None
        # Issue #23 B1: fail closed on off-topic thesis payload before save.
        ensure_topic_consistency(
            session["topic"], _card_topic_texts(result.data),
            what="选题卡草稿",
        )
        card_id = f"CTC-wb-{session['session_id'].split('-')[-1]}"
        prepared = prepare_codex_content_thesis(
            result.data, report, self.repo_root / "content_theses", card_id=card_id
        )
        card = prepared.card

        def _mutate(new_session):
            new_session["thesis"] = {
                "status": card.status,
                "card_id": card.card_id,
                "draft_path": str(prepared.paths.json),
                "review_path": "",
                "approved_path": "",
            }
            new_session["status"] = "thesis"

        self.store.update(session_id, _mutate)
        return self._thesis_summary(card, str(prepared.paths.json))

    @staticmethod
    def _thesis_summary(card: ContentThesisCard, path: str) -> Dict[str, Any]:
        data = card.data
        return {
            "card_id": card.card_id,
            "revision": card.revision,
            "status": card.status,
            "core_question": data.get("core_question", ""),
            "core_thesis": data.get("core_thesis", ""),
            "differentiated_angle": data.get("differentiated_angle", ""),
            "hook_promise": data.get("hook_promise", ""),
            "path": path,
        }

    def review_thesis(self, session_id: str) -> Dict[str, Any]:
        session = self.store.load(session_id)
        report = self._approved_report(session)
        draft_path = session["thesis"].get("draft_path", "")
        if not draft_path:
            raise WorkbenchFlowError("请先生成选题卡")
        card = ContentThesisCard(
            json.loads(Path(draft_path).read_text(encoding="utf-8"))
        )
        llm = self._llm()
        profile = load_content_director_profile()
        check_names = list(profile["thesis_gate_checks"])
        try:
            result = llm.review_thesis(report.to_dict(), card.data, check_names)
        except WorkbenchLLMError as exc:
            raise WorkbenchFlowError(str(exc)) from None
        reviewed = run_codex_content_thesis_review(
            result.data,
            card,
            report,
            self.repo_root / "content_theses",
            profile=profile,
        )
        gate = reviewed.artifact["gate"]

        def _mutate(new_session):
            new_session["thesis"]["status"] = "reviewed"
            new_session["thesis"]["review_path"] = str(reviewed.paths.json)

        self.store.update(session_id, _mutate)
        return {
            "gate_decision": gate["decision"],
            "blocking_issue_count": gate["blocking_issue_count"],
            "checks": [
                {key: check[key] for key in ("check_name", "outcome", "reason")}
                for check in reviewed.artifact["content"]["checks"]
            ],
            "review_path": str(reviewed.paths.json),
            "user_review": reviewed.user_review,
        }

    def approve_thesis(self, session_id: str, confirmation: str) -> Dict[str, Any]:
        session = self.store.load(session_id)
        report = self._approved_report(session)
        draft_path = session["thesis"].get("draft_path", "")
        review_path = session["thesis"].get("review_path", "")
        if not draft_path or not review_path:
            raise WorkbenchFlowError("请先生成并审核选题卡")
        card = ContentThesisCard(
            json.loads(Path(draft_path).read_text(encoding="utf-8"))
        )
        # Issue #23 B1: an off-topic card can never be confirmed for writing.
        ensure_topic_consistency(
            session["topic"], _card_topic_texts(card.data),
            what="待确认的选题卡",
        )
        review_artifact = json.loads(Path(review_path).read_text(encoding="utf-8"))
        if not str(confirmation).strip():
            raise WorkbenchFlowError("请填写明确的选题确认说明（需包含「确认」与「进入写稿」）")
        confirmed = confirm_content_thesis(
            card,
            review_artifact,
            report,
            self.repo_root / "content_theses",
            confirmation=confirmation.strip(),
        )

        def _mutate(new_session):
            new_session["thesis"]["status"] = confirmed.card.status
            new_session["thesis"]["approved_path"] = str(confirmed.paths.json)

        self.store.update(session_id, _mutate)
        return {
            "status": confirmed.card.status,
            "card_id": confirmed.card.card_id,
            "revision": confirmed.card.revision,
        }

    def _approved_thesis(self, session: Mapping[str, Any]) -> ContentThesisCard:
        path = session["thesis"].get("approved_path", "")
        if not path:
            raise WorkbenchFlowError("请先人工确认选题卡，再进行写稿")
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        review_path = session["thesis"].get("review_path", "")
        review_artifact = (
            json.loads(Path(review_path).read_text(encoding="utf-8"))
            if review_path and Path(review_path).is_file()
            else None
        )
        return ContentThesisCard(data, review_artifact)

    # -- script --------------------------------------------------------------

    def generate_script(self, session_id: str) -> Dict[str, Any]:
        session = self.store.load(session_id)
        report = self._approved_report(session)
        card = self._approved_thesis(session)
        # Issue #23 B1: an off-topic report/card can never drive a script —
        # and an off-topic script can never reach the delivery view.
        ensure_topic_consistency(
            session["topic"], _report_topic_texts(report.to_dict()),
            what="写稿所依据的研究报告",
        )
        ensure_topic_consistency(
            session["topic"], _card_topic_texts(card.data),
            what="写稿所依据的选题卡",
        )
        llm = self._llm()
        result = run_script_workflow(
            report,
            llm,
            self.repo_root / "script_drafts",
            profile=load_workbench_script_profile(),
            content_thesis_card=card,
        )
        teleprompter_path = Path(result.reviewed.json).with_name(
            Path(result.reviewed.json).stem + ".teleprompter.md"
        )
        if teleprompter_path.is_file():
            ensure_topic_consistency(
                session["topic"], [teleprompter_path.read_text(encoding="utf-8")],
                what="口播稿",
            )
        view = self._script_view(session_id, str(result.reviewed.json))
        view["review_path"] = str(result.review_artifact)
        if view.get("gate_status") != "pass":
            view["blocking_issues"] = self._review_blocking_issues(result.review_artifact)
        return view

    @staticmethod
    def _review_blocking_issues(review_artifact_path: str) -> List[Dict[str, Any]]:
        try:
            artifact = json.loads(Path(review_artifact_path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return [
            {
                "issue_id": issue.get("issue_id", ""),
                "issue_type": issue.get("issue_type", ""),
                "explanation": issue.get("explanation", issue.get("description", "")),
                "suggested_fix": issue.get("suggested_fix", ""),
            }
            for issue in artifact.get("issues", [])
            if issue.get("severity") == "blocking"
        ][:8]

    def _script_view(self, session_id: str, script_json_path: str) -> Dict[str, Any]:
        session = self.store.load(session_id)
        report = self._approved_report(session)
        card = self._approved_thesis(session)
        profile = load_workbench_script_profile()
        script = load_script(
            Path(script_json_path), report, profile, content_thesis_card=card
        )
        teleprompter = Path(script_json_path).with_name(
            Path(script_json_path).stem + ".teleprompter.md"
        )
        review_state = script.data.get("review_state", {})

        def _mutate(new_session):
            new_session["script"] = {
                "status": script.status,
                "script_id": script.script_id,
                "revision": script.revision,
                "reviewed_path": script_json_path,
                "gate_status": review_state.get("review_gate_status", ""),
            }
            new_session["status"] = "script"

        self.store.update(session_id, _mutate)
        return {
            "script_id": script.script_id,
            "revision": script.revision,
            "status": script.status,
            "gate_status": review_state.get("review_gate_status", ""),
            "working_title": script.data.get("working_title", ""),
            "character_count": script.character_count,
            "estimated_duration_minutes": script.estimated_duration_minutes,
            "beat_count": len(script.beats),
            "teleprompter_path": str(teleprompter),
            "teleprompter_text": teleprompter.read_text(encoding="utf-8")
            if teleprompter.is_file()
            else "",
            "topic": session.get("topic", ""),
            "reference_synthesis": self._synthesis_view(session.get("research", {})),
        }

    @staticmethod
    def _synthesis_view(research: Mapping[str, Any]) -> Dict[str, Any]:
        """Honest reference-synthesis summary shown with every script view
        (Issue #23 B3): analyzed N / eligible M, partial or not, including
        unresolved acquisition identifiers when a partial override was used."""
        comparison = research.get("reference_comparison") or {}
        if not comparison:
            return {}
        return {
            "analyzed": comparison.get("analyzed", 0),
            "eligible": comparison.get("eligible", 0),
            "viewpoint_count": comparison.get("viewpoint_count", 0),
            "partial": bool(comparison.get("partial")),
            "partial_reason": str(comparison.get("partial_reason", "")),
            "pending_bvids": list(comparison.get("pending_bvids", [])),
            "failed_bvids": list(comparison.get("failed_bvids", [])),
            "failure_reasons": dict(comparison.get("failure_reasons", {})),
        }

    def final_script(self, session_id: str) -> Dict[str, Any]:
        session = self.store.load(session_id)
        script_path = session["script"].get("reviewed_path", "")
        if not script_path:
            raise WorkbenchFlowError("请先完成写稿与审核")
        return self._script_view(session_id, script_path)
