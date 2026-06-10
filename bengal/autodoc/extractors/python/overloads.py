"""
@overload grouping for Python autodoc extraction.

Python's ``typing.overload`` produces several type-only stub definitions of the
same callable followed by a single concrete implementation. Extracted naively,
these become N+1 separate ``DocElement`` peers that all share one name (and, once
URLs are computed, one ``#name`` anchor -- an anchor collision).

:func:`collapse_overloads` folds each such group into ONE ``DocElement``:

- The implementation (the def WITHOUT ``@overload``) provides the canonical
  docstring/description and typed metadata; if there is no implementation (e.g.
  a ``.pyi``-style stub set), the last overload stub is used as the canonical
  carrier so no documentation is lost.
- All signature variants are recorded, in source order, on the canonical element:
  ``metadata['overload_signatures']`` (list of signature strings) and
  ``metadata['is_overloaded'] = True``.
- The redundant peers are dropped, leaving exactly one entry per overloaded name.

This runs BEFORE member-order sorting so ordering stays stable, and operates on
the assembled member list (not the per-method extraction loop), because grouping
needs to see all same-named definitions together.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.autodoc.base import DocElement


def _decorator_is_overload(decorator: str) -> bool:
    """
    True if a decorator string denotes ``typing.overload``.

    Matches both bare ``@overload`` and dotted forms such as
    ``@typing.overload`` / ``@t.overload`` by comparing the final attribute
    component. Decorators may carry a call suffix in rare cases; compare the
    bare attribute path only.
    """
    if not decorator:
        return False
    # Defensive: ignore any accidental call/whitespace noise.
    base = decorator.split("(", 1)[0].strip()
    return base.rsplit(".", 1)[-1] == "overload"


def _element_signature(el: DocElement) -> str:
    """Best-effort signature string for an element, for the variant list."""
    tm = el.typed_metadata
    sig = getattr(tm, "signature", None) if tm is not None else None
    if sig:
        return sig
    meta = el.metadata or {}
    return str(meta.get("signature", "") or "")


def _has_overload_decorator(el: DocElement) -> bool:
    """True if the element's captured decorators include ``overload``."""
    tm = el.typed_metadata
    decorators = getattr(tm, "decorators", None) if tm is not None else None
    if not decorators:
        decorators = el.metadata.get("decorators", ()) if el.metadata else ()
    return any(_decorator_is_overload(str(d)) for d in (decorators or ()))


def collapse_overloads(members: list[DocElement]) -> list[DocElement]:
    """
    Collapse ``@overload`` stub groups into single elements.

    Args:
        members: Assembled method/function DocElements (source order preserved).

    Returns:
        A new list with each overloaded name represented by exactly ONE element
        carrying all signature variants. Non-overloaded members pass through
        unchanged and in their original relative order. The collapsed element is
        placed at the position of the group's FIRST occurrence so source ordering
        stays stable.
    """
    if not members:
        return members

    # Identify names that have at least one @overload-decorated definition.
    overloaded_names: set[str] = set()
    for el in members:
        if _has_overload_decorator(el):
            overloaded_names.add(el.name)

    if not overloaded_names:
        return members

    # Group members of an overloaded name together (in source order). For names
    # that are NOT overloaded, emit them as-is.
    result: list[DocElement] = []
    seen_collapsed: set[str] = set()

    # Pre-group by name so we can choose a canonical carrier + collect variants.
    groups: dict[str, list[DocElement]] = {}
    for el in members:
        if el.name in overloaded_names:
            groups.setdefault(el.name, []).append(el)

    for el in members:
        if el.name not in overloaded_names:
            result.append(el)
            continue

        if el.name in seen_collapsed:
            # Redundant peer of an already-collapsed group; drop it.
            continue

        group = groups[el.name]
        seen_collapsed.add(el.name)

        # Canonical carrier: prefer the concrete implementation (the def WITHOUT
        # @overload). If every member is an overload stub, keep the LAST stub so
        # the most-recent (typically the broadest) docstring survives.
        impl = next((m for m in group if not _has_overload_decorator(m)), None)
        canonical = impl if impl is not None else group[-1]

        # Record all signature variants in source order, de-duplicating exact
        # repeats while preserving first-seen order (deterministic).
        variants: list[str] = []
        for m in group:
            sig = _element_signature(m)
            if sig and sig not in variants:
                variants.append(sig)

        canonical.metadata["is_overloaded"] = True
        canonical.metadata["overload_signatures"] = variants
        result.append(canonical)

    return result
