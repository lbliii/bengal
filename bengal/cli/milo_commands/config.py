"""Config group — configuration management and introspection."""

from __future__ import annotations

from typing import Annotated

from milo import Description


def config_show(
    source: Annotated[str, Description("Source directory path")] = "",
    environment: Annotated[str, Description("Environment: local, preview, production")] = "",
    profile: Annotated[str, Description("Profile to load")] = "",
    origin: Annotated[bool, Description("Show which file contributed each config key")] = False,
    section: Annotated[str, Description("Show only specific section (e.g. site, build)")] = "",
    output_format: Annotated[str, Description("Output format: yaml or json")] = "yaml",
) -> dict:
    """Display merged configuration with environment and profile resolution."""
    from pathlib import Path

    from bengal.cli.utils import get_cli_output
    from bengal.config.environment import detect_environment
    from bengal.config.unified_loader import UnifiedConfigLoader

    source = source or "."
    environment_val = environment or None
    profile_val = profile or None
    section_val = section or None

    cli = get_cli_output()
    root_path = Path(source).resolve()
    config_dir = root_path / "config"

    if not config_dir.exists():
        cli.warning(f"Config directory not found: {config_dir}")
        cli.info("Run 'bengal config init' to create config structure")
        raise SystemExit(1)

    loader = UnifiedConfigLoader(track_origins=origin)

    if environment_val is None:
        environment_val = detect_environment()
        cli.info(f"Environment: {environment_val} (auto-detected)")
    else:
        cli.info(f"Environment: {environment_val}")

    if profile_val:
        cli.info(f"Profile: {profile_val}")

    cli.blank()

    config_obj = loader.load(root_path, environment=environment_val, profile=profile_val)
    config = config_obj.raw

    if section_val:
        if section_val in config:
            config = {section_val: config[section_val]}
        else:
            cli.error(f"Section '{section_val}' not found in config")
            cli.info(f"Available sections: {', '.join(sorted(config.keys()))}")
            raise SystemExit(1)

    if origin and loader.get_origin_tracker():
        tracker = loader.get_origin_tracker()
        if tracker:
            output = tracker.show_with_origin()
            cli.info(output)
    elif output_format == "json":
        import json

        cli.render_write("json_output.kida", data=json.dumps(config, indent=2))
    else:
        import yaml

        cli.render_write(
            "json_output.kida",
            data=yaml.dump(config, default_flow_style=False, sort_keys=False),
            language="yaml",
        )

    return {"environment": environment_val, "section": section_val, "keys": list(config.keys())}


def config_doctor(
    source: Annotated[str, Description("Source directory path")] = "",
    environment: Annotated[str, Description("Environment: local, preview, production")] = "",
) -> dict:
    """Validate and lint configuration files."""
    from pathlib import Path

    from bengal.cli.helpers import (
        check_unknown_keys,
        check_yaml_syntax,
        cli_progress,
        validate_config_types,
        validate_config_values,
    )
    from bengal.cli.utils import get_cli_output
    from bengal.config.unified_loader import ConfigLoadError, UnifiedConfigLoader

    source = source or "."
    environment_val = environment or None

    cli = get_cli_output()
    root_path = Path(source).resolve()
    config_dir = root_path / "config"

    if not config_dir.exists():
        cli.warning(f"Config directory not found: {config_dir}")
        cli.info("Run 'bengal config init' to create config structure")
        raise SystemExit(1)

    errors: list[str] = []
    warnings: list[str] = []

    check_yaml_syntax(config_dir, errors, warnings)

    environments = [environment_val] if environment_val else ["local", "production"]

    with cli_progress("Checking environments...", total=len(environments), cli=cli) as update:
        for env in environments:
            try:
                loader = UnifiedConfigLoader()
                config_obj = loader.load(root_path, environment=env)
                config = config_obj.raw if hasattr(config_obj, "raw") else config_obj

                validate_config_types(config, errors, warnings)
                validate_config_values(config, env, errors, warnings)
                check_unknown_keys(config, warnings)
            except ConfigLoadError as e:
                errors.append(f"Failed to load {env} config: {e}")
            update(item=env)

    cli.blank()

    issues = [
        *[{"level": "error", "message": e} for e in errors],
        *[{"level": "warning", "message": w} for w in warnings],
    ]

    if issues:
        cli.render_write(
            "validation_report.kida",
            title="Config Health Check",
            issues=issues,
            summary={"errors": len(errors), "warnings": len(warnings), "passed": 0},
        )
    else:
        cli.render_write(
            "validation_report.kida",
            title="Config Health Check",
            issues=[{"level": "success", "message": "Config is valid — no issues found"}],
            summary={"errors": 0, "warnings": 0, "passed": 1},
        )

    if errors:
        raise SystemExit(1)

    return {"errors": len(errors), "warnings": len(warnings), "passed": len(errors) == 0}


