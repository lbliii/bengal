---
title: Architecture
description: High-level architecture overview of Bengal
weight: 50
type: doc
tags:
- architecture
- overview
- design
- systems
- components
keywords:
- architecture
- design
- overview
- systems
- components
- structure
category: architecture
cascade:
  type: doc
props:
  icon: folder
---
# Architecture Overview

Bengal SSG follows a modular architecture with clear separation of concerns to avoid "God objects" and maintain high performance even with large sites.

:::{child-cards}
:columns: 2
:include: sections
:fields: title, description, icon
:::

## High-Level Architecture

```mermaid
graph TB
    subgraph "Entry Points"
        CLI[CLI<br/>bengal/cli/]
        Server[Dev Server<br/>bengal/server/]
    end

    subgraph "Core Build Pipeline"
        Discovery[Discovery<br/>bengal/discovery/]
        Orchestration[Orchestration<br/>bengal/orchestration/]
        Rendering[Rendering<br/>bengal/rendering/]
        PostProcess[Post-Processing<br/>bengal/postprocess/]
    end

    subgraph "Object Model"
        Site[Site<br/>bengal/core/site.py]
        Pages[Pages<br/>bengal/core/page/]
        Sections[Sections<br/>bengal/core/section.py]
        Assets[Assets<br/>bengal/core/asset.py]
        Menus[Menus<br/>bengal/core/menu.py]
    end

    subgraph "Supporting Systems"
        Cache[Build Cache<br/>bengal/cache/]
        Health[Health Checks<br/>bengal/health/]
        Autodoc[Autodoc<br/>bengal/autodoc/]
        Config[Config<br/>bengal/config/]
        Analysis[Analysis<br/>bengal/analysis/]
        Fonts[Fonts<br/>bengal/fonts/]
    end

    CLI --> Site
    Server --> Site
    Site --> Discovery
    Discovery --> Pages
    Discovery --> Sections
    Discovery --> Assets
    Site --> Orchestration
    Orchestration --> Menus
    Orchestration --> Rendering
    Menus -.->|"used by"| Rendering
    Rendering --> PostProcess
    Cache -.->|"cache checks"| Orchestration
    Health -.->|"validation"| PostProcess
    Autodoc -.->|"generates"| Pages
    Config -.->|"configuration"| Site
    Analysis -.->|"analyzes"| Site
    Fonts -.->|"downloads/generates"| Assets
```

**Key Flows:**
1. **Build**: CLI → Site → Discovery → Orchestration → [Menus + Rendering] → Post-Process
2. **Menu Building**: Orchestration builds menus → Rendering uses menus in templates
3. **Cache**: Build Cache checks file changes and dependencies before rebuilding
4. **Autodoc**: Generate Python/CLI docs → treated as regular content pages
5. **Dev Server**: Watch files → trigger incremental rebuilds → serve output
