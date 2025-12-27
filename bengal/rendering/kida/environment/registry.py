"""Filter and test registry for Kida environment.

Provides Jinja2-compatible dict-like interface for filters and tests.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.rendering.kida.environment.core import Environment


class FilterRegistry:
    """Dict-like interface for filters/tests that matches Jinja2's API.

    Supports:
        - env.filters['name'] = func
        - env.filters.update({'name': func})
        - func = env.filters['name']
        - 'name' in env.filters

    All mutations use copy-on-write for thread-safety.
    """

    __slots__ = ("_env", "_attr")

    def __init__(self, env: Environment, attr: str):
        self._env = env
        self._attr = attr

    def _get_dict(self) -> dict[str, Callable]:
        return getattr(self._env, self._attr)

    def _set_dict(self, d: dict[str, Callable]) -> None:
        setattr(self._env, self._attr, d)

    def __getitem__(self, name: str) -> Callable:
        return self._get_dict()[name]

    def __setitem__(self, name: str, func: Callable) -> None:
        new = self._get_dict().copy()
        new[name] = func
        self._set_dict(new)

    def __contains__(self, name: object) -> bool:
        return name in self._get_dict()

    def get(self, name: str, default: Callable | None = None) -> Callable | None:
        return self._get_dict().get(name, default)

    def update(self, mapping: dict[str, Callable]) -> None:
        """Batch update filters (Jinja2 compatibility)."""
        new = self._get_dict().copy()
        new.update(mapping)
        self._set_dict(new)

    def copy(self) -> dict[str, Callable]:
        """Return a copy of the underlying dict."""
        return self._get_dict().copy()

    def keys(self):
        return self._get_dict().keys()

    def values(self):
        return self._get_dict().values()

    def items(self):
        return self._get_dict().items()
