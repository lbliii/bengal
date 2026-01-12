---
title: CLI
description: Modular command-line interface
weight: 10
category: tooling
tags:
- tooling
- cli
- commands
- click
- command-line
- interface
keywords:
- CLI
- command-line interface
- Click
- commands
- build
- serve
- graph
---

# CLI (`bengal/cli/`)

**Structure**: Modular command-line interface with Click framework

**Location**: `bengal/cli/` directory with organized command modules

**Architecture**:
- `bengal/cli/__init__.py` - Main CLI group with command registration and typo detection
- `bengal/cli/base.py` - Custom Click classes (`BengalGroup`, `BengalCommand`) with themed help
- `bengal/cli/commands/` - Individual command modules
  - `build.py` - Build commands
  - `serve.py` - Development server
  - `graph/` - Graph analysis commands (package with report, orphans, pagerank, etc.)
  - `perf.py` - Performance analysis
  - `clean.py` - Cleanup utilities
  - `new/` - Content creation (package with presets, wizard, config, site, scaffolds)
  - `validate.py` - Content validation

**Features**:
- **Typo Detection**: Fuzzy matching for command names with suggestions
- **Rich Output**: Colored output and progress bars using Rich library
- **Error Handling**: Beautiful tracebacks with context and locals
- **Extensibility**: Easy to add new commands in separate modules

## Core Commands {#commands}

**Build Commands** {#build-commands}:
```bash
# Basic build (parallel by default)
bengal build

# Incremental build (uses cache for faster rebuilds)
bengal build --incremental

# Force sequential processing (disable auto-parallel)
bengal build --no-parallel

# Strict mode (fail on template errors, recommended for CI)
bengal build --strict

# Debug mode (full tracebacks, developer profile)
bengal build --debug

# Verbose output (show detailed phase timing and stats)
bengal build --verbose

# Fast mode (quiet output, max speed)
bengal build --fast

# Memory-optimized for large sites (5K+ pages)
bengal build --memory-optimized
```

**Development Commands** {#serve-commands}:
```bash
# Start development server with file watching
bengal serve

# Custom port
bengal serve --port 8080

# Disable file watching
bengal serve --no-watch

# Open browser automatically (default)
bengal serve --open

# Verbose output (show file watch events)
bengal serve --verbose
```

**Graph Analysis Commands**:
```bash
# Top-level graph command group
bengal graph

# Unified site analysis report
bengal graph report
bengal graph report --brief          # CI-friendly compact output
bengal graph report --format json    # Export as JSON

# CI integration with thresholds
bengal graph report --ci --threshold-isolated 5

# Connectivity analysis by level
bengal graph orphans                 # Show isolated pages (score < 0.25)
bengal graph orphans --level lightly # Show lightly-linked pages
bengal graph orphans --level all     # Show all under-linked pages
bengal graph orphans --format json   # Export with detailed metrics

# Analyze site structure and connectivity
bengal graph analyze
bengal graph analyze --tree          # Show site structure as tree
bengal graph analyze --output public/graph.html  # Interactive viz

# Compute PageRank scores
bengal graph pagerank --top 20

# Detect topical communities
bengal graph communities --min-size 3

# Find bridge pages (navigation bottlenecks)
bengal graph bridges --top 10

# Get link suggestions
bengal graph suggest --min-score 0.5

# Short aliases
bengal g report                      # g → graph
bengal analyze                       # Top-level alias for graph analyze
```

:::{example-label} bengal graph report Output
:::

```text
📊 Site Analysis Report
================================================================================
📈 Overview
   Total pages:        124
   Avg conn. score:    1.46

🔗 Connectivity Distribution
   🟢 Well-Connected:      39 pages (31.5%)
   🟡 Adequately:          38 pages (30.6%)
   🟠 Lightly Linked:      26 pages (21.0%)
   🔴 Isolated:            21 pages (16.9%) ⚠️
================================================================================
```

Refer to [Graph Analysis](../../../content/analysis/graph.md) for details and [Analyze site connectivity](../../../../tutorials/operations/analyze-site-connectivity/) for a guided walkthrough.

**Performance Commands**:
```bash
# Show recent build performance metrics
bengal perf

# Show last N builds
bengal perf --last 20

# Compare last two builds
bengal perf --compare

# Export as JSON
bengal perf --format json
```

**Utility Commands**:
```bash
# Clean output directory
bengal clean

# Clean cache and output
bengal clean --cache

# Create new site
bengal new site mysite

# Create new page
bengal new page content/blog/post.md

# Show version
bengal --version

# Show help
bengal --help
```

## Command Registration

Commands are registered in `bengal/cli/__init__.py`. The CLI uses command groups for organization and top-level aliases for convenience:

```python
from bengal.cli.base import BengalCommand, BengalGroup
from bengal.cli.commands.build import build as build_cmd
from bengal.cli.commands.serve import serve as serve_cmd
from bengal.cli.commands.clean import clean as clean_cmd
from bengal.cli.commands.graph import graph_cli
from bengal.cli.commands.new import new

@click.group(cls=BengalGroup, name="bengal", invoke_without_command=True)
@click.version_option(version=__version__, prog_name="Bengal SSG")
def main(ctx: click.Context) -> None:
    """Bengal Static Site Generator CLI."""
    pass

# Command groups (organized by category)
main.add_command(graph_cli)       # bengal graph <subcommand>
main.add_command(new)             # bengal new <subcommand>

# Top-level aliases (most common operations)
main.add_command(build_cmd, name="build")
main.add_command(serve_cmd, name="serve")
main.add_command(clean_cmd, name="clean")

# Short aliases for power users
main.add_command(build_cmd, name="b")   # b → build
main.add_command(serve_cmd, name="s")   # s → serve
main.add_command(serve_cmd, name="dev") # dev → serve
main.add_command(graph_cli, name="g")   # g → graph
```

## Custom Click Group

Bengal uses custom `BengalGroup` and `BengalCommand` classes in `bengal/cli/base.py` that provide themed help output and typo detection:

```python
class BengalGroup(click.Group):
    """Custom Click group with typo detection and themed help output."""

    command_class = BengalCommand  # Use themed command class

    def resolve_command(self, ctx, args):
        """Resolve command with fuzzy matching for typos."""
        try:
            return super().resolve_command(ctx, args)
        except click.exceptions.UsageError as e:
            if "No such command" in str(e) and args:
                unknown_cmd = args[0]
                suggestions = self._get_similar_commands(unknown_cmd)
                if suggestions:
                    cli = CLIOutput()
                    cli.error_header(f"Unknown command '{unknown_cmd}'.")
                    cli.console.print("[header]Did you mean one of these?[/header]")
                    for suggestion in suggestions:
                        cli.console.print(f"  [info]•[/info] {suggestion}")
                    raise SystemExit(2)
            raise

    def _get_similar_commands(self, unknown_cmd, max_suggestions=3):
        """Find similar commands using difflib fuzzy matching."""
        from difflib import get_close_matches
        return get_close_matches(unknown_cmd, self.commands.keys(),
                                 n=max_suggestions, cutoff=0.5)
```

:::{example-label} Command Suggestion
:::

```bash
$ bengal bild
Unknown command 'bild'.

Did you mean one of these?
  • build
  • bridges

Run 'bengal --help' to see all commands.
```
