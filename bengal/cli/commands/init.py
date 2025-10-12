"""Commands for initializing site structure.

This module provides the 'bengal init' command for quickly scaffolding
site structure with sections and sample content.

Features:
- Create multiple sections at once
- Generate sample content with context-aware naming
- Preview changes with dry-run mode
- Smart name sanitization
- Staggered dates for blog posts
"""

from datetime import datetime, timedelta
from pathlib import Path

import click

from bengal.utils.build_stats import show_error

# Constants
DEFAULT_PAGES_PER_SECTION = 3
WEIGHT_INCREMENT = 10


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug.

    Args:
        text: The text to convert to a slug

    Returns:
        URL-friendly slug with lowercase letters, numbers, and hyphens

    Examples:
        >>> slugify("Hello World")
        'hello-world'
        >>> slugify("My Blog Post!")
        'my-blog-post'
    """
    import re

    # Convert to lowercase and strip whitespace
    slug = text.lower().strip()
    # Remove special characters (keep alphanumeric, spaces, hyphens, underscores)
    slug = re.sub(r"[^\w\s-]", "", slug)
    # Convert underscores and spaces to hyphens
    slug = re.sub(r"[_\s-]+", "-", slug)
    # Remove leading/trailing hyphens
    return slug.strip("-")


def titleize(slug: str) -> str:
    """Convert slug to title case.

    Args:
        slug: The slug to convert (e.g., 'hello-world')

    Returns:
        Title-cased string (e.g., 'Hello World')
    """
    return slug.replace("-", " ").replace("_", " ").title()


def _infer_section_type(section_name: str) -> str:
    """Infer appropriate section type based on name."""
    section_lower = section_name.lower()

    # Blog sections
    if section_lower in ["blog", "posts", "articles", "news"]:
        return "blog"

    # Documentation sections
    if section_lower in [
        "docs",
        "documentation",
        "guides",
        "reference",
        "getting-started",
        "tutorials",
    ]:
        return "doc"

    # Default to section for others (about, contact, projects, etc.)
    return "section"


def generate_section_index(section_name: str, weight: int) -> str:
    """Generate content for a section _index.md file.

    Args:
        section_name: The section slug (e.g., 'blog')
        weight: The section weight for menu ordering

    Returns:
        Markdown content for the section index file
    """
    title = titleize(section_name)
    section_type = _infer_section_type(section_name)

    # Customize description based on type
    if section_type == "blog":
        description = "Latest posts and articles"
    elif section_type == "doc":
        description = "Documentation and guides"
    else:
        description = f"{title} section"

    return f"""---
title: {title}
description: {description}
type: {section_type}
weight: {weight}
---

# {title}

This is the {title.lower()} section. Add your content here.

<!-- TODO: Customize this section -->
"""


def generate_sample_page(
    section_name: str, page_name: str, page_number: int, date: datetime | None = None
) -> str:
    """Generate content for a sample page.

    Args:
        section_name: The section slug this page belongs to
        page_name: The page slug
        page_number: Page number (currently unused, reserved for future use)
        date: Publication date (defaults to now)

    Returns:
        Markdown content for the sample page
    """
    title = titleize(page_name)
    section_title = titleize(section_name)

    if date is None:
        date = datetime.now()

    return f"""---
title: {title}
date: {date.isoformat()}
draft: false
description: Sample page in the {section_title} section
tags: [sample, generated]
---

# {title}

This is a sample page in the {section_title} section.

## Getting Started

Replace this content with your own.

