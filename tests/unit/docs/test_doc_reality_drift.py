"""CI guard: docs must describe the real, on-HEAD product surface (issue #474).

A 2026-06 docs-reality sweep found four classes of drift in
``site/content/docs`` (and the shared ``site/content/_snippets`` tree) that
would actively mislead a reader who copy-pasted the example:

1. ``base_url`` — the real Bengal config key is ``baseurl``
   (see ``bengal/config/accessor.py``: ``SiteConfig.baseurl``). Snippets that
   set ``base_url`` in a ``bengal.toml``/``[site]`` context silently no-op.
2. ``0.1.10`` — a long-gone version string used in install/verify examples
   and as a pinned-version sample. The current release is ``0.4.1``.
3. ``Jinja2`` named as *the* template engine in error-code docs — Bengal's
   default engine is Kida.
4. Phantom ``bengal/core/page`` modules (``content.py`` /
   ``relationships.py``) that do not exist on disk.

These assertions are intentionally narrow: each fails on the pre-fix docs and
passes once the corresponding drift is corrected, and each would fail again if
the drift were re-introduced.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

# tests/unit/docs/ -> repo root is three parents up.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTENT = _REPO_ROOT / "site" / "content"
_DOCS = _CONTENT / "docs"


def _markdown_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.md"))


def test_no_base_url_config_key_in_bengal_docs() -> None:
    """The real config key is ``baseurl``; ``base_url`` must not appear in docs.

    Pages that legitimately discuss an *external* API's ``base_url`` (e.g. the
    migration tutorials' OpenAPI examples) are exempted by listing them here,
    so the guard still catches a stray Bengal-config ``base_url``. Release-notes
    / changelog pages under ``releases/`` are also exempt: they describe the
    drift fix itself and so legitimately mention the old ``base_url`` spelling
    (mirrors the historical-version exemption in the ``0.1.10`` guard below).
    """
    # Files where ``base_url`` refers to a third-party API config, not Bengal's.
    exempt = {
        _DOCS / "content" / "authoring" / "external-references.md",
    }
    releases = _CONTENT / "releases"
    offenders: dict[str, list[int]] = {}
    for path in _markdown_files(_CONTENT):
        if path in exempt or path.is_relative_to(releases):
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "base_url" in line:
                offenders.setdefault(str(path.relative_to(_REPO_ROOT)), []).append(lineno)

    assert not offenders, (
        "Docs use the non-existent `base_url` config key (real key is `baseurl`):\n"
        + "\n".join(f"  {p}: lines {ls}" for p, ls in sorted(offenders.items()))
    )


def test_no_stale_0_1_10_version_string_in_docs() -> None:
    """The stale ``0.1.10`` version string must not appear in the docs tree.

    Release-notes / changelog history pages legitimately reference historical
    versions; this guard covers the prose docs tree, not those archives.
    """
    offenders: dict[str, list[int]] = {}
    for path in _markdown_files(_DOCS):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "0.1.10" in line:
                offenders.setdefault(str(path.relative_to(_REPO_ROOT)), []).append(lineno)

    assert not offenders, "Docs reference the stale version `0.1.10`:\n" + "\n".join(
        f"  {p}: lines {ls}" for p, ls in sorted(offenders.items())
    )


def test_error_code_docs_name_kida_not_jinja2() -> None:
    """Error-code docs must name Kida (the default engine), not Jinja2."""
    targets = (
        _DOCS / "reference" / "errors" / "_index.md",
        _DOCS / "reference" / "errors" / "health-codes.md",
    )
    offenders: dict[str, list[int]] = {}
    for path in targets:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "Jinja2" in line:
                offenders.setdefault(str(path.relative_to(_REPO_ROOT)), []).append(lineno)

    assert not offenders, (
        "Error-code docs name Jinja2; Bengal's default engine is Kida:\n"
        + "\n".join(f"  {p}: lines {ls}" for p, ls in sorted(offenders.items()))
    )


def test_object_model_lists_only_real_core_page_modules() -> None:
    """The object-model doc must not list phantom ``bengal/core/page`` modules."""
    doc = _DOCS / "reference" / "architecture" / "core" / "object-model.md"
    page_dir = _REPO_ROOT / "bengal" / "core" / "page"
    real_modules = {p.name for p in page_dir.glob("*.py")}

    text = doc.read_text(encoding="utf-8")
    cited = set(re.findall(r"`([a-z_]+\.py)`", text))
    phantom = {"content.py", "relationships.py"}
    assert not (cited & phantom), (
        f"object-model.md cites phantom core/page modules {sorted(cited & phantom)}; "
        f"real modules are {sorted(real_modules)}"
    )


def test_no_bengal_ssg_package_name_in_docs() -> None:
    """The PyPI package is ``bengal``, not the retired ``bengal-ssg`` name."""
    offenders: dict[str, list[int]] = {}
    for path in _markdown_files(_DOCS):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "bengal-ssg" in line:
                offenders.setdefault(str(path.relative_to(_REPO_ROOT)), []).append(lineno)

    assert not offenders, (
        "Docs reference the wrong PyPI package `bengal-ssg` (use `bengal`):\n"
        + "\n".join(f"  {p}: lines {ls}" for p, ls in sorted(offenders.items()))
    )


def test_architecture_cli_doc_matches_shipped_version() -> None:
    """The architecture CLI help snapshot is version-agnostic; stale versions must not linger."""
    doc = _DOCS / "reference" / "architecture" / "tooling" / "cli.md"
    text = doc.read_text(encoding="utf-8")
    assert "bengal VERSION" in text, (
        "cli.md root help snapshot should use the normalized `bengal VERSION` placeholder. "
        "Regenerate with: python scripts/update_cli_help_snapshot.py"
    )
    known_stale = ("0.3.3", "0.3.2", "0.3.1", "0.3.0")
    embedded = re.findall(r"^bengal (\d+\.\d+\.\d+)", text, flags=re.MULTILINE)
    stale_hits = [v for v in embedded if v in known_stale]
    assert not stale_hits, f"cli.md still embeds stale CLI version(s): {stale_hits}"


_HUB_PAGES = (
    _DOCS / "_index.md",
    _DOCS / "about" / "_index.md",
    _DOCS / "get-started" / "_index.md",
    _DOCS / "content" / "_index.md",
    _DOCS / "theming" / "_index.md",
    _DOCS / "extending" / "_index.md",
    _DOCS / "building" / "_index.md",
    _DOCS / "tutorials" / "_index.md",
    _DOCS / "reference" / "_index.md",
)


def test_hub_pages_do_not_reference_phantom_cli_section() -> None:
    """Hub pages must not link to a non-existent top-level ``/cli/`` section."""
    offenders: dict[str, list[int]] = {}
    for path in _HUB_PAGES:
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\[\[cli[\]|/cli/]", line):
                offenders.setdefault(str(path.relative_to(_REPO_ROOT)), []).append(lineno)

    assert not offenders, (
        "Hub pages link to phantom `/cli/` section; use docs/reference/architecture/tooling/cli:\n"
        + "\n".join(f"  {p}: lines {ls}" for p, ls in sorted(offenders.items()))
    )


def test_deploy_production_snippet_is_tracked_in_git() -> None:
    """Production build snippet must not live under a gitignored ``build/`` path."""
    snippet = _REPO_ROOT / "site" / "content" / "_snippets" / "deploy" / "production-build.md"
    assert snippet.is_file(), f"Missing deploy snippet at {snippet.relative_to(_REPO_ROOT)}"
    # git ls-files returns empty when ignored or untracked
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(snippet.relative_to(_REPO_ROOT))],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert tracked.returncode == 0, (
        "Deploy production-build snippet is not tracked by git "
        "(check site/.gitignore for overly broad rules)"
    )


def test_no_phantom_health_linkcheck_subcommand_in_docs() -> None:
    """``bengal health`` is a legacy ``check`` alias; link checks use ``inspect links``."""
    versions = _CONTENT / "_versions"
    offenders: dict[str, list[int]] = {}
    for path in _markdown_files(_DOCS):
        if path.is_relative_to(versions):
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "health linkcheck" in line:
                offenders.setdefault(str(path.relative_to(_REPO_ROOT)), []).append(lineno)

    assert not offenders, (
        "Docs reference phantom `bengal health linkcheck`; use `bengal inspect links` or `bengal check`:\n"
        + "\n".join(f"  {p}: lines {ls}" for p, ls in sorted(offenders.items()))
    )


def test_cli_command_inventory_matches_registry() -> None:
    """Committed cli.md inventory must match the live Milo command registry."""
    from tests._testing.cli_help_snapshot import (
        parse_cli_doc_inventory,
        registered_command_inventory,
    )

    doc = _DOCS / "reference" / "architecture" / "tooling" / "cli.md"
    doc_inventory = parse_cli_doc_inventory(doc.read_text(encoding="utf-8"))
    registered = registered_command_inventory()
    assert doc_inventory == registered, (
        "cli.md command inventory drifted from Milo registry.\n"
        "Regenerate with: python scripts/update_cli_help_snapshot.py\n"
        f"  doc-only: {sorted(set(doc_inventory) - set(registered))}\n"
        f"  registry-only: {sorted(set(registered) - set(doc_inventory))}"
    )


def test_cli_root_help_snapshot_matches_live_output() -> None:
    """Committed CLI help snapshot must match live root help command sections."""
    from tests._testing.cli_help_snapshot import (
        capture_root_help_command_sections,
        snapshot_path,
    )

    snapshot = snapshot_path()
    assert snapshot.is_file(), (
        f"Missing CLI help snapshot at {snapshot.relative_to(_REPO_ROOT)}. "
        "Generate with: python scripts/update_cli_help_snapshot.py"
    )
    expected = snapshot.read_text(encoding="utf-8")
    live = capture_root_help_command_sections()
    assert live == expected, (
        "CLI root help snapshot drifted from live Milo output.\n"
        "Regenerate with: python scripts/update_cli_help_snapshot.py"
    )


def test_architecture_cli_doc_root_help_matches_snapshot() -> None:
    """Embedded cli.md help block must match the committed CLI help snapshot."""
    from tests._testing.cli_help_snapshot import parse_cli_doc_root_help, snapshot_path

    doc = _DOCS / "reference" / "architecture" / "tooling" / "cli.md"
    doc_help = parse_cli_doc_root_help(doc.read_text(encoding="utf-8"))
    expected = snapshot_path().read_text(encoding="utf-8")
    assert doc_help == expected, (
        "cli.md root help block drifted from committed snapshot.\n"
        "Regenerate with: python scripts/update_cli_help_snapshot.py"
    )


def test_directive_option_tables_match_registry() -> None:
    """Committed directive option snapshot must match create_default_registry()."""
    from tests._testing.directive_options_snapshot import (
        load_snapshot,
        registry_option_tables,
        snapshot_path,
    )

    snapshot = snapshot_path()
    assert snapshot.is_file(), (
        f"Missing directive options snapshot at {snapshot.relative_to(_REPO_ROOT)}. "
        "Generate with: python scripts/update_directive_options_snapshot.py"
    )
    expected = load_snapshot()
    live = registry_option_tables()
    assert live == expected, (
        "Directive option tables drifted from registry.\n"
        "Regenerate with: python scripts/update_directive_options_snapshot.py"
    )
