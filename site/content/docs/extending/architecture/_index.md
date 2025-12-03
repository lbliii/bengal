---
title: Architecture
description: Bengal internals for contributors
weight: 40
draft: false
lang: en
tags: [architecture, internals, contributing]
keywords: [architecture, internals, contributing, development]
category: explanation
---

# Architecture

Deep dive into Bengal's internals for contributors and advanced users.

## Overview

Bengal is built around these core concepts:

- **Object Model** — Site, Page, Section, Asset
- **Build Pipeline** — Discovery → Build → Render → Output
- **Orchestration** — Coordinated build operations
- **Extension Points** — Hooks for customization

## Core Objects

```
Site
├── Pages[]          # All content pages
├── Sections[]       # Content hierarchy
├── Assets[]         # Static and processed assets
├── Menus{}          # Navigation structures
└── Config           # Site configuration
```

## Build Pipeline

1. **Discovery** — Find all content and assets
2. **Build** — Parse frontmatter, process content
3. **Render** — Apply templates, generate HTML
4. **Output** — Write files, process assets

## Project Structure

```
bengal/
├── core/           # Passive data models (no I/O)
├── orchestration/  # Build coordination
├── rendering/      # Template and content rendering
├── discovery/      # Content/asset discovery
├── cache/          # Caching infrastructure
├── health/         # Validation and health checks
└── cli/            # Command-line interface
```

## In This Section

- **[Object Model](/docs/extending/architecture/object-model/)** — Site, Page, Section, Asset
- **[Build Pipeline](/docs/extending/architecture/build-pipeline/)** — How builds work
- **[Plugin API](/docs/extending/architecture/plugin-api/)** — Extension points
- **[Contributing](/docs/extending/architecture/contributing/)** — Development guide

