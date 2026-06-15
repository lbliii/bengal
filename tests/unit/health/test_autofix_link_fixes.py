"""
Broken-link autofix suggestions for the Links validator (issue #491).

``AutoFixer._suggest_link_fixes`` used to be a hard-coded ``return []`` despite a
docstring promising typo / moved-page / anchor fixes. These tests pin the real
behavior: for a broken *internal* link reported by the Links validator, the
fixer must emit a concrete ``FixAction`` that rewrites the link to a valid
target, and the produced ``apply`` callable must actually rewrite the source.

Every "non-empty" assertion here is discriminating: if the method body regresses
to ``return []`` (or stops matching), the lists go empty and the asserts fail.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bengal.health.remediation.autofix import AutoFixer, FixSafety
from bengal.health.report import CheckResult, HealthReport, ValidatorReport

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_content_tree(root: Path) -> None:
    """A small but realistic content tree used as the valid-URL corpus."""
    content = root / "content"
    _write(content / "_index.md", "# Home\n")
    _write(
        content / "docs" / "installation.md",
        "# Installation\n\n## Getting Started\n\nbody\n",
    )
    _write(content / "docs" / "configuration.md", "# Configuration\n")
    # A page that lives under guides/ -- its slug ('configuration') also exists
    # under docs/, so a moved-page suggestion must stay unambiguous: we make the
    # broken-link slug unique to one location below.
    _write(content / "guides" / "deployment.md", "# Deployment\n")


def _links_report(root: Path, *results: CheckResult) -> tuple[HealthReport, AutoFixer]:
    vr = ValidatorReport(validator_name="Links", results=list(results))
    report = HealthReport(validator_reports=[vr])
    return report, AutoFixer(report, site_root=root)


def test_typo_link_produces_real_fix_action(tmp_path):
    """A one-edit typo in an internal link path yields a rewrite FixAction.

    Discriminating: with ``return []`` the suggestions list is empty and this
    fails. The link ``/docs/instalation/`` is one edit from the real page
    ``/docs/installation/``.
    """
    _build_content_tree(tmp_path)
    source = tmp_path / "content" / "docs" / "configuration.md"
    _write(source, "# Configuration\n\nSee [install](/docs/instalation/).\n")

    result = CheckResult.error(
        "1 broken internal link(s)",
        code="H101",
        details=["content/docs/configuration.md: /docs/instalation/"],
    )
    _report, fixer = _links_report(tmp_path, result)

    fixes = fixer.suggest_fixes()
    link_fixes = [f for f in fixes if f.fix_type == "link_update"]

    assert link_fixes, "expected a broken-link FixAction (regression to [] fails here)"
    fix = link_fixes[0]
    assert fix.safety == FixSafety.CONFIRM
    assert "/docs/installation/" in fix.description
    assert fix.file_path == source
    assert fix.check_result is result


def test_typo_fix_apply_rewrites_the_source_link(tmp_path):
    """The produced ``apply`` callable rewrites the broken link in the file."""
    _build_content_tree(tmp_path)
    source = tmp_path / "content" / "docs" / "configuration.md"
    body = "# Configuration\n\nSee [install](/docs/instalation/).\n"
    _write(source, body)

    result = CheckResult.error(
        "1 broken internal link(s)",
        code="H101",
        details=["content/docs/configuration.md: /docs/instalation/"],
    )
    _report, fixer = _links_report(tmp_path, result)

    fix = next(f for f in fixer.suggest_fixes() if f.fix_type == "link_update")
    assert fix.apply() is True

    rewritten = source.read_text(encoding="utf-8")
    assert "/docs/installation/" in rewritten
    assert "/docs/instalation/" not in rewritten
    # Surrounding prose is untouched.
    assert rewritten.startswith("# Configuration")


def test_moved_page_uses_unique_slug_match(tmp_path):
    """A link whose slug exists at exactly one *other* path is re-pointed there.

    ``/old/deployment/`` does not exist, but ``deployment`` lives uniquely at
    ``/guides/deployment/``, so the fixer suggests the moved path.
    """
    _build_content_tree(tmp_path)
    source = tmp_path / "content" / "docs" / "configuration.md"
    _write(source, "# Configuration\n\nSee [deploy](/old/deployment/).\n")

    result = CheckResult.error(
        "1 broken internal link(s)",
        code="H101",
        metadata={
            "source_path": str(source),
            "broken_links": ["/old/deployment/"],
        },
    )
    _report, fixer = _links_report(tmp_path, result)

    link_fixes = [f for f in fixer.suggest_fixes() if f.fix_type == "link_update"]
    assert link_fixes, "expected a moved-page FixAction"
    assert "/guides/deployment/" in link_fixes[0].description
    assert "moved-page" in link_fixes[0].description


def test_anchor_fix_suggests_closest_heading(tmp_path):
    """A valid page with a bad ``#fragment`` gets the closest heading anchor.

    ``/docs/installation/`` exists and has a "## Getting Started" heading
    (slug ``getting-started``); the broken ``#getting-startd`` is corrected.
    """
    _build_content_tree(tmp_path)
    source = tmp_path / "content" / "docs" / "configuration.md"
    _write(source, "# Configuration\n\n[start](/docs/installation/#getting-startd)\n")

    result = CheckResult.error(
        "1 broken internal link(s)",
        code="H101",
        details=["content/docs/configuration.md: /docs/installation/#getting-startd"],
    )
    _report, fixer = _links_report(tmp_path, result)

    link_fixes = [f for f in fixer.suggest_fixes() if f.fix_type == "link_update"]
    assert link_fixes, "expected an anchor FixAction"
    fix = link_fixes[0]
    assert "#getting-started" in fix.description
    assert "anchor" in fix.description

    assert fix.apply() is True
    assert "#getting-started" in source.read_text(encoding="utf-8")


def test_external_links_are_not_suggested(tmp_path):
    """External links are out of scope and produce no FixActions."""
    _build_content_tree(tmp_path)
    source = tmp_path / "content" / "docs" / "configuration.md"
    _write(source, "# Configuration\n")

    result = CheckResult.warning(
        "1 broken external link(s)",
        code="H102",
        details=["content/docs/configuration.md: https://example.invalid/missing"],
    )
    _report, fixer = _links_report(tmp_path, result)

    assert [f for f in fixer.suggest_fixes() if f.fix_type == "link_update"] == []


def test_unfixable_link_yields_no_suggestion(tmp_path):
    """A link with no close valid target produces no (misleading) suggestion."""
    _build_content_tree(tmp_path)
    source = tmp_path / "content" / "docs" / "configuration.md"
    _write(source, "# Configuration\n")

    result = CheckResult.error(
        "1 broken internal link(s)",
        code="H101",
        details=["content/docs/configuration.md: /this/path/is/totally/unrelated/"],
    )
    _report, fixer = _links_report(tmp_path, result)

    assert [f for f in fixer.suggest_fixes() if f.fix_type == "link_update"] == []
