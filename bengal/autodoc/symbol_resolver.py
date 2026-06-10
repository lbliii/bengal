"""
Symbol name -> URL resolution for autodoc cross-references.

Provides a deterministic, read-only :class:`SymbolResolver` service that maps
documented symbol names (qualified or simple) to their rendered page ``href``.
This powers cross-reference linking in autodoc templates: return types, parameter
types, base classes, ``See Also`` targets, and docstring symbol references resolve
to linked symbol pages when a documented page exists, and degrade silently to plain
text otherwise (no broken links).

Design notes:
- The resolver is built ONCE after the full element tree is assembled and the
  per-element ``href`` values are computed (``compute_element_urls`` in
  ``page_builders.py``). It is immutable thereafter, making it safe to read
  concurrently during shard/thread-parallel rendering (epic #350).
- Resolution is deterministic. A qualified-name match wins. Otherwise a simple
  name is resolved ONLY when exactly one documented symbol carries that simple
  name; ambiguous simple names degrade to ``None`` (a wrong link is worse than no
  link). Candidate lists are sorted so the ambiguity check is stable.
- Names that don't resolve (stdlib, undocumented, builtins) return ``None`` so the
  caller renders plain text.

This service lives under ``bengal/autodoc/`` per the architecture boundary: it is
not attached to core ``Page``/``Section`` and adds no mixin to ``bengal/core/``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from bengal.autodoc.base import DocElement


def _strip_role_prefix(name: str) -> str:
    """
    Normalize a raw symbol token the way docstring role conversion does.

    Strips a leading ``~`` (Sphinx "short name" marker), surrounding whitespace,
    and inline-code backticks. Does NOT strip module prefixes here -- qualified
    name matching needs the full dotted path; the simple-name fallback strips the
    prefix separately.
    """
    name = name.strip()
    # Strip inline-code backticks if a docstring token was wrapped.
    if len(name) >= 2 and name.startswith("`") and name.endswith("`"):
        name = name[1:-1].strip()
    # Strip Sphinx short-name marker.
    if name.startswith("~"):
        name = name[1:]
    # Drop a trailing "()" that role conversion appends for :func:/:meth:.
    if name.endswith("()"):
        name = name[:-2]
    return name.strip()


class SymbolResolver:
    """
    Resolve documented symbol names to their rendered page URLs.

    Build via :meth:`from_elements` after element hrefs are computed. The instance
    is read-only after construction and safe to share across render threads.

    Attributes:
        _by_qualified: Exact qualified-name -> href.
        _by_simple: Simple name -> sorted list of qualified names sharing it.
    """

    __slots__ = ("_by_qualified", "_by_simple")

    def __init__(
        self,
        by_qualified: dict[str, str],
        by_simple: dict[str, list[str]],
    ) -> None:
        self._by_qualified = by_qualified
        self._by_simple = by_simple

    #: Element types that are rendered on their OWN page (vs. inline on an
    #: ancestor's page). Only these own a standalone URL; inline descendants
    #: resolve to ``{owner_page_href}#{simple_name}`` so links never 404.
    DEFAULT_PAGE_OWNER_TYPES = frozenset(
        {
            # Python: only modules get their own page (classes/functions/methods
            # render inline as cards on the module page).
            "module",
            # CLI: commands and groups each get a page.
            "command",
            "command-group",
            # OpenAPI: schemas and endpoints each get a page.
            "openapi_schema",
            "openapi_endpoint",
        }
    )

    @classmethod
    def from_elements(
        cls,
        elements: Iterable[DocElement],
        *,
        page_owner_types: frozenset[str] | None = None,
    ) -> SymbolResolver:
        """
        Build a resolver by walking the full element tree.

        A symbol resolves to a URL that actually exists. Elements whose
        ``element_type`` is in ``page_owner_types`` resolve to their own
        computed ``href``. Inline descendants (e.g. a Python class/method that
        renders on its module page) resolve to the NEAREST page-owning
        ancestor's href plus a ``#simple_name`` fragment, so xref links never
        point at a non-existent page.

        Elements with no resolvable page (no page-owning ancestor and not a page
        owner themselves) are skipped -- resolution returns None and the caller
        degrades to plain text.

        Args:
            elements: Top-level DocElements (modules, etc.).
            page_owner_types: Element types that get standalone pages. Defaults
                to :attr:`DEFAULT_PAGE_OWNER_TYPES`.

        Returns:
            An immutable SymbolResolver.
        """
        owners = page_owner_types if page_owner_types is not None else cls.DEFAULT_PAGE_OWNER_TYPES

        by_qualified: dict[str, str] = {}
        by_simple_set: dict[str, set[str]] = {}

        def _record(qualified: str | None, url: str | None) -> None:
            if not qualified or not url:
                return
            # First write wins; qualified names are unique in a well-formed tree.
            by_qualified.setdefault(qualified, url)
            simple = qualified.rsplit(".", 1)[-1]
            by_simple_set.setdefault(simple, set()).add(qualified)

        def _visit(el: DocElement, owner_href: str | None, anchor: str | None) -> None:
            qualified = getattr(el, "qualified_name", None)
            href = getattr(el, "href", None)
            element_type = getattr(el, "element_type", "")
            simple = qualified.rsplit(".", 1)[-1] if qualified else None

            child_anchor = anchor
            if element_type in owners and href:
                # This element owns its own page; descendants anchor onto it.
                owner_href = href
                child_anchor = None  # reset: top-level members anchor on this page
                _record(qualified, href)
            elif owner_href and qualified:
                # Inline element rendered on the owning page. Anchor onto the
                # HIGHEST inline ancestor (a card with a stable, unique id on the
                # page) rather than the deepest simple name -- method simple names
                # can collide with module-level function names, but the top-level
                # card name is unique within a page.
                if anchor is None:
                    child_anchor = simple
                _record(qualified, f"{owner_href}#{child_anchor}")
            # else: no page owner in scope yet -> not resolvable, skip.

            children = getattr(el, "children", None)
            if children:
                for child in children:
                    _visit(child, owner_href, child_anchor)

        for element in elements:
            _visit(element, None, None)

        # Freeze simple-name candidate lists in sorted order for deterministic
        # ambiguity resolution across rebuilds.
        by_simple = {name: sorted(qualifieds) for name, qualifieds in by_simple_set.items()}
        return cls(by_qualified, by_simple)

    def resolve(self, name: str | None) -> str | None:
        """
        Resolve a symbol name to its page href, or None.

        Resolution order:
          1. Exact qualified-name match.
          2. Simple-name match ONLY if exactly one documented symbol has that
             simple name (ambiguous -> None).

        Args:
            name: Raw symbol token (may carry ``~``, backticks, trailing ``()``,
                or a module prefix).

        Returns:
            The href string when resolvable, else None.
        """
        if not name:
            return None

        token = _strip_role_prefix(name)
        if not token:
            return None

        # 1. Exact qualified match.
        href = self._by_qualified.get(token)
        if href is not None:
            return href

        # 2. Simple-name fallback (deterministic, ambiguity-safe).
        simple = token.rsplit(".", 1)[-1]
        candidates = self._by_simple.get(simple)
        if candidates and len(candidates) == 1:
            return self._by_qualified.get(candidates[0])

        return None

    def __bool__(self) -> bool:
        return bool(self._by_qualified)
