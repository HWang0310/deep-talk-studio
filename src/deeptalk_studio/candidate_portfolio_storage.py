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
    if not isinstance(value, Mapping) or value.get("artifact_version") != "candidate-portfolio/1" or not re.fullmatch(r"CP-[0-9a-f]{24}", str(value.get("portfolio_id", ""))):
        raise CandidatePortfolioStorageError("portfolio schema 无效")
    if "opportunities" in value: _validate_phase2(value)
    else:
        if not _identifier(value.get("opportunity_id")): raise CandidatePortfolioStorageError("portfolio schema 无效")
        _validate_phase1(value)
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
    allowed={"artifact_version","portfolio_id","visual_opportunity_plan_digest","plugin_config_digest","generation_policy_digest","production_profile","opportunities","audit_records","portfolio_digest"}
    if set(value) != allowed or not all(_is_digest(value.get(k)) for k in ("visual_opportunity_plan_digest","plugin_config_digest","generation_policy_digest")) or value.get("production_profile") not in {"LEAN","STANDARD","RICH"} or not isinstance(value.get("opportunities"),list) or not isinstance(value.get("audit_records"),list): raise CandidatePortfolioStorageError("Phase 2 portfolio schema 无效")
    seen_opportunities=set(); candidate_ids=[]
    for block in value["opportunities"]:
        if not isinstance(block,Mapping) or set(block)!={"opportunity","proposals","policy_records","generation_records","candidates"} or not isinstance(block["opportunity"],Mapping) or not _identifier(block["opportunity"].get("opportunity_id")) or block["opportunity"]["opportunity_id"] in seen_opportunities or not all(isinstance(block[k],list) for k in ("proposals","policy_records","generation_records","candidates")): raise CandidatePortfolioStorageError("opportunity portfolio schema 无效")
        seen_opportunities.add(block["opportunity"]["opportunity_id"]); policy={item.get("plugin_id"):item for item in block["policy_records"] if isinstance(item,Mapping)}
        if len(policy)!=len(block["policy_records"]): raise CandidatePortfolioStorageError("policy record 无效")
        for proposal in block["proposals"]:
            if not isinstance(proposal,Mapping) or set(proposal)!={"plugin_id","resolved_plugin_version","suitability_execution","suitability_raw"} or not _identifier(proposal.get("plugin_id")): raise CandidatePortfolioStorageError("proposal record 无效")
            raw=proposal["suitability_raw"]
            _validate_execution(proposal["suitability_execution"])
            if raw is not None:
                from .visual_asset_plugin_contract import validate_suitability_response
                try: validate_suitability_response(raw)
                except Exception as exc: raise CandidatePortfolioStorageError("raw suitability 无效") from exc
        for record in block["generation_records"]:
            if not isinstance(record,Mapping) or set(record)!={"plugin_id","generation_execution","generation_raw"}: raise CandidatePortfolioStorageError("generation record 无效")
            if record["generation_raw"] is not None:
                _validate_execution(record["generation_execution"])
                from .visual_asset_plugin_contract import validate_generation_result
                try: validate_generation_result(record["generation_raw"],block["opportunity"])
                except Exception as exc: raise CandidatePortfolioStorageError("raw generation 无效") from exc
        for candidate in block["candidates"]:
            if not isinstance(candidate,Mapping) or set(candidate)-{"plugin_id","proposal_id","suitability","plugin_candidate","core_acceptance","suggested_review_order"} or not isinstance(candidate.get("plugin_candidate"),Mapping) or not _identifier(candidate["plugin_candidate"].get("candidate_id")): raise CandidatePortfolioStorageError("candidate record 无效")
            candidate_ids.append(candidate["plugin_candidate"]["candidate_id"]); _validate_acceptance(candidate.get("core_acceptance"))
    if len(candidate_ids)!=len(set(candidate_ids)): raise CandidatePortfolioStorageError("candidate_id 不可重复")
    if len(value["audit_records"]) < 1 or any(not isinstance(item,Mapping) or set(item)!={"opportunity_id","plugin_id","operation","execution","raw_response","request_snapshot"} or item.get("operation") not in {"suitability","generation"} for item in value["audit_records"]): raise CandidatePortfolioStorageError("audit records 无效")
    for audit in value["audit_records"]: _validate_execution(audit["execution"])

def _validate_execution(value: Any) -> None:
    if value is None: return
    fields={"plugin_id","resolved_plugin_version","config_digest","request_id","operation","job_locator","request_locator","result_locator","stdout_locator","stderr_locator","output_locator","status","retryable","reason","started_at","finished_at","runtime_duration_ms"}
    if not isinstance(value,Mapping) or set(value)!=fields or not _identifier(value.get("plugin_id")) or not isinstance(value.get("resolved_plugin_version"),str) or not _is_digest(value.get("config_digest")) or not _identifier(value.get("request_id")) or value.get("operation") not in {"suitability","generation"} or value.get("status") not in {"COMPLETED","FAILED"} or not isinstance(value.get("retryable"),bool) or not _identifier(value.get("reason")) or not isinstance(value.get("runtime_duration_ms"),int) or value["runtime_duration_ms"]<0 or not all(isinstance(value.get(k),str) and value[k] for k in ("job_locator","request_locator","result_locator","stdout_locator","stderr_locator","output_locator","started_at","finished_at")): raise CandidatePortfolioStorageError("execution evidence 无效")

def _validate_acceptance(value: Any) -> None:
    if value is None: return
    if not isinstance(value, Mapping) or set(value) - {"status","problem","problems","core_locator","observed_sha256","observed_duration_ms"} or value.get("status") not in {"ACCEPTED","REJECTED"}: raise CandidatePortfolioStorageError("core acceptance 无效")
    if "problems" in value and (not isinstance(value["problems"], list) or any(not isinstance(p, Mapping) or set(p) != {"code","message"} or not _identifier(p.get("code")) or not _identifier(p.get("message")) for p in value["problems"])): raise CandidatePortfolioStorageError("Core problems 无效")
