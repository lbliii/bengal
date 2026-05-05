"""
Bengal CLI — powered by milo-cli.

This module defines Bengal's CLI surface area using milo's type-annotated
command framework. Milo owns command registration, structured output,
MCP server mode, completions, and llms.txt generation.

Surface area (12 groups, 4 tiers):

    Tier 1 — Core workflow (daily use):
        build, serve, clean, check, audit, fix, new

    Tier 2 — Feature groups (weekly use):
        config, theme, content, version, i18n

    Tier 3 — Analysis & debugging (power users):
        inspect, debug

    Tier 4 — Infrastructure (rare):
        cache, codemod, upgrade
"""

from __future__ import annotations

import sys
from typing import Any

from milo import CLI

from bengal import __version__

# ---------------------------------------------------------------------------
# Root CLI
# ---------------------------------------------------------------------------


class BengalCLI(CLI):
    """Milo CLI that routes compatibility output through CLIOutput."""

    _ROOT_HELP_SECTIONS = (
        {
            "title": "Core workflow",
            "commands": ("build", "serve", "check", "audit", "fix", "clean", "health"),
        },
        {"title": "Create", "commands": ("new",)},
        {
            "title": "Site systems",
            "commands": ("config", "theme", "content", "version", "i18n", "plugin"),
        },
        {"title": "Inspect and debug", "commands": ("inspect", "debug")},
        {"title": "Infrastructure", "commands": ("cache", "upgrade", "codemod")},
    )

    def run(self, argv: list[str] | None = None) -> Any:
        """Run the CLI, rendering root help through Bengal's Kida template."""
        resolved_argv = list(sys.argv[1:] if argv is None else argv)
        if not resolved_argv:
            self._parser = self.build_parser()
            self._format_root_help()
            return None
        if "--help" in resolved_argv or "-h" in resolved_argv:
            self._parser = self.build_parser()
            self._format_help_for_argv(resolved_argv)
            return None
        if self._render_unknown_command_if_needed(resolved_argv):
            sys.exit(2)
        return super().run(resolved_argv)

    def _consume_result(self, result: Any, *, emit_progress: bool = True) -> Any:
        """Consume Milo generator progress through Bengal's renderer bridge."""
        from milo.streaming import consume_generator, is_generator_result

        if not is_generator_result(result):
            return result

        progress_list, final_value = consume_generator(result)
        if emit_progress:
            from bengal.output import get_cli_output

            bridge = get_cli_output()
            for progress in progress_list:
                bridge.progress_status(
                    progress.status,
                    step=progress.step,
                    total=progress.total,
                )
        return final_value

    def _write_command_output(
        self,
        result: Any,
        fmt: str,
        output_file: str,
        *,
        force: bool = False,
    ) -> None:
        """Write Milo command results through CLIOutput when targeting stdout."""
        if output_file:
            from pathlib import Path

            from milo.output import format_output

            from bengal.output import get_cli_output
            from bengal.utils.io.atomic_write import atomic_write_text

            output_path = Path(output_file)
            if output_path.exists() and not force:
                get_cli_output().raw(
                    f"error: output file {output_file!r} already exists. Use --force to overwrite.",
                    stream="stderr",
                    level=None,
                )
                sys.exit(1)
            atomic_write_text(output_path, format_output(result, fmt=fmt) + "\n")
            return

        from milo.output import format_output

        from bengal.output import get_cli_output

        get_cli_output().raw(format_output(result, fmt=fmt), level=None)
        return

    def _resolve_command_execution(self, args: Any) -> Any:
        """Resolve commands, rendering group help through Bengal templates."""
        from milo.commands import (
            CommandExecution,
            LazyCommandDef,
            LazyImportError,
            ResolvedGroup,
            ResolvedNothing,
        )

        result = self._resolve_command_from_args(args)

        if isinstance(result, ResolvedGroup):
            self._format_group_help(result.group, result.prog)
            return None

        if isinstance(result, ResolvedNothing):
            attempted = result.attempted
            if attempted:
                suggestion = self.suggest_command(attempted)
                if suggestion:
                    self._write_stderr(
                        f"Unknown command: {attempted!r}. Did you mean {suggestion!r}?\n"
                    )
                    return None
            self._format_root_help()
            return None

        found = result.command
        try:
            cmd = found.resolve() if isinstance(found, LazyCommandDef) else found
        except LazyImportError as exc:
            self._write_stderr(f"error: {exc}\n")
            self._write_stderr(
                f"  hint: Check that {exc.import_path!r} is installed and importable.\n"
            )
            return None
        confirm_msg = getattr(found, "confirm", "") or getattr(cmd, "confirm", "")
        return CommandExecution(found=found, command=cmd, fmt=result.fmt, confirm_msg=confirm_msg)

    @staticmethod
    def _write_stderr(message: str) -> None:
        """Write CLI diagnostics through Bengal's output bridge."""
        from bengal.output import get_cli_output

        get_cli_output().raw(message.rstrip("\n"), stream="stderr", level=None)

    def _format_root_help(self) -> None:
        """Render root help from the command registry with Bengal's CLI template."""
        from bengal.output import get_cli_output

        commands = self._root_help_commands()
        sections = []
        included: set[str] = set()
        for section in self._ROOT_HELP_SECTIONS:
            entries = [commands[name] for name in section["commands"] if name in commands]
            if entries:
                included.update(entry["name"] for entry in entries)
                sections.append({"title": section["title"], "commands": entries})

        remaining = [entry for name, entry in commands.items() if name not in included]
        if remaining:
            sections.append({"title": "Other", "commands": remaining})

        get_cli_output().render_write(
            "cli_root_help.kida",
            name=self.name,
            version=self.version,
            brand_mark=self._brand_mark(),
            description=self.description,
            sections=sections,
            options=self._root_help_options(),
            examples=[
                {"command": "bengal build --strict", "description": "Build for CI"},
                {
                    "command": "bengal check --templates",
                    "description": "Validate content and templates",
                },
                {
                    "command": "bengal --llms-txt",
                    "description": "Show agent-readable CLI reference",
                },
            ],
        )

    def _format_group_help(self, group: Any, prog: str) -> None:
        """Render group help from a Milo group using Bengal's CLI template."""
        from bengal.output import get_cli_output

        commands = [
            self._help_entry(cmd.name, cmd.description, cmd.aliases, kind="command")
            for cmd in group.commands.values()
            if not getattr(cmd, "hidden", False)
        ]
        commands.extend(
            self._help_entry(sub.name, sub.description, sub.aliases, kind="group")
            for sub in group.groups.values()
            if not getattr(sub, "hidden", False)
        )
        get_cli_output().render_write(
            "cli_group_help.kida",
            prog=prog,
            brand_mark=self._brand_mark(),
            description=group.description,
            commands=commands,
        )

    def _format_command_help(self, command_ref: Any, prog: str) -> None:
        """Render leaf command help from Milo's command schema."""
        from milo.commands import LazyCommandDef, LazyImportError

        from bengal.output import get_cli_output

        try:
            command = (
                command_ref.resolve() if isinstance(command_ref, LazyCommandDef) else command_ref
            )
        except LazyImportError as exc:
            self._write_stderr(f"error: {exc}\n")
            self._write_stderr(
                f"  hint: Check that {exc.import_path!r} is installed and importable.\n"
            )
            return

        get_cli_output().render_write(
            "cli_command_help.kida",
            prog=prog,
            brand_mark=self._brand_mark(),
            description=command.description,
            options=self._command_help_options(command.schema),
            examples=[
                {
                    "command": example.command,
                    "description": example.description,
                }
                for example in getattr(command, "examples", ()) or ()
            ],
        )

    def _format_help_for_argv(self, argv: list[str]) -> None:
        """Render root, group, or leaf help for a help-bearing invocation."""
        tokens = [token for token in argv if token not in {"--help", "-h"}]
        if not tokens:
            self._format_root_help()
            return

        first = tokens[0]
        command = self._find_command(first, self._commands)
        if command is not None:
            canonical = command.name
            self._format_command_help(command, f"{self.name} {canonical}")
            return

        group = self._find_group(first, self._groups)
        if group is None:
            self._format_root_help()
            return

        group_name = group.name
        if len(tokens) == 1:
            self._format_group_help(group, f"{self.name} {group_name}")
            return

        child = self._find_command(tokens[1], group.commands)
        if child is None:
            self._format_group_help(group, f"{self.name} {group_name}")
            return

        self._format_command_help(child, f"{self.name} {group_name} {child.name}")

    def _render_unknown_command_if_needed(self, argv: list[str]) -> bool:
        """Render common command-choice errors before argparse emits raw usage."""
        tokens = self._extract_command_tokens(argv)
        if not tokens:
            return False

        first = tokens[0]
        if first.startswith("-"):
            return False

        command = self._find_command(first, self._commands)
        if command is not None:
            return False

        group = self._find_group(first, self._groups)
        if group is None:
            suggestion = self._suggest_name(first, self._commands, self._groups)
            self._format_command_error(
                title="Unknown command",
                message=f"Unknown command: {first!r}",
                suggestion=f"Did you mean {suggestion!r}?"
                if suggestion
                else "Run `bengal --help`.",
                commands=list(self._root_help_commands().values()),
            )
            return True

        if len(tokens) < 2 or tokens[1].startswith("-"):
            return False

        child = self._find_command(tokens[1], group.commands)
        if child is not None:
            return False

        suggestion = self._suggest_name(tokens[1], group.commands)
        self._format_command_error(
            title=f"Unknown {group.name} command",
            message=f"Unknown command: {group.name} {tokens[1]!r}",
            suggestion=(
                f"Did you mean `{self.name} {group.name} {suggestion}`?"
                if suggestion
                else f"Run `{self.name} {group.name} --help`."
            ),
            commands=[
                self._help_entry(cmd.name, cmd.description, cmd.aliases, kind="command")
                for cmd in group.commands.values()
                if not getattr(cmd, "hidden", False)
            ],
        )
        return True

    @staticmethod
    def _extract_command_tokens(argv: list[str]) -> list[str]:
        """Return likely command tokens after leading global options."""
        value_options = {"--output-file", "-o", "--completions"}
        flag_options = {
            "--force",
            "--llms-txt",
            "--mcp",
            "--mcp-install",
            "--mcp-uninstall",
            "--no-color",
            "--quiet",
            "--verbose",
            "--version",
            "-n",
            "-q",
            "-v",
        }
        index = 0
        while index < len(argv):
            token = argv[index]
            if token == "--":
                return argv[index + 1 :]
            if token in value_options:
                index += 2
                continue
            if any(
                token.startswith(f"{option}=")
                for option in value_options
                if option.startswith("--")
            ):
                index += 1
                continue
            if token in flag_options or (token.startswith("-v") and set(token[1:]) == {"v"}):
                index += 1
                continue
            return argv[index:]
        return []

    def _format_command_error(
        self,
        *,
        title: str,
        message: str,
        suggestion: str,
        commands: list[dict[str, Any]],
    ) -> None:
        """Render a command error through Bengal's Kida template on stderr."""
        from bengal.output import get_cli_output

        cli = get_cli_output()
        rendered = cli.render(
            "command_error.kida",
            title=title,
            message=message,
            suggestion=suggestion,
            commands=commands,
        )
        cli.raw(rendered.rstrip("\n"), stream="stderr", level=None)

    @staticmethod
    def _suggest_name(
        name: str,
        commands: dict[str, Any],
        groups: dict[str, Any] | None = None,
    ) -> str | None:
        """Suggest a command or group name from names and aliases."""
        import difflib

        choices: list[str] = []
        for entry in commands.values():
            choices.append(entry.name)
            choices.extend(getattr(entry, "aliases", ()))
        for entry in (groups or {}).values():
            choices.append(entry.name)
            choices.extend(getattr(entry, "aliases", ()))
        matches = difflib.get_close_matches(name, choices, n=1, cutoff=0.6)
        return matches[0] if matches else None

    @staticmethod
    def _find_command(name: str, commands: dict[str, Any]) -> Any | None:
        """Find a command by name or alias."""
        if name in commands:
            return commands[name]
        for command in commands.values():
            if name in getattr(command, "aliases", ()):
                return command
        return None

    @staticmethod
    def _find_group(name: str, groups: dict[str, Any]) -> Any | None:
        """Find a group by name or alias."""
        if name in groups:
            return groups[name]
        for group in groups.values():
            if name in getattr(group, "aliases", ()):
                return group
        return None

    @staticmethod
    def _brand_mark() -> str:
        """Return Bengal's terminal logo, compacting for very narrow terminals."""
        import shutil

        width = shutil.get_terminal_size(fallback=(80, 24)).columns
        return "ᗢ" if width < 48 else "ᓚᘏᗢ"

    def _root_help_commands(self) -> dict[str, dict[str, Any]]:
        """Return visible top-level commands and groups keyed by name."""
        commands: dict[str, dict[str, Any]] = {}
        for cmd in self._commands.values():
            if not getattr(cmd, "hidden", False):
                commands[cmd.name] = self._help_entry(
                    cmd.name, cmd.description, cmd.aliases, kind="command"
                )
        for group in self._groups.values():
            if not group.hidden:
                commands[group.name] = self._help_entry(
                    group.name, group.description, group.aliases, kind="group"
                )
        return commands

    def _root_help_options(self) -> list[dict[str, str]]:
        """Return visible root parser options for help rendering."""
        import argparse

        options = []
        for action in self._parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                continue
            flags = ", ".join(action.option_strings) if action.option_strings else ""
            if not flags:
                continue
            options.append(
                {
                    "flags": flags,
                    "help": action.help or "",
                    "metavar": action.metavar or "",
                    "label": f"{flags} {action.metavar}".strip() if action.metavar else flags,
                    "label_len": len(f"{flags} {action.metavar}".strip())
                    if action.metavar
                    else len(flags),
                    "padding": " "
                    * max(
                        28
                        - (
                            len(f"{flags} {action.metavar}".strip())
                            if action.metavar
                            else len(flags)
                        ),
                        1,
                    ),
                }
            )
        return options

    def _command_help_options(self, schema: dict[str, Any]) -> list[dict[str, Any]]:
        """Return template-friendly option entries from a Milo command schema."""
        options = [
            self._option_entry("-h, --help", "show this help message and exit"),
        ]
        properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
        required = set(schema.get("required", ())) if isinstance(schema, dict) else set()
        for name, spec in properties.items():
            if not isinstance(spec, dict):
                continue
            flag = f"--{name.replace('_', '-')}"
            help_text = str(spec.get("description", ""))
            if name in required:
                help_text = f"{help_text} (required)" if help_text else "required"
            default = spec.get("default", None)
            if default not in (None, "", False):
                help_text = (
                    f"{help_text} (default: {default})" if help_text else f"default: {default}"
                )
            options.append(self._option_entry(flag, help_text))
        options.append(self._option_entry("--format", "Output format (default: plain)"))
        return options

    @staticmethod
    def _option_entry(label: str, help_text: str) -> dict[str, Any]:
        """Build an aligned option row for CLI help templates."""
        return {
            "label": label,
            "help": help_text,
            "label_len": len(label),
            "padding": " " * max(28 - len(label), 1),
        }

    @staticmethod
    def _help_entry(
        name: str,
        description: str,
        aliases: tuple[str, ...] | list[str],
        *,
        kind: str,
    ) -> dict[str, Any]:
        """Build a template-friendly command entry."""
        alias_text = f" ({', '.join(aliases)})" if aliases else ""
        label = f"{name}{alias_text}"
        return {
            "name": name,
            "description": description,
            "aliases": tuple(aliases),
            "kind": kind,
            "label": label,
            "label_len": len(label),
            "padding": " " * max(24 - len(label), 1),
        }


cli = BengalCLI(
    name="bengal",
    description="Static site generator for Python teams — every layer pure Python, scales with your cores",
    version=__version__,
)


# ---------------------------------------------------------------------------
# Tier 1 — Core workflow (daily use, top-level with short aliases)
# ---------------------------------------------------------------------------

cli.lazy_command(
    "build",
    import_path="bengal.cli.milo_commands.build:build",
    description="Build your site",
    aliases=("b",),
    annotations={"destructiveHint": False, "idempotentHint": True},
    display_result=False,
)

cli.lazy_command(
    "serve",
    import_path="bengal.cli.milo_commands.serve:serve",
    description="Start dev server with hot reload",
    aliases=("s", "dev"),
    annotations={"readOnlyHint": True},
    display_result=False,
)

cli.lazy_command(
    "clean",
    import_path="bengal.cli.milo_commands.clean:clean",
    description="Clean output directory and cache",
    aliases=("c",),
    annotations={"destructiveHint": True, "idempotentHint": True},
    display_result=False,
)

cli.lazy_command(
    "check",
    import_path="bengal.cli.milo_commands.check:check",
    description="Validate your site",
    aliases=("v",),
    annotations={"readOnlyHint": True},
    display_result=False,
)

cli.lazy_command(
    "audit",
    import_path="bengal.cli.milo_commands.audit:audit",
    description="Audit generated artifacts",
    annotations={"readOnlyHint": True},
    display_result=False,
)

cli.lazy_command(
    "health",
    import_path="bengal.cli.milo_commands.check:check",
    description="Legacy alias for check",
    annotations={"readOnlyHint": True},
    display_result=False,
)

cli.lazy_command(
    "fix",
    import_path="bengal.cli.milo_commands.fix:fix",
    description="Auto-fix issues",
    annotations={"destructiveHint": True},
    display_result=False,
)

# `new` group — create sites, themes, content
new = cli.group("new", description="Create new site, theme, or content", aliases=("n",))

for name, desc in [
    ("site", "Create a new Bengal site"),
    ("theme", "Create a new theme scaffold"),
    ("page", "Create a new content page"),
    ("layout", "Create a new layout template"),
    ("partial", "Create a new partial template"),
]:
    new.lazy_command(
        name,
        import_path=f"bengal.cli.milo_commands.new:new_{name}",
        description=desc,
        annotations={"destructiveHint": True, "idempotentHint": False},
        display_result=False,
    )

new.lazy_command(
    "content-type",
    import_path="bengal.cli.milo_commands.new:new_content_type",
    description="Create a new ContentTypeStrategy scaffold",
    annotations={"destructiveHint": True, "idempotentHint": False},
    display_result=False,
)

# ---------------------------------------------------------------------------
# Tier 2 — Feature groups (weekly use)
# ---------------------------------------------------------------------------

# --- config ---
config = cli.group("config", description="Configuration management")

config.lazy_command(
    "show",
    import_path="bengal.cli.milo_commands.config:config_show",
    description="Display merged configuration",
    annotations={"readOnlyHint": True},
    display_result=False,
)

config.lazy_command(
    "doctor",
    import_path="bengal.cli.milo_commands.config:config_doctor",
    description="Validate configuration",
    annotations={"readOnlyHint": True},
    display_result=False,
)

config.lazy_command(
    "diff",
    import_path="bengal.cli.milo_commands.config:config_diff",
    description="Compare environments",
    annotations={"readOnlyHint": True},
    display_result=False,
)

config.lazy_command(
    "init",
    import_path="bengal.cli.milo_commands.config:config_init",
    description="Create configuration structure",
    annotations={"destructiveHint": True, "idempotentHint": False},
    display_result=False,
)

config.lazy_command(
    "inspect",
    import_path="bengal.cli.milo_commands.config:config_inspect",
    description="Advanced config inspection with origin tracking",
    annotations={"readOnlyHint": True},
    display_result=False,
)

# --- theme ---
theme = cli.group("theme", description="Theme development, directives, and assets")

for name, desc in [
    ("list", "List available themes"),
    ("info", "Show theme details"),
    ("discover", "List swizzlable templates"),
    ("swizzle", "Copy template from theme to project"),
    ("install", "Install theme from PyPI"),
    ("validate", "Validate theme directory structure"),
    ("new", "Create new theme scaffold"),
    ("debug", "Debug theme resolution and inheritance"),
    ("directives", "List available directives"),
    ("test", "Render a directive in isolation"),
    ("assets", "Build CSS/JS assets"),
]:
    theme.lazy_command(
        name,
        import_path=f"bengal.cli.milo_commands.theme:theme_{name}",
        description=desc,
        annotations={
            "readOnlyHint": name
            in {"list", "info", "discover", "validate", "debug", "directives", "test"},
            "destructiveHint": name in {"swizzle", "install", "new", "assets"},
            "idempotentHint": name in {"assets", "validate"},
        },
        display_result=False,
    )

