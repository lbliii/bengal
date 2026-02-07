"""
Integration tests for building documentation sites with template examples.

These tests ensure that documentation content with template syntax examples
can be built without errors, addressing the showcase site issues.

Uses Phase 1 infrastructure: @pytest.mark.bengal with test-templates root.
"""

import shutil

import pytest

bs4 = pytest.importorskip("bs4", reason="beautifulsoup4 required for output quality tests")
BeautifulSoup = bs4.BeautifulSoup

from bengal.core.site import Site
from bengal.orchestration.build import BuildOrchestrator
from bengal.orchestration.build.options import BuildOptions
from bengal.parsing.factory import ParserFactory


class TestDocumentationBuild:
    """Integration tests for building documentation pages."""

    @pytest.mark.bengal(testroot="test-templates")
    def test_build_page_with_template_examples(self, site, build_site):
        """Test building a page with escaped template examples.

        Uses test-templates root which contains guide.md with template examples.
        """
        # Build the site - should NOT raise errors
        build_site()

        # Verify output exists (guide.md → guide/index.html)
        output_file = site.output_dir / "guide" / "index.html"
        assert output_file.exists(), "Output file was not generated"

        # Verify template examples are in the output as HTML entities
        output_content = output_file.read_text()

        # These should appear as HTML entities (which render as {{ }} in browser)
        # This prevents Jinja2 from trying to process them
        assert "&#123;&#123; page.title &#125;&#125;" in output_content
        assert "&#123;&#123; post.content | truncatewords(50) &#125;&#125;" in output_content
        assert "&#123;&#123; page.date | format_date" in output_content
        assert "&#123;&#123; page.url | absolute_url &#125;&#125;" in output_content

        # Extract just the body content to check for escape markers
        # Meta tags may contain raw markdown (that's OK), but the body should be clean
        parser = ParserFactory.get_html_parser("native")
        soup = parser(output_content)
        assert len(soup.get_text()) > 0  # Verify text was extracted

        soup = BeautifulSoup(output_content, "html.parser")
        body_content = soup.find("body")
        if body_content:
            body_text = str(body_content)
            # Escape markers should NOT be in visible page body
            assert "{{/*" not in body_text, "Escape markers found in page body"
            assert "*/}}" not in body_text, "Escape markers found in page body"

    def test_build_multiple_doc_pages(self, tmp_path):
        """Test building multiple documentation pages with various template examples."""
        # Create site structure
        site_dir = tmp_path / "site"
        content_dir = site_dir / "content"
        docs_dir = content_dir / "docs"
        docs_dir.mkdir(parents=True)

        # Create config
        config_file = site_dir / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test Docs"

[build]
content_dir = "content"
output_dir = "public"

[markdown]
parser = "mistune"
""")

        # Create multiple doc pages
        pages_content = {
            "strings.md": """---
title: String Functions
---
Use {{/* text | truncatewords(50) */}} to truncate.
""",
            "dates.md": """---
title: Date Functions
---
Use {{/* date | time_ago */}} for relative times.
""",
            "urls.md": """---
title: URL Functions
---
Use {{/* url | absolute_url */}} for absolute URLs.
""",
            "seo.md": """---
title: SEO Functions
---
Use {{/* content | meta_description(160) */}} for meta tags.
""",
        }

        for filename, content in pages_content.items():
            (docs_dir / filename).write_text(content)

        # Build site
        site = Site.from_config(site_dir)
        orchestrator = BuildOrchestrator(site)

        # Should build without errors
        orchestrator.build(BuildOptions())

        # Verify all pages built
        for filename in pages_content:
            output_file = site_dir / "public" / "docs" / filename.replace(".md", "") / "index.html"
            assert output_file.exists(), f"{filename} was not built"

    @pytest.mark.bengal(testroot="test-templates")
    def test_mixed_real_and_example_variables(self, site, build_site):
        """Test page with both real variable substitution and examples."""
        # Build site - test-templates root has guide.md with both real and escaped vars
        build_site()

        # Check output
        output_file = site.output_dir / "guide" / "index.html"
        output = output_file.read_text()

        # Real variables should be substituted by the template
        # page.title is rendered by the page.html template in the H1 header
        assert "Template Guide" in output  # page.title from frontmatter
        # Note: page.author is NOT rendered - the page.html template doesn't include it

        # Examples should be literal (as HTML entities to prevent Jinja2 processing)
        # Browsers will render &#123;&#123; as {{ for the user
        assert "&#123;&#123; page.title &#125;&#125;" in output
        assert "&#123;&#123; post.content | truncatewords" in output
        assert "&#123;&#123; page.date | format_date" in output


@pytest.fixture
def clean_site(tmp_path):
    """Create a clean site directory for testing."""
    site_dir = tmp_path / "test_site"
    site_dir.mkdir()

    # Create basic structure
    (site_dir / "content").mkdir()
    (site_dir / "public").mkdir(exist_ok=True)

    # Create minimal config
    config = site_dir / "bengal.toml"
    config.write_text("""
[site]
title = "Test Site"

[build]
content_dir = "content"
output_dir = "public"
theme = "default"

[markdown]
parser = "mistune"
""")

    yield site_dir

    # Cleanup
    if site_dir.exists():
        shutil.rmtree(site_dir)
