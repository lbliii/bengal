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
        "PageMetadataMixin",
        "PageContentMixin",
        "PageRelationshipsMixin",
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
