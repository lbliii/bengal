---
title: About Bengal
description: Philosophy, concepts, and comparisons
weight: 5
cascade:
  type: doc
layout: list
menu:
  main:
    weight: 40
---

# About Bengal

A Python-native static site generator built for simplicity and performance.

## Why Bengal?

- **Python-native** — Use the tools you know (pip, venv, Jinja2)
- **Parallel builds** — Free-threaded Python support for large sites
- **Incremental builds** — Only rebuild what changed
- **Zero JavaScript required** — Unless you want it

::::{cards}
:columns: 2
:gap: medium

:::{card} 🆚 Comparison
:link: ./comparison/
:color: blue

How Bengal compares to Hugo, Jekyll, MkDocs, and other static site generators.
:::

:::{card} ❓ FAQ
:link: ./faq/
:color: green

Frequently asked questions about Bengal, its design decisions, and use cases.
:::
::::

## Core Concepts

Understand how Bengal thinks about documentation:

::::{cards}
:columns: 3
:gap: small

:::{card} ⚙️ Configuration
:link: ./concepts/configuration/
Layered config with environment overrides
:::

:::{card} 🎨 Assets
:link: ./concepts/assets/
Pipeline for CSS, JS, images, fonts
:::

:::{card} 📁 Content
:link: ./concepts/content-organization/
Pages, sections, bundles, resources
:::

:::{card} 🧩 Templating
:link: ./concepts/templating/
Jinja2, shortcodes, and filters
:::

:::{card} 📤 Output
:link: ./concepts/output-formats/
HTML, JSON, LLM-ready formats
:::

:::{card} 🔧 Build
:link: ./concepts/build-pipeline/
Discovery → Render → Post-process
:::
::::
