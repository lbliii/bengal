"""
Unit tests for bengal.build.contracts.results.

Tests ChangeDetectionResult, RebuildReason, and RebuildReasonCode.
"""

from __future__ import annotations

import pytest

from bengal.build.contracts.keys import CacheKey
from bengal.build.contracts.results import (
    ChangeDetectionResult,
    RebuildReason,
    RebuildReasonCode,
)

# =============================================================================
# RebuildReasonCode Tests
# =============================================================================


class TestRebuildReasonCode:
    """Tests for RebuildReasonCode enum."""

    def test_all_reason_codes_exist(self) -> None:
        """All expected reason codes are defined."""
        expected_codes = [
            "CONTENT_CHANGED",
            "DATA_FILE_CHANGED",
            "TEMPLATE_CHANGED",
            "TAXONOMY_CASCADE",
            "CASCADE",
            "ASSET_FINGERPRINT_CHANGED",
            "CONFIG_CHANGED",
            "OUTPUT_MISSING",
            "CROSS_VERSION_DEPENDENCY",
            "ADJACENT_NAV_CHANGED",
            "FORCED",
            "FULL_REBUILD",
        ]
        actual_codes = [code.name for code in RebuildReasonCode]
        for code in expected_codes:
            assert code in actual_codes, f"Missing reason code: {code}"

    def test_reason_codes_are_unique(self) -> None:
        """All reason code values are unique."""
        values = [code.value for code in RebuildReasonCode]
        assert len(values) == len(set(values)), "Duplicate reason code values found"


# =============================================================================
# RebuildReason Tests
# =============================================================================


class TestRebuildReason:
    """Tests for RebuildReason dataclass."""

    def test_creates_with_code_only(self) -> None:
        """RebuildReason can be created with code only."""
        reason = RebuildReason(code=RebuildReasonCode.CONTENT_CHANGED)
        assert reason.code == RebuildReasonCode.CONTENT_CHANGED
        assert reason.trigger == ""

    def test_creates_with_code_and_trigger(self) -> None:
        """RebuildReason can be created with code and trigger."""
        reason = RebuildReason(
            code=RebuildReasonCode.DATA_FILE_CHANGED,
            trigger="data/team.yaml",
        )
        assert reason.code == RebuildReasonCode.DATA_FILE_CHANGED
        assert reason.trigger == "data/team.yaml"

    def test_str_without_trigger(self) -> None:
        """__str__ returns code name when no trigger."""
        reason = RebuildReason(code=RebuildReasonCode.FORCED)
        assert str(reason) == "FORCED"

    def test_str_with_trigger(self) -> None:
        """__str__ includes trigger when present."""
        reason = RebuildReason(
            code=RebuildReasonCode.TEMPLATE_CHANGED,
            trigger="templates/base.html",
        )
        assert str(reason) == "TEMPLATE_CHANGED: templates/base.html"

    def test_is_frozen(self) -> None:
        """RebuildReason is immutable (frozen)."""
        reason = RebuildReason(code=RebuildReasonCode.CONTENT_CHANGED)
        with pytest.raises(AttributeError):
            reason.code = RebuildReasonCode.FORCED  # type: ignore[misc]


# =============================================================================
# ChangeDetectionResult Tests
# =============================================================================


