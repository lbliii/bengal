"""
Unit tests for NavTree navigation architecture.

Tests cover:
- NavNode: dict-like access, iteration, lookup
- NavTree: building, version filtering, shared content
- NavTreeContext: active trail overlay
- NavTreeCache: caching and thread safety
- Version URL fallback cascade
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock

import pytest

from bengal.core.nav_tree import NavNode, NavTree, NavTreeCache, NavTreeContext
from bengal.core.page import Page
from bengal.core.section import Section
from bengal.core.site import Site


class TestNavNode:
    """Test NavNode dataclass functionality."""

    @pytest.fixture
    def simple_node(self):
        """Create a simple NavNode for testing."""
        return NavNode(
            id="test-node",
            title="Test Node",
            _path="/test/",
            icon="test-icon",
            weight=10,
        )

    @pytest.fixture
    def node_with_children(self):
        """Create a NavNode with children."""
        parent = NavNode(
            id="parent",
            title="Parent",
            _path="/parent/",
            weight=0,
        )
        child1 = NavNode(
            id="child1",
            title="Child 1",
            _path="/parent/child1/",
            weight=1,
        )
        child2 = NavNode(
            id="child2",
            title="Child 2",
            _path="/parent/child2/",
            weight=2,
        )
        parent.children = [child1, child2]
        return parent

    def test_dict_like_access(self, simple_node):
        """Test dict-like access via __getitem__."""
        assert simple_node["title"] == "Test Node"
        assert simple_node["_path"] == "/test/"
        assert simple_node["icon"] == "test-icon"
        assert simple_node["weight"] == 10

    def test_dict_like_access_raises_keyerror(self, simple_node):
        """Test that missing keys raise KeyError."""
        with pytest.raises(KeyError):
            _ = simple_node["nonexistent"]

    def test_get_method(self, simple_node):
        """Test .get() method with default."""
        assert simple_node.get("title") == "Test Node"
        assert simple_node.get("nonexistent") is None
        assert simple_node.get("nonexistent", "default") == "default"

    def test_keys_method(self, simple_node):
        """Test .keys() returns expected attributes."""
        keys = simple_node.keys()
        assert "id" in keys
        assert "title" in keys
        assert "_path" in keys
        assert "has_children" in keys
        assert "depth" in keys

    def test_has_children_property(self, simple_node, node_with_children):
        """Test has_children property."""
        assert simple_node.has_children is False
        assert node_with_children.has_children is True

    def test_depth_property(self, simple_node):
        """Test depth property."""
        assert simple_node.depth == 0
        simple_node._depth = 2
        assert simple_node.depth == 2

    def test_walk_iteration(self, node_with_children):
        """Test walk() iterates over node and all descendants."""
        nodes = list(node_with_children.walk())
        assert len(nodes) == 3  # parent + 2 children
        assert nodes[0] == node_with_children
        assert nodes[1] == node_with_children.children[0]
        assert nodes[2] == node_with_children.children[1]


class TestNavTree:
    """Test NavTree building and operations."""

    @pytest.fixture
    def simple_site(self, tmp_path):
        """Create a simple site with sections and pages."""
        site = Site(root_path=tmp_path, config={"title": "Test Site"})

        # Create sections with proper setup
        section1 = Section(name="docs", path=tmp_path / "content" / "docs")
        section1._site = site
        section2 = Section(name="blog", path=tmp_path / "content" / "blog")
        section2._site = site

        # Set nav_title via metadata (nav_title property reads from metadata)
        section1.metadata["nav_title"] = "Docs"
        section2.metadata["nav_title"] = "Blog"

        # Create pages with proper _path setup
        # cached_property stores value in __dict__ once computed, so we set it there
        page1 = Page(
            source_path=tmp_path / "content" / "docs" / "page1.md",
            _raw_content="# Page 1",
            _raw_metadata={"title": "Page 1", "weight": 1},
        )
        page1._site = site
        page1.__dict__["_path"] = "/docs/page1/"

        page2 = Page(
            source_path=tmp_path / "content" / "docs" / "page2.md",
            _raw_content="# Page 2",
            _raw_metadata={"title": "Page 2", "weight": 2},
        )
        page2._site = site
        page2.__dict__["_path"] = "/docs/page2/"

        page3 = Page(
            source_path=tmp_path / "content" / "blog" / "post1.md",
            _raw_content="# Post 1",
            _raw_metadata={"title": "Post 1"},
        )
        page3._site = site
        page3.__dict__["_path"] = "/blog/post1/"

        # Associate pages with sections
        section1.pages = [page1, page2]
        section2.pages = [page3]

        # Set _path for sections via __dict__ (cached_property override)
        section1.__dict__["_path"] = "/docs/"
        section2.__dict__["_path"] = "/blog/"

        # Set up site structure
        site.sections = [section1, section2]
        site.pages = [page1, page2, page3]

        return site

    @pytest.fixture
    def versioned_site(self, tmp_path):
        """Create a versioned site for testing."""
        site = Site(
            root_path=tmp_path,
            config={
                "title": "Versioned Site",
                "versioning": {"enabled": True, "versions": ["v1", "v2"]},
            },
        )

        # Version config is set up automatically from config in Site.__post_init__
        # No need to mock it

        # Create v1 section
        section_v1 = Section(name="docs", path=tmp_path / "content" / "_versions" / "v1" / "docs")
        section_v1._site = site
        page_v1 = Page(
            source_path=tmp_path / "content" / "_versions" / "v1" / "docs" / "guide.md",
            _raw_content="# Guide",
            _raw_metadata={"title": "Guide"},
        )
        page_v1.__dict__["_path"] = "/v1/docs/guide/"
        page_v1.version = "v1"
        section_v1.pages = [page_v1]

        # Create v2 section
        section_v2 = Section(name="docs", path=tmp_path / "content" / "_versions" / "v2" / "docs")
        section_v2._site = site
        page_v2 = Page(
            source_path=tmp_path / "content" / "_versions" / "v2" / "docs" / "guide.md",
            _raw_content="# Guide",
            _raw_metadata={"title": "Guide"},
        )
        page_v2.__dict__["_path"] = "/v2/docs/guide/"
        page_v2.version = "v2"
        section_v2.pages = [page_v2]

        # Mock pages_for_version
        def pages_for_version(version_id):
            if version_id == "v1":
                return [page_v1]
            elif version_id == "v2":
                return [page_v2]
            return []

        section_v1.pages_for_version = pages_for_version
        section_v2.pages_for_version = pages_for_version

        # Mock subsections_for_version
        section_v1.subsections_for_version = Mock(return_value=[])
        section_v2.subsections_for_version = Mock(return_value=[])

        site.sections = [section_v1, section_v2]
        site.pages = [page_v1, page_v2]
        # versions property is computed from version_config automatically

        return site

    def test_build_simple_site(self, simple_site):
        """Test building NavTree from simple site."""
        tree = NavTree.build(simple_site)

        assert tree.root.id == "nav-root"
        assert tree.root.title == "Test Site"
        assert tree.root._path == "/"
        assert len(tree.root.children) == 2  # docs and blog sections

    def test_build_versioned_site(self, versioned_site):
        """Test building NavTree with version filtering."""
        tree_v1 = NavTree.build(versioned_site, version_id="v1")
        tree_v2 = NavTree.build(versioned_site, version_id="v2")

        # Each version should have its own tree
        assert tree_v1.version_id == "v1"
        assert tree_v2.version_id == "v2"

        # Verify version lists
        assert "v1" in tree_v1.versions
        assert "v2" in tree_v1.versions

    def test_nav_tree_includes_sections_with_only_index_pages(self, tmp_path):
        """Test that sections with only index pages are included in navigation."""

        site = Site(
            root_path=tmp_path,
            config={
                "title": "Test Site",
                "versioning": {"enabled": True, "versions": ["v1"]},
            },
        )

        # Create a section with only an index page for v1
        section = Section(name="docs", path=tmp_path / "content" / "_versions" / "v1" / "docs")
        section._site = site

        index_page = Page(
            source_path=tmp_path / "content" / "_versions" / "v1" / "docs" / "_index.md",
            _raw_content="# Docs",
            _raw_metadata={"title": "Docs"},
        )
        index_page.__dict__["_path"] = "/docs/"
        index_page.version = "v1"
        index_page._section_path = section.path
        index_page._site = site

        section.index_page = index_page
        section.pages = [index_page]
        # Set nav_title via metadata and _path via __dict__ (cached_property)
        section.metadata["nav_title"] = "Docs"
        section.__dict__["_path"] = "/docs/"

        # Mock version-aware methods
        def pages_for_version(version_id):
            if version_id == "v1":
                return [index_page]
            return []

        def subsections_for_version(version_id):
            return []

        def has_content_for_version(version_id):
            return version_id == "v1"  # Has index page

        section.pages_for_version = pages_for_version
        section.subsections_for_version = subsections_for_version
        section.has_content_for_version = has_content_for_version

        site.sections = [section]
        site.pages = [index_page]

        # Build nav tree for v1
        tree_v1 = NavTree.build(site, version_id="v1")

        # Section should be included even though it only has an index page
        assert len(tree_v1.root.children) > 0
        docs_node = tree_v1.find("/docs/")
        assert docs_node is not None, "Section with only index page should be in nav tree"

    def test_nav_tree_filters_empty_sections(self, tmp_path):
        """Test that sections with no content for a version are excluded."""

        site = Site(
            root_path=tmp_path,
            config={
                "title": "Test Site",
                "versioning": {"enabled": True, "versions": ["v1", "v2"]},
            },
        )

        # Create section with content only for v1
        section_v1_only = Section(
            name="docs", path=tmp_path / "content" / "_versions" / "v1" / "docs"
        )
        section_v1_only._site = site

        page_v1 = Page(
            source_path=tmp_path / "content" / "_versions" / "v1" / "docs" / "guide.md",
            _raw_content="# Guide",
            _raw_metadata={"title": "Guide"},
        )
        page_v1.__dict__["_path"] = "/docs/v1/guide/"
        page_v1.version = "v1"
        page_v1._section_path = section_v1_only.path
        page_v1._site = site

        section_v1_only.pages = [page_v1]

        # Mock version-aware methods
        def pages_for_version(version_id):
            if version_id == "v1":
                return [page_v1]
            return []

        def subsections_for_version(version_id):
            return []

        def has_content_for_version(version_id):
            return version_id == "v1"

        section_v1_only.pages_for_version = pages_for_version
        section_v1_only.subsections_for_version = subsections_for_version
        section_v1_only.has_content_for_version = has_content_for_version

        site.sections = [section_v1_only]
        site.pages = [page_v1]

        # Build nav tree for v1 - should include section
        tree_v1 = NavTree.build(site, version_id="v1")
        assert len(tree_v1.root.children) > 0

        # Build nav tree for v2 - should exclude section (no content)
        tree_v2 = NavTree.build(site, version_id="v2")
        assert len(tree_v2.root.children) == 0, "Section with no v2 content should be excluded"

    def test_nav_tree_includes_sections_with_subsections_only(self, tmp_path):
        """Test that sections with only subsections (no direct pages) are included."""

        site = Site(
            root_path=tmp_path,
            config={
                "title": "Test Site",
                "versioning": {"enabled": True, "versions": ["v1"]},
            },
        )

        # Create parent section
        parent_section = Section(
            name="docs", path=tmp_path / "content" / "_versions" / "v1" / "docs"
        )
        parent_section._site = site
        parent_section.metadata["nav_title"] = "Docs"
        parent_section.__dict__["_path"] = "/docs/"

        # Create subsection with a page
        subsection = Section(
            name="guide", path=tmp_path / "content" / "_versions" / "v1" / "docs" / "guide"
        )
        subsection._site = site
        subsection.parent = parent_section
        subsection.metadata["nav_title"] = "Guide"
        subsection.__dict__["_path"] = "/docs/guide/"

        page = Page(
            source_path=tmp_path / "content" / "_versions" / "v1" / "docs" / "guide" / "page.md",
            _raw_content="# Page",
            _raw_metadata={"title": "Page"},
        )
        page.__dict__["_path"] = "/docs/guide/page/"
        page.version = "v1"
        page._section_path = subsection.path
        page._site = site

        subsection.pages = [page]
        parent_section.subsections = [subsection]

        # Mock version-aware methods for parent
        def parent_pages_for_version(version_id):
            return []  # No direct pages

        def parent_subsections_for_version(version_id):
            if version_id == "v1":
                return [subsection]
            return []

        def parent_has_content_for_version(version_id):
            return version_id == "v1"  # Has subsection with content

        # Mock version-aware methods for subsection
        def subsection_pages_for_version(version_id):
            if version_id == "v1":
                return [page]
            return []

        def subsection_subsections_for_version(version_id):
            return []

        def subsection_has_content_for_version(version_id):
            return version_id == "v1"

        parent_section.pages_for_version = parent_pages_for_version
        parent_section.subsections_for_version = parent_subsections_for_version
        parent_section.has_content_for_version = parent_has_content_for_version

        subsection.pages_for_version = subsection_pages_for_version
        subsection.subsections_for_version = subsection_subsections_for_version
        subsection.has_content_for_version = subsection_has_content_for_version

        site.sections = [parent_section]
        site.pages = [page]

        # Build nav tree for v1
        tree_v1 = NavTree.build(site, version_id="v1")

        # Parent section should be included (has subsection with content)
        assert len(tree_v1.root.children) > 0
        docs_node = tree_v1.find("/docs/")
        assert docs_node is not None, "Section with subsections should be in nav tree"

    def test_flat_nodes_property(self, simple_site):
        """Test flat_nodes cached property."""
        tree = NavTree.build(simple_site)
        flat = tree.flat_nodes

        assert isinstance(flat, dict)
        assert "/docs/page1/" in flat
        assert "/docs/page2/" in flat
        assert "/blog/post1/" in flat

    def test_urls_property(self, simple_site):
        """Test urls cached property."""
        tree = NavTree.build(simple_site)
        urls = tree.urls

        assert isinstance(urls, set)
        assert "/docs/page1/" in urls
        assert "/docs/page2/" in urls
        assert "/blog/post1/" in urls

    def test_find_method(self, simple_site):
        """Test find() method for O(1) lookup."""
        tree = NavTree.build(simple_site)

        found = tree.find("/docs/page1/")
        assert found is not None
        assert found.title == "Page 1"

        not_found = tree.find("/nonexistent/")
        assert not_found is None

    def test_context(self, simple_site):
        """Test context() creates NavTreeContext."""
        tree = NavTree.build(simple_site)
        page = simple_site.pages[0]  # Get first page

        context = tree.context(page)

        assert isinstance(context, NavTreeContext)
        assert context.tree == tree
        assert context.page == page


class TestNavTreeContext:
    """Test NavTreeContext active trail overlay."""

    @pytest.fixture
    def tree_with_pages(self, tmp_path):
        """Create a NavTree with nested structure."""
        site = Site(root_path=tmp_path, config={"title": "Test Site"})
        # Versioning disabled by default

        # Create nested sections
        root_section = Section(name="docs", path=tmp_path / "content" / "docs")
        root_section._site = site
        root_section.__dict__["_path"] = "/docs/"
        subsection = Section(name="guide", path=tmp_path / "content" / "docs" / "guide")
        subsection._site = site
        subsection.parent = root_section
        subsection.__dict__["_path"] = "/docs/guide/"

        # Create pages with proper _path
        root_page = Page(
            source_path=tmp_path / "content" / "docs" / "_index.md",
            _raw_content="# Docs",
            _raw_metadata={"title": "Docs"},
        )
        root_page._site = site
        root_page.__dict__["_path"] = "/docs/"
        root_section.index_page = root_page

        sub_page = Page(
            source_path=tmp_path / "content" / "docs" / "guide" / "page.md",
            _raw_content="# Page",
            _raw_metadata={"title": "Page"},
        )
        sub_page._site = site
        sub_page.__dict__["_path"] = "/docs/guide/page/"

        root_section.pages = [root_page]
        subsection.pages = [sub_page]
        root_section.subsections = [subsection]

        site.sections = [root_section]
        site.pages = [root_page, sub_page]

        # Register sections in site registry for path-based lookups
        site.register_sections()

        # Set up section references on pages using the _section setter
        # This stores the path/URL for lookup
        root_page._section = root_section
        sub_page._section = subsection

        tree = NavTree.build(site)
        return tree, sub_page

    def test_is_active(self, tree_with_pages):
        """Test is_active() identifies nodes in active trail."""
        tree, current_page = tree_with_pages
        context = NavTreeContext(tree, current_page)

        # Current page should be active (NavTree uses _path)
        current_node = tree.find(current_page._path)
        assert current_node is not None, f"Page {current_page._path} should be in nav tree"
        assert context.is_active(current_node) is True

        # Parent section should be active
        parent_node = tree.find("/docs/")
        assert parent_node is not None
        assert context.is_active(parent_node) is True

    def test_is_current(self, tree_with_pages):
        """Test is_current() identifies only the current page."""
        tree, current_page = tree_with_pages
        context = NavTreeContext(tree, current_page)

        # Current page should be current (NavTree uses _path)
        current_node = tree.find(current_page._path)
        assert current_node is not None, f"Page {current_page._path} should be in nav tree"
        assert context.is_current(current_node) is True

        # Parent should not be current
        parent_node = tree.find("/docs/")
        assert parent_node is not None
        assert context.is_current(parent_node) is False

    def test_immutability(self, tree_with_pages):
        """Test that context doesn't mutate cached tree."""
        tree, current_page = tree_with_pages
        original_urls = tree.urls.copy()

        # Create context (this should not mutate the cached tree)
        NavTreeContext(tree, current_page)

        # Tree should be unchanged
        assert tree.urls == original_urls
        assert tree.flat_nodes == tree.flat_nodes  # Same object


