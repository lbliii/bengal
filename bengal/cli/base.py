"""
Custom Click classes and CLI infrastructure for Bengal.

This module provides the core Click extensions that give Bengal's CLI
its distinctive themed output, fuzzy command matching, and alias support.

Classes:
    BengalCommand: Custom Click command with themed help output
    BengalGroup: Custom Click group with typo detection and themed help

The module also maintains the alias registry that maps short commands
(e.g., 'b', 's', 'dev') to their canonical counterparts.

Example:
    >>> @click.command(cls=BengalCommand)
    ... def my_command():
    ...     pass

Related:
    - bengal/cli/__init__.py: Main CLI assembly
    - bengal/output/: Output formatting utilities
"""

from __future__ import annotations

import re

import click

from bengal.output import CLIOutput

# =============================================================================
# ALIAS REGISTRY
# =============================================================================
# Maps aliases to their canonical command names for help and typo detection.
# This enables power users to use shortcuts like 'b' for 'build'.

COMMAND_ALIASES: dict[str, str] = {
    # Short aliases
    "b": "build",
    "s": "serve",
    "c": "clean",
    "v": "validate",
    "sk": "skeleton",
    # Semantic aliases
    "dev": "serve",
    "check": "validate",
    "lint": "validate",
}

# Reverse mapping: canonical name → list of aliases
CANONICAL_TO_ALIASES: dict[str, list[str]] = {}
for alias, canonical in COMMAND_ALIASES.items():
    if canonical not in CANONICAL_TO_ALIASES:
        CANONICAL_TO_ALIASES[canonical] = []
    CANONICAL_TO_ALIASES[canonical].append(alias)

# =============================================================================
# QUICK START & SHORTCUTS CONFIG
# =============================================================================
# Featured commands shown in Quick Start section (command, description)
QUICK_START_COMMANDS: list[tuple[str, str]] = [
    ("bengal build", "Build your site"),
    ("bengal serve", "Start dev server with live reload"),
    ("bengal new site", "Create a new site"),
]

# Shortcuts shown in help - tuple of (aliases_display, canonical_name)
# Derived from CANONICAL_TO_ALIASES but with custom display formatting
SHORTCUTS_DISPLAY: list[tuple[str, str]] = [
    ("b", "build"),
    ("s, dev", "serve"),
    ("c", "clean"),
    ("v, check, lint", "validate"),
]


def get_aliases_for_command(cmd_name: str) -> list[str]:
    """
    Get all aliases for a canonical command name.

    Args:
        cmd_name: The canonical command name (e.g., 'build', 'serve')

    Returns:
        List of alias strings, or empty list if no aliases exist.

    Example:
        >>> get_aliases_for_command('build')
        ['b']
        >>> get_aliases_for_command('serve')
        ['s', 'dev']
    """
    return CANONICAL_TO_ALIASES.get(cmd_name, [])


def get_canonical_name(cmd_or_alias: str) -> str:
    """
    Get the canonical command name for an alias.

    If the input is already a canonical name (or not a known alias),
    returns the input unchanged.

    Args:
        cmd_or_alias: A command name or alias string

    Returns:
        The canonical command name.

    Example:
        >>> get_canonical_name('b')
        'build'
        >>> get_canonical_name('build')
        'build'
    """
    return COMMAND_ALIASES.get(cmd_or_alias, cmd_or_alias)


def _sanitize_help_text(text: str) -> str:
    """
    Remove Commands section from help text to avoid duplication.

    Click automatically generates a Commands section in group help output,
    so we remove any manually-written Commands section from docstrings
    to avoid showing duplicated information.

    Args:
        text: Raw help text from command/group docstring

    Returns:
        Sanitized help text with Commands section removed.
    """
    if not text:
        return ""

    lines = text.splitlines()
    result: list[str] = []
    in_commands = False
    for line in lines:
        if re.match(r"^\s*Commands:\s*$", line):
            in_commands = True
            continue
        if in_commands:
            if line.strip() == "":
                in_commands = False
            continue
        result.append(line)
    # Collapse leading/trailing blank lines
    return "\n".join(result).strip()


