"""
Unit tests for BlockDiffService and DiffResult.
"""

from dataclasses import dataclass
from pathlib import Path

import pytest

from bengal.effects.block_diff import BlockDiffService, DiffResult


# Mock snapshot types for testing
@dataclass
class MockPageSnapshot:
    """Mock PageSnapshot for testing."""

    source_path: Path
    content_hash: str
    content: str
    metadata: dict
    template_name: str = "page.html"


@dataclass
class MockTemplateSnapshot:
    """Mock TemplateSnapshot for testing."""

    all_dependencies: frozenset[str]


@dataclass
class MockSiteSnapshot:
    """Mock SiteSnapshot for testing."""

    pages: list[MockPageSnapshot]
    templates: dict[str, MockTemplateSnapshot]


class TestDiffResult:
    """Tests for DiffResult dataclass."""

    def test_create_with_defaults(self) -> None:
        """DiffResult can be created with minimal args."""
        result = DiffResult(requires_rebuild=True, reason="Test reason")
        assert result.requires_rebuild is True
        assert result.reason == "Test reason"
        assert result.affected_blocks == frozenset()
        assert result.is_content_only is False
        assert result.is_metadata_only is False

    def test_create_with_all_fields(self) -> None:
        """DiffResult can be created with all fields."""
        result = DiffResult(
            requires_rebuild=False,
            reason="No changes",
            affected_blocks=frozenset({"nav", "footer"}),
            is_content_only=True,
            is_metadata_only=False,
        )
        assert result.requires_rebuild is False
        assert result.affected_blocks == frozenset({"nav", "footer"})
        assert result.is_content_only is True

    def test_is_frozen(self) -> None:
        """DiffResult is immutable."""
        result = DiffResult(requires_rebuild=True, reason="Test")
        with pytest.raises(AttributeError):
            result.requires_rebuild = False  # type: ignore[misc]


class TestBlockDiffService:
    """Tests for BlockDiffService class."""

    def test_fresh_build_all_pages_need_rebuild(self) -> None:
        """With no old snapshot, all pages need rebuild."""
        new_snapshot = MockSiteSnapshot(
            pages=[
                MockPageSnapshot(
                    source_path=Path("content/page.md"),
                    content_hash="abc123",
                    content="# Hello",
                    metadata={"title": "Hello"},
                )
            ],
            templates={},
        )

        service = BlockDiffService(None, new_snapshot)  # type: ignore[arg-type]
        result = service.diff_page(Path("content/page.md"))

        assert result.requires_rebuild is True
        assert result.reason == "New page"

    def test_unchanged_page_no_rebuild(self) -> None:
        """Unchanged page doesn't need rebuild."""
        page = MockPageSnapshot(
            source_path=Path("content/page.md"),
            content_hash="abc123",
            content="# Hello",
            metadata={"title": "Hello"},
        )
        old_snapshot = MockSiteSnapshot(pages=[page], templates={})
        new_snapshot = MockSiteSnapshot(pages=[page], templates={})

        service = BlockDiffService(old_snapshot, new_snapshot)  # type: ignore[arg-type]
        result = service.diff_page(Path("content/page.md"))

        assert result.requires_rebuild is False
        assert "hash match" in result.reason.lower()

    def test_content_changed_needs_rebuild(self) -> None:
        """Content change triggers rebuild."""
        old_page = MockPageSnapshot(
            source_path=Path("content/page.md"),
            content_hash="abc123",
            content="# Hello",
            metadata={"title": "Hello"},
        )
        new_page = MockPageSnapshot(
            source_path=Path("content/page.md"),
            content_hash="def456",
            content="# World",
            metadata={"title": "Hello"},
        )
        old_snapshot = MockSiteSnapshot(pages=[old_page], templates={})
        new_snapshot = MockSiteSnapshot(pages=[new_page], templates={})

        service = BlockDiffService(old_snapshot, new_snapshot)  # type: ignore[arg-type]
        result = service.diff_page(Path("content/page.md"))

        assert result.requires_rebuild is True
        assert result.is_content_only is True

    def test_metadata_only_change(self) -> None:
        """Metadata-only change triggers appropriate rebuild."""
        old_page = MockPageSnapshot(
            source_path=Path("content/page.md"),
            content_hash="abc123",
            content="# Hello",
            metadata={"title": "Old Title"},
        )
        new_page = MockPageSnapshot(
            source_path=Path("content/page.md"),
            content_hash="abc123",  # Same hash
            content="# Hello",
            metadata={"title": "New Title"},
        )
        old_snapshot = MockSiteSnapshot(pages=[old_page], templates={})
        new_snapshot = MockSiteSnapshot(pages=[new_page], templates={})

        service = BlockDiffService(old_snapshot, new_snapshot)  # type: ignore[arg-type]
        result = service.diff_page(Path("content/page.md"))

        assert result.requires_rebuild is True
        assert result.is_metadata_only is True

    def test_internal_metadata_change_no_rebuild(self) -> None:
        """Internal metadata fields (_parsed_at, etc.) don't trigger rebuild."""
        old_page = MockPageSnapshot(
            source_path=Path("content/page.md"),
            content_hash="abc123",
            content="# Hello",
            metadata={"title": "Hello", "_parsed_at": "2024-01-01"},
        )
        new_page = MockPageSnapshot(
            source_path=Path("content/page.md"),
            content_hash="abc123",
            content="# Hello",
            metadata={"title": "Hello", "_parsed_at": "2024-01-02"},
        )
        old_snapshot = MockSiteSnapshot(pages=[old_page], templates={})
        new_snapshot = MockSiteSnapshot(pages=[new_page], templates={})

        service = BlockDiffService(old_snapshot, new_snapshot)  # type: ignore[arg-type]
        result = service.diff_page(Path("content/page.md"))

        assert result.requires_rebuild is False
        assert result.is_metadata_only is True

    def test_page_no_longer_exists(self) -> None:
        """Removed page doesn't need rebuild."""
        old_page = MockPageSnapshot(
            source_path=Path("content/old.md"),
            content_hash="abc123",
            content="# Old",
            metadata={},
        )
        old_snapshot = MockSiteSnapshot(pages=[old_page], templates={})
        new_snapshot = MockSiteSnapshot(pages=[], templates={})

        service = BlockDiffService(old_snapshot, new_snapshot)  # type: ignore[arg-type]
        result = service.diff_page(Path("content/old.md"))

        assert result.requires_rebuild is False
        assert "no longer exists" in result.reason.lower()

    def test_frontmatter_only_change(self) -> None:
        """Frontmatter-only change is detected."""
        old_page = MockPageSnapshot(
            source_path=Path("content/page.md"),
            content_hash="abc123",
            content="---\ntitle: Old\n---\n# Hello",
            metadata={"title": "Old"},
        )
        new_page = MockPageSnapshot(
            source_path=Path("content/page.md"),
            content_hash="def456",  # Different hash
            content="---\ntitle: New\n---\n# Hello",  # Same body, different frontmatter
            metadata={"title": "New"},
        )
        old_snapshot = MockSiteSnapshot(pages=[old_page], templates={})
        new_snapshot = MockSiteSnapshot(pages=[new_page], templates={})

        service = BlockDiffService(old_snapshot, new_snapshot)  # type: ignore[arg-type]
        result = service.diff_page(Path("content/page.md"))

        assert result.requires_rebuild is True
        assert result.is_metadata_only is True
        assert "frontmatter" in result.reason.lower()


