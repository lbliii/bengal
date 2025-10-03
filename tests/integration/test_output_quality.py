"""
Integration tests that validate rendered output quality.

These tests catch issues where pages render but produce broken/incomplete HTML,
like the template rendering bug where pages fell back to simple HTML without themes.
"""
import pytest
from pathlib import Path
from bs4 import BeautifulSoup
import tempfile
import shutil

from bengal.core.site import Site


@pytest.fixture
def built_site(tmp_path):
    """
    Build a complete site and return the output directory.
    
    Uses the quickstart example as test data.
    """
    # Copy quickstart example to tmp
    quickstart = Path("examples/quickstart")
    site_dir = tmp_path / "site"
    
    # Copy content and config
    shutil.copytree(quickstart / "content", site_dir / "content")
    shutil.copy(quickstart / "bengal.toml", site_dir / "bengal.toml")
    
    # Build site in strict mode (fail if rendering broken)
    site = Site.from_config(site_dir)
    site.config["strict_mode"] = True  # Fail loudly on errors
    # No need for ignore list - health check now recognizes code blocks automatically!
    site.build()
    
    return site.output_dir


class TestOutputQuality:
    """Test that built pages have expected quality and content."""
    
    def test_pages_include_theme_assets(self, built_site):
        """Verify pages include CSS and JS from theme."""
        index_html = (built_site / "index.html").read_text()
        soup = BeautifulSoup(index_html, 'html.parser')
        
        # Must have stylesheet links
        stylesheets = soup.find_all('link', rel='stylesheet')
        assert len(stylesheets) > 0, "No stylesheets found in output"
        
        # Check for asset_url helper working
        assert any('assets/css' in str(link.get('href', '')) for link in stylesheets), \
            "No theme CSS linked"
        
        # Must have navigation
        nav = soup.find('nav')
        assert nav is not None, "No navigation found in output"
    
    def test_pages_have_proper_html_structure(self, built_site):
        """Verify pages have proper HTML5 structure."""
        index_html = (built_site / "index.html").read_text()
        soup = BeautifulSoup(index_html, 'html.parser')
        
        # Must have proper HTML structure
        assert soup.find('html') is not None, "No <html> tag"
        assert soup.find('head') is not None, "No <head> tag"
        assert soup.find('body') is not None, "No <body> tag"
        assert soup.find('title') is not None, "No <title> tag"
        
        # Must have meta tags
        charset = soup.find('meta', attrs={'charset': True})
        assert charset is not None, "No charset meta tag"
        
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        assert viewport is not None, "No viewport meta tag"
    
    def test_pages_have_reasonable_size(self, built_site):
        """
        Verify pages aren't tiny fallback HTML.
        
        Full themed pages should be at least 3KB.
        Fallback HTML is typically < 2KB.
        """
        index_html = built_site / "index.html"
        size = index_html.stat().st_size
        
        # Full themed pages should be substantial
        assert size > 3000, \
            f"Page too small ({size} bytes), likely fallback HTML instead of themed output"
        
        # Check a few other pages too
        about_html = built_site / "about/index.html"
        if about_html.exists():
            about_size = about_html.stat().st_size
            assert about_size > 2000, \
                f"About page too small ({about_size} bytes)"
    
    def test_pages_contain_actual_content(self, built_site):
        """Verify pages include the actual markdown content."""
        # Check index page
        index_html = (built_site / "index.html").read_text()
        assert "Bengal" in index_html, "Index missing expected content"
        
        # Check about page if it exists
        about_html_path = built_site / "about/index.html"
        if about_html_path.exists():
            about_html = about_html_path.read_text()
            # Should contain content from about.md
            assert len(about_html) > 100, "About page suspiciously short"
    
    def test_no_unrendered_jinja2_in_output(self, built_site):
        """Verify no unrendered Jinja2 variables leak through."""
        from bs4 import BeautifulSoup
        
        for html_file in built_site.rglob("*.html"):
            content = html_file.read_text()
            
            # Use smart detection to skip code blocks (documentation)
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove code blocks (allowed to have Jinja2 syntax)
            for code_block in soup.find_all(['code', 'pre']):
                code_block.decompose()
            
            remaining_text = soup.get_text()
            
            # Check for unrendered Jinja2 syntax outside of code blocks
            if "{{ page." in remaining_text or "{% if page" in remaining_text:
                pytest.fail(f"Unrendered Jinja2 page variable in {html_file}")
            
            if "{{ site." in remaining_text or "{% if site" in remaining_text:
                pytest.fail(f"Unrendered Jinja2 site variable in {html_file}")
    
    def test_theme_assets_copied(self, built_site):
        """Verify theme CSS/JS files are copied to output."""
        assets_dir = built_site / "assets"
        assert assets_dir.exists(), "No assets directory in output"
        
        # Should have CSS
        css_dir = assets_dir / "css"
        assert css_dir.exists(), "No CSS directory in output"
        css_files = list(css_dir.glob("*.css"))
        assert len(css_files) > 0, "No CSS files in output"
        
        # Should have JS
        js_dir = assets_dir / "js"
        assert js_dir.exists(), "No JS directory in output"
        js_files = list(js_dir.glob("*.js"))
        assert len(js_files) > 0, "No JS files in output"
    
    def test_pages_have_proper_meta_tags(self, built_site):
        """Verify SEO meta tags are properly rendered."""
        index_html = (built_site / "index.html").read_text()
        soup = BeautifulSoup(index_html, 'html.parser')
        
        # Check Open Graph tags
        og_title = soup.find('meta', property='og:title')
        assert og_title is not None, "Missing og:title meta tag"
        
        og_type = soup.find('meta', property='og:type')
        assert og_type is not None, "Missing og:type meta tag"
        
        # Check Twitter Card tags
        twitter_card = soup.find('meta', attrs={'name': 'twitter:card'})
        assert twitter_card is not None, "Missing twitter:card meta tag"
    
    def test_rss_feed_generated(self, built_site):
        """Verify RSS feed is generated and valid."""
        rss_path = built_site / "rss.xml"
        assert rss_path.exists(), "RSS feed not generated"
        
        rss_content = rss_path.read_text()
        assert '<?xml' in rss_content, "RSS missing XML declaration"
        assert '<rss' in rss_content, "RSS missing <rss> tag"
        assert '<channel>' in rss_content, "RSS missing <channel> tag"
    
    def test_sitemap_generated(self, built_site):
        """Verify sitemap is generated and valid."""
        sitemap_path = built_site / "sitemap.xml"
        assert sitemap_path.exists(), "Sitemap not generated"
        
        sitemap_content = sitemap_path.read_text()
        assert '<?xml' in sitemap_content, "Sitemap missing XML declaration"
        assert '<urlset' in sitemap_content, "Sitemap missing <urlset> tag"
        assert '<url>' in sitemap_content, "Sitemap missing <url> entries"


