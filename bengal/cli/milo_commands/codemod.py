"""Codemod command — automated code migrations."""

from __future__ import annotations

import re
from typing import Annotated

from milo import Description


def codemod(
    path: Annotated[str, Description("Directory path to process recursively")],
    dry_run: Annotated[bool, Description("Preview changes without modifying files")] = False,
    diff: Annotated[bool, Description("Show unified diff of changes")] = False,
    yes: Annotated[bool, Description("Skip confirmation prompt (for CI/automation)")] = False,
) -> dict:
    """Run automated code migrations (URL property migration).

    Replaces old URL properties with new naming convention:
    .url -> .href, .relative_url -> ._path, .site_path -> ._path, .permalink -> .href
    """
    from pathlib import Path

    from bengal.output import get_cli_output
    from bengal.utils.io.atomic_write import atomic_write_text

    cli = get_cli_output()
    target = Path(path).resolve()

    if not target.exists() or not target.is_dir():
        cli.error(f"Directory not found: {target}")
        cli.tip("Pass a path to your site's templates/ directory, or the project root.")
        raise SystemExit(1)

    mode_badge = (
        {"level": "warning", "text": "DRY RUN"} if dry_run else {"level": "info", "text": "APPLY"}
    )
    cli.render_write(
        "kv_detail.kida",
        title="Codemod: URL Property Migration",
        items=[
            {"label": "Path", "value": str(target)},
            {"label": "Mode", "value": "DRY RUN" if dry_run else "APPLY CHANGES"},
        ],
        badge=mode_badge,
    )

    extensions = {".html", ".py", ".jinja2", ".j2", ".js"}

    files_to_process: list[Path] = [
        file_path
        for ext in extensions
        for file_path in target.rglob(f"*{ext}")
        if "vendor" not in file_path.parts
    ]

    if not files_to_process:
        cli.render_write(
            "command_empty.kida",
            title="Codemod Changes",
            message="No matching files found.",
            steps=["Pass a directory containing .html, .py, .jinja2, .j2, or .js files."],
        )
        return {"status": "skipped", "message": "No matching files found", "files_processed": 0}

    replacements = [
        (r"\.url\b", ".href", "url -> href"),
        (r"\.relative_url\b", "._path", "relative_url -> _path"),
        (r"\.site_path\b", "._path", "site_path -> _path"),
        (r"\.permalink\b", ".href", "permalink -> href"),
    ]

    total_changes = 0
    files_changed = 0
    pending_writes: list[tuple[Path, str]] = []
    changed_items = []
    error_items = []

    for file_path in sorted(files_to_process):
        try:
            original_content = file_path.read_text(encoding="utf-8")
            modified_content = original_content
            file_changes: list[tuple[str, str]] = []

            for pattern, replacement, description in replacements:
                if replacement.startswith("._") and re.search(
                    rf"\{replacement}\b",
                    modified_content,
                ):
                    continue

                new_content = re.sub(pattern, replacement, modified_content)
                if new_content != modified_content:
                    matches = len(re.findall(pattern, modified_content))
                    file_changes.append((description, str(matches)))
                    modified_content = new_content

            if file_changes:
                files_changed += 1
                changes_count = sum(int(count) for _, count in file_changes)
                total_changes += changes_count
                changed_items.append(
                    {
                        "name": str(file_path.relative_to(target)),
                        "description": ", ".join(
                            f"{desc}: {count}" for desc, count in file_changes
                        ),
                    }
                )

                if diff:
                    cli.blank()
                    _show_diff(cli, original_content, modified_content, file_path)
                    cli.blank()

                if not dry_run:
                    pending_writes.append((file_path, modified_content))

        except Exception as e:
            error_items.append({"name": str(file_path), "description": str(e)})

    if changed_items:
        cli.render_write(
            "command_list.kida",
            title="Codemod Changes",
            summary=f"{files_changed} file(s), {total_changes} replacement(s)",
            items=changed_items,
            mascot=False,
        )
    if error_items:
        cli.render_write(
            "command_list.kida",
            title="Codemod Read Errors",
            summary=f"{len(error_items)} file(s) skipped",
            items=error_items,
            mascot=False,
        )

    cli.render_write(
        "kv_detail.kida",
        title="Summary",
        items=[
            {"label": "Files processed", "value": str(len(files_to_process))},
            {"label": "Files changed", "value": str(files_changed)},
            {"label": "Replacements", "value": str(total_changes)},
        ],
    )
    if dry_run:
        cli.warning("DRY RUN — no files were modified")
        cli.tip("Run without --dry-run to apply changes")
    elif pending_writes:
        if not yes and not cli.confirm(
            f"Apply {len(pending_writes)} file change(s)?", default=False
        ):
            cli.warning("Aborted — no files were modified")
            return {
                "files_processed": len(files_to_process),
                "files_changed": 0,
                "total_replacements": 0,
                "dry_run": False,
                "aborted": True,
            }
        for file_path, modified_content in pending_writes:
            atomic_write_text(file_path, modified_content)
        cli.success(f"Applied changes to {len(pending_writes)} file(s)")

    return {
        "files_processed": len(files_to_process),
        "files_changed": files_changed,
        "total_replacements": total_changes,
        "dry_run": dry_run,
    }


def _show_diff(cli, original: str, modified: str, file_path) -> None:
    """Show unified diff between original and modified content."""
    import difflib

    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)

    diff_output = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=str(file_path),
        tofile=str(file_path),
        lineterm="",
    )

    for line in diff_output:
        cli.info(line.rstrip("\n"))
