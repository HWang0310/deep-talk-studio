from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class ResearchReport:
    """Validated, versioned Research Report value object."""

    data: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchReport":
        from .validation import ReportValidationError, validate_report

        if not isinstance(data, dict):
            raise ReportValidationError("Research Report 必须是 JSON 对象")
        report = cls(deepcopy(data))
        validate_report(report)
        return report

    def to_dict(self) -> Dict[str, Any]:
        return deepcopy(self.data)

    def __getattr__(self, name: str) -> Any:
        try:
            return self.data[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


@dataclass(frozen=True)
class TopicCandidateSet:
    """Validated, versioned Topic Discovery value object."""

    data: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TopicCandidateSet":
        from .discovery_validation import DiscoveryValidationError, validate_candidate_set

        if not isinstance(data, dict):
            raise DiscoveryValidationError("Topic Candidate Set 必须是 JSON 对象")
        artifact = cls(deepcopy(data))
        validate_candidate_set(artifact)
        return artifact

    def to_dict(self) -> Dict[str, Any]:
        return deepcopy(self.data)

    def __getattr__(self, name: str) -> Any:
        try:
            return self.data[name]
        except KeyError as exc:
            raise AttributeError(name) from exc
