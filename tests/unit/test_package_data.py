"""Tests to verify package-data configuration includes all required files.

This prevents regressions where template files exist in source but are
not included in PyPI distributions (see PR #129).

The issue: unit tests run against source code, so missing package-data
entries aren't caught until users install from PyPI and hit FileNotFoundError.

This test suite verifies that pyproject.toml package-data patterns cover
all template directories and bundled resources.
"""

from pathlib import Path

import pytest

# Root paths
REPO_ROOT = Path(__file__).parent.parent.parent
BENGAL_PKG = REPO_ROOT / "bengal"
PYPROJECT = REPO_ROOT / "pyproject.toml"


@pytest.fixture
def package_data_patterns() -> list[str]:
    """Extract package-data patterns from pyproject.toml."""
    content = PYPROJECT.read_text()
    # Find the bengal = [...] section under [tool.setuptools.package-data]
    in_package_data = False
    patterns = []
    for line in content.splitlines():
        if "[tool.setuptools.package-data]" in line:
            in_package_data = True
            continue
        if in_package_data:
            if line.startswith("[") and "package-data" not in line:
                break
            # Extract quoted patterns
            if '"' in line:
                start = line.index('"') + 1
                end = line.index('"', start)
                patterns.append(line[start:end])
    return patterns


class TestPackageDataCompleteness:
    """Verify all template directories are covered by package-data config."""

    def test_themes_covered(self, package_data_patterns: list[str]) -> None:
        """themes/**/* should be in package-data."""
        assert any("themes/**/*" in p for p in package_data_patterns), (
            "Missing themes/**/* in package-data"
        )

    def test_autodoc_templates_in_theme(self, package_data_patterns: list[str]) -> None:
        """Autodoc templates are in themes/**/* (Kida uses .html, not .jinja2)."""
        # Autodoc templates live in themes/default/templates/autodoc/
        # They're covered by the themes/**/* pattern
        assert any("themes/**/*" in p for p in package_data_patterns), (
            "Missing themes/**/* which covers autodoc templates"
        )

    def test_scaffolds_covered(self, package_data_patterns: list[str]) -> None:
        """scaffolds/**/* should be in package-data."""
        assert any("scaffolds/**/*" in p for p in package_data_patterns), (
            "Missing scaffolds/**/* in package-data"
        )

    def test_graph_templates_covered(self, package_data_patterns: list[str]) -> None:
        """analysis/graph/templates/**/* should be in package-data.

        Regression test for PR #129 - graph_visualizer.html was missing
        from PyPI distributions.
        """
        assert any("analysis/graph/templates" in p for p in package_data_patterns), (
            "Missing analysis/graph/templates in package-data. "
            "See PR #129 - this causes FileNotFoundError when installed from PyPI."
        )

    def test_py_typed_covered(self, package_data_patterns: list[str]) -> None:
        """py.typed marker should be in package-data."""
        assert any("py.typed" in p for p in package_data_patterns), (
            "Missing py.typed in package-data"
        )


class TestTemplateDirectoriesExist:
    """Verify template directories referenced in package-data actually exist."""

    def test_themes_directory_exists(self) -> None:
        """bengal/themes/ should exist with templates."""
        themes_dir = BENGAL_PKG / "themes"
        assert themes_dir.exists(), f"themes directory not found: {themes_dir}"
        # Should have at least the default theme
        default_theme = themes_dir / "default" / "templates"
        assert default_theme.exists(), f"default theme templates not found: {default_theme}"

    def test_autodoc_templates_in_theme_exist(self) -> None:
        """bengal/themes/default/templates/autodoc/ should exist with templates.

        Autodoc templates live in the default theme, not in a separate fallback
        directory. The theme's templates are always available as the template
        engine adds default theme as the final fallback in the search path.
        """
        autodoc_dir = BENGAL_PKG / "themes" / "default" / "templates" / "autodoc"
        assert autodoc_dir.exists(), f"autodoc templates not found: {autodoc_dir}"
        # Should have python, cli, and openapi subdirectories
        assert (autodoc_dir / "python").exists(), "Missing autodoc/python templates"
        assert (autodoc_dir / "cli").exists(), "Missing autodoc/cli templates"
        assert (autodoc_dir / "openapi").exists(), "Missing autodoc/openapi templates"

    def test_scaffolds_directory_exists(self) -> None:
        """bengal/scaffolds/ should exist."""
        scaffolds_dir = BENGAL_PKG / "scaffolds"
        assert scaffolds_dir.exists(), f"scaffolds directory not found: {scaffolds_dir}"

    def test_graph_visualizer_template_exists(self) -> None:
        """bengal/analysis/graph/templates/graph_visualizer.html should exist.

        Regression test for PR #129.
        """
        template = BENGAL_PKG / "analysis" / "graph" / "templates" / "graph_visualizer.html"
        assert template.exists(), (
            f"graph_visualizer.html not found: {template}. "
            "This template is required for knowledge graph visualization."
        )

    def test_py_typed_marker_exists(self) -> None:
        """bengal/py.typed should exist for type checker support."""
        py_typed = BENGAL_PKG / "py.typed"
        assert py_typed.exists(), f"py.typed marker not found: {py_typed}"


class TestNoUnpackagedTemplates:
    """Detect template directories that might be missing from package-data."""

    def test_all_template_dirs_are_packaged(self, package_data_patterns: list[str]) -> None:
        """Find any templates/ directories not covered by package-data.

        This test scans for 'templates' directories in the bengal package
        and verifies each is covered by a package-data glob pattern.
        """
        # Find all templates directories
        template_dirs = list(BENGAL_PKG.rglob("templates"))
        template_dirs = [d for d in template_dirs if d.is_dir()]

        # Check each is covered by a pattern
        uncovered = []
        for tdir in template_dirs:
            rel_path = tdir.relative_to(BENGAL_PKG)
            # Check if any pattern covers this path
            covered = False
            for pattern in package_data_patterns:
                # Simple check: the pattern's base path should match
                pattern_base = pattern.split("**")[0].rstrip("/")
                if pattern_base and str(rel_path).startswith(pattern_base):
                    covered = True
                    break
                # themes/**/* covers themes/default/templates
                if "themes/**/*" in pattern and str(rel_path).startswith("themes"):
                    covered = True
                    break
            if not covered:
                uncovered.append(str(rel_path))

        assert not uncovered, (
            f"Template directories not covered by package-data: {uncovered}. "
            "Add appropriate patterns to [tool.setuptools.package-data] in pyproject.toml"
        )
