---
title: Subsystems
description: Specialized feature subsystems
weight: 30
cascade:
  type: doc
icon: list
---
# Subsystems

Specialized subsystems that extend Bengal's core functionality.

| Subsystem | Purpose | Entry Point |
|-----------|---------|-------------|
| **Autodoc** | Generate docs from Python, CLI, OpenAPI | `bengal/autodoc/` |
| **Analysis** | Graph analysis, PageRank, link suggestions | `bengal/analysis/` |
| **Health** | Content validation, broken link detection | `bengal/health/` |
| **Fonts** | Google Fonts download, self-hosting | `bengal/fonts/` |
| **Collections** | Type-safe content schemas | `bengal/collections/` |
| **Content Layer** | Unified API for remote content | `bengal/content_layer/` |
| **CLI Output** | Terminal output formatting | `bengal/output/` |
| **Debug Tools** | Build diagnostics | `bengal/debug/` |

:::{note}
Subsystems are **lazy-loaded** — they only import when used, minimizing startup time.
:::
