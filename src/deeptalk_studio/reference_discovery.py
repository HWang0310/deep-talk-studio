"""Phase 1 reference-video discovery service (Issue #24, unreleased).

Turns a topic plus 0–5 optional Bilibili references into a validated,
machine-readable candidate set:

  user URLs (canonicalized + validated, kept first)
  → bounded multi-query anonymous search
  → deterministic topical filtering (anchor / trigram heuristics)
  → dedup by BVID
  → per-video metadata verification of view counts (bounded budget)
  → up to ``max_candidates`` entries, sorted by measured views

The artifact explicitly records coverage and limitations; it never claims
site-wide ranking, and search-snippet view counts are never presented as
verified numbers.
"""

import re
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple

BVID_RE = re.compile(r"^BV[0-9A-Za-z]{10}$")
VIDEO_PATH_RE = re.compile(r"/video/(BV[0-9A-Za-z]{10})")

REFERENCE_CANDIDATE_SET_VERSION = "1"
DEFAULT_MAX_CANDIDATES = 5
MAX_CANDIDATES_LIMIT = 20
MAX_QUERIES = 4
VERIFICATION_BUDGET = 15
EXCLUDED_PREVIEW_LIMIT = 8

GENERIC_SUFFIXES = ("事件", "视频", "完整版", "最新", "怎么回事", "盘点", "回顾", "解读")

SET_STATUSES = ("ok", "degraded", "blocked")
VIEW_COUNT_STATUSES = ("verified", "unverified", "unavailable")
VIEW_COUNT_SOURCES = ("per_video_api", "search_result", "none")
QUERY_STATUSES = ("ok", "blocked", "failed")
RELEVANCE_DECISIONS = ("relevant", "kept_user_supplied")
VIDEO_ERROR_REASONS = ("video_invalid", "video_unavailable", "video_restricted")
REJECTION_REASONS = (
    "short_link_unsupported",
    "not_bilibili_url",
    "malformed_reference",
    "duplicate_bvid",
    "exceeds_max_candidates",
) + VIDEO_ERROR_REASONS
EXCLUSION_REASONS = (
    "low_relevance",
    "missing_required_term",
    "excluded_term_match",
    "unavailable_video",
    "restricted_video",
    "invalid_video",
    "beyond_verification_budget",
)

CANDIDATE_KEYS = (
    "bvid", "url", "title", "uploader", "published_at", "view_count",
    "view_count_status", "view_count_source", "search_snippet_view_count",
    "duration_sec", "user_supplied", "found_via_queries", "relevance",
    "retrieval_note", "fetched_at",
)
RELEVANCE_KEYS = ("decision", "reason", "matched_terms", "anchor_hit", "trigram_hits", "score")
SEARCH_BLOCK_KEYS = (
    "queries", "page_limit", "raw_result_count", "deduplicated_count",
    "verification_budget", "verification_performed", "excluded_preview",
    "not_selected_relevant", "coverage_note",
)
QUERY_RECORD_KEYS = ("query", "page", "status", "http_status", "api_code",
                     "message", "result_count")
EXCLUDED_PREVIEW_KEYS = ("bvid", "title", "reason", "matched_terms")
PROVIDER_BLOCK_KEYS = ("name", "visitor_identity", "endpoints",
                       "request_interval_seconds", "max_retries", "timeout_seconds")
ARTIFACT_KEYS = (
    "artifact_version", "candidate_set_id", "generated_at", "topic", "provider",
    "query_plan", "user_supplied_urls", "candidates", "rejected_user_urls",
    "search", "status", "action_note", "limitations",
)

COVERAGE_NOTE = (
    "排序仅基于本轮已检索、判定相关且完成播放量核验的候选，"
    "是检索范围内的最高播放量，不代表 B 站站内整体排名。"
)

DEFAULT_LIMITATIONS = (
    "B 站 Web 搜索为非合同化公开接口，可能随时变更或限流；结果仅代表检索当时状态。",
    "播放量只是公开接口计数，不代表内容事实质量；参考视频不得作为事实来源。",
    "参考视频仅用于研究叙事结构与风格；不会下载、转写或重新分发站内视频。",
)


class ReferenceDiscoveryError(ValueError):
    """Raised for invalid inputs or artifacts (fail closed)."""


# ---------------------------------------------------------------------------
# canonicalization
# ---------------------------------------------------------------------------


