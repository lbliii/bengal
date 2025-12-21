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

- **Documentation Sites** — Technical docs with automatic API reference generation from Python source code
- **Blogs & Journals** — Personal and professional writing with tags, categories, and related posts
- **Product & Marketing Sites** — Landing pages, portfolios, and company websites
- **Knowledge Bases** — Internal wikis and help centers with full-text search

## Why Bengal?

| Benefit | What It Means |
|---------|---------------|
| **Fast Builds** | Parallel processing + incremental builds = 18-42× faster rebuilds on large sites |
| **Python-Native** | Built for Python 3.14+ with free-threading support; no Node.js required |
| **Auto API Docs** | AST-based autodoc generates reference docs from your Python source and CLI tools |
| **Batteries Included** | Dev server, live reload, syntax highlighting, sitemap, RSS, search—all built in |
| **Flexible Theming** | Theme inheritance, template swizzling, and 200+ CSS design tokens |
| **Content First** | Markdown with MyST directives, YAML/TOML front matter, and cascading config |

---

:::{child-cards}
:columns: 2
:include: all
:fields: title, description, icon
:::
