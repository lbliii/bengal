"""Level ``AGGRESSIVE`` structural rewrites (cascade-invariant only).

Every pass here is provably cascade-invariant — it may not change which
declaration wins for any element in any state. The membership rule is strict
adjacency + identity:

- remove empty style rules (``.a{}``);
- remove an exact-duplicate declaration shadowed by a later identical one;
- merge **adjacent** rules with identical selector preludes (concatenate blocks);
- merge **adjacent** rules with identical blocks (union the selector lists);
- merge **adjacent** at-rules with identical name + prelude (concatenate blocks).

Deliberately excluded (cascade-risky): fallback-duplicate removal
(``display:flex;display:grid``), longhand→shorthand folding, non-adjacent merges,
and override elimination. The :func:`bengal.css.cascade.resolve` oracle guards
this whole tier at runtime.
"""

from bengal.css.cascade import selector_sig, tree_sig
from bengal.css.nodes import AtRule, Declaration, Node, QualifiedRule
from bengal.css.tokens import Token, TokenType

_COMMA = Token(TokenType.COMMA, ",")


def structural_optimize(nodes: tuple[Node, ...]) -> tuple[Node, ...]:
    """Apply all cascade-invariant structural passes to a node list."""
    nodes = tuple(_recurse(n) for n in nodes)
    nodes = _dedup_declarations(nodes)
    nodes = _drop_empty(nodes)
    return _merge_adjacent(nodes)


def _recurse(node: Node) -> Node:
    if isinstance(node, QualifiedRule):
        return QualifiedRule(node.prelude, structural_optimize(node.block))
    if isinstance(node, AtRule) and node.block is not None:
        return AtRule(node.name, node.prelude, structural_optimize(node.block))
    return node


def _decl_key(decl: Declaration) -> tuple[object, ...]:
    name = decl.name if decl.name.startswith("--") else decl.name.lower()
    return (name, decl.value, decl.important)


def _dedup_declarations(nodes: tuple[Node, ...]) -> tuple[Node, ...]:
    keys: list[tuple[object, ...] | None] = [
        _decl_key(n) if isinstance(n, Declaration) else None for n in nodes
    ]
    out: list[Node] = []
    for i, node in enumerate(nodes):
        if keys[i] is not None and keys[i] in keys[i + 1 :]:
            continue
        out.append(node)
    return tuple(out)


def _drop_empty(nodes: tuple[Node, ...]) -> tuple[Node, ...]:
    return tuple(n for n in nodes if not (isinstance(n, QualifiedRule) and not n.block))


def _merge_adjacent(nodes: tuple[Node, ...]) -> tuple[Node, ...]:
    out: list[Node] = []
    for node in nodes:
        if out:
            merged = _try_merge(out[-1], node)
            if merged is not None:
                out[-1] = merged
                continue
        out.append(node)
    return tuple(out)


def _try_merge(a: Node, b: Node) -> Node | None:
    if isinstance(a, QualifiedRule) and isinstance(b, QualifiedRule):
        if selector_sig(a.prelude) == selector_sig(b.prelude):
            return QualifiedRule(a.prelude, structural_optimize(a.block + b.block))
        if tree_sig(a.block, normalize=False) == tree_sig(b.block, normalize=False):
            return QualifiedRule((*a.prelude, _COMMA, *b.prelude), a.block)
        return None
    if (
        isinstance(a, AtRule)
        and isinstance(b, AtRule)
        and a.block is not None
        and b.block is not None
        and a.name.lower() == b.name.lower()
        and selector_sig(a.prelude) == selector_sig(b.prelude)
    ):
        return AtRule(a.name, a.prelude, structural_optimize(a.block + b.block))
    return None
