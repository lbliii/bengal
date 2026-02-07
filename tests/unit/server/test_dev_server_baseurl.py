"""
Test that dev server correctly clears baseurl during development.

This prevents 404 errors when serving files locally since the dev server
serves from the root (/) not from a subdirectory (/bengal).
"""

import json

import pytest


class TestBaseurlClearingLogic:
    """Test the baseurl clearing decision logic in _prepare_dev_config."""

    def _should_clear_baseurl(self, baseurl_value: str) -> bool:
        """Simulate the baseurl clearing decision from _prepare_dev_config."""
        baseurl = (baseurl_value or "").strip()
        # "/" is equivalent to no baseurl (dev server serves from root)
        if not baseurl or baseurl == "/":
            return False  # No baseurl to clear
        return True

    def test_empty_baseurl_does_not_trigger_clear(self):
        """Empty baseurl should not trigger cache clearing."""
        assert self._should_clear_baseurl("") is False

    def test_slash_baseurl_does_not_trigger_clear(self):
        """Baseurl '/' should not trigger cache clearing (serves from root)."""
        assert self._should_clear_baseurl("/") is False

    def test_subdirectory_baseurl_triggers_clear(self):
        """Baseurl '/bengal' should trigger cache clearing."""
        assert self._should_clear_baseurl("/bengal") is True

    def test_subdirectory_with_trailing_slash_triggers_clear(self):
        """Baseurl '/docs/' should trigger cache clearing."""
        assert self._should_clear_baseurl("/docs/") is True

    def test_whitespace_only_baseurl_does_not_trigger_clear(self):
        """Whitespace-only baseurl should not trigger cache clearing."""
        assert self._should_clear_baseurl("   ") is False

    def test_none_baseurl_does_not_trigger_clear(self):
        """None baseurl should not trigger cache clearing."""
        # Simulates cfg.get("baseurl") returning None
        assert self._should_clear_baseurl(None) is False  # type: ignore[arg-type]


@pytest.mark.bengal(testroot="test-baseurl", confoverrides={"site.baseurl": "/bengal"})
def test_dev_server_clears_baseurl_in_html(site, build_site):
    """Test that baseurl is cleared in HTML when built by dev server simulation."""
    # Simulate dev server behavior: clear baseurl before build
    # Access from site section (supports both Config and dict)
    if hasattr(site.config, "site"):
        original_baseurl = site.config.site.baseurl or ""
    else:
        original_baseurl = site.config.get("site", {}).get("baseurl", "")
    assert original_baseurl == "/bengal", "Test setup: baseurl should be /bengal initially"

    # Clear baseurl (what dev server does)
    site.config["baseurl"] = ""

    # Build with cleared baseurl (non-incremental to regenerate HTML)
    build_site(incremental=False)

    # Verify HTML has empty baseurl, not /bengal
    html = (site.output_dir / "index.html").read_text(encoding="utf-8")

    # Check meta tags don't have /bengal
    assert (
        '<meta name="bengal:baseurl" _raw_content="">' in html
        or '_raw_content="/bengal"' not in html
    ), "HTML should not contain /bengal baseurl after clearing"

    # CSS links should not have /bengal prefix
    assert "/bengal/assets/" not in html, "Asset links should not have /bengal prefix"

    # index.json URL should not have /bengal prefix
    if "bengal:index_url" in html:
        assert '_raw_content="/bengal/index.json"' not in html, (
            "index.json URL should not have /bengal prefix"
        )


@pytest.mark.bengal(testroot="test-baseurl", confoverrides={"site.baseurl": "/bengal"})
def test_dev_server_clears_baseurl_in_index_json(site, build_site):
    """Test that index.json is accessible at root when baseurl is cleared."""
    # Simulate dev server: clear baseurl
    site.config["baseurl"] = ""

    # Build
    build_site(incremental=False)

    # Verify index.json exists at root (not in /bengal subdirectory)
    index_path = site.output_dir / "index.json"
    assert index_path.exists(), "index.json should exist at root"

    # Verify baseurl in index.json is empty
    data = json.loads(index_path.read_text(encoding="utf-8"))
    assert data.get("site", {}).get("baseurl") == "", (
        f"index.json baseurl should be empty, got: {data.get('site', {}).get('baseurl')}"
    )

    # Verify page URLs don't have /bengal prefix
    if data.get("pages"):
        first_page = data["pages"][0]
        page_url = first_page.get("url", "")
        assert not page_url.startswith("/bengal/"), (
            f"Page URLs in index.json should not have /bengal prefix, got: {page_url}"
        )
