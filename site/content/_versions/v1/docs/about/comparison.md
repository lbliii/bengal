---
title: Comparison
description: How Bengal compares to other static site generators
weight: 10
type: doc
tags:
- comparison
- benchmarks
---

# Comparison

| | Bengal | Hugo | MkDocs | Jekyll |
|---|--------|------|--------|--------|
| **Language** | Python | Go | Python | Ruby |
| **Templates** | Jinja2 | Go Templates | Jinja2 | Liquid |
| **Speed** | ~200 pages/s | ~10,000 pages/s | ~100 pages/s | ~50 pages/s |
| **Mixed content** | Yes | Yes | No (docs only) | Yes |
| **Incremental builds** | Yes | Yes | No | No |

## What Bengal Does

- **Jinja2 templates** — Same templating as Flask/Django
- **Incremental builds** — Rebuild only changed files
- **Mixed content** — Docs, blog, landing pages in one site
- **Auto-generated docs** — API docs from Python source
- **Asset pipeline** — Fingerprinting and minification
- **MyST Markdown** — Directives, admonitions, cross-references

:::{seealso}
- [[docs/about/benchmarks|Benchmarks]]
- [[docs/about/limitations|Limitations]]
:::
