"""
Tests for build orchestration result dataclasses.

Tests dataclass creation, field access, and tuple unpacking backward compatibility.
"""

from pathlib import Path
from unittest.mock import MagicMock

from bengal.orchestration.build.results import (
    ChangeSummary,
    ConfigCheckResult,
    FilterResult,
    IncrementalDecision,
    RebuildReason,
    RebuildReasonCode,
    SkipReasonCode,
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


class TestRebuildReasonCode:
    """Tests for RebuildReasonCode enum."""

    def test_all_reason_codes_have_values(self):
        """Test that all reason codes have string values."""
        assert RebuildReasonCode.CONTENT_CHANGED.value == "content_changed"
        assert RebuildReasonCode.TEMPLATE_CHANGED.value == "template_changed"
        assert RebuildReasonCode.ASSET_FINGERPRINT_CHANGED.value == "asset_fingerprint_changed"
        assert RebuildReasonCode.CASCADE_DEPENDENCY.value == "cascade_dependency"
        assert RebuildReasonCode.NAV_CHANGED.value == "nav_changed"
        assert RebuildReasonCode.CROSS_VERSION_DEPENDENCY.value == "cross_version_dependency"
        assert RebuildReasonCode.ADJACENT_NAV_CHANGED.value == "adjacent_nav_changed"
        assert RebuildReasonCode.FORCED.value == "forced"
        assert RebuildReasonCode.FULL_REBUILD.value == "full_rebuild"
        assert RebuildReasonCode.OUTPUT_MISSING.value == "output_missing"

    def test_reason_codes_are_unique(self):
        """Test that all reason code values are unique."""
        values = [code.value for code in RebuildReasonCode]
        assert len(values) == len(set(values))


class TestSkipReasonCode:
    """Tests for SkipReasonCode enum."""

    def test_all_skip_codes_have_values(self):
        """Test that all skip codes have string values."""
        assert SkipReasonCode.CACHE_HIT.value == "cache_hit"
        assert SkipReasonCode.NO_CHANGES.value == "no_changes"
        assert SkipReasonCode.SECTION_FILTERED.value == "section_filtered"


class TestRebuildReason:
    """Tests for RebuildReason dataclass."""

    def test_creates_with_code_only(self):
        """Test creating RebuildReason with code only."""
        reason = RebuildReason(code=RebuildReasonCode.CONTENT_CHANGED)

        assert reason.code == RebuildReasonCode.CONTENT_CHANGED
        assert reason.details == {}

    def test_creates_with_code_and_details(self):
        """Test creating RebuildReason with code and details."""
        reason = RebuildReason(
            code=RebuildReasonCode.ASSET_FINGERPRINT_CHANGED,
            details={"assets": ["style.css", "main.js"]},
        )

        assert reason.code == RebuildReasonCode.ASSET_FINGERPRINT_CHANGED
        assert reason.details == {"assets": ["style.css", "main.js"]}

    def test_str_without_details(self):
        """Test __str__ without details returns code value."""
        reason = RebuildReason(code=RebuildReasonCode.CONTENT_CHANGED)

        assert str(reason) == "content_changed"

    def test_str_with_details(self):
        """Test __str__ with details includes them in output."""
        reason = RebuildReason(
            code=RebuildReasonCode.ASSET_FINGERPRINT_CHANGED,
            details={"assets": ["style.css"]},
        )

        result = str(reason)
        assert "asset_fingerprint_changed" in result
        assert "assets=['style.css']" in result

    def test_str_with_multiple_details(self):
        """Test __str__ with multiple details."""
        reason = RebuildReason(
            code=RebuildReasonCode.OUTPUT_MISSING,
            details={"html_missing": True, "autodoc_missing": False},
        )

        result = str(reason)
        assert "output_missing" in result
        assert "html_missing=True" in result
        assert "autodoc_missing=False" in result


class TestIncrementalDecision:
    """Tests for IncrementalDecision dataclass."""

    def test_creates_with_minimal_fields(self):
        """Test creating IncrementalDecision with minimal fields."""
        decision = IncrementalDecision(
            pages_to_build=[],
            pages_skipped_count=0,
        )

        assert decision.pages_to_build == []
        assert decision.pages_skipped_count == 0
        assert decision.rebuild_reasons == {}
        assert decision.skip_reasons == {}
        assert decision.asset_changes == []
        assert decision.fingerprint_changes is False

    def test_creates_with_all_fields(self):
        """Test creating IncrementalDecision with all fields."""
        mock_page = MagicMock()
        decision = IncrementalDecision(
            pages_to_build=[mock_page],
            pages_skipped_count=10,
            rebuild_reasons={"content/index.md": RebuildReason(code=RebuildReasonCode.CONTENT_CHANGED)},
            skip_reasons={"content/about.md": SkipReasonCode.NO_CHANGES},
            asset_changes=["style.css"],
            fingerprint_changes=True,
        )

        assert len(decision.pages_to_build) == 1
        assert decision.pages_skipped_count == 10
        assert len(decision.rebuild_reasons) == 1
        assert len(decision.skip_reasons) == 1
        assert decision.asset_changes == ["style.css"]
        assert decision.fingerprint_changes is True

    def test_add_rebuild_reason(self):
        """Test add_rebuild_reason method."""
        decision = IncrementalDecision(
            pages_to_build=[],
            pages_skipped_count=0,
        )

        decision.add_rebuild_reason(
            "content/index.md",
            RebuildReasonCode.CONTENT_CHANGED,
        )

        assert "content/index.md" in decision.rebuild_reasons
        assert decision.rebuild_reasons["content/index.md"].code == RebuildReasonCode.CONTENT_CHANGED

    def test_add_rebuild_reason_with_details(self):
        """Test add_rebuild_reason method with details."""
        decision = IncrementalDecision(
            pages_to_build=[],
            pages_skipped_count=0,
        )

        decision.add_rebuild_reason(
            "content/index.md",
            RebuildReasonCode.ASSET_FINGERPRINT_CHANGED,
            {"assets": ["style.css"]},
        )

        assert decision.rebuild_reasons["content/index.md"].details == {"assets": ["style.css"]}

    def test_add_rebuild_reason_does_not_overwrite(self):
        """Test that add_rebuild_reason does not overwrite existing reasons."""
        decision = IncrementalDecision(
            pages_to_build=[],
            pages_skipped_count=0,
        )

        # Add first reason
        decision.add_rebuild_reason(
            "content/index.md",
            RebuildReasonCode.CONTENT_CHANGED,
        )

        # Try to add second reason (should be ignored)
        decision.add_rebuild_reason(
            "content/index.md",
            RebuildReasonCode.ASSET_FINGERPRINT_CHANGED,
        )

        # First reason should be preserved
        assert decision.rebuild_reasons["content/index.md"].code == RebuildReasonCode.CONTENT_CHANGED

    def test_get_reason_summary(self):
        """Test get_reason_summary returns counts by reason code."""
        decision = IncrementalDecision(
            pages_to_build=[],
            pages_skipped_count=0,
            rebuild_reasons={
                "content/index.md": RebuildReason(code=RebuildReasonCode.CONTENT_CHANGED),
                "content/about.md": RebuildReason(code=RebuildReasonCode.CONTENT_CHANGED),
                "content/blog.md": RebuildReason(code=RebuildReasonCode.ASSET_FINGERPRINT_CHANGED),
            },
        )

        summary = decision.get_reason_summary()

        assert summary["content_changed"] == 2
        assert summary["asset_fingerprint_changed"] == 1

    def test_log_summary(self):
        """Test log_summary emits INFO-level log."""
        mock_page = MagicMock()
        decision = IncrementalDecision(
            pages_to_build=[mock_page],
            pages_skipped_count=10,
            fingerprint_changes=True,
            asset_changes=["style.css"],
        )

        mock_logger = MagicMock()
        decision.log_summary(mock_logger)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "incremental_decision"
        assert call_args[1]["pages_to_build"] == 1
        assert call_args[1]["pages_skipped"] == 10
        assert call_args[1]["fingerprint_changes"] is True

    def test_log_details(self):
        """Test log_details emits DEBUG-level logs for each page."""
        decision = IncrementalDecision(
            pages_to_build=[],
            pages_skipped_count=0,
            rebuild_reasons={
                "content/index.md": RebuildReason(
                    code=RebuildReasonCode.CONTENT_CHANGED,
                ),
                "content/about.md": RebuildReason(
                    code=RebuildReasonCode.ASSET_FINGERPRINT_CHANGED,
                    details={"assets": ["style.css"]},
                ),
            },
        )

        mock_logger = MagicMock()
        decision.log_details(mock_logger)

        # Should be called twice (once per page)
        assert mock_logger.debug.call_count == 2

    def test_skip_reasons_only_populated_when_verbose(self):
        """Test that skip_reasons is typically empty and populated only when needed."""
        decision = IncrementalDecision(
            pages_to_build=[],
            pages_skipped_count=10,
        )

        # By default, skip_reasons should be empty (populated only when verbose=True)
        assert decision.skip_reasons == {}

        # Can be manually populated
        decision.skip_reasons["content/about.md"] = SkipReasonCode.NO_CHANGES
        assert len(decision.skip_reasons) == 1
