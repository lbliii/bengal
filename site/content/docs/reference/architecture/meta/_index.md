---
title: Meta & Operations
nav_title: Meta
description: Performance, testing, and project structure
weight: 50
cascade:
  type: doc
icon: tag
---
# Meta & Operations

Operational details and project standards.

| Area | Coverage | Approach |
|------|----------|----------|
| **Testing** | Unit + Integration + Benchmarks | pytest, fixture-based |
| **Organization** | Documented | Clear module boundaries |

## Extension Points

| Level | Mechanism | Use Case |
|-------|-----------|----------|
| **Content** | Custom loaders | New content sources |
| **Validation** | Custom validators | Project-specific rules |
| **Rendering** | Custom shortcodes | Rich content components |
| **Post-process** | Custom processors | Output transformations |

:::{seealso}
- [Extension Points](extension-points.md) — Hook documentation
- [Testing](testing.md) — Test patterns and fixtures
:::
