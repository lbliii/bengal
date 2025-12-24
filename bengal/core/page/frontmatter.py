"""Typed frontmatter with dict-style access for template compatibility."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Frontmatter:
    """
    Typed frontmatter metadata with backward-compatible dict access.

    Standard fields have explicit types for IDE autocomplete and type checking.
    Unknown fields are stored in `extra` and accessible via dict syntax.

    Example:
        >>> fm = Frontmatter(title="My Post", tags=["python"])
        >>> fm.title           # Typed access: str
        'My Post'
        >>> fm["title"]        # Dict access (templates): Any
        'My Post'
        >>> fm.get("missing")  # Safe access with default
        None
    """

    # Core fields (from PageCore, single source of truth)
    title: str = ""
    date: datetime | None = None
    tags: list[str] = field(default_factory=list)
    slug: str | None = None
    weight: int | None = None

    # i18n
    lang: str | None = None

    # Content type
    type: str | None = None
    layout: str | None = None

    # SEO
    description: str | None = None

    # Behavior
    draft: bool = False
    aliases: list[str] = field(default_factory=list)

    # Extension point for custom fields
    extra: dict[str, Any] = field(default_factory=dict)

    # ---- Dict Compatibility (for templates) ----

    def __getitem__(self, key: str) -> Any:
        """Dict-style access: fm["title"]."""
        if key == "extra":
            return self.extra
        if hasattr(self, key) and key != "extra":
            value = getattr(self, key)
            if value is not None:
                return value
        if key in self.extra:
            return self.extra[key]
        raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        """Support `"title" in fm`."""
        if not isinstance(key, str):
            return False
        if hasattr(self, key) and key != "extra":
            return getattr(self, key) is not None
        return key in self.extra

    def get(self, key: str, default: Any = None) -> Any:
        """Dict.get() compatibility."""
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self) -> Iterator[str]:
        """Iterate over available keys."""
        for f in self.__dataclass_fields__:
            if f != "extra" and getattr(self, f) is not None:
                yield f
        yield from self.extra.keys()

    def items(self) -> Iterator[tuple[str, Any]]:
        """Iterate over key-value pairs."""
        for key in self.keys():
            yield key, self[key]

    # ---- Factory ----

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Frontmatter:
        """
        Create Frontmatter from raw dict (e.g., parsed YAML).

        Known fields are extracted and typed; unknown fields go to extra.
        """
        known_fields = {f for f in cls.__dataclass_fields__ if f != "extra"}
        known = {}
        extra = {}

        for key, value in data.items():
            if key in known_fields:
                known[key] = value
            else:
                extra[key] = value

        return cls(**known, extra=extra)
