---
title: Rendering Pipeline
nav_title: Rendering
description: How Bengal transforms Markdown to HTML
weight: 20
cascade:
  type: doc
icon: arrow-clockwise
---
# Rendering Pipeline

How Bengal transforms source content into final output.

| Stage | What it does | Key modules |
|-------|--------------|-------------|
| **Discovery** | Find `.md` files, parse frontmatter | `bengal/discovery/` |
| **Rendering** | Template selection, Markdown → HTML | `bengal/rendering/` |
| **Post-Process** | Sitemap, RSS, link validation | `bengal/postprocess/` |

## Template Resolution

1. Check for explicit `layout` in frontmatter
2. Match by content `type` (doc, post, page)
3. Fall back to `single.html`

:::{note}
The rendering pipeline is **lazy** — templates are compiled on first use and cached.
:::
