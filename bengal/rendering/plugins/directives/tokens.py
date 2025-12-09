"""
Typed token structures for directive AST.

Provides DirectiveToken as a typed replacement for ad-hoc dicts,
ensuring consistent structure and IDE support across all directives.

Architecture:
    DirectiveToken wraps the dict structure expected by mistune's AST,
    providing type safety while maintaining full compatibility via to_dict().

Related:
    - bengal/rendering/plugins/directives/base.py: BengalDirective uses these tokens
    - RFC: plan/active/rfc-directive-system-v2.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DirectiveToken:
    """
    Typed AST token for directives.

    Replaces ad-hoc dicts like:
        {"type": "dropdown", "attrs": {...}, "children": [...]}

    Benefits:
        - Type checking catches typos
        - IDE autocomplete for fields
        - Consistent structure across all directives

    Example:
        token = DirectiveToken(
            type="dropdown",
            attrs={"title": "Details", "open": True},
            children=parsed_children,
        )
        return token.to_dict()  # For mistune compatibility

    Attributes:
        type: Token type string (e.g., "dropdown", "step", "tab_item")
        attrs: Token attributes dict (title, options, etc.)
        children: Nested tokens (parsed child content)
    """

    type: str
    attrs: dict[str, Any] = field(default_factory=dict)
    children: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dict for mistune AST compatibility.

        Returns:
            Dict in the format mistune expects:
            {"type": str, "attrs": dict, "children": list}
        """
        return {
            "type": self.type,
            "attrs": self.attrs,
            "children": self.children,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DirectiveToken:
        """
        Create from dict (useful for testing and deserialization).

        Args:
            data: Dict with "type", optional "attrs", optional "children"

        Returns:
            DirectiveToken instance
        """
        return cls(
            type=data["type"],
            attrs=data.get("attrs", {}),
            children=data.get("children", []),
        )

    def with_attrs(self, **extra_attrs: Any) -> DirectiveToken:
        """
        Return new token with additional/updated attributes.

        Useful for adding computed attributes without mutating original.

        Args:
            **extra_attrs: Attributes to add or update

        Returns:
            New DirectiveToken with merged attrs
        """
        return DirectiveToken(
            type=self.type,
            attrs={**self.attrs, **extra_attrs},
            children=self.children,
        )

    def with_children(self, children: list[Any]) -> DirectiveToken:
        """
        Return new token with different children.

        Args:
            children: New children list

        Returns:
            New DirectiveToken with specified children
        """
        return DirectiveToken(
            type=self.type,
            attrs=self.attrs,
            children=children,
        )

