---
title: About
description: A pure-Python documentation generator built on free-threading — every layer scales with your cores
weight: 5
layout: list
menu:
  main:
    weight: 40
icon: info
---

# About

Bengal is a static site generator where the entire stack is Python you can read, debug, and extend. Every library in the pipeline — [Patitas](https://github.com/lbliii/patitas) (markdown), [Rosettes](https://github.com/lbliii/rosettes) (syntax highlighting), [Kida](https://github.com/lbliii/kida) (templates), [Pounce](https://github.com/lbliii/pounce) (dev server) — is purpose-built for Python 3.14+ [free-threading](./free-threading). No JavaScript toolchains. No compiled C extensions in the critical path. `pip install bengal` and go.

## Why Bengal?

| Benefit | What It Means |
|---------|---------------|
| **Scales with cores** | True thread parallelism on Python 3.14t — no GIL contention. See [Benchmarks](./benchmarks) |
| **AI-native output** | [llms.txt](https://llmstxt.org/), agent manifests, per-page JSON, [Content Signals](https://contentsignals.org/) — machines can discover and navigate your docs |
| **Sub-second rebuilds** | Provenance-based incremental builds with content-addressed hashing |
| **Python-native workflows** | Jupyter rendering, autodoc for Python/CLI/OpenAPI, `pip install` and go |
| **Batteries included** | Sitemap, RSS, social cards, search indexes, broken link detection, validation |
| **Extensible** | Pluggable engines, theme inheritance, swizzling, 9 plugin extension points |

## Use Cases

- **Documentation Sites** — Versioned docs, API reference, search, and internal linking
- **Blogs & Journals** — Tags, categories, feeds, related content, and social sharing
- **Knowledge Bases** — Markdown-first publishing with validation and JSON search indexes
- **Product & Marketing Sites** — Landing pages, content collections, and social cards

## Philosophy

Bengal prioritizes **correctness over backwards compatibility**. Each release reflects our best design. When better approaches emerge, behavior may change.

See [[docs/about/philosophy|Project Philosophy]] for details.

---

:::{child-cards}
:columns: 2
:include: all
:fields: title, description, icon
:::
