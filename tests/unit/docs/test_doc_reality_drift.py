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
import tomllib
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
    """The architecture CLI help snapshot must match ``pyproject.toml`` version."""
    version = tomllib.load((_REPO_ROOT / "pyproject.toml").open("rb"))["project"]["version"]
    doc = _DOCS / "reference" / "architecture" / "tooling" / "cli.md"
    text = doc.read_text(encoding="utf-8")
    assert f"bengal {version}" in text, (
        f"cli.md help snapshot missing shipped version `bengal {version}`"
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
