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
        Discovery[Discovery<br/>bengal/discovery/]
        Orchestration[Orchestration<br/>bengal/orchestration/]
        Rendering[Rendering<br/>bengal/rendering/]
        PostProcess[Post-Processing<br/>bengal/postprocess/]
    end

    subgraph "Object Model"
        Site[Site<br/>bengal/core/site/]
        Pages[Pages<br/>bengal/core/page/]
        Sections[Sections<br/>bengal/core/section.py]
        Assets[Assets<br/>bengal/core/asset/]
        Menus[Menus<br/>bengal/core/menu.py]
        NavTree[NavTree<br/>bengal/core/nav_tree.py]
    end

    subgraph "Supporting Systems"
        Cache[Build Cache<br/>bengal/cache/]
        Health[Health Checks<br/>bengal/health/]
        Autodoc[Autodoc<br/>bengal/autodoc/]
        Config[Config<br/>bengal/config/]
        Analysis[Analysis<br/>bengal/analysis/]
        Fonts[Fonts<br/>bengal/fonts/]
        Collections[Collections<br/>bengal/collections/]
        ContentLayer[Content Layer<br/>bengal/content_layer/]
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
    Health -.->|"validation"| PostProcess
    Autodoc -.->|"generates"| Pages
    Config -.->|"configuration"| Site
    Analysis -.->|"analyzes"| Site
    Fonts -.->|"downloads/generates"| Assets
    Collections -.->|"schema validation"| Discovery
    ContentLayer -.->|"remote sources"| Collections
    Output -.->|"terminal output"| CLI
    Debug -.->|"diagnostics"| Site
```

::::{dropdown} Key flows (overview)
1. **Build**: CLI → Site → Discovery → Orchestration → Rendering → Post-process
2. **Dev server**: watch → incremental rebuild → serve output
3. **Template context**: Site + Page + NavTree → Rendering
::::

## Module Overview

### Core Modules

- **`core/`**: Passive data models (Site, Page, Section, Asset, Menu, NavTree)
- **`orchestration/`**: Build coordination via specialized orchestrators
- **`rendering/`**: Template engine, Markdown parsing, directive system
- **`discovery/`**: Content and asset discovery from filesystem or remote sources

### Supporting Modules

- **`cache/`**: Build cache with Zstandard compression, dependency tracking, query indexes, and incremental build support
- **`collections/`**: Type-safe content schemas with validation for frontmatter
- **`content_layer/`**: Unified API for local/remote content sources (GitHub, Notion, REST)
- **`content_types/`**: Content strategies (Blog, Docs, Portfolio, Landing) with Strategy Pattern
- **`directives/`**: 50+ MyST-style directives for markdown (admonitions, cards, tabs, code-tabs, embeds, navigation, versioning)
- **`postprocess/`**: Sitemap, RSS, link validation
- **`health/`**: Comprehensive build validation with 20+ validators organized in tiers
- **`config/`**: Format-agnostic configuration loading, environment detection, build profiles
- **`cli/`**: Command-line interface with typo detection and Rich output
- **`output/`**: Centralized CLI output system with profile-aware formatting
- **`server/`**: Development server with SSE-based live reload
- **`utils/`**: Shared utilities (paths, file I/O, dates, pagination, atomic writes)
- **`errors/`**: Structured error system with actionable suggestions

### Feature Subsystems

- **`autodoc/`**: Generate docs from Python (AST-based), CLI (Click), and OpenAPI specs
- **`analysis/`**: Knowledge graph, PageRank, community detection, link suggestions, graph visualization
- **`fonts/`**: Google Fonts download, self-hosting, and CSS generation
- **`debug/`**: Diagnostic tools (Page Explainer, Delta Analyzer, Dependency Visualizer)
- **`services/`**: Service interfaces and implementations
- **`assets/`**: Asset processing pipeline (minification, optimization, fingerprinting)

## Pointers

- **Object model**: refer to [Object Model](core/object-model/)
- **Rendering pipeline**: refer to [Rendering Pipeline](rendering/rendering/)
- **Build orchestration**: refer to [Orchestration](core/orchestration/)
