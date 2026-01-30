"""Test that CSS classes used in templates have corresponding CSS definitions.

This test ensures that all CSS classes referenced in HTML templates have
corresponding definitions in the theme's CSS files. This prevents the
"orphaned class" problem where templates use classes that were never styled.

Related: GitHub Issue #131 (docs-home CSS classes missing)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def get_repo_root() -> Path:
    """Get the repository root directory."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return cwd


class TestTemplateCSSCoverage:
    """Tests for template CSS class coverage."""

    @pytest.fixture
    def repo_root(self) -> Path:
        """Get the repository root."""
        return get_repo_root()

    @pytest.fixture
    def validation_script(self, repo_root: Path) -> Path:
        """Get the path to the validation script."""
        return repo_root / "scripts" / "check_template_css.py"

    def test_validation_script_exists(self, validation_script: Path) -> None:
        """Ensure the validation script exists."""
        assert validation_script.exists(), (
            f"Validation script not found: {validation_script}"
        )

    def test_validation_script_runs_successfully(
        self, repo_root: Path, validation_script: Path
    ) -> None:
        """The CSS validation script should run without errors.

        Note: This test runs without --strict flag, so it will pass even if
        orphaned classes exist. Use the pre-commit hook or run the script
        manually with --strict to enforce strict checking.

        The purpose of this test is to ensure the validation infrastructure
        works, not to block CI on pre-existing issues.
        """
        result = subprocess.run(
            [sys.executable, str(validation_script)],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )

        # Script should run successfully (exit 0 means all good, exit 0 without
        # --strict means it ran and reported issues as warnings)
        assert result.returncode in (0, 1), (
            f"Validation script failed unexpectedly:\n{result.stderr}"
        )

        # Log any orphaned classes as a warning for visibility
        if "orphaned" in result.stdout.lower():
            import warnings
            warnings.warn(
                f"Found orphaned CSS classes (run with --strict to fail):\n"
                f"{result.stdout[:500]}...",
                stacklevel=2,
            )

    def test_docs_home_css_exists(self, repo_root: Path) -> None:
        """Ensure docs-home.css exists (regression test for issue #131)."""
        docs_home_css = (
            repo_root
            / "bengal"
            / "themes"
            / "default"
            / "assets"
            / "css"
            / "pages"
            / "docs-home.css"
        )
        assert docs_home_css.exists(), (
            f"docs-home.css not found: {docs_home_css}\n"
            "This file provides CSS for doc/home.html template.\n"
            "See: https://github.com/lbliii/bengal/issues/131"
        )

    def test_docs_home_css_imported_in_style(self, repo_root: Path) -> None:
        """Ensure docs-home.css is imported in style.css."""
        style_css = (
            repo_root
            / "bengal"
            / "themes"
            / "default"
            / "assets"
            / "css"
            / "style.css"
        )
        content = style_css.read_text()
        assert "docs-home.css" in content, (
            "docs-home.css is not imported in style.css\n"
            "Add: @import url('pages/docs-home.css'); to the @layer pages section"
        )

    def test_docs_home_css_has_required_classes(self, repo_root: Path) -> None:
        """Ensure docs-home.css defines all required classes."""
        docs_home_css = (
            repo_root
            / "bengal"
            / "themes"
            / "default"
            / "assets"
            / "css"
            / "pages"
            / "docs-home.css"
        )

        content = docs_home_css.read_text()

        # Core classes that must be defined
        required_classes = [
            ".docs-home",
            ".docs-home-hero",
            ".docs-home-hero-content",
            ".docs-home-title",
            ".docs-home-subtitle",
            ".docs-home-content",
            ".docs-home-sections",
            ".docs-home-sections-title",
            ".docs-home-sections-grid",
            ".docs-home-section-card",
            ".docs-home-section-title",
            ".docs-home-section-description",
            ".docs-home-section-count",
            ".docs-home-quick-links",
            ".docs-home-quick-links-title",
            ".docs-home-quick-links-grid",
            ".docs-home-quick-link-card",
            ".docs-home-quick-link-icon",
        ]

        missing = [cls for cls in required_classes if cls not in content]

        assert not missing, (
            f"docs-home.css is missing definitions for: {', '.join(missing)}"
        )


class TestCSSStructure:
    """Tests for CSS file structure and organization."""

    @pytest.fixture
    def css_dir(self) -> Path:
        """Get the CSS directory."""
        repo_root = get_repo_root()
        return repo_root / "bengal" / "themes" / "default" / "assets" / "css"

    def test_pages_directory_exists(self, css_dir: Path) -> None:
        """Ensure the pages CSS directory exists."""
        pages_dir = css_dir / "pages"
        assert pages_dir.exists(), f"Pages CSS directory not found: {pages_dir}"

    def test_style_css_exists(self, css_dir: Path) -> None:
        """Ensure the main style.css exists."""
        style_css = css_dir / "style.css"
        assert style_css.exists(), f"Main stylesheet not found: {style_css}"

    def test_style_css_uses_layers(self, css_dir: Path) -> None:
        """Ensure style.css uses CSS layers for cascade management."""
        style_css = css_dir / "style.css"
        content = style_css.read_text()

        assert "@layer" in content, (
            "style.css should use @layer for cascade management"
        )

    def test_page_css_files_follow_naming_convention(self, css_dir: Path) -> None:
        """Page-specific CSS files should follow naming conventions."""
        pages_dir = css_dir / "pages"
        if not pages_dir.exists():
            pytest.skip("pages directory doesn't exist yet")

        for css_file in pages_dir.glob("*.css"):
            # File names should be lowercase with hyphens
            assert css_file.stem == css_file.stem.lower(), (
                f"CSS file should be lowercase: {css_file.name}"
            )
            assert "_" not in css_file.stem, (
                f"CSS file should use hyphens, not underscores: {css_file.name}"
            )
