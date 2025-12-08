---
title: Tooling & CLI
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

The CLI uses [Typer](https://typer.tiangolo.com/) with command groups:

```
bengal
├── build      # Build site
├── serve      # Dev server
├── new        # Scaffolding
├── validate   # Health checks
├── autodoc    # Documentation generation
└── analyze    # Site analysis
```

:::{tip}
The CLI is fully documented via autodoc. See [CLI Reference](/cli/) for complete command documentation.
:::
