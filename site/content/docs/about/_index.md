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

Bengal is a high-performance static site generator built in Python for Python 3.14+. It transforms Markdown content into fast, beautiful websites with minimal configuration and maximum speed.

## Use Cases

- **Documentation Sites** — Technical docs with automatic API reference generation from Python, CLI, and OpenAPI sources
- **Blogs & Journals** — Personal and professional writing with tags, categories, and related posts
- **Product & Marketing Sites** — Landing pages, portfolios, and company websites
- **Knowledge Bases** — Internal wikis and help centers with full-text search

## Why Bengal?

| Benefit | What It Means |
|---------|---------------|
| **Fast Builds** | Parallel processing + incremental builds; see [[docs/about/benchmarks\|Benchmarks]] for measured times |
| **Python-Native** | Built for Python 3.14+ with free-threading support (PEP 703); no Node.js required |
| **Auto API Docs** | AST-based autodoc generates reference docs from Python source, CLI tools, and OpenAPI specs |
| **Batteries Included** | Dev server, live reload, syntax highlighting, sitemap, RSS, Lunr search—all built in |
| **Flexible Theming** | Theme inheritance, template swizzling, and 1000+ CSS design tokens |
| **Content First** | Markdown with MyST directives, YAML/TOML front matter, and cascading config |

## Philosophy

Bengal prioritizes **correctness and clarity over backwards compatibility**. Each release represents the best solution we know how to deliver—when existing behavior no longer reflects the best design, it may be changed.

This keeps the codebase healthy and enables rapid evolution. See [[docs/about/philosophy|Project Philosophy]] for details.

---

:::{child-cards}
:columns: 2
:include: all
:fields: title, description, icon
:::