class TestChangeDetectionResult:
    """Tests for ChangeDetectionResult dataclass."""

    def test_empty_creates_default_values(self) -> None:
        """empty() creates result with default values."""
        result = ChangeDetectionResult.empty()
        assert result.pages_to_rebuild == frozenset()
        assert result.rebuild_reasons == {}
        assert result.assets_to_process == frozenset()
        assert result.content_files_changed == frozenset()
        assert result.data_files_changed == frozenset()
        assert result.templates_changed == frozenset()
        assert result.affected_tags == frozenset()
        assert result.affected_sections == frozenset()
        assert result.config_changed is False
        assert result.force_full_rebuild is False

    def test_full_rebuild_sets_flag(self) -> None:
        """full_rebuild() creates result with force_full_rebuild=True."""
        result = ChangeDetectionResult.full_rebuild()
        assert result.force_full_rebuild is True

    def test_needs_rebuild_with_pages(self) -> None:
        """needs_rebuild returns True when pages need rebuilding."""
        result = ChangeDetectionResult(pages_to_rebuild=frozenset([CacheKey("content/about.md")]))
        assert result.needs_rebuild is True

    def test_needs_rebuild_with_full_rebuild(self) -> None:
        """needs_rebuild returns True when force_full_rebuild is True."""
        result = ChangeDetectionResult(force_full_rebuild=True)
        assert result.needs_rebuild is True

    def test_needs_rebuild_when_empty(self) -> None:
        """needs_rebuild returns False when no changes."""
        result = ChangeDetectionResult.empty()
        assert result.needs_rebuild is False

    def test_merge_combines_pages(self) -> None:
        """merge() combines pages_to_rebuild from both results."""
        result1 = ChangeDetectionResult(pages_to_rebuild=frozenset([CacheKey("page1.md")]))
        result2 = ChangeDetectionResult(pages_to_rebuild=frozenset([CacheKey("page2.md")]))
        merged = result1.merge(result2)
        assert CacheKey("page1.md") in merged.pages_to_rebuild
        assert CacheKey("page2.md") in merged.pages_to_rebuild

    def test_merge_combines_rebuild_reasons(self) -> None:
        """merge() combines rebuild_reasons from both results."""
        reason1 = RebuildReason(RebuildReasonCode.CONTENT_CHANGED)
        reason2 = RebuildReason(RebuildReasonCode.DATA_FILE_CHANGED)
        result1 = ChangeDetectionResult(rebuild_reasons={CacheKey("page1.md"): reason1})
        result2 = ChangeDetectionResult(rebuild_reasons={CacheKey("page2.md"): reason2})
        merged = result1.merge(result2)
        assert CacheKey("page1.md") in merged.rebuild_reasons
        assert CacheKey("page2.md") in merged.rebuild_reasons

    def test_merge_combines_assets(self) -> None:
        """merge() combines assets_to_process from both results."""
        result1 = ChangeDetectionResult(assets_to_process=frozenset([CacheKey("style.css")]))
        result2 = ChangeDetectionResult(assets_to_process=frozenset([CacheKey("main.js")]))
        merged = result1.merge(result2)
        assert CacheKey("style.css") in merged.assets_to_process
        assert CacheKey("main.js") in merged.assets_to_process

    def test_merge_combines_content_files(self) -> None:
        """merge() combines content_files_changed from both results."""
        result1 = ChangeDetectionResult(content_files_changed=frozenset([CacheKey("content/a.md")]))
        result2 = ChangeDetectionResult(content_files_changed=frozenset([CacheKey("content/b.md")]))
        merged = result1.merge(result2)
        assert CacheKey("content/a.md") in merged.content_files_changed
        assert CacheKey("content/b.md") in merged.content_files_changed

    def test_merge_combines_data_files(self) -> None:
        """merge() combines data_files_changed from both results."""
        result1 = ChangeDetectionResult(
            data_files_changed=frozenset([CacheKey("data:data/a.yaml")])
        )
        result2 = ChangeDetectionResult(
            data_files_changed=frozenset([CacheKey("data:data/b.yaml")])
        )
        merged = result1.merge(result2)
        assert CacheKey("data:data/a.yaml") in merged.data_files_changed
        assert CacheKey("data:data/b.yaml") in merged.data_files_changed

    def test_merge_combines_templates(self) -> None:
        """merge() combines templates_changed from both results."""
        result1 = ChangeDetectionResult(templates_changed=frozenset([CacheKey("base.html")]))
        result2 = ChangeDetectionResult(templates_changed=frozenset([CacheKey("single.html")]))
        merged = result1.merge(result2)
        assert CacheKey("base.html") in merged.templates_changed
        assert CacheKey("single.html") in merged.templates_changed

    def test_merge_combines_tags(self) -> None:
        """merge() combines affected_tags from both results."""
        result1 = ChangeDetectionResult(affected_tags=frozenset(["python"]))
        result2 = ChangeDetectionResult(affected_tags=frozenset(["rust"]))
        merged = result1.merge(result2)
        assert "python" in merged.affected_tags
        assert "rust" in merged.affected_tags

    def test_merge_combines_sections(self) -> None:
        """merge() combines affected_sections from both results."""
        result1 = ChangeDetectionResult(affected_sections=frozenset([CacheKey("docs")]))
        result2 = ChangeDetectionResult(affected_sections=frozenset([CacheKey("blog")]))
        merged = result1.merge(result2)
        assert CacheKey("docs") in merged.affected_sections
        assert CacheKey("blog") in merged.affected_sections

    def test_merge_ors_config_changed(self) -> None:
        """merge() ORs config_changed from both results."""
        result1 = ChangeDetectionResult(config_changed=True)
        result2 = ChangeDetectionResult(config_changed=False)
        merged = result1.merge(result2)
        assert merged.config_changed is True

    def test_merge_ors_force_full_rebuild(self) -> None:
        """merge() ORs force_full_rebuild from both results."""
        result1 = ChangeDetectionResult(force_full_rebuild=True)
        result2 = ChangeDetectionResult(force_full_rebuild=False)
        merged = result1.merge(result2)
        assert merged.force_full_rebuild is True

    def test_with_pages_adds_pages(self) -> None:
        """with_pages() adds pages to result."""
        result = ChangeDetectionResult.empty()
        reason = RebuildReason(RebuildReasonCode.CONTENT_CHANGED)
        new_result = result.with_pages(
            frozenset([CacheKey("page.md")]),
            reason,
        )
        assert CacheKey("page.md") in new_result.pages_to_rebuild
        assert new_result.rebuild_reasons[CacheKey("page.md")] == reason

    def test_with_pages_preserves_existing_reason(self) -> None:
        """with_pages() does not overwrite existing rebuild reason."""
        reason1 = RebuildReason(RebuildReasonCode.CONTENT_CHANGED)
        reason2 = RebuildReason(RebuildReasonCode.DATA_FILE_CHANGED)
        result = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("page.md")]),
            rebuild_reasons={CacheKey("page.md"): reason1},
        )
        new_result = result.with_pages(
            frozenset([CacheKey("page.md")]),
            reason2,
        )
        # Original reason should be preserved
        assert new_result.rebuild_reasons[CacheKey("page.md")] == reason1

    def test_with_pages_returns_new_instance(self) -> None:
        """with_pages() returns new instance (immutable)."""
        result = ChangeDetectionResult.empty()
        reason = RebuildReason(RebuildReasonCode.CONTENT_CHANGED)
        new_result = result.with_pages(frozenset([CacheKey("page.md")]), reason)
        assert new_result is not result
        assert result.pages_to_rebuild == frozenset()

    def test_summary_empty(self) -> None:
        """summary() returns 'no changes' for empty result."""
        result = ChangeDetectionResult.empty()
        assert result.summary() == "no changes"

    def test_summary_full_rebuild(self) -> None:
        """summary() includes 'FULL REBUILD' when force_full_rebuild."""
        result = ChangeDetectionResult(force_full_rebuild=True)
        assert "FULL REBUILD" in result.summary()

    def test_summary_pages(self) -> None:
        """summary() includes page count."""
        result = ChangeDetectionResult(
            pages_to_rebuild=frozenset([CacheKey("a.md"), CacheKey("b.md")])
        )
        assert "2 pages" in result.summary()

    def test_summary_assets(self) -> None:
        """summary() includes asset count."""
        result = ChangeDetectionResult(assets_to_process=frozenset([CacheKey("style.css")]))
        assert "1 assets" in result.summary()

    def test_summary_data_files(self) -> None:
        """summary() includes data file count."""
        result = ChangeDetectionResult(
            data_files_changed=frozenset([CacheKey("data:data/team.yaml")])
        )
        assert "1 data files" in result.summary()

    def test_summary_templates(self) -> None:
        """summary() includes template count."""
        result = ChangeDetectionResult(
            templates_changed=frozenset([CacheKey("base.html"), CacheKey("single.html")])
        )
        assert "2 templates" in result.summary()

    def test_is_frozen(self) -> None:
        """ChangeDetectionResult is immutable (frozen)."""
        result = ChangeDetectionResult.empty()
        with pytest.raises(AttributeError):
            result.config_changed = True  # type: ignore[misc]
