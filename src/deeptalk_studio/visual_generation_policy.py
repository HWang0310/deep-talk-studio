"""Declarative candidate-generation-profile/1 loader and evaluator."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping, Sequence

class CandidateGenerationPolicyError(ValueError): pass

def normalize_candidate_generation_policy(value: Any) -> dict:
    if not isinstance(value, Mapping) or set(value) != {"profile_version","profiles","never_generate_suitability","notes"} or value.get("profile_version") != "candidate-generation-profile/1": raise CandidateGenerationPolicyError("candidate generation policy schema 无效")
    expected={"LEAN":{"generate_suitability":["SUITABLE"]},"STANDARD":{"generate_suitability":["SUITABLE"],"generate_borderline_when_no_suitable":True},"RICH":{"generate_suitability":["SUITABLE","BORDERLINE"]}}
    if value.get("profiles") != expected or value.get("never_generate_suitability") != ["ABSTAIN"] or not isinstance(value.get("notes"),str): raise CandidateGenerationPolicyError("candidate generation policy 必须精确编码 LEAN/STANDARD/RICH")
    return {"profile_version":value["profile_version"],"profiles":expected,"never_generate_suitability":["ABSTAIN"],"notes":value["notes"]}

def generation_policy_digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(normalize_candidate_generation_policy(value),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def load_candidate_generation_policy(path: Path) -> dict:
    try: return normalize_candidate_generation_policy(json.loads(Path(path).read_text(encoding="utf-8")))
    except (OSError,json.JSONDecodeError,CandidateGenerationPolicyError) as exc: raise CandidateGenerationPolicyError("candidate generation policy 无效") from exc

def policy_actions(profile: str, results: Sequence[Mapping[str, Any] | None], enabled: Sequence[bool], policy: Mapping[str, Any]) -> list[str]:
    normalize_candidate_generation_policy(policy)
    if profile not in {"LEAN","STANDARD","RICH"} or len(results)!=len(enabled): raise CandidateGenerationPolicyError("production profile 无效")
    suitable=any(ok and item and item.get("operation_status")=="COMPLETED" and item.get("suitability")=="SUITABLE" for item,ok in zip(results,enabled))
    values=[]
    for raw,ok in zip(results,enabled):
        status=raw.get("suitability") if ok and raw and raw.get("operation_status")=="COMPLETED" else None
        values.append("REQUESTED" if status=="SUITABLE" or (status=="BORDERLINE" and (profile=="RICH" or (profile=="STANDARD" and not suitable))) else "NOT_REQUESTED")
    return values
