"""
Integration tests for autodoc HTML page generation.

Verifies that all autodoc types (Python API, CLI, OpenAPI) generate
HTML pages at every navigation level with correct page types.
Requires pre-built site (bengal build). Excluded from PR integration.

These tests ensure:
1. Every autodoc section directory has an index.html file
2. Every module/command page has proper HTML output
3. Page types are correctly set for nav tree rendering
4. No missing HTML files after a clean build
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.autodoc


@pytest.fixture
def built_site_output() -> Path:
    """Return the built site output directory."""
    site_output = Path(__file__).parents[2] / "site" / "public"
    if not site_output.exists():
        pytest.skip("Site not built. Run 'bengal build' first.")
    return site_output


class TestAutodocHTMLGeneration:
    """Test that all autodoc pages generate HTML files."""

    def test_all_python_api_directories_have_html(self, built_site_output: Path) -> None:
        """Every Python API directory should have index.html."""
        api_dir = built_site_output / "api" / "bengal"
        if not api_dir.exists():
            pytest.skip("api/bengal directory not found")

        missing_html: list[str] = []
        for dir_path in api_dir.rglob("*"):
            if dir_path.is_dir():
                index_html = dir_path / "index.html"
                if not index_html.exists():
                    missing_html.append(str(dir_path.relative_to(built_site_output)))

        assert not missing_html, (
            "Python API directories missing index.html:\n"
            + "\n".join(f"  - {p}" for p in missing_html[:10])
            + (f"\n  ... and {len(missing_html) - 10} more" if len(missing_html) > 10 else "")
        )

    def test_all_cli_directories_have_html(self, built_site_output: Path) -> None:
        """Every CLI directory should have index.html."""
        cli_dir = built_site_output / "cli"
        if not cli_dir.exists():
            pytest.skip("cli directory not found")

        missing_html: list[str] = []
        for dir_path in cli_dir.rglob("*"):
            if dir_path.is_dir():
                index_html = dir_path / "index.html"
                if not index_html.exists():
                    missing_html.append(str(dir_path.relative_to(built_site_output)))

        assert not missing_html, (
            "CLI directories missing index.html:\n"
            + "\n".join(f"  - {p}" for p in missing_html[:10])
            + (f"\n  ... and {len(missing_html) - 10} more" if len(missing_html) > 10 else "")
        )

    def test_python_api_html_file_count_matches_txt(self, built_site_output: Path) -> None:
        """Python API should have equal HTML and TXT files (1:1 ratio)."""
        api_dir = built_site_output / "api" / "bengal"
        if not api_dir.exists():
            pytest.skip("api/bengal directory not found")

        html_count = len(list(api_dir.rglob("*.html")))
        txt_count = len(list(api_dir.rglob("*.txt")))

        assert html_count == txt_count, (
            f"Mismatch: {html_count} HTML files vs {txt_count} TXT files. "
            f"Every autodoc page should have both."
        )

    def test_cli_html_file_count_matches_txt(self, built_site_output: Path) -> None:
        """CLI should have equal HTML and TXT files (1:1 ratio)."""
        cli_dir = built_site_output / "cli"
        if not cli_dir.exists():
            pytest.skip("cli directory not found")

        html_count = len(list(cli_dir.rglob("*.html")))
        txt_count = len(list(cli_dir.rglob("*.txt")))

        assert html_count == txt_count, (
            f"Mismatch: {html_count} HTML files vs {txt_count} TXT files. "
            f"Every autodoc page should have both."
        )


class TestAutodocPageTypes:
    """Test that autodoc pages have correct data-type attributes."""

    def test_python_api_pages_have_correct_type(self, built_site_output: Path) -> None:
        """Python API pages should have data-type='autodoc-python'."""
        api_dir = built_site_output / "api" / "bengal"
        if not api_dir.exists():
            pytest.skip("api/bengal directory not found")

        # Check a sample of pages
        sample_pages = [
            api_dir / "index.html",
            api_dir / "core" / "index.html" if (api_dir / "core").exists() else None,
            api_dir / "cli" / "index.html" if (api_dir / "cli").exists() else None,
        ]

        for page_path in sample_pages:
            if page_path is None or not page_path.exists():
                continue

            html = page_path.read_text()
            assert 'data-type="autodoc-python"' in html, (
                f"Page {page_path.relative_to(built_site_output)} "
                f"missing data-type='autodoc-python' attribute"
            )

    def test_cli_pages_have_correct_type(self, built_site_output: Path) -> None:
        """CLI pages should have data-type='autodoc-cli'."""
        cli_dir = built_site_output / "cli"
        if not cli_dir.exists():
            pytest.skip("cli directory not found")

        # Check a sample of pages
        sample_pages = [
            cli_dir / "index.html",
            cli_dir / "build" / "index.html" if (cli_dir / "build").exists() else None,
            cli_dir / "serve" / "index.html" if (cli_dir / "serve").exists() else None,
        ]

        for page_path in sample_pages:
            if page_path is None or not page_path.exists():
                continue

            html = page_path.read_text()
            assert 'data-type="autodoc-cli"' in html, (
                f"Page {page_path.relative_to(built_site_output)} "
                f"missing data-type='autodoc-cli' attribute"
            )

    @pytest.mark.parametrize(
        ("autodoc_type", "expected_type"),
        [
            ("python", "autodoc-python"),
            ("cli", "autodoc-cli"),
        ],
    )
    def test_nested_pages_have_correct_type(
        self, built_site_output: Path, autodoc_type: str, expected_type: str
    ) -> None:
        """Deeply nested pages should have correct data-type."""
        if autodoc_type == "python":
            base_dir = built_site_output / "api" / "bengal"
        else:
            base_dir = built_site_output / "cli"

        if not base_dir.exists():
            pytest.skip(f"{base_dir} directory not found")

        # Find a deeply nested page (3+ levels)
        deep_pages = [
            p for p in base_dir.rglob("index.html") if len(p.relative_to(base_dir).parts) >= 3
        ]

        if not deep_pages:
            pytest.skip(f"No deeply nested pages found in {base_dir}")

        # Check the deepest page
        deepest = max(deep_pages, key=lambda p: len(p.relative_to(base_dir).parts))
        html = deepest.read_text()

        assert f'data-type="{expected_type}"' in html, (
            f"Deeply nested page {deepest.relative_to(built_site_output)} "
            f"missing data-type='{expected_type}' attribute"
        )


class TestAutodocPageStructure:
    """Test that autodoc pages have proper HTML structure."""

    def test_python_module_page_has_article_element(self, built_site_output: Path) -> None:
        """Python module pages should have article with data-element='module'."""
        # Find a module page (not a section index)
        api_dir = built_site_output / "api" / "bengal"
        if not api_dir.exists():
            pytest.skip("api/bengal directory not found")

        # Look for a deep module page
        for page_path in api_dir.rglob("index.html"):
            html = page_path.read_text()
            if 'data-element="module"' in html:
                assert "data-autodoc" in html
                return

        # If no module pages found, that's okay - skip
        pytest.skip("No module pages found")

    def test_cli_command_page_has_article_element(self, built_site_output: Path) -> None:
        """CLI command pages should have article with data-element='command'."""
        cli_dir = built_site_output / "cli"
        if not cli_dir.exists():
            pytest.skip("cli directory not found")

        # Find a command page
        for page_path in cli_dir.rglob("index.html"):
            html = page_path.read_text()
            if 'data-element="command"' in html:
                assert "data-autodoc" in html
                return

        # If no command pages found, that's okay - skip
        pytest.skip("No command pages found")

    def test_section_index_pages_have_section_element(self, built_site_output: Path) -> None:
        """Section index pages should have data-element='section-index'."""
        api_dir = built_site_output / "api" / "bengal"
        if not api_dir.exists():
            pytest.skip("api/bengal directory not found")

        # Check root index
        root_index = api_dir / "index.html"
        if root_index.exists():
            html = root_index.read_text()
            # Root or section index should have section-index element
            assert 'data-element="section-index"' in html or 'data-element="module"' in html, (
                "Root index page missing expected data-element attribute"
            )


class TestAutodocHTMLContent:
    """Test that autodoc HTML pages have required content."""

    def test_pages_have_valid_doctype(self, built_site_output: Path) -> None:
        """All autodoc pages should have valid HTML doctype."""
        api_dir = built_site_output / "api" / "bengal"
        cli_dir = built_site_output / "cli"

        pages_to_check: list[Path] = []
        if api_dir.exists():
            pages_to_check.extend(list(api_dir.rglob("index.html"))[:10])
        if cli_dir.exists():
            pages_to_check.extend(list(cli_dir.rglob("index.html"))[:10])

        if not pages_to_check:
            pytest.skip("No autodoc pages found")

        for page_path in pages_to_check:
            html = page_path.read_text()
            assert html.strip().lower().startswith("<!doctype html>"), (
                f"Page {page_path} missing DOCTYPE"
            )

    def test_pages_have_title_tag(self, built_site_output: Path) -> None:
        """All autodoc pages should have a title tag."""
        api_dir = built_site_output / "api" / "bengal"

        if not api_dir.exists():
            pytest.skip("api/bengal directory not found")

        for page_path in list(api_dir.rglob("index.html"))[:10]:
            html = page_path.read_text()
            assert "<title>" in html, f"Page {page_path} missing <title>"
            assert "</title>" in html, f"Page {page_path} missing </title>"

    def test_pages_have_navigation(self, built_site_output: Path) -> None:
        """All autodoc pages should have navigation elements."""
        api_dir = built_site_output / "api" / "bengal"

        if not api_dir.exists():
            pytest.skip("api/bengal directory not found")

        for page_path in list(api_dir.rglob("index.html"))[:5]:
            html = page_path.read_text()
            # Should have some form of navigation
            assert "<nav" in html or "nav-" in html, f"Page {page_path} missing navigation element"


class TestAutodocGenerationConsistency:
    """Test consistency of autodoc generation across types."""

    def test_python_and_cli_have_similar_structure(self, built_site_output: Path) -> None:
        """Python API and CLI should have similar output structure."""
        api_dir = built_site_output / "api" / "bengal"
        cli_dir = built_site_output / "cli"

        if not api_dir.exists() or not cli_dir.exists():
            pytest.skip("Both api/bengal and cli directories required")

        # Both should have root index.html
        assert (api_dir / "index.html").exists(), "Python API missing root index.html"
        assert (cli_dir / "index.html").exists(), "CLI missing root index.html"

        # Both should have subdirectories
        api_subdirs = [d for d in api_dir.iterdir() if d.is_dir()]
        cli_subdirs = [d for d in cli_dir.iterdir() if d.is_dir()]

        assert len(api_subdirs) > 0, "Python API has no subdirectories"
        assert len(cli_subdirs) > 0, "CLI has no subdirectories"

    def test_no_orphan_txt_files(self, built_site_output: Path) -> None:
        """Every .txt file should have a corresponding .html file."""
        api_dir = built_site_output / "api" / "bengal"
        cli_dir = built_site_output / "cli"

        orphan_txt: list[str] = []

        for base_dir in [api_dir, cli_dir]:
            if not base_dir.exists():
                continue

            for txt_file in base_dir.rglob("*.txt"):
                html_file = txt_file.with_suffix(".html")
                if txt_file.stem == "index":
                    html_file = txt_file.parent / "index.html"

                if not html_file.exists():
                    orphan_txt.append(str(txt_file.relative_to(built_site_output)))

        assert not orphan_txt, "TXT files without corresponding HTML:\n" + "\n".join(
            f"  - {p}" for p in orphan_txt[:10]
        )
