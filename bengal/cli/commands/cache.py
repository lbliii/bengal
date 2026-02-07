"""
Cache management commands for Bengal.

Provides CLI commands for managing build cache and generating cache keys
for CI systems. Enables correct CI cache invalidation by listing all
input paths that affect the build.

Commands:
    inputs: List all input globs that affect the build
    hash: Compute deterministic hash of all build inputs

Example:
    >>> # List input patterns for CI cache key
    >>> bengal cache inputs
content/**
config/**
../bengal/**/*.py

    >>> # Get hash for CI cache key
    >>> bengal cache hash
a1b2c3d4e5f6g7h8

Related:
- plan/rfc-ci-cache-inputs.md: Design rationale
- bengal/utils/hashing.py: Shared hashing utilities

"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

import click

import bengal
from bengal.cli.base import BengalCommand, BengalGroup
from bengal.cli.helpers import (
    command_metadata,
    get_cli_output,
    handle_cli_errors,
    load_site_from_cli,
)

if TYPE_CHECKING:
    from bengal.protocols import SiteLike


def get_input_globs(site: SiteLike) -> list[tuple[str, str]]:
    """
    Return list of (glob_pattern, source_description) tuples.

    Patterns are relative to site_root or use ../ for external paths.
    These represent all inputs that can affect the build output.

    Args:
        site: Loaded Site instance

    Returns:
        List of tuples: (glob_pattern, source_description)

    Example:
            >>> globs = get_input_globs(site)
            >>> for pattern, source in globs:
            ...     print(f"{pattern} <- {source}")
        content/** <- built-in
        config/** <- built-in
        ../bengal/**/*.py <- autodoc.python.source_dirs

    """
    inputs: list[tuple[str, str]] = []
    site_root = site.root_path

    # Always include content and config
    inputs.append(("content/**", "built-in"))
    inputs.append(("config/**", "built-in"))

    # Templates (if custom templates directory exists)
    templates_dir = site_root / "templates"
    if templates_dir.exists():
        inputs.append(("templates/**", "custom templates"))

    # Static assets
    static_dir = site_root / "static"
    if static_dir.exists():
        inputs.append(("static/**", "static assets"))

    # Assets directory
    assets_dir = site_root / "assets"
    if assets_dir.exists():
        inputs.append(("assets/**", "assets"))

    # Get config as dict for accessing nested config
    config = site.config

    # Autodoc Python sources
    autodoc_config = config.get("autodoc", {})
    python_config = autodoc_config.get("python", {})
    if python_config.get("enabled", False):
        source_dirs = python_config.get("source_dirs", [])
        inputs.extend(
            (f"{source_dir}/**/*.py", "autodoc.python.source_dirs")
            for source_dir in source_dirs
        )

    # Autodoc CLI (derive package from app_module)
    cli_config = autodoc_config.get("cli", {})
    if cli_config.get("enabled", False):
        app_module = cli_config.get("app_module")
        if app_module:
            # Extract package name from "package.module:func" format
            # e.g., "bengal.cli:main" -> "bengal"
            package = app_module.split(":")[0].split(".")[0]
            inputs.append((f"../{package}/**/*.py", "autodoc.cli.app_module"))

    # Autodoc OpenAPI
    openapi_config = autodoc_config.get("openapi", {})
    if openapi_config.get("enabled", False):
        spec_file = openapi_config.get("spec_file")
        if spec_file:
            inputs.append((spec_file, "autodoc.openapi.spec_file"))

    # External refs (local index paths only)
    external_refs = config.get("external_refs", {})
    if external_refs.get("enabled", True):  # Enabled by default
        indexes = external_refs.get("indexes", [])
        for idx in indexes:
            url = idx.get("url", "") if isinstance(idx, dict) else ""
            # Only include local paths, not remote URLs
            if url and not url.startswith(("http://", "https://")):
                inputs.append((url, "external_refs.indexes"))

    # Theme (if external path specified)
    theme_config = config.get("theme", {})
    theme_path = theme_config.get("path") if isinstance(theme_config, dict) else None
    if theme_path:
        inputs.append((f"{theme_path}/**", "theme.path"))

    # Local themes directory
    themes_dir = site_root / "themes"
    if themes_dir.exists():
        inputs.append(("themes/**", "local themes"))

    return inputs


@click.group("cache", cls=BengalGroup)
def cache_cli() -> None:
    """
    Cache management commands.

    Commands for managing Bengal's build cache and generating cache keys
    for CI systems. Use `bengal cache inputs` to list all paths that affect
    the build, or `bengal cache hash` to get a deterministic hash for CI
    cache keys.

    Examples:
        bengal cache inputs              # List input patterns
        bengal cache inputs --verbose    # Show pattern sources
        bengal cache hash                # Get cache key hash

    """


@cache_cli.command("inputs", cls=BengalCommand)
@command_metadata(
    category="cache",
    description="List all input paths/globs that affect the build",
    examples=[
        "bengal cache inputs",
        "bengal cache inputs --verbose",
        "bengal cache inputs --format json",
    ],
    requires_site=True,
    tags=["cache", "ci", "build"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["lines", "json"]),
    default="lines",
    help="Output format (default: lines)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show source of each input pattern",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    help="Path to config file (default: bengal.toml)",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def inputs(output_format: str, verbose: bool, config: str | None, source: str) -> None:
    """
    List all input paths/globs that affect the build.

    Use this to construct CI cache keys that properly invalidate
    when any build input changes. The output includes:

    - Content and config directories (always)
    - Custom templates and static assets (if present)
    - Autodoc source directories (if enabled)
    - External reference indexes (local paths only)
    - Theme paths (if external theme configured)

    Examples:
        bengal cache inputs                  # One pattern per line
        bengal cache inputs --verbose        # Show where each pattern comes from
        bengal cache inputs --format json    # JSON output for scripting

    For CI (GitHub Actions):
        inputs=$(bengal cache inputs | tr '\n' ' ')
        key: bengal-${{ hashFiles(inputs) }}

    """
    cli = get_cli_output()

    # Load site
    site = load_site_from_cli(source=source, config=config, environment=None, profile=None, cli=cli)

    # Get input globs
    input_globs = get_input_globs(site)

    if output_format == "json":
        if verbose:
            data = [{"pattern": p, "source": s} for p, s in input_globs]
            click.echo(json.dumps(data, indent=2))
        else:
            data = [p for p, _ in input_globs]
            click.echo(json.dumps(data, indent=2))
    else:
        for pattern, source_desc in input_globs:
            if verbose:
                click.echo(f"{pattern:<30} # {source_desc}")
            else:
                click.echo(pattern)


@cache_cli.command("hash", cls=BengalCommand)
@command_metadata(
    category="cache",
    description="Compute deterministic hash of all build inputs",
    examples=[
        "bengal cache hash",
        "bengal cache hash --no-include-version",
    ],
    requires_site=True,
    tags=["cache", "ci", "build"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--include-version/--no-include-version",
    default=True,
    help="Include Bengal version in hash (recommended, default: true)",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    help="Path to config file (default: bengal.toml)",
)
@click.argument("source", type=click.Path(exists=True), default=".")
def cache_hash(include_version: bool, config: str | None, source: str) -> None:
    """
    Compute deterministic hash of all build inputs.

    Use this as a CI cache key for accurate invalidation.
    The hash includes:

    - All input file contents (from `bengal cache inputs`)
    - Relative file paths (for determinism across machines)
    - Bengal version (by default, for cache invalidation on upgrades)

    Examples:
        bengal cache hash                     # Include version (recommended)
        bengal cache hash --no-include-version  # Exclude version

    For CI (GitHub Actions):
        hash=$(bengal cache hash)
        key: bengal-${{ runner.os }}-$hash

    """
    cli = get_cli_output()

    # Load site
    site = load_site_from_cli(source=source, config=config, environment=None, profile=None, cli=cli)

    # Get input globs
    input_globs = get_input_globs(site)

    hasher = hashlib.sha256()

    # Include Bengal version for cache invalidation on upgrades
    if include_version:
        hasher.update(f"bengal:{bengal.__version__}".encode())

    # Resolve and hash all matching files
    for glob_pattern, _source in input_globs:
        # Validate pattern - reject deeply nested parent paths
        if glob_pattern.count("../") > 1:
            click.echo(
                f"Warning: Skipping unsupported pattern '{glob_pattern}' (nested ../ not supported)",
                err=True,
            )
            continue

        # Handle ../ patterns by resolving from site root
        if glob_pattern.startswith("../"):
            base_path = site.root_path.parent
            resolved_pattern = glob_pattern[3:]  # Strip ../
        else:
            base_path = site.root_path
            resolved_pattern = glob_pattern

        # Glob for matching files
        try:
            matched_files = sorted(base_path.glob(resolved_pattern))
        except Exception as e:
            click.echo(f"Warning: Error matching pattern '{glob_pattern}': {e}", err=True)
            continue

        for file_path in matched_files:
            if not file_path.is_file():
                continue

            # Resolve symlinks for consistent hashing
            try:
                file_path = file_path.resolve()
            except OSError:
                continue

            # Hash relative path for determinism across machines
            try:
                rel_path = file_path.relative_to(site.root_path.resolve())
            except ValueError:
                # File is outside site root (e.g., ../bengal/)
                try:
                    rel_path = file_path.relative_to(site.root_path.parent.resolve())
                except ValueError:
                    # Fallback: use filename only (rare edge case)
                    rel_path = Path(file_path.name)

            try:
                hasher.update(rel_path.as_posix().encode())
                hasher.update(file_path.read_bytes())
            except OSError as e:
                raise click.ClickException(f"Cannot read file '{file_path}': {e}") from e

    # Output truncated hash (16 chars is sufficient for cache keys)
    click.echo(hasher.hexdigest()[:16])
