from typing import Any, Dict, Protocol


class ResearchProvider(Protocol):
    def research(self, topic: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        ...

