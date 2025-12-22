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
| **Language** | Python 3.14+ | Go | Python | Ruby |
| **Templates** | Jinja2 | Go Templates | Jinja2 | Liquid |
| **Full build (1k pages)** | 2.5–4.8 s | 0.45 s | 9+ s | 38+ s |
| **Incremental rebuild** | 35–50 ms | 40–60 ms | 150–300 ms | 3–8 s |
| **Mixed content** | Yes | Yes | No (docs only) | Yes |
| **Incremental builds** | Yes | Yes | No | No |
| **Free-threading (GIL=0)** | Yes | N/A | No | No |

## What Bengal Does

- **Jinja2 templates** — Same templating as Flask/Django
- **Incremental builds** — Rebuild only changed files (35–50 ms)
- **Mixed content** — Docs, blog, landing pages in one site
- **Auto-generated docs** — API docs from Python source, CLI tools, and OpenAPI specs
- **Asset pipeline** — Fingerprinting and minification
- **MyST Markdown** — Directives, admonitions, cross-references
- **Free-threading** — True parallelism on Python 3.14+ with GIL disabled

:::{seealso}
- [[docs/about/benchmarks|Benchmarks]]
- [[docs/about/limitations|Limitations]]
:::
