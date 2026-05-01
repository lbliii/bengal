"""Plugin group — discovery and capability readiness."""

from __future__ import annotations

from typing import Annotated, Any

from milo import Description


def _status_label(status: str) -> str:
    match status:
        case "ready":
            return "ready"
        case "partial":
            return "partial"
        case "invalid" | "load_error" | "register_error":
            return "error"
        case _:
            return status


def _load_reports() -> list[Any]:
    from bengal.plugins.inspection import inspect_installed_plugins

    return inspect_installed_plugins()


def plugin_list() -> dict:
    """List installed Bengal plugins and readiness status."""
    from bengal.cli.utils import get_cli_output

    cli = get_cli_output()
    reports = _load_reports()

    if not reports:
        cli.info("No Bengal plugins discovered")
        return {"plugins": [], "count": 0}

    cli.render_write(
        "item_list.kida",
        title="Bengal Plugins",
        items=[
            {
                "name": report.plugin_name or report.entry_point,
                "description": (
                    f"{report.version or 'unknown'}  "
                    f"{_status_label(report.status)}  "
                    f"{report.entry_point}"
                ),
            }
            for report in reports
        ],
    )

    return {
        "plugins": [report.to_dict() for report in reports],
        "count": len(reports),
    }


def plugin_info(
    name: Annotated[str, Description("Plugin name or entry point name")],
) -> dict:
    """Show detailed plugin capability readiness."""
    from bengal.cli.utils import get_cli_output
    from bengal.plugins.inspection import capability_details

    cli = get_cli_output()
    reports = _load_reports()
    report = next(
        (item for item in reports if item.entry_point == name or item.plugin_name == name),
        None,
    )

    if report is None:
        cli.error(f"Plugin not found: {name}")
        cli.tip("Run `bengal plugin list` to see installed plugin entry points.")
        raise SystemExit(1)

    items = [
        {"label": "Entry point", "value": report.entry_point},
        {"label": "Object", "value": report.value},
        {"label": "Name", "value": report.plugin_name or ""},
        {"label": "Version", "value": report.version or "unknown"},
        {"label": "Status", "value": _status_label(report.status)},
    ]
    if report.errors:
        items.append({"label": "Errors", "value": "; ".join(report.errors)})
    pending = report.pending_capabilities
    if pending:
        items.append({"label": "Pending capabilities", "value": ", ".join(pending)})

    cli.render_write("kv_detail.kida", title=f"Plugin: {name}", items=items)

    return {
        "plugin": report.to_dict(),
        "capabilities": capability_details(report.capabilities),
    }


def plugin_validate() -> dict:
    """Validate installed plugins against currently wired Bengal capabilities."""
    from bengal.cli.utils import get_cli_output
    from bengal.plugins.inspection import capability_details

    cli = get_cli_output()
    reports = _load_reports()
    issues: list[dict[str, str]] = []

    for report in reports:
        label = report.plugin_name or report.entry_point
        issues.extend({"level": "error", "message": f"{label}: {error}"} for error in report.errors)
        issues.extend(
            {
                "level": "warning",
                "message": (
                    f"{label}: {detail['count']} {detail['name']} registered, "
                    f"but integration is {detail['integration_status']}"
                ),
            }
            for detail in capability_details(report.capabilities)
            if detail["count"] and not detail["ready"]
        )

    if not reports:
        cli.info("No Bengal plugins discovered")
        return {"valid": True, "plugins": [], "issues": []}

    passed = len(reports) if not issues else 0
    summary = {
        "errors": sum(1 for issue in issues if issue["level"] == "error"),
        "warnings": sum(1 for issue in issues if issue["level"] == "warning"),
        "passed": passed,
    }

    cli.render_write(
        "validation_report.kida",
        title="Plugin Validation",
        issues=issues
        or [{"level": "success", "message": "All installed plugins use wired capabilities"}],
        summary=summary,
    )

    result = {
        "valid": not issues,
        "plugins": [report.to_dict() for report in reports],
        "issues": issues,
        "summary": summary,
    }
    if issues:
        raise SystemExit(1)
    return result
