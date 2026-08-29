"""Minimal machine-only Candidate Portfolio with separate raw and Core states."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping, Sequence


def build_candidate_portfolio(opportunity: Mapping[str, Any], suitability: Mapping[str, Any], generation: Mapping[str, Any] | None, *, core_status: str | None = None, core_problem: Mapping[str, Any] | None = None) -> dict:
    if not opportunity.get("opportunity_id") or suitability.get("operation_status") != "COMPLETED" or not suitability.get("proposal_id"):
        raise ValueError("invalid opportunity or suitability")
    proposal = {key: copy.deepcopy(suitability[key]) for key in ("proposal_id", "suitability", "reason")}
    base = {"opportunity_id": opportunity["opportunity_id"], "proposal_id": proposal["proposal_id"]}
    artifact = {"artifact_version": "candidate-portfolio/1", "portfolio_id": "CP-" + _digest(base)[:24], "opportunity_id": opportunity["opportunity_id"], "proposal": proposal, "suitability_raw": copy.deepcopy(dict(suitability)), "generation_call": "NOT_REQUESTED" if proposal["suitability"] == "ABSTAIN" else "REQUESTED", "plugin_candidate": None, "core_acceptance": None}
    if proposal["suitability"] == "ABSTAIN": artifact["portfolio_digest"] = _digest(artifact); return artifact
    if generation is None: raise ValueError("generation required for non-ABSTAIN")
    artifact["generation_raw"] = copy.deepcopy(dict(generation))
    candidate = generation.get("candidate")
    if candidate is not None:
        artifact["plugin_candidate"] = copy.deepcopy(dict(candidate))
        status = core_status or ("ACCEPTED" if candidate.get("candidate_status") == "READY" else "REJECTED")
        if status not in {"ACCEPTED", "REJECTED"}: raise ValueError("invalid core status")
        artifact["core_acceptance"] = {"status": status, **({"problem": copy.deepcopy(dict(core_problem))} if core_problem else {})}
    artifact["portfolio_digest"] = _digest(artifact)
    return artifact


def ready_candidates(portfolios: Sequence[Mapping[str, Any]]) -> list[dict]:
    return [copy.deepcopy(dict(item["plugin_candidate"])) for item in portfolios if item.get("plugin_candidate", {}).get("candidate_status") == "READY" and item.get("core_acceptance", {}).get("status") == "ACCEPTED"]


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
