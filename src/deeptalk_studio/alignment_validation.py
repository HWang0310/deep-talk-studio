"""Independent full re-derivation validator for Script Alignment artifacts."""

from typing import Any, Mapping, Sequence

from .alignment_builder import build_script_alignment
from .alignment_schema import SCRIPT_ALIGNMENT_SCHEMA
from .validation import ReportValidationError, validate_json_schema


class AlignmentValidationError(ValueError):
    """Script Alignment is invalid, tampered, stale or false-precise."""


def validate_script_alignment(
    artifact: Mapping[str, Any], script, transcript, mapping,
    profile: Mapping[str, Any], cues: Sequence[Mapping[str, Any]], media,
) -> None:
    try:
        validate_json_schema(dict(artifact), SCRIPT_ALIGNMENT_SCHEMA)
    except (ReportValidationError, RuntimeError) as exc:
        raise AlignmentValidationError(f"Script Alignment schema 无效：{exc}") from exc
    expected = build_script_alignment(
        script, transcript, mapping, profile, cues,
        alignment_id=artifact["alignment_id"], created_at=artifact["created_at"],
        media=media,
    )
    if dict(artifact) != expected:
        raise AlignmentValidationError("Script Alignment 与受控输入的重推导结果不一致")
