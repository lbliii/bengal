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
from bengal.cli.helpers import get_cli_output
from bengal.config.directory_loader import ConfigDirectoryLoader, ConfigLoadError
from bengal.config.environment import detect_environment
from bengal.utils.build_stats import show_error
from bengal.utils.cli_output import CLIOutput


@click.group("config", cls=BengalGroup)
def config_cli():
    """
    ⚙️  Configuration management and introspection.

    Commands:
        show     Display merged configuration
        doctor   Validate and lint configuration
        diff     Compare configurations
        init     Initialize config structure
    """
    pass


@config_cli.command()
@click.option(
    "--environment",
    "-e",
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

    Examples:
        bengal config show
        bengal config show --environment production
        bengal config show --profile dev --origin
        bengal config show --section site
    """
    cli = get_cli_output()

    try:
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
            print(output)
        else:
            # YAML output (default)
            import yaml

            output = yaml.dump(config, default_flow_style=False, sort_keys=False)
            print(output)

    except ConfigLoadError as e:
        show_error(f"Config load failed: {e}", show_art=False)
        raise click.Abort() from e
    except Exception as e:
        show_error(f"Error: {e}", show_art=False)
        raise click.Abort() from e


@config_cli.command()
@click.option(
    "--environment",
    "-e",
    help="Environment to validate (default: all)",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def doctor(
    environment: str | None,
    source: str,
) -> None:
    """
    🩺 Validate and lint configuration.

    Checks for:
    - Valid YAML syntax
    - Type errors (bool, int, str)
    - Unknown keys (typo detection)
    - Required fields
    - Value ranges
    - Deprecated keys

    Examples:
        bengal config doctor
        bengal config doctor --environment production
    """
    cli = get_cli_output()

    try:
        root_path = Path(source).resolve()
        config_dir = root_path / "config"

        # Check if config directory exists
        if not config_dir.exists():
            cli.warning(f"Config directory not found: {config_dir}")
            cli.info("Run 'bengal config init' to create config structure")
            raise click.Abort()

        cli.header("🩺 Config Health Check")
        cli.blank()

        errors = []
        warnings = []

        # Check YAML syntax for all files
        _check_yaml_syntax(config_dir, errors, warnings)

        # Load and validate config
        environments = [environment] if environment else ["local", "production"]

        for env in environments:
            cli.info(f"Checking environment: {env}")

            try:
                loader = ConfigDirectoryLoader()
                config = loader.load(config_dir, environment=env)

                # Run validation checks
                _validate_config_types(config, errors, warnings)
                _validate_config_values(config, env, errors, warnings)
                _check_unknown_keys(config, warnings)

            except ConfigLoadError as e:
                errors.append(f"Failed to load {env} config: {e}")

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

    except ConfigLoadError as e:
        show_error(f"Config load failed: {e}", show_art=False)
        raise click.Abort() from e
    except click.Abort:
        raise
    except Exception as e:
        show_error(f"Error: {e}", show_art=False)
        raise click.Abort() from e


def _check_yaml_syntax(config_dir: Path, errors: list, warnings: list) -> None:
    """Check YAML syntax for all config files."""
    import yaml

    yaml_files = list(config_dir.glob("**/*.yaml")) + list(config_dir.glob("**/*.yml"))

    for yaml_file in yaml_files:
        try:
            with yaml_file.open("r", encoding="utf-8") as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML in {yaml_file.relative_to(config_dir)}: {e}")


def _validate_config_types(config: dict, errors: list, warnings: list) -> None:
    """Validate config value types."""
    # Known boolean fields
    boolean_fields = [
        "parallel",
        "incremental",
        "minify_html",
        "generate_rss",
        "generate_sitemap",
        "validate_links",
    ]

    for field in boolean_fields:
        if field in config and not isinstance(config[field], bool):
            errors.append(f"'{field}' must be boolean, got {type(config[field]).__name__}")


def _validate_config_values(config: dict, environment: str, errors: list, warnings: list) -> None:
    """Validate config values and ranges."""
    # Check required fields for production
    if environment == "production" and "site" in config:
        if not config["site"].get("title"):
            warnings.append("'site.title' is recommended for production")
        if not config["site"].get("baseurl"):
            warnings.append("'site.baseurl' is recommended for production")

    # Check value ranges
    if "build" in config:
        max_workers = config["build"].get("max_workers")
        if max_workers is not None:
            if not isinstance(max_workers, int):
                errors.append(
                    f"'build.max_workers' must be integer, got {type(max_workers).__name__}"
                )
            elif max_workers < 0:
                errors.append("'build.max_workers' must be >= 0")
            elif max_workers > 100:
                warnings.append("'build.max_workers' > 100 seems excessive")


def _check_unknown_keys(config: dict, warnings: list) -> None:
    """Check for unknown/typo keys."""
    import difflib

    known_sections = {
        "site",
        "build",
        "features",
        "theme",
        "markdown",
        "assets",
        "pagination",
        "health",
        "dev",
        "output_formats",
    }

    for key in config:
        if key not in known_sections:
            # Check for typos
            suggestions = difflib.get_close_matches(key, known_sections, n=1, cutoff=0.6)
            if suggestions:
                warnings.append(f"Unknown section '{key}'. Did you mean '{suggestions[0]}'?")


@config_cli.command()
@click.option(
    "--against",
    required=True,
    help="Environment or file to compare against",
)
@click.option(
    "--environment",
    "-e",
    help="Environment to compare (default: local)",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def diff(
    against: str,
    environment: str | None,
    source: str,
) -> None:
    """
    🔍 Compare configurations.

    Shows differences between two configurations (environments, profiles, or files).

    Examples:
        bengal config diff --against production
        bengal config diff --environment local --against production
    """
    cli = get_cli_output()

    try:
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

    except ConfigLoadError as e:
        show_error(f"Config load failed: {e}", show_art=False)
        raise click.Abort() from e
    except Exception as e:
        show_error(f"Error: {e}", show_art=False)
        raise click.Abort() from e


def _compute_diff(config1: dict, config2: dict, path: list[str]) -> list[dict[str, Any]]:
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
    ✨ Initialize configuration structure.

    Creates config directory with examples, or a single config file.

    Examples:
        bengal config init
        bengal config init --type file
        bengal config init --template blog
    """
    cli = get_cli_output()

    try:
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

    except Exception as e:
        show_error(f"Error: {e}", show_art=False)
        raise click.Abort() from e


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
