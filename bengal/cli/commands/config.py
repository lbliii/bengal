"""
Config management commands.

Provides introspection and management commands for Bengal configuration:
- show: Display merged config
- doctor: Validate and lint config
- diff: Compare configurations
- init: Scaffold config structure
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from bengal.cli.base import BengalGroup
from bengal.cli.helpers import (
    check_unknown_keys,
    check_yaml_syntax,
    cli_progress,
    command_metadata,
    get_cli_output,
    handle_cli_errors,
    validate_config_types,
    validate_config_values,
)
from bengal.config.directory_loader import ConfigDirectoryLoader, ConfigLoadError
from bengal.config.environment import detect_environment
from bengal.output import CLIOutput


@click.group("config", cls=BengalGroup)
def config_cli() -> None:
    """
    Configuration management and introspection.

    Commands:
        show     Display merged configuration
        doctor   Validate and lint configuration
        diff     Compare configurations
        init     Initialize config structure
    """
    pass


@config_cli.command()
@command_metadata(
    category="config",
    description="Display merged configuration with environment and profile resolution",
    examples=[
        "bengal config show",
        "bengal config show --environment production",
        "bengal config show --section build",
        "bengal config show --origin",
    ],
    requires_site=False,
    tags=["config", "debug", "quick"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--environment",
    "-e",
    type=click.Choice(["local", "preview", "production"], case_sensitive=False),
    help="Environment to load (auto-detected if not specified)",
)
@click.option(
    "--profile",
    "-p",
    help="Profile to load (optional)",
)
@click.option(
    "--origin",
    is_flag=True,
    help="Show which file contributed each config key",
)
@click.option(
    "--section",
    "-s",
    help="Show only specific section (e.g., 'site', 'build')",
)
@click.option(
    "--format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="Output format",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def show(
    environment: str | None,
    profile: str | None,
    origin: bool,
    section: str | None,
    format: str,
    source: str,
) -> None:
    """
    📋 Display merged configuration.

    Shows the effective configuration after merging defaults, environment,
    and profile settings.

    Use --origin to see which file contributed each config key, useful
    for debugging configuration issues.

    Examples:
        bengal config show
        bengal config show --environment production
        bengal config show --profile dev --origin
        bengal config show --section site

    See also:
        bengal config doctor - Validate configuration
        bengal config diff - Compare configurations
    """
    cli = get_cli_output()

    root_path = Path(source).resolve()
    config_dir = root_path / "config"

    # Check if config directory exists
    if not config_dir.exists():
        cli.warning(f"Config directory not found: {config_dir}")
        cli.info("Run 'bengal config init' to create config structure")
        raise click.Abort()

    # Load config with origin tracking if requested
    loader = ConfigDirectoryLoader(track_origins=origin)

    # Auto-detect environment if not specified
    if environment is None:
        environment = detect_environment()
        cli.info(f"Environment: {environment} (auto-detected)")
    else:
        cli.info(f"Environment: {environment}")

    if profile:
        cli.info(f"Profile: {profile}")

    cli.blank()

    # Load config
    config = loader.load(config_dir, environment=environment, profile=profile)

    # Filter to section if requested
    if section:
        if section in config:
            config = {section: config[section]}
        else:
            cli.error(f"Section '{section}' not found in config")
            cli.info(f"Available sections: {', '.join(sorted(config.keys()))}")
            raise click.Abort()

    # Display config
    if origin and loader.get_origin_tracker():
        # Show with origin annotations
        tracker = loader.get_origin_tracker()
        if tracker:
            output = tracker.show_with_origin()
            cli.info(output)
    elif format == "json":
        # JSON output
        import json

        output = json.dumps(config, indent=2)
        cli.console.print(output)
    else:
        # YAML output (default)
        import yaml

        output = yaml.dump(config, default_flow_style=False, sort_keys=False)
        cli.console.print(output)


@config_cli.command()
@command_metadata(
    category="config",
    description="Validate and lint configuration files",
    examples=[
        "bengal config doctor",
        "bengal config doctor --environment production",
    ],
    requires_site=False,
    tags=["config", "validation", "ci"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--environment",
    "-e",
    type=click.Choice(["local", "preview", "production"], case_sensitive=False),
    help="Environment to validate (default: all)",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def doctor(
    environment: str | None,
    source: str,
) -> None:
    """
    Validate and lint configuration.

    Checks for:
    - Valid YAML syntax
    - Type errors (bool, int, str)
    - Unknown keys (typo detection)
    - Required fields
    - Value ranges
    - Deprecated keys

    Run this before deploying to catch configuration errors early.
    Exits with non-zero code if errors are found (useful for CI/CD).

    Examples:
        bengal config doctor
        bengal config doctor --environment production

    See also:
        bengal config show - View merged configuration
        bengal config diff - Compare configurations
    """
    cli = get_cli_output()

    root_path = Path(source).resolve()
    config_dir = root_path / "config"

    # Check if config directory exists
    if not config_dir.exists():
        cli.warning(f"Config directory not found: {config_dir}")
        cli.info("Run 'bengal config init' to create config structure")
        raise click.Abort()

    cli.header("🩺 Config Health Check")
    cli.blank()

    errors: list[str] = []
    warnings: list[str] = []

    # Check YAML syntax for all files
    check_yaml_syntax(config_dir, errors, warnings)

    # Load and validate config
    environments = [environment] if environment else ["local", "production"]

    with cli_progress("Checking environments...", total=len(environments), cli=cli) as update:
        for env in environments:
            try:
                loader = ConfigDirectoryLoader()
                config = loader.load(config_dir, environment=env)

                # Run validation checks
                validate_config_types(config, errors, warnings)
                validate_config_values(config, env, errors, warnings)
                check_unknown_keys(config, warnings)

            except ConfigLoadError as e:
                errors.append(f"Failed to load {env} config: {e}")

            update(item=env)

    # Display results
    cli.blank()

    if errors:
        cli.info("❌ Errors:")
        for i, error in enumerate(errors, 1):
            cli.error(f"  {i}. {error}")
        cli.blank()

    if warnings:
        cli.info("⚠️  Warnings:")
        for i, warning in enumerate(warnings, 1):
            cli.warning(f"  {i}. {warning}")
        cli.blank()

    # Summary
    if not errors and not warnings:
        cli.success("✅ Config is valid!")
    else:
        cli.info(f"📊 Summary: {len(errors)} errors, {len(warnings)} warnings")

        if errors:
            raise click.Abort()


@config_cli.command()
@handle_cli_errors(show_art=False)
@click.option(
    "--against",
    required=True,
    type=click.Choice(["local", "preview", "production"], case_sensitive=False),
    help="Environment to compare against",
)
@click.option(
    "--environment",
    "-e",
    type=click.Choice(["local", "preview", "production"], case_sensitive=False),
    help="Environment to compare (default: local)",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def diff(
    against: str,
    environment: str | None,
    source: str,
) -> None:
    """
    Compare configurations.

    Shows differences between two configurations (environments, profiles, or files).
    Useful for verifying that production settings differ correctly from local/preview.

    Examples:
        bengal config diff --against production
        bengal config diff --environment local --against production

    See also:
        bengal config show - View merged configuration
        bengal config doctor - Validate configuration
    """
    cli = get_cli_output()

    root_path = Path(source).resolve()
    config_dir = root_path / "config"

    if not config_dir.exists():
        cli.warning(f"Config directory not found: {config_dir}")
        raise click.Abort()

    # Load first config
    env1 = environment or "local"
    loader = ConfigDirectoryLoader()
    config1 = loader.load(config_dir, environment=env1)

    # Load second config
    config2 = loader.load(config_dir, environment=against)

    cli.header(f"🔍 Comparing: {env1} → {against}")
    cli.blank()

    # Compute diff
    diffs = _compute_diff(config1, config2, path=[])

    if not diffs:
        cli.success("✅ Configurations are identical")
        return

    # Display diffs
    for diff in diffs:
        if diff["type"] == "changed":
            cli.info(f"{diff['path']}:")
            cli.error(f"  - {diff['old']}  [{env1}]")
            cli.success(f"  + {diff['new']}  [{against}]")
        elif diff["type"] == "added":
            cli.info(f"{diff['path']}:")
            cli.success(f"  + {diff['value']}  [{against}]")
        elif diff["type"] == "removed":
            cli.info(f"{diff['path']}:")
            cli.error(f"  - {diff['value']}  [{env1}]")

    cli.blank()
    cli.info(f"Found {len(diffs)} differences")


def _compute_diff(
    config1: dict[str, Any], config2: dict[str, Any], path: list[str]
) -> list[dict[str, Any]]:
    """Recursively compute diff between two configs."""
    diffs = []

    all_keys = set(config1.keys()) | set(config2.keys())

    for key in sorted(all_keys):
        key_path = ".".join(path + [key])

        if key not in config1:
            # Added in config2
            diffs.append({"type": "added", "path": key_path, "value": config2[key]})
        elif key not in config2:
            # Removed from config2
            diffs.append({"type": "removed", "path": key_path, "value": config1[key]})
        elif config1[key] != config2[key]:
            # Changed
            if isinstance(config1[key], dict) and isinstance(config2[key], dict):
                # Recurse into nested dicts
                diffs.extend(_compute_diff(config1[key], config2[key], path + [key]))
            else:
                diffs.append(
                    {
                        "type": "changed",
                        "path": key_path,
                        "old": config1[key],
                        "new": config2[key],
                    }
                )

    return diffs


@config_cli.command()
@command_metadata(
    category="config",
    description="Initialize configuration structure with templates",
    examples=[
        "bengal config init",
        "bengal config init --type file",
        "bengal config init --template blog",
    ],
    requires_site=False,
    tags=["config", "setup", "quick"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--type",
    "init_type",
    type=click.Choice(["directory", "file"]),
    default="directory",
    help="Config structure type (default: directory)",
)
@click.option(
    "--template",
    type=click.Choice(["docs", "blog", "minimal"]),
    default="docs",
    help="Config template (default: docs)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing config files",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def init(
    init_type: str,
    template: str,
    force: bool,
    source: str,
) -> None:
    """
    Initialize configuration structure.

    Creates config directory with examples, or a single config file.
    Use --template to choose a preset (docs, blog, minimal).

    Examples:
        bengal config init
        bengal config init --type file
        bengal config init --template blog

    See also:
        bengal config show - View configuration
        bengal config doctor - Validate configuration
    """
    cli = get_cli_output()

    root_path = Path(source).resolve()
    config_dir = root_path / "config"

    if config_dir.exists() and not force:
        cli.warning(f"Config directory already exists: {config_dir}")
        cli.info("Use --force to overwrite")
        raise click.Abort()

    if init_type == "directory":
        _create_directory_structure(config_dir, template, cli)
    else:
        _create_single_file(root_path, template, cli)

    cli.blank()
    cli.success("✨ Config structure created!")
    cli.blank()

    cli.info("💡 Next steps:")
    cli.info("  1. Edit config files to match your site")
    cli.info("  2. Run: bengal config doctor")
    cli.info("  3. Build: bengal build")


def _create_directory_structure(config_dir: Path, template: str, cli: CLIOutput) -> None:
    """Create config directory structure."""
    import yaml

    # Create directories
    defaults = config_dir / "_default"
    defaults.mkdir(parents=True, exist_ok=True)

    envs = config_dir / "environments"
    envs.mkdir(exist_ok=True)

    profiles = config_dir / "profiles"
    profiles.mkdir(exist_ok=True)

    # Create default configs
    site_config = {
        "site": {
            "title": "My Bengal Site",
            "description": "Built with Bengal SSG",
            "language": "en",
        }
    }

    build_config = {
        "build": {
            "parallel": True,
            "incremental": True,
            "minify_html": True,
        }
    }

    features_config = {
        "features": {"rss": True, "sitemap": True, "search": True, "json": True, "llm_txt": True}
    }

    # Write default configs
    (defaults / "site.yaml").write_text(
        yaml.dump(site_config, default_flow_style=False, sort_keys=False)
    )
    (defaults / "build.yaml").write_text(
        yaml.dump(build_config, default_flow_style=False, sort_keys=False)
    )
    (defaults / "features.yaml").write_text(
        yaml.dump(features_config, default_flow_style=False, sort_keys=False)
    )

    # Create environment configs
    (envs / "local.yaml").write_text(
        yaml.dump({"build": {"debug": True, "strict_mode": False}}, default_flow_style=False)
    )
    (envs / "production.yaml").write_text(
        yaml.dump(
            {"site": {"baseurl": "https://example.com"}, "build": {"strict_mode": True}},
            default_flow_style=False,
        )
    )

    # Create profile configs
    (profiles / "writer.yaml").write_text(
        yaml.dump(
            {
                "observability": {
                    "track_memory": False,
                    "verbose": False,
                }
            },
            default_flow_style=False,
        )
    )
    (profiles / "dev.yaml").write_text(
        yaml.dump(
            {
                "observability": {
                    "track_memory": True,
                    "verbose": True,
                }
            },
            default_flow_style=False,
        )
    )

    cli.success("✨ Created config structure:")
    cli.info(f"   {config_dir}/_default/site.yaml")
    cli.info(f"   {config_dir}/_default/build.yaml")
    cli.info(f"   {config_dir}/_default/features.yaml")
    cli.info(f"   {config_dir}/environments/local.yaml")
    cli.info(f"   {config_dir}/environments/production.yaml")
    cli.info(f"   {config_dir}/profiles/writer.yaml")
    cli.info(f"   {config_dir}/profiles/dev.yaml")


def _create_single_file(root_path: Path, template: str, cli: CLIOutput) -> None:
    """Create single bengal.yaml file."""
    import yaml

    config_file = root_path / "bengal.yaml"

    config = {
        "site": {
            "title": "My Site",
            "baseurl": "https://example.com",
        },
        "features": {
            "rss": True,
            "sitemap": True,
            "search": True,
        },
        "build": {
            "parallel": True,
            "incremental": True,
        },
    }

    config_file.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))

    cli.success(f"✨ Created {config_file}")
