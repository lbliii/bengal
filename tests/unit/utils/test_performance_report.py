"""Tests for Kida-routed performance reporting."""

from __future__ import annotations

import json

from bengal.utils.observability.performance_report import PerformanceReport


def _write_metric(metrics_dir, **overrides):
    metrics_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp": "2026-05-03T12:00:00",
        "total_pages": 12,
        "build_time_ms": 1200,
        "memory_rss_mb": 18.5,
        "memory_heap_mb": 7.0,
        "memory_peak_mb": 22.0,
        "parallel": True,
        "incremental": False,
        "skipped": False,
        "discovery_time_ms": 100,
        "taxonomy_time_ms": 80,
        "rendering_time_ms": 900,
        "assets_time_ms": 50,
        "postprocess_time_ms": 70,
    }
    data.update(overrides)
    with (metrics_dir / "history.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")


def test_show_table_renders_through_cli_templates(tmp_path, capsys):
    """Performance history should render via CLIOutput/Kida instead of print."""
    metrics_dir = tmp_path / "metrics"
    _write_metric(metrics_dir)

    PerformanceReport(metrics_dir=metrics_dir).show(last=1, format="table")

    output = capsys.readouterr().out
    assert "Performance History" in output
    assert "Builds shown" in output
    assert "2026-05-03 12:00" in output
    assert "18.5MB" in output


def test_show_json_renders_json_template(tmp_path, capsys):
    """JSON performance output should still be machine-readable."""
    metrics_dir = tmp_path / "metrics"
    _write_metric(metrics_dir)

    PerformanceReport(metrics_dir=metrics_dir).show(last=1, format="json")

    output = capsys.readouterr().out
    assert '"pages": 12' in output
    assert '"parallel": true' in output


def test_compare_renders_kida_table(tmp_path, capsys):
    """Build comparison should render through the shared CLI bridge."""
    metrics_dir = tmp_path / "metrics"
    _write_metric(metrics_dir, timestamp="2026-05-03T12:00:00", build_time_ms=1000)
    _write_metric(metrics_dir, timestamp="2026-05-03T12:05:00", build_time_ms=1500)

    PerformanceReport(metrics_dir=metrics_dir).compare()

    output = capsys.readouterr().out
    assert "Build Comparison" in output
    assert "Build time" in output
    assert "1.50s" in output
    assert "1.00s" in output
