"""Runtime capability group — registry inspection (#588)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from milo import Description


def _load_reports(
    *, config: dict[str, Any] | None = None, site_root: Path | None = None
) -> list[Any]:
    from bengal.capabilities.inspection import inspect_capabilities

    return inspect_capabilities(config=config, site_root=site_root)


def _resolve_site_context() -> tuple[dict[str, Any] | None, Path | None]:
    from bengal.cli.utils.site import load_site_from_cli
    from bengal.output import get_cli_output

    if not Path("bengal.toml").is_file() and not Path("config").is_dir():
        return None, None
    try:
        site = load_site_from_cli(source=".", cli=get_cli_output())
    except SystemExit:
        return None, None
    config = getattr(site, "config", {}) or {}
    site_root = Path(getattr(site, "root_path", Path(".")))
    return config, site_root


def capability_list() -> dict:
    """List registered runtime capabilities."""
    from bengal.output import get_cli_output

    cli = get_cli_output()
    config, site_root = _resolve_site_context()
    reports = _load_reports(config=config, site_root=site_root)

    if not reports:
        cli.render_write(
            "command_empty.kida",
            title="Bengal Capabilities",
            message="No runtime capabilities discovered.",
            steps=[
                "Built-in capabilities register via bengal.capabilities entry points.",
                "Run `bengal capability info <name>` for spec details.",
            ],
        )
        return {"capabilities": [], "count": 0}

    cli.render_write(
        "command_list.kida",
        title="Bengal Capabilities",
        items=[
            {
                "name": report.name,
                "status": report.origin,
                "description": _list_description(report),
            }
            for report in reports
        ],
    )

    return {
        "capabilities": [report.to_dict() for report in reports],
        "count": len(reports),
    }


def _list_description(report: Any) -> str:
    parts = [report.origin]
    if report.version:
        parts.append(report.version)
    if report.enabled_in_config is True:
        parts.append("enabled")
    elif report.enabled_in_config is False:
        parts.append("disabled")
    if report.vendors_present is False:
        parts.append("vendors missing")
    return "  ".join(parts)


def capability_info(
    name: Annotated[str, Description("Capability name or entry point name")],
) -> dict:
    """Show detailed runtime capability spec."""
    from bengal.output import get_cli_output

    cli = get_cli_output()
    config, site_root = _resolve_site_context()
    reports = _load_reports(config=config, site_root=site_root)
    report = next((item for item in reports if item.name == name), None)

    if report is None:
        cli.error(f"Capability not found: {name}")
        cli.tip("Run `bengal capability list` to see registered capabilities.")
        raise SystemExit(1)

    spec = report.spec
    items = [
        {"label": "Name", "value": report.name},
        {"label": "Origin", "value": report.origin},
        {"label": "Entry point", "value": report.entry_point or "(built-in)"},
        {"label": "Distribution", "value": report.distribution or "unknown"},
        {"label": "Version", "value": report.version or "unknown"},
        {"label": "Default pin", "value": spec.default_pin if spec else ""},
        {"label": "Assets", "value": ", ".join(spec.vendor_files) if spec else ""},
        {"label": "Fence languages", "value": ", ".join(spec.fence_languages) if spec else ""},
        {
            "label": "Depends on",
            "value": ", ".join(spec.depends_on) if spec and spec.depends_on else "—",
        },
        {"label": "Implies", "value": ", ".join(spec.implies) if spec and spec.implies else "—"},
    ]
    if report.enabled_in_config is not None:
        items.append(
            {"label": "Enabled in config", "value": "yes" if report.enabled_in_config else "no"}
        )
    if report.vendors_present is not None:
        items.append(
            {
                "label": "Vendor files present",
                "value": "yes" if report.vendors_present else "no",
            }
        )
    if spec and spec.init:
        init = spec.init
        items.extend(
            [
                {"label": "Init load position", "value": init.load_position},
                {"label": "Lazy selector", "value": init.lazy_selector or "—"},
                {"label": "Companion scripts", "value": ", ".join(init.companion_scripts) or "—"},
            ]
        )

    cli.render_write("kv_detail.kida", title=f"Capability: {name}", items=items)
    return {"capability": report.to_dict()}


def capability_validate() -> dict:
    """Validate site capability configuration against the registry."""
    from bengal.capabilities.inspection import validate_capability_config
    from bengal.output import get_cli_output

    cli = get_cli_output()
    config, site_root = _resolve_site_context()
    if config is None:
        cli.error("Could not load site configuration.")
        cli.tip("Run from a Bengal site directory or pass --source to a site with bengal.toml.")
        raise SystemExit(1)

    issues = validate_capability_config(config, site_root=site_root)
    reports = _load_reports(config=config, site_root=site_root)

    if not reports:
        cli.render_write(
            "command_empty.kida",
            title="Capability Validation",
            message="No runtime capabilities discovered.",
            steps=["Install a capability package, then run `bengal capability validate` again."],
        )
        return {"valid": True, "capabilities": [], "issues": []}

    passed = len(reports) if not issues else 0
    summary = {
        "errors": sum(1 for issue in issues if issue["level"] == "error"),
        "warnings": sum(1 for issue in issues if issue["level"] == "warning"),
        "passed": passed,
    }

    cli.render_write(
        "validation_report.kida",
        title="Capability Validation",
        issues=issues or [{"level": "success", "message": "Capability configuration looks good"}],
        summary=summary,
    )

    result = {
        "valid": not issues,
        "capabilities": [report.to_dict() for report in reports],
        "issues": issues,
        "summary": summary,
    }
    if issues:
        raise SystemExit(1)
    return result
