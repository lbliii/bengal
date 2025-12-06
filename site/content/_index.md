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

Your site runs at `localhost:5173`. Edit markdown files and watch them rebuild.