def canonicalize_bilibili_reference(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(bvid, None)`` or ``(None, reason)`` for a user reference."""

    text = (raw or "").strip()
    if not text:
        return None, "malformed_reference"
    if BVID_RE.match(text):
        return text, None
    lowered = text.lower()
    url_like = (
        lowered.startswith("http://")
        or lowered.startswith("https://")
        or "bilibili.com" in lowered
        or "b23.tv" in lowered
    )
    if not url_like:
        return None, "malformed_reference"
    candidate = text if "://" in text else f"https://{text}"
    try:
        parsed = urllib.parse.urlparse(candidate)
    except ValueError:
        return None, "malformed_reference"
    host = (parsed.netloc or "").lower()
    if host == "b23.tv" or host.endswith(".b23.tv"):
        return None, "short_link_unsupported"
    if host == "bilibili.com" or host.endswith(".bilibili.com"):
        match = VIDEO_PATH_RE.search(parsed.path)
        if match:
            return match.group(1), None
        return None, "malformed_reference"
    return None, "not_bilibili_url"


def canonical_video_url(bvid: str) -> str:
    return f"https://www.bilibili.com/video/{bvid}"


# ---------------------------------------------------------------------------
# query plan & relevance heuristics (deterministic)
# ---------------------------------------------------------------------------


def normalize_topic(topic: str) -> str:
    return re.sub(r"\s+", " ", (topic or "").strip())


def topic_anchor(topic: str) -> str:
    text = re.sub(r"\s+", "", (topic or "").strip())
    if len(text) < 2:
        return text
    for suffix in GENERIC_SUFFIXES:
        if text.endswith(suffix) and len(text) - len(suffix) >= 3:
            return text[: -len(suffix)]
    return text


def build_query_plan(topic: str, aliases: Sequence[str] = ()) -> List[str]:
    queries: List[str] = []

    def add(value: str) -> None:
        cleaned = value.strip()
        if cleaned and cleaned not in queries:
            queries.append(cleaned)

    topic_norm = normalize_topic(topic)
    add(topic_norm)
    anchor = topic_anchor(topic_norm)
    if len(anchor) >= 4 and anchor not in queries:
        add(anchor)
    for alias in aliases:
        add(alias)
    return queries[:MAX_QUERIES]


def _ngram_normalize(text: str) -> str:
    return re.sub(r"[\W_]+", "", (text or "").lower(), flags=re.UNICODE)


def topic_trigrams(topic: str) -> set:
    normalized = _ngram_normalize(topic_anchor(topic))
    if len(normalized) < 3:
        return set()
    return {normalized[i:i + 3] for i in range(len(normalized) - 2)}


def assess_relevance(
    title: str,
    description: str,
    topic: str,
    required_terms: Sequence[str] = (),
    excluded_terms: Sequence[str] = (),
) -> Dict[str, object]:
    """Deterministic topical relevance: anchor hit or >=2 distinct trigram hits."""

    text = f"{title or ''} {description or ''}"
    for term in excluded_terms:
        if term and term in text:
            return {
                "decision": "excluded", "reason": "excluded_term_match",
                "matched_terms": [term], "anchor_hit": False, "trigram_hits": [], "score": 0,
            }
    for term in required_terms:
        if term and term not in text:
            return {
                "decision": "excluded", "reason": "missing_required_term",
                "matched_terms": [], "anchor_hit": False, "trigram_hits": [], "score": 0,
            }
    anchor = topic_anchor(topic)
    anchor_hit = bool(anchor) and len(anchor) >= 2 and anchor in text
    trigram_hits = sorted(gram for gram in topic_trigrams(topic) if gram in text)
    if anchor_hit:
        return {
            "decision": "relevant", "reason": "anchor_hit", "matched_terms": [anchor],
            "anchor_hit": True, "trigram_hits": trigram_hits[:5], "score": len(trigram_hits),
        }
    if len(trigram_hits) >= 2:
        return {
            "decision": "relevant", "reason": "trigram_hits",
            "matched_terms": trigram_hits[:5], "anchor_hit": False,
            "trigram_hits": trigram_hits[:5], "score": len(trigram_hits),
        }
    return {
        "decision": "excluded", "reason": "low_relevance",
        "matched_terms": trigram_hits[:5], "anchor_hit": False,
        "trigram_hits": trigram_hits[:5], "score": len(trigram_hits),
    }


# ---------------------------------------------------------------------------
# candidate set construction
# ---------------------------------------------------------------------------


def _now_iso(now) -> str:
    if isinstance(now, str):
        return now
    if isinstance(now, datetime):
        return now.astimezone(timezone.utc).isoformat() if now.tzinfo else now.replace(tzinfo=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def build_reference_candidate_set(
    topic: str,
    user_urls: Sequence[str] = (),
    *,
    provider,
    aliases: Sequence[str] = (),
    required_terms: Sequence[str] = (),
    excluded_terms: Sequence[str] = (),
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    verification_budget: int = VERIFICATION_BUDGET,
    now=None,
    candidate_set_id: str = "",
) -> Dict[str, object]:
    topic_norm = normalize_topic(topic)
    if not topic_norm:
        raise ReferenceDiscoveryError("主题不能为空")
    if not 1 <= int(max_candidates) <= MAX_CANDIDATES_LIMIT:
        raise ReferenceDiscoveryError(
            f"max_candidates 必须在 1 到 {MAX_CANDIDATES_LIMIT} 之间"
        )
    max_candidates = int(max_candidates)
    verification_budget = max(1, int(verification_budget))
    now_iso = _now_iso(now)

    # ---- 1. user references: canonicalize, dedupe, cap, validate metadata ----
    rejected: List[Dict[str, str]] = []
    user_bvids: List[str] = []
    for raw in user_urls:
        bvid, reason = canonicalize_bilibili_reference(raw)
        if bvid is None:
            rejected.append({"input": raw, "reason": reason})
            continue
        if bvid in user_bvids:
            rejected.append({"input": raw, "reason": "duplicate_bvid"})
            continue
        user_bvids.append(bvid)
    for bvid in user_bvids[max_candidates:]:
        rejected.append({"input": bvid, "reason": "exceeds_max_candidates"})
    user_bvids = user_bvids[:max_candidates]
    user_bvid_set = set(user_bvids)

    user_candidates: List[Dict[str, object]] = []
    metadata_non_ok = False
    verification_performed = 0

    def _base_candidate(bvid: str) -> Dict[str, object]:
        return {
            "bvid": bvid,
            "url": canonical_video_url(bvid),
            "title": None,
            "uploader": None,
            "published_at": None,
            "view_count": None,
            "view_count_status": "unverified",
            "view_count_source": "none",
            "search_snippet_view_count": None,
            "duration_sec": None,
            "user_supplied": True,
            "found_via_queries": ["user_supplied"],
            "relevance": None,
            "retrieval_note": None,
            "fetched_at": now_iso,
        }

    for bvid in user_bvids:
        outcome = provider.fetch_video_metadata(bvid)
        if outcome.status == "ok":
            verification_performed += 1
            candidate = _base_candidate(bvid)
            candidate.update({
                "title": outcome.title or None,
                "uploader": outcome.uploader or None,
                "published_at": outcome.published_at or None,
                "view_count": outcome.view_count if isinstance(outcome.view_count, int) else None,
                "view_count_status": "verified" if isinstance(outcome.view_count, int) else "unavailable",
                "view_count_source": "per_video_api" if isinstance(outcome.view_count, int) else "none",
                "duration_sec": outcome.duration_sec,
            })
            user_candidates.append(candidate)
        elif outcome.status in ("invalid", "unavailable", "restricted"):
            rejected.append({"input": bvid, "reason": f"video_{outcome.status}"})
        else:  # blocked | failed — keep the reference honestly unverified
            metadata_non_ok = True
            candidate = _base_candidate(bvid)
            candidate.update({
                "view_count_status": "unavailable",
                "retrieval_note": "metadata_fetch_blocked",
            })
            user_candidates.append(candidate)

    # ---- 2. bounded search ----
    queries = build_query_plan(topic_norm, aliases)
    search_records: List[Dict[str, object]] = []
    raw_items: Dict[str, Dict[str, object]] = {}
    raw_result_count = 0
    for query in queries:
        outcome = provider.search_videos(query, page=1)
        search_records.append({
            "query": query,
            "page": 1,
            "status": outcome.status,
            "http_status": outcome.http_status,
            "api_code": outcome.api_code,
            "message": (outcome.message or "")[:200],
            "result_count": len(outcome.items),
        })
        if outcome.status == "ok":
            raw_result_count += len(outcome.items)
            for item in outcome.items:
                entry = raw_items.setdefault(item.bvid, {"item": item, "queries": []})
                entry["queries"].append(query)

    # ---- 3. deterministic relevance over search results ----
    excluded_preview: List[Dict[str, object]] = []
    auto_relevant: List[Dict[str, object]] = []
    for bvid, entry in raw_items.items():
        item = entry["item"]
        relevance = assess_relevance(
            item.title, item.description, topic_norm, required_terms, excluded_terms
        )
        if bvid in user_bvid_set:
            target = next(c for c in user_candidates if c["bvid"] == bvid)
            target["found_via_queries"].extend(entry["queries"])
            if relevance["decision"] != "relevant":
                target["relevance"] = dict(
                    relevance, decision="kept_user_supplied", reason="kept_user_supplied"
                )
            else:
                target["relevance"] = relevance
            continue
        if relevance["decision"] != "relevant":
            excluded_preview.append({
                "bvid": bvid, "title": (item.title or "")[:60],
                "reason": relevance["reason"], "matched_terms": relevance["matched_terms"][:3],
            })
            continue
        auto_relevant.append({
            "bvid": bvid, "item": item, "relevance": relevance,
            "queries": list(entry["queries"]),
        })

    # user candidates never assessed through search keep a recorded decision
    for candidate in user_candidates:
        if candidate["relevance"] is None:
            relevance = assess_relevance(
                str(candidate["title"] or ""), "", topic_norm, required_terms, excluded_terms
            )
            if relevance["decision"] != "relevant":
                candidate["relevance"] = dict(
                    relevance, decision="kept_user_supplied", reason="kept_user_supplied"
                )
            else:
                candidate["relevance"] = relevance

    # ---- 4. bounded per-video verification ----
    auto_relevant.sort(
        key=lambda entry: (-(entry["item"].snippet_view_count or 0), entry["bvid"])
    )
    beyond_budget = auto_relevant[verification_budget:]
    for entry in beyond_budget:
        excluded_preview.append({
            "bvid": entry["bvid"], "title": (entry["item"].title or "")[:60],
            "reason": "beyond_verification_budget", "matched_terms": [],
        })
    verified_auto: List[Dict[str, object]] = []
    for entry in auto_relevant[:verification_budget]:
        item = entry["item"]
        outcome = provider.fetch_video_metadata(item.bvid)
        candidate: Dict[str, object] = {
            "bvid": item.bvid,
            "url": canonical_video_url(item.bvid),
            "title": item.title or None,
            "uploader": item.uploader or None,
            "published_at": item.published_at or None,
            "view_count": None,
            "view_count_status": "unverified",
            "view_count_source": "none",
            "search_snippet_view_count": item.snippet_view_count,
            "duration_sec": None,
            "user_supplied": False,
            "found_via_queries": list(entry["queries"]),
            "relevance": entry["relevance"],
            "retrieval_note": None,
            "fetched_at": now_iso,
        }
        if outcome.status == "ok":
            verification_performed += 1
            verified = isinstance(outcome.view_count, int)
            candidate.update({
                "title": outcome.title or item.title or None,
                "uploader": outcome.uploader or item.uploader or None,
                "published_at": outcome.published_at or item.published_at or None,
                "view_count": outcome.view_count if verified else None,
                "view_count_status": "verified" if verified else "unavailable",
                "view_count_source": "per_video_api" if verified else "none",
                "duration_sec": outcome.duration_sec,
            })
            verified_auto.append(candidate)
        elif outcome.status in ("invalid", "unavailable", "restricted"):
            excluded_preview.append({
                "bvid": item.bvid, "title": (item.title or "")[:60],
                "reason": f"{outcome.status}_video", "matched_terms": [],
            })
        else:  # blocked | failed — keep, but never copy snippet views as fact
            metadata_non_ok = True
            verified_auto.append(candidate)

    # ---- 5. selection: user first, then verified views desc ----
    verified_auto.sort(key=lambda c: (
        0 if c["view_count_status"] == "verified" else 1,
        -(c["view_count"] or 0),
        -(c["search_snippet_view_count"] or 0),
        c["bvid"],
    ))
    selected = user_candidates + verified_auto
    not_selected_relevant = max(0, len(selected) - max_candidates)
    selected = selected[:max_candidates]
    for candidate in selected:
        candidate["relevance"] = candidate["relevance"] or {
            "decision": "kept_user_supplied", "reason": "kept_user_supplied",
            "matched_terms": [], "anchor_hit": False, "trigram_hits": [], "score": 0,
        }

    # ---- 6. status & guidance ----
    query_ok_any = any(r["status"] == "ok" for r in search_records)
    query_non_ok = any(r["status"] != "ok" for r in search_records)
    if not query_ok_any:
        status = "degraded" if user_candidates else "blocked"
    elif query_non_ok or metadata_non_ok:
        status = "degraded"
    else:
        status = "ok"

    if status == "blocked":
        action_note = (
            "B 站搜索当前不可用（平台限制或网络异常）。可稍后重试，"
            "或直接通过 --url 手动提供 B 站链接完成候选构建。"
        )
    elif len(selected) < max_candidates:
        action_note = (
            f"仅找到 {len(selected)} 条合格候选，未强行凑数；"
            "可改用更具体的主题词、增加查询别名，或手动补充链接。"
        )
    else:
        action_note = f"已生成 {len(selected)} 条参考候选。"

    artifact = {
        "artifact_version": REFERENCE_CANDIDATE_SET_VERSION,
        "candidate_set_id": candidate_set_id or f"REF-{uuid.uuid4().hex[:12]}",
        "generated_at": now_iso,
        "topic": topic_norm,
        "provider": {
            "name": "bilibili_web_search",
            "visitor_identity": getattr(provider, "visitor_identity_mode", "disabled"),
            "endpoints": {
                "search": "api.bilibili.com/x/web-interface/search/type",
                "video": "api.bilibili.com/x/web-interface/view",
            },
            "request_interval_seconds": getattr(provider, "request_interval", None),
            "max_retries": getattr(provider, "max_retries", None),
            "timeout_seconds": getattr(provider, "timeout_seconds", None),
        },
        "query_plan": queries,
        "user_supplied_urls": list(user_urls),
        "candidates": selected,
        "rejected_user_urls": rejected,
        "search": {
            "queries": search_records,
            "page_limit": 1,
            "raw_result_count": raw_result_count,
            "deduplicated_count": len(raw_items),
            "verification_budget": verification_budget,
            "verification_performed": verification_performed,
            "excluded_preview": excluded_preview[:EXCLUDED_PREVIEW_LIMIT],
            "not_selected_relevant": not_selected_relevant,
            "coverage_note": COVERAGE_NOTE,
        },
        "status": status,
        "action_note": action_note,
        "limitations": list(DEFAULT_LIMITATIONS),
    }
    validate_reference_candidate_set(artifact)
    return artifact


# ---------------------------------------------------------------------------
# artifact validation (fail closed)
# ---------------------------------------------------------------------------


def _fail(message: str) -> None:
    raise ReferenceDiscoveryError(message)


def _check_keys(payload: Dict[str, object], keys: Tuple[str, ...], label: str) -> None:
    if not isinstance(payload, dict) or set(payload) != set(keys):
        _fail(f"{label} 字段不完整或包含未知字段")


def validate_reference_candidate_set(artifact: Dict[str, object]) -> None:
    if not isinstance(artifact, dict):
        _fail("候选集必须是 JSON 对象")
    _check_keys(artifact, ARTIFACT_KEYS, "候选集")
    if artifact["artifact_version"] != REFERENCE_CANDIDATE_SET_VERSION:
        _fail("unsupported artifact_version")
    if not isinstance(artifact["candidate_set_id"], str) or not artifact["candidate_set_id"].startswith("REF-"):
        _fail("candidate_set_id 无效")
    if artifact["status"] not in SET_STATUSES:
        _fail("候选集 status 无效")
    if not isinstance(artifact["topic"], str) or not artifact["topic"]:
        _fail("topic 无效")
    if not isinstance(artifact["action_note"], str):
        _fail("action_note 无效")
    if not isinstance(artifact["limitations"], list) or not all(
        isinstance(item, str) and item for item in artifact["limitations"]
    ):
        _fail("limitations 无效")
    if not isinstance(artifact["query_plan"], list) or not artifact["query_plan"] or not all(
        isinstance(q, str) and q for q in artifact["query_plan"]
    ):
        _fail("query_plan 无效")
    if not isinstance(artifact["user_supplied_urls"], list):
        _fail("user_supplied_urls 无效")

    provider_block = artifact["provider"]
    _check_keys(provider_block, PROVIDER_BLOCK_KEYS, "provider")
    if provider_block["name"] != "bilibili_web_search":
        _fail("provider.name 无效")
    if provider_block["visitor_identity"] not in ("disabled", "anonymous", "preset"):
        _fail("provider.visitor_identity 无效")
    if not isinstance(provider_block["endpoints"], dict):
        _fail("provider.endpoints 无效")

    if not isinstance(artifact["candidates"], list) or len(artifact["candidates"]) > MAX_CANDIDATES_LIMIT * 4:
        _fail("candidates 无效")
    seen_auto = False
    query_plan = list(artifact["query_plan"])
    for candidate in artifact["candidates"]:
        _check_keys(candidate, CANDIDATE_KEYS, "candidate")
        bvid = candidate["bvid"]
        if not isinstance(bvid, str) or not BVID_RE.match(bvid):
            _fail("candidate.bvid 无效")
        if candidate["url"] != canonical_video_url(bvid):
            _fail("candidate.url 与 bvid 不一致")
        if candidate["view_count_status"] not in VIEW_COUNT_STATUSES:
            _fail("candidate.view_count_status 无效")
        if candidate["view_count_source"] not in VIEW_COUNT_SOURCES:
            _fail("candidate.view_count_source 无效")
        if candidate["view_count_status"] == "verified":
            if not isinstance(candidate["view_count"], int) or candidate["view_count"] < 0:
                _fail("verified 播放量必须是整数")
            if candidate["view_count_source"] != "per_video_api":
                _fail("verified 播放量必须来自 per_video_api")
        elif candidate["view_count"] is not None:
            _fail("非 verified 候选不得给出已核验播放量")
        if candidate["title"] is None and candidate["retrieval_note"] != "metadata_fetch_blocked":
            _fail("缺少标题的候选必须带 metadata_fetch_blocked 说明")
        if not isinstance(candidate["user_supplied"], bool):
            _fail("candidate.user_supplied 必须是布尔值")
        if not isinstance(candidate["found_via_queries"], list) or not candidate["found_via_queries"]:
            _fail("candidate.found_via_queries 无效")
        if candidate["user_supplied"]:
            if seen_auto:
                _fail("用户候选必须排在自动候选之前")
            if candidate["found_via_queries"][0] != "user_supplied":
                _fail("用户候选的 found_via_queries 必须以 user_supplied 开头")
        else:
            seen_auto = True
            if not set(candidate["found_via_queries"]) <= set(query_plan):
                _fail("自动候选的 found_via_queries 超出 query_plan")
        if not isinstance(candidate["search_snippet_view_count"], (int, type(None))):
            _fail("search_snippet_view_count 无效")
        if not isinstance(candidate["duration_sec"], (int, type(None))):
            _fail("duration_sec 无效")
        relevance = candidate["relevance"]
        _check_keys(relevance, RELEVANCE_KEYS, "candidate.relevance")
        if relevance["decision"] not in RELEVANCE_DECISIONS:
            _fail("candidate.relevance.decision 无效")
        if not isinstance(relevance["matched_terms"], list):
            _fail("candidate.relevance.matched_terms 无效")

    if not isinstance(artifact["rejected_user_urls"], list):
        _fail("rejected_user_urls 无效")
    for entry in artifact["rejected_user_urls"]:
        _check_keys(entry, ("input", "reason"), "rejected_user_urls 项")
        if entry["reason"] not in REJECTION_REASONS:
            _fail("rejected_user_urls.reason 无效")

    search_block = artifact["search"]
    _check_keys(search_block, SEARCH_BLOCK_KEYS, "search")
    for record in search_block["queries"]:
        _check_keys(record, QUERY_RECORD_KEYS, "search.queries 项")
        if record["status"] not in QUERY_STATUSES:
            _fail("search.queries.status 无效")
        if not isinstance(record["result_count"], int) or record["result_count"] < 0:
            _fail("search.queries.result_count 无效")
    for key in ("raw_result_count", "deduplicated_count", "verification_budget",
                "verification_performed", "not_selected_relevant"):
        if not isinstance(search_block[key], int) or search_block[key] < 0:
            _fail(f"search.{key} 无效")
    for entry in search_block["excluded_preview"]:
        _check_keys(entry, EXCLUDED_PREVIEW_KEYS, "search.excluded_preview 项")
        if entry["reason"] not in EXCLUSION_REASONS:
            _fail("search.excluded_preview.reason 无效")
    if not isinstance(search_block["coverage_note"], str) or not search_block["coverage_note"]:
        _fail("search.coverage_note 无效")
