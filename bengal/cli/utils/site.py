"""
Site loading utilities for CLI commands.

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

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.output import CLIOutput
    from bengal.utils.observability.profile import BuildProfile


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
    from bengal.cache.paths import STATE_DIR_NAME
    from bengal.utils.observability.logger import get_logger

    logger = get_logger(__name__)
    parent = root_path.parent

    # Check up to 3 levels (avoid checking too far up)
    levels_checked = 0
    max_levels = 3

    while parent != parent.parent and levels_checked < max_levels:
        # Signs of a Bengal project in parent:
        # 1. .bengal/ cache directory
        # 2. bengal.toml/yaml config file
        # 3. config/_default/ directory structure

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
    except PermissionError, OSError:
        return 0


def _is_bengal_site(candidate: Path) -> bool:
    """True if path has Bengal site markers: config + content."""
    has_config = (
        (candidate / "bengal.toml").exists()
        or (candidate / "bengal.yaml").exists()
        or (candidate / "config" / "_default").exists()
    )
    has_content = (candidate / "content").exists()
    return bool(has_config and has_content)


def _check_subdirectory_site(root_path: Path, cli: CLIOutput) -> Path | None:
    """
    Check if a subdirectory contains what looks like the actual site.

    Scans all direct subdirectories for Bengal site markers (config + content)
    instead of hardcoding directory names. Handles blog/, site/, docs/, etc.

    Args:
        root_path: The resolved site root path
        cli: CLI output for warnings

    Returns:
        Path to subdirectory site if found, None otherwise.

    """
    from bengal.utils.observability.logger import get_logger

    logger = get_logger(__name__)

    current_content = root_path / "content"
    current_md_count = _count_markdown_files(current_content)

    try:
        subdirs = [d for d in root_path.iterdir() if d.is_dir() and not d.name.startswith(".")]
    except OSError:
        return None

    # Collect all Bengal site candidates
    candidates: list[tuple[Path, int]] = []

    for subdir in sorted(subdirs):
        if not _is_bengal_site(subdir):
            continue

        subdir_md_count = _count_markdown_files(subdir / "content")

        if not current_content.exists():
            candidates.append((subdir, subdir_md_count))
        else:
            significantly_more = (
                subdir_md_count > current_md_count * 2 and subdir_md_count > current_md_count + 50
            )
            if significantly_more:
                candidates.append((subdir, subdir_md_count))

    if not candidates:
        return None

    # Pick one: prompt if multiple and interactive, else use largest
    if len(candidates) > 1 and sys.stdin.isatty():
        cli.warning("Multiple Bengal sites found in subdirectories:")
        for i, (subdir, count) in enumerate(candidates, 1):
            cli.warning(f"  {i}. {subdir.name}/ ({count} markdown files)")
        cli.blank()

        default_idx = str(max(range(len(candidates)), key=lambda j: candidates[j][1]) + 1)
        try:
            choice = cli.prompt(
                "Which site to use?",
                default=default_idx,
            )
            idx = int(choice) - 1
            if idx < 0 or idx >= len(candidates):
                idx = int(default_idx) - 1
            subdir = candidates[idx][0]
            subdir_md_count = _count_markdown_files(subdir / "content")
        except EOFError, KeyboardInterrupt, ValueError:
            sys.exit(1)
    else:
        subdir, subdir_md_count = max(candidates, key=lambda c: c[1])

    subdir_name = subdir.name

    if not current_content.exists():
        cli.warning(f"Using subdirectory '{subdir_name}/' (Bengal site with content).")
        cli.warning(f"   To run explicitly: cd {subdir_name} && bengal serve", icon="")
        cli.blank()

        logger.warning(
            "subdirectory_site_detected",
            _console=False,
            current=root_path.name,
            subdirectory=subdir_name,
            hint=f"cd {subdir_name} && bengal serve",
        )
    else:
        cli.warning(
            f"Using subdirectory '{subdir_name}/' (has more content: "
            f"{subdir_md_count} vs {current_md_count} markdown files)."
        )
        cli.warning(f"   To run explicitly: cd {subdir_name} && bengal serve", icon="")
        cli.blank()

        logger.warning(
            "larger_subdirectory_site_detected",
            _console=False,
            current=root_path.name,
            current_md_count=current_md_count,
            subdirectory=subdir_name,
            subdir_md_count=subdir_md_count,
            hint=f"cd {subdir_name} && bengal serve",
        )

    return subdir


def load_site_from_cli(
    source: str = ".",
    config: str | None = None,
    environment: str | None = None,
    profile: str | BuildProfile | None = None,
    cli: CLIOutput | None = None,
) -> Site:
    """
    Load a Site instance from CLI arguments with consistent error handling.

    Args:
        source: Source directory path (default: current directory)
        config: Optional config file path
        environment: Optional environment name (local, preview, production)
        profile: Optional profile name or BuildProfile object
        cli: Optional CLIOutput instance (creates new if not provided)

    Returns:
        Site instance

    Raises:
        SystemExit: If site loading fails

    """
    from bengal.cli.utils.output import get_cli_output
    from bengal.core.site import Site
    from bengal.utils.observability.profile import BuildProfile

    if cli is None:
        cli = get_cli_output()

    # Normalize profile to string if it's an enum
    profile_name = str(profile) if isinstance(profile, BuildProfile) else profile

    root_path = Path(source).resolve()

    if not root_path.exists():
        cli.error(f"Source directory does not exist: {root_path}")
        sys.exit(1)

    # Check for common directory structure mistakes
    _check_parent_project_conflict(root_path, cli)
    subdir_site = _check_subdirectory_site(root_path, cli)
    if subdir_site and not (
        (root_path / "bengal.toml").exists()
        or (root_path / "bengal.yaml").exists()
        or (root_path / "config" / "_default").exists()
    ):
        # Auto-correct when the current directory lacks config but a clear site
        # exists in a common subdirectory (e.g., /site).
        root_path = subdir_site

    config_path = Path(config).resolve() if config else None

    if config_path and not config_path.exists():
        cli.error(f"Config file does not exist: {config_path}")
        sys.exit(1)

    from bengal.cli.utils.errors import handle_exception

    try:
        return Site.from_config(
            root_path, config_path, environment=environment, profile=profile_name
        )
    except SystemExit, KeyboardInterrupt:
        raise
    except Exception as e:
        handle_exception(e, cli, operation="loading site configuration")
        raise SystemExit(1) from e
