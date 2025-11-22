# orchestration

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/orchestration/__init__.py

Build orchestration module for Bengal SSG.

This module provides specialized orchestrators that handle different phases
of the build process. The orchestrator pattern separates build coordination
from data management, making the Site class simpler and more maintainable.

Orchestrators:
    - BuildOrchestrator: Main build coordinator
    - ContentOrchestrator: Content/asset discovery and setup
    - TaxonomyOrchestrator: Taxonomies and dynamic page generation
    - MenuOrchestrator: Navigation menu building
    - RenderOrchestrator: Page rendering (sequential and parallel)
    - AssetOrchestrator: Asset processing (minify, optimize, copy)
    - PostprocessOrchestrator: Sitemap, RSS, link validation
    - IncrementalOrchestrator: Incremental build logic

Usage:
    from bengal.orchestration import BuildOrchestrator

    orchestrator = BuildOrchestrator(site)
    stats = orchestrator.build(parallel=True, incremental=True)

*Note: Template has undefined variables. This is fallback content.*
