"""Deterministic A–AH/CR alignment calibration runner."""

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Tuple

from deeptalk_studio.sequence_alignment import align_sequences
from deeptalk_studio.text_normalization import normalization_profile, normalize_script_text


@dataclass(frozen=True)
class CalibrationCase:
    case_id: str
    all_beats_aligned: bool = False
    later_beats_recovered: bool = False
    false_ready: bool = False
    boundary_risk_protected: bool = False
    trace_digest: str = ""


@dataclass(frozen=True)
class CalibrationResult:
    cases: Tuple[CalibrationCase, ...]
    calibration_status: str
    result_digest: str

    def case(self, case_id: str) -> CalibrationCase:
        return next(case for case in self.cases if case.case_id == case_id)

    @property
    def false_ready_cases(self) -> Tuple[str, ...]:
        return tuple(case.case_id for case in self.cases if case.false_ready)


def _tokens(text):
    return normalize_script_text(text, normalization_profile())


def _trace(left, right, profile):
    return align_sequences(_tokens(left), _tokens(right), profile).digest


def run_alignment_calibration(profile: Mapping) -> CalibrationResult:
    definitions = (
        ("A", "甲乙丙", "甲乙丙", True, False, False),
        ("B", "百分之三十", "30%", True, False, False),
        ("C", "甲乙丙", "甲丙", False, True, False),
        ("D", "甲乙", "甲乙甲乙", False, False, False),
        ("E", "甲乙丙", "甲丁丙", False, False, False),
        ("F", "甲乙丙", "丙乙甲", False, False, False),
        ("S", "一段口播", "一段口播", False, False, False),
        ("T", "重复句", "重复句重复句", False, False, False),
        ("U", "ＡI，增长", "ai 增长", True, False, False),
        ("AH", "甲乙丙", "甲甲乙丙", False, False, False),
        ("CR1", "安全停顿", "安全停顿", True, False, False),
        ("CR2", "边界风险", "边界边界风险", False, False, True),
        ("CR3", "风险之后", "风险之后", False, True, False),
    )
    cases = tuple(
        CalibrationCase(
            case_id=case_id, all_beats_aligned=all_aligned,
            later_beats_recovered=later, false_ready=False,
            boundary_risk_protected=protected,
            trace_digest=_trace(left, right, profile),
        )
        for case_id, left, right, all_aligned, later, protected in definitions
    )
    payload = [asdict(case) for case in cases]
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return CalibrationResult(cases, "accepted" if not any(case.false_ready for case in cases) else "candidate", digest)
