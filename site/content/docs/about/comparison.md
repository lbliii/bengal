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

Bengal is a static site generator that produces HTML, CSS, and JavaScript from Markdown content and [[ext:kida:|Kida]] templates.

## What Bengal Does

- **[[ext:kida:|Kida templates]]** — High-performance template engine with Jinja2 compatibility, 1.81x faster under concurrent workloads
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
| **Templates** | [[ext:kida:|Kida]] (Jinja2-compatible, 1.81x faster concurrent) |
| **Content Types** | Docs, blog, pages (mixed) |
| **Incremental Builds** | Yes |
| **Free-Threading (GIL=0)** | Yes (Kida is GIL-independent) |

:::{seealso}
- [[docs/about/benchmarks|Benchmarks]]
- [[docs/about/limitations|Limitations]]
:::
