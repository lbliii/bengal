import click

from bengal.utils.cli_output import CLIOutput


class BengalCommand(click.Command):
    """Custom Click command with themed help output."""

    def format_help(self, ctx, formatter):
        """Format help output using our themed CLIOutput."""
        cli = CLIOutput()

        if cli.use_rich:
            cli.blank()
            cli.header(f"ᓚᘏᗢ  {ctx.command_path}")
            cli.blank()

            # Help text
            if self.help:
                cli.info(self.help)
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
            cli.blank()

            # Options
            options = [p for p in self.params if isinstance(p, click.Option)]
            if options:
                cli.header("Options:")
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
                cli.header("Arguments:")
                for param in arguments:
                    name = param.human_readable_name.upper()
                    help_text = param.help or ""
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

    def format_help(self, ctx, formatter):
        """Format help output using our themed CLIOutput."""
        cli = CLIOutput()

        if not cli.use_rich:
            # Fallback to Click's default formatting
            super().format_help(ctx, formatter)
            return

        # Help text
        if self.help:
            cli.info(self.help)
            cli.blank()

        # Quick Start section (styled like Options/Commands) - only for root
        if ctx.command_path == "bengal":
            cli.header("Quick Start:", leading_blank=False)
            if cli.use_rich:
                cli.console.print("  [info]bengal site build[/info]     Build your site")
                cli.console.print(
                    "  [info]bengal site serve[/info]     Start dev server with live reload"
                )
                cli.console.print("  [info]bengal new site[/info]       Create a new site")
            else:
                cli.info("  bengal site build     Build your site")
                cli.info("  bengal site serve     Start dev server with live reload")
                cli.info("  bengal new site       Create a new site")
            cli.blank()
            cli.info("For more commands: bengal --help")
            cli.blank()

        # Usage pattern
        prog_name = ctx.command_path
        cli.console.print(
            f"[header]Usage:[/header] {prog_name} [dim][OPTIONS][/dim] [info]COMMAND[/info] [dim][ARGS]...[/dim]"
        )
        cli.blank()

        # Options
        if self.params:
            cli.header("Options:")
            for param in self.params:
                opts = "/".join(param.opts)
                help_text = param.help or ""
                cli.console.print(f"  [info]{opts:<20}[/info] {help_text}")
            cli.blank()

        # Commands
        commands = self.list_commands(ctx)
        if commands:
            cli.header("Commands:")
            for name in commands:
                cmd = self.get_command(ctx, name)
                if cmd and not cmd.hidden:
                    help_text = cmd.get_short_help_str(limit=60)
                    cli.console.print(f"  [info]{name:<12}[/info] {help_text}")
            cli.blank()

        # Don't let Click write anything else
        formatter.write("")

    def resolve_command(self, ctx, args):
        """Resolve command with fuzzy matching for typos."""
        try:
            return super().resolve_command(ctx, args)
        except click.exceptions.UsageError as e:
            # Check if it's an unknown command error
            if "No such command" in str(e) and args:
                unknown_cmd = args[0]
                suggestions = self._get_similar_commands(unknown_cmd)

                if suggestions:
                    # Format error message with suggestions
                    msg = f"Unknown command '{unknown_cmd}'.\n\n"
                    msg += "Did you mean one of these?\n"
                    for _i, suggestion in enumerate(suggestions, 1):
                        msg += f"  • {click.style(suggestion, fg='cyan', bold=True)}\n"
                    msg += (
                        f"\nRun '{click.style('bengal --help', fg='yellow')}' to see all commands."
                    )
                    raise click.exceptions.UsageError(msg) from e

                # Re-raise original error if no suggestions
                raise

            # Re-raise original error if no suggestions
            raise

    def _get_similar_commands(self, unknown_cmd: str, max_suggestions: int = 3):
        """Find similar command names using simple string similarity."""
        from difflib import get_close_matches

        available_commands = list(self.commands.keys())

        # Use difflib for fuzzy matching
        matches = get_close_matches(
            unknown_cmd,
            available_commands,
            n=max_suggestions,
            cutoff=0.6,  # 60% similarity threshold
        )

        return matches
