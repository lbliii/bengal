---
title: CLI
description: Modular command-line interface
weight: 10
category: tooling
tags: [tooling, cli, commands, click, command-line, interface]
keywords: [CLI, command-line interface, Click, commands, build, serve, autodoc, graph]
---

# CLI (`bengal/cli/`)

**Structure**: Modular command-line interface with Click framework

**Location**: `bengal/cli/` directory with organized command modules

**Architecture**:
- `bengal/cli/__init__.py` - Main CLI group with command registration and typo detection
- `bengal/cli/commands/` - Individual command modules
  - `build.py` - Build commands
  - `serve.py` - Development server
  - `autodoc.py` - Documentation generation
  - `graph.py` - Graph analysis commands
  - `perf.py` - Performance analysis
  - `clean.py` - Cleanup utilities
  - `new/` - Content creation (package with presets, wizard, config, site, scaffolds)

**Features**:
- **Typo Detection**: Fuzzy matching for command names with suggestions
- **Rich Output**: Colored output and progress bars using Rich library
- **Error Handling**: Beautiful tracebacks with context and locals
- **Extensibility**: Easy to add new commands in separate modules

## Core Commands

**Build Commands**:
```bash
# Basic build
bengal site build

# Incremental build (18-42x faster)
bengal site build --incremental

# Parallel build (default, 2-4x faster)
bengal site build --parallel

# Strict mode (fail on template errors, recommended for CI)
bengal site build --strict

# Debug mode (full tracebacks)
bengal site build --debug

# Verbose output (show detailed change info)
bengal site build --incremental --verbose
```

**Development Commands**:
```bash
# Start development server with live reload
bengal site serve

# Custom port
bengal site serve --port 8080

# Disable live reload
bengal site serve --no-reload
```

**Documentation Commands**:
```bash
# Generate Python API documentation
bengal autodoc

# Generate CLI documentation (Click only)
bengal autodoc-cli --app myapp.cli:main --framework click

# Override source/output
bengal autodoc --source mylib --output content/api

# Show extraction stats
bengal autodoc --stats --verbose
```

**Graph Analysis Commands**:
```bash
# Analyze site structure and connectivity
bengal graph

# Show site structure as tree
bengal graph --tree

# Generate interactive visualization
bengal graph --output public/graph.html

# Compute PageRank scores
bengal pagerank --top 20

# Detect topical communities
bengal communities --min-size 3

# Find bridge pages (navigation bottlenecks)
bengal bridges --top 10

# Get link suggestions
bengal suggest --min-score 0.5
```

**Performance Commands**:
```bash
# Performance analysis
bengal perf

# Detailed performance breakdown
bengal perf --verbose
```

**Utility Commands**:
```bash
# Clean output directory
bengal site clean

# Clean cache and output
bengal site cleanup

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

Commands are registered in `bengal/cli/__init__.py`:

```python
from bengal.cli.commands.build import build
from bengal.cli.commands.serve import serve
from bengal.cli.commands.autodoc import autodoc, autodoc_cli
from bengal.cli.commands.graph import graph, pagerank, communities, bridges, suggest
from bengal.cli.commands.perf import perf
from bengal.cli.commands.clean import clean, cleanup
from bengal.cli.commands.new import new

@click.group(cls=BengalGroup)
@click.version_option(version=__version__, prog_name="Bengal SSG")
def main() -> None:
    """Bengal SSG - A high-performance static site generator."""
    pass

# Register commands
main.add_command(build)
main.add_command(serve)
main.add_command(autodoc)
main.add_command(autodoc_cli)
main.add_command(graph)
main.add_command(pagerank)
main.add_command(communities)
main.add_command(bridges)
main.add_command(suggest)
main.add_command(perf)
main.add_command(clean)
main.add_command(cleanup)
main.add_command(new)
```

## Custom Click Group

Bengal uses a custom `BengalGroup` class that provides typo detection:

```python
class BengalGroup(click.Group):
    """Custom Click group with typo detection and suggestions."""

    def resolve_command(self, ctx, args):
        """Resolve command with fuzzy matching for typos."""
        try:
            return super().resolve_command(ctx, args)
        except click.exceptions.UsageError as e:
            if "No such command" in str(e) and args:
                suggestions = self._get_similar_commands(args[0])
                if suggestions:
                    # Show suggestions
                    pass
            raise
```

**Example**:
```bash
$ bengal bild
Unknown command 'bild'.

Did you mean one of these?
  • build
  • bridges

Run 'bengal --help' to see all commands.
```

# Utilities (`bengal/utils/`)

Bengal provides a comprehensive set of utility modules that consolidate common operations across the codebase, eliminating duplication and providing consistent, well-tested implementations.

## Text Utilities (`bengal/utils/text.py`)