class TestNavNodeProxy:
    """Test NavNodeProxy URL handling with baseurl.

    Critical for GitHub Pages and subdirectory deployments.
    NavNodeProxy.href should apply baseurl, while _path should not.

    """

    @pytest.fixture
    def tree_with_baseurl(self, tmp_path):
        """Create a tree with baseurl configured for testing."""
        # Create site with baseurl configured (simulates GitHub Pages)
        config = {
            "title": "Test Site",
            "baseurl": "/bengal",  # GitHub Pages subdirectory
        }
        site = Site(root_path=tmp_path, config=config)

        # Create a simple section with an index page
        docs_path = tmp_path / "content" / "docs"
        docs_path.mkdir(parents=True)
        (docs_path / "_index.md").write_text("---\ntitle: Docs\n---\n# Docs")

        section = Section(name="docs", path=docs_path)
        section._site = site
        section.__dict__["_path"] = "/docs/"

        # Create a page in the section
        page_path = docs_path / "getting-started.md"
        page_path.write_text("---\ntitle: Getting Started\n---\n# Getting Started")
        page = Page(source_path=page_path)
        page._site = site
        page._section = section
        page._raw_metadata = {"title": "Getting Started"}
        # Simulate output path being set
        page.output_path = tmp_path / "public" / "docs" / "getting-started" / "index.html"
        site.output_dir = tmp_path / "public"
        # Set _path directly for test
        page.__dict__["_path"] = "/docs/getting-started/"

        section.add_page(page)
        site.sections = [section]

        tree = NavTree.build(site)
        return tree, page, site

    def test_proxy_url_includes_baseurl(self, tree_with_baseurl):
        """Test that NavNodeProxy.url includes baseurl for templates."""
        tree, current_page, site = tree_with_baseurl
        context = NavTreeContext(tree, current_page)

        # Get the wrapped root node (NavNodeProxy)
        root_proxy = context._wrap_node(tree.root)

        # The proxy's .href should include baseurl
        # The internal _path is "/docs/" but public URL is "/bengal/docs/"
        assert root_proxy.href.startswith("/bengal/"), (
            f"NavNodeProxy.href should include baseurl. "
            f"Got: {root_proxy.href}, expected to start with /bengal/"
        )

    def test_proxy_path_excludes_baseurl(self, tree_with_baseurl):
        """Test that NavNodeProxy._path does NOT include baseurl."""
        tree, current_page, site = tree_with_baseurl
        context = NavTreeContext(tree, current_page)

        # Get the wrapped root node (NavNodeProxy)
        root_proxy = context._wrap_node(tree.root)

        # _path should NOT include baseurl (used for internal lookups)
        assert not root_proxy._path.startswith("/bengal/"), (
            f"NavNodeProxy._path should NOT include baseurl. Got: {root_proxy._path}"
        )
        # Should start with / but not /bengal/
        assert root_proxy._path.startswith("/"), (
            f"_path should start with /. Got: {root_proxy._path}"
        )

    def test_proxy_href_no_baseurl_equals_path(self, tmp_path):
        """Test that NavNodeProxy.href equals _path when no baseurl configured."""
        # Create site WITHOUT baseurl (local development)
        site = Site(root_path=tmp_path, config={"title": "Test Site"})

        # Create minimal section
        docs_path = tmp_path / "content" / "docs"
        docs_path.mkdir(parents=True)
        (docs_path / "_index.md").write_text("---\ntitle: Docs\n---\n")

        section = Section(name="docs", path=docs_path)
        section._site = site
        section.__dict__["_path"] = "/docs/"
        site.sections = [section]

        # Create a page
        page_path = docs_path / "test.md"
        page_path.write_text("---\ntitle: Test\n---\n")
        page = Page(source_path=page_path)
        page._site = site
        page._raw_metadata = {"title": "Test"}
        page.__dict__["_path"] = "/docs/test/"

        section.add_page(page)

        tree = NavTree.build(site)
        context = NavTreeContext(tree, page)
        root_proxy = context._wrap_node(tree.root)

        # Without baseurl, href and _path should be the same
        assert root_proxy.href == root_proxy._path, "Without baseurl, href should equal _path"

    def test_proxy_dict_access_href_includes_baseurl(self, tree_with_baseurl):
        """Test that dict-style access ['href'] also includes baseurl."""
        tree, current_page, site = tree_with_baseurl
        context = NavTreeContext(tree, current_page)
        root_proxy = context._wrap_node(tree.root)

        # Templates often use item['href'] - should also include baseurl
        assert root_proxy["href"].startswith("/bengal/"), (
            f"Dict access ['href'] should include baseurl. Got: {root_proxy['href']}"
        )

    def test_proxy_children_also_have_baseurl(self, tree_with_baseurl):
        """Test that child proxies also have baseurl applied."""
        tree, current_page, site = tree_with_baseurl
        context = NavTreeContext(tree, current_page)
        root_proxy = context._wrap_node(tree.root)

        # Check children if any
        for child in root_proxy.children:
            assert child.href.startswith("/bengal/"), (
                f"Child proxy href should include baseurl. Got: {child.href}"
            )


