---
title: CLI Commands
nav_title: Commands
description: CLI workflow guides for Bengal
weight: 20
category: guide
icon: terminal
card_color: green
---
# CLI Commands

Workflow guides for Bengal's command-line interface.

## Essential Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `bengal build` | Generate static site | Production builds |
| `bengal serve` | Dev server with live reload | Local development |
| `bengal new` | Scaffold projects/content | Starting new work |
| `bengal validate` | Run health checks | Before deploying |
| `bengal clean` | Remove generated files | Clear stale output |

## Quick Reference

:::{tab-set}
:::{tab-item} Build
```bash
# Development build (default: parallel + incremental)
bengal build

# Production build with strict validation
bengal build --environment production --strict

# Fast mode (quiet output, max parallelism)
bengal build --fast

# Clean output directory before building
bengal build --clean-output

# Memory-optimized build for large sites
bengal build --memory-optimized
```
:::

:::{tab-item} Serve
```bash
# Start dev server (opens browser by default)
bengal serve

# Custom port
bengal serve --port 8080

# Disable auto-open browser
bengal serve --no-open

# Theme development mode
bengal serve --profile theme-dev
```
:::

:::{tab-item} New
```bash
# New project
bengal new site my-site

# New page in a section
bengal new page "My Post" --section blog

# New layout template
bengal new layout article

# New theme scaffold
bengal new theme custom-theme
```
:::

:::{tab-item} Validate
```bash
# Run health checks
bengal validate

# Validate specific files
bengal validate --file content/page.md

# Watch mode (validate on file changes)
bengal validate --watch

# Verbose output (show all checks)
bengal validate --verbose
```
:::
:::{/tab-set}

## Build Profiles

Bengal includes three profiles optimized for different workflows:

```bash
# Writer (default): Fast, clean builds
bengal build

# Theme development: Template debugging
bengal build --theme-dev

# Developer: Full observability
bengal build --dev
```

See [Build Profiles](../configuration/profiles/) for details.

## Getting Help

```bash
# General help
bengal --help

# Command-specific help
bengal build --help
bengal serve --help

# Short aliases (power users)
bengal b     # build
bengal s     # serve
bengal c     # clean
bengal v     # validate
```

:::{seealso}
For comprehensive flag references, see [[docs/reference/architecture/tooling/cli|CLI Reference]].
:::
