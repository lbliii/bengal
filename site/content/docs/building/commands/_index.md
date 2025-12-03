---
title: CLI Commands
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

## Quick Reference

::::{tab-set}
:::{tab-item} Build
```bash
# Development build
bengal build

# Production build
bengal build --environment production --strict

# Clean and rebuild
bengal build --clean
```
:::

:::{tab-item} Serve
```bash
# Start dev server
bengal serve

# Custom port
bengal serve --port 8080

# Open browser automatically
bengal serve --open
```
:::

:::{tab-item} New
```bash
# New project
bengal new site my-site

# New page
bengal new page "My Post" --section blog
```
:::
::::

## Getting Help

```bash
# General help
bengal --help

# Command-specific help
bengal build --help
bengal serve --help
```

:::{seealso}
For comprehensive flag references, see the auto-generated [CLI Reference](/cli/).
:::
