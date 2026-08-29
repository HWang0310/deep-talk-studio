"""Minimal machine-only Candidate Portfolio with separate raw and Core states."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping, Sequence
from .visual_asset_plugin_contract import validate_generation_result, validate_suitability_response


def build_candidate_portfolio(opportunity: Mapping[str, Any], suitability: Mapping[str, Any], generation: Mapping[str, Any] | None, *, core_status: str | None = None, core_problem: Mapping[str, Any] | None = None) -> dict:
    suitability_execution, suitability_raw = _operation(suitability)
    try: validate_suitability_response(suitability_raw)
    except Exception as exc: raise ValueError("invalid suitability Contract response") from exc
    if not opportunity.get("opportunity_id") or suitability_raw.get("operation_status") != "COMPLETED" or suitability_raw.get("suitability") not in {"SUITABLE", "ABSTAIN"} or suitability_raw.get("opportunity_id") != opportunity["opportunity_id"]:
        raise ValueError("invalid opportunity or suitability")
    proposal = {key: copy.deepcopy(suitability_raw[key]) for key in ("proposal_id", "suitability", "reason")}
    base = {"opportunity_id": opportunity["opportunity_id"], "proposal_id": proposal["proposal_id"]}
    artifact = {"artifact_version": "candidate-portfolio/1", "portfolio_id": "CP-" + _digest(base)[:24], "opportunity_id": opportunity["opportunity_id"], "proposal": proposal, "suitability_raw": copy.deepcopy(dict(suitability_raw)), "suitability_execution": suitability_execution, "generation_call": "NOT_REQUESTED" if proposal["suitability"] == "ABSTAIN" else "REQUESTED", "plugin_candidate": None, "core_acceptance": None}
    if proposal["suitability"] == "ABSTAIN": artifact["portfolio_digest"] = _digest(artifact); return artifact
    if generation is None: raise ValueError("generation required for non-ABSTAIN")
    generation_execution, generation_raw = _operation(generation)
    try: validate_generation_result(generation_raw, opportunity)
    except Exception as exc: raise ValueError("invalid generation Contract result") from exc
    if any(generation_raw.get(key) != suitability_raw.get(key) for key in ("opportunity_id", "proposal_id", "plugin_id", "plugin_version")):
        raise ValueError("generation lineage mismatch")
    artifact["generation_raw"] = copy.deepcopy(dict(generation_raw)); artifact["generation_execution"] = generation_execution
    candidate = generation_raw.get("candidate")
    if candidate is not None:
        artifact["plugin_candidate"] = copy.deepcopy(dict(candidate))
        if core_status is None:
            raise ValueError("core_status 必须由 Core 显式决定")
        status = core_status
        if status not in {"ACCEPTED", "REJECTED"}: raise ValueError("invalid core status")
        artifact["core_acceptance"] = {"status": status, **({"problem": copy.deepcopy(dict(core_problem))} if core_problem else {})}
    artifact["portfolio_digest"] = _digest(artifact)
    return artifact


def ready_candidates(portfolios: Sequence[Mapping[str, Any]]) -> list[dict]:
    return [copy.deepcopy(dict(item["plugin_candidate"])) for item in portfolios if item.get("plugin_candidate", {}).get("candidate_status") == "READY" and item.get("core_acceptance", {}).get("status") == "ACCEPTED"]


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

def _operation(value: Mapping[str, Any]) -> tuple[dict | None, Mapping[str, Any]]:
    if "raw_response" in value:
        return copy.deepcopy(value.get("execution")), value["raw_response"]
    return None, value
