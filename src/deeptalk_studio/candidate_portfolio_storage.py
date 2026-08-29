"""Fail-closed immutable JSON storage for Candidate Portfolio V1."""
from __future__ import annotations
import hashlib, json, os, re
from pathlib import Path
from typing import Any, Mapping

class CandidatePortfolioStorageError(ValueError): pass

def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def save_candidate_portfolio(value: Mapping[str, Any], root: Path) -> Path:
    _validate(value); identity = str(value["portfolio_id"])
    path = Path(root) / identity / "candidate-portfolio.json"; path.parent.mkdir(parents=True, exist_ok=True)
    try: fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc: raise CandidatePortfolioStorageError("不会覆盖已有工件") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as handle: handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+"\n")
    return path

def load_candidate_portfolio(path: Path) -> dict:
    source = Path(path)
    try:
        if source.is_symlink() or not source.is_file(): raise CandidatePortfolioStorageError("portfolio 路径不安全")
        value=json.loads(source.read_text(encoding="utf-8")); _validate(value)
    except (OSError,json.JSONDecodeError,CandidatePortfolioStorageError) as exc: raise CandidatePortfolioStorageError("portfolio 工件无效") from exc
    if source.parent.name != value["portfolio_id"] or source.name != "candidate-portfolio.json": raise CandidatePortfolioStorageError("portfolio 路径无效")
    return value

def _is_digest(value: Any) -> bool: return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None
def _identifier(value: Any) -> bool: return isinstance(value, str) and bool(value.strip())

def _validate(value: Any) -> None:
    if not isinstance(value, Mapping) or value.get("artifact_version") != "candidate-portfolio/1" or not re.fullmatch(r"CP-[0-9a-f]{24}", str(value.get("portfolio_id", ""))) or not _identifier(value.get("opportunity_id")):
        raise CandidatePortfolioStorageError("portfolio schema 无效")
    if "plugin_records" in value: _validate_phase2(value)
    else: _validate_phase1(value)
    payload=dict(value); digest=payload.pop("portfolio_digest",None)
    if digest != _digest(payload): raise CandidatePortfolioStorageError("portfolio digest 无效")

def _validate_phase1(value: Mapping[str, Any]) -> None:
    allowed={"artifact_version","portfolio_id","opportunity_id","proposal","suitability_raw","suitability_execution","generation_call","generation_raw","generation_execution","plugin_candidate","core_acceptance","portfolio_digest"}
    if set(value) - allowed or not isinstance(value.get("proposal"), Mapping) or value.get("generation_call") not in {"REQUESTED","NOT_REQUESTED"}: raise CandidatePortfolioStorageError("Phase 1 portfolio schema 无效")
    proposal=value["proposal"]
    if set(proposal) != {"proposal_id","suitability","reason"} or proposal.get("suitability") not in {"SUITABLE","ABSTAIN"}: raise CandidatePortfolioStorageError("proposal schema 无效")
    if not isinstance(value.get("suitability_raw"), Mapping): raise CandidatePortfolioStorageError("suitability raw 无效")
    if value["generation_call"] == "NOT_REQUESTED" and (proposal["suitability"] != "ABSTAIN" or value.get("plugin_candidate") is not None): raise CandidatePortfolioStorageError("Phase 1 no-call 无效")
    _validate_acceptance(value.get("core_acceptance"))

def _validate_phase2(value: Mapping[str, Any]) -> None:
    allowed={"artifact_version","portfolio_id","opportunity_id","policy_profile","policy_digest","config_digest","plugin_records","suggested_review_order","audit_records","portfolio_digest"}
    if set(value) != allowed or value.get("policy_profile") not in {"LEAN","STANDARD","RICH"} or not _is_digest(value.get("policy_digest")) or not _is_digest(value.get("config_digest")) or not isinstance(value.get("plugin_records"), list) or not isinstance(value.get("suggested_review_order"), list) or not isinstance(value.get("audit_records"), list): raise CandidatePortfolioStorageError("Phase 2 portfolio schema 无效")
    plugin_ids=set(); accepted_ids=[]
    for entry in value["plugin_records"]:
        if not isinstance(entry, Mapping): raise CandidatePortfolioStorageError("plugin record 无效")
        allowed_record={"plugin_id","resolved_plugin_version","enabled","suitability_execution","suitability_raw","generation_call","generation_no_call_reason","generation_execution","generation_raw","plugin_candidate","core_acceptance"}
        if set(entry) - allowed_record or not _identifier(entry.get("plugin_id")) or not isinstance(entry.get("enabled"), bool) or not _identifier(entry.get("resolved_plugin_version")) or not isinstance(entry.get("suitability_raw"), Mapping) or entry.get("generation_call") not in {"REQUESTED","NOT_REQUESTED"} or entry["plugin_id"] in plugin_ids: raise CandidatePortfolioStorageError("plugin record schema 无效")
        plugin_ids.add(entry["plugin_id"])
        if entry["generation_call"] == "NOT_REQUESTED":
            if not _identifier(entry.get("generation_no_call_reason")) or any(key in entry for key in ("generation_raw","generation_execution","plugin_candidate","core_acceptance")): raise CandidatePortfolioStorageError("no-call evidence 无效")
        elif "generation_raw" not in entry: raise CandidatePortfolioStorageError("generation evidence 缺失")
        _validate_acceptance(entry.get("core_acceptance"))
        candidate=entry.get("plugin_candidate")
        if candidate is not None:
            if not isinstance(candidate, Mapping) or not _identifier(candidate.get("candidate_id")): raise CandidatePortfolioStorageError("candidate schema 无效")
            if entry.get("core_acceptance", {}).get("status") == "ACCEPTED": accepted_ids.append(candidate["candidate_id"])
    if len(accepted_ids) != len(set(accepted_ids)) or value["suggested_review_order"] != accepted_ids: raise CandidatePortfolioStorageError("review order 或 candidate uniqueness 无效")
    if len(value["audit_records"]) != len(value["plugin_records"]): raise CandidatePortfolioStorageError("audit record 数量无效")

def _validate_acceptance(value: Any) -> None:
    if value is None: return
    if not isinstance(value, Mapping) or set(value) - {"status","problem","problems","core_locator","observed_sha256","observed_duration_ms"} or value.get("status") not in {"ACCEPTED","REJECTED"}: raise CandidatePortfolioStorageError("core acceptance 无效")
    if "problems" in value and (not isinstance(value["problems"], list) or any(not isinstance(p, Mapping) or set(p) != {"code","message"} or not _identifier(p.get("code")) or not _identifier(p.get("message")) for p in value["problems"])): raise CandidatePortfolioStorageError("Core problems 无效")