class TestBlockDiffServiceTemplates:
    """Tests for template diffing."""

    def test_template_change_unknown_blocks_rebuilds(self) -> None:
        """Template change with unknown blocks requires rebuild."""
        new_snapshot = MockSiteSnapshot(pages=[], templates={})
        service = BlockDiffService(None, new_snapshot)  # type: ignore[arg-type]

        result = service.diff_template("page.html", changed_blocks=None)

        assert result.requires_rebuild is True
        assert "unknown" in result.reason.lower()

    def test_site_scoped_blocks_no_rebuild(self) -> None:
        """Site-scoped block changes don't require page rebuilds."""
        new_snapshot = MockSiteSnapshot(pages=[], templates={})
        service = BlockDiffService(None, new_snapshot)  # type: ignore[arg-type]

        result = service.diff_template(
            "page.html",
            changed_blocks=frozenset({"nav", "footer", "header"}),
        )

        assert result.requires_rebuild is False
        assert "site-scoped" in result.reason.lower()
        assert result.affected_blocks == frozenset({"nav", "footer", "header"})

    def test_page_scoped_blocks_require_rebuild(self) -> None:
        """Page-scoped block changes require rebuild."""
        new_snapshot = MockSiteSnapshot(pages=[], templates={})
        service = BlockDiffService(None, new_snapshot)  # type: ignore[arg-type]

        result = service.diff_template(
            "page.html",
            changed_blocks=frozenset({"content", "sidebar"}),
        )

        assert result.requires_rebuild is True
        assert "content" in result.reason or "page-scoped" in result.reason.lower()

    def test_mixed_blocks_require_rebuild(self) -> None:
        """Mixed site/page scoped blocks require rebuild."""
        new_snapshot = MockSiteSnapshot(pages=[], templates={})
        service = BlockDiffService(None, new_snapshot)  # type: ignore[arg-type]

        result = service.diff_template(
            "page.html",
            changed_blocks=frozenset({"nav", "content"}),  # nav=site, content=page
        )

        assert result.requires_rebuild is True


class TestBlockDiffServiceAffectedPages:
    """Tests for get_affected_pages method."""

    def test_direct_page_change(self) -> None:
        """Direct page change is detected."""
        old_page = MockPageSnapshot(
            source_path=Path("content/page.md"),
            content_hash="abc123",
            content="# Old",
            metadata={},
        )
        new_page = MockPageSnapshot(
            source_path=Path("content/page.md"),
            content_hash="def456",
            content="# New",
            metadata={},
        )
        old_snapshot = MockSiteSnapshot(pages=[old_page], templates={})
        new_snapshot = MockSiteSnapshot(pages=[new_page], templates={})

        service = BlockDiffService(old_snapshot, new_snapshot)  # type: ignore[arg-type]
        affected = service.get_affected_pages({Path("content/page.md")})

        assert Path("content/page.md") in affected

    def test_unrelated_file_no_affected_pages(self) -> None:
        """Unrelated file changes don't affect pages."""
        page = MockPageSnapshot(
            source_path=Path("content/page.md"),
            content_hash="abc123",
            content="# Hello",
            metadata={},
        )
        snapshot = MockSiteSnapshot(pages=[page], templates={})

        service = BlockDiffService(snapshot, snapshot)  # type: ignore[arg-type]
        affected = service.get_affected_pages({Path("content/other.md")})

        assert len(affected) == 0
