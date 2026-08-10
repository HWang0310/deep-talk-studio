from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict


REQUIRED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "topic",
    "research_question",
    "generated_at",
    "scope_summary",
    "executive_summary",
    "sources",
    "claims",
    "timeline",
    "perspectives",
    "conflicts",
    "open_questions",
    "angles",
    "fact_check_notes",
    "limitations",
    "handoff_to_script_agent",
)


@dataclass(frozen=True)
class ResearchReport:
    """Versioned Research Report value object.

    Nested values remain JSON-compatible dictionaries and lists so future agents can
    extend the schema without coupling the renderer to API-specific classes.
    """

    data: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResearchReport":
        if not isinstance(data, dict):
            raise TypeError("Research Report 必须是 JSON 对象")
        missing = [field for field in REQUIRED_TOP_LEVEL_FIELDS if field not in data]
        if missing:
            raise ValueError("Research Report 缺少字段：" + ", ".join(missing))
        return cls(deepcopy(data))

    def to_dict(self) -> Dict[str, Any]:
        return deepcopy(self.data)

    def __getattr__(self, name: str) -> Any:
        try:
            return self.data[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

