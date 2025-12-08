"""
Tests for build orchestration result dataclasses.

Tests dataclass creation, field access, and tuple unpacking backward compatibility.
"""

from pathlib import Path

from bengal.orchestration.build.results import (
    ChangeSummary,
    ConfigCheckResult,
    FilterResult,
)


class TestConfigCheckResult:
    """Tests for ConfigCheckResult dataclass."""

    def test_creates_with_fields(self):
        """Test creating ConfigCheckResult with fields."""
        result = ConfigCheckResult(incremental=True, config_changed=False)

        assert result.incremental is True
        assert result.config_changed is False

    def test_tuple_unpacking_backward_compatibility(self):
        """Test that tuple unpacking still works for backward compatibility."""
        result = ConfigCheckResult(incremental=True, config_changed=False)

        incremental, config_changed = result

        assert incremental is True
        assert config_changed is False

    def test_all_field_combinations(self):
        """Test all combinations of field values."""
        # Both True
        result1 = ConfigCheckResult(incremental=True, config_changed=True)
        assert result1.incremental is True
        assert result1.config_changed is True

        # Both False
        result2 = ConfigCheckResult(incremental=False, config_changed=False)
        assert result2.incremental is False
        assert result2.config_changed is False

        # Mixed
        result3 = ConfigCheckResult(incremental=True, config_changed=False)
        assert result3.incremental is True
        assert result3.config_changed is False

        result4 = ConfigCheckResult(incremental=False, config_changed=True)
        assert result4.incremental is False
        assert result4.config_changed is True


class TestFilterResult:
    """Tests for FilterResult dataclass."""

    def test_creates_with_fields(self):
        """Test creating FilterResult with fields."""
        pages = [object(), object()]
        assets = [object()]
        tags = {"python", "web"}
        paths = {Path("content/post.md")}
        sections = {"blog"}

        result = FilterResult(
            pages_to_build=pages,
            assets_to_process=assets,
            affected_tags=tags,
            changed_page_paths=paths,
            affected_sections=sections,
        )

        assert result.pages_to_build == pages
        assert result.assets_to_process == assets
        assert result.affected_tags == tags
        assert result.changed_page_paths == paths
        assert result.affected_sections == sections

    def test_tuple_unpacking_backward_compatibility(self):
        """Test that tuple unpacking still works for backward compatibility."""
        pages = [object()]
        assets = [object()]
        tags = {"python"}
        paths = {Path("test.md")}
        sections = {"docs"}

        result = FilterResult(
            pages_to_build=pages,
            assets_to_process=assets,
            affected_tags=tags,
            changed_page_paths=paths,
            affected_sections=sections,
        )

        (
            unpacked_pages,
            unpacked_assets,
            unpacked_tags,
            unpacked_paths,
            unpacked_sections,
        ) = result

        assert unpacked_pages == pages
        assert unpacked_assets == assets
        assert unpacked_tags == tags
        assert unpacked_paths == paths
        assert unpacked_sections == sections

    def test_none_affected_sections(self):
        """Test FilterResult with None affected_sections."""
        result = FilterResult(
            pages_to_build=[],
            assets_to_process=[],
            affected_tags=set(),
            changed_page_paths=set(),
            affected_sections=None,
        )

        assert result.affected_sections is None

        # Tuple unpacking should preserve None
        _, _, _, _, sections = result
        assert sections is None


class TestChangeSummary:
    """Tests for ChangeSummary dataclass."""

    def test_creates_with_defaults(self):
        """Test creating ChangeSummary with default empty lists."""
        summary = ChangeSummary()

        assert summary.modified_content == []
        assert summary.modified_assets == []
        assert summary.modified_templates == []
        assert summary.taxonomy_changes == []
        assert summary.extra_changes == {}

    def test_creates_with_fields(self):
        """Test creating ChangeSummary with populated fields."""
        content = [Path("content/post.md")]
        assets = [Path("assets/image.png")]
        templates = [Path("templates/base.html")]
        taxonomy = ["python", "web"]

        summary = ChangeSummary(
            modified_content=content,
            modified_assets=assets,
            modified_templates=templates,
            taxonomy_changes=taxonomy,
        )

        assert summary.modified_content == content
        assert summary.modified_assets == assets
        assert summary.modified_templates == templates
        assert summary.taxonomy_changes == taxonomy

    def test_to_dict_conversion(self):
        """Test converting ChangeSummary to dict format."""
        summary = ChangeSummary(
            modified_content=[Path("content/post.md")],
            modified_assets=[Path("assets/image.png")],
            modified_templates=[Path("templates/base.html")],
            taxonomy_changes=["python"],
        )

        result = summary.to_dict()

        assert result["Modified content"] == [Path("content/post.md")]
        assert result["Modified assets"] == [Path("assets/image.png")]
        assert result["Modified templates"] == [Path("templates/base.html")]
        assert result["Taxonomy changes"] == ["python"]

    def test_to_dict_omits_empty_fields(self):
        """Test that to_dict omits empty fields."""
        summary = ChangeSummary()
        summary.modified_content = [Path("content/post.md")]

        result = summary.to_dict()

        assert "Modified content" in result
        assert "Modified assets" not in result
        assert "Modified templates" not in result
        assert "Taxonomy changes" not in result

    def test_to_dict_includes_extra_changes(self):
        """Test that to_dict includes extra_changes."""
        summary = ChangeSummary()
        summary.extra_changes["Cascade changes"] = ["message1", "message2"]
        summary.extra_changes["Navigation changes"] = ["message3"]

        result = summary.to_dict()

        assert result["Cascade changes"] == ["message1", "message2"]
        assert result["Navigation changes"] == ["message3"]

    def test_items_method(self):
        """Test items() method for dict-like iteration."""
        summary = ChangeSummary()
        summary.modified_content = [Path("content/post.md")]
        summary.extra_changes["Cascade changes"] = ["message1"]

        items = list(summary.items())

        assert len(items) == 2
        assert ("Modified content", [Path("content/post.md")]) in items
        assert ("Cascade changes", ["message1"]) in items

    def test_get_method(self):
        """Test get() method for dict-like access."""
        summary = ChangeSummary()
        summary.modified_content = [Path("content/post.md")]

        assert summary.get("Modified content") == [Path("content/post.md")]
        assert summary.get("Nonexistent") is None
        assert summary.get("Nonexistent", []) == []

