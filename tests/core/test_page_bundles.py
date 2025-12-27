"""Tests for page bundle detection and resources.

RFC: hugo-inspired-features

Tests Hugo-style page bundles:
- Leaf bundles (index.md with co-located resources)
- Branch bundles (_index.md section indexes)
- Regular pages (standalone .md files)
- PageResources collection and access methods
"""

from pathlib import Path

import pytest

from bengal.core.page import BundleType, Page, PageResource, PageResources


class TestBundleTypeDetection:
    """Test bundle type detection based on filename."""

    def test_leaf_bundle_index_md(self):
        """index.md is detected as LEAF bundle."""
        page = Page(source_path=Path("content/posts/my-post/index.md"))
        assert page.bundle_type == BundleType.LEAF
        assert page.is_bundle is True
        assert page.is_branch_bundle is False

    def test_branch_bundle_underscore_index(self):
        """_index.md is detected as BRANCH bundle."""
        page = Page(source_path=Path("content/posts/_index.md"))
        assert page.bundle_type == BundleType.BRANCH
        assert page.is_bundle is False
        assert page.is_branch_bundle is True

    def test_regular_page(self):
        """Regular .md file is detected as NONE."""
        page = Page(source_path=Path("content/posts/my-post.md"))
        assert page.bundle_type == BundleType.NONE
        assert page.is_bundle is False
        assert page.is_branch_bundle is False

    def test_case_insensitive_index(self):
        """Bundle detection is case-insensitive."""
        page = Page(source_path=Path("content/posts/my-post/INDEX.MD"))
        assert page.bundle_type == BundleType.LEAF

    def test_deeply_nested_bundle(self):
        """Bundle detection works for deeply nested paths."""
        page = Page(source_path=Path("content/docs/guides/advanced/chapter-1/index.md"))
        assert page.bundle_type == BundleType.LEAF
        assert page.is_bundle is True


class TestPageResources:
    """Test PageResources collection functionality."""

    @pytest.fixture
    def bundle_with_resources(self, tmp_path):
        """Create a bundle directory with various resources."""
        bundle_dir = tmp_path / "posts" / "my-post"
        bundle_dir.mkdir(parents=True)

        # Create index.md
        (bundle_dir / "index.md").write_text("# My Post")

        # Create various resources
        (bundle_dir / "hero.jpg").write_bytes(b"fake jpeg")
        (bundle_dir / "hero.png").write_bytes(b"fake png")
        (bundle_dir / "diagram.svg").write_text("<svg></svg>")
        (bundle_dir / "data.json").write_text('{"key": "value"}')
        (bundle_dir / "config.yaml").write_text("key: value")
        (bundle_dir / "doc.pdf").write_bytes(b"fake pdf")

        # Content file (should be excluded)
        (bundle_dir / "notes.txt").write_text("Some notes")

        return bundle_dir / "index.md"

    def test_non_bundle_returns_empty_resources(self):
        """Non-bundle page has empty resources."""
        page = Page(source_path=Path("content/posts/my-post.md"))
        assert len(page.resources) == 0
        assert bool(page.resources) is False

    def test_bundle_discovers_resources(self, bundle_with_resources):
        """Leaf bundle discovers co-located resources."""
        page = Page(source_path=bundle_with_resources)
        resources = page.resources

        # Should find all non-content files
        assert len(resources) >= 5
        assert "hero.jpg" in resources
        assert "data.json" in resources

    def test_get_exact_match(self, bundle_with_resources):
        """get() returns resource by exact name."""
        page = Page(source_path=bundle_with_resources)

        resource = page.resources.get("data.json")
        assert resource is not None
        assert resource.name == "data.json"

        missing = page.resources.get("nonexistent.txt")
        assert missing is None

    def test_get_match_glob(self, bundle_with_resources):
        """get_match() returns first matching resource."""
        page = Page(source_path=bundle_with_resources)

        hero = page.resources.get_match("hero.*")
        assert hero is not None
        assert hero.name.startswith("hero.")

        svg = page.resources.get_match("*.svg")
        assert svg is not None
        assert svg.suffix == ".svg"

    def test_match_returns_all(self, bundle_with_resources):
        """match() returns all matching resources."""
        page = Page(source_path=bundle_with_resources)

        heroes = page.resources.match("hero.*")
        assert len(heroes) == 2  # hero.jpg, hero.png

        all_files = page.resources.match("*")
        assert len(all_files) >= 5

    def test_by_type_image(self, bundle_with_resources):
        """by_type('image') returns image resources."""
        page = Page(source_path=bundle_with_resources)

        images = page.resources.by_type("image")
        assert len(images) == 3  # hero.jpg, hero.png, diagram.svg

    def test_by_type_data(self, bundle_with_resources):
        """by_type('data') returns data resources."""
        page = Page(source_path=bundle_with_resources)

        data = page.resources.by_type("data")
        assert len(data) == 2  # data.json, config.yaml

    def test_by_type_document(self, bundle_with_resources):
        """by_type('document') returns document resources."""
        page = Page(source_path=bundle_with_resources)

        docs = page.resources.by_type("document")
        assert len(docs) == 1  # doc.pdf


