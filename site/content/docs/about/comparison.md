---
title: Key Capabilities
description: What Bengal does
weight: 10
type: doc
tags:
- features
- capabilities
---

# Key Capabilities

Bengal is a static site generator that produces HTML, CSS, and JavaScript from Markdown content and Jinja2 templates.

## What Bengal Does

- **Jinja2 templates** — Same templating engine used by Flask and Django
- **Incremental builds** — Rebuild only changed files
- **Mixed content** — Docs, blog, landing pages in one site
- **Auto-generated docs** — API docs from Python source, CLI tools, and OpenAPI specs
- **Asset pipeline** — Fingerprinting and minification
- **MyST Markdown** — Directives, admonitions, cross-references
- **Free-threading** — True parallelism on Python 3.14+ with GIL disabled

## Technical Details

| Feature | Description |
|---------|-------------|
| **Language** | Python 3.14+ |
| **Templates** | Jinja2 |
| **Content Types** | Docs, blog, pages (mixed) |
| **Incremental Builds** | Yes |
| **Free-Threading (GIL=0)** | Yes |

:::{seealso}
- [[docs/about/benchmarks|Benchmarks]]
- [[docs/about/limitations|Limitations]]
:::
