from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bengal.build.contracts.keys import CacheKey
from bengal.build.contracts.protocol import DetectionContext
from bengal.build.contracts.results import ChangeDetectionResult
from bengal.build.pipeline import DetectionPipeline


@dataclass
class DummyDetector:
    result: ChangeDetectionResult
    called: bool = False

    def detect(self, ctx: DetectionContext) -> ChangeDetectionResult:
        self.called = True
        return self.result


class DummyCache:
    pass


class DummySite:
    root_path = Path(".")
    pages: list = []
    assets: list = []
    page_by_source_path = {}


def test_pipeline_accumulates_results() -> None:
    detector1 = DummyDetector(
        ChangeDetectionResult(pages_to_rebuild=frozenset({CacheKey("page1.md")}))
    )
    detector2 = DummyDetector(
        ChangeDetectionResult(pages_to_rebuild=frozenset({CacheKey("page2.md")}))
    )

    pipeline = DetectionPipeline([detector1, detector2])
    ctx = DetectionContext(cache=DummyCache(), site=DummySite())
    result = pipeline.run(ctx)

    assert CacheKey("page1.md") in result.pages_to_rebuild
    assert CacheKey("page2.md") in result.pages_to_rebuild


def test_pipeline_short_circuits_on_full_rebuild() -> None:
    detector1 = DummyDetector(ChangeDetectionResult(force_full_rebuild=True))
    detector2 = DummyDetector(ChangeDetectionResult())

    pipeline = DetectionPipeline([detector1, detector2])
    ctx = DetectionContext(cache=DummyCache(), site=DummySite())
    result = pipeline.run(ctx)

    assert result.force_full_rebuild
    assert detector1.called
    assert not detector2.called
