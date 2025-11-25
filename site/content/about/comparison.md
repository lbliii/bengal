---
title: Bengal vs. The World
description: How Bengal compares to Hugo, Jekyll, Pelican, and MkDocs.
weight: 10
type: doc
tags: [comparison, alternatives, hugo, jekyll, pelican]
---

# Why Bengal?

There are hundreds of Static Site Generators (SSGs). Why use Bengal?

## The Philosophy

Bengal optimizes for **Developer Experience (DX)** over raw build speed (though it's still very fast).

*   **Pythonic**: If you know Python, you know Bengal. No Go templates, no Ruby gems.
*   **Jinja2**: The industry-standard templating engine. Powerful, readable, and extensible.
*   **Batteries Included**: Asset pipeline, image optimization, and syntax highlighting work out of the box.

## Comparison Matrix

| Feature | Bengal 🐯 | Hugo ⚡️ | Jekyll 🧪 | MkDocs 📘 |
| :--- | :--- | :--- | :--- | :--- |
| **Language** | Python | Go | Ruby | Python |
| **Templating** | Jinja2 | Go Templates | Liquid | Jinja2 |
| **Speed** | Fast (~35 pages/s) | Instant | Slow | Fast |
| **Asset Pipeline** | Built-in (PostCSS-like) | Built-in (ESBuild) | Plugin required | None |
| **Extensibility** | Python Classes | Go Modules | Ruby Gems | Python Plugins |
| **Best For** | Python Devs, Custom Sites | 10k+ Page Sites | GitHub Pages | Documentation |

## Detailed Breakdown

::::{tab-set}
:::{tab-item} vs. Hugo
**Hugo** is the speed king. If you have 50,000 pages, use Hugo.

**However**, Hugo's Go Templates can be notoriously difficult to debug and extend. Bengal offers a sane templating system (Jinja2) and a plugin system written in a language you likely already use (Python).

**Choose Bengal if:**
*   You prefer Python over Go.
*   You want readable templates.
*   You need deep customization via Python code.
:::

:::{tab-item} vs. Pelican
**Pelican** is the grandfather of Python SSGs. It is stable but shows its age.

Bengal is a modern reimplementation of the Python SSG concept.
*   **Better Markdown**: We use Mistune (2x faster).
*   **Modern Assets**: Built-in minification and hashing.
*   **Live Reload**: A robust dev server that actually works.

**Choose Bengal if:**
*   You want a modern CLI experience.
*   You need built-in asset management.
:::

:::{tab-item} vs. MkDocs
**MkDocs** is fantastic for documentation (we love Material for MkDocs!).

However, MkDocs is *strictly* for documentation. Building a blog, portfolio, or marketing site with MkDocs is a struggle against the tool.

**Choose Bengal if:**
*   You are building a mixed content site (Blog + Docs + Landing Page).
*   You need full control over HTML structure.
:::
::::

## When NOT to use Bengal

We want you to be happy, even if it means using another tool.

*   **Extremely Large Sites (>10,000 pages)**: You will feel the Python GIL. Use Hugo.
*   **React/Vue SPA**: Use Next.js, Nuxt, or Astro. Bengal is for Multi-Page Apps (MPA).
*   **Non-Technical Users**: Use WordPress or Ghost.

