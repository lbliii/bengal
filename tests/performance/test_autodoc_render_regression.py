"""Regression guards for autodoc-like render output shape and size drift."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from tests.performance.autodoc_regression_fixtures import (
    build_autodoc_like_html,
    build_real_members_template_html,
    collect_output_metrics,
    load_baseline,
)

_METRICS_ROWS: list[dict[str, object]] = []


def _record_metrics(page_type: str, metrics: dict[str, int | str]) -> None:
    _METRICS_ROWS.append(
        {
            "page_type": page_type,
            **metrics,
        }
    )


@pytest.fixture(scope="session", autouse=True)
def _write_metrics_artifact() -> None:
    yield
    cache_dir = Path(".pytest_cache")
    cache_dir.mkdir(exist_ok=True)
    out_path = cache_dir / "render_output_metrics.json"
    out_path.write_text(json.dumps(_METRICS_ROWS, indent=2) + "\n")


def _median_render_ms(*, member_count: int, rounds: int = 5) -> float:
    timings_ms: list[float] = []
    for _ in range(rounds):
        start = time.perf_counter()
        html = build_autodoc_like_html(
            member_count=member_count,
            include_assets=True,
            include_empty_member_names=False,
        )
        collect_output_metrics(html)
        timings_ms.append((time.perf_counter() - start) * 1000.0)
    return sorted(timings_ms)[len(timings_ms) // 2]


@pytest.mark.performance
def test_autodoc_output_shape_matches_baseline() -> None:
    """
    Regression guard for deterministic output shape.

    This catches silent structure drift (unexpected empty member names, changed
    card counts, or shape hash changes) even if HTML is still technically valid.
    """
    baseline = load_baseline()
    fixture = baseline["fixture"]
    metrics = baseline["metrics"]

    html = build_autodoc_like_html(
        member_count=int(fixture["member_count"]),
        include_assets=bool(fixture["include_assets"]),
        include_empty_member_names=bool(fixture["include_empty_member_names"]),
    )
    current = collect_output_metrics(html)
    _record_metrics("autodoc_synthetic_default", current.to_dict())

    assert current.details_count == int(metrics["details_count"])
    assert current.asset_ref_count == int(metrics["asset_ref_count"])
    assert current.shape_hash == str(metrics["shape_hash"])
    assert current.empty_member_name_count <= int(
        baseline["budgets"]["max_empty_member_name_count"]
    )


@pytest.mark.performance
def test_autodoc_output_size_and_timing_budgets() -> None:
    """
    Enforce conservative size/timing budgets for the regression fixture.

    Uses ratio-style checks against a checked-in baseline rather than hardcoded
    absolute timing values to keep CI stable across runners.
    """
    baseline = load_baseline()
    fixture = baseline["fixture"]
    metrics = baseline["metrics"]
    budgets = baseline["budgets"]

    html = build_autodoc_like_html(
        member_count=int(fixture["member_count"]),
        include_assets=bool(fixture["include_assets"]),
        include_empty_member_names=bool(fixture["include_empty_member_names"]),
    )
    current = collect_output_metrics(html)
    _record_metrics("autodoc_synthetic_size_budget", current.to_dict())

    growth_ratio = current.total_bytes / int(metrics["total_bytes"])
    assert current.total_bytes <= int(budgets["max_total_bytes"])
    assert growth_ratio <= float(budgets["max_bytes_growth_ratio"])

    baseline_render_ms = _median_render_ms(member_count=int(fixture["member_count"]))
    heavier_render_ms = _median_render_ms(member_count=int(fixture["member_count"]) * 2)
    # The synthetic fixture scales linearly; this check catches accidental super-linear behavior.
    assert heavier_render_ms / baseline_render_ms <= 2.5


@pytest.mark.performance
@pytest.mark.parametrize("profile", ["public_heavy", "internal_heavy", "long_signatures"])
def test_real_template_members_profiles_match_baseline(profile: str) -> None:
    """Render real members template and enforce profile-specific shape/size budgets."""
    baseline = load_baseline()
    matrix = baseline["fixture_matrix"][profile]
    metrics = matrix["metrics"]
    budgets = matrix["budgets"]

    rendered = build_real_members_template_html(profile)
    current = collect_output_metrics(rendered)
    _record_metrics(f"autodoc_real_template_{profile}", current.to_dict())

    assert current.shape_hash == str(metrics["shape_hash"])
    assert current.details_count == int(metrics["details_count"])
    assert current.total_bytes <= int(budgets["max_total_bytes"])
    assert current.empty_member_name_count <= int(budgets["max_empty_member_name_count"])
