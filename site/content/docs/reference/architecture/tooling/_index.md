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

## Tool Architecture

```mermaid
flowchart TB
    subgraph "User Interface"
        CLI[CLI Commands]
        Server[Dev Server]
    end

    subgraph "Configuration"
        Config[Config Loader]
        Env[Environment]
    end

    subgraph "Core"
        Site[Site]
        Build[Build System]
    end

    CLI --> Config
    Server --> Config
    Config --> Site
    Site --> Build
    Server -.->|watches| Build
```

## Component Overview

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| **CLI** | Command interface | Typer-based, auto-generated help |
| **Dev Server** | Local development | Live reload, WebSocket updates |
| **Config** | Settings loader | TOML/YAML, environment merging |
| **Utils** | Shared utilities | Progress reporting, file handling |

## CLI Architecture

The CLI uses [Click](https://click.palletsprojects.com/) with command groups and aliases:

```
bengal
├── build      # Build site (also: b)
├── serve      # Dev server (also: s, dev)
├── clean      # Clean output (also: c)
├── validate   # Health checks (also: v, check)
├── new        # Scaffolding (site, page, layout, etc.)
├── config     # Configuration management
├── collections # Content collections
├── health     # Health check commands
├── debug      # Debug tools
├── explain    # Page explanation
└── ...        # Many more commands
```

**Alias System**: Bengal supports intuitive command aliases:
- Top-level shortcuts: `bengal build`, `bengal serve`, `bengal dev`
- Single-letter aliases: `bengal b`, `bengal s`, `bengal c`, `bengal v`

:::{tip}
The CLI is fully documented. See [[docs/reference/architecture/tooling/cli|CLI Reference]] for complete command documentation.
:::