class TestPageResource:
    """Test individual PageResource functionality."""

    def test_resource_properties(self, tmp_path):
        """PageResource exposes correct properties."""
        resource_file = tmp_path / "image.jpg"
        resource_file.write_bytes(b"fake image data")

        resource = PageResource(path=resource_file, page_url="/posts/my-post/")

        assert resource.name == "image.jpg"
        assert resource.stem == "image"
        assert resource.suffix == ".jpg"
        assert resource.exists is True
        assert resource.size > 0
        assert resource.resource_type == "image"

    def test_rel_permalink(self, tmp_path):
        """rel_permalink is correctly constructed."""
        resource_file = tmp_path / "hero.jpg"
        resource_file.write_bytes(b"fake")

        resource = PageResource(path=resource_file, page_url="/posts/my-post/")
        assert resource.rel_permalink == "/posts/my-post/hero.jpg"

        # Without trailing slash
        resource2 = PageResource(path=resource_file, page_url="/posts/my-post")
        assert resource2.rel_permalink == "/posts/my-post/hero.jpg"

    def test_read_json(self, tmp_path):
        """read_json() parses JSON file."""
        json_file = tmp_path / "data.json"
        json_file.write_text('{"name": "test", "count": 42}')

        resource = PageResource(path=json_file, page_url="/")
        data = resource.read_json()

        assert data["name"] == "test"
        assert data["count"] == 42

    def test_read_text(self, tmp_path):
        """read_text() returns file contents."""
        text_file = tmp_path / "notes.txt"
        text_file.write_text("Hello World")

        resource = PageResource(path=text_file, page_url="/")
        assert resource.read_text() == "Hello World"

    def test_resource_type_categories(self, tmp_path):
        """resource_type correctly categorizes files."""
        test_cases = [
            ("image.jpg", "image"),
            ("photo.png", "image"),
            ("icon.svg", "image"),
            ("video.mp4", "video"),
            ("audio.mp3", "audio"),
            ("doc.pdf", "document"),
            ("data.json", "data"),
            ("config.yaml", "data"),
            ("script.js", "code"),
            ("archive.zip", "archive"),
            ("unknown.xyz", None),
        ]

        for filename, expected_type in test_cases:
            resource_file = tmp_path / filename
            resource_file.write_bytes(b"data")
            resource = PageResource(path=resource_file, page_url="/")
            assert resource.resource_type == expected_type, f"{filename} should be {expected_type}"


class TestPageResourcesCollection:
    """Test PageResources collection behavior."""

    def test_iteration(self):
        """PageResources supports iteration."""
        from bengal.core.page.bundle import PageResource

        resources = PageResources(
            [
                PageResource(path=Path("/a.jpg"), page_url="/"),
                PageResource(path=Path("/b.png"), page_url="/"),
            ]
        )

        names = [r.name for r in resources]
        assert names == ["a.jpg", "b.png"]

    def test_contains(self):
        """PageResources supports 'in' operator."""
        from bengal.core.page.bundle import PageResource

        resources = PageResources([PageResource(path=Path("/test.jpg"), page_url="/")])

        assert "test.jpg" in resources
        assert "other.png" not in resources

    def test_bool(self):
        """PageResources is falsy when empty, truthy otherwise."""
        empty = PageResources([])
        assert bool(empty) is False

        from bengal.core.page.bundle import PageResource

        non_empty = PageResources([PageResource(path=Path("/x.jpg"), page_url="/")])
        assert bool(non_empty) is True

    def test_convenience_methods(self):
        """images() and data() are convenience aliases."""
        from bengal.core.page.bundle import PageResource

        resources = PageResources(
            [
                PageResource(path=Path("/photo.jpg"), page_url="/"),
                PageResource(path=Path("/config.json"), page_url="/"),
            ]
        )

        images = resources.images()
        assert len(images) == 1
        assert images[0].name == "photo.jpg"

        data = resources.data()
        assert len(data) == 1
        assert data[0].name == "config.json"
