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
| **Discovery** | Find `.md` files, parse frontmatter | `bengal/content/discovery/` |
| **Rendering** | Template selection, Markdown → HTML | `bengal/rendering/`, `bengal/parsing/` |
| **Post-Process** | Sitemap, RSS, redirects, social cards | `bengal/postprocess/` |
| **Health** | Link validation, content checks | `bengal/health/` |

## Template Resolution

1. Check for explicit `template` in frontmatter
2. Match by content `type` (page → `page.html`, section → `list.html`)
3. Fall back to `single.html`

:::{note}
The rendering pipeline is **lazy** — templates are compiled on first use and cached.
:::
