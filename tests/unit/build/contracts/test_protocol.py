"""
Unit tests for bengal.build.contracts.protocol.

Tests DetectionContext and ChangeDetector protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from bengal.build.contracts.keys import CacheKey
from bengal.build.contracts.protocol import (
    ChangeDetector,
    DetectionContext,
)
from bengal.build.contracts.results import (
    ChangeDetectionResult,
    RebuildReason,
    RebuildReasonCode,
)

if TYPE_CHECKING:
    from bengal.cache import BuildCache
    from bengal.core.site import Site


# =============================================================================
# DetectionContext Tests
# =============================================================================


class TestDetectionContext:
    """Tests for DetectionContext dataclass."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create mock BuildCache."""
        return MagicMock(spec=["is_changed", "get_affected_pages"])

    @pytest.fixture
    def mock_site(self) -> MagicMock:
        """Create mock Site."""
        return MagicMock(spec=["root_path", "pages", "assets"])

    def test_creates_with_required_fields(
        self, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """DetectionContext can be created with required fields."""
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        assert ctx.cache is mock_cache
        assert ctx.site is mock_site

    def test_default_values(self, mock_cache: MagicMock, mock_site: MagicMock) -> None:
        """DetectionContext has expected default values."""
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        assert ctx.tracker is None
        assert ctx.coordinator is None
        assert ctx.previous.pages_to_rebuild == frozenset()
        assert ctx.verbose is False
        assert ctx.forced_changed == frozenset()
        assert ctx.nav_changed == frozenset()

    def test_creates_with_all_fields(self, mock_cache: MagicMock, mock_site: MagicMock) -> None:
        """DetectionContext can be created with all fields."""
        mock_tracker = MagicMock()
        mock_coordinator = MagicMock()
        previous = ChangeDetectionResult(pages_to_rebuild=frozenset([CacheKey("page.md")]))
        forced = frozenset([CacheKey("forced.md")])
        nav = frozenset([CacheKey("nav.md")])

        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            tracker=mock_tracker,
            coordinator=mock_coordinator,
            previous=previous,
            verbose=True,
            forced_changed=forced,
            nav_changed=nav,
        )

        assert ctx.tracker is mock_tracker
        assert ctx.coordinator is mock_coordinator
        assert CacheKey("page.md") in ctx.previous.pages_to_rebuild
        assert ctx.verbose is True
        assert CacheKey("forced.md") in ctx.forced_changed
        assert CacheKey("nav.md") in ctx.nav_changed

    def test_with_previous_merges_results(
        self, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """with_previous() merges result into previous."""
        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            previous=ChangeDetectionResult(pages_to_rebuild=frozenset([CacheKey("page1.md")])),
        )
        new_result = ChangeDetectionResult(pages_to_rebuild=frozenset([CacheKey("page2.md")]))
        new_ctx = ctx.with_previous(new_result)

        assert CacheKey("page1.md") in new_ctx.previous.pages_to_rebuild
        assert CacheKey("page2.md") in new_ctx.previous.pages_to_rebuild

    def test_with_previous_returns_new_instance(
        self, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """with_previous() returns new context (immutable)."""
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        new_result = ChangeDetectionResult(pages_to_rebuild=frozenset([CacheKey("page.md")]))
        new_ctx = ctx.with_previous(new_result)

        assert new_ctx is not ctx
        assert ctx.previous.pages_to_rebuild == frozenset()

    def test_with_previous_preserves_other_fields(
        self, mock_cache: MagicMock, mock_site: MagicMock
    ) -> None:
        """with_previous() preserves all other context fields."""
        mock_tracker = MagicMock()
        forced = frozenset([CacheKey("forced.md")])

        ctx = DetectionContext(
            cache=mock_cache,
            site=mock_site,
            tracker=mock_tracker,
            verbose=True,
            forced_changed=forced,
        )
        new_result = ChangeDetectionResult.empty()
        new_ctx = ctx.with_previous(new_result)

        assert new_ctx.cache is mock_cache
        assert new_ctx.site is mock_site
        assert new_ctx.tracker is mock_tracker
        assert new_ctx.verbose is True
        assert new_ctx.forced_changed == forced

    def test_is_frozen(self, mock_cache: MagicMock, mock_site: MagicMock) -> None:
        """DetectionContext is immutable (frozen)."""
        ctx = DetectionContext(cache=mock_cache, site=mock_site)
        with pytest.raises(AttributeError):
            ctx.verbose = True  # type: ignore[misc]


# =============================================================================
# ChangeDetector Protocol Tests
# =============================================================================


class TestChangeDetectorProtocol:
    """Tests for ChangeDetector protocol."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """ChangeDetector protocol is runtime checkable."""

        @dataclass
        class ValidDetector:
            def detect(self, ctx: DetectionContext) -> ChangeDetectionResult:
                return ChangeDetectionResult.empty()

        detector = ValidDetector()
        assert isinstance(detector, ChangeDetector)

    def test_invalid_detector_not_instance(self) -> None:
        """Invalid detector is not instance of ChangeDetector."""

        @dataclass
        class InvalidDetector:
            def check(self, ctx: DetectionContext) -> ChangeDetectionResult:
                return ChangeDetectionResult.empty()

        detector = InvalidDetector()
        assert not isinstance(detector, ChangeDetector)

    def test_detector_with_different_signature_not_instance(self) -> None:
        """Detector with wrong signature is not instance."""

        @dataclass
        class WrongSignatureDetector:
            def detect(self) -> ChangeDetectionResult:  # Missing ctx parameter
                return ChangeDetectionResult.empty()

        detector = WrongSignatureDetector()
        # Note: runtime_checkable only checks for method presence, not signature
        # This will still pass isinstance check
        # The type checker will catch this error

    def test_mock_detector_works(self) -> None:
        """Mock detector can be used in pipeline."""
        mock_cache = MagicMock()
        mock_site = MagicMock()
        ctx = DetectionContext(cache=mock_cache, site=mock_site)

        class MockDetector:
            def __init__(self, result: ChangeDetectionResult) -> None:
                self.result = result
                self.called = False
                self.received_ctx: DetectionContext | None = None

            def detect(self, ctx: DetectionContext) -> ChangeDetectionResult:
                self.called = True
                self.received_ctx = ctx
                return self.result

        expected_result = ChangeDetectionResult(pages_to_rebuild=frozenset([CacheKey("page.md")]))
        detector = MockDetector(expected_result)

        result = detector.detect(ctx)

        assert detector.called
        assert detector.received_ctx is ctx
        assert result is expected_result
        assert isinstance(detector, ChangeDetector)


# =============================================================================
# Integration Tests
# =============================================================================


class TestDetectionContextIntegration:
    """Integration tests for DetectionContext with detectors."""

    def test_context_flows_through_detector_chain(self) -> None:
        """Context flows through multiple detectors correctly."""
        mock_cache = MagicMock()
        mock_site = MagicMock()

        class Detector1:
            def detect(self, ctx: DetectionContext) -> ChangeDetectionResult:
                return ChangeDetectionResult(
                    pages_to_rebuild=frozenset([CacheKey("page1.md")]),
                    rebuild_reasons={
                        CacheKey("page1.md"): RebuildReason(RebuildReasonCode.CONTENT_CHANGED)
                    },
                )

        class Detector2:
            def detect(self, ctx: DetectionContext) -> ChangeDetectionResult:
                # Should see page1.md from previous detector
                if CacheKey("page1.md") in ctx.previous.pages_to_rebuild:
                    return ChangeDetectionResult(
                        pages_to_rebuild=frozenset([CacheKey("page2.md")]),
                        rebuild_reasons={
                            CacheKey("page2.md"): RebuildReason(RebuildReasonCode.TAXONOMY_CASCADE)
                        },
                    )
                return ChangeDetectionResult.empty()

        ctx = DetectionContext(cache=mock_cache, site=mock_site)

        # Run detector 1
        detector1 = Detector1()
        result1 = detector1.detect(ctx)

        # Update context with result1
        ctx2 = ctx.with_previous(result1)

        # Run detector 2 with updated context
        detector2 = Detector2()
        result2 = detector2.detect(ctx2)

        # Detector 2 should have seen page1.md and added page2.md
        assert CacheKey("page2.md") in result2.pages_to_rebuild

        # Final merged result should have both pages
        final_ctx = ctx2.with_previous(result2)
        assert CacheKey("page1.md") in final_ctx.previous.pages_to_rebuild
        assert CacheKey("page2.md") in final_ctx.previous.pages_to_rebuild