class TestNavTreeCache:
    """Test NavTreeCache caching and invalidation."""

    @pytest.fixture
    def mock_site(self, tmp_path):
        """Create a mock site for caching tests."""
        site = Site(root_path=tmp_path, config={"title": "Cache Test Site"})
        # Versioning disabled by default (no versioning in config)
        site.sections = []
        return site

    def test_cache_hit_same_version(self, mock_site):
        """Test that cache returns same tree for same version."""
        NavTreeCache.invalidate()

        tree1 = NavTreeCache.get(mock_site, version_id=None)
        tree2 = NavTreeCache.get(mock_site, version_id=None)

        # Should be the same object (cached)
        assert tree1 is tree2

    def test_cache_different_versions(self, mock_site):
        """Test that different versions get different trees."""
        NavTreeCache.invalidate()

        tree_none = NavTreeCache.get(mock_site, version_id=None)
        tree_v1 = NavTreeCache.get(mock_site, version_id="v1")
        tree_v2 = NavTreeCache.get(mock_site, version_id="v2")

        # All should be different objects
        assert tree_none is not tree_v1
        assert tree_v1 is not tree_v2
        assert tree_none is not tree_v2

    def test_cache_invalidation_all(self, mock_site):
        """Test that invalidate() clears all cached trees."""
        NavTreeCache.invalidate()

        tree1 = NavTreeCache.get(mock_site, version_id=None)
        NavTreeCache.invalidate()

        tree2 = NavTreeCache.get(mock_site, version_id=None)

        # Should be different objects after invalidation
        assert tree1 is not tree2

    def test_cache_invalidation_specific_version(self, mock_site):
        """Test that invalidate(version_id) clears only that version."""
        NavTreeCache.invalidate()

        tree_none = NavTreeCache.get(mock_site, version_id=None)
        tree_v1 = NavTreeCache.get(mock_site, version_id="v1")

        # Invalidate only v1
        NavTreeCache.invalidate(version_id="v1")

        # None should still be cached
        tree_none_after = NavTreeCache.get(mock_site, version_id=None)
        assert tree_none is tree_none_after

        # v1 should be rebuilt
        tree_v1_after = NavTreeCache.get(mock_site, version_id="v1")
        assert tree_v1 is not tree_v1_after

    def test_cache_site_change_invalidation(self, mock_site, tmp_path):
        """Test that site object change triggers full invalidation."""
        NavTreeCache.invalidate()

        tree1 = NavTreeCache.get(mock_site, version_id=None)

        # Create new site object
        new_site = Site(root_path=tmp_path, config={"title": "New Site"})
        new_site.sections = []

        tree2 = NavTreeCache.get(new_site, version_id=None)

        # Should be different (new site triggered invalidation)
        assert tree1 is not tree2

    def test_thread_safety_concurrent_access(self, mock_site):
        """Test thread safety under concurrent cache access."""
        NavTreeCache.invalidate()

        def get_tree(_):
            return NavTreeCache.get(mock_site, version_id=None)

        # Concurrent access from multiple threads
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(get_tree, i) for i in range(20)]
            results = [f.result() for f in as_completed(futures)]

        # All results should be the same object (cached)
        assert all(r is results[0] for r in results)

    def test_thread_safety_concurrent_invalidation(self, mock_site):
        """Test thread safety when invalidating during concurrent reads."""
        NavTreeCache.invalidate()

        def get_tree(_):
            return NavTreeCache.get(mock_site, version_id=None)

        def invalidate_cache():
            NavTreeCache.invalidate()

        # Mix of reads and invalidations
        with ThreadPoolExecutor(max_workers=8) as executor:
            read_futures = [executor.submit(get_tree, i) for i in range(10)]
            invalidation_futures = [executor.submit(invalidate_cache) for _ in range(5)]

            # Wait for all
            reads = [f.result() for f in as_completed(read_futures)]
            [f.result() for f in as_completed(invalidation_futures)]

        # Should not raise exceptions (thread safety)
        assert len(reads) == 10


class TestGetTargetUrl:
    """Test version URL fallback cascade."""

    @pytest.fixture
    def versioned_site_with_fallback(self, tmp_path):
        """Create a versioned site for fallback testing."""
        # This is a simplified test - full implementation would require
        # more complex site setup with version config
        site = Site(
            root_path=tmp_path,
            config={
                "title": "Versioned Site",
                "versioning": {"enabled": True, "versions": ["v1", "v2"]},
            },
        )
        return site

    def test_version_switching_uses_site_api(self, versioned_site_with_fallback):
        """Test that version switching uses Site API (public contract)."""
        site = versioned_site_with_fallback
        site.discover_content()

        # Create a mock page
        page = Mock(spec=Page)
        page._path = "/v1/docs/guide/"
        page.href = "/v1/docs/guide/"
        page.version = "v1"
        page._site = site

        # Version switching should use Site API, not NavTree method
        # (NavTree.get_target_url was removed to eliminate core → rendering coupling)
        v2_version = {"id": "v2", "latest": False, "url_prefix": "/v2"}
        target_url = site.get_version_target_url(page, v2_version)

        assert isinstance(target_url, str)
        assert len(target_url) > 0
