---
title: Bengal
description: A static site generator written in Python.
template: home.html
weight: 100
type: page
draft: false
lang: en
keywords: [bengal, static site generator, python, ssg]
category: home

# Hero configuration
blob_background: true

# CTA Buttons
cta_buttons:
  - text: Get Started
    url: /docs/get-started/
    style: primary
  - text: Docs
    url: /docs/
    style: secondary

# Features (3-column)
features:
  - title: Jinja2 Templates
    icon: 🐍
    description: Same templating you know from Flask and Django. Extend, override, customize.
    link:
      text: Theming guide
      url: /docs/theming/

  - title: Incremental Builds
    icon: ⚡
    description: Change one file, rebuild one file. Edit and see results in seconds.
    link:
      text: See benchmarks
      url: /docs/about/benchmarks/

  - title: Auto-Generated Docs
    icon: 📄
    description: Generate API documentation from Python source code and docstrings.
    link:
      text: Autodoc guide
      url: /docs/extending/autodoc/

# Quick links section
quick_links:
  - title: Documentation
    description: Guides and reference
    url: /docs/
    icon: 📚
  - title: API Reference
    description: Auto-generated from source
    url: /api/
    icon: 🔧
  - title: CLI Reference
    description: All commands
    url: /cli/
    icon: 💻
  - title: Tutorials
    description: Step-by-step guides
    url: /docs/tutorials/
    icon: 🎓

# Hide recent posts for product homepage
show_recent_posts: false
---

## Install

```bash
pip install bengal
```

## Create a Site

```bash
bengal new site mysite
cd mysite
bengal site serve
```

Your site runs at `localhost:8000`. Edit markdown files and watch them rebuild.

---

## What You Get

- **Markdown with MyST** — Write content with directives, admonitions, and cross-references
- **Jinja2 templates** — Customize layouts, create partials, override anything
- **Incremental builds** — Fast rebuilds during development
- **Asset pipeline** — CSS/JS fingerprinting and minification
- **Auto-generated docs** — API docs from Python source, CLI docs from Click apps
- **Dev server** — Live reload, error overlay, fast refresh

---

## Paths

::::{cards}
:columns: 1-2-3
:gap: medium

:::{card} Writer
:link: /docs/get-started/quickstart-writer/

Write content in Markdown. Use the default theme.
:::

:::{card} Themer
:link: /docs/get-started/quickstart-themer/

Customize templates and styles. Build your own theme.
:::

:::{card} Contributor
:link: /docs/get-started/quickstart-contributor/

Hack on Bengal. Fix bugs, add features.
:::
::::

---

## Links

- [GitHub](https://github.com/lbliii/bengal)
- [Documentation](/docs/)
- [Discussions](https://github.com/lbliii/bengal/discussions)
