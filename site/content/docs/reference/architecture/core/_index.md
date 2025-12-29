---
title: Core Architecture
nav_title: Core
description: Data models and build coordination
weight: 10
cascade:
  type: doc
icon: bengal-rosette
---
# Core Architecture

Foundational data models and build coordination.

| Component | Responsibility | Module |
|-----------|----------------|--------|
| **Site** | Central container, holds all content | `bengal/core/site/` |
| **Page** | Single content page with metadata | `bengal/core/page/` |
| **Section** | Directory container, holds children | `bengal/core/section.py` |
| **Asset** | Static file with processing metadata | `bengal/core/asset/` |

## Design Principles

- **No God Objects**: Each class has single responsibility
- **Passive Core**: Data models don't perform I/O
- **Composition over Inheritance**: BuildContext passes services
- **Immutable Where Possible**: Minimize side effects

:::{seealso}
[Design Principles](../design-principles/) — Full architectural guidelines
:::
