"""
Command metadata system for discovery and documentation.

Provides a decorator-based system for attaching metadata to CLI commands,
enabling automatic documentation generation, command categorization,
tag-based filtering, and discovery of command requirements.

Classes:
    CommandMetadata: Dataclass holding command metadata

Functions:
    command_metadata: Decorator to attach metadata to commands
    get_command_metadata: Extract metadata from a command
    list_commands_by_category: Group commands by their category
    find_commands_by_tag: Find commands with a specific tag

Example:
    @click.command()
    @command_metadata(
        category="build",
        description="Build the static site",
        requires_site=True,
        tags=["production"]
    )
    def build():
        pass
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

import click

F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class CommandMetadata:
    """
    Metadata for a CLI command.

    Stores information about a command that can be used for documentation,
    categorization, and runtime validation. Attach to commands using the
    @command_metadata decorator.

    Attributes:
        category: Functional grouping (build, content, config, dev)
        description: One-line summary of command purpose
        examples: List of example invocations
        requires_site: True if command needs a valid Bengal site
        requires_build: True if site must be built first
        tags: Searchable tags for filtering
        aliases: Alternative names for command discovery
    """

    category: str = "general"
    """Command category (e.g., 'build', 'content', 'config', 'dev')"""

    description: str = ""
    """Short description of what the command does"""

    examples: list[str] = field(default_factory=list)
    """Example usage strings"""

    requires_site: bool = False
    """Whether this command requires a site to be loaded"""

    requires_build: bool = False
    """Whether this command requires the site to be built first"""

    tags: list[str] = field(default_factory=list)
    """Tags for filtering/discovery (e.g., ['dev', 'content', 'quick'])"""

    aliases: list[str] = field(default_factory=list)
    """Command aliases (for discovery)"""

    def to_dict(self) -> dict[str, Any]:
        """
        Convert metadata to a dictionary representation.

        Returns:
            Dict with all metadata fields for serialization/display.
        """
        return {
            "category": self.category,
            "description": self.description,
            "examples": self.examples,
            "requires_site": self.requires_site,
            "requires_build": self.requires_build,
            "tags": self.tags,
            "aliases": self.aliases,
        }


def command_metadata(
    category: str = "general",
    description: str = "",
    examples: list[str] | None = None,
    requires_site: bool = False,
    requires_build: bool = False,
    tags: list[str] | None = None,
    aliases: list[str] | None = None,
) -> Callable[[F], F]:
    """
    Decorator to attach metadata to a CLI command.

    Args:
        category: Command category (e.g., 'build', 'content', 'config', 'dev')
        description: Short description of what the command does
        examples: Example usage strings
        requires_site: Whether this command requires a site to be loaded
        requires_build: Whether this command requires the site to be built first
        tags: Tags for filtering/discovery (e.g., ['dev', 'content', 'quick'])
        aliases: Command aliases (for discovery)

    Example:
        @click.command()
        @command_metadata(
            category="build",
            description="Build the static site",
            examples=["bengal build", "bengal build --incremental"],
            requires_site=True,
            tags=["build", "production"]
        )
        def build():
            # ...
            pass
    """

    def decorator(func: F) -> F:
        metadata = CommandMetadata(
            category=category,
            description=description,
            examples=examples or [],
            requires_site=requires_site,
            requires_build=requires_build,
            tags=tags or [],
            aliases=aliases or [],
        )
        # Attach metadata to the function
        func.__command_metadata__ = metadata  # type: ignore[attr-defined]
        return func

    return decorator


def get_command_metadata(cmd: click.Command | Callable[..., Any]) -> CommandMetadata | None:
    """
    Get metadata from a command.

    Args:
        cmd: Click command or callable

    Returns:
        CommandMetadata if found, None otherwise
    """
    if isinstance(cmd, click.Command):
        # Check if metadata is attached to the callback
        callback = cmd.callback
        if callback and hasattr(callback, "__command_metadata__"):
            metadata: CommandMetadata = callback.__command_metadata__  # type: ignore[attr-defined]
            return metadata
    elif hasattr(cmd, "__command_metadata__"):
        metadata_attr: CommandMetadata = cmd.__command_metadata__  # type: ignore[attr-defined]
        return metadata_attr
    return None


def list_commands_by_category(group: click.Group) -> dict[str, list[click.Command]]:
    """
    List all commands in a group, organized by category.

    Args:
        group: Click group to scan

    Returns:
        Dictionary mapping category names to lists of commands
    """
    categories: dict[str, list[click.Command]] = {}

    def scan_group(grp: click.Group, prefix: str = "") -> None:
        for name, cmd in grp.commands.items():
            full_name = f"{prefix}{name}" if prefix else name

            if isinstance(cmd, click.Group):
                scan_group(cmd, f"{full_name} ")
            else:
                metadata = get_command_metadata(cmd)
                category = metadata.category if metadata else "general"
                if category not in categories:
                    categories[category] = []
                categories[category].append(cmd)

    scan_group(group)
    return categories


def find_commands_by_tag(group: click.Group, tag: str) -> list[tuple[str, click.Command]]:
    """
    Find commands that have a specific tag.

    Args:
        group: Click group to scan
        tag: Tag to search for

    Returns:
        List of (command_path, command) tuples
    """
    results: list[tuple[str, click.Command]] = []

    def scan_group(grp: click.Group, prefix: str = "") -> None:
        for name, cmd in grp.commands.items():
            full_name = f"{prefix}{name}" if prefix else name

            if isinstance(cmd, click.Group):
                scan_group(cmd, f"{full_name} ")
            else:
                metadata = get_command_metadata(cmd)
                if metadata and tag in metadata.tags:
                    results.append((full_name, cmd))

    scan_group(group)
    return results
