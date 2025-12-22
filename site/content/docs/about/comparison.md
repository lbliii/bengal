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
| **Mixed content** | Yes | Yes | No (docs only) | Yes |
| **Incremental builds** | Yes | Yes | No | No |
| **Free-threading (GIL=0)** | Yes | N/A | No | No |

:::{note}
See [[docs/about/benchmarks|Benchmarks]] for Bengal's measured build times. We do not publish comparative benchmarks for other SSGs.
:::

## What Bengal Does

- **Jinja2 templates** — Same templating as Flask/Django
- **Incremental builds** — Rebuild only changed files
- **Mixed content** — Docs, blog, landing pages in one site
- **Auto-generated docs** — API docs from Python source, CLI tools, and OpenAPI specs
- **Asset pipeline** — Fingerprinting and minification
- **MyST Markdown** — Directives, admonitions, cross-references
- **Free-threading** — True parallelism on Python 3.14+ with GIL disabled

:::{seealso}
- [[docs/about/benchmarks|Benchmarks]]
- [[docs/about/limitations|Limitations]]
:::