def config_diff(
    against: Annotated[str, Description("Environment to compare against (e.g. production)")],
    source: Annotated[str, Description("Source directory path")] = "",
    environment: Annotated[str, Description("Environment to compare (default: local)")] = "",
) -> dict:
    """Compare configurations between environments."""
    from pathlib import Path
    from typing import Any

    from bengal.cli.utils import get_cli_output
    from bengal.config.unified_loader import UnifiedConfigLoader

    source = source or "."
    cli = get_cli_output()
    root_path = Path(source).resolve()
    config_dir = root_path / "config"

    if not config_dir.exists():
        cli.warning(f"Config directory not found: {config_dir}")
        raise SystemExit(1)

    env1 = environment or "local"
    loader = UnifiedConfigLoader()
    config1_obj = loader.load(root_path, environment=env1)
    config1 = config1_obj.raw if hasattr(config1_obj, "raw") else config1_obj

    config2_obj = loader.load(root_path, environment=against)
    config2 = config2_obj.raw if hasattr(config2_obj, "raw") else config2_obj

    def _compute_diff(
        c1: dict[str, Any], c2: dict[str, Any], path: list[str]
    ) -> list[dict[str, Any]]:
        diffs = []
        for key in sorted(set(c1.keys()) | set(c2.keys())):
            key_path = ".".join([*path, key])
            if key not in c1:
                diffs.append({"type": "added", "path": key_path, "value": str(c2[key])})
            elif key not in c2:
                diffs.append({"type": "removed", "path": key_path, "value": str(c1[key])})
            elif c1[key] != c2[key]:
                if isinstance(c1[key], dict) and isinstance(c2[key], dict):
                    diffs.extend(_compute_diff(c1[key], c2[key], [*path, key]))
                else:
                    diffs.append(
                        {
                            "type": "changed",
                            "path": key_path,
                            "old": str(c1[key]),
                            "new": str(c2[key]),
                        }
                    )
        return diffs

    diffs = _compute_diff(config1, config2, path=[])

    if not diffs:
        cli.success("Configurations are identical")
        return {"env1": env1, "env2": against, "diff_count": 0, "diffs": []}

    cli.render_write(
        "diff_view.kida",
        title=f"Config diff: {env1} → {against}",
        changes=diffs,
        summary=f"{len(diffs)} difference(s) found",
        labels=(env1, against),
    )

    return {"env1": env1, "env2": against, "diff_count": len(diffs), "diffs": diffs}


def config_init(
    source: Annotated[str, Description("Source directory path")] = "",
    init_type: Annotated[
        str, Description("Config structure type: directory or file")
    ] = "directory",
    template: Annotated[str, Description("Config template: docs, blog, minimal")] = "docs",
    force: Annotated[bool, Description("Overwrite existing config files")] = False,
) -> dict:
    """Initialize configuration structure with templates."""
    from pathlib import Path

    from bengal.cli.utils import get_cli_output

    source = source or "."
    cli = get_cli_output()
    root_path = Path(source).resolve()
    config_dir = root_path / "config"

    if config_dir.exists() and not force:
        cli.warning(f"Config directory already exists: {config_dir}")
        cli.info("Use --force to overwrite")
        raise SystemExit(1)

    if init_type == "directory":
        entries = _create_directory_structure(config_dir, template, cli)
    else:
        entries = _create_single_file(root_path, template, cli)

    cli.render_write(
        "scaffold_result.kida",
        title=f"Config initialized ({template})",
        entries=entries,
        steps=[
            "Edit config files to match your site",
            "Run: bengal config doctor",
            "Build: bengal build",
        ],
        summary="Config structure created!",
    )

    return {"config_dir": str(config_dir), "init_type": init_type, "template": template}


def _create_directory_structure(config_dir, template, cli):
    """Create config directory structure. Returns file tree entries."""
    import yaml

    defaults = config_dir / "_default"
    defaults.mkdir(parents=True, exist_ok=True)
    envs = config_dir / "environments"
    envs.mkdir(exist_ok=True)
    profiles = config_dir / "profiles"
    profiles.mkdir(exist_ok=True)

    site_config = {
        "site": {
            "title": "My Bengal Site",
            "description": "Built with Bengal SSG",
            "language": "en",
        }
    }
    build_config = {"build": {"parallel": True, "incremental": True, "minify_html": True}}
    features_config = {
        "features": {"rss": True, "sitemap": True, "search": True, "json": True, "llm_txt": True}
    }

    (defaults / "site.yaml").write_text(
        yaml.dump(site_config, default_flow_style=False, sort_keys=False)
    )
    (defaults / "build.yaml").write_text(
        yaml.dump(build_config, default_flow_style=False, sort_keys=False)
    )
    (defaults / "features.yaml").write_text(
        yaml.dump(features_config, default_flow_style=False, sort_keys=False)
    )

    (envs / "local.yaml").write_text(
        yaml.dump({"build": {"debug": True, "strict_mode": False}}, default_flow_style=False)
    )
    (envs / "production.yaml").write_text(
        yaml.dump(
            {"site": {"baseurl": "https://example.com"}, "build": {"strict_mode": True}},
            default_flow_style=False,
        )
    )

    (profiles / "writer.yaml").write_text(
        yaml.dump(
            {"observability": {"track_memory": False, "verbose": False}}, default_flow_style=False
        )
    )
    (profiles / "dev.yaml").write_text(
        yaml.dump(
            {"observability": {"track_memory": True, "verbose": True}}, default_flow_style=False
        )
    )

    return [
        {"name": "_default/site.yaml", "note": "site metadata"},
        {"name": "_default/build.yaml", "note": "build settings"},
        {"name": "_default/features.yaml", "note": "feature flags"},
        {"name": "environments/local.yaml", "note": "local overrides"},
        {"name": "environments/production.yaml", "note": "production overrides"},
        {"name": "profiles/writer.yaml", "note": "writer profile"},
        {"name": "profiles/dev.yaml", "note": "developer profile"},
    ]


