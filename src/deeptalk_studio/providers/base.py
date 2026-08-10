from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol

from ..provenance import ProviderProvenance


@dataclass(frozen=True)
class ProviderResult:
    data: Dict[str, Any]
    provenance: ProviderProvenance


class ResearchProvider(Protocol):
    def discover(self, query: str, schema: Dict[str, Any]) -> ProviderResult:
        ...

    def research(
        self, topic: str, schema: Dict[str, Any], research_handoff: Optional[Dict[str, Any]] = None
    ) -> ProviderResult:
        ...

    def fact_check(self, report: Dict[str, Any], schema: Dict[str, Any]) -> ProviderResult:
        ...
