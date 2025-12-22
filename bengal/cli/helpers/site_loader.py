"""
Helper for loading Site instances from CLI arguments.

Provides a centralized function for loading Bengal sites from CLI
context, with intelligent error handling, directory structure validation,
and detection of common mistakes like running from the wrong directory.

Functions:
    load_site_from_cli: Load a Site with CLI-friendly error handling

The loader performs several helpful checks:
- Validates that source directory exists
- Detects parent directories with Bengal projects (common cd mistake)
- Detects subdirectories with more content (site/ folder pattern)
- Provides clear error messages with suggestions
"""

from __future__ import annotations

from pathlib import Path

import click

from bengal.core.site import Site
from bengal.output import CLIOutput
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def _check_parent_project_conflict(root_path: Path, cli: CLIOutput) -> None:
    """
    Check if parent directories contain another Bengal project.

    This helps catch a common mistake: running bengal from a subdirectory
    of another Bengal project (e.g., running from project root when the
    actual site is in a 'site/' subdirectory, or vice versa).

    Args:
        root_path: The resolved site root path
        cli: CLI output for warnings
    """
    parent = root_path.parent

    # Check up to 3 levels (avoid checking too far up)
    levels_checked = 0
    max_levels = 3

    while parent != parent.parent and levels_checked < max_levels:
        # Signs of a Bengal project in parent:
        # 1. .bengal/ cache directory
        # 2. bengal.toml/yaml config file
        # 3. config/_default/ directory structure

        from bengal.cache.paths import STATE_DIR_NAME

        parent_bengal_cache = parent / STATE_DIR_NAME
        parent_config_toml = parent / "bengal.toml"
        parent_config_yaml = parent / "bengal.yaml"
        parent_config_dir = parent / "config" / "_default"

        has_parent_project = (
            parent_bengal_cache.exists()
            or parent_config_toml.exists()
            or parent_config_yaml.exists()
            or parent_config_dir.exists()
        )

        if has_parent_project:
            # Check if the current directory might be a subdirectory site
            current_has_config = (
                (root_path / "bengal.toml").exists()
                or (root_path / "bengal.yaml").exists()
                or (root_path / "config" / "_default").exists()
            )

            if current_has_config:
                # Both have config - this is likely intentional (nested site)
                logger.debug(
                    "nested_bengal_project_detected",
                    current=root_path.name,
                    parent=parent.name,
                    note="Both have config files, assuming intentional nesting",
                )
            else:
                # Current doesn't have config but parent does - likely mistake
                cli.warning(f"Parent directory has Bengal project: {parent.name}/")
                cli.warning(
                    f"   Current directory ({root_path.name}/) may not be the intended site root.",
                    icon="",
                )
                cli.warning(
                    "   If this is wrong, cd to the correct directory and try again.", icon=""
                )
                cli.blank()

                logger.warning(
                    "parent_bengal_project_detected",
                    current=root_path.name,
                    parent=parent.name,
                    hint="You may be running from wrong directory",
                )
            break

        parent = parent.parent
        levels_checked += 1


def _count_markdown_files(directory: Path) -> int:
    """Count markdown files in a directory tree."""
    if not directory.exists():
        return 0
    try:
        return len(list(directory.rglob("*.md")))
    except (PermissionError, OSError):
        return 0


def _check_subdirectory_site(root_path: Path, cli: CLIOutput) -> None:
    """
    Check if a subdirectory contains what looks like the actual site.

    Common case: running from project root when site/ subdirectory
    contains the actual Bengal site with content.

    Args:
        root_path: The resolved site root path
        cli: CLI output for warnings
    """
    # Check common subdirectory names for site content
    common_site_dirs = ["site", "docs", "website", "web"]

    current_content = root_path / "content"
    current_md_count = _count_markdown_files(current_content)

    for subdir_name in common_site_dirs:
        subdir = root_path / subdir_name

        if not subdir.exists() or not subdir.is_dir():
            continue

        # Check if subdirectory looks like a Bengal site
        has_config = (
            (subdir / "bengal.toml").exists()
            or (subdir / "bengal.yaml").exists()
            or (subdir / "config" / "_default").exists()
        )
        subdir_content = subdir / "content"
        has_content = subdir_content.exists()

        if has_config and has_content:
            subdir_md_count = _count_markdown_files(subdir_content)

            # Warn if subdirectory has significantly more content
            # (at least 2x and at least 50 more files)
            significantly_more = (
                subdir_md_count > current_md_count * 2 and subdir_md_count > current_md_count + 50
            )

            if not current_content.exists():
                # Current has no content at all
                cli.warning(
                    f"Subdirectory '{subdir_name}/' appears to be a Bengal site with content."
                )
                cli.warning(f"   Did you mean to run: cd {subdir_name} && bengal serve", icon="")
                cli.blank()

                logger.warning(
                    "subdirectory_site_detected",
                    current=root_path.name,
                    subdirectory=subdir_name,
                    hint=f"cd {subdir_name} && bengal serve",
                )
            elif significantly_more:
                # Subdirectory has way more content
                cli.warning(
                    f"Subdirectory '{subdir_name}/' has significantly more content "
                    f"({subdir_md_count} vs {current_md_count} markdown files)."
                )
                cli.warning(
                    f"   If you meant to build that site: cd {subdir_name} && bengal serve", icon=""
                )
                cli.blank()

                logger.warning(
                    "larger_subdirectory_site_detected",
                    current=root_path.name,
                    current_md_count=current_md_count,
                    subdirectory=subdir_name,
                    subdir_md_count=subdir_md_count,
                    hint=f"cd {subdir_name} && bengal serve",
                )
            break


def load_site_from_cli(
    source: str = ".",
    config: str | None = None,
    environment: str | None = None,
    profile: str | None = None,
    cli: CLIOutput | None = None,
) -> Site:
    """
    Load a Site instance from CLI arguments with consistent error handling.

    Args:
        source: Source directory path (default: current directory)
        config: Optional config file path
        environment: Optional environment name (local, preview, production)
        profile: Optional profile name (writer, theme-dev, dev)
        cli: Optional CLIOutput instance (creates new if not provided)

    Returns:
        Site instance

    Raises:
        click.Abort: If site loading fails

    Example:
        @click.command()
        def my_command(source: str, config: str | None):
            site = load_site_from_cli(source, config)
            # ... use site ...
    """
    if cli is None:
        cli = CLIOutput()

    root_path = Path(source).resolve()

    if not root_path.exists():
        cli.error(f"Source directory does not exist: {root_path}")
        raise click.Abort()

    # Check for common directory structure mistakes
    _check_parent_project_conflict(root_path, cli)
    _check_subdirectory_site(root_path, cli)

    config_path = Path(config).resolve() if config else None

    if config_path and not config_path.exists():
        cli.error(f"Config file does not exist: {config_path}")
        raise click.Abort()

    try:
        site = Site.from_config(root_path, config_path, environment=environment, profile=profile)
        return site
    except Exception as e:
        cli.error(f"Failed to load site from {root_path}: {e}")
        raise click.Abort() from e
