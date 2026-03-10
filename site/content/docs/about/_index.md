---
title: About
description: What Bengal is, where it fits, and which kinds of static sites it is designed to build
weight: 5
layout: list
menu:
  main:
    weight: 40
icon: info
---

# About

Bengal is a Python static site generator for documentation sites, blogs, knowledge
bases, and product sites. It transforms Markdown, notebooks, and structured content
into fast websites with built-in SEO/discovery features and a Python-native workflow.

## Use Cases

- **Documentation Sites** — Technical docs with auto-generated API reference
- **Blogs & Journals** — Personal writing with tags and categories
- **Product & Marketing Sites** — Landing pages and portfolios
- **Knowledge Bases** — Internal wikis with full-text search

## Why Bengal?

| Benefit | What It Means |
|---------|---------------|
| **Fast Builds** | Parallel + incremental builds. See [Benchmarks](./benchmarks) |
| **Python-Native** | Python 3.14+ with free-threading (PEP 703). No Node.js |
| **Auto API Docs** | AST-based docs from Python, CLI, and OpenAPI sources |
| **SEO & Discovery** | Sitemap, RSS, canonical URLs, Open Graph tags, social cards, and search indexes |
| **Batteries Included** | Development server, live reload, validation, search, and content analysis |
| **Flexible Theming** | Theme inheritance, swizzling, 1,100+ CSS tokens |
| **Content First** | MyST Markdown, YAML/TOML front matter, cascading config |

## Discovery Strategy

Bengal is strongest when you publish pages that match how people actually search:

- Installation and quickstart guides
- Tutorials for specific use cases
- Migration guides from other static site generators
- Troubleshooting pages for concrete errors
- Comparison pages for adjacent tools or approaches

The generator already provides the technical pieces: metadata fields, canonical URLs,
sitemap generation, feeds, social cards, search indexes, JSON output, and internal-link
analysis. The remaining work is content strategy and better README/docs framing.

## Philosophy

Bengal prioritizes **correctness over backwards compatibility**. Each release reflects our best design. When better approaches emerge, behavior may change.

See [[docs/about/philosophy|Project Philosophy]] for details.

---

:::{child-cards}
:columns: 2
:include: all
:fields: title, description, icon
:::
