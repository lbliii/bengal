"""
Tests for Sitemap validator.
"""

import pytest
from unittest.mock import Mock

from bengal.health.validators.sitemap import SitemapValidator
from bengal.health.report import CheckStatus


@pytest.fixture
def mock_site(tmp_path):
    """Create a mock site for testing."""
    site = Mock()
    site.output_dir = tmp_path
    site.config = {'baseurl': 'https://example.com'}
    
    # Create mock pages
    page1 = Mock()
    page1.metadata = {'draft': False}
    
    page2 = Mock()
    page2.metadata = {'draft': False}
    
    page3 = Mock()
    page3.metadata = {'draft': True}
    
    site.pages = [page1, page2, page3]
    return site


def test_sitemap_validator_missing_file(mock_site):
    """Test validator warns when sitemap not generated."""
    validator = SitemapValidator()
    results = validator.validate(mock_site)
    
    assert len(results) > 0
    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("not generated" in r.message.lower() for r in results)


def test_sitemap_validator_valid_sitemap(mock_site, tmp_path):
    """Test validator passes for valid sitemap."""
    sitemap_path = tmp_path / 'sitemap.xml'
    sitemap_content = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://example.com/page1/</loc>
        <lastmod>2025-01-01</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.5</priority>
    </url>
    <url>
        <loc>https://example.com/page2/</loc>
        <changefreq>weekly</changefreq>
        <priority>0.5</priority>
    </url>
</urlset>'''
    sitemap_path.write_text(sitemap_content)
    
    validator = SitemapValidator()
    results = validator.validate(mock_site)
    
    # Should have success results
    assert any(r.status == CheckStatus.SUCCESS for r in results)
    assert any("Sitemap file exists" in r.message for r in results)
    assert any("well-formed" in r.message for r in results)


def test_sitemap_validator_malformed_xml(mock_site, tmp_path):
    """Test validator catches malformed XML."""
    sitemap_path = tmp_path / 'sitemap.xml'
    sitemap_content = '<urlset><url></urlset>'  # Unclosed url
    sitemap_path.write_text(sitemap_content)
    
    validator = SitemapValidator()
    results = validator.validate(mock_site)
    
    assert any(r.status == CheckStatus.ERROR for r in results)
    assert any("malformed" in r.message.lower() for r in results)


def test_sitemap_validator_wrong_root_element(mock_site, tmp_path):
    """Test validator catches wrong root element."""
    sitemap_path = tmp_path / 'sitemap.xml'
    sitemap_content = '''<?xml version="1.0"?>
<sitemapindex>
    <sitemap>
        <loc>https://example.com/sitemap.xml</loc>
    </sitemap>
</sitemapindex>'''
    sitemap_path.write_text(sitemap_content)
    
    validator = SitemapValidator()
    results = validator.validate(mock_site)
    
    assert any(r.status == CheckStatus.ERROR for r in results)
    assert any("urlset" in r.message.lower() for r in results)


def test_sitemap_validator_no_urls(mock_site, tmp_path):
    """Test validator warns when sitemap has no URLs."""
    sitemap_path = tmp_path / 'sitemap.xml'
    sitemap_content = '''<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
</urlset>'''
    sitemap_path.write_text(sitemap_content)
    
    validator = SitemapValidator()
    results = validator.validate(mock_site)
    
    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("no" in r.message.lower() and "url" in r.message.lower() for r in results)


def test_sitemap_validator_relative_urls(mock_site, tmp_path):
    """Test validator catches relative URLs."""
    sitemap_path = tmp_path / 'sitemap.xml'
    sitemap_content = '''<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>/page1/</loc>
    </url>
</urlset>'''
    sitemap_path.write_text(sitemap_content)
    
    validator = SitemapValidator()
    results = validator.validate(mock_site)
    
    assert any(r.status == CheckStatus.ERROR for r in results)
    assert any("relative" in r.message.lower() for r in results)


def test_sitemap_validator_duplicate_urls(mock_site, tmp_path):
    """Test validator catches duplicate URLs."""
    sitemap_path = tmp_path / 'sitemap.xml'
    sitemap_content = '''<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://example.com/page1/</loc>
    </url>
    <url>
        <loc>https://example.com/page1/</loc>
    </url>
</urlset>'''
    sitemap_path.write_text(sitemap_content)
    
    validator = SitemapValidator()
    results = validator.validate(mock_site)
    
    assert any(r.status == CheckStatus.ERROR for r in results)
    assert any("duplicate" in r.message.lower() for r in results)


def test_sitemap_validator_missing_loc(mock_site, tmp_path):
    """Test validator catches URLs without <loc>."""
    sitemap_path = tmp_path / 'sitemap.xml'
    sitemap_content = '''<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <changefreq>weekly</changefreq>
    </url>
</urlset>'''
    sitemap_path.write_text(sitemap_content)
    
    validator = SitemapValidator()
    results = validator.validate(mock_site)
    
    assert any(r.status == CheckStatus.ERROR for r in results)
    assert any("missing" in r.message.lower() and "loc" in r.message.lower() for r in results)


def test_sitemap_validator_coverage_warning(mock_site, tmp_path):
    """Test validator warns about coverage issues."""
    # Site has 2 publishable pages
    sitemap_path = tmp_path / 'sitemap.xml'
    sitemap_content = '''<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://example.com/page1/</loc>
    </url>
</urlset>'''
    sitemap_path.write_text(sitemap_content)
    
    validator = SitemapValidator()
    results = validator.validate(mock_site)
    
    # Should warn about missing pages
    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("missing" in r.message.lower() or "publishable" in r.message.lower() for r in results)


def test_sitemap_validator_name_and_description():
    """Test validator metadata."""
    validator = SitemapValidator()
    
    assert validator.name == "Sitemap"
    assert "sitemap" in validator.description.lower()
    assert validator.enabled_by_default is True

