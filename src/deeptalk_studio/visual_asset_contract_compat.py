"""Read-only adapter: frozen Contract V1 generation result -> V2 result view.

Phase A compatibility surface only.  It does **not** change the frozen V1
runtime path (``visual_asset_plugin_contract.py`` / ``visual_plugin_adapter.py``)
and never writes back to any artifact.

Mapping rules (read-only):
- ``suggested_placement`` -> ``intrinsic_placement_hint`` (plugin-owned hint).
- Failure statuses (FAILED / BLOCKED / UNAVAILABLE) produce **no** result view.
- Raw candidate identity fields and raw statuses are preserved unchanged.
- No new IDs are created by this adapter.
"""
from __future__ import annotations

from typing import Any, Mapping

from .visual_asset_plugin_contract import (
    VisualAssetPluginContractError,
    validate_generation_result,
)
from .visual_asset_plugin_contract_v2 import (
    CONTRACT_VERSION_V2,
    VisualAssetPluginContractV2Error,
    validate_v2_result_view,
)


class ContractV1ToV2AdapterError(ValueError):
    """A deterministic error for incompatible V1 -> V2 conversion."""


class ContractV1ToV2Adapter:
    """Convert a validated V1 generation result into a V2 result view."""

    def __init__(self, result: Mapping[str, Any], opportunity: Mapping[str, Any]):
        self._result = dict(result)
        self._opportunity = dict(opportunity)

    def convert(self) -> dict[str, Any]:
        try:
            validate_generation_result(self._result, self._opportunity)
        except VisualAssetPluginContractError as exc:
            raise ContractV1ToV2AdapterError(f"invalid_v1_result: {exc}") from exc
        if self._result.get("operation_status") != "COMPLETED":
            raise ContractV1ToV2AdapterError(
                f"no_candidate: operation_status={self._result.get('operation_status')!r}"
            )
        candidate = self._result.get("candidate")
        if not isinstance(candidate, Mapping):
            raise ContractV1ToV2AdapterError("no_candidate: COMPLETED result missing candidate")
        view_candidate = {
            "candidate_id": candidate["candidate_id"],
            "asset_family": candidate["asset_family"],
            "candidate_status": candidate["candidate_status"],
        }
        if "duration_ms" in candidate:
            view_candidate["duration_ms"] = candidate["duration_ms"]
        if "suggested_placement" in candidate:
            view_candidate["intrinsic_placement_hint"] = dict(candidate["suggested_placement"])
        for field in ("artifacts", "qa", "provenance", "plugin_metadata"):
            if field in candidate:
                view_candidate[field] = candidate[field]
        view = {
            "contract_version": CONTRACT_VERSION_V2,
            "request_id": self._result["request_id"],
            "opportunity_id": self._result["opportunity_id"],
            "proposal_id": self._result["proposal_id"],
            "plugin_id": self._result["plugin_id"],
            "plugin_version": self._result["plugin_version"],
            "operation_status": "COMPLETED",
            "candidate": view_candidate,
        }
        validate_v2_result_view(view, self._opportunity)
        return view

    def __call__(self) -> dict[str, Any]:
        return self.convert()


def convert_v1_generation_result_to_v2_candidate(
    result: Mapping[str, Any], opportunity: Mapping[str, Any]
) -> dict[str, Any]:
    """Module-level convenience for the read-only V1 -> V2 adapter."""
    return ContractV1ToV2Adapter(result, opportunity).convert()