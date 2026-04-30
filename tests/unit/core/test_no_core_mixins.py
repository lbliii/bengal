"""
Architectural guard: no new *Mixin classes in bengal/core/.

Domain types (Site, Page, Section) should not use inheritance-based composition.
The choice between "mixin split" and "inlined methods" becomes a bikeshed; the
orthogonal move is to treat vestigial forwarders as deletion candidates and
keep genuine domain logic inline.

History:
- 2026-04-06 (PR #194, d536880dc): 10+ commit campaign eliminated all Site mixins.
- Later: Sprint B3 of immutable-floating-sun.md re-introduced 5 Site mixins.
- 2026-04-20 (epic-delete-forwarding-wrappers.md S4): dissolved all Site mixins.

The epic explicitly targeted Site. Page and Section still have legacy mixins
(pre-dating the epic); they are allow-listed below and slated for a follow-up
audit using the same greenfield-design test.

This test pins the outcome: Site stays mixin-free; any NEW mixin added to
bengal/core/ fails CI.

See also:
- plan/epic-delete-forwarding-wrappers.md (S5.1)
- .claude/projects/.../memory/feedback_domain_facets_vs_vestiges.md
"""

from __future__ import annotations

import ast
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parents[3] / "bengal" / "core"

# Legacy mixins that pre-date epic-delete-forwarding-wrappers.md. Each entry
# should be removed (and the mixin dissolved) in a follow-up audit. New names
# must not be added without running the greenfield-design test first.
LEGACY_MIXINS: frozenset[str] = frozenset(
    {
        "SectionErgonomicsMixin",
        "SectionHierarchyMixin",
        "SectionQueryMixin",
        "SectionNavigationMixin",
    }
)


def _find_mixin_classes(core_dir: Path) -> list[tuple[Path, str, int]]:
    """Return (file, class_name, line) for every class in core_dir whose name ends in 'Mixin'."""
    hits: list[tuple[Path, str, int]] = []
    for py_file in core_dir.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        hits.extend(
            (py_file, node.name, node.lineno)
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name.endswith("Mixin")
        )
    return hits


def test_no_new_mixin_classes_in_bengal_core() -> None:
    assert CORE_DIR.exists(), f"Expected {CORE_DIR} to exist"

    hits = _find_mixin_classes(CORE_DIR)
    unexpected = [(p, n, ln) for p, n, ln in hits if n not in LEGACY_MIXINS]

    if unexpected:
        detail = "\n".join(
            f"  {path.relative_to(CORE_DIR.parent.parent)}:{line}  class {name}"
            for path, name, line in unexpected
        )
        raise AssertionError(
            "bengal/core/ must not contain new *Mixin classes. Found:\n"
            f"{detail}\n\n"
            "Domain types (Site, Page, Section) use inline methods or composed services, "
            "not mixin inheritance. Before adding a mixin, run the greenfield-design "
            "test: 'would I design this greenfield, naming it exactly this?' If no, "
            "it's a vestige — delete it. See plan/epic-delete-forwarding-wrappers.md."
        )


def test_site_remains_mixin_free() -> None:
    """Hard guard: no mixins in bengal/core/site/ (epic-delete-forwarding-wrappers S4)."""
    site_dir = CORE_DIR / "site"
    hits = _find_mixin_classes(site_dir)
    if hits:
        detail = "\n".join(
            f"  {path.relative_to(CORE_DIR.parent.parent)}:{line}  class {name}"
            for path, name, line in hits
        )
        raise AssertionError(
            "bengal/core/site/ must remain mixin-free. Found:\n"
            f"{detail}\n\n"
            "Site dissolved all 5 mixins in epic-delete-forwarding-wrappers S4 "
            "(2026-04-20). Do not re-introduce — see the epic and PR #194."
        )


def test_page_does_not_inherit_rendering_operations() -> None:
    """Page keeps rendering operations behind shims, not inheritance."""
    page_file = CORE_DIR / "page" / "__init__.py"
    tree = ast.parse(page_file.read_text(encoding="utf-8"))

    page_class = next(
        node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == "Page"
    )
    base_names = {
        base.id if isinstance(base, ast.Name) else base.attr
        for base in page_class.bases
        if isinstance(base, (ast.Name, ast.Attribute))
    }

    assert "PageOperationsMixin" not in base_names


def test_page_has_no_module_level_rendering_operations_import() -> None:
    """Core Page should not import rendering page operations at module import time."""
    page_file = CORE_DIR / "page" / "__init__.py"
    tree = ast.parse(page_file.read_text(encoding="utf-8"))

    imports = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "bengal.rendering.page_operations"
    ]

    assert imports == []


def test_page_does_not_inherit_content_mixin() -> None:
    """Page content access stays inline and delegates processing outward."""
    page_file = CORE_DIR / "page" / "__init__.py"
    tree = ast.parse(page_file.read_text(encoding="utf-8"))

    page_class = next(
        node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == "Page"
    )
    base_names = {
        base.id if isinstance(base, ast.Name) else base.attr
        for base in page_class.bases
        if isinstance(base, (ast.Name, ast.Attribute))
    }

    assert "PageContentMixin" not in base_names


def test_page_does_not_inherit_metadata_mixin() -> None:
    """Page metadata access is inline and delegates normalization to helpers."""
    page_file = CORE_DIR / "page" / "__init__.py"
    tree = ast.parse(page_file.read_text(encoding="utf-8"))

    page_class = next(
        node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == "Page"
    )
    base_names = {
        base.id if isinstance(base, ast.Name) else base.attr
        for base in page_class.bases
        if isinstance(base, (ast.Name, ast.Attribute))
    }

    assert "PageMetadataMixin" not in base_names


def test_page_does_not_inherit_relationships_mixin() -> None:
    """Page relationship helpers are inline compatibility methods."""
    page_file = CORE_DIR / "page" / "__init__.py"
    tree = ast.parse(page_file.read_text(encoding="utf-8"))

    page_class = next(
        node for node in ast.walk(tree) if isinstance(node, ast.ClassDef) and node.name == "Page"
    )
    base_names = {
        base.id if isinstance(base, ast.Name) else base.attr
        for base in page_class.bases
        if isinstance(base, (ast.Name, ast.Attribute))
    }

    assert "PageRelationshipsMixin" not in base_names


def test_page_computed_keeps_content_rendering_out_of_core() -> None:
    """Core Page computed helpers keep content rendering/parsing out of core."""
    computed_file = CORE_DIR / "page" / "computed.py"
    tree = ast.parse(computed_file.read_text(encoding="utf-8"))

    imported_modules: set[str] = set()
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)

    parser_imports = {
        module
        for module in imported_modules
        if module == "bengal.parsing" or module.startswith("bengal.parsing.")
    }
    assert parser_imports == set()
    assert "strip_html" not in imported_names
    assert "truncate_at_sentence" not in imported_names


def test_legacy_mixin_allowlist_is_accurate() -> None:
    """Shrink the allow-list as Page/Section mixins are dissolved."""
    hits = _find_mixin_classes(CORE_DIR)
    found_names = {n for _, n, _ in hits}
    stale = LEGACY_MIXINS - found_names
    if stale:
        raise AssertionError(
            f"LEGACY_MIXINS contains entries that no longer exist: {sorted(stale)}\n"
            "Remove them from the allow-list to keep the guard accurate."
        )
