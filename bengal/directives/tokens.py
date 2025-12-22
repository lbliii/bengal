"""Typed token structures for the directive AST.

This module provides ``DirectiveToken``, a typed dataclass that replaces
ad-hoc dictionaries for representing directive nodes in Mistune's AST.
Using a typed class provides type safety, IDE autocomplete, and consistent
structure across all directive implementations.

Key Features:
    - **Type Safety**: Type annotations catch typos and invalid structures.
    - **IDE Support**: Autocomplete for ``type``, ``attrs``, ``children``.
    - **Mistune Compatibility**: ``to_dict()`` converts to the dict format
      expected by Mistune's AST.
    - **Immutable Operations**: ``with_attrs()`` and ``with_children()`` return
      new tokens without mutating the original.
    - **DirectiveType Enum**: Known directive types for type-safe validation.

Example:
    Create a token and convert for Mistune::

        token = DirectiveToken(
            type="dropdown",
            attrs={"title": "Details", "open": True},
            children=parsed_children,
        )
        return token.to_dict()  # {"type": "dropdown", "attrs": {...}, ...}

See Also:
    - ``bengal.directives.base``: ``BengalDirective.parse_directive()`` returns tokens.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DirectiveType(Enum):
    """Known directive types for type-safe validation.

    This enum defines all standard Bengal directive types, enabling type-safe
    comparisons and IDE autocomplete when working with directive tokens.

    Example:
        >>> DirectiveType.STEP.value
        'step'
        >>> DirectiveType.NOTE.value
        'note'
    """

    # Container directives
    STEP = "step"
    STEPS = "steps"
    TAB_ITEM = "tab_item"
    TAB_SET = "tab_set"
    TABS = "tabs"

    # Admonition directives
    NOTE = "note"
    WARNING = "warning"
    TIP = "tip"
    IMPORTANT = "important"
    CAUTION = "caution"

    # Code directives
    CODE_INCLUDE = "code_include"
    CODE_TABS = "code_tabs"
    LITERALINCLUDE = "literalinclude"

    # Card directives
    CARD = "card"
    CARDS_GRID = "cards_grid"
    CHILD_CARDS = "child_cards"

    # Other directives
    DROPDOWN = "dropdown"
    FIGURE = "figure"
    GALLERY = "gallery"
    GLOSSARY = "glossary"
    TOC = "toc"
    BUTTON = "button"
    BADGE = "badge"
    ICON = "icon"
    VIDEO = "video"
    EMBED = "embed"
    TERMINAL = "terminal"
    MARIMO = "marimo"
    CHECKLIST = "checklist"
    DATA_TABLE = "data_table"
    LIST_TABLE = "list_table"
    INCLUDE = "include"
    TARGET = "target"
    RUBRIC = "rubric"


@dataclass(slots=True)
class DirectiveToken:
    """Typed AST token for directive nodes.

    A structured replacement for ad-hoc dictionaries like
    ``{"type": "dropdown", "attrs": {...}, "children": [...]}``.
    Provides type safety, IDE support, and consistent structure.

    Attributes:
        type: Token type string matching the directive's ``TOKEN_TYPE``
            (e.g., ``"dropdown"``, ``"step"``, ``"tab_item"``).
        attrs: Dictionary of token attributes (title, options, etc.).
            Defaults to empty dict.
        children: List of nested tokens (parsed child content).
            Defaults to empty list.

    Example:
        Create a token in ``parse_directive()``::

            token = DirectiveToken(
                type="dropdown",
                attrs={"title": "Details", "open": True},
                children=parsed_children,
            )
            return token.to_dict()  # Convert for Mistune compatibility

        Add attributes without mutation::

            updated = token.with_attrs(id="my-dropdown")
    """

    type: str
    """Token type string (e.g., 'dropdown', 'step')."""

    attrs: dict[str, Any] = field(default_factory=dict)
    """Token attributes dictionary."""

    children: list[Any] = field(default_factory=list)
    """Nested child tokens."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to a dictionary for Mistune AST compatibility.

        Mistune expects tokens as dictionaries with ``type``, ``attrs``, and
        ``children`` keys. Call this method when returning from ``parse_directive()``.

        Returns:
            Dictionary in Mistune's expected format::

                {"type": str, "attrs": dict, "children": list}
        """
        return {
            "type": self.type,
            "attrs": self.attrs,
            "children": self.children,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DirectiveToken:
        """Create a token from a dictionary.

        Useful for testing, deserialization, or converting existing dict-based
        tokens to typed instances.

        Args:
            data: Dictionary with ``"type"`` (required), and optional ``"attrs"``
                and ``"children"``.

        Returns:
            A new ``DirectiveToken`` instance.

        Example:
            >>> token = DirectiveToken.from_dict({"type": "note", "attrs": {"class": "info"}})
            >>> token.type
            'note'
        """
        return cls(
            type=data["type"],
            attrs=data.get("attrs", {}),
            children=data.get("children", []),
        )

    def with_attrs(self, **extra_attrs: Any) -> DirectiveToken:
        """Return a new token with additional or updated attributes.

        Creates a new token with merged attributes, leaving the original
        unchanged. Useful for adding computed attributes after initial parsing.

        Args:
            **extra_attrs: Attributes to add or update. Existing attributes
                with the same keys are overwritten.

        Returns:
            A new ``DirectiveToken`` with merged ``attrs``.

        Example:
            >>> token = DirectiveToken(type="card", attrs={"title": "My Card"})
            >>> updated = token.with_attrs(id="card-1", open=True)
            >>> updated.attrs
            {'title': 'My Card', 'id': 'card-1', 'open': True}
        """
        return DirectiveToken(
            type=self.type,
            attrs={**self.attrs, **extra_attrs},
            children=self.children,
        )

    def with_children(self, children: list[Any]) -> DirectiveToken:
        """Return a new token with different children.

        Creates a new token with the specified children, leaving the original
        unchanged. Useful for post-processing or filtering nested content.

        Args:
            children: The new children list to use.

        Returns:
            A new ``DirectiveToken`` with the specified ``children``.

        Example:
            >>> token = DirectiveToken(type="tabs", children=raw_children)
            >>> filtered = token.with_children([c for c in raw_children if c["type"] == "tab"])
        """
        return DirectiveToken(
            type=self.type,
            attrs=self.attrs,
            children=children,
        )
