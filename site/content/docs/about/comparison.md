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

### Content & Authoring

- **MyST Markdown** — Directives, admonitions, cross-references, tabs, cards
- **50+ Built-in Directives** — Code tabs, dropdowns, galleries, video embeds, versioning badges
- **Content Collections** — Type-safe frontmatter validation with dataclass or Pydantic schemas
- **Mixed Content Types** — Docs, blog, landing pages, changelogs in one site

### Performance

- **[[ext:kida:|Kida Templates]]** — 1.81x faster than Jinja2 under concurrent workloads
- **Incremental Builds** — 35-80ms rebuilds for single-page edits
- **Free-Threading** — True parallelism on Python 3.14+ (no GIL contention)
- **Parallel Rendering** — 2-4x speedup on multi-core systems

### Developer Experience

- **Auto-generated API Docs** — From Python source, CLI tools, and OpenAPI specs
- **Image Processing** — Resize, crop, format conversion (WebP/AVIF), srcset generation
- **Zero-Config Deploy** — Auto-detects GitHub Pages, Netlify, Vercel
- **Theme System** — Install themes from PyPI, swizzle templates, 650+ CSS tokens

### Quality & Validation

- **Health Checks** — Broken links, missing images, frontmatter validation
- **Auto-Fix** — `bengal fix` repairs common issues automatically
- **Site Analysis** — Graph visualization, orphan detection, content metrics

## Technical Details

| Feature | Description |
|---------|-------------|
| **Language** | Python 3.14+ |
| **Templates** | [[ext:kida:|Kida]] (Jinja2-compatible, 1.81x faster concurrent) |
| **Markdown** | [[ext:patitas:|Patitas]] (typed AST, O(n) parsing, thread-safe) |
| **Highlighting** | [[ext:rosettes:|Rosettes]] (3.4x faster than Pygments, 55+ languages) |
| **Content Types** | Docs, blog, pages, changelog (mixed) |
| **Incremental Builds** | Yes (35-80ms single-page, cache-validated) |
| **Free-Threading (GIL=0)** | Yes (Kida, Patitas, Rosettes are all GIL-independent) |
| **Image Processing** | fill, fit, resize, WebP/AVIF, srcset |
| **Content Collections** | Dataclass and Pydantic schema validation |
| **Deploy Detection** | GitHub Pages, Netlify, Vercel (zero-config) |

:::{seealso}
- [[docs/about/benchmarks|Benchmarks]]
- [[docs/about/limitations|Limitations]]
:::
