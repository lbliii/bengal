---
title: CLI
description: Modular command-line interface
weight: 10
category: tooling
tags:
- tooling
- cli
- commands
- milo
- command-line
- interface
keywords:
- CLI
- command-line interface
- Milo
- commands
- build
- serve
- graph
---

# CLI (`bengal/cli/`)

**Structure**: Modular command-line interface with Milo CLI

**Location**: `bengal/cli/` directory with organized command modules

**Architecture**:
- `bengal/cli/milo_app.py` - Root Milo app and lazy command registration
- `bengal/cli/milo_commands/` - Annotated Milo command modules
- `bengal/output/templates/` - Kida templates for terminal output
  - `build.py` - Build commands
  - `serve.py` - Development server
  - `preview.py` - Build-then-static local preview
  - `check.py` - Author-facing validation checks
  - `audit.py` - Generated artifact audit
  - `clean.py` - Cleanup utilities
  - `new.py` - Content and theme creation

**Features**:
- **Lazy command imports**: Fast CLI startup with command modules loaded on demand
- **Kida output**: Structured command results rendered through Milo/Kida templates
- **Bengal help templates**: Root and group help dogfood Milo's registry with Bengal-owned Kida templates
- **Command state templates**: Empty states, command lists, and command errors use reusable Bengal Kida templates
- **Shared output bridge**: Semantic command messages, logger console events, and phase summaries route through `CLIOutput`
- **Aggregated notices**: Repeated warnings such as missing icons, unknown config entries, and URL collision claimants collapse into compact summaries
- **Milo built-ins**: `--llms-txt`, shell completions, and MCP gateway modes are generated from the registered command tree
- **Error Handling**: Beautiful tracebacks with context and locals
- **Extensibility**: Easy to add new commands in separate modules

**Milo Built-ins**:
```bash
# Agent-readable command reference
bengal --llms-txt

# Shell completion scripts
bengal --completions zsh
bengal --completions bash
bengal --completions fish

# Expose Bengal commands through Milo's MCP transport
bengal --mcp

# Register or remove Bengal from the local Milo MCP gateway
bengal --mcp-install
bengal --mcp-uninstall
```

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

# ASCII-safe lifecycle output for CI logs
bengal build --style ci

# Memory-optimized for large sites (5K+ pages)
bengal build --memory-optimized

# Preview build without writing files (see what WOULD happen)
bengal build --dry-run

# Show detailed breakdown of why pages are rebuilt/skipped
bengal build --explain

# Machine-readable explain output (for tooling)
bengal build --explain --explain-json
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
bengal serve --open-browser

# ASCII-safe server lifecycle output for CI or log capture
bengal serve --style ci

# Verbose output (show file watch events)
bengal serve --verbose

# Build completely, then serve generated output read-only
bengal preview

# Preview with production environment settings
bengal preview --environment production

# Preview on a custom port without opening the browser
bengal preview --port 8080 --no-open-browser
```

**Inspection Commands**:
```bash
# Explain how a page is built
bengal inspect page --page-path index

# Check internal and external links
bengal inspect links
bengal inspect links --internal-only
bengal inspect links --external-only

# Analyze site structure and link graph
bengal inspect graph

# Visualize dependency relationships
bengal debug deps
```

:::{example-label} bengal inspect graph Output
:::

```text
ᓚᘏᗢ Site Graph

Pages: 124
Links: 428
Orphans: 3
```

Refer to [Graph Analysis](../../../content/analysis/graph.md) for details and [Analyze site connectivity](../../../../tutorials/operations/analyze-site-connectivity/) for a guided walkthrough.

**Performance Commands**:
```bash
# Show recent build performance metrics
bengal inspect perf

# Show last N builds
bengal inspect perf --last 20

# Compare last two builds
bengal inspect perf --compare

# Export as JSON
bengal inspect perf --output-format json
```

**Utility Commands**:
```bash
# Validate source content and author-facing policy
bengal check

# Bounded ASCII-safe health report for CI logs
bengal check --style ci --limit 5

# Drill into one health finding code from the report
bengal check --focus H101-001 --suggestions

# Compatibility alias while older automation migrates
bengal health

# Audit generated artifacts after a build
bengal audit

# Bounded verdict-first audit report for CI logs
bengal audit --style ci --limit 5

# Drill into one finding code from the report
bengal audit --focus A101-001

# Clean output directory
bengal clean

# Clean cache and output
bengal clean --cache

# Create new site
bengal new site --name mysite

# Create new page
bengal new page --name post --section blog

# Show version
bengal --version

# Show help
bengal --help
```

**Plugin Commands**:
```bash
# List installed plugins and readiness
bengal plugin list

# Show capability details for one plugin
bengal plugin info my-plugin

# Validate plugins against capabilities Bengal currently wires
bengal plugin validate
```

Plugin introspection is intentionally conservative: it loads the same
`bengal.plugins` entry points as a build, runs each plugin's `register()` method
against a temporary registry, and reports capability counts plus whether each
capability is actually integrated today.

**Upgrade Commands**:
```bash
# Check for updates and upgrade interactively
bengal upgrade

