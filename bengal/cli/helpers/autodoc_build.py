"""Autodoc regeneration helpers for build command."""

from __future__ import annotations

import os
from pathlib import Path


def should_regenerate_autodoc(
    autodoc_flag: bool | None, config_path: Path | None, root_path: Path, quiet: bool
) -> bool:
    """
    Determine if autodoc should be regenerated based on:
    1. CLI flag (highest priority)
    2. Config setting
    3. Timestamp checking (if neither flag nor config explicitly disable)
    """
    # CLI flag takes precedence
    if autodoc_flag is not None:
        return autodoc_flag

    # If no explicit flag, delegate to checker (tests patch this; config gate handled by caller)
    from bengal.autodoc.config import load_autodoc_config

    # load_autodoc_config can find config automatically if config_path is None
    # It will look for config/ directory or bengal.toml relative to current working directory
    # Since build command runs from site root, this should work
    original_cwd = os.getcwd()
    try:
        # Change to root_path so load_autodoc_config can find config relative to site root
        os.chdir(root_path)
        config = load_autodoc_config(config_path)
    finally:
        os.chdir(original_cwd)

    return check_autodoc_needs_regeneration(config, root_path, quiet)


def check_autodoc_needs_regeneration(autodoc_config: dict, root_path: Path, quiet: bool) -> bool:
    """
    Check if source files are newer than generated docs.
    Returns True if regeneration is needed.
    """
    python_config = autodoc_config.get("python", {})
    cli_config = autodoc_config.get("cli", {})

    needs_regen = False

    # Check Python docs
    if python_config.get("enabled", True):
        source_dirs = python_config.get("source_dirs", ["."])
        output_dir = root_path / python_config.get("output_dir", "content/api")

        if output_dir.exists():
            # Get newest source file
            newest_source = 0
            for source_dir in source_dirs:
                source_path = root_path / source_dir
                if source_path.exists():
                    for py_file in source_path.rglob("*.py"):
                        if "__pycache__" not in str(py_file):
                            mtime = os.path.getmtime(py_file)
                            newest_source = max(newest_source, mtime)

            # Get oldest generated file
            oldest_output = float("inf")
            for md_file in output_dir.rglob("*.md"):
                mtime = os.path.getmtime(md_file)
                oldest_output = min(oldest_output, mtime)

            if newest_source > oldest_output:
                if not quiet:
                    from bengal.cli.helpers.cli_output import get_cli_output

                    cli = get_cli_output(quiet=quiet)
                    cli.warning("📝 Python source files changed, regenerating API docs...")
                needs_regen = True
        else:
            # Output doesn't exist: do not force regeneration from this heuristic alone
            # (callers may still choose to regenerate).
            needs_regen = False

    # Check CLI docs
    if cli_config.get("enabled", False) and cli_config.get("app_module"):
        output_dir = root_path / cli_config.get("output_dir", "content/cli")

        if not output_dir.exists() or not list(output_dir.rglob("*.md")):
            if not quiet:
                from bengal.cli.helpers.cli_output import get_cli_output

                cli = get_cli_output(quiet=quiet)
                cli.warning("📝 CLI docs not found, generating...")
            needs_regen = True

    return needs_regen


def run_autodoc_before_build(config_path: Path | None, root_path: Path, quiet: bool) -> None:
    """Run autodoc generation before build."""
    from bengal.autodoc.config import load_autodoc_config
    from bengal.cli.commands.autodoc import _generate_cli_docs, _generate_python_docs
    from bengal.cli.helpers.cli_output import get_cli_output

    cli = get_cli_output(quiet=quiet)

    if not quiet:
        cli.blank()
        cli.header("📚 Regenerating documentation...")
        cli.blank()

    # load_autodoc_config can find config automatically if config_path is None
    # It will look for config/ directory or bengal.toml relative to current working directory
    # Since build command runs from site root, this should work
    original_cwd = os.getcwd()
    try:
        # Change to root_path so load_autodoc_config can find config relative to site root
        os.chdir(root_path)
        autodoc_config = load_autodoc_config(config_path)
    finally:
        os.chdir(original_cwd)
    python_config = autodoc_config.get("python", {})
    cli_config = autodoc_config.get("cli", {})

    # Determine what to generate
    generate_python = python_config.get("enabled", True)
    generate_cli = cli_config.get("enabled", False) and cli_config.get("app_module")

    # Generate Python docs
    if generate_python:
        try:
            _generate_python_docs(
                source=tuple(python_config.get("source_dirs", ["."])),
                output=python_config.get("output_dir", "content/api"),
                clean=False,
                parallel=True,
                verbose=False,
                stats=False,
                python_config=python_config,
            )
        except Exception as e:
            if not quiet:
                cli.warning(f"⚠️  Python autodoc failed: {e}")
                cli.warning("Continuing with build...")

    # Generate CLI docs
    if generate_cli:
        try:
            _generate_cli_docs(
                app=cli_config.get("app_module"),
                framework=cli_config.get("framework", "click"),
                output=cli_config.get("output_dir", "content/cli"),
                include_hidden=cli_config.get("include_hidden", False),
                clean=False,
                verbose=False,
                cli_config=cli_config,
                autodoc_config=autodoc_config,
            )
        except Exception as e:
            if not quiet:
                cli.warning(f"⚠️  CLI autodoc failed: {e}")
                cli.warning("Continuing with build...")

    if not quiet:
        cli.blank()
