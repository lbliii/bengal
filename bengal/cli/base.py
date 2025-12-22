from __future__ import annotations

import re

import click

from bengal.output import CLIOutput

# =============================================================================
# ALIAS REGISTRY
# =============================================================================
# Maps aliases to their canonical command names for help and typo detection

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


def get_aliases_for_command(cmd_name: str) -> list[str]:
    """Get all aliases for a canonical command name."""
    return CANONICAL_TO_ALIASES.get(cmd_name, [])


def get_canonical_name(cmd_or_alias: str) -> str:
    """Get the canonical command name for an alias (or return as-is if not an alias)."""
    return COMMAND_ALIASES.get(cmd_or_alias, cmd_or_alias)


def _sanitize_help_text(text: str) -> str:
    """
    Remove Commands section from help text to avoid duplication.

    Click automatically generates a Commands section, so we remove it
    from the docstring to avoid showing it twice.
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
    """Custom Click command with themed help output."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Format help output using our themed CLIOutput."""
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
    """Custom Click group with typo detection and themed help output."""

    # Use our custom command class by default
    command_class = BengalCommand

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Format help output using our themed CLIOutput."""
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
            if cli.use_rich:
                cli.console.print("  [info]bengal build[/info]          Build your site")
                cli.console.print(
                    "  [info]bengal serve[/info]          Start dev server with live reload"
                )
                cli.console.print("  [info]bengal new site[/info]       Create a new site")
            else:
                cli.info("  bengal build          Build your site")
                cli.info("  bengal serve          Start dev server with live reload")
                cli.info("  bengal new site       Create a new site")
            cli.blank()

            # Show shortcuts section
            cli.subheader("Shortcuts:", leading_blank=False, trailing_blank=False)
            if cli.use_rich:
                cli.console.print("  [dim]b[/dim]                      build")
                cli.console.print("  [dim]s[/dim], [dim]dev[/dim]               serve")
                cli.console.print("  [dim]c[/dim]                      clean")
                cli.console.print("  [dim]v[/dim], [dim]check[/dim], [dim]lint[/dim]      validate")
            else:
                cli.info("  b                      build")
                cli.info("  s, dev                 serve")
                cli.info("  c                      clean")
                cli.info("  v, check, lint         validate")
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
        """Resolve command with fuzzy matching for typos."""
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
        """Find similar command names using simple string similarity."""
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
