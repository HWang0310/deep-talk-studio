"""Immutable, non-exclusive Candidate Portfolio Core records."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from .visual_asset_plugin_contract import validate_generation_result, validate_suitability_response


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _operation(value: Mapping[str, Any]) -> tuple[dict | None, Mapping[str, Any] | None]:
    if "raw_response" in value:
        raw = value.get("raw_response")
        return copy.deepcopy(value.get("execution")), copy.deepcopy(raw) if isinstance(raw, Mapping) else None
    return None, copy.deepcopy(dict(value))


def apply_generation_policy(profile: str, suitability_results: Sequence[Mapping[str, Any]], *, enabled: Sequence[bool] | None = None) -> list[str]:
    """Return a call/no-call action per independent plugin, without ranking."""
    if profile not in {"LEAN", "STANDARD", "RICH"}:
        raise ValueError("unknown candidate generation profile")
    enabled = list(enabled) if enabled is not None else [True] * len(suitability_results)
    if len(enabled) != len(suitability_results):
        raise ValueError("enabled length mismatch")
    completed_suitable = any(bool(ok) and item.get("operation_status") == "COMPLETED" and item.get("suitability") == "SUITABLE" for item, ok in zip(suitability_results, enabled))
    return ["REQUESTED" if (ok and item.get("operation_status") == "COMPLETED" and (item.get("suitability") == "SUITABLE" or (profile == "RICH" and item.get("suitability") == "BORDERLINE") or (profile == "STANDARD" and not completed_suitable and item.get("suitability") == "BORDERLINE"))) else "NOT_REQUESTED" for item, ok in zip(suitability_results, enabled)]


def _policy_reason(profile: str, raw: Mapping[str, Any], enabled: bool) -> str:
    if not enabled: return "PLUGIN_DISABLED"
    if raw.get("operation_status") != "COMPLETED": return str(raw.get("operation_status", "NO_RAW_RESULT"))
    if raw.get("suitability") == "ABSTAIN": return "ABSTAIN"
    if raw.get("suitability") == "BORDERLINE" and profile in {"LEAN", "STANDARD"}: return "BORDERLINE_POLICY_NO_CALL"
    return "POLICY_NO_CALL"


def _problem(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def _resolve_artifact(uri: Any, output_root: Path) -> tuple[Path | None, str | None]:
    if not isinstance(uri, str) or not uri.startswith("local-runner://"):
        return None, None
    relative = uri[len("local-runner://"):]
    if not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        return None, None
    root = Path(output_root).resolve(strict=True)
    candidate = (root / relative).resolve(strict=False)
    try: candidate.relative_to(root)
    except ValueError: return None, None
    if candidate.is_symlink(): return None, None
    return candidate, "local-plugin-artifact://" + hashlib.sha256(uri.encode("utf-8")).hexdigest()


def _ffprobe_duration_ms(path: Path) -> int | None:
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, timeout=5, check=True)
        return int(round(float(result.stdout.strip()) * 1000))
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def core_accept_candidate(opportunity: Mapping[str, Any], suitability_raw: Mapping[str, Any], generation_raw: Mapping[str, Any], plugin: Mapping[str, Any], output_root: Path, *, seen_candidate_ids: set[str] | None = None, suitability_execution: Mapping[str, Any] | None = None, generation_execution: Mapping[str, Any] | None = None) -> dict:
    """Perform ordered Core QA while preserving the raw plugin result untouched."""
    problems: list[dict] = []
    try: validate_suitability_response(suitability_raw)
    except Exception: problems.append(_problem("INVALID_SUITABILITY_CONTRACT", "suitability response is not Contract V1 valid"))
    try: validate_generation_result(generation_raw, opportunity)
    except Exception: problems.append(_problem("INVALID_GENERATION_CONTRACT", "generation response is not Contract V1 valid"))
    for execution, raw, label in ((suitability_execution, suitability_raw, "suitability"), (generation_execution, generation_raw, "generation")):
        if execution is not None and execution.get("request_id") != raw.get("request_id"):
            problems.append(_problem("REQUEST_RESPONSE_CORRELATION_MISMATCH", label + " request id differs from Core evidence"))
    candidate = generation_raw.get("candidate") if isinstance(generation_raw, Mapping) else None
    if not isinstance(candidate, Mapping):
        problems.append(_problem("MISSING_CANDIDATE", "completed result has no candidate")); candidate = {}
    if suitability_raw.get("opportunity_id") != opportunity.get("opportunity_id") or generation_raw.get("opportunity_id") != opportunity.get("opportunity_id"): problems.append(_problem("OPPORTUNITY_LINEAGE_MISMATCH", "opportunity lineage differs"))
    if generation_raw.get("proposal_id") != suitability_raw.get("proposal_id"): problems.append(_problem("PROPOSAL_LINEAGE_MISMATCH", "proposal lineage differs"))
    if generation_raw.get("plugin_id") != plugin.get("plugin_id") or suitability_raw.get("plugin_id") != plugin.get("plugin_id"): problems.append(_problem("PLUGIN_ID_MISMATCH", "configured plugin id differs"))
    if generation_raw.get("plugin_version") != plugin.get("plugin_version") or suitability_raw.get("plugin_version") != plugin.get("plugin_version"): problems.append(_problem("PLUGIN_VERSION_MISMATCH", "resolved plugin version differs"))
    if candidate.get("candidate_id") in (seen_candidate_ids or set()): problems.append(_problem("DUPLICATE_CANDIDATE_ID", "candidate id is already present in this portfolio"))
    if candidate.get("candidate_status") != "READY": problems.append(_problem("PLUGIN_QA_NOT_READY", "raw plugin candidate is not READY"))
    placement, window = candidate.get("suggested_placement", {}), opportunity.get("a_roll_window", {})
    if not isinstance(placement, Mapping) or placement.get("start_ms", -1) < window.get("start_ms", 0) or placement.get("end_ms", -1) > window.get("end_ms", -1): problems.append(_problem("PLACEMENT_OUTSIDE_OPPORTUNITY", "candidate placement escapes opportunity"))
    primary = next((item for item in candidate.get("artifacts", []) if isinstance(item, Mapping) and item.get("role") == "PRIMARY_MEDIA"), None)
    if not primary: problems.append(_problem("MISSING_PRIMARY_MEDIA", "READY candidate lacks PRIMARY_MEDIA")); primary = {}
    if primary.get("media_type") != "video/mp4": problems.append(_problem("PRIMARY_MEDIA_TYPE_INVALID", "PRIMARY_MEDIA must be video/mp4"))
    path, locator = _resolve_artifact(primary.get("uri"), Path(output_root))
    if path is None: problems.append(_problem("ARTIFACT_URI_UNSAFE", "raw artifact URI cannot resolve under Core output root"))
    elif not path.is_file(): problems.append(_problem("ARTIFACT_FILE_MISSING", "resolved artifact does not exist"))
    else:
        observed_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if primary.get("sha256") != observed_sha: problems.append(_problem("SHA256_MISMATCH", "artifact SHA-256 differs"))
        observed_duration = _ffprobe_duration_ms(path)
        if observed_duration is None: problems.append(_problem("FFPROBE_UNREADABLE", "ffprobe cannot read artifact"))
        elif abs(observed_duration - int(candidate.get("duration_ms", 0))) > 100: problems.append(_problem("DURATION_MISMATCH", "observed duration exceeds 100 ms tolerance"))
        if observed_duration is not None and primary.get("duration_ms") and abs(observed_duration - int(primary["duration_ms"])) > 100: problems.append(_problem("ARTIFACT_DURATION_MISMATCH", "primary artifact duration differs"))
    if candidate.get("factual_context", opportunity.get("factual_context")) != opportunity.get("factual_context"): problems.append(_problem("FACTUAL_CONTEXT_LINEAGE_MISMATCH", "factual context differs from opportunity"))
    provenance = candidate.get("provenance")
    if not isinstance(provenance, Mapping) or provenance.get("origin") != "plugin-generated": problems.append(_problem("PLUGIN_PROVENANCE_INVALID", "candidate must declare plugin-generated provenance"))
    if isinstance(provenance, Mapping) and provenance.get("generated_as") not in {"illustration", "synthetic", "documentary-recreation"}: problems.append(_problem("GENERATED_AS_REAL_MATERIAL", "generated candidate cannot claim real material"))
    result = {"status": "ACCEPTED" if not problems else "REJECTED", "problems": problems}
    if locator: result["core_locator"] = locator
    if path is not None and path.is_file():
        result["observed_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest(); duration = _ffprobe_duration_ms(path)
        if duration is not None: result["observed_duration_ms"] = duration
    return result


def build_multi_candidate_portfolio(opportunity: Mapping[str, Any], records: Sequence[Mapping[str, Any]], *, profile: str, output_root: Path, config: Mapping[str, Any] | None = None) -> dict:
    raw_suitability, enabled, prepared = [], [], []
    for record in records:
        execution, raw = _operation(record["suitability"]); raw = raw or {"operation_status": "FAILED", "problem": {"code": "NO_RAW_RESULT", "message": "no raw response"}}
        prepared.append((record, execution, raw)); raw_suitability.append(raw); enabled.append(bool(record["plugin"].get("enabled", False)))
    calls = apply_generation_policy(profile, raw_suitability, enabled=enabled)
    plugin_records, seen = [], set()
    for (record, suitability_execution, raw), generation_call in zip(prepared, calls):
        plugin_cfg = record["plugin"]; entry = {"plugin_id": plugin_cfg["plugin_id"], "resolved_plugin_version": plugin_cfg.get("plugin_version"), "enabled": bool(plugin_cfg.get("enabled", False)), "suitability_execution": suitability_execution, "suitability_raw": copy.deepcopy(raw), "generation_call": generation_call}
        if generation_call == "NOT_REQUESTED": entry["generation_no_call_reason"] = _policy_reason(profile, raw, bool(plugin_cfg.get("enabled", False)))
        elif "generation" not in record: entry.update({"generation_raw": None, "generation_execution": {"status": "FAILED", "reason": "GENERATION_NOT_RUN"}})
        else:
            generation_execution, generation_raw = _operation(record["generation"]); entry["generation_execution"] = generation_execution; entry["generation_raw"] = generation_raw
            if isinstance(generation_raw, Mapping) and isinstance(generation_raw.get("candidate"), Mapping):
                entry["plugin_candidate"] = copy.deepcopy(generation_raw["candidate"]); entry["core_acceptance"] = core_accept_candidate(opportunity, raw, generation_raw, plugin_cfg, Path(output_root), seen_candidate_ids=seen, suitability_execution=suitability_execution, generation_execution=generation_execution)
                seen.add(generation_raw["candidate"]["candidate_id"])
        plugin_records.append(entry)
    base = {"artifact_version": "candidate-portfolio/1", "opportunity_id": opportunity["opportunity_id"], "policy_profile": profile, "policy_digest": _digest({"profile": profile}), "config_digest": _digest(config or {"plugins": [{"plugin_id": r["plugin_id"], "enabled": r["enabled"]} for r in plugin_records]}), "plugin_records": plugin_records}
    base["portfolio_id"] = "CP-" + _digest({"opportunity_id": base["opportunity_id"], "policy_digest": base["policy_digest"], "config_digest": base["config_digest"]})[:24]
    base["suggested_review_order"] = [entry["plugin_candidate"]["candidate_id"] for entry in plugin_records if entry.get("core_acceptance", {}).get("status") == "ACCEPTED" and entry.get("plugin_candidate", {}).get("candidate_status") == "READY"]
    base["audit_records"] = [{"opportunity_id": base["opportunity_id"], "plugin_id": r["plugin_id"], "resolved_plugin_version": r["resolved_plugin_version"], "policy": r["generation_call"], "suitability_raw": r["suitability_raw"], "generation_raw": r.get("generation_raw"), "core_acceptance": r.get("core_acceptance")} for r in plugin_records]
    base["portfolio_digest"] = _digest(base)
    return base


def build_candidate_portfolio(opportunity: Mapping[str, Any], suitability: Mapping[str, Any], generation: Mapping[str, Any] | None, *, core_status: str | None = None, core_problem: Mapping[str, Any] | None = None) -> dict:
    """Narrow Phase 1 compatibility helper."""
    execution, raw = _operation(suitability)
    if raw is None: raise ValueError("invalid suitability Contract response")
    try: validate_suitability_response(raw)
    except Exception as exc: raise ValueError("invalid suitability Contract response") from exc
    if not opportunity.get("opportunity_id") or raw.get("operation_status") != "COMPLETED" or raw.get("suitability") not in {"SUITABLE", "ABSTAIN"} or raw.get("opportunity_id") != opportunity["opportunity_id"]: raise ValueError("invalid opportunity or suitability")
    proposal = {key: copy.deepcopy(raw[key]) for key in ("proposal_id", "suitability", "reason")}
    artifact = {"artifact_version": "candidate-portfolio/1", "portfolio_id": "CP-" + _digest({"opportunity_id": opportunity["opportunity_id"], "proposal_id": proposal["proposal_id"]})[:24], "opportunity_id": opportunity["opportunity_id"], "proposal": proposal, "suitability_raw": raw, "suitability_execution": execution, "generation_call": "NOT_REQUESTED" if proposal["suitability"] == "ABSTAIN" else "REQUESTED", "plugin_candidate": None, "core_acceptance": None}
    if proposal["suitability"] != "ABSTAIN":
        if generation is None: raise ValueError("generation required for non-ABSTAIN")
        gen_execution, gen_raw = _operation(generation)
        try: validate_generation_result(gen_raw, opportunity)
        except Exception as exc: raise ValueError("invalid generation Contract result") from exc
        if any(gen_raw.get(key) != raw.get(key) for key in ("opportunity_id", "proposal_id", "plugin_id", "plugin_version")): raise ValueError("generation lineage mismatch")
        artifact.update({"generation_raw": gen_raw, "generation_execution": gen_execution})
        if gen_raw.get("candidate") is not None:
            if core_status not in {"ACCEPTED", "REJECTED"}: raise ValueError("core_status 必须由 Core 显式决定")
            artifact["plugin_candidate"] = copy.deepcopy(gen_raw["candidate"]); artifact["core_acceptance"] = {"status": core_status, **({"problem": copy.deepcopy(dict(core_problem))} if core_problem else {})}
    artifact["portfolio_digest"] = _digest(artifact)
    return artifact


def ready_candidates(portfolios: Sequence[Mapping[str, Any]]) -> list[dict]:
    result = []
    for portfolio in portfolios:
        entries = portfolio.get("plugin_records") if isinstance(portfolio, Mapping) else None
        for entry in (entries if isinstance(entries, list) else [portfolio]):
            candidate = entry.get("plugin_candidate", {}) if isinstance(entry, Mapping) else {}
            if candidate.get("candidate_status") == "READY" and entry.get("core_acceptance", {}).get("status") == "ACCEPTED": result.append(copy.deepcopy(dict(candidate)))
    return result
