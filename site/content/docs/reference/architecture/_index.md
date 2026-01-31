---
title: Architecture
description: High-level architecture overview of Bengal
weight: 50
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
icon: folder
---
# Architecture Overview

Bengal is organized as a set of small subsystems with clear boundaries. Use this section to orient yourself and then jump to the specific subsystem you are changing.

## How to use this section

- Start with the overview diagram on this page.
- Use the cards to jump to a subsystem.
- Prefer subsystem pages over repeating context here.

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
        Discovery[Discovery<br/>bengal/content/discovery/]
        Orchestration[Orchestration<br/>bengal/orchestration/]
        Rendering[Rendering<br/>bengal/rendering/]
        PostProcess[Post-Processing<br/>bengal/postprocess/]
    end

    subgraph "Object Model"
        Site[Site<br/>bengal/core/site/]
        Pages[Pages<br/>bengal/core/page/]
        Sections[Sections<br/>bengal/core/section/]
        Assets[Assets<br/>bengal/core/asset/]
        Menus[Menus<br/>bengal/core/menu.py]
        NavTree[NavTree<br/>bengal/core/nav_tree.py]
    end

    subgraph "Contracts"
        Protocols[Protocols<br/>bengal/protocols/]
    end

    subgraph "Supporting Systems"
        Cache[Build Cache<br/>bengal/cache/]
        Health[Health Checks<br/>bengal/health/]
        Autodoc[Autodoc<br/>bengal/autodoc/]
        Config[Config<br/>bengal/config/]
        Analysis[Analysis<br/>bengal/analysis/]
        Fonts[Fonts<br/>bengal/fonts/]
        Collections[Collections<br/>bengal/collections/]
        ContentLayer[Content Layer<br/>bengal/content/sources/]
        Output[CLI Output<br/>bengal/output/]
        Debug[Debug Tools<br/>bengal/debug/]
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
    Site --> NavTree
    Sections -.->|"builds from"| NavTree
    Menus -.->|"used by"| Rendering
    NavTree -.->|"used by"| Rendering
    Rendering --> PostProcess
    Cache -.->|"cache checks"| Orchestration
    Health -.->|"post-build validation"| Orchestration
    Autodoc -.->|"generates"| Pages
    Config -.->|"configuration"| Site
    Analysis -.->|"analyzes"| Site
    Fonts -.->|"font files"| Orchestration
    Fonts -.->|"social cards"| PostProcess
    Collections -.->|"schema validation"| Discovery
    ContentLayer -.->|"remote sources"| Collections
    Output -.->|"terminal output"| CLI
    Debug -.->|"diagnostics"| Site
    Protocols -.->|"contracts"| Rendering
    Protocols -.->|"contracts"| Cache
    Protocols -.->|"contracts"| Orchestration
```

## Key Flows

| Flow | Path |
|------|------|
| **Build** | CLI → Site → Discovery → Orchestration → Rendering → Post-process |
| **Dev server** | Watch → Incremental rebuild → Serve output |
| **Template context** | Site + Page + NavTree → Rendering |

## Quick Links

| Topic | Page |
|-------|------|
| Data models (Site, Page, Section) | [Object Model](core/object-model/) |
| Build coordination | [Orchestration](core/orchestration/) |
| Markdown → HTML | [Rendering Pipeline](rendering/rendering/) |
| Interface contracts | [Protocol Layer](meta/protocols/) |
| Design guidelines | [Design Principles](design-principles/) |
