"""Kida rendering helpers for debug-style CLI reports."""

from __future__ import annotations

from typing import Any


def render_debug_report(cli: Any, report: Any, *, title: str | None = None) -> None:
    """Render a DebugReport-like object through shared Kida templates."""
    report_title = title or f"{getattr(report, 'tool_name', 'Debug')} Report"
    items = [
        {"label": "Summary", "value": getattr(report, "summary", "") or "No summary"},
        {"label": "Findings", "value": str(len(getattr(report, "findings", [])))},
    ]
    if getattr(report, "error_count", 0):
        items.append({"label": "Errors", "value": str(report.error_count)})
    if getattr(report, "warning_count", 0):
        items.append({"label": "Warnings", "value": str(report.warning_count)})
    if getattr(report, "execution_time_ms", 0):
        items.append({"label": "Execution time", "value": f"{report.execution_time_ms:.1f}ms"})
    for key, value in getattr(report, "statistics", {}).items():
        items.append({"label": str(key).replace("_", " ").title(), "value": str(value)})

    cli.render_write("kv_detail.kida", title=report_title, items=items)

    findings = getattr(report, "findings", [])
    if findings:
        cli.render_write(
            "item_list.kida",
            title="Findings",
            items=[{"name": finding.format_short(), "description": ""} for finding in findings],
        )

    recommendations = getattr(report, "recommendations", [])
    if recommendations:
        cli.render_write(
            "item_list.kida",
            title="Recommendations",
            items=[{"name": rec, "description": ""} for rec in recommendations],
        )
