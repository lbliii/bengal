"""
Graph state validation utilities.

Provides decorators and helpers for validating that the KnowledgeGraph
has been built before analysis methods are called.

This centralizes the validation logic that was previously duplicated in:
- analyzer.py (_ensure_built)
- reporter.py (_ensure_built)
- knowledge_graph.py (inline checks in 15+ methods)

Example:
    >>> from bengal.analysis.utils import require_built
    >>>
    >>> class MyAnalyzer:
    ...     def __init__(self, graph):
    ...         self._graph = graph
    ...
    ...     @require_built
    ...     def analyze(self):
    ...         # Graph is guaranteed to be built here
    ...         return self._graph.metrics

"""

from functools import wraps
from typing import TYPE_CHECKING, Any

from bengal.errors import BengalGraphError, ErrorCode

if TYPE_CHECKING:
    from collections.abc import Callable


def require_built[F: Callable[..., Any]](method: F) -> F:
    """
    Decorator ensuring KnowledgeGraph is built before method execution.

    Works with methods on objects that have either:
    - A `_graph` attribute pointing to a KnowledgeGraph
    - Are themselves a KnowledgeGraph (have `_built` attribute)

    Raises:
        BengalGraphError: With code G001 if graph is not built.

    Example:
        >>> class GraphAnalyzer:
        ...     def __init__(self, graph):
        ...         self._graph = graph
        ...
        ...     @require_built
        ...     def get_hubs(self):
        ...         return self._graph.get_hubs()

    """

    @wraps(method)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        # Get the graph - either self._graph or self if it's a KnowledgeGraph
        graph = getattr(self, "_graph", self)

        # Check if built
        if not getattr(graph, "_built", False):
            raise BengalGraphError(
                "KnowledgeGraph is not built",
                code=ErrorCode.G001,
                suggestion=f"Call graph.build() before {method.__name__}()",
            )

        return method(self, *args, **kwargs)

    return wrapper  # type: ignore[return-value]


def ensure_built(graph: Any, method_name: str = "this operation") -> None:
    """
    Ensure a graph is built, raising an error if not.

    This is the non-decorator version for cases where a decorator
    doesn't fit well (e.g., standalone functions).

    Args:
        graph: KnowledgeGraph instance to check
        method_name: Name to include in error message

    Raises:
        BengalGraphError: With code G001 if graph is not built.

    Example:
        >>> from bengal.analysis.utils.validation import ensure_built
        >>> ensure_built(graph, "path analysis")

    """
    if not getattr(graph, "_built", False):
        raise BengalGraphError(
            "KnowledgeGraph is not built",
            code=ErrorCode.G001,
            suggestion=f"Call graph.build() before {method_name}",
        )
