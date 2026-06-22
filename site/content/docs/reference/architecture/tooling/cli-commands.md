---
title: CLI Commands Reference
nav_title: CLI Commands
description: bengal build, serve, check, inspect, and utility command examples
weight: 11
category: tooling
tags:
- tooling
- cli
- commands
- persona-operator
keywords:
- bengal build
- bengal serve
- bengal check
- CLI flags
---

# CLI Commands Reference

Command examples and flags for day-to-day Bengal workflows.

:::{note}
**Do I need this?** Use when you need a specific command or flag. For CLI
architecture and registration internals, see
[[docs/reference/architecture/tooling/cli|CLI Architecture]].
:::

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

# Inspect include/literalinclude targets for a page
bengal debug includes docs/get-started/installation.md
```

:::{example-label} bengal inspect graph Output
:::

```text
ᓚᘏᗢ Site Graph

Pages: 124
Links: 428
Orphans: 3
```

Refer to [Graph Analysis](/docs/content/analysis/graph/) for details and [Analyze site connectivity](../../../../tutorials/operations/analyze-site-connectivity/) for a guided walkthrough.

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


## See Also

- [[docs/reference/architecture/tooling/cli|CLI Architecture]] — Milo registration, output templates, MCP
