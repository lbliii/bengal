"""
Unit tests for bengal.snapshots.utils module.

Tests the shared utilities extracted from builder.py, persistence.py, and scheduler.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bengal.snapshots.utils import (
    RenderProgressTracker,
    build_pages_by_template,
    build_path_index,
    compute_content_hash,
    compute_page_hash,
    resolve_template_name,
    update_frozen,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@dataclass(frozen=True, slots=True)
class FrozenExample:
    """Example frozen dataclass for testing update_frozen."""

    name: str
    value: int
    tags: tuple[str, ...] = ()


class MockPage:
    """Mock page for testing."""

    def __init__(
        self,
        source_path: Path,
        content: str = "",
        metadata: dict[str, Any] | None = None,
        output_path: Path | None = None,
    ):
        self.source_path = source_path
        self.content = content
        self.metadata = metadata or {}
        self.output_path = output_path


class MockProgressManager:
    """Mock progress manager for testing."""

    def __init__(self) -> None:
        self.updates: list[dict[str, Any]] = []

    def update_phase(
        self,
        phase: str,
        *,
        current: int | None = None,
        current_item: str | None = None,
    ) -> None:
        self.updates.append(
            {"phase": phase, "current": current, "current_item": current_item}
        )


class MockSite:
    """Mock site for testing."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir


# =============================================================================
# Tests: compute_content_hash
# =============================================================================


class TestComputeContentHash:
    """Tests for compute_content_hash function."""

    def test_returns_hex_string(self) -> None:
        """Hash is a hex string."""
        result = compute_content_hash("hello")
        assert isinstance(result, str)
        assert all(c in "0123456789abcdef" for c in result)

    def test_returns_full_sha256(self) -> None:
        """Returns full 64-character SHA-256 hash."""
        result = compute_content_hash("hello")
        assert len(result) == 64

    def test_same_content_same_hash(self) -> None:
        """Same content produces same hash."""
        assert compute_content_hash("hello") == compute_content_hash("hello")

    def test_different_content_different_hash(self) -> None:
        """Different content produces different hash."""
        assert compute_content_hash("hello") != compute_content_hash("world")

    def test_empty_string(self) -> None:
        """Empty string produces valid hash."""
        result = compute_content_hash("")
        assert len(result) == 64

    def test_unicode_content(self) -> None:
        """Unicode content is handled correctly."""
        result = compute_content_hash("héllo wörld 日本語")
        assert len(result) == 64


# =============================================================================
# Tests: compute_page_hash
# =============================================================================


class TestComputePageHash:
    """Tests for compute_page_hash function."""

    def test_hashes_page_content(self) -> None:
        """Extracts content from page and hashes it."""
        page = MockPage(Path("test.md"), content="# Hello World")
        result = compute_page_hash(page)
        assert result == compute_content_hash("# Hello World")

    def test_handles_empty_content(self) -> None:
        """Handles page with empty content."""
        page = MockPage(Path("test.md"), content="")
        result = compute_page_hash(page)
        assert result == compute_content_hash("")

    def test_handles_missing_content(self) -> None:
        """Handles page without content attribute."""
        page = MockPage(Path("test.md"))
        delattr(page, "content")
        result = compute_page_hash(page)
        assert result == compute_content_hash("")


# =============================================================================
# Tests: update_frozen
# =============================================================================


class TestUpdateFrozen:
    """Tests for update_frozen function."""

    def test_updates_single_field(self) -> None:
        """Updates a single field."""
        original = FrozenExample(name="test", value=1)
        updated = update_frozen(original, value=2)

        assert updated.name == "test"
        assert updated.value == 2
        assert original.value == 1  # Original unchanged

    def test_updates_multiple_fields(self) -> None:
        """Updates multiple fields at once."""
        original = FrozenExample(name="test", value=1)
        updated = update_frozen(original, name="new", value=99)

        assert updated.name == "new"
        assert updated.value == 99

    def test_preserves_unchanged_fields(self) -> None:
        """Fields not specified stay unchanged."""
        original = FrozenExample(name="test", value=1, tags=("a", "b"))
        updated = update_frozen(original, value=2)

        assert updated.name == "test"
        assert updated.tags == ("a", "b")

    def test_returns_new_instance(self) -> None:
        """Returns a new instance, not the same object."""
        original = FrozenExample(name="test", value=1)
        updated = update_frozen(original, value=1)  # Same values

        assert updated is not original
        assert updated == original  # But equal

    def test_works_with_tuple_fields(self) -> None:
        """Can update tuple fields."""
        original = FrozenExample(name="test", value=1, tags=())
        updated = update_frozen(original, tags=("new", "tags"))

        assert updated.tags == ("new", "tags")


# =============================================================================
# Tests: resolve_template_name
# =============================================================================


class TestResolveTemplateName:
    """Tests for resolve_template_name function."""

    def test_returns_template_from_metadata(self) -> None:
        """Uses template from metadata if present."""
        page = MockPage(Path("test.md"), metadata={"template": "custom.html"})
        assert resolve_template_name(page) == "custom.html"

    def test_returns_layout_from_metadata(self) -> None:
        """Uses layout from metadata if template not present."""
        page = MockPage(Path("test.md"), metadata={"layout": "post.html"})
        assert resolve_template_name(page) == "post.html"

    def test_template_takes_precedence_over_layout(self) -> None:
        """Template takes precedence over layout."""
        page = MockPage(
            Path("test.md"),
            metadata={"template": "custom.html", "layout": "post.html"},
        )
        assert resolve_template_name(page) == "custom.html"

    def test_returns_type_from_metadata(self) -> None:
        """Uses type from metadata if template/layout not present."""
        page = MockPage(Path("test.md"), metadata={"type": "blog"})
        assert resolve_template_name(page) == "blog"

    def test_returns_default_when_no_metadata(self) -> None:
        """Returns default when no template metadata."""
        page = MockPage(Path("test.md"))
        assert resolve_template_name(page) == "page.html"

    def test_custom_default(self) -> None:
        """Uses custom default if provided."""
        page = MockPage(Path("test.md"))
        assert resolve_template_name(page, default="single.html") == "single.html"


