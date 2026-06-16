"""Frozen AST node types for the CSS rule tree.

Mirrors the patitas ``nodes.py`` discipline: every node is a frozen, slotted
dataclass with tuple children, so the tree is immutable and safe to share across
threads. The tree is intentionally shallow — qualified rules, at-rules, and
declarations — because that is all a minifier needs to reason about whitespace
and cascade-safe structural rewrites.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.css.tokens import Token

type Node = QualifiedRule | AtRule | Declaration


@dataclass(frozen=True, slots=True)
class Declaration:
    """A ``property: value`` declaration.

    ``name`` is empty for declarations that could not be parsed into the normal
    shape; in that case ``value`` carries the original tokens and the serializer
    emits them verbatim (fail-safe).
    """

    name: str
    value: tuple[Token, ...]
    important: bool = False


@dataclass(frozen=True, slots=True)
class QualifiedRule:
    """A style rule: a selector prelude followed by a ``{}`` block."""

    prelude: tuple[Token, ...]
    block: tuple[Node, ...]


@dataclass(frozen=True, slots=True)
class AtRule:
    """An at-rule. ``block`` is ``None`` for statement at-rules (``@import ...;``)."""

    name: str  # includes the leading "@"
    prelude: tuple[Token, ...]
    block: tuple[Node, ...] | None