# Skip confirmation prompt
bengal upgrade -y

# Show what would be done without executing
bengal upgrade --dry-run

# Force upgrade even if already on latest
bengal upgrade --force
```

The upgrade command automatically detects how Bengal was installed (uv, pip, pipx, conda) and runs the appropriate upgrade command. It checks PyPI for the latest version with a 24-hour cache to avoid repeated network requests.

## Command Registration

Commands are registered in `bengal/cli/milo_app.py`. The CLI uses Milo's lazy
registration API so importing `bengal` or rendering root help does not import
every command implementation:

```python
from milo import CLI

cli = CLI(name="bengal", description="Static site generator for Python teams")

cli.lazy_command(
    "build",
    import_path="bengal.cli.milo_commands.build:build",
    description="Build your site",
    aliases=("b",),
    display_result=False,
)

new = cli.group("new", description="Create new site, theme, or content", aliases=("n",))
new.lazy_command(
    "site",
    import_path="bengal.cli.milo_commands.new:new_site",
    description="Create a new Bengal site",
    display_result=False,
)
```

## Command Inventory

The public command inventory is generated from the Milo registry and guarded by
unit tests against this documentation, `--llms-txt`, README command snippets,
and runtime smoke coverage.

```text cli-command-inventory
build
serve
preview
clean
check
audit
health
fix
upgrade
codemod
new.site
new.theme
new.page
new.layout
new.partial
new.content-type
config.show
config.doctor
config.diff
config.init
config.inspect
theme.list
theme.info
theme.discover
theme.swizzle
theme.install
theme.validate
theme.new
theme.debug
theme.directives
theme.test
theme.assets
content.sources
content.fetch
content.collections
content.schemas
version.list
version.info
version.create
version.diff
i18n.init
i18n.extract
i18n.compile
i18n.sync
i18n.status
plugin.list
plugin.info
plugin.validate
inspect.page
inspect.links
inspect.graph
inspect.perf
debug.incremental
debug.delta
debug.deps
debug.migrate
debug.sandbox
cache.inputs
cache.hash
```

Root aliases are part of the contract: `b` for `build`, `s` and `dev` for
`serve`, `c` for `clean`, and `v` for `check`. Group aliases are `n` for `new`
and `plugins` for `plugin`.

`health` remains a top-level legacy alias for `check`. It is kept for existing
automation, but new docs and examples should use `check`.

## Themed Help

Bengal subclasses Milo's `CLI` as `BengalCLI` so command results and root help
render through the shared `CLIOutput` bridge. Root `bengal`, `bengal --help`,
and group invocations such as `bengal new` use Bengal-owned Kida templates fed
by Milo's command registry, while leaf command help is generated from the
annotated command signatures.

```bash
$ bengal --help
bengal 0.3.2
Static site generator for Python teams — every layer pure Python, scales with your cores

Core workflow
  build (b)               Build your site
  serve (s, dev)          Start dev server with hot reload
  preview                  Build and serve completed output
  check (v)               Validate your site

Site systems
  config                  Configuration management [group]
  theme                   Theme development, directives, and assets [group]
```

## Command Output Templates

Command implementations should return structured dictionaries for automation
and use `bengal.output.get_cli_output()` for human terminal output. Prefer
command-state templates for user-facing branches:

- `command_empty.kida` for no-op, missing setup, or nothing-to-do states
- `command_list.kida` for lists with names, status, descriptions, or source metadata
- `command_error.kida` for command-choice errors before argparse usage leaks through
- `_report_primitives.kida` for verdict-first reports with meters and issue cards
- Domain templates such as `build_summary.kida`, `validation_report.kida`,
  `check_report.kida`, `scaffold_result.kida`, `clean_plan.kida`,
  `clean_result.kida`, and `artifact_audit.kida` for richer flows

The first parity pass covers plugin discovery, content sources/collections,
cache input lists, theme lists/discovery, missing config states, and unknown
root/group command errors. New command work should add the command to the
output matrix in `tests/unit/cli/test_command_output_templates.py` when it
introduces a new terminal branch.

Build summaries, health checks, and artifact audit now follow the Milo output
gallery pattern: the first screen states the verdict, details are bounded by
`--limit` where findings can be long, `--focus CODE` drills into one finding
for check/audit, `--style ci` and `--style ascii` use stable ASCII glyphs, and
JSON-producing paths keep their existing structured envelopes for automation.
Commands apply these styles with `CLIOutput.output_mode(...)`, so direct
in-process command calls restore the previous terminal mode after completion or
early exit.

## MCP Annotations

Command registration includes Milo MCP annotations where intent matters.
Read-only commands such as `check`, `audit`, `plugin list`, `config show`, and
`cache inputs` advertise `readOnlyHint`. File-writing or state-changing commands
such as `clean`, `fix`, `new`, `config init`, `theme swizzle`, `i18n compile`,
`version create`, `upgrade`, and `codemod` advertise `destructiveHint` and
`idempotentHint` where applicable.
