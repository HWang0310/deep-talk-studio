"""Read-only adapters: frozen Contract V1 -> V2 compatibility views.

Phase A compatibility surface only.  It does **not** change the frozen V1
runtime path (``visual_asset_plugin_contract.py`` / ``visual_plugin_adapter.py``)
and never writes back to any artifact.

Mapping rules (read-only, deep-copy):
  Generation result:
    - COMPLETED + READY / QA_REJECTED  -> V2 result view with candidate
    - FAILED / BLOCKED / UNAVAILABLE    -> V2 result view with problem, no candidate
    - ``suggested_placement`` -> ``intrinsic_placement_hint``
  Suitability response:
    - COMPLETED + SUITABLE / BORDERLINE / ABSTAIN -> V2 suitability view
    - FAILED / UNAVAILABLE                         -> V2 suitability view with problem

No new IDs are created.  All outputs are deep-copied so callers cannot
mutate the source artifact through nested object references.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from .visual_asset_plugin_contract import (
    VisualAssetPluginContractError,
    validate_generation_result,
    validate_suitability_response,
)
from .visual_asset_plugin_contract_v2 import (
    CONTRACT_VERSION_V2,
    VisualAssetPluginContractV2Error,
    validate_v2_result_view,
    validate_v2_suitability_view,
)


class ContractV1ToV2AdapterError(ValueError):
    """A deterministic error for incompatible V1 -> V2 conversion."""


# ===========================================================================
# Generation result adapter
# ===========================================================================

def convert_v1_generation_result_to_v2(
    result: Mapping[str, Any], opportunity: Mapping[str, Any]
) -> dict[str, Any]:
    """Convert a validated V1 generation result into a V2 result view.

    COMPLETED results carry a candidate; failure statuses preserve the
    raw ``operation_status`` and ``problem`` without fabricating a candidate.
    """
    try:
        validate_generation_result(result, opportunity)
    except VisualAssetPluginContractError as exc:
        raise ContractV1ToV2AdapterError(f"invalid_v1_result: {exc}") from exc

    view: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION_V2,
        "request_id": result["request_id"],
        "opportunity_id": result["opportunity_id"],
        "proposal_id": result["proposal_id"],
        "plugin_id": result["plugin_id"],
        "plugin_version": result["plugin_version"],
        "operation_status": result["operation_status"],
    }

    status = result["operation_status"]
    if status == "COMPLETED":
        candidate = result.get("candidate")
        if not isinstance(candidate, Mapping):
            raise ContractV1ToV2AdapterError(
                "no_candidate: COMPLETED result missing candidate"
            )
        view_candidate: dict[str, Any] = {
            "candidate_id": candidate["candidate_id"],
            "asset_family": candidate["asset_family"],
            "candidate_status": candidate["candidate_status"],
        }
        if "duration_ms" in candidate:
            view_candidate["duration_ms"] = candidate["duration_ms"]
        if "suggested_placement" in candidate:
            view_candidate["intrinsic_placement_hint"] = copy.deepcopy(
                candidate["suggested_placement"]
            )
        for field in ("artifacts", "qa", "provenance", "plugin_metadata"):
            if field in candidate:
                view_candidate[field] = copy.deepcopy(candidate[field])
        view["candidate"] = view_candidate
    else:
        view["problem"] = copy.deepcopy(result["problem"])

    validate_v2_result_view(view, opportunity)
    return view


# ===========================================================================
# Suitability response adapter
# ===========================================================================

def convert_v1_suitability_response_to_v2(
    response: Mapping[str, Any],
) -> dict[str, Any]:
    """Convert a validated V1 suitability response into a V2 suitability view.

    COMPLETED responses carry proposal_id / suitability / reason; failure
    statuses preserve the raw ``operation_status`` and ``problem``.
    """
    try:
        validate_suitability_response(response)
    except VisualAssetPluginContractError as exc:
        raise ContractV1ToV2AdapterError(f"invalid_v1_suitability: {exc}") from exc

    view: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION_V2,
        "request_id": response["request_id"],
        "opportunity_id": response["opportunity_id"],
        "plugin_id": response["plugin_id"],
        "plugin_version": response["plugin_version"],
        "operation_status": response["operation_status"],
    }

    status = response["operation_status"]
    if status == "COMPLETED":
        view["proposal_id"] = response["proposal_id"]
        view["suitability"] = response["suitability"]
        view["reason"] = response["reason"]
    else:
        view["problem"] = copy.deepcopy(response["problem"])

    validate_v2_suitability_view(view)
    return view