"""
Bengal CLI — powered by milo-cli.

This module defines the new CLI surface area using milo's type-annotated
command framework. It replaces the Click-based CLI with a cleaner 4-tier
hierarchy and gains MCP server, structured output, and llms.txt for free.

Surface area (12 groups, 4 tiers):

    Tier 1 — Core workflow (daily use):
        build, serve, clean, check, audit, fix, new

    Tier 2 — Feature groups (weekly use):
        config, theme, content, version, i18n

    Tier 3 — Analysis & debugging (power users):
        inspect, debug

    Tier 4 — Infrastructure (rare):
        cache, codemod, upgrade, provenance
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

    def _consume_result(self, result: Any, *, emit_progress: bool = True) -> Any:
        """Consume Milo generator progress through Bengal's renderer bridge."""
        from milo.streaming import consume_generator, is_generator_result

        if not is_generator_result(result):
            return result

        progress_list, final_value = consume_generator(result)
        if emit_progress:
            from bengal.cli.utils.output import get_cli_output

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
            return super()._write_command_output(result, fmt, output_file, force=force)

        from milo.output import format_output

        from bengal.cli.utils.output import get_cli_output

        get_cli_output().raw(format_output(result, fmt=fmt), level=None)
        return None


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
    display_result=False,
)

cli.lazy_command(
    "serve",
    import_path="bengal.cli.milo_commands.serve:serve",
    description="Start dev server with hot reload",
    aliases=("s", "dev"),
    display_result=False,
)

cli.lazy_command(
    "clean",
    import_path="bengal.cli.milo_commands.clean:clean",
    description="Clean output directory and cache",
    aliases=("c",),
    display_result=False,
)

cli.lazy_command(
    "check",
    import_path="bengal.cli.milo_commands.check:check",
    description="Validate your site",
    aliases=("v",),
    display_result=False,
)

cli.lazy_command(
    "audit",
    import_path="bengal.cli.milo_commands.audit:audit",
    description="Audit generated artifacts",
    display_result=False,
)

cli.lazy_command(
    "health",
    import_path="bengal.cli.milo_commands.check:check",
    description="Legacy alias for check",
    display_result=False,
)

cli.lazy_command(
    "fix",
    import_path="bengal.cli.milo_commands.fix:fix",
    description="Auto-fix issues",
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
        display_result=False,
    )

new.lazy_command(
    "content-type",
    import_path="bengal.cli.milo_commands.new:new_content_type",
    description="Create a new ContentTypeStrategy scaffold",
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
    display_result=False,
)

config.lazy_command(
    "doctor",
    import_path="bengal.cli.milo_commands.config:config_doctor",
    description="Validate configuration",
    display_result=False,
)

config.lazy_command(
    "diff",
    import_path="bengal.cli.milo_commands.config:config_diff",
    description="Compare environments",
    display_result=False,
)

config.lazy_command(
    "init",
    import_path="bengal.cli.milo_commands.config:config_init",
    description="Create configuration structure",
    display_result=False,
)

config.lazy_command(
    "inspect",
    import_path="bengal.cli.milo_commands.config:config_inspect",
    description="Advanced config inspection with origin tracking",
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
    display_result=False,
)

cache.lazy_command(
    "hash",
    import_path="bengal.cli.milo_commands.cache:cache_hash",
    description="Compute deterministic hash of build inputs",
    display_result=False,
)

# --- standalone ---
cli.lazy_command(
    "upgrade",
    import_path="bengal.cli.milo_commands.upgrade:upgrade",
    description="Check for and install Bengal updates",
    display_result=False,
)

cli.lazy_command(
    "codemod",
    import_path="bengal.cli.milo_commands.codemod:codemod",
    description="Run automated code migrations",
    display_result=False,
)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run() -> None:
    """Entry point for bengal-next console script."""
    try:
        cli.run()
    except KeyboardInterrupt:
        from bengal.cli.utils.output import get_cli_output

        get_cli_output().interrupted()
        sys.exit(130)
