"""Commands for initializing site structure.

This module provides the 'bengal init' command for quickly scaffolding
site structure. It now delegates to the skeleton system under the hood.

Features:
- Create sections using built-in skeletons (blog, docs, empty)
- Backward compatibility with --with-content flags (maps to props)
"""

from __future__ import annotations

from pathlib import Path

import click

from bengal.cli.base import BengalCommand
from bengal.cli.helpers import command_metadata, handle_cli_errors
from bengal.cli.skeleton.hydrator import Hydrator
from bengal.cli.skeleton.schema import Component, Skeleton
from bengal.orchestration.stats import show_error
from bengal.output import CLIOutput


def create_skeleton_from_args(
    sections: tuple[str, ...],
    with_content: bool,
    pages_per_section: int,
) -> Skeleton:
    """
    Create an in-memory skeleton based on legacy init arguments.

    This bridges the gap between the old imperative init command
    and the new declarative skeleton system.
    """
    structure: list[Component] = []

    # If no sections provided, default to blog
    section_names = sections if sections else ("blog",)

    for name in section_names:
        name = name.lower().strip()

        # Determine type based on name (simple heuristic)
        type_ = "section"
        if name in ("blog", "posts", "news"):
            type_ = "blog"
        elif name in ("docs", "guides", "reference"):
            type_ = "doc"

        # Create section component
        section = Component(
            path=name,
            type=type_,
            props={"title": name.title().replace("-", " ")},
        )

        # Add sample pages if requested
        if with_content:
            for i in range(pages_per_section):
                page_num = i + 1
                page_name = f"sample-post-{page_num}" if type_ == "blog" else f"page-{page_num}"

                page = Component(
                    path=f"{page_name}.md",
                    props={"title": f"Sample {name.title()} {page_num}", "draft": False},
                    content=f"# Sample Page {page_num}\n\nThis is sample content for {name}.",
                )
                section.pages.append(page)

        structure.append(section)

    return Skeleton(
        name="init-scaffold", description="Scaffold created via bengal init", structure=structure
    )


@click.command(cls=BengalCommand)
@command_metadata(
    category="project",
    description="Initialize site structure (delegates to skeleton system)",
    examples=[
        "bengal init",
        "bengal init --sections blog --sections docs",
        "bengal init --sections blog --with-content",
    ],
    requires_site=True,
    tags=["project", "setup", "quick"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--sections",
    "-s",
    multiple=True,
    default=("blog",),
    help="Content sections to create (e.g., blog, docs). Default: blog",
)
@click.option(
    "--with-content",
    is_flag=True,
    help="Generate sample content in each section",
)
@click.option(
    "--pages-per-section",
    default=3,
    type=int,
    help="Number of sample pages per section (with --with-content)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be created without creating files",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing sections and files",
)
def init(
    sections: tuple[str, ...],
    with_content: bool,
    pages_per_section: int,
    dry_run: bool,
    force: bool,
) -> None:
    """
    Initialize site structure.

    Uses the Component Model to generate sections and pages.
    """
    cli = CLIOutput()

    try:
        # Ensure we're in a Bengal site
        content_dir = Path("content")
        if not content_dir.exists():
            # Auto-create content dir if missing
            if not dry_run:
                content_dir.mkdir(exist_ok=True)
            elif not content_dir.exists():
                # If dry run and dir missing, we can't really proceed with hydrator validation
                # unless we mock it, but let's just warn
                pass

        # Build skeleton from args
        skeleton = create_skeleton_from_args(sections, with_content, pages_per_section)

        # Hydrate
        hydrator = Hydrator(content_dir, dry_run=dry_run, force=force)
        hydrator.apply(skeleton)

        # Report
        cli.blank()
        if dry_run:
            cli.warning("📋 Dry run - no files created")
        else:
            cli.success("✨ Site initialized successfully!")

        cli.info(f"Created: {len(hydrator.created_files)} files")
        if hydrator.skipped_files:
            cli.warning(
                f"Skipped: {len(hydrator.skipped_files)} existing files (use --force to overwrite)"
            )

        # Tip
        cli.blank()
        cli.tip("To create more complex structures, try 'bengal skeleton apply'")

    except Exception as e:
        show_error(f"Failed to initialize: {e}", show_art=False)
        raise click.Abort() from e
