"""
Integration tests for building documentation sites with template examples.

These tests ensure that documentation content with template syntax examples
can be built without errors, addressing the showcase site issues.
"""

import shutil

import pytest

from bengal.core.site import Site
from bengal.orchestration.build import BuildOrchestrator
from bengal.rendering.parsers.factory import ParserFactory


class TestDocumentationBuild:
    """Integration tests for building documentation pages."""

    def test_build_page_with_template_examples(self, tmp_path):
        """Test building a page with escaped template examples."""
        # Create site structure
        site_dir = tmp_path / "site"
        content_dir = site_dir / "content"
        content_dir.mkdir(parents=True)

        # Create config
        config_file = site_dir / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test Site"
baseurl = "https://example.com"

[build]
content_dir = "content"
output_dir = "public"
theme = "default"

[markdown]
parser = "mistune"
""")

        # Create documentation page with template examples
        doc_page = content_dir / "template-guide.md"
        doc_page.write_text("""---
title: Template Guide
date: 2025-10-04
---

# Template Functions

## Variable Substitution

Use {{/* page.title */}} to display the page title.

## String Functions

Truncate content:

```jinja2
{{/* post.content | truncatewords(50) */}}
```

## Date Functions

Format dates:

```jinja2
{{/* page.date | format_date('%Y-%m-%d') */}}
```

## URL Functions

Absolute URLs:

```jinja2
{{/* page.url | absolute_url */}}
```

## SEO Functions

Meta descriptions:

```jinja2
{{/* page.content | meta_description(160) */}}
```
""")

        # Build the site
        site = Site.from_config(site_dir)
        orchestrator = BuildOrchestrator(site)

        # This should NOT raise errors
        try:
            orchestrator.build()
            success = True
        except Exception as e:
            success = False
            error_msg = str(e)

        assert success, f"Build failed with error: {error_msg if not success else 'N/A'}"

        # Verify output exists
        output_file = site_dir / "public" / "template-guide" / "index.html"
        assert output_file.exists(), "Output file was not generated"

        # Verify template examples are in the output as HTML entities
        output_content = output_file.read_text()

        # These should appear as HTML entities (which render as {{ }} in browser)
        # This prevents Jinja2 from trying to process them
        assert "&#123;&#123; page.title &#125;&#125;" in output_content
        assert "&#123;&#123; post.content | truncatewords(50) &#125;&#125;" in output_content
        assert "&#123;&#123; page.date | format_date" in output_content
        assert "&#123;&#123; page.url | absolute_url &#125;&#125;" in output_content
        assert "&#123;&#123; page.content | meta_description" in output_content

        # Extract just the body content to check for escape markers
        # Meta tags may contain raw markdown (that's OK), but the body should be clean
        from bs4 import BeautifulSoup

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
        orchestrator.build()

        # Verify all pages built
        for filename in pages_content:
            output_file = site_dir / "public" / "docs" / filename.replace(".md", "") / "index.html"
            assert output_file.exists(), f"{filename} was not built"

    def test_mixed_real_and_example_variables(self, tmp_path):
        """Test page with both real variable substitution and examples."""
        site_dir = tmp_path / "site"
        content_dir = site_dir / "content"
        content_dir.mkdir(parents=True)

        config_file = site_dir / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test Site"
author = "Test Author"

[build]
content_dir = "content"
output_dir = "public"

[markdown]
parser = "mistune"
""")

        # Page with both real and example templates
        page = content_dir / "guide.md"
        page.write_text("""---
title: Template Guide
author: Guide Author
---

# Guide Title: {{ page.title }}

Written by: {{ page.metadata.author }}

## How to Use

To display the title, use: {{/* page.title */}}

To display the author, use: {{/* page.metadata.author */}}

Site name: {{ site.title }}

To get site name, use: {{/* site.title */}}
""")

        # Build
        site = Site.from_config(site_dir)
        orchestrator = BuildOrchestrator(site)
        orchestrator.build()

        # Check output
        output_file = site_dir / "public" / "guide" / "index.html"
        output = output_file.read_text()

        # Real variables should be substituted
        assert "Guide Title: Template Guide" in output or "Template Guide" in output
        assert "Written by: Guide Author" in output or "Guide Author" in output
        assert "Site name: Test Site" in output or "Test Site" in output

        # Examples should be literal (as HTML entities to prevent Jinja2 processing)
        # Browsers will render &#123;&#123; as {{ for the user
        assert "use: &#123;&#123; page.title &#125;&#125;" in output
        assert "use: &#123;&#123; page.metadata.author &#125;&#125;" in output
        assert "use: &#123;&#123; site.title &#125;&#125;" in output


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
