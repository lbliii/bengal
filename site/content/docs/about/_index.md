---
title: About
description: Concepts, benchmarks, and reference
weight: 5
layout: list
menu:
  main:
    weight: 40
cascade:
  type: doc
icon: info
---

# About

Bengal is a high-performance static site generator for Python 3.14+. It transforms Markdown into fast, beautiful websites with minimal configuration.

## Use Cases

- **Documentation Sites** — Technical docs with auto-generated API reference
- **Blogs & Journals** — Personal writing with tags and categories
- **Product & Marketing Sites** — Landing pages and portfolios
- **Knowledge Bases** — Internal wikis with full-text search

## Why Bengal?

| Benefit | What It Means |
|---------|---------------|
| **Fast Builds** | Parallel + incremental builds. See [[docs/about/benchmarks\|Benchmarks]] |
| **Python-Native** | Python 3.14+ with free-threading (PEP 703). No Node.js |
| **Auto API Docs** | AST-based docs from Python, CLI, and OpenAPI sources |
| **Batteries Included** | Dev server, live reload, sitemap, RSS, Lunr search |
| **Flexible Theming** | Theme inheritance, swizzling, 650+ CSS tokens |
| **Content First** | MyST Markdown, YAML/TOML front matter, cascading config |

## Philosophy

Bengal prioritizes **correctness over backwards compatibility**. Each release reflects our best design. When better approaches emerge, behavior may change.

See [[docs/about/philosophy|Project Philosophy]] for details.

---

:::{child-cards}
:columns: 2
:include: all
:fields: title, description, icon
:::
