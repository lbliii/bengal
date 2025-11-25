---
title: Design Principles
description: Core patterns and philosophies guiding Bengal's architecture.
weight: 50
category: core
tags: [core, design-principles, architecture, patterns, best-practices, performance]
keywords: [design principles, architecture patterns, best practices, performance, extensibility]
---

# Design Principles

Bengal follows a set of strict architectural principles to ensure maintainability, performance, and scalability.

## 1. No "God Objects"

We strictly avoid monolithic classes that know too much.

- **Site** is just a container. It delegates logic to **Orchestrators**.
- **Page** is split into mixins (`Metadata`, `Navigation`, `Operations`).
- **Dependencies** flow downwards: `Site` → `Section` → `Page`.

## 2. Performance First

::::{cards}
:columns: 2
:gap: small
:variant: concept

:::{card} Parallel by Default
Use `ThreadPoolExecutor` for any workload > 5 items.
:::

:::{card} Lazy Loading
Don't parse content or generate HTML until it's actually requested.
:::

:::{card} Incremental
Only rebuild what changed. Track dependencies to know what that is.
:::

:::{card} Caching
Cache parsed ASTs and template bytecode to skip expensive steps.
:::
::::

## 3. Explicit Data Flow

We avoid global state (`global _site`) at all costs.

- **BuildContext**: A context object is explicitly passed through the pipeline.
- **Immutability**: Once parsed, page content should not change.
- **Single Source**: The `Site` object is the only source of truth.

## 4. Resilience

::::{tab-set}
:::{tab-item} Graceful Degradation
**In Development**
If a template is missing or frontmatter is invalid, we **warn and continue**. We render a fallback or skip the bad item so the user can fix it without restarting.
:::

:::{tab-item} Fail-Fast
**In Production (Strict Mode)**
When `strict=true`, any error (broken link, missing variable) immediately stops the build to prevent deploying bad content.
:::
::::

## 5. Extensibility

Bengal is designed to be extended, not forked.

- **Strategy Pattern**: For content types (Blog vs Docs).
- **Registry Pattern**: For template functions and parsers.
- **Factory Pattern**: For creating parsers and renderers.

## 6. User Experience

Error messages must be **actionable**.

- ❌ "File not found"
- ✅ "Template 'blog/post.html' not found. Searched in: themes/default/templates/, site/templates/"
