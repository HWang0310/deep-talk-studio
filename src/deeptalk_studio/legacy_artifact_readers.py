"""Read-only compatibility readers for legacy artifact versions.

Phase A surface: these readers verify the declared artifact version and digest
consistency, then return a shallow copy so callers can never mutate the
historical artifact.  Unknown versions and tampered digests fail closed.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


class LegacyArtifactReadError(ValueError):
    """Raised when a legacy artifact cannot be read safely."""


class _DigestArtifactReader:
    """Base class: verify artifact_version + digest, return a shallow copy."""

    artifact_version = ""
    digest_field = ""

    def read(self, value: Any) -> dict[str, Any]:
        data = self._mapping(value)
        version = data.get("artifact_version")
        if version != self.artifact_version:
            raise LegacyArtifactReadError(
                f"unsupported artifact_version: {version!r} (expected {self.artifact_version})"
            )
        digest = data.get(self.digest_field)
        if not isinstance(digest, str) or not digest:
            raise LegacyArtifactReadError(f"missing {self.digest_field}")
        expected = self._digest_without(data, self.digest_field)
        if digest != expected:
            raise LegacyArtifactReadError(f"tampered {self.digest_field}")
        return dict(data)

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


class VisualDirectorPlanV1Reader(_DigestArtifactReader):
    """Read-only reader for ``visual-director-plan/1`` artifacts."""

    artifact_version = "visual-director-plan/1"
    digest_field = "plan_digest"


class LegacyEditMapV1Reader(_DigestArtifactReader):
    """Read-only reader for ``edit-map/1`` artifacts."""

    artifact_version = "edit-map/1"
    digest_field = "map_digest"