"""Read-only compatibility readers for legacy artifact versions.

Phase A surface: these readers verify the declared artifact version and, when
the artifact carries a digest, verify digest consistency.  Artifacts without a
digest (e.g. ``edit-map/1`` from ``build_edit_map()``) undergo strict
schema/type/version validation instead — no historical integrity field is
invented.  All readers return a **deep copy** so callers cannot mutate the
source artifact through nested object references.  Unknown versions fail
closed.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping


class LegacyArtifactReadError(ValueError):
    """Raised when a legacy artifact cannot be read safely."""


class _LegacyArtifactReader:
    """Base class: verify artifact_version, optional digest, return deep copy."""

    artifact_version = ""
    digest_field = ""

    def read(self, value: Any) -> dict[str, Any]:
        data = self._mapping(value)
        version = data.get("artifact_version")
        if version != self.artifact_version:
            raise LegacyArtifactReadError(
                f"unsupported artifact_version: {version!r} "
                f"(expected {self.artifact_version})"
            )
        if self.digest_field and self.digest_field in data:
            digest = data[self.digest_field]
            if not isinstance(digest, str) or not digest:
                raise LegacyArtifactReadError(f"invalid {self.digest_field}")
            expected = self._digest_without(data, self.digest_field)
            if digest != expected:
                raise LegacyArtifactReadError(f"tampered {self.digest_field}")
        self._validate_schema(data)
        return copy.deepcopy(dict(data))

    def _validate_schema(self, data: Mapping[str, Any]) -> None:
        """Subclasses may override for additional schema checks."""
        pass

    def _digest_without(self, data: Mapping[str, Any], field: str) -> str:
        stripped = {key: value for key, value in data.items() if key != field}
        return hashlib.sha256(
            json.dumps(
                stripped, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()

    def _mapping(self, value: Any) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise LegacyArtifactReadError("artifact 必须是 JSON 对象")
        return value


class VisualDirectorPlanV1Reader(_LegacyArtifactReader):
    """Read-only reader for ``visual-director-plan/1`` artifacts.

    The canonical producer (``build_visual_director_plan``) emits a
    ``plan_digest``, so it is verified when present.
    """

    artifact_version = "visual-director-plan/1"
    digest_field = "plan_digest"


class LegacyEditMapV1Reader(_LegacyArtifactReader):
    """Read-only reader for ``edit-map/1`` artifacts.

    The canonical producer (``build_edit_map``) does **not** emit a digest,
    so no digest field is declared.  Schema validation ensures the three
    real fields (``markdown``, ``csv_text``, ``rows``) are present.
    """

    artifact_version = "edit-map/1"
    digest_field = ""  # real edit-map/1 has no digest

    def _validate_schema(self, data: Mapping[str, Any]) -> None:
        for field in ("markdown", "csv_text", "rows"):
            if field not in data:
                raise LegacyArtifactReadError(
                    f"edit-map/1 缺少必填字段：{field}"
                )
        if not isinstance(data["rows"], list):
            raise LegacyArtifactReadError("edit-map/1.rows 必须是列表")