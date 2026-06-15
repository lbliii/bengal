"""Unit tests for bengal.rendering.pipeline.json_accumulator.JsonAccumulator."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from bengal.orchestration.stats import BuildStats
from bengal.rendering.pipeline.json_accumulator import JsonAccumulator


class _ExplodingPage:
    """Page whose content-derivative access raises a long error.

    URL-shaped attributes resolve cleanly so the first failure inside
    ``accumulate_unified_page_data`` is the content-derivative access
    (``plain_text``). The error message is intentionally longer than 100
    characters so a test can prove the recorded warning is NOT truncated.
    """

    LONG_ERROR = (
        "plain_text rendering blew up because of a deeply nested directive that "
        "could not be resolved and produced an unexpectedly verbose traceback "
        "well beyond one hundred characters of detail"
    )

    def __init__(self) -> None:
        self.source_path = Path("/content/exploding.md")
        self.title = "Exploding"
        self.metadata: dict[str, Any] = {}
        self.tags: list[str] = []
        # URL-shaped attributes used by get_page_url / get_page_relative_url.
        self.href = "/exploding/"
        self._path = "/exploding/"

    @property
    def plain_text(self) -> str:
        raise RuntimeError(self.LONG_ERROR)


def _make_site() -> Any:
    site = MagicMock()
    site.config = {}
    return site


class TestAccumulationFailureSurfacesWarning:
    """accumulate_unified_page_data must surface failures as build warnings."""

    def test_records_single_untruncated_build_warning_on_failure(self) -> None:
        """A failing page records exactly one non-truncated build-stats warning.

        RED on unfixed code: the failure is swallowed at logger.debug and the
        BuildStats warnings list stays empty.
        """
        stats = BuildStats()
        build_context = MagicMock()
        build_context.stats = stats

        site = _make_site()
        accumulator = JsonAccumulator(site, build_context)

        page = _ExplodingPage()
        accumulator.accumulate_unified_page_data(page)

        # Exactly one warning recorded.
        assert len(stats.warnings) == 1, (
            f"expected exactly one recorded warning, got {len(stats.warnings)}"
        )

        warning = stats.warnings[0]
        # The full error text must be present (not truncated to 100 chars).
        assert _ExplodingPage.LONG_ERROR in warning.message, (
            "recorded warning message must contain the full, untruncated error"
        )
        assert len(_ExplodingPage.LONG_ERROR) > 100
        # File path of the offending page is recorded for actionability.
        assert "exploding.md" in warning.file_path

    def test_build_completes_without_reraising(self) -> None:
        """The accumulation failure must not propagate (build keeps going)."""
        stats = BuildStats()
        build_context = MagicMock()
        build_context.stats = stats

        accumulator = JsonAccumulator(_make_site(), build_context)

        # Should not raise.
        accumulator.accumulate_unified_page_data(_ExplodingPage())
