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

from bengal.health.remediation.autofix import AutoFixer, FixAction, FixSafety
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


def test_metadata_path_supports_more_than_five_broken_links(tmp_path):
    """Production-shaped Links results expose every broken link via metadata (#508)."""
    _build_content_tree(tmp_path)
    source = tmp_path / "content" / "docs" / "configuration.md"
    broken_links = [f"/docs/instalation-{index}/" for index in range(6)]
    _write(
        source,
        "# Configuration\n\n"
        + "\n".join(f"[link{i}]({link})" for i, link in enumerate(broken_links))
        + "\n",
    )

    for index in range(len(broken_links)):
        typo_page = tmp_path / "content" / "docs" / f"installation-{index}.md"
        _write(typo_page, f"# Installation {index}\n")

    result = CheckResult.error(
        "6 broken internal link(s)",
        code="H101",
        metadata={
            "source_path": str(source),
            "broken_links": broken_links,
        },
    )
    _report, fixer = _links_report(tmp_path, result)

    link_fixes = [fix for fix in fixer.suggest_fixes() if fix.fix_type == "link_update"]
    assert len(link_fixes) == 6


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


# ---------------------------------------------------------------------------
# Full apply-path coverage (issue #491 reviewer regression).
#
# The suggestion tests above call ``fix.apply()`` directly, which bypasses the
# ``can_apply()`` gate inside ``AutoFixer.apply_fixes()`` -- the *only* route the
# ``bengal fix`` CLI uses. Link fixes are emitted at FixSafety.CONFIRM, and
# ``can_apply()`` is True only for SAFE, so a confirmed CONFIRM link fix used to
# be counted "skipped" and its callable never invoked. These tests exercise the
# real apply path so a regression to that behavior fails here.
# ---------------------------------------------------------------------------


def _typo_fixer(tmp_path):
    """Build a fixer carrying exactly one CONFIRM link fix for a typo'd link."""
    _build_content_tree(tmp_path)
    source = tmp_path / "content" / "docs" / "configuration.md"
    _write(source, "# Configuration\n\nSee [install](/docs/instalation/).\n")

    result = CheckResult.error(
        "1 broken internal link(s)",
        code="H101",
        details=["content/docs/configuration.md: /docs/instalation/"],
    )
    _report, fixer = _links_report(tmp_path, result)
    fixer.suggest_fixes()
    return fixer, source


def test_confirmed_link_fix_applies_through_apply_fixes(tmp_path):
    """A confirmed CONFIRM link fix is applied (0->1) and rewrites the file.

    Discriminating: on the pre-fix code ``apply_fixes`` gates on ``can_apply()``
    (SAFE only), so this CONFIRM fix is *skipped* -- ``applied`` stays 0 and the
    file is unchanged. This is the exact reviewer-reproduced regression.
    """
    fixer, source = _typo_fixer(tmp_path)
    link_fixes = [f for f in fixer.fixes if f.fix_type == "link_update"]
    assert link_fixes, "fixture must produce a CONFIRM link fix"
    assert link_fixes[0].safety == FixSafety.CONFIRM

    results = fixer.apply_fixes(link_fixes, confirmed=True)

    assert results["applied"] == 1, results
    assert results["skipped"] == 0, results
    rewritten = source.read_text(encoding="utf-8")
    assert "/docs/installation/" in rewritten
    assert "/docs/instalation/" not in rewritten


def test_unconfirmed_link_fix_is_not_applied(tmp_path):
    """Without confirmation a CONFIRM link fix is skipped and the file is intact.

    This pins the safety model: CONFIRM fixes must NOT auto-apply. If
    ``apply_fixes`` ever applied CONFIRM fixes unconditionally this fails.
    """
    fixer, source = _typo_fixer(tmp_path)
    link_fixes = [f for f in fixer.fixes if f.fix_type == "link_update"]
    before = source.read_text(encoding="utf-8")

    results = fixer.apply_fixes(link_fixes)  # confirmed defaults to False

    assert results["applied"] == 0, results
    assert results["skipped"] == 1, results
    assert source.read_text(encoding="utf-8") == before


def test_safe_fix_still_auto_applies_without_confirmation(tmp_path):
    """A SAFE fix is applied through the unconfirmed path (no regression)."""
    _build_content_tree(tmp_path)
    source = tmp_path / "content" / "docs" / "configuration.md"
    _write(source, "# Configuration\n")
    marker = {"count": 0}

    def _apply():
        marker["count"] += 1
        return True

    _report, fixer = _links_report(tmp_path)
    safe_fix = FixAction(
        description="safe sentinel",
        file_path=source,
        fix_type="link_update",
        safety=FixSafety.SAFE,
        apply=_apply,
    )

    results = fixer.apply_fixes([safe_fix])

    assert results["applied"] == 1, results
    assert marker["count"] == 1


def test_unsafe_fix_never_applies_even_when_confirmed(tmp_path):
    """UNSAFE fixes require manual review; confirmed=True must NOT apply them."""
    _build_content_tree(tmp_path)
    source = tmp_path / "content" / "docs" / "configuration.md"
    _write(source, "# Configuration\n")
    marker = {"count": 0}

    def _apply():
        marker["count"] += 1
        return True

    _report, fixer = _links_report(tmp_path)
    unsafe_fix = FixAction(
        description="dangerous sentinel",
        file_path=source,
        fix_type="link_update",
        safety=FixSafety.UNSAFE,
        apply=_apply,
    )

    results = fixer.apply_fixes([unsafe_fix], confirmed=True)

    assert results["applied"] == 0, results
    assert results["skipped"] == 1, results
    assert marker["count"] == 0
