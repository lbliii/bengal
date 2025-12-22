"""Collection commands for managing content schemas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from bengal.cli.base import BengalGroup
from bengal.cli.helpers import (
    command_metadata,
    get_cli_output,
    handle_cli_errors,
)

# Template for generated collections.py file
COLLECTIONS_TEMPLATE = '''\
"""
Content Collections - Type-safe schemas for your content.

This file defines collection schemas that validate your content's frontmatter
during discovery. Invalid content will be caught early with helpful error messages.

Usage:
    1. Define dataclass schemas for your content types
    2. Map directories to schemas using define_collection()
    3. Bengal will validate content automatically during builds

Configuration:
    Enable strict mode in bengal.toml to fail builds on validation errors:

    [build]
    strict_collections = true  # Default: false (warn only)

For more information, see: https://bengal.dev/docs/collections
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from bengal.collections import define_collection

# You can import standard schemas or define your own:
# from bengal.collections.schemas import BlogPost, DocPage, APIReference


# Example: Blog post schema
@dataclass
class BlogPost:
    """Schema for blog posts in content/blog/."""

    title: str
    date: datetime
    author: str = "Anonymous"
    tags: list[str] = field(default_factory=list)
    draft: bool = False
    description: Optional[str] = None
    image: Optional[str] = None


# Example: Documentation page schema
@dataclass
class DocPage:
    """Schema for documentation in content/docs/."""

    title: str
    weight: int = 0
    category: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    toc: bool = True
    description: Optional[str] = None


# Define your collections here
# Maps directory paths to schemas for validation
collections = {
    # Uncomment and adjust based on your content structure:
    #
    # "blog": define_collection(
    #     schema=BlogPost,
    #     directory="blog",  # Relative to content/
    # ),
    #
    # "docs": define_collection(
    #     schema=DocPage,
    #     directory="docs",  # Relative to content/
    # ),
}
'''

# Minimal template when using --minimal flag
COLLECTIONS_TEMPLATE_MINIMAL = '''\
"""Content collection schemas for Bengal."""

from __future__ import annotations

from bengal.collections import define_collection
from bengal.collections.schemas import BlogPost, DocPage

