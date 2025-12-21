"""
Codemod command for automated code transformations.

Provides utilities for migrating codebases, particularly for URL property migrations.
"""

from __future__ import annotations

import re
from pathlib import Path

import click

from bengal.cli.base import BengalGroup
from bengal.output import CLIOutput


@click.group("codemod", cls=BengalGroup)
def codemod_cli() -> None:
    """
    Automated code transformation utilities.

    Use codemod commands to migrate codebases safely with preview and dry-run modes.
    """
    pass


@codemod_cli.command("urls")
@click.option(
    "--path",
    "-p",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Directory path to process (recursively)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview changes without modifying files",
)
@click.option(
    "--diff",
    is_flag=True,
    default=False,
    help="Show unified diff of changes",
)
def codemod_urls(path: Path, dry_run: bool, diff: bool) -> None:
    """
    Migrate URL properties from old naming to new href/_path convention.

    Replaces:
    - .url → .href (but NOT source_url, canonical_url, etc.)
    - .relative_url → ._path
    - .site_path → ._path
    - .permalink → .href

    Examples:
        bengal codemod-urls --path site/themes/ --dry-run
        bengal codemod-urls --path site/themes/ --diff
        bengal codemod-urls --path site/themes/
    """
    cli = CLIOutput()
    cli.info("Codemod: URL Property Migration")
    cli.detail(f"Path: {path}")
    cli.detail(f"Mode: {'DRY RUN' if dry_run else 'APPLY CHANGES'}")
    cli.blank()

    # File extensions to process
    extensions = {".html", ".py", ".jinja2", ".j2", ".js"}

    # Find all matching files (exclude vendor directories)
    files_to_process: list[Path] = []
    for ext in extensions:
        for file_path in path.rglob(f"*{ext}"):
            # Skip vendor directories (third-party libraries)
            if "vendor" not in file_path.parts:
                files_to_process.append(file_path)

    if not files_to_process:
        cli.warning("No matching files found.")
        return

    cli.info(f"Found {len(files_to_process)} files to process")
    cli.blank()

    # Replacement patterns
    # Use word boundaries to avoid matching source_url, canonical_url, etc.
    replacements = [
        (r"\.url\b", ".href", "url → href"),
        (r"\.relative_url\b", "._path", "relative_url → _path"),
        (r"\.site_path\b", "._path", "site_path → _path"),
        (r"\.permalink\b", ".href", "permalink → href"),
    ]

    total_changes = 0
    files_changed = 0

    for file_path in sorted(files_to_process):
        try:
            original_content = file_path.read_text(encoding="utf-8")
            modified_content = original_content
            file_changes: list[tuple[str, str]] = []

            # Apply all replacements
            for pattern, replacement, description in replacements:
                # Skip if replacement would create something that already exists
                # (e.g., if ._path already exists, don't replace .relative_url → ._path)
                if replacement.startswith("._") and re.search(
                    rf"\{replacement}\b", modified_content
                ):
                    # Check if the replacement target already exists in the file
                    # This prevents double-migration
                    continue

                new_content = re.sub(pattern, replacement, modified_content)
                if new_content != modified_content:
                    # Count occurrences
                    matches = len(re.findall(pattern, modified_content))
                    file_changes.append((description, str(matches)))
                    modified_content = new_content

            if file_changes:
                files_changed += 1
                changes_count = sum(int(count) for _, count in file_changes)
                total_changes += changes_count

                cli.detail(f"✓ {file_path.relative_to(path)}", icon="✓")
                for desc, count in file_changes:
                    cli.detail(f"  {desc}: {count} occurrences", indent=2)

                if diff:
                    cli.blank()
                    _show_diff(cli, original_content, modified_content, file_path)
                    cli.blank()

                if not dry_run:
                    file_path.write_text(modified_content, encoding="utf-8")

        except Exception as e:
            cli.error(f"✗ {file_path}: {e}")

    cli.blank()
    cli.info("Summary:")
    cli.detail(f"Files processed: {len(files_to_process)}", indent=1)
    cli.detail(f"Files changed: {files_changed}", indent=1)
    cli.detail(f"Total replacements: {total_changes}", indent=1)

    if dry_run:
        cli.blank()
        cli.warning("DRY RUN - No files were modified.")
        cli.detail("Run without --dry-run to apply changes.", indent=1)


def _show_diff(cli: CLIOutput, original: str, modified: str, file_path: Path) -> None:
    """Show unified diff between original and modified content."""
    import difflib

    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=str(file_path),
        tofile=str(file_path),
        lineterm="",
    )

    # Use console directly for diff output (supports rich formatting)
    for line in diff:
        if line.startswith("---") or line.startswith("+++"):
            cli.console.print(line, style="dim")
        elif line.startswith("@@"):
            cli.console.print(line, style="cyan")
        elif line.startswith("-"):
            cli.console.print(line, style="red")
        elif line.startswith("+"):
            cli.console.print(line, style="green")
        else:
            cli.console.print(line)
