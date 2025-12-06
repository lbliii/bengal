---
title: Documentation
weight: 5
draft: false
lang: en
icon: book-open

# 1. Identity (What is it?)
type: doc

# 2. Mode (How does it look?)
# 'overview' sets the hero style and grid layout for top-level docs
variant: overview

# 3. Data (Props)
# Explicit props block (preferred for new model)
props:
  description: Everything you need to build and ship with Bengal
  category: documentation
  tags: [documentation, docs]
  keywords: [documentation, docs, guides, reference]
  menu:
    main:
      weight: 10

# 4. Cascade (Inheritance)
cascade:
  type: doc          # All children are docs
  variant: standard  # Default children to standard layout (not overview)
---

# Documentation

Build static sites in Python. Ship faster with incremental builds. Extend everything in the language you already know.

---

## Start Here

New to Bengal? Pick your path:

| I want to... | Go to... |
|--------------|----------|
| **Install Bengal** | [Installation](/docs/get-started/installation/) |
| **Write content** | [Writer Quickstart](/docs/get-started/quickstart-writer/) |
| **Customize themes** | [Themer Quickstart](/docs/get-started/quickstart-themer/) |
| **Build a blog** | [Build a Blog Tutorial](/docs/tutorials/build-a-blog/) |
| **Deploy my site** | [Deployment](/docs/building/deployment/) |

---

## Learn by Doing

- **[Get Started](/docs/get-started/)** — Installation and quickstart guides
- **[Tutorials](/docs/tutorials/)** — Hands-on learning journeys

---

## Explore Features

| Dimension | What You'll Learn |
|-----------|-------------------|
| **[Content](/docs/content/)** | Markdown authoring, collections, content sources, reuse patterns |
| **[Theming](/docs/theming/)** | Templates, assets, theme customization, styling |
| **[Building](/docs/building/)** | Configuration, CLI, performance, deployment |
| **[Extending](/docs/extending/)** | Autodoc, analysis tools, validation, architecture |

---

## Reference

- **[About Bengal](/docs/about/)** — Philosophy, concepts, comparisons, FAQ
- **[API Reference](/api/)** — Complete Python API documentation
- **[CLI Reference](/cli/)** — All commands and options

---

## Why Bengal?

- **Python-native** — Everything is Python. No Go templates or Ruby gems.
- **Fast iteration** — Incremental builds mean seconds, not minutes.
- **Mixed content** — Docs, blogs, portfolios in one tool.
- **Modern defaults** — Python 3.14+, free-threading, great DX.

[Learn more about Bengal →](/docs/about/)