collections = {
    # "blog": define_collection(schema=BlogPost, directory="blog"),
    # "docs": define_collection(schema=DocPage, directory="docs"),
}
'''


@click.group(cls=BengalGroup, invoke_without_command=True)
@click.pass_context
def collections(ctx: click.Context) -> None:
    """
    Manage content collections.

    Collections provide type-safe schemas for your content's frontmatter.
    Define schemas to validate content during builds and catch errors early.

    Commands:
      init     Generate a starter collections.py file
      list     Show defined collections and their schemas
      validate Validate content against collection schemas
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@collections.command("init")
@command_metadata(
    category="setup",
    description="Generate a collections.py file with example schemas",
    examples=[
        "bengal collections init",
        "bengal collections init --minimal",
        "bengal collections init --force",
    ],
    requires_site=False,
    tags=["setup", "collections", "schema"],
)
@handle_cli_errors(show_art=False)
@click.option("--force", "-f", is_flag=True, help="Overwrite existing collections.py")
@click.option(
    "--minimal", "-m", is_flag=True, help="Generate minimal template using built-in schemas"
)
@click.argument("source", type=click.Path(), default=".")
def init_collections(force: bool, minimal: bool, source: str) -> None:
    """
    Generate a collections.py file with example schemas.

    Creates a starter collections.py file at your project root with
    example schemas for blog posts and documentation pages.

    Examples:
      bengal collections init           # Generate full template
      bengal collections init --minimal # Use built-in schemas
      bengal collections init --force   # Overwrite existing file
    """
    cli = get_cli_output()
    root_path = Path(source).resolve()
    collections_path = root_path / "collections.py"

    cli.blank()
    cli.header("Initializing content collections...")
    cli.blank()

    # Check if file already exists
    if collections_path.exists() and not force:
        cli.warning(f"collections.py already exists at {collections_path}")
        cli.tip("Use --force to overwrite")
        cli.blank()
        return

    # Choose template
    template = COLLECTIONS_TEMPLATE_MINIMAL if minimal else COLLECTIONS_TEMPLATE

    # Write the file
    collections_path.write_text(template)

    # Show success
    cli.success(f"Created {collections_path}", icon="✓")
    cli.blank()

    # Show next steps
    cli.info("Next steps:")
    cli.detail("1. Edit collections.py to define your schemas", indent=1)
    cli.detail("2. Uncomment collections for directories you want to validate", indent=1)
    cli.detail("3. Run 'bengal build' - content will be validated automatically", indent=1)
    cli.blank()

    if not minimal:
        cli.tip("Tip: Use --minimal for a shorter template with built-in schemas")
    else:
        cli.tip("Tip: Import custom schemas from bengal.collections.schemas")

    cli.blank()


@collections.command("list")
@command_metadata(
    category="info",
    description="List defined collections and their schemas",
    examples=[
        "bengal collections list",
    ],
    requires_site=True,
    tags=["info", "collections"],
)
@handle_cli_errors(show_art=False)
@click.option(
    "--config", type=click.Path(exists=True), help="Path to config file (default: bengal.toml)"
)
@click.argument("source", type=click.Path(exists=True), default=".")
def list_collections(config: str | None, source: str) -> None:
    """
    📋 List defined collections and their schemas.

    Shows all collections defined in collections.py with their
    directories and schema fields.
    """
    from dataclasses import fields, is_dataclass

    from bengal.collections import CollectionConfig, load_collections

    cli = get_cli_output()
    root_path = Path(source).resolve()

    cli.blank()
    cli.header("Content Collections")
    cli.blank()

    # Load collections
    loaded: dict[str, CollectionConfig[Any]] = load_collections(root_path)

    if not loaded:
        cli.warning("No collections defined")
        cli.blank()
        cli.info("To get started:")
        cli.detail("bengal collections init", indent=1)
        cli.blank()
        return

    # Display each collection
    for name, coll_config in loaded.items():
        cli.info(f"📁 {name}")
        cli.detail(f"Directory: content/{coll_config.directory}", indent=1)
        cli.detail(f"Schema: {coll_config.schema.__name__}", indent=1)
        cli.detail(f"Strict: {coll_config.strict}", indent=1)

        # Show schema fields
        if is_dataclass(coll_config.schema):
            cli.detail("Fields:", indent=1)
            for f in fields(coll_config.schema):
                required = f.default is f.default_factory is type(f.default)
                marker = "*" if required else " "
                cli.detail(f"  {marker} {f.name}: {f.type}", indent=1)

        cli.blank()

    cli.info(f"Total: {len(loaded)} collection(s)")
    cli.blank()


@collections.command("validate")
@command_metadata(
    category="validation",
    description="Validate content against collection schemas",
    examples=[
        "bengal collections validate",
        "bengal collections validate --collection blog",
    ],
    requires_site=True,
    tags=["validation", "collections"],
)
@handle_cli_errors(show_art=False)
@click.option("--collection", "-c", help="Validate specific collection only")
@click.option(
    "--config", type=click.Path(exists=True), help="Path to config file (default: bengal.toml)"
)
@click.argument("source", type=click.Path(exists=True), default=".")
def validate_collections(collection: str | None, config: str | None, source: str) -> None:
    """
    ✓ Validate content against collection schemas.

    Validates all content files against their collection schemas,
    reporting any validation errors.
    """
    import frontmatter

    from bengal.collections import SchemaValidator, load_collections

    cli = get_cli_output()
    root_path = Path(source).resolve()
    content_dir = root_path / "content"

    cli.blank()
    cli.header("Validating collections...")
    cli.blank()

    # Load collections
    loaded = load_collections(root_path)

    if not loaded:
        cli.warning("No collections defined")
        cli.detail("Run 'bengal collections init' to create collections.py", indent=1)
        cli.blank()
        return

    # Filter to specific collection if requested
    if collection:
        if collection not in loaded:
            cli.error(f"Collection '{collection}' not found")
            cli.detail(f"Available: {', '.join(loaded.keys())}", indent=1)
            cli.blank()
            return
        loaded = {collection: loaded[collection]}

    total_files = 0
    total_errors = 0
    errors_by_file: dict[str, list[str]] = {}

    for name, coll_config in loaded.items():
        collection_dir = content_dir / coll_config.directory

        if not collection_dir.exists():
            cli.warning(f"Collection '{name}' directory not found: {collection_dir}")
            continue

        cli.info(f"📁 {name}")

        # Find all content files
        files = list(collection_dir.glob(coll_config.glob))
        validator = SchemaValidator(coll_config.schema, strict=coll_config.strict)

        file_count = 0
        error_count = 0

        for file_path in files:
            file_count += 1
            total_files += 1

            try:
                # Parse frontmatter
                with open(file_path) as f:
                    post = frontmatter.load(f)

                metadata = dict(post.metadata)

                # Apply transform if defined
                if coll_config.transform:
                    metadata = coll_config.transform(metadata)

                # Validate
                result = validator.validate(metadata, source_file=file_path)

                if not result.valid:
                    error_count += 1
                    total_errors += 1
                    rel_path = file_path.relative_to(root_path)
                    errors_by_file[str(rel_path)] = [
                        f"{e.field}: {e.message}" for e in result.errors
                    ]
                    cli.detail(f"✗ {rel_path}", indent=1)
                else:
                    rel_path = file_path.relative_to(root_path)
                    cli.detail(f"✓ {rel_path}", indent=1)

            except Exception as e:
                error_count += 1
                total_errors += 1
                rel_path = file_path.relative_to(root_path)
                errors_by_file[str(rel_path)] = [str(e)]
                cli.detail(f"✗ {rel_path}: {e}", indent=1)

        if error_count == 0:
            cli.detail(f"  All {file_count} files valid ✓", indent=1)
        else:
            cli.detail(f"  {error_count}/{file_count} files have errors", indent=1)

        cli.blank()

    # Show summary
    if total_errors == 0:
        cli.success(f"All {total_files} files valid!", icon="✓")
    else:
        cli.error(f"Validation failed: {total_errors} error(s) in {len(errors_by_file)} file(s)")
        cli.blank()

        # Show detailed errors
        for err_file_path, errors in errors_by_file.items():
            cli.info(f"  {err_file_path}")
            for error in errors:
                cli.detail(f"    └─ {error}", indent=0)

    cli.blank()
