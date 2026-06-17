"""
CSS manifest coverage guard for the default theme.

Every component imported by style.css must appear in css_manifest.py so
tree-shaking never silently drops shipped styles.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

THEME_CSS = Path(__file__).resolve().parents[3] / "bengal" / "themes" / "default" / "assets" / "css"
STYLE_CSS = THEME_CSS / "style.css"

# Paths that style.css imports but are intentionally outside the manifest
# (third-party bundles referenced by feature keys, not component files).
MANIFEST_EXEMPT = frozenset({"tabulator.min.css"})

IMPORT_RE = re.compile(r"""@import\s+url\(['"]([^'"]+)['"]\)""")


def _style_css_imports() -> list[str]:
    text = STYLE_CSS.read_text(encoding="utf-8")
    return IMPORT_RE.findall(text)


def _manifest_paths() -> set[str]:
    from bengal.themes.default.css_manifest import (
        CSS_CORE,
        CSS_EXPERIMENTAL,
        CSS_FEATURE_MAP,
        CSS_PALETTES,
        CSS_SHARED,
        CSS_TYPE_MAP,
    )

    paths: set[str] = set()
    paths.update(CSS_CORE)
    paths.update(CSS_SHARED)
    paths.update(CSS_PALETTES)
    paths.update(CSS_EXPERIMENTAL)
    for files in CSS_TYPE_MAP.values():
        paths.update(files)
    for files in CSS_FEATURE_MAP.values():
        paths.update(files)
    return paths


def test_style_css_imports_are_in_manifest() -> None:
    """Every @import in style.css must be covered by css_manifest.py."""
    manifest = _manifest_paths()
    orphans = [p for p in _style_css_imports() if p not in manifest and p not in MANIFEST_EXEMPT]
    assert not orphans, (
        "style.css imports not covered by css_manifest.py "
        f"(add to the appropriate manifest category): {sorted(orphans)}"
    )


def test_manifest_coverage_guard_detects_planted_orphan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Guard must fail when a style.css import is missing from the manifest."""
    fake_style = tmp_path / "style.css"
    fake_style.write_text("@import url('components/planted-orphan.css');\n", encoding="utf-8")

    def fake_imports() -> list[str]:
        return ["components/planted-orphan.css"]

    monkeypatch.setattr(
        "tests.unit.themes.test_css_manifest_coverage._style_css_imports",
        fake_imports,
    )
    manifest = _manifest_paths()
    orphans = [p for p in fake_imports() if p not in manifest and p not in MANIFEST_EXEMPT]
    assert orphans == ["components/planted-orphan.css"]
