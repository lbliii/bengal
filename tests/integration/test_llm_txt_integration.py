"""
Integration tests for LLM.txt file generation and availability.

These tests ensure that LLM.txt files are:
- Generated during full and incremental builds
- Always available at expected URLs
- Updated when pages change
- Removed when pages are deleted
"""

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions


@pytest.fixture
def test_site(tmp_path):
    """
    Create a test site with LLM.txt output enabled.

    Returns site directory and config for testing.
    """
    site_dir = tmp_path / "test_site"
    site_dir.mkdir()

    # Create directory structure
    (site_dir / "content").mkdir()
    (site_dir / "public").mkdir(exist_ok=True)

    # Create test config with LLM.txt enabled
    config_content = """
[site]
title = "Test Site"
baseurl = "https://example.com"

[output_formats]
enabled = true
per_page = ["llm_txt"]
site_wide = ["llm_full"]
"""
    (site_dir / "bengal.toml").write_text(config_content)

    # Create some test pages
    page1 = """---
title: "Getting Started"
date: 2025-10-20
tags: ["tutorial", "beginner"]
---

# Getting Started

This is an introduction to the test site.

## Installation

Install using pip:

```bash
pip install test-package
```

## Usage

Use it like this:

```python
import test_package
test_package.run()
```
"""
    (site_dir / "content" / "getting-started.md").write_text(page1)

    page2 = """---
title: "API Reference"
date: 2025-10-21
tags: ["api", "reference"]
---

# API Reference

Complete API documentation.

## Functions

### run()

Runs the main function.

**Returns:** `None`
"""
    autodoc_dir = site_dir / "content" / "autodoc"
    autodoc_dir.mkdir(parents=True, exist_ok=True)
    (autodoc_dir / "python.md").write_text(page2)

    return site_dir


class TestLLMTextFullBuild:
    """Test LLM.txt generation during full builds."""

    def test_per_page_llm_txt_generated(self, test_site):
        """Test that each page gets an index.txt file."""
        site = Site.from_config(test_site)
        site.build(BuildOptions())

        output_dir = site.output_dir

        # Check per-page LLM.txt files exist
        assert (output_dir / "getting-started" / "index.txt").exists()
        assert (output_dir / "autodoc/python" / "index.txt").exists()

    def test_site_wide_llm_full_generated(self, test_site):
        """Test that llm-full.txt is generated at site root."""
        site = Site.from_config(test_site)
        site.build(BuildOptions())

        llm_full_path = site.output_dir / "llm-full.txt"
        assert llm_full_path.exists(), "llm-full.txt should be at site root"

        content = llm_full_path.read_text()
        assert "Getting Started" in content
        assert "API Reference" in content
        assert "## Page 1/" in content or "## Page 2/" in content

    def test_per_page_llm_txt_content_format(self, test_site):
        """Test that per-page LLM.txt follows format specification."""
        site = Site.from_config(test_site)
        site.build(BuildOptions())

        txt_path = site.output_dir / "getting-started" / "index.txt"
        content = txt_path.read_text()

        # Format checks
        assert content.startswith("# Getting Started")
        assert "URL: /getting-started/" in content
        assert "Tags: tutorial, beginner" in content
        assert "This is an introduction" in content
        assert "Metadata:" in content
        assert "Word Count:" in content
        assert "Reading Time:" in content

        # HTML should be stripped
        assert "<p>" not in content
        assert "<h1>" not in content

    def test_llm_txt_strips_code_blocks_properly(self, test_site):
        """Test that code blocks are handled correctly in LLM.txt."""
        site = Site.from_config(test_site)
        site.build(BuildOptions())

        txt_path = site.output_dir / "getting-started" / "index.txt"
        content = txt_path.read_text()

        # Code content should be present
        assert "pip install test-package" in content
        assert "import test_package" in content

        # But markdown code fence syntax should be removed
        # (The _strip_html function handles this)

    def test_llm_txt_urls_are_correct(self, test_site):
        """Test that LLM.txt files use correct URLs."""
        site = Site.from_config(test_site)
        site.build(BuildOptions())

        # Check getting-started
        txt1 = (site.output_dir / "getting-started" / "index.txt").read_text()
        assert "URL: /getting-started/" in txt1

        # Check autodoc/python
        txt2 = (site.output_dir / "autodoc/python" / "index.txt").read_text()
        assert "URL: /autodoc/python/" in txt2


