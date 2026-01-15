"""
Composable change detection pipeline.

Detectors are composed in explicit order. Each detector
receives results from previous detectors via context.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.build.contracts.protocol import ChangeDetector, DetectionContext
    from bengal.build.contracts.results import ChangeDetectionResult

logger = get_logger(__name__)


@dataclass
class DetectionPipeline:
    """
    Ordered sequence of change detectors.

    Detectors run in sequence, each receiving accumulated
    results from previous detectors.
    """

    detectors: Sequence["ChangeDetector"]

    def run(self, ctx: "DetectionContext") -> "ChangeDetectionResult":
        current_ctx = ctx

        for detector in self.detectors:
            detector_name = type(detector).__name__
            logger.debug(
                "detector_start",
                detector=detector_name,
                previous_pages=len(current_ctx.previous.pages_to_rebuild),
            )

            result = detector.detect(current_ctx)

            logger.debug(
                "detector_complete",
                detector=detector_name,
                pages_found=len(result.pages_to_rebuild),
                data_files=len(result.data_files_changed),
                templates=len(result.templates_changed),
            )

            current_ctx = current_ctx.with_previous(result)

            if result.force_full_rebuild:
                logger.info(
                    "full_rebuild_triggered",
                    detector=detector_name,
                )
                break

        return current_ctx.previous


def create_early_pipeline() -> DetectionPipeline:
    """Pipeline for early (pre-taxonomy) detection."""
    from bengal.build.detectors import (
        ContentChangeDetector,
        DataChangeDetector,
        TemplateChangeDetector,
    )

    return DetectionPipeline(
        [
            ContentChangeDetector(),
            DataChangeDetector(),
            TemplateChangeDetector(),
        ]
    )


def create_full_pipeline() -> DetectionPipeline:
    """Pipeline for full (post-taxonomy) detection."""
    from bengal.build.detectors import (
        AutodocChangeDetector,
        TaxonomyCascadeDetector,
        VersionChangeDetector,
    )

    return DetectionPipeline(
        [
            TaxonomyCascadeDetector(),
            AutodocChangeDetector(),
            VersionChangeDetector(),
        ]
    )
