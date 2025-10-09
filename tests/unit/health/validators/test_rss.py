"""
Tests for RSS validator.
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock

from bengal.health.validators.rss import RSSValidator
from bengal.health.report import CheckStatus


@pytest.fixture
def mock_site(tmp_path):
    """Create a mock site for testing."""
    site = Mock()
    site.output_dir = tmp_path
    site.config = {'baseurl': 'https://example.com'}
    site.pages = []
    return site


@pytest.fixture
def site_with_dated_pages(mock_site):
    """Create a site with dated pages."""
    page1 = Mock()
    page1.date = datetime(2025, 1, 1)
    
    page2 = Mock()
    page2.date = datetime(2025, 1, 2)
    
    page3 = Mock()
    page3.date = None
    
    mock_site.pages = [page1, page2, page3]
    return mock_site


def test_rss_validator_no_dated_content(mock_site):
    """Test validator with no dated content."""
    validator = RSSValidator()
    results = validator.validate(mock_site)
    
    assert len(results) > 0
    assert any(r.status == CheckStatus.INFO for r in results)
    assert any("No dated content" in r.message for r in results)


def test_rss_validator_missing_file(site_with_dated_pages):
    """Test validator warns when RSS not generated."""
    validator = RSSValidator()
    results = validator.validate(site_with_dated_pages)
    
    assert len(results) > 0
    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("not generated" in r.message for r in results)


def test_rss_validator_valid_feed(site_with_dated_pages, tmp_path):
    """Test validator passes for valid RSS feed."""
    # Create valid RSS
    rss_path = tmp_path / 'rss.xml'
    rss_content = '''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Test Site</title>
        <link>https://example.com</link>
        <description>Test Description</description>
        <item>
            <title>Post 1</title>
            <link>https://example.com/post1/</link>
            <guid>https://example.com/post1/</guid>
            <description>Test post</description>
            <pubDate>Mon, 01 Jan 2025 00:00:00 +0000</pubDate>
        </item>
    </channel>
</rss>'''
    rss_path.write_text(rss_content)
    
    validator = RSSValidator()
    results = validator.validate(site_with_dated_pages)
    
    # Should have success results
    assert any(r.status == CheckStatus.SUCCESS for r in results)
    assert any("RSS file exists" in r.message for r in results)
    assert any("well-formed" in r.message for r in results)


def test_rss_validator_malformed_xml(site_with_dated_pages, tmp_path):
    """Test validator catches malformed XML."""
    # Create malformed RSS
    rss_path = tmp_path / 'rss.xml'
    rss_content = '<rss><channel></rss>'  # Unclosed channel
    rss_path.write_text(rss_content)
    
    validator = RSSValidator()
    results = validator.validate(site_with_dated_pages)
    
    assert any(r.status == CheckStatus.ERROR for r in results)
    assert any("malformed" in r.message.lower() for r in results)


def test_rss_validator_wrong_version(site_with_dated_pages, tmp_path):
    """Test validator warns about wrong RSS version."""
    rss_path = tmp_path / 'rss.xml'
    rss_content = '''<?xml version="1.0"?>
<rss version="1.0">
    <channel>
        <title>Test</title>
        <link>https://example.com</link>
        <description>Test</description>
    </channel>
</rss>'''
    rss_path.write_text(rss_content)
    
    validator = RSSValidator()
    results = validator.validate(site_with_dated_pages)
    
    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("version" in r.message.lower() for r in results)


def test_rss_validator_missing_required_elements(site_with_dated_pages, tmp_path):
    """Test validator catches missing required elements."""
    rss_path = tmp_path / 'rss.xml'
    rss_content = '''<?xml version="1.0"?>
<rss version="2.0">
    <channel>
        <title>Test</title>
        <!-- Missing link and description -->
    </channel>
</rss>'''
    rss_path.write_text(rss_content)
    
    validator = RSSValidator()
    results = validator.validate(site_with_dated_pages)
    
    assert any(r.status == CheckStatus.ERROR for r in results)
    assert any("required" in r.message.lower() for r in results)


def test_rss_validator_no_items(site_with_dated_pages, tmp_path):
    """Test validator warns when feed has no items."""
    rss_path = tmp_path / 'rss.xml'
    rss_content = '''<?xml version="1.0"?>
<rss version="2.0">
    <channel>
        <title>Test</title>
        <link>https://example.com</link>
        <description>Test</description>
    </channel>
</rss>'''
    rss_path.write_text(rss_content)
    
    validator = RSSValidator()
    results = validator.validate(site_with_dated_pages)
    
    assert any(r.status == CheckStatus.WARNING for r in results)
    assert any("no items" in r.message.lower() for r in results)


def test_rss_validator_relative_urls(site_with_dated_pages, tmp_path):
    """Test validator catches relative URLs."""
    rss_path = tmp_path / 'rss.xml'
    rss_content = '''<?xml version="1.0"?>
<rss version="2.0">
    <channel>
        <title>Test</title>
        <link>https://example.com</link>
        <description>Test</description>
        <item>
            <title>Post 1</title>
            <link>/post1/</link>
            <guid>/post1/</guid>
        </item>
    </channel>
</rss>'''
    rss_path.write_text(rss_content)
    
    validator = RSSValidator()
    results = validator.validate(site_with_dated_pages)
    
    assert any(r.status == CheckStatus.ERROR for r in results)
    assert any("relative" in r.message.lower() for r in results)


def test_rss_validator_name_and_description():
    """Test validator metadata."""
    validator = RSSValidator()
    
    assert validator.name == "RSS Feed"
    assert "RSS feed" in validator.description
    assert validator.enabled_by_default is True

