---
title: Tooling & CLI
nav_title: Tooling
description: Developer tools, CLI, server, and configuration
weight: 40
cascade:
  type: doc
icon: terminal
---
# Tooling & CLI

Developer interfaces for working with Bengal.

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| **CLI** | Command interface | Click-based, auto-generated help |
| **Dev Server** | Local development | Live reload, SSE hot updates |
| **Config** | Settings loader | TOML/YAML, environment merging |
| **Utils** | Shared utilities | Progress reporting, file handling |

## CLI Commands

```
bengal
├── build (b)     # Build site
├── serve (s)     # Dev server
├── clean (c)     # Clean output
├── validate (v)  # Health checks
├── new           # Scaffolding
└── ...           # Many more
```

:::{tip}
See [CLI Reference](cli/) for complete command documentation.
:::
