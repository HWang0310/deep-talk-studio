"""Versioned deterministic alignment scoring and status thresholds."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from .alignment_schema import ALIGNMENT_PROFILE_SCHEMA
from .validation import ReportValidationError, validate_json_schema


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ALIGNMENT_PROFILE = REPO_ROOT / "config" / "alignment-profile-candidate.json"


class AlignmentProfileError(ValueError):
    """Alignment profile violates the approved candidate/accepted contract."""


def _canonical_digest(value: Mapping[str, Any], digest_field: str) -> str:
    payload = deepcopy(dict(value))
    payload.pop(digest_field, None)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def alignment_profile_digest(profile: Mapping[str, Any]) -> str:
    return _canonical_digest(profile, "profile_digest")


def _validate_candidate_values(profile: Mapping[str, Any]) -> None:
    locked = {
        "artifact_version": "alignment-profile/1",
        "algorithm_version": "alignment-algorithm/1",
        "normalization_profile_version": "normalization-profile/1",
        "value_revision": 1,
        "primary_match_score": 4.0,
        "numeric_alias_match_score": 3.0,
        "substitution_score": -2.5,
        "script_deletion_score": -2.0,
        "transcript_insertion_score": -1.5,
        "ambiguity_normalized_margin": 0.08,
        "accepted_floors": {"coverage": 0.85, "similarity": 0.88},
        "review_floors": {"coverage": 0.55, "similarity": 0.65},
        "long_gap_token_threshold": 8,
        "timestamp_epsilon_seconds": "0.001",
        "source_design_head": "702c63e13d579bb5a651727684a546527c6a8731",
        "source_design_digest": "68f8a10e09390b13b616d361dc8b42074e2af2ec73ee16f41ee74bb2bbe4cc17",
    }
    for key, expected in locked.items():
        if profile.get(key) != expected:
            raise AlignmentProfileError(f"Alignment Profile candidate 受控字段被更改：{key}")
    if profile.get("calibration_status") != "candidate":
        raise AlignmentProfileError("校准证据完成前不得标记 accepted")


def load_alignment_profile(path: Optional[Path] = None) -> Dict[str, Any]:
    selected = Path(path or DEFAULT_ALIGNMENT_PROFILE)
    try:
        profile = json.loads(selected.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AlignmentProfileError(f"无法读取 Alignment Profile：{selected}") from exc
    try:
        validate_json_schema(profile, ALIGNMENT_PROFILE_SCHEMA)
    except (ReportValidationError, RuntimeError) as exc:
        raise AlignmentProfileError(f"Alignment Profile schema 无效：{exc}") from exc
    _validate_candidate_values(profile)
    actual = alignment_profile_digest(profile)
    if profile["profile_digest"] != actual:
        raise AlignmentProfileError("Alignment Profile digest 不匹配")
    return profile
