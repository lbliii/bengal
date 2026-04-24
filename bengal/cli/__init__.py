"""
Command-line interface for Bengal Static Site Generator.

The CLI is powered by milo-cli with kida template rendering.

Entry points:
    bengal      → bengal.cli.milo_app:run
    bengal-next → bengal.cli.milo_app:run  (alias during migration, will be removed)

Surface area (12 groups, 4 tiers):

    Tier 1 — Core workflow (daily use):
        build, serve, clean, check, fix, new

    Tier 2 — Feature groups (weekly use):
        config, theme, content, version, i18n

    Tier 3 — Analysis & debugging (power users):
        inspect, debug

    Tier 4 — Infrastructure (rare):
        cache, codemod, upgrade, provenance

Related:
- bengal/cli/milo_app.py: CLI definition and entry point
- bengal/cli/milo_commands/: Command implementations
- bengal/cli/utils/: Shared utilities (CLIOutput, site loading, etc.)

"""

from __future__ import annotations

from bengal.cli.milo_app import cli, run

__all__ = ["cli", "run"]
