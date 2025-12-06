---
title: Bengal
description: Build static sites in Python, without the compromises.
template: home.html
weight: 100
type: page
draft: false
lang: en
keywords: [bengal, static site generator, python, ssg, python-native, incremental builds]
category: home

# Hero configuration
blob_background: true

# CTA Buttons
cta_buttons:
  - text: Get Started
    url: /docs/get-started/
    style: primary
  - text: View Docs
    url: /docs/
    style: secondary

# Value Proposition Features (3-column)
features:
  - title: Zero Context Switching
    icon: 🐍
    description: Everything is Python—templates, plugins, config. No Go templates or Ruby gems to learn. Use the language you already know.
    link:
      text: Learn more
      url: /docs/about/

  - title: Fast Enough, Built Right
    icon: ⚡
    description: Parallel processing and free-threading ensure builds are fast. A 1,000-page site builds in seconds, not minutes.
    link:
      text: See benchmarks
      url: /docs/about/benchmarks/

  - title: Modern by Default
    icon: ✨
    description: Built for Python 3.14+, with incremental builds, great defaults, and an interactive CLI. No legacy baggage.
    link:
      text: Get started
      url: /docs/get-started/

# Stats section
stats:
  - value: "200+"
    label: "Pages/sec (parallel)"
  - value: "18-42x"
    label: "Faster incremental builds"
  - value: "Python"
    label: "100% Python-native"

# Quick links section
quick_links:
  - title: Documentation
    description: Complete guides and reference
    url: /docs/
    icon: 📚
  - title: API Reference
    description: Auto-generated Python API docs
    url: /api/
    icon: 🔧
  - title: CLI Reference
    description: All commands and options
    url: /cli/
    icon: 💻
  - title: Tutorials
    description: Hands-on learning journeys
    url: /docs/tutorials/
    icon: 🎓

# Hide recent posts for product homepage
show_recent_posts: false
---

## Built for Python Teams

Bengal is the static site generator for Python developers who want to ship fast without fighting their tools.

### Why Python Developers Choose Bengal

**Stay in your flow state.** Everything is Python—Jinja2 templates, Python config, Python extensions. No context switching to Go templates or Ruby gems.

**Ship mixed-content sites.** Not just docs, not just blogs—build documentation, blogs, portfolios, and landing pages in one cohesive tool.

**Iterate quickly.** Incremental builds mean you see changes in seconds. Edit a blog post and watch it update instantly.

---

## Choose Your Path

Bengal serves different roles. Pick the path that matches your goal:

::::{cards}
:columns: 1-2-3
:gap: medium

:::{card} 📝 Writer
:link: /docs/get-started/quickstart-writer/

Start a blog or documentation site. Focus on writing, not tooling. Use beautiful themes and templates as-is.
:::

:::{card} 🎨 Themer
:link: /docs/get-started/quickstart-themer/

Create custom themes and branded experiences. Override templates, customize styles, build something unique.
:::

:::{card} 🛠️ Contributor
:link: /docs/get-started/quickstart-contributor/

Fix bugs, add features, improve Bengal's core. Contribute to the project and help shape its future.
:::
::::

---

## When to Use Bengal

**Choose Bengal if:**
- You're a Python developer (or team)
- You want mixed-content sites (docs + blog + landing pages)
- You value developer experience over raw speed
- You need incremental builds for fast iteration

**Consider alternatives if:**
- You have 50,000+ pages → [Hugo](https://gohugo.io) (raw speed wins)
- You need React/Vue SPAs → [Next.js](https://nextjs.org) or [Astro](https://astro.build)
- You're building docs-only → [MkDocs](https://www.mkdocs.org) with Material theme

We want you to be happy, even if it means using another tool.

---

## Quick Start

```bash
# Install
pip install bengal

# Create a new site (interactive wizard)
bengal new site mysite
cd mysite

# Build and serve
bengal site build
bengal site serve
```

**For maximum speed** (Python 3.14+):

```bash
PYTHON_GIL=0 bengal site build --fast
```

---

## What Makes Bengal Different

| Capability | Bengal | What It Means |
|------------|--------|---------------|
| **Python-native** | ✅ | Templates, plugins, config—all Python |
| **Mixed content** | ✅ | Docs, blogs, portfolios in one tool |
| **Incremental builds** | ✅ | Rebuild in seconds, not minutes |
| **Free-threading** | ✅ | Leverage Python 3.14+ for speed |
| **Auto-generated docs** | ✅ | API docs from Python source |
| **Interactive CLI** | ✅ | Wizards and helpful prompts |

---

## Join the Community

- **[GitHub](https://github.com/lbliii/bengal)** — Star the repo, file issues, contribute
- **[Documentation](/docs/)** — Complete guides and reference
- **[Discussions](https://github.com/lbliii/bengal/discussions)** — Questions and community help
