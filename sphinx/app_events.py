from __future__ import annotations

from typing import TYPE_CHECKING, overload

from sphinx.util.typing import RoleFunction, TitleGetter

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any, Final, Literal

    from sphinx import addnodes
    from sphinx.builders import Builder
    from sphinx.config import Config, _ConfigRebuild
    from sphinx.domains import Domain, Index
    from sphinx.environment import BuildEnvironment
    from sphinx.environment.collectors import EnvironmentCollector
    from sphinx.ext.autodoc._documenters import Documenter
    from sphinx.ext.autodoc._event_listeners import _AutodocProcessDocstringListener
    from sphinx.ext.todo import todo_node
    from sphinx.extension import Extension
    from sphinx.registry import (
        _MathsBlockRenderers,
        _MathsInlineRenderers,
        _NodeHandler,
        _NodeHandlerPair,
    )
    from sphinx.roles import XRefRole
    from sphinx.search import SearchLanguage
    from sphinx.theming import Theme
    from sphinx.util.docfields import Field

    from .application import Sphinx


class EventManager:
    """Event manager for Sphinx application."""

    def __init__(self, app: Sphinx) -> None:
        self.app = app
        self._listeners: dict[str, list[tuple[int, Callable[..., Any], int]]] = {}

    def add(self, name: str) -> None:
        """Add a new event type."""
        if name not in self._listeners:
            self._listeners[name] = []

    def connect(self, event: str, callback: Callable[..., Any], priority: int = 500) -> int:
        """Connect an event handler."""
        if event not in self._listeners:
            self._listeners[event] = []
        listener_id = len(self._listeners[event])
        self._listeners[event].append((priority, callback, listener_id))
        # Sort by priority (lower number = higher priority)
        self._listeners[event].sort(key=lambda x: x[0])
        return listener_id

    def disconnect(self, listener_id: int) -> None:
        """Disconnect an event handler."""
        for event_listeners in self._listeners.values():
            for i, (_, _, lid) in enumerate(event_listeners):
                if lid == listener_id:
                    event_listeners.pop(i)
                    return

    def emit(self, event: str, *args: Any, **kwargs: Any) -> list[Any]:
        """Emit an event."""
        if event not in self._listeners:
            return []

        results = []
        for _, callback, _ in self._listeners[event]:
            try:
                if 'allowed_exceptions' in kwargs:
                    # Handle exceptions gracefully if specified
                    try:
                        result = callback(*args)
                        results.append(result)
                    except kwargs['allowed_exceptions']:
                        pass
                else:
                    result = callback(*args)
                    results.append(result)
            except Exception:
                # For now, ignore exceptions in event handlers
                pass
        return results

    def emit_firstresult(self, event: str, *args: Any, **kwargs: Any) -> Any | None:
        """Emit an event and return the first non-None result."""
        results = self.emit(event, *args, **kwargs)
        for result in results:
            if result is not None:
                return result
        return None


# Define __all__ for this module
__all__ = ['EventManager']
