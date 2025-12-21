"""
Comprehensive tests for href and _path properties.

Tests the new unified URL model across all core classes:
- Page, PageProxy
- Section
- NavNode, NavNodeProxy
- Asset

Covers all baseurl scenarios:
- Empty baseurl ("")
- Path-only baseurl ("/bengal")
- Absolute baseurl ("https://example.com")
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bengal.core.asset.asset_core import Asset
from bengal.core.nav_tree import NavNode, NavNodeProxy, NavTree, NavTreeContext
from bengal.core.page import Page
from bengal.core.page.proxy import PageProxy
from bengal.core.page.page_core import PageCore
from bengal.core.section import Section
from bengal.core.site import Site


class TestPageHrefPath:
    """Test Page.href and Page._path properties."""

    @pytest.mark.parametrize(
        "baseurl,expected_href,expected_path",
        [
            ("", "/docs/getting-started/", "/docs/getting-started/"),
            ("/bengal", "/bengal/docs/getting-started/", "/docs/getting-started/"),
            ("https://example.com", "https://example.com/docs/getting-started/", "/docs/getting-started/"),
        ],
    )
    def test_href_includes_baseurl(self, baseurl, expected_href, expected_path):
        """Test that href includes baseurl while _path does not."""
        site = Site(root_path=Path("/site"), config={"baseurl": baseurl})
        site.output_dir = Path("/site/public")

        page = Page(
            source_path=Path("/content/docs/getting-started.md"),
            metadata={"title": "Getting Started"},
            output_path=Path("/site/public/docs/getting-started/index.html"),
        )
        page._site = site

        assert page.href == expected_href
        assert page._path == expected_path

    def test_href_and_path_properties(self):
        """Test that href and _path properties work correctly."""
        site = Site(root_path=Path("/site"), config={"baseurl": "/bengal"})
        site.output_dir = Path("/site/public")

        page = Page(
            source_path=Path("/content/docs/page.md"),
            metadata={"title": "Page"},
            output_path=Path("/site/public/docs/page/index.html"),
        )
        page._site = site

        # Verify href and _path are correct
        assert page.href == "/bengal/docs/page/"
        assert page._path == "/docs/page/"

    def test_absolute_href(self):
        """Test absolute_href property."""
        # Test with path-only baseurl
        site = Site(root_path=Path("/site"), config={"baseurl": "/bengal"})
        site.output_dir = Path("/site/public")

        page = Page(
            source_path=Path("/content/docs/page.md"),
            metadata={"title": "Page"},
            output_path=Path("/site/public/docs/page/index.html"),
        )
        page._site = site

        # For path-only baseurl, absolute_href returns href as-is
        assert page.absolute_href == "/bengal/docs/page/"

        # Test with absolute baseurl (need new page to avoid cache)
        site2 = Site(root_path=Path("/site"), config={"baseurl": "https://example.com"})
        site2.output_dir = Path("/site/public")

        page2 = Page(
            source_path=Path("/content/docs/page.md"),
            metadata={"title": "Page"},
            output_path=Path("/site/public/docs/page/index.html"),
        )
        page2._site = site2
        assert page2.absolute_href == "https://example.com/docs/page/"

    def test_href_without_output_path(self):
        """Test href falls back correctly when output_path not set."""
        page = Page(
            source_path=Path("/content/docs/page.md"),
            metadata={"title": "Page"},
        )

        # Should use slug-based fallback
        assert page.href == "/page/"
        assert page._path == "/page/"


class TestSectionHrefPath:
    """Test Section.href and Section._path properties."""

    @pytest.mark.parametrize(
        "baseurl,expected_href,expected_path",
        [
            ("", "/docs/", "/docs/"),
            ("/bengal", "/bengal/docs/", "/docs/"),
            ("https://example.com", "https://example.com/docs/", "/docs/"),
        ],
    )
    def test_href_includes_baseurl(self, baseurl, expected_href, expected_path):
        """Test that href includes baseurl while _path does not."""
        site = Site(root_path=Path("/site"), config={"baseurl": baseurl})
        section = Section(name="docs", path=Path("/content/docs"))
        section._site = site

        assert section.href == expected_href
        assert section._path == expected_path

    def test_href_and_path_properties(self):
        """Test that href and _path properties work correctly."""
        site = Site(root_path=Path("/site"), config={"baseurl": "/bengal"})
        section = Section(name="docs", path=Path("/content/docs"))
        section._site = site

        # Verify href and _path are correct
        assert section.href == "/bengal/docs/"
        assert section._path == "/docs/"


class TestNavNodeHrefPath:
    """Test NavNode and NavNodeProxy href/_path properties."""

    def test_navnode_path_field(self):
        """Test that NavNode stores _path field."""
        node = NavNode(
            id="test",
            title="Test",
            _path="/test/",
        )

        assert node._path == "/test/"
        # Backward compatibility
        assert node._path == "/test/"

    def test_navnodeproxy_href_includes_baseurl(self):
        """Test NavNodeProxy.href includes baseurl."""
        node = NavNode(
            id="test",
            title="Test",
            _path="/docs/page/",
        )

        # Create a proper NavTree
        root = NavNode(id="root", title="Root", _path="/")
        tree = NavTree(root=root, version_id=None)

        # Create a mock site
        site = MagicMock()
        site.config = {"baseurl": "/bengal"}

        # Create a page with site reference
        page = Page(
            source_path=Path("/content/docs/page.md"),
            metadata={"title": "Page"},
        )
        page._site = site

        context = NavTreeContext(tree, page, mark_active_trail=False)
        proxy = NavNodeProxy(node, context)

        assert proxy.href == "/bengal/docs/page/"
        assert proxy._path == "/docs/page/"

    def test_navnodeproxy_href_and_path(self):
        """Test NavNodeProxy href and _path properties."""
        node = NavNode(
            id="test",
            title="Test",
            _path="/docs/page/",
        )

        # Create a proper NavTree
        root = NavNode(id="root", title="Root", _path="/")
        tree = NavTree(root=root, version_id=None)

        site = MagicMock()
        site.config = {"baseurl": "/bengal"}

        page = Page(
            source_path=Path("/content/docs/page.md"),
            metadata={"title": "Page"},
        )
        page._site = site

        context = NavTreeContext(tree, page, mark_active_trail=False)
        proxy = NavNodeProxy(node, context)

        # Verify href and _path are correct
        assert proxy.href == "/bengal/docs/page/"
        assert proxy._path == "/docs/page/"

    def test_navnodeproxy_absolute_href(self):
        """Test NavNodeProxy.absolute_href."""
        node = NavNode(
            id="test",
            title="Test",
            _path="/docs/page/",
        )

        # Create a proper NavTree
        root = NavNode(id="root", title="Root", _path="/")
        tree = NavTree(root=root, version_id=None)

        site = MagicMock()
        site.config = {"baseurl": "/bengal"}

        page = Page(
            source_path=Path("/content/docs/page.md"),
            metadata={"title": "Page"},
        )
        page._site = site

        context = NavTreeContext(tree, page, mark_active_trail=False)
        proxy = NavNodeProxy(node, context)

        assert proxy.absolute_href == "/bengal/docs/page/"


class TestAssetHrefPath:
    """Test Asset.href and Asset._path properties."""

    def test_asset_href_includes_baseurl(self):
        """Test Asset.href includes baseurl."""
        site = Site(root_path=Path("/site"), config={"baseurl": "/bengal"})
        site.output_dir = Path("/site/public")

        asset = Asset(
            source_path=Path("/assets/css/style.css"),
            logical_path=Path("assets/css/style.css"),
        )
        asset._site = site

        # Asset href should include baseurl
        assert asset.href.startswith("/bengal/")
        assert asset._path == "assets/css/style.css"

    def test_asset_href_without_site(self):
        """Test Asset.href fallback when site not available."""
        asset = Asset(
            source_path=Path("/assets/css/style.css"),
            logical_path=Path("assets/css/style.css"),
        )

        # Should fallback to simple path
        assert asset.href == "/assets/assets/css/style.css"  # logical_path is used
        assert asset._path == "assets/css/style.css"

    def test_asset_absolute_href(self):
        """Test Asset.absolute_href."""
        site = Site(root_path=Path("/site"), config={"baseurl": "/bengal"})
        site.output_dir = Path("/site/public")

        asset = Asset(
            source_path=Path("/assets/css/style.css"),
            logical_path=Path("assets/css/style.css"),
        )
        asset._site = site

        assert asset.absolute_href == asset.href


class TestPageProxyHrefPath:
    """Test PageProxy.href and PageProxy._path delegation."""

    def test_pageproxy_delegates_to_page(self):
        """Test PageProxy delegates href/_path to underlying page."""
        site = Site(root_path=Path("/site"), config={"baseurl": "/bengal"})
        site.output_dir = Path("/site/public")

        page = Page(
            source_path=Path("/content/docs/page.md"),
            metadata={"title": "Page"},
            output_path=Path("/site/public/docs/page/index.html"),
        )
        page._site = site

        core = PageCore(
            source_path=str(page.source_path),
            title="Page",
        )

        def loader(path: Path) -> Page:
            return page

        proxy = PageProxy(
            source_path=page.source_path,
            metadata=core,
            loader=loader,
        )
        proxy._site = site

        # Proxy should delegate to page
        assert proxy.href == page.href
        assert proxy._path == page._path
        assert proxy.absolute_href == page.absolute_href

    def test_pageproxy_href_and_path(self):
        """Test PageProxy href and _path properties."""
        site = Site(root_path=Path("/site"), config={"baseurl": "/bengal"})
        site.output_dir = Path("/site/public")

        page = Page(
            source_path=Path("/content/docs/page.md"),
            metadata={"title": "Page"},
            output_path=Path("/site/public/docs/page/index.html"),
        )
        page._site = site

        core = PageCore(
            source_path=str(page.source_path),
            title="Page",
        )

        def loader(path: Path) -> Page:
            return page

        proxy = PageProxy(
            source_path=page.source_path,
            metadata=core,
            loader=loader,
        )
        proxy._site = site

        # Verify href and _path are correct
        assert proxy.href == "/bengal/docs/page/"
        assert proxy._path == "/docs/page/"


class TestHrefPathConsistency:
    """Test consistency between href/_path across all classes."""

    def test_all_classes_have_href_and_path(self):
        """Test that all URL-bearing classes have href and _path."""
        site = Site(root_path=Path("/site"), config={"baseurl": "/bengal"})
        site.output_dir = Path("/site/public")

        # Page
        page = Page(
            source_path=Path("/content/docs/page.md"),
            metadata={"title": "Page"},
            output_path=Path("/site/public/docs/page/index.html"),
        )
        page._site = site
        assert hasattr(page, "href")
        assert hasattr(page, "_path")
        assert hasattr(page, "absolute_href")

        # Section
        section = Section(name="docs", path=Path("/content/docs"))
        section._site = site
        assert hasattr(section, "href")
        assert hasattr(section, "_path")
        assert hasattr(section, "absolute_href")

        # Asset
        asset = Asset(
            source_path=Path("/assets/css/style.css"),
            logical_path=Path("assets/css/style.css"),
        )
        asset._site = site
        assert hasattr(asset, "href")
        assert hasattr(asset, "_path")
        assert hasattr(asset, "absolute_href")

        # NavNodeProxy
        node = NavNode(id="test", title="Test", _path="/test/")
        root = NavNode(id="root", title="Root", _path="/")
        tree = NavTree(root=root, version_id=None)
        page_mock = Page(
            source_path=Path("/content/test.md"),
            metadata={"title": "Test"},
        )
        page_mock._site = site
        context = NavTreeContext(tree, page_mock, mark_active_trail=False)
        proxy = NavNodeProxy(node, context)
        assert hasattr(proxy, "href")
        assert hasattr(proxy, "_path")
        assert hasattr(proxy, "absolute_href")

