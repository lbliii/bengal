"""Intra-stylesheet dead-code removal (opt-in).

Removes ``@keyframes``, ``@font-face``, and custom-property definitions that are
never referenced within the same stylesheet. References are discovered by
scanning declaration values (``animation`` / ``animation-name``, ``font-family``,
``var()``) — no HTML scan. Guarded at runtime by
:func:`~bengal.css.cascade.surviving_resolve_ok`.
"""

from dataclasses import dataclass

from bengal.css.nodes import AtRule, Declaration, Node, QualifiedRule
from bengal.css.tokens import Token, TokenType

_SKIP = (TokenType.WHITESPACE, TokenType.COMMENT)

_GENERIC_FAMILIES = frozenset(
    {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui"}
)

_ANIMATION_KEYWORDS = frozenset(
    {
        "inherit",
        "initial",
        "unset",
        "revert",
        "revert-layer",
        "none",
        "normal",
        "running",
        "paused",
        "linear",
        "ease",
        "ease-in",
        "ease-out",
        "ease-in-out",
        "infinite",
        "alternate",
        "alternate-reverse",
        "forwards",
        "backwards",
        "both",
        "step-start",
        "step-end",
    }
)


@dataclass(frozen=True, slots=True)
class _Definitions:
    keyframes: frozenset[str]
    font_faces: frozenset[str]
    custom_props: frozenset[str]


@dataclass(frozen=True, slots=True)
class _References:
    keyframes: frozenset[str]
    font_faces: frozenset[str]
    custom_props: frozenset[str]


def has_removable_dead_code(nodes: tuple[Node, ...]) -> bool:
    """Return whether the tree has provably unreferenced intra-sheet definitions."""
    defs = _collect_definitions(nodes)
    refs = _collect_references(nodes)
    return (
        bool(defs.keyframes - refs.keyframes)
        or bool(defs.font_faces - refs.font_faces)
        or bool(defs.custom_props - refs.custom_props)
    )


def remove_dead_code_tree(nodes: tuple[Node, ...]) -> tuple[Node, ...]:
    """Drop unreferenced @keyframes, @font-face, and custom-property definitions."""
    defs = _collect_definitions(nodes)
    refs = _collect_references(nodes)
    if not (
        defs.keyframes - refs.keyframes
        or defs.font_faces - refs.font_faces
        or defs.custom_props - refs.custom_props
    ):
        return nodes
    return _prune(nodes, defs, refs)


def _collect_definitions(nodes: tuple[Node, ...]) -> _Definitions:
    keyframes: set[str] = set()
    font_faces: set[str] = set()
    custom_props: set[str] = set()

    def walk(items: tuple[Node, ...]) -> None:
        for node in items:
            if isinstance(node, Declaration):
                if node.name.startswith("--"):
                    custom_props.add(node.name)
            elif isinstance(node, QualifiedRule):
                walk(node.block)
            elif isinstance(node, AtRule):
                name = node.name.lower()
                if name == "@keyframes":
                    kf = _keyframe_name(node.prelude)
                    if kf:
                        keyframes.add(kf)
                elif name == "@font-face" and node.block is not None:
                    for fam in _font_face_families(node.block):
                        font_faces.add(fam)
                if node.block is not None:
                    walk(node.block)

    walk(nodes)
    return _Definitions(
        frozenset(keyframes),
        frozenset(font_faces),
        frozenset(custom_props),
    )


def _collect_references(nodes: tuple[Node, ...]) -> _References:
    keyframes: set[str] = set()
    font_faces: set[str] = set()
    custom_props: set[str] = set()

    def walk(items: tuple[Node, ...], *, in_font_face: bool = False) -> None:
        for node in items:
            if isinstance(node, Declaration):
                prop = node.name.lower()
                if prop in ("animation", "animation-name"):
                    keyframes.update(_animation_name_idents(node.value))
                elif prop == "font-family" and not in_font_face:
                    font_faces.update(_font_families_from_value(node.value))
                custom_props.update(_var_refs(node.value))
            elif isinstance(node, QualifiedRule):
                walk(node.block)
            elif isinstance(node, AtRule):
                in_face = in_font_face or node.name.lower() == "@font-face"
                if node.block is not None:
                    walk(node.block, in_font_face=in_face)

    walk(nodes)
    return _References(
        frozenset(keyframes),
        frozenset(font_faces),
        frozenset(custom_props),
    )


def _prune(nodes: tuple[Node, ...], defs: _Definitions, refs: _References) -> tuple[Node, ...]:
    out: list[Node] = []
    for node in nodes:
        if isinstance(node, Declaration):
            if node.name.startswith("--") and node.name in defs.custom_props - refs.custom_props:
                continue
            out.append(node)
        elif isinstance(node, QualifiedRule):
            block = _prune(node.block, defs, refs)
            out.append(QualifiedRule(node.prelude, block))
        elif isinstance(node, AtRule):
            name = node.name.lower()
            if name == "@keyframes":
                kf = _keyframe_name(node.prelude)
                if kf and kf in defs.keyframes - refs.keyframes:
                    continue
            elif name == "@font-face" and node.block is not None:
                families = _font_face_families(node.block)
                if families and families <= defs.font_faces - refs.font_faces:
                    continue
            block = None if node.block is None else _prune(node.block, defs, refs)
            out.append(AtRule(node.name, node.prelude, block))
        else:
            out.append(node)
    return tuple(out)


def _keyframe_name(prelude: tuple[Token, ...]) -> str | None:
    for tok in prelude:
        if tok.type in _SKIP:
            continue
        if tok.type is TokenType.IDENT:
            return tok.value.lower()
        return None
    return None


def _font_face_families(block: tuple[Node, ...]) -> frozenset[str]:
    for node in block:
        if isinstance(node, Declaration) and node.name.lower() == "font-family":
            return frozenset(_font_families_from_value(node.value))
    return frozenset()


def _font_families_from_value(value: tuple[Token, ...]) -> set[str]:
    families: set[str] = set()
    for part in _split_comma_values(value):
        fam = _primary_family(part)
        if fam and fam.lower() not in _GENERIC_FAMILIES:
            families.add(fam.lower())
    return families


def _primary_family(part: tuple[Token, ...]) -> str | None:
    name_parts: list[str] = []
    for tok in part:
        if tok.type in _SKIP:
            continue
        if tok.type is TokenType.STRING:
            body = tok.value
            if len(body) >= 2 and body[0] in "\"'" and body[-1] == body[0]:
                return body[1:-1]
            return body
        if tok.type is TokenType.IDENT:
            name_parts.append(tok.value)
            continue
        if name_parts:
            break
    if name_parts:
        return " ".join(name_parts)
    return None


def _animation_name_idents(value: tuple[Token, ...]) -> set[str]:
    names: set[str] = set()
    for part in _split_comma_values(value):
        for tok in part:
            if tok.type is TokenType.IDENT and tok.value.lower() not in _ANIMATION_KEYWORDS:
                names.add(tok.value.lower())
    return names


def _var_refs(value: tuple[Token, ...]) -> set[str]:
    refs: set[str] = set()
    i = 0
    while i < len(value):
        tok = value[i]
        if tok.type is TokenType.FUNCTION and tok.value.lower() == "var":
            j = i + 1
            while j < len(value) and value[j].type in _SKIP:
                j += 1
            if (
                j < len(value)
                and value[j].type is TokenType.IDENT
                and value[j].value.startswith("--")
            ):
                refs.add(value[j].value)
            i += 1
            continue
        i += 1
    return refs


def _split_comma_values(value: tuple[Token, ...]) -> list[tuple[Token, ...]]:
    parts: list[list[Token]] = [[]]
    depth = 0
    for tok in value:
        if tok.type in _SKIP:
            continue
        if tok.type in (TokenType.LPAREN, TokenType.LBRACKET, TokenType.LBRACE, TokenType.FUNCTION):
            depth += 1
        elif tok.type in (TokenType.RPAREN, TokenType.RBRACKET, TokenType.RBRACE):
            depth = max(0, depth - 1)
        if depth == 0 and tok.type is TokenType.COMMA:
            parts.append([])
            continue
        parts[-1].append(tok)
    return [tuple(part) for part in parts if part]