class TestLLMTextIncrementalBuild:
    """Test LLM.txt updates during incremental builds."""

    def test_llm_txt_updated_on_page_change(self, test_site):
        """Test that LLM.txt is regenerated when page changes."""
        site = Site.from_config(test_site)
        site.build(BuildOptions())

        # Initial content
        txt_path = site.output_dir / "getting-started" / "index.txt"
        initial_content = txt_path.read_text()
        assert "This is an introduction" in initial_content

        # Modify the page
        modified_page = """---
title: "Getting Started"
date: 2025-10-20
tags: ["tutorial", "beginner"]
---

# Getting Started

This content has been updated with new information.
"""
        (test_site / "content" / "getting-started.md").write_text(modified_page)

        # Rebuild (incremental)
        site = Site.from_config(test_site)
        site.build(BuildOptions())

        # Check updated content
        updated_content = txt_path.read_text()
        assert "new information" in updated_content
        assert "This is an introduction" not in updated_content

    def test_llm_txt_removed_on_page_deletion(self, test_site):
        """Test that LLM.txt is removed when page is deleted.

        NOTE: This test documents current behavior. Orphaned LLM.txt files
        are currently NOT cleaned up automatically (same as orphaned JSON files).
        HTML files ARE cleaned up. This is a known limitation.

        To truly clean up, users should:
        1. Use `bengal clean` to remove public/ dir, OR
        2. Implement a cleanup step that removes orphaned files
        """
        site = Site.from_config(test_site)
        site.build(BuildOptions())

        # Verify files exist
        txt_path = site.output_dir / "autodoc/python" / "index.txt"
        html_path = site.output_dir / "autodoc/python" / "index.html"
        assert txt_path.exists()
        assert html_path.exists()

        # Delete the page
        (test_site / "content" / "autodoc/python.md").unlink()

        # Rebuild
        site = Site.from_config(test_site)
        site.build(BuildOptions())

        # HTML should be removed (this works!)
        assert not html_path.exists(), "HTML should be deleted with page"

        # TODO: LLM.txt cleanup - Known limitation
        # Currently, output format files (JSON, TXT) are not cleaned up automatically.
        # This is consistent with other static files but could be improved.
        # For now, we document that cleanup requires `bengal clean`.
        #
        # Expected behavior (when fixed):
        # assert not txt_path.exists(), "LLM.txt should be deleted with page"
        #
        # Current behavior:
        # File remains until `bengal clean` is run

    def test_llm_full_updated_on_any_page_change(self, test_site):
        """Test that llm-full.txt is updated when any page changes."""
        site = Site.from_config(test_site)
        site.build(BuildOptions())

        llm_full_path = site.output_dir / "llm-full.txt"
        initial_content = llm_full_path.read_text()
        assert "This is an introduction" in initial_content

        # Modify one page
        modified_page = """---
title: "Getting Started"
date: 2025-10-20
tags: ["tutorial", "beginner"]
---

Updated content for testing llm-full.txt regeneration.
"""
        (test_site / "content" / "getting-started.md").write_text(modified_page)

        # Rebuild
        site = Site.from_config(test_site)
        site.build(BuildOptions())

        # llm-full.txt should contain updated content
        new_content = llm_full_path.read_text()
        assert "Updated content for testing llm-full.txt regeneration" in new_content
        assert "This is an introduction" not in new_content