# =============================================================================
# Tests: RenderProgressTracker
# =============================================================================


class TestRenderProgressTracker:
    """Tests for RenderProgressTracker class."""

    def test_increment_updates_count(self) -> None:
        """Increment increases internal count."""
        manager = MockProgressManager()
        site = MockSite(Path("/output"))
        tracker = RenderProgressTracker(manager, site)

        page = MockPage(Path("test.md"), output_path=Path("/output/test.html"))
        tracker.increment(page)

        assert tracker.count == 1

    def test_increment_returns_current_count(self) -> None:
        """Increment returns the current count."""
        manager = MockProgressManager()
        site = MockSite(Path("/output"))
        tracker = RenderProgressTracker(manager, site)

        page = MockPage(Path("test.md"), output_path=Path("/output/test.html"))
        result = tracker.increment(page)

        assert result == 1

    def test_finalize_sends_final_update(self) -> None:
        """Finalize sends 100% update."""
        manager = MockProgressManager()
        site = MockSite(Path("/output"))
        tracker = RenderProgressTracker(manager, site)

        tracker.finalize(100)

        assert len(manager.updates) == 1
        assert manager.updates[0]["phase"] == "rendering"
        assert manager.updates[0]["current"] == 100
        assert manager.updates[0]["current_item"] == ""

    def test_works_without_manager(self) -> None:
        """Works when manager is None."""
        site = MockSite(Path("/output"))
        tracker = RenderProgressTracker(None, site)

        page = MockPage(Path("test.md"), output_path=Path("/output/test.html"))
        result = tracker.increment(page)

        assert result == 1
        tracker.finalize(1)  # Should not raise

    def test_batch_update_triggers_at_batch_size(self) -> None:
        """Updates trigger at batch_size intervals."""
        manager = MockProgressManager()
        site = MockSite(Path("/output"))
        tracker = RenderProgressTracker(manager, site, batch_size=5)

        page = MockPage(Path("test.md"), output_path=Path("/output/test.html"))

        # First 4 increments should not trigger update (batched)
        for _ in range(4):
            tracker.increment(page)

        # But after 5th, should have an update
        tracker.increment(page)

        assert len(manager.updates) >= 1


# =============================================================================
# Tests: build_path_index
# =============================================================================


class TestBuildPathIndex:
    """Tests for build_path_index function."""

    def test_builds_index_by_source_path(self) -> None:
        """Creates mapping from source_path to page."""
        pages = [
            MockPage(Path("a.md")),
            MockPage(Path("b.md")),
            MockPage(Path("c.md")),
        ]

        index = build_path_index(pages)

        assert len(index) == 3
        assert index[Path("a.md")] is pages[0]
        assert index[Path("b.md")] is pages[1]
        assert index[Path("c.md")] is pages[2]

    def test_empty_list(self) -> None:
        """Returns empty dict for empty list."""
        index = build_path_index([])
        assert index == {}

    def test_custom_path_attr(self) -> None:
        """Can use custom path attribute."""
        pages = [
            MockPage(Path("a.md"), output_path=Path("out/a.html")),
            MockPage(Path("b.md"), output_path=Path("out/b.html")),
        ]

        index = build_path_index(pages, path_attr="output_path")

        assert Path("out/a.html") in index
        assert Path("out/b.html") in index


# =============================================================================
# Tests: build_pages_by_template
# =============================================================================


class TestBuildPagesByTemplate:
    """Tests for build_pages_by_template function."""

    def test_groups_by_template(self) -> None:
        """Groups pages by their template name."""
        pages = [
            MockPage(Path("a.md"), metadata={"template": "post.html"}),
            MockPage(Path("b.md"), metadata={"template": "post.html"}),
            MockPage(Path("c.md"), metadata={"template": "page.html"}),
        ]

        groups = build_pages_by_template(pages)

        assert "post.html" in groups
        assert "page.html" in groups
        assert len(groups["post.html"]) == 2
        assert len(groups["page.html"]) == 1

    def test_default_template(self) -> None:
        """Pages without template get default."""
        pages = [
            MockPage(Path("a.md")),
            MockPage(Path("b.md")),
        ]

        groups = build_pages_by_template(pages)

        assert "page.html" in groups
        assert len(groups["page.html"]) == 2

    def test_empty_list(self) -> None:
        """Returns empty dict for empty list."""
        groups = build_pages_by_template([])
        assert groups == {}

    def test_custom_resolver(self) -> None:
        """Can use custom template resolver."""
        pages = [
            MockPage(Path("a.md"), metadata={"custom_type": "blog"}),
            MockPage(Path("b.md"), metadata={"custom_type": "docs"}),
        ]

        def custom_resolver(page: MockPage) -> str:
            return page.metadata.get("custom_type", "default")

        groups = build_pages_by_template(pages, template_resolver=custom_resolver)

        assert "blog" in groups
        assert "docs" in groups