class TestStrictMode:
    """Test that strict mode catches rendering errors."""
    
    def test_strict_mode_fails_on_bad_template(self, tmp_path):
        """Verify strict mode fails build on template errors."""
        # Create a minimal site with a broken template reference
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        
        content_dir = site_dir / "content"
        content_dir.mkdir()
        
        # Create a page with a non-existent template
        page_file = content_dir / "test.md"
        page_file.write_text("""---
title: Test Page
template: nonexistent.html
---

# Test Content
""")
        
        # Create minimal config
        config_file = site_dir / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test Site"
""")
        
        # Build should fail in strict mode
        site = Site.from_config(site_dir)
        site.config["strict_mode"] = True
        
        with pytest.raises(Exception):
            site.build()
    
    def test_non_strict_mode_allows_fallback(self, tmp_path):
        """Verify non-strict mode allows fallback on template errors."""
        # Same setup as above
        site_dir = tmp_path / "site"
        site_dir.mkdir()
        
        content_dir = site_dir / "content"
        content_dir.mkdir()
        
        page_file = content_dir / "test.md"
        page_file.write_text("""---
title: Test Page
template: nonexistent.html
---

# Test Content
""")
        
        config_file = site_dir / "bengal.toml"
        config_file.write_text("""
[site]
title = "Test Site"
""")
        
        # Build should succeed with fallback in non-strict mode
        site = Site.from_config(site_dir)
        site.config["strict_mode"] = False
        
        # Should not raise
        site.build()
        
        # But output should be fallback HTML (small)
        output_file = site.output_dir / "test/index.html"
        if output_file.exists():
            size = output_file.stat().st_size
            # Fallback HTML should be small
            assert size < 2000, "Expected small fallback HTML in non-strict mode"

