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

The epic explicitly targeted Site. Page and Section mixins have since been
dissolved during the boundary cleanup work that followed it.

This test pins the outcome: Site, Page, and Section stay mixin-free, and any NEW
mixin added to bengal/core/ fails CI.

See also:
- plan/epic-delete-forwarding-wrappers.md (S5.1)
- .claude/projects/.../memory/feedback_domain_facets_vs_vestiges.md
"""

from __future__ import annotations

import ast
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parents[3] / "bengal" / "core"

#: The live, mutable runtime page object. The legacy ``Page`` class is gone; any
#: rendering-mixin regression would land here, not in the ``page/`` package root.
RUNTIME_PAGE_FILE = CORE_DIR / "page" / "runtime.py"
RUNTIME_PAGE_CLASS = "RuntimePage"

LEGACY_MIXINS: frozenset[str] = frozenset()


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


def _base_name(base: ast.expr) -> str:
    """Render a class-base expression node back to its dotted leaf name for matching."""
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    if isinstance(base, ast.Subscript):  # e.g. Generic[T]
        return _base_name(base.value)
    return ""


def _runtime_page_bases() -> list[str]:
    """Return the rendered base-class names of ``RuntimePage`` in ``runtime.py``.

    A non-empty result that includes a ``*Mixin`` name is the composition-over-
    inheritance regression this guard exists to catch.
    """
    tree = ast.parse(RUNTIME_PAGE_FILE.read_text(encoding="utf-8"))
    classdefs = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == RUNTIME_PAGE_CLASS
    ]
    assert classdefs, (
        f"{RUNTIME_PAGE_CLASS} not found in {RUNTIME_PAGE_FILE}. The guard tests below "
        "scan the live runtime page object; update them if it was renamed or moved."
    )
    bases: list[str] = []
    for classdef in classdefs:
        bases.extend(_base_name(base) for base in classdef.bases)
    return bases


def _runtime_page_mixin_bases() -> list[str]:
    """Return the ``*Mixin`` base classes ``RuntimePage`` inherits from (should be empty)."""
    return [name for name in _runtime_page_bases() if name.endswith("Mixin")]


def _module_level_rendering_imports(py_file: Path) -> list[tuple[str, int]]:
    """Return (module, line) for top-level ``from bengal.rendering[.x] import ...`` statements.

    Only statements at module scope (``tree.body``) count: the legitimate pattern
    is a deferred import inside a compatibility-shim method body, which a hoist to
    module scope would break -- and which this scan would then flag.
    """
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    return [
        (node.module, node.lineno)
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and (node.module == "bengal.rendering" or node.module.startswith("bengal.rendering."))
    ]


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


def test_runtime_page_does_not_inherit_rendering_operations() -> None:
    """The live ``RuntimePage`` must not inherit rendering behavior via a mixin base.

    Rendering operations (content, html, urls, link/shortcode extraction) live in
    ``bengal/rendering/`` and are reached through deferred imports inside
    compatibility-shim methods -- never inherited. This goes red if ``RuntimePage``
    re-acquires a ``*Mixin`` base.
    """
    mixin_bases = _runtime_page_mixin_bases()
    assert mixin_bases == [], (
        f"{RUNTIME_PAGE_CLASS} must not inherit from mixin bases; found: {mixin_bases}. "
        "Rendering behavior belongs behind deferred imports in compatibility shims, "
        "not inherited. See CLAUDE.md and plan/epic-delete-forwarding-wrappers.md."
    )


def test_page_package_root_defines_no_page_class() -> None:
    """The ``page/`` package root defines no concrete ``Page``/``RuntimePage`` class.

    The legacy mutable ``Page`` was removed from ``bengal/core/page/__init__.py``;
    the live object is ``RuntimePage`` in ``runtime.py`` (guarded separately above).
    This pins that the package root stays free of a re-introduced page class so the
    runtime-scanning guards remain the single source of truth.
    """
    page_file = CORE_DIR / "page" / "__init__.py"
    tree = ast.parse(page_file.read_text(encoding="utf-8"))

    page_classes = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name in {"Page", RUNTIME_PAGE_CLASS}
    ]
    assert page_classes == []


def test_page_has_no_module_level_rendering_helper_imports() -> None:
    """Core Page imports rendering helpers only inside compatibility-shim bodies.

    Scans both the package root (``__init__.py``) and the live ``RuntimePage``
    module (``runtime.py``). ``runtime.py`` reaches ``bengal.rendering.*`` for
    content/url/operation shims via deferred (in-method) imports; this goes red if
    any such import is hoisted to module scope.
    """
    page_init = CORE_DIR / "page" / "__init__.py"
    offenders = _module_level_rendering_imports(page_init) + _module_level_rendering_imports(
        RUNTIME_PAGE_FILE
    )

    assert offenders == [], (
        "Core Page modules must reach bengal.rendering.* only via deferred imports "
        f"inside compatibility shims. Found module-level imports: {offenders}. "
        "See CLAUDE.md (rendering behavior stays out of core Page)."
    )


def test_page_bundle_resource_io_stays_out_of_core() -> None:
    """Page bundle resource filesystem access belongs in rendering helpers."""
    bundle_file = CORE_DIR / "page" / "bundle.py"
    tree = ast.parse(bundle_file.read_text(encoding="utf-8"))
    filesystem_call_names = {
        "exists",
        "is_dir",
        "is_file",
        "iterdir",
        "read_bytes",
        "read_text",
        "stat",
    }

    hits = [
        (node.func.attr, node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in filesystem_call_names
    ]

    assert hits == []

    core_resource_imports = [
        (node.module, node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("bengal.core.resources")
    ]
    assert core_resource_imports == []


def test_section_has_no_module_level_rendering_helper_imports() -> None:
    """Core Section should import rendering helpers only inside compatibility shims."""
    section_dir = CORE_DIR / "section"
    imports: list[tuple[Path, str]] = []
    for section_file in section_dir.rglob("*.py"):
        tree = ast.parse(section_file.read_text(encoding="utf-8"))
        imports.extend(
            (section_file, node.module)
            for node in tree.body
            if isinstance(node, ast.ImportFrom)
            and node.module is not None
            and (node.module == "bengal.rendering" or node.module.startswith("bengal.rendering."))
        )

    assert imports == []


def test_runtime_page_does_not_inherit_content_mixin() -> None:
    """``RuntimePage`` must not inherit a ``ContentMixin`` (or any ``*Mixin``) base."""
    mixin_bases = _runtime_page_mixin_bases()
    assert mixin_bases == [], (
        f"{RUNTIME_PAGE_CLASS} must not inherit a content mixin (e.g. ContentMixin); "
        f"found mixin bases: {mixin_bases}."
    )


def test_runtime_page_does_not_inherit_metadata_mixin() -> None:
    """``RuntimePage`` must not inherit a ``MetadataMixin`` (or any ``*Mixin``) base."""
    mixin_bases = _runtime_page_mixin_bases()
    assert mixin_bases == [], (
        f"{RUNTIME_PAGE_CLASS} must not inherit a metadata mixin (e.g. MetadataMixin); "
        f"found mixin bases: {mixin_bases}."
    )


def test_runtime_page_does_not_inherit_relationships_mixin() -> None:
    """``RuntimePage`` must not inherit a ``RelationshipsMixin`` (or any ``*Mixin``) base."""
    mixin_bases = _runtime_page_mixin_bases()
    assert mixin_bases == [], (
        f"{RUNTIME_PAGE_CLASS} must not inherit a relationships mixin (e.g. RelationshipsMixin); "
        f"found mixin bases: {mixin_bases}."
    )


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


def test_legacy_mixin_allowlist_stays_empty() -> None:
    """Keep the legacy allow-list empty now that Page and Section mixins are dissolved."""
    hits = _find_mixin_classes(CORE_DIR)
    found_names = {n for _, n, _ in hits}
    stale = LEGACY_MIXINS - found_names
    if stale:
        raise AssertionError(
            f"LEGACY_MIXINS contains entries that no longer exist: {sorted(stale)}\n"
            "Remove them from the allow-list to keep the guard accurate."
        )
