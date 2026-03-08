"""Regression guards for asset extraction fallback cost and usage."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from bengal.rendering.asset_extractor import extract_assets_from_html
from bengal.rendering.pipeline.core import RenderingPipeline
from tests.performance.autodoc_regression_fixtures import build_autodoc_like_html

_FALLBACK_METRICS: list[dict[str, float | int | str]] = []


@dataclass
class _DummyPage:
    source_path: Path
    rendered_html: str


@dataclass
class _DummyBuildContext:
    page_assets: dict[Path, set[str]]

    def accumulate_page_assets(self, source_path: Path, assets: set[str]) -> None:
        self.page_assets[source_path] = assets


def _pipeline_with_context() -> tuple[SimpleNamespace, _DummyBuildContext]:
    context = _DummyBuildContext(page_assets={})
    pipeline = SimpleNamespace(build_context=context)
    return pipeline, context


@pytest.fixture(scope="session", autouse=True)
def _write_fallback_metrics_artifact() -> None:
    yield
    cache_dir = Path(".pytest_cache")
    cache_dir.mkdir(exist_ok=True)
    out_path = cache_dir / "fallback_parser_metrics.json"
    out_path.write_text(json.dumps(_FALLBACK_METRICS, indent=2) + "\n")


@pytest.mark.performance
def test_tracked_assets_path_avoids_html_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """When tracked assets are available, HTML fallback parser must not run."""
    fallback_calls = {"count": 0}

    def _counting_extractor(html_content: str) -> set[str]:
        fallback_calls["count"] += 1
        return extract_assets_from_html(html_content)

    monkeypatch.setattr(
        "bengal.rendering.asset_extractor.extract_assets_from_html", _counting_extractor
    )

    pipeline, context = _pipeline_with_context()
    page = _DummyPage(
        source_path=Path("content/docs/autodoc-page.md"),
        rendered_html=build_autodoc_like_html(
            member_count=80,
            include_assets=True,
            include_empty_member_names=False,
        ),
    )
    tracked_assets = {"/assets/css/site.css", "/assets/js/site.js"}

    RenderingPipeline._accumulate_asset_deps(pipeline, page, tracked_assets=tracked_assets)
    _FALLBACK_METRICS.append(
        {
            "scenario": "tracked_assets_fast_path",
            "fallback_invocations": fallback_calls["count"],
            "parse_seconds_total": 0.0,
        }
    )

    assert fallback_calls["count"] == 0
    assert context.page_assets[page.source_path] == tracked_assets


@pytest.mark.performance
def test_missing_tracked_assets_uses_fallback_and_extracts_dependencies() -> None:
    """Fallback parser path should still populate dependency map correctly."""
    pipeline, context = _pipeline_with_context()
    page = _DummyPage(
        source_path=Path("content/docs/fallback-page.md"),
        rendered_html=build_autodoc_like_html(
            member_count=60,
            include_assets=True,
            include_empty_member_names=False,
        ),
    )

    start = time.perf_counter()
    RenderingPipeline._accumulate_asset_deps(pipeline, page, tracked_assets=None)
    parse_seconds = time.perf_counter() - start
    _FALLBACK_METRICS.append(
        {
            "scenario": "fallback_path_extract",
            "fallback_invocations": 1,
            "parse_seconds_total": parse_seconds,
        }
    )

    extracted = context.page_assets[page.source_path]
    assert "/assets/css/site.css" in extracted
    assert "/assets/js/site.js" in extracted
    assert any(asset.startswith("/assets/images/") for asset in extracted)


@pytest.mark.performance
def test_fallback_parse_cost_remains_near_linear() -> None:
    """
    Fallback parse cost should scale near-linearly with HTML size.

    Guards against pathological parser amplification where larger HTML causes
    disproportionate slowdown beyond normal linear growth.
    """
    baseline_html = build_autodoc_like_html(
        member_count=80,
        include_assets=True,
        include_empty_member_names=False,
    )
    larger_html = build_autodoc_like_html(
        member_count=800,
        include_assets=True,
        include_empty_member_names=False,
    )

    def _run_extract(html_content: str, rounds: int = 3) -> float:
        timings: list[float] = []
        for _ in range(rounds):
            start = time.perf_counter()
            extract_assets_from_html(html_content)
            timings.append(time.perf_counter() - start)
        return sorted(timings)[len(timings) // 2]

    baseline_s = _run_extract(baseline_html)
    larger_s = _run_extract(larger_html)
    baseline_per_byte = baseline_s / len(baseline_html)
    larger_per_byte = larger_s / len(larger_html)
    _FALLBACK_METRICS.append(
        {
            "scenario": "fallback_parser_scaling",
            "fallback_invocations": 6,
            "parse_seconds_total": baseline_s * 3 + larger_s * 3,
            "baseline_seconds": baseline_s,
            "larger_seconds": larger_s,
            "per_byte_ratio": larger_per_byte / baseline_per_byte,
        }
    )

    # Allow substantial variance while still catching severe parser amplification.
    assert larger_per_byte / baseline_per_byte <= 4.0