# --- content ---
content = cli.group("content", description="Content sources and collections")

for name, desc in [
    ("sources", "List configured content sources"),
    ("fetch", "Fetch remote content"),
    ("collections", "List defined content collections"),
    ("schemas", "Validate content against schemas"),
]:
    content.lazy_command(
        name,
        import_path=f"bengal.cli.milo_commands.content:content_{name}",
        description=desc,
        annotations={
            "readOnlyHint": name in {"sources", "collections", "schemas"},
            "destructiveHint": name == "fetch",
            "idempotentHint": name in {"sources", "collections", "schemas"},
        },
        display_result=False,
    )

# --- version ---
version = cli.group("version", description="Documentation versioning")

for name, desc in [
    ("list", "List configured versions"),
    ("info", "Show version details"),
    ("create", "Create a version snapshot"),
    ("diff", "Compare versions"),
]:
    version.lazy_command(
        name,
        import_path=f"bengal.cli.milo_commands.version:version_{name}",
        description=desc,
        annotations={
            "readOnlyHint": name in {"list", "info", "diff"},
            "destructiveHint": name == "create",
            "idempotentHint": name in {"list", "info", "diff"},
        },
        display_result=False,
    )

# --- i18n ---
i18n = cli.group("i18n", description="Internationalization (PO/MO)")

