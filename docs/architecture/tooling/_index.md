---
title: Tooling & CLI
nav_title: Tooling
description: Developer tools, CLI, server, and configuration
weight: 40
icon: terminal
---
# Tooling & CLI

Developer interfaces for working with Bengal.

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| **CLI** | Command interface | Milo registry, autodoc `/cli/` reference |
| **Dev Server** | Local development | Live reload, SSE hot updates |
| **Config** | Settings loader | TOML/YAML, environment merging |
| **Utils** | Shared utilities | Progress reporting, file handling |

## CLI Commands

```
bengal
├── build (b)     # Build site
├── serve (s)     # Dev server
├── preview       # Static output preview
├── clean (c)     # Clean output
├── check (v)     # Health checks
├── new           # Scaffolding
└── ...           # Many more
```

:::{tip}
See [[/cli/|Bengal CLI Reference]] (autodoc, generated from Milo) for complete
command and flag lookup. This page covers architecture and contributor internals.
:::