class BengalCommand(click.Command):
    """
    Custom Click command with themed help output.

    Extends Click's Command class to provide Bengal-branded help formatting
    using Rich console output with consistent styling.

    Features:
        - Bengal mascot in headers (ᓚᘏᗢ)
        - Themed options and arguments display
        - Automatic fallback to plain text for non-TTY

    Example:
        >>> @click.command(cls=BengalCommand)
        ... @click.option('--verbose', is_flag=True)
        ... def my_command(verbose):
        ...     '''My command description.'''
        ...     pass
    """

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Format help output using Bengal's themed CLIOutput.

        Renders command help with Bengal styling, including mascot header,
        formatted options table, and styled usage patterns.

        Args:
            ctx: Click context
            formatter: Click help formatter (used for fallback)
        """
        cli = CLIOutput()

        if cli.use_rich:
            cli.blank()
            cli.header(f"ᓚᘏᗢ  {ctx.command_path}")
            cli.blank()

            # Help text (sanitized to avoid duplicating Commands section from docstring)
            if self.help:
                sanitized = _sanitize_help_text(self.help)
                if sanitized:
                    if cli.use_rich:
                        cli.console.print(f"[dim]{sanitized}[/dim]")
                    else:
                        cli.info(sanitized)
                cli.blank()

            # Usage
            pieces = [ctx.command_path]
            if self.params:
                pieces.append("[dim][OPTIONS][/dim]")
            for param in self.params:
                if isinstance(param, click.Argument):
                    pieces.append(f"[info]{param.human_readable_name.upper()}[/info]")

            if cli.use_rich:
                cli.console.print(f"[header]Usage:[/header] {' '.join(pieces)}")
            else:
                cli.info(f"Usage: {' '.join(pieces)}")

            # Options
            options = [p for p in self.params if isinstance(p, click.Option)]
            if options:
                cli.subheader("Options:", trailing_blank=False)
                for param in options:
                    opts = "/".join(param.opts)
                    help_text = param.help or ""

                    # Add default value if present
                    if param.default is not None and not param.is_flag:
                        help_text += f" [dim](default: {param.default})[/dim]"

                    if cli.use_rich:
                        cli.console.print(f"  [info]{opts:<20}[/info] {help_text}")
                    else:
                        cli.info(f"  {opts:<20} {help_text}")
                cli.blank()

            # Arguments
            arguments = [p for p in self.params if isinstance(p, click.Argument)]
            if arguments:
                cli.subheader("Arguments:", trailing_blank=False)
                for param in arguments:
                    name = param.human_readable_name.upper()
                    help_text = getattr(param, "help", "") or ""  # type: ignore[attr-defined]
                    if cli.use_rich:
                        cli.console.print(f"  [info]{name:<20}[/info] {help_text}")
                    else:
                        cli.info(f"  {name:<20} {help_text}")
                cli.blank()
        else:
            # Fallback to Click's default formatting
            super().format_help(ctx, formatter)


class BengalGroup(click.Group):
    """
    Custom Click group with typo detection and themed help output.

    Extends Click's Group class to provide:
    - Fuzzy command matching with helpful suggestions for typos
    - Bengal-themed help output with Quick Start section
    - Alias display in shortcuts section
    - Filtered command list (hides aliases from main list)

    The group automatically uses BengalCommand for all subcommands.

    Example:
        >>> @click.group(cls=BengalGroup)
        ... def my_group():
        ...     '''My command group.'''
        ...     pass
    """

    # Use our custom command class by default
    command_class = BengalCommand

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """
        Format group help output using Bengal's themed CLIOutput.

        For the root group, displays:
        - Quick Start section with common commands
        - Shortcuts section showing all aliases
        - Filtered commands list (excluding aliases)

        Args:
            ctx: Click context
            formatter: Click help formatter (used for fallback)
        """
        cli = CLIOutput()

        if not cli.use_rich:
            # Fallback to Click's default formatting
            super().format_help(ctx, formatter)
            return

        # Help text (sanitized to avoid duplicating Commands section from docstring)
        if self.help:
            sanitized = _sanitize_help_text(self.help)
            if sanitized:
                if cli.use_rich:
                    cli.console.print(f"[dim]{sanitized}[/dim]")
                else:
                    cli.info(sanitized)
            cli.blank()

        # Quick Start section (styled like Options/Commands) - only for root command
        # Check if this is the root command (no parent or parent is None)
        if ctx.parent is None:
            cli.subheader("Quick Start:", leading_blank=False)
            for cmd, desc in QUICK_START_COMMANDS:
                if cli.use_rich:
                    cli.console.print(f"  [info]{cmd:<18}[/info] {desc}")
                else:
                    cli.info(f"  {cmd:<18} {desc}")
            cli.blank()

            # Show shortcuts section
            cli.subheader("Shortcuts:", leading_blank=False, trailing_blank=False)
            for aliases, canonical in SHORTCUTS_DISPLAY:
                # Calculate padding based on visible text width
                padding = 18 - len(aliases)
                if cli.use_rich:
                    # Style each alias as dim
                    styled_aliases = ", ".join(
                        f"[dim]{a.strip()}[/dim]" for a in aliases.split(",")
                    )
                    cli.console.print(f"  {styled_aliases}{' ' * padding} {canonical}")
                else:
                    cli.info(f"  {aliases:<18} {canonical}")
            cli.blank()

        # Usage pattern
        prog_name = ctx.command_path
        cli.console.print(
            f"[header]Usage:[/header] {prog_name} [dim][OPTIONS][/dim] [info]COMMAND[/info] [dim][ARGS]...[/dim]"
        )

        # Options
        if self.params:
            cli.subheader("Options:", trailing_blank=False)
            for param in self.params:
                opts = "/".join(param.opts)
                help_text = getattr(param, "help", "") or ""  # type: ignore[attr-defined]
                cli.console.print(f"  [info]{opts:<20}[/info] {help_text}")
            cli.blank()

        # Commands (filter out aliases to avoid clutter)
        commands = self.list_commands(ctx)
        if commands:
            cli.subheader("Commands:", trailing_blank=False)

            # For root bengal group, filter out aliases to reduce clutter
            if ctx.command_path == "bengal":
                # These are aliases we register - skip them in the main list
                # The user already sees them in the Shortcuts section
                skip_names = {"b", "s", "c", "v", "dev", "check", "lint"}
                shown_commands = [
                    name
                    for name in commands
                    if name not in skip_names
                    and (cmd := self.get_command(ctx, name)) is not None
                    and not cmd.hidden
                ]
            else:
                shown_commands = [
                    name
                    for name in commands
                    if (cmd := self.get_command(ctx, name)) is not None and not cmd.hidden
                ]

            for name in shown_commands:
                cmd = self.get_command(ctx, name)
                if cmd:
                    help_text = cmd.get_short_help_str(limit=60)
                    cli.console.print(f"  [info]{name:<12}[/info] {help_text}")
            cli.blank()

        # Don't let Click write anything else
        formatter.write("")

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        """
        Resolve command with fuzzy matching for typos.

        Extends Click's command resolution to catch unknown commands
        and suggest similar alternatives using difflib matching.

        Args:
            ctx: Click context
            args: Command-line arguments

        Returns:
            Tuple of (command_name, command, remaining_args)

        Raises:
            SystemExit: If command not found, after showing suggestions
        """
        try:
            return super().resolve_command(ctx, args)
        except click.exceptions.UsageError as e:
            # Check if it's an unknown command error
            if "No such command" in str(e) and args:
                unknown_cmd = args[0]
                suggestions = self._get_similar_commands(unknown_cmd)

                if suggestions:
                    # Themed error output using CLIOutput
                    cli = CLIOutput()
                    cli.error_header(f"Unknown command '{unknown_cmd}'.", mouse=True)
                    if cli.use_rich:
                        cli.console.print("[header]Did you mean one of these?[/header]")
                        for suggestion in suggestions:
                            # Show alias info if relevant
                            aliases = get_aliases_for_command(suggestion)
                            if aliases:
                                alias_hint = f" [dim](or: {', '.join(aliases)})[/dim]"
                            else:
                                alias_hint = ""
                            cli.console.print(
                                f"  [info]•[/info] [phase]{suggestion}[/phase]{alias_hint}"
                            )
                    else:
                        cli.info("Did you mean one of these?")
                        for suggestion in suggestions:
                            cli.info(f"  • {suggestion}")
                    cli.blank()
                    cli.tip("Run 'bengal --help' to see all commands and shortcuts.")
                    cli.blank()
                    raise SystemExit(2) from None

                # Re-raise original error if no suggestions
                # Use themed single-line error
                cli = CLIOutput()
                cli.error_header(f"Unknown command '{unknown_cmd}'.", mouse=True)
                cli.tip("Run 'bengal --help' to see all commands and shortcuts.")
                raise SystemExit(2) from None

            # Re-raise original error if no suggestions
            raise

    def _get_similar_commands(self, unknown_cmd: str, max_suggestions: int = 3) -> list[str]:
        """
        Find similar command names using string similarity.

        Uses difflib's get_close_matches to find commands that are
        similar to the unknown input, prioritizing canonical names
        over aliases.

        Args:
            unknown_cmd: The unrecognized command string
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of similar canonical command names.
        """
        from difflib import get_close_matches

        # Get all available commands, but prefer canonical names over aliases
        available_commands = list(self.commands.keys())

        # Filter to prefer canonical commands and avoid suggesting aliases
        # (user will see aliases in the output anyway)
        canonical_commands = [cmd for cmd in available_commands if cmd not in COMMAND_ALIASES]

        # Use difflib for fuzzy matching against canonical commands first
        matches = get_close_matches(
            unknown_cmd,
            canonical_commands,
            n=max_suggestions,
            cutoff=0.5,  # Slightly lower threshold for better suggestions
        )

        # If no matches, try aliases too
        if not matches:
            matches = get_close_matches(
                unknown_cmd,
                available_commands,
                n=max_suggestions,
                cutoff=0.5,
            )
            # Convert aliases to canonical names and deduplicate while preserving order
            matches = list(dict.fromkeys(get_canonical_name(m) for m in matches))

        return matches[:max_suggestions]
