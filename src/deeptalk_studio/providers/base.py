from dataclasses import dataclass
from typing import Any, Dict, Protocol

from ..provenance import ProviderProvenance


@dataclass(frozen=True)
class ProviderResult:
    data: Dict[str, Any]
    provenance: ProviderProvenance


class ResearchProvider(Protocol):
    def research(self, topic: str, schema: Dict[str, Any]) -> ProviderResult:
        ...

    def fact_check(self, report: Dict[str, Any], schema: Dict[str, Any]) -> ProviderResult:
        ...
