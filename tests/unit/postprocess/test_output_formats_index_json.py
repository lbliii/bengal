"""
Tests for index.json site-wide search index generation.

This test suite ensures that index.json is always correctly generated with:
- Complete pages array with all site pages
- Valid site metadata (title, baseurl, build_time)
- Section counts aggregated correctly
- Tag counts aggregated and sorted by popularity
- Proper handling of incremental vs full builds
"""

import json
from pathlib import Path
from unittest.mock import Mock

from bengal.postprocess.output_formats import OutputFormatsGenerator


class TestSiteIndexJsonGeneration:
    """Test site-wide index.json generation."""

    def test_generates_index_json_at_site_root(self, tmp_path):
        """Test that index.json is generated at site root."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page1 = self._create_mock_page(
            title="Page One",
            url="/page1/",
            content="Content one",
            output_path=output_dir / "page1/index.html",
        )
        page2 = self._create_mock_page(
            title="Page Two",
            url="/page2/",
            content="Content two",
            output_path=output_dir / "page2/index.html",
        )
        mock_site.pages = [page1, page2]

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}
        generator = OutputFormatsGenerator(mock_site, config)

        # Execute
        generator.generate()

        # Assert
        index_path = output_dir / "index.json"
        assert index_path.exists(), "index.json should exist at site root"

    def test_index_json_has_valid_structure(self, tmp_path):
        """Test that index.json has the expected structure with all required fields."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Test Page",
            url="/test/",
            content="Test content",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}
        generator = OutputFormatsGenerator(mock_site, config)
        generator.generate()

        # Load and validate structure
        index_path = output_dir / "index.json"
        data = json.loads(index_path.read_text())

        # Assert top-level structure
        assert "site" in data, "index.json must have 'site' key"
        assert "pages" in data, "index.json must have 'pages' key"
        assert "sections" in data, "index.json must have 'sections' key"
        assert "tags" in data, "index.json must have 'tags' key"

        # Assert site metadata
        assert isinstance(data["site"], dict)
        assert "title" in data["site"]
        assert "baseurl" in data["site"]
        assert "build_time" in data["site"]

        # Assert collections are lists
        assert isinstance(data["pages"], list)
        assert isinstance(data["sections"], list)
        assert isinstance(data["tags"], list)

    def test_index_json_pages_array_not_empty_with_pages(self, tmp_path):
        """CRITICAL: Test that pages array is populated when site has pages."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        pages = []
        for i in range(5):
            page = self._create_mock_page(
                title=f"Page {i}",
                url=f"/page{i}/",
                content=f"Content {i}",
                output_path=output_dir / f"page{i}/index.html",
            )
            pages.append(page)

        mock_site.pages = pages

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}
        generator = OutputFormatsGenerator(mock_site, config)
        generator.generate()

        # Load index.json
        index_path = output_dir / "index.json"
        data = json.loads(index_path.read_text())

        # CRITICAL ASSERTION: pages array must not be empty
        assert len(data["pages"]) == 5, (
            f"Expected 5 pages in index.json, got {len(data['pages'])}. "
            "This is a critical bug - index.json is useless without pages!"
        )

        # Verify each page has required fields
        for page_data in data["pages"]:
            assert "objectID" in page_data, "Page must have objectID"
            assert "url" in page_data, "Page must have url"
            assert "title" in page_data, "Page must have title"
            assert "excerpt" in page_data, "Page must have excerpt"

    def test_index_json_empty_pages_array_when_no_pages(self, tmp_path):
        """Test that pages array is empty (not null) when site has no pages."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        mock_site.pages = []  # No pages

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}
        generator = OutputFormatsGenerator(mock_site, config)
        generator.generate()

        # Load index.json
        index_path = output_dir / "index.json"
        data = json.loads(index_path.read_text())

        # Should be empty array, not null
        assert isinstance(data["pages"], list)
        assert len(data["pages"]) == 0

    def test_index_json_aggregates_section_counts(self, tmp_path):
        """Test that section counts are correctly aggregated."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        # Create pages in different sections
        pages = []
        for i in range(3):
            page = self._create_mock_page(
                title=f"Docs {i}",
                url=f"/docs/page{i}/",
                content=f"Content {i}",
                output_path=output_dir / f"docs/page{i}/index.html",
                section_name="docs",
            )
            pages.append(page)

        for i in range(2):
            page = self._create_mock_page(
                title=f"Blog {i}",
                url=f"/blog/post{i}/",
                content=f"Content {i}",
                output_path=output_dir / f"blog/post{i}/index.html",
                section_name="blog",
            )
            pages.append(page)

        mock_site.pages = pages

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}
        generator = OutputFormatsGenerator(mock_site, config)
        generator.generate()

        # Load and validate
        index_path = output_dir / "index.json"
        data = json.loads(index_path.read_text())

        # Check section counts
        sections = {s["name"]: s["count"] for s in data["sections"]}
        assert sections["docs"] == 3, "Should have 3 docs pages"
        assert sections["blog"] == 2, "Should have 2 blog pages"

    def test_index_json_aggregates_and_sorts_tag_counts(self, tmp_path):
        """Test that tag counts are aggregated and sorted by popularity."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        # Create pages with different tags
        pages = []
        # 3 pages with "python" tag
        for i in range(3):
            page = self._create_mock_page(
                title=f"Python {i}",
                url=f"/python{i}/",
                content="Content",
                output_path=output_dir / f"python{i}/index.html",
                tags=["python", "tutorial"],
            )
            pages.append(page)

        # 1 page with only "tutorial" tag
        page = self._create_mock_page(
            title="Tutorial",
            url="/tutorial/",
            content="Content",
            output_path=output_dir / "tutorial/index.html",
            tags=["tutorial"],
        )
        pages.append(page)

        mock_site.pages = pages

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}
        generator = OutputFormatsGenerator(mock_site, config)
        generator.generate()

        # Load and validate
        index_path = output_dir / "index.json"
        data = json.loads(index_path.read_text())

        # Check tag counts and sorting (most popular first)
        tags = data["tags"]
        assert len(tags) == 2

        # "tutorial" appears 4 times (3 + 1)
        assert tags[0]["name"] == "tutorial"
        assert tags[0]["count"] == 4

        # "python" appears 3 times
        assert tags[1]["name"] == "python"
        assert tags[1]["count"] == 3

    def test_index_json_includes_page_metadata(self, tmp_path):
        """Test that page summaries include important metadata for search."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Advanced Tutorial",
            url="/tutorial/advanced/",
            content="This is an advanced tutorial about Python programming.",
            output_path=output_dir / "tutorial/advanced/index.html",
            tags=["python", "advanced"],
            section_name="docs",
            metadata={
                "description": "Learn advanced Python concepts",
                "author": "Jane Doe",
                "difficulty": "advanced",
            },
        )
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}
        generator = OutputFormatsGenerator(mock_site, config)
        generator.generate()

        # Load and validate
        index_path = output_dir / "index.json"
        data = json.loads(index_path.read_text())

        page_data = data["pages"][0]
        assert page_data["title"] == "Advanced Tutorial"
        assert page_data["url"].endswith("/tutorial/advanced/")
        assert page_data["description"] == "Learn advanced Python concepts"
        assert page_data["section"] == "docs"
        assert "python" in page_data["tags"]
        assert "advanced" in page_data["tags"]
        assert page_data["author"] == "Jane Doe"
        assert page_data["difficulty"] == "advanced"
        assert "word_count" in page_data
        assert "reading_time" in page_data

    def test_index_json_respects_baseurl(self, tmp_path):
        """Test that baseurl is correctly included in site metadata and page URLs."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir, baseurl="https://example.com")
        page = self._create_mock_page(
            title="Test Page",
            url="/test/",
            content="Content",
            output_path=output_dir / "test/index.html",
        )
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}
        generator = OutputFormatsGenerator(mock_site, config)
        generator.generate()

        # Load and validate
        index_path = output_dir / "index.json"
        data = json.loads(index_path.read_text())

        # Check site baseurl
        assert data["site"]["baseurl"] == "https://example.com"

        # Check page URL includes baseurl
        page_data = data["pages"][0]
        assert page_data["url"] == "https://example.com/test/"
        assert page_data["uri"] == "/test/"  # Relative URI should not have baseurl

    def test_index_json_filters_excluded_pages(self, tmp_path):
        """Test that excluded patterns (404, search) are not in index.json."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)

        # Create normal page and excluded pages
        normal_page = self._create_mock_page(
            title="Normal Page",
            url="/normal/",
            content="Content",
            output_path=output_dir / "normal/index.html",
        )
        page_404 = self._create_mock_page(
            title="404 Not Found",
            url="/404.html",
            content="Not found",
            output_path=output_dir / "404.html",
        )
        search_page = self._create_mock_page(
            title="Search",
            url="/search/",
            content="Search page",
            output_path=output_dir / "search.html",
        )

        mock_site.pages = [normal_page, page_404, search_page]

        config = {
            "enabled": True,
            "per_page": [],
            "site_wide": ["index_json"],
            "options": {"exclude_patterns": ["404.html", "search.html"]},
        }
        generator = OutputFormatsGenerator(mock_site, config)
        generator.generate()

        # Load and validate
        index_path = output_dir / "index.json"
        data = json.loads(index_path.read_text())

        # Should only have 1 page (normal page)
        assert len(data["pages"]) == 1
        assert data["pages"][0]["title"] == "Normal Page"

    # Helper methods

    def _create_mock_site(self, site_dir: Path, output_dir: Path, baseurl: str = "") -> Mock:
        """Create a mock Site instance."""
        from datetime import datetime
        
        site = Mock()
        site.site_dir = site_dir
        site.output_dir = output_dir
        site.dev_mode = False  # Ensure build_time is included in index.json
        site.versioning_enabled = False  # Prevent Mock auto-creation (bool(Mock) is True)
        # Set a real datetime for build_time (required for JSON serialization)
        site.build_time = datetime(2024, 1, 1, 12, 0, 0)
        site.config = {
            "title": "Test Site",
            "baseurl": baseurl,
            "description": "Test site description",
        }
        # Set properties as string attributes (not Mock objects) for JSON serialization
        site.title = "Test Site"
        site.baseurl = baseurl
        site.description = "Test site description"
        site.pages = []
        return site

    def _create_mock_page(
        self,
        title: str,
        url: str,
        content: str,
        output_path: Path | None,
        tags: list[str] | None = None,
        section_name: str | None = None,
        metadata: dict | None = None,
    ) -> Mock:
        """Create a mock Page instance."""
        page = Mock()
        page.title = title
        page.href = url
        page._path = url  # Site-relative path (used by get_page_relative_url)
        page.content = content
        page.parsed_ast = content  # Simplified for testing
        page.plain_text = content  # For AST-based extraction
        page.output_path = output_path
        page.tags = tags or []
        page.date = None
        page.metadata = metadata or {}
        page.source_path = Path("content/test.md")
        page.version = None  # Prevent Mock auto-creation for JSON serialization

        # Mock section
        if section_name:
            section = Mock()
            section.name = section_name
            page._section = section
        else:
            page._section = None

        return page

    def test_index_json_includes_version_field_when_present(self, tmp_path):
        """Test that version field is included in page summaries when page has version."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Versioned Page",
            url="/docs/v1/guide/",
            content="Content",
            output_path=output_dir / "docs/v1/guide/index.html",
        )
        # Set version attribute
        page.version = "v1"
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}
        generator = OutputFormatsGenerator(mock_site, config)
        generator.generate()

        # Load and validate
        index_path = output_dir / "index.json"
        data = json.loads(index_path.read_text())

        page_data = data["pages"][0]
        assert page_data["version"] == "v1", (
            "Version field should be included when page has version"
        )

    def test_index_json_omits_version_field_when_none(self, tmp_path):
        """Test that version field is omitted when page has no version."""
        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        page = self._create_mock_page(
            title="Unversioned Page",
            url="/guide/",
            content="Content",
            output_path=output_dir / "guide/index.html",
        )
        # No version attribute
        page.version = None
        mock_site.pages = [page]

        config = {"enabled": True, "per_page": [], "site_wide": ["index_json"]}
        generator = OutputFormatsGenerator(mock_site, config)
        generator.generate()

        # Load and validate
        index_path = output_dir / "index.json"
        data = json.loads(index_path.read_text())

        page_data = data["pages"][0]
        assert "version" not in page_data, (
            "Version field should be omitted when page has no version"
        )

    def test_index_generator_groups_pages_by_version(self, tmp_path):
        """Test that pages are correctly grouped by version."""
        from bengal.postprocess.output_formats.index_generator import SiteIndexGenerator

        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        # Mock versioning_enabled
        mock_site.versioning_enabled = True

        # Create pages with different versions
        pages = []
        for version_id in ["v1", "v2", None]:
            page = self._create_mock_page(
                title=f"Page {version_id or 'unversioned'}",
                url=f"/docs/{version_id or ''}/page/",
                content="Content",
                output_path=output_dir / f"docs/{version_id or ''}/page/index.html",
            )
            page.version = version_id
            pages.append(page)

        generator = SiteIndexGenerator(mock_site)
        by_version = generator._group_by_version(pages)

        # Assert grouping
        assert len(by_version["v1"]) == 1, "Should have 1 v1 page"
        assert len(by_version["v2"]) == 1, "Should have 1 v2 page"
        assert len(by_version[None]) == 1, "Should have 1 unversioned page"
        assert by_version["v1"][0].version == "v1"
        assert by_version["v2"][0].version == "v2"
        assert by_version[None][0].version is None

    def test_index_generator_generates_per_version_indexes_when_versioning_enabled(self, tmp_path):
        """Test that generate() returns list of paths when versioning is enabled."""
        from bengal.core.version import Version, VersionConfig
        from bengal.postprocess.output_formats.index_generator import SiteIndexGenerator

        output_dir = tmp_path / "public"
        output_dir.mkdir()

        mock_site = self._create_mock_site(tmp_path, output_dir)
        mock_site.versioning_enabled = True

        # Create version config with v3 (latest) and v1
        version_config = VersionConfig(
            enabled=True,
            versions=[
                Version(id="v3", latest=True),
                Version(id="v1", latest=False),
            ],
        )
        mock_site.version_config = version_config

        # Create pages with different versions
        pages = []
        # v3 page (latest)
        page_v3 = self._create_mock_page(
            title="Page v3",
            url="/docs/guide/",
            content="Content v3",
            output_path=output_dir / "docs/guide/index.html",
        )
        page_v3.version = "v3"
        pages.append(page_v3)

        # v1 page
        page_v1 = self._create_mock_page(
            title="Page v1",
            url="/docs/v1/guide/",
            content="Content v1",
            output_path=output_dir / "docs/v1/guide/index.html",
        )
        page_v1.version = "v1"
        pages.append(page_v1)

        generator = SiteIndexGenerator(mock_site)
        result = generator.generate(pages)

        # Should return list of paths
        assert isinstance(result, list), "Should return list when versioning enabled"
        assert len(result) == 2, "Should generate 2 indexes (latest + v1)"

        # Check that indexes exist
        index_paths = [Path(p) for p in result]
        assert any(p.name == "index.json" and p.parent == output_dir for p in index_paths), (
            "Latest version index should be at root"
        )
        assert any(p.name == "index.json" and "docs/v1" in str(p) for p in index_paths), (
            "v1 index should be in docs/v1/"
        )