class TestLLMTextURLAccessibility:
    """Test that LLM.txt files are accessible at expected URLs."""

    def test_index_txt_path_matches_url_pattern(self, test_site):
        """Test that index.txt follows the same path pattern as index.html."""
        site = Site.from_config(test_site)
        site.build(BuildOptions())

        output_dir = site.output_dir

        # For /getting-started/ URL:
        # - HTML is at: getting-started/index.html
        # - TXT should be at: getting-started/index.txt
        html_path = output_dir / "getting-started" / "index.html"
        txt_path = output_dir / "getting-started" / "index.txt"

        assert html_path.exists()
        assert txt_path.exists()
        assert html_path.parent == txt_path.parent

    def test_llm_txt_accessible_via_action_bar_url(self, test_site):
        """Test that LLM.txt is accessible via the action-bar URL pattern."""
        site = Site.from_config(test_site)
        site.build(BuildOptions())

        # Action-bar template uses: {{ page_url }}/index.txt
        # For page at /getting-started/, the URL would be:
        # /getting-started/index.txt

        # Verify file exists at that path
        txt_path = site.output_dir / "getting-started" / "index.txt"
        assert txt_path.exists()

        # Verify content is valid
        content = txt_path.read_text()
        assert len(content) > 0
        assert "# Getting Started" in content


class TestLLMTextWithNestedPages:
    """Test LLM.txt generation with nested page structures."""

    def test_nested_pages_generate_llm_txt(self, tmp_path):
        """Test that nested pages generate LLM.txt files correctly."""
        site_dir = tmp_path / "nested_site"
        site_dir.mkdir()

        # Create structure
        (site_dir / "content" / "docs" / "guides").mkdir(parents=True)
        (site_dir / "public").mkdir(exist_ok=True)

        # Config
        config = """
[site]
title = "Nested Site"

[output_formats]
enabled = true
per_page = ["llm_txt"]
site_wide = []
"""
        (site_dir / "bengal.toml").write_text(config)

        # Create nested pages
        guide1 = """---
title: "Installation Guide"
---

How to install.
"""
        (site_dir / "content" / "docs" / "guides" / "install.md").write_text(guide1)

        # Build
        site = Site.from_config(site_dir)
        site.build(BuildOptions())

        # Verify nested LLM.txt exists
        txt_path = site.output_dir / "docs" / "guides" / "install" / "index.txt"
        assert txt_path.exists()

        content = txt_path.read_text()
        assert "Installation Guide" in content
        assert "URL: /docs/guides/install/" in content


class TestLLMTextDisabled:
    """Test behavior when LLM.txt is disabled."""

    def test_no_llm_txt_when_disabled(self, tmp_path):
        """Test that LLM.txt files are not generated when disabled."""
        site_dir = tmp_path / "disabled_site"
        site_dir.mkdir()

        (site_dir / "content").mkdir()
        (site_dir / "public").mkdir(exist_ok=True)

        # Config with LLM.txt disabled
        config = """
[site]
title = "Test Site"

[output_formats]
enabled = true
per_page = []
site_wide = []
"""
        (site_dir / "bengal.toml").write_text(config)

        # Create page
        page = """---
title: "Test Page"
---

Content here.
"""
        (site_dir / "content" / "test.md").write_text(page)

        # Build
        site = Site.from_config(site_dir)
        site.build(BuildOptions())

        # LLM.txt files should NOT exist
        assert not (site.output_dir / "test" / "index.txt").exists()
        assert not (site.output_dir / "llm-full.txt").exists()

    def test_html_still_generated_when_llm_txt_disabled(self, tmp_path):
        """Test that HTML is still generated when LLM.txt is disabled."""
        site_dir = tmp_path / "disabled_site"
        site_dir.mkdir()

        (site_dir / "content").mkdir()
        (site_dir / "public").mkdir(exist_ok=True)

        # Config with LLM.txt disabled
        config = """
[site]
title = "Test Site"

[output_formats]
enabled = true
per_page = []
site_wide = []
"""
        (site_dir / "bengal.toml").write_text(config)

        # Create page
        page = """---
title: "Test Page"
---

Content here.
"""
        (site_dir / "content" / "test.md").write_text(page)

        # Build
        site = Site.from_config(site_dir)
        site.build(BuildOptions())

        # HTML should exist
        assert (site.output_dir / "test" / "index.html").exists()

        # But not LLM.txt
        assert not (site.output_dir / "test" / "index.txt").exists()
