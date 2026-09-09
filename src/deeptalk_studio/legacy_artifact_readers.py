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
    """Base class: verify artifact_version, optional digest, return deep copy.

    Subclasses with ``digest_field`` set may choose to make the digest
    mandatory by overriding :meth:`_validate_schema`.
    """

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
        self._validate_schema(data)
        return copy.deepcopy(dict(data))

    def _validate_schema(self, data: Mapping[str, Any]) -> None:
        """Subclasses override for additional schema checks.

        The base implementation handles optional digest verification: if
        ``digest_field`` is set and present in ``data``, the digest is
        verified.  Subclasses that need a *mandatory* digest should override
        this method entirely (see :class:`VisualDirectorPlanV1Reader`).
        """
        if self.digest_field and self.digest_field in data:
            self._verify_digest(data, self.digest_field)

    def _verify_digest(self, data: Mapping[str, Any], field: str) -> None:
        digest = data[field]
        if not isinstance(digest, str) or not digest:
            raise LegacyArtifactReadError(f"invalid {field}")
        expected = self._digest_without(data, field)
        if digest != expected:
            raise LegacyArtifactReadError(f"tampered {field}")

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

    The canonical producer (``build_visual_director_plan``) always emits a
    ``plan_digest``, so this reader **requires** it to be present and
    correct.  In addition, the full canonical schema is validated:

    ``plan_id``, ``revision``, ``previous_revision``, ``created_at``,
    ``alignment_digest``, ``opportunities`` must all be present with
    correct types.
    """

    artifact_version = "visual-director-plan/1"
    digest_field = "plan_digest"

    _REQUIRED_FIELDS = (
        "plan_id", "revision", "previous_revision", "created_at",
        "alignment_digest", "opportunities",
    )

    def _validate_schema(self, data: Mapping[str, Any]) -> None:
        # --- mandatory fields ---
        for field in self._REQUIRED_FIELDS:
            if field not in data:
                raise LegacyArtifactReadError(
                    f"visual-director-plan/1 缺少必填字段：{field}"
                )
        # --- type validation ---
        if not isinstance(data["plan_id"], str) or not data["plan_id"].strip():
            raise LegacyArtifactReadError("plan_id 必须是非空文本")
        if not isinstance(data["revision"], int) or isinstance(data["revision"], bool):
            raise LegacyArtifactReadError("revision 必须是整数")
        if not isinstance(data["previous_revision"], int) or isinstance(data["previous_revision"], bool):
            raise LegacyArtifactReadError("previous_revision 必须是整数")
        if not isinstance(data["created_at"], str) or not data["created_at"].strip():
            raise LegacyArtifactReadError("created_at 必须是非空文本")
        if not isinstance(data["alignment_digest"], str) or not data["alignment_digest"].strip():
            raise LegacyArtifactReadError("alignment_digest 必须是非空文本")
        if not isinstance(data["opportunities"], list):
            raise LegacyArtifactReadError("opportunities 必须是列表")
        # --- mandatory plan_digest (always emitted by canonical producer) ---
        if self.digest_field not in data:
            raise LegacyArtifactReadError(
                f"visual-director-plan/1 缺少必填字段：{self.digest_field}"
            )
        self._verify_digest(data, self.digest_field)


class LegacyEditMapV1Reader(_LegacyArtifactReader):
    """Read-only reader for ``edit-map/1`` artifacts.

    The canonical producer (``build_edit_map``) does **not** emit a digest,
    so no digest field is declared.  Schema validation ensures the three
    real fields (``markdown``, ``csv_text``, ``rows``) are present with
    correct types, and each row is a mapping containing the canonical
    producer keys (``时间``, ``素材``, ``建议``, ``用途``, ``为什么``,
    ``备选``) with string values.
    """

    artifact_version = "edit-map/1"
    digest_field = ""  # real edit-map/1 has no digest

    _CANONICAL_ROW_KEYS = ("时间", "素材", "建议", "用途", "为什么", "备选")

    def _validate_schema(self, data: Mapping[str, Any]) -> None:
        for field in ("markdown", "csv_text", "rows"):
            if field not in data:
                raise LegacyArtifactReadError(
                    f"edit-map/1 缺少必填字段：{field}"
                )
        if not isinstance(data["markdown"], str):
            raise LegacyArtifactReadError("markdown 必须是字符串")
        if not isinstance(data["csv_text"], str):
            raise LegacyArtifactReadError("csv_text 必须是字符串")
        if not isinstance(data["rows"], list):
            raise LegacyArtifactReadError("edit-map/1.rows 必须是列表")
        for index, row in enumerate(data["rows"]):
            if not isinstance(row, Mapping):
                raise LegacyArtifactReadError(
                    f"edit-map/1.rows[{index}] 必须是 JSON 对象"
                )
            for key in self._CANONICAL_ROW_KEYS:
                if key not in row:
                    raise LegacyArtifactReadError(
                        f"edit-map/1.rows[{index}] 缺少必填字段：{key}"
                    )
                if not isinstance(row[key], str):
                    raise LegacyArtifactReadError(
                        f"edit-map/1.rows[{index}].{key} 必须是字符串"
                    )