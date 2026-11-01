from typing import Any, Protocol


class SemanticAdapter(Protocol):
    """Domain plugins consume the generic document and never mutate it."""

    domain: str

    def adapt(self, document: Any) -> Any: ...
