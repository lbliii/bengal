"""Post-render pipeline budget smoke tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.performance.post_render_harness import (
    create_post_render_site,
    run_post_render_scenarios,
    write_metrics,
)


@pytest.mark.performance
def test_post_render_pipeline_tail_is_measured_and_bounded(tmp_path: Path) -> None:
    """Exercise the user-visible tail after rendering on common warm scenarios."""
    site_root = create_post_render_site(tmp_path, page_count=40)
    metrics = run_post_render_scenarios(site_root)
    by_name = {metric.scenario: metric for metric in metrics}

    write_metrics(Path(".pytest_cache/post_render_pipeline_metrics.json"), metrics)

    cold = by_name["cold"]
    warm_noop = by_name["warm_noop"]
    single_page = by_name["single_page_edit"]
    css_only = by_name["css_only_edit"]

    assert cold.postprocess_task_timings_ms
    assert cold.post_render_timings_ms
    assert warm_noop.pages_rendered <= 1
    assert single_page.pages_rendered <= 3

    cold_tail = max(cold.tail_time_ms, 1.0)
    assert warm_noop.tail_time_ms <= cold_tail * 1.25
    assert single_page.tail_time_ms <= cold_tail * 1.50
    assert css_only.tail_time_ms <= cold_tail * 1.50

    assert warm_noop.store_sizes is not None
    assert warm_noop.store_sizes.state_total_bytes > 0