def _create_single_file(root_path, template, cli):
    """Create single bengal.yaml file. Returns file tree entries."""
    import yaml

    config_file = root_path / "bengal.yaml"
    config = {
        "site": {"title": "My Site", "baseurl": "https://example.com"},
        "features": {"rss": True, "sitemap": True, "search": True},
        "build": {"parallel": True, "incremental": True},
    }
    config_file.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))

    return [{"name": "bengal.yaml", "note": "single-file config"}]


def config_inspect(
    source: Annotated[str, Description("Source directory path")] = "",
    compare_to: Annotated[str, Description("Compare to environment/profile")] = "",
    explain_key: Annotated[
        str, Description("Explain how a key got its value (e.g. site.title)")
    ] = "",
    list_sources: Annotated[bool, Description("List available configuration sources")] = False,
    find_issues: Annotated[bool, Description("Find potential configuration issues")] = False,
    output_format: Annotated[str, Description("Output format: console or json")] = "console",
    traceback: Annotated[
        str, Description("Traceback verbosity: full | compact | minimal | off")
    ] = "",
) -> dict:
    """Advanced configuration inspection and comparison."""
    import json

    from bengal.cli.utils import configure_traceback, get_cli_output, load_site_from_cli
    from bengal.debug import ConfigInspector

    source = source or "."
    traceback_val = traceback or None
    compare_to_val = compare_to or None
    explain_key_val = explain_key or None

    cli = get_cli_output()
    configure_traceback(debug=False, traceback=traceback_val)

    cli.header("Config Inspector")

    cli.info("Loading site...")
    site = load_site_from_cli(source=source, config=None, environment=None, profile=None, cli=cli)
    configure_traceback(debug=False, traceback=traceback_val, site=site)

    inspector = ConfigInspector(site=site)

    if list_sources:
        sources = inspector._list_available_sources()
        cli.render_write(
            "item_list.kida",
            title="Available Configuration Sources",
            items=[{"name": s, "description": ""} for s in sources],
        )
        return {"sources": sources}

    if explain_key_val:
        explanation = inspector.explain_key(explain_key_val)
        cli.blank()
        if explanation:
            cli.info(explanation.format())
        else:
            cli.warning(f"Key not found: {explain_key_val}")
        return {"key": explain_key_val, "found": explanation is not None}

    if compare_to_val:
        from bengal.config.environment import detect_environment

        current_env = detect_environment()
        comparison = inspector.compare(current_env, compare_to_val)

        cli.blank()
        if output_format == "json":
            data = {
                "source1": comparison.source1,
                "source2": comparison.source2,
                "diffs": [
                    {
                        "path": d.path,
                        "type": d.type,
                        "old_value": d.old_value,
                        "new_value": d.new_value,
                        "old_origin": d.old_origin,
                        "new_origin": d.new_origin,
                        "impact": d.impact,
                    }
                    for d in comparison.diffs
                ],
            }
            cli.render_write("json_output.kida", data=json.dumps(data, indent=2))
        else:
            cli.info(comparison.format_detailed())
        return {
            "source1": comparison.source1,
            "source2": comparison.source2,
            "diff_count": len(comparison.diffs),
        }

    if find_issues:
        findings = inspector.find_issues()
        if findings:
            issues = []
            for finding in findings:
                level = (
                    finding.severity.value
                    if finding.severity.value in ("error", "warning")
                    else "info"
                )
                detail = finding.suggestion if finding.suggestion else None
                issues.append({"level": level, "message": finding.title, "detail": detail})
            error_count = sum(1 for f in findings if f.severity.value == "error")
            warn_count = sum(1 for f in findings if f.severity.value == "warning")
            cli.render_write(
                "validation_report.kida",
                title="Config Issues",
                issues=issues,
                summary={"errors": error_count, "warnings": warn_count, "passed": 0},
            )
        else:
            cli.render_write(
                "validation_report.kida",
                issues=[{"level": "success", "message": "No issues found"}],
                summary={"errors": 0, "warnings": 0, "passed": 1},
            )
        return {"issues": [{"title": f.title, "severity": f.severity.value} for f in findings]}

    cli.info("Use --list-sources, --explain-key, --compare-to, or --find-issues")
    return {}