<!-- TODO: Replace this sample content -->
"""


def get_sample_page_names(section_name: str, count: int) -> list[str]:
    """Generate sample page names for a section.

    Uses context-aware naming based on section type:
    - 'blog' gets: welcome-post, getting-started, etc.
    - 'projects'/'portfolio' get: project-alpha, project-beta, etc.
    - 'docs'/'documentation' get: introduction, quickstart, etc.
    - Others get generic: {section}-page-1, {section}-page-2, etc.

    Args:
        section_name: The section slug
        count: Number of page names to generate

    Returns:
        List of page slugs (limited to requested count)
    """
    # Different naming patterns for different section types
    if section_name == "blog":
        names = [
            "welcome-post",
            "getting-started",
            "tips-and-tricks",
            "best-practices",
            "updates",
            "announcements",
            "tutorial",
            "guide",
            "walkthrough",
            "how-to",
        ]
    elif section_name in ["projects", "portfolio"]:
        names = [
            "project-alpha",
            "project-beta",
            "project-gamma",
            "project-delta",
            "project-epsilon",
            "project-zeta",
        ]
    elif section_name in ["docs", "documentation", "guides"]:
        names = [
            "introduction",
            "quickstart",
            "installation",
            "configuration",
            "usage",
            "advanced",
            "troubleshooting",
            "faq",
        ]
    else:
        # Generic names
        names = [f"{section_name}-page-{i+1}" for i in range(count)]

    return names[:count]


class FileOperation:
    """Represents a file operation (create/overwrite).

    Attributes:
        path: Path to the file
        content: Content to write
        is_overwrite: Whether this overwrites an existing file
    """

    def __init__(self, path: Path, content: str, is_overwrite: bool = False):
        """Initialize a file operation.

        Args:
            path: Path to the file
            content: Content to write
            is_overwrite: Whether this overwrites an existing file
        """
        self.path = path
        self.content = content
        self.is_overwrite = is_overwrite

    def execute(self) -> None:
        """Execute the file operation (write to disk)."""
        from bengal.utils.atomic_write import atomic_write_text

        self.path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self.path, self.content)

    def size_bytes(self) -> int:
        """Get the content size in bytes.

        Returns:
            Size of content when encoded as UTF-8
        """
        return len(self.content.encode("utf-8"))


def plan_init_operations(
    content_dir: Path,
    sections: list[str],
    with_content: bool = False,
    pages_per_section: int = DEFAULT_PAGES_PER_SECTION,
    force: bool = False,
) -> tuple[list[FileOperation], list[str]]:
    """Plan all file operations for initialization.

    Args:
        content_dir: Path to the content directory
        sections: List of section slugs to create
        with_content: Whether to generate sample pages
        pages_per_section: Number of sample pages per section
        force: Whether to overwrite existing sections

    Returns:
        Tuple of (list of file operations, list of warning messages)
    """
    operations = []
    warnings = []

    for idx, section in enumerate(sections):
        section_slug = slugify(section)
        section_dir = content_dir / section_slug
        weight = (idx + 1) * WEIGHT_INCREMENT

        # Check if section already exists
        if section_dir.exists() and not force:
            warnings.append(f"Section '{section_slug}' already exists (use --force to overwrite)")
            continue

        # Section index
        index_path = section_dir / "_index.md"
        index_content = generate_section_index(section_slug, weight)
        is_overwrite = index_path.exists()
        operations.append(FileOperation(index_path, index_content, is_overwrite))

        # Sample pages
        if with_content:
            page_names = get_sample_page_names(section_slug, pages_per_section)
            base_date = datetime.now()

            for page_idx, page_name in enumerate(page_names):
                page_slug = slugify(page_name)
                page_path = section_dir / f"{page_slug}.md"

                # Stagger dates for blog posts (most recent first)
                page_date = base_date - timedelta(days=page_idx)

                page_content = generate_sample_page(
                    section_slug, page_slug, page_idx + 1, page_date
                )

                is_overwrite = page_path.exists()
                operations.append(FileOperation(page_path, page_content, is_overwrite))

    return operations, warnings


def format_file_tree(operations: list[FileOperation], content_dir: Path) -> str:
    """Format operations as a tree structure for preview.

    Args:
        operations: List of file operations to format
        content_dir: Base content directory for relative paths

    Returns:
        Formatted tree structure as a string
    """
    from collections import defaultdict

    # Group by directory
    by_dir = defaultdict(list)
    for op in operations:
        rel_path = op.path.relative_to(content_dir)
        dir_path = str(rel_path.parent) if rel_path.parent != Path(".") else "content"
        by_dir[dir_path].append((rel_path.name, op.size_bytes()))

    # Build tree
    lines = []
    sorted_dirs = sorted(by_dir.keys())

    for dir_idx, dir_path in enumerate(sorted_dirs):
        is_last_dir = dir_idx == len(sorted_dirs) - 1
        dir_prefix = "└─" if is_last_dir else "├─"
        lines.append(f"  {dir_prefix} {dir_path}/")

        files = sorted(by_dir[dir_path])
        for file_idx, (filename, size) in enumerate(files):
            is_last_file = file_idx == len(files) - 1
            file_prefix = "   └─" if is_last_dir and is_last_file else "   ├─"
            if not is_last_dir:
                file_prefix = "│  " + ("└─" if is_last_file else "├─")

            size_kb = size / 1024
            size_str = f"{size} bytes" if size < 1024 else f"{size_kb:.1f} KB"
            lines.append(f"  {file_prefix} {filename}  ({size_str})")

    return "\n".join(lines)


@click.command()
@click.option(
    "--sections",
    help="Comma-separated section names (e.g., 'blog,projects,about')",
)
@click.option(
    "--with-content",
    is_flag=True,
    help="Generate sample content in each section",
)
@click.option(
    "--pages-per-section",
    default=DEFAULT_PAGES_PER_SECTION,
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
    sections: str | None, with_content: bool, pages_per_section: int, dry_run: bool, force: bool
) -> None:
    """
    🏗️  Initialize site structure with sections and pages.

    Examples:

      bengal init --sections "blog,projects,about"

      bengal init --sections "blog" --with-content --pages-per-section 10

      bengal init --sections "docs,guides" --dry-run
    """
    try:
        # Ensure we're in a Bengal site
        content_dir = Path("content")
        if not content_dir.exists():
            show_error(
                "Not in a Bengal site directory! Run this from your site root.", show_art=False
            )
            raise click.Abort()

        # Validate and parse sections
        if not sections:
            show_error(
                "Please provide --sections (e.g., --sections 'blog,projects')", show_art=False
            )
            raise click.Abort()

        section_list = [s.strip() for s in sections.split(",") if s.strip()]

        if not section_list:
            show_error("No valid sections provided", show_art=False)
            raise click.Abort()

        # Sanitize section names
        original_sections = section_list.copy()
        section_list = [slugify(s) for s in section_list]

        # Warn about name changes
        name_changes = []
        for orig, sanitized in zip(original_sections, section_list, strict=False):
            if orig != sanitized:
                name_changes.append(f"  • '{orig}' → '{sanitized}'")

        if name_changes:
            click.echo(click.style("\n⚠️  Section names sanitized:", fg="yellow"))
            for change in name_changes:
                click.echo(click.style(change, fg="yellow"))
            click.echo()

        # Plan operations
        operations, warnings = plan_init_operations(
            content_dir, section_list, with_content, pages_per_section, force
        )

        # Show warnings
        if warnings:
            click.echo(click.style("\n⚠️  Warnings:", fg="yellow", bold=True))
            for warning in warnings:
                click.echo(click.style(f"  • {warning}", fg="yellow"))
            click.echo()

            if not operations:
                show_error(
                    "Nothing to create. Use --force to overwrite existing content.", show_art=False
                )
                raise click.Abort()

        if not operations:
            show_error("No operations to perform", show_art=False)
            raise click.Abort()

        # Dry run - just preview
        if dry_run:
            click.echo(
                click.style("\n📋 Dry run - no files will be created\n", fg="cyan", bold=True)
            )
            click.echo(click.style("Would create:", fg="cyan"))
            click.echo(format_file_tree(operations, content_dir))

            total_size = sum(op.size_bytes() for op in operations)
            size_kb = total_size / 1024
            click.echo(
                click.style(f"\nTotal: {len(operations)} files, {size_kb:.1f} KB", fg="cyan")
            )
            click.echo(click.style("\nRun without --dry-run to create these files", fg="yellow"))
            return

        # Execute operations
        click.echo(click.style("\n🏗️  Initializing site structure...\n", fg="cyan", bold=True))

        sections_created = set()
        pages_created = 0

        for op in operations:
            # Calculate relative path for display
            try:
                rel_path = op.path.relative_to(Path.cwd())
            except ValueError:
                # If path is not relative to cwd, just use the path itself
                rel_path = op.path

            op.execute()

            if op.path.name == "_index.md":
                sections_created.add(op.path.parent.name)
                click.echo(click.style("   ✓ ", fg="green") + f"Created {rel_path}")
            else:
                pages_created += 1
                click.echo(click.style("   ✓ ", fg="green") + f"Created {rel_path}")

        # Summary
        click.echo(click.style("\n✨ Site initialized successfully!\n", fg="green", bold=True))
        click.echo(click.style("Created:", fg="cyan"))
        click.echo(f"  • {len(sections_created)} sections")
        click.echo(f"  • {pages_created} pages")

        # Show tip about auto-navigation
        if sections_created:
            click.echo(click.style("\n🎯 Navigation configured!", fg="green", bold=True))
            click.echo(click.style("   Sections will appear automatically in nav", fg="green"))
            click.echo()
            click.echo(
                click.style("   💡 Tip: ", fg="cyan")
                + click.style("To customize nav order or add external links,", fg="white")
            )
            click.echo(click.style("      add [[menu.main]] entries to bengal.toml", fg="white"))
            click.echo()

        # Next steps
        click.echo(click.style("\n📚 Next steps:", fg="cyan", bold=True))
        click.echo("  1. Review and customize generated content")
        click.echo("  2. Run 'bengal serve' to preview your site")
        click.echo("  3. Edit files in content/ to add your content")
        click.echo()

    except click.Abort:
        raise
    except Exception as e:
        show_error(f"Failed to initialize: {e}", show_art=False)
        raise click.Abort() from e