for name, desc in [
    ("init", "Initialize locale directories"),
    ("extract", "Extract translatable strings"),
    ("compile", "Compile PO to MO files"),
    ("sync", "Sync PO files with current keys"),
    ("status", "Show translation coverage"),
]:
    i18n.lazy_command(
        name,
        import_path=f"bengal.cli.milo_commands.i18n:i18n_{name}",
        description=desc,
        annotations={
            "readOnlyHint": name == "status",
            "destructiveHint": name in {"init", "extract", "compile", "sync"},
            "idempotentHint": name in {"status", "extract", "compile", "sync"},
        },
        display_result=False,
    )

# --- plugin ---
plugin = cli.group("plugin", description="Plugin discovery and readiness", aliases=("plugins",))

for name, desc in [
    ("list", "List installed Bengal plugins"),
    ("info", "Show plugin capability readiness"),
    ("validate", "Validate plugin capability wiring"),
]:
    plugin.lazy_command(
        name,
        import_path=f"bengal.cli.milo_commands.plugin:plugin_{name}",
        description=desc,
        annotations={"readOnlyHint": True},
        display_result=False,
    )

# ---------------------------------------------------------------------------
# Tier 3 — Analysis & debugging (power users)
# ---------------------------------------------------------------------------

# --- inspect ---
inspect_group = cli.group("inspect", description="Analyze and inspect your site")

for name, desc in [
    ("page", "Explain how a page is built"),
    ("links", "Check internal and external links"),
    ("graph", "Analyze site structure and link graph"),
    ("perf", "Show build performance metrics"),
]:
    inspect_group.lazy_command(
        name,
        import_path=f"bengal.cli.milo_commands.inspect:inspect_{name}",
        description=desc,
        annotations={"readOnlyHint": True},
        display_result=False,
    )

# --- debug ---
debug = cli.group("debug", description="Debug builds and dependencies")

for name, desc in [
    ("incremental", "Debug incremental rebuild decisions"),
    ("delta", "Compare builds and identify changes"),
    ("deps", "Visualize dependency graph"),
    ("migrate", "Preview or execute content migrations"),
    ("sandbox", "Test directives in isolation"),
]:
    debug.lazy_command(
        name,
        import_path=f"bengal.cli.milo_commands.debug:debug_{name}",
        description=desc,
        annotations={
            "readOnlyHint": name in {"incremental", "delta", "deps", "sandbox"},
            "destructiveHint": name == "migrate",
        },
        display_result=False,
    )

# ---------------------------------------------------------------------------
# Tier 4 — Infrastructure (rare)
# ---------------------------------------------------------------------------

# --- cache ---
cache = cli.group("cache", description="CI cache management")

cache.lazy_command(
    "inputs",
    import_path="bengal.cli.milo_commands.cache:cache_inputs",
    description="List build input patterns for CI cache keys",
    annotations={"readOnlyHint": True},
    display_result=False,
)

cache.lazy_command(
    "hash",
    import_path="bengal.cli.milo_commands.cache:cache_hash",
    description="Compute deterministic hash of build inputs",
    annotations={"readOnlyHint": True},
    display_result=False,
)

# --- standalone ---
cli.lazy_command(
    "upgrade",
    import_path="bengal.cli.milo_commands.upgrade:upgrade",
    description="Check for and install Bengal updates",
    annotations={"destructiveHint": True},
    display_result=False,
)

cli.lazy_command(
    "codemod",
    import_path="bengal.cli.milo_commands.codemod:codemod",
    description="Run automated code migrations",
    annotations={"destructiveHint": True},
    display_result=False,
)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run() -> None:
    """Entry point for the bengal console script."""
    try:
        cli.run()
    except KeyboardInterrupt:
        from bengal.output import get_cli_output

        get_cli_output().interrupted()
        sys.exit(130)
