---
title: Documentation
draft: false
weight: 5
lang: en
type: doc
cascade:
  type: doc
  variant: standard
category: documentation
description: Guides for building documentation sites, blogs, knowledge bases, and product sites with Bengal
keywords:
- bengal
- python static site generator
- documentation site generator
- blog generator
- knowledge base
- seo
- sitemap
- rss
- search
menu:
  main:
    weight: 10
tags:
- documentation
- docs
variant: overview
icon: book-open
---

# Documentation

Bengal is a Python static site generator for documentation sites, blogs,
knowledge bases, and product sites — authoring, search, SEO, theming, and
deployment in one toolchain.

**New here?** Start with **Get Started**. **Evaluating Bengal?** Read
**About**. **Writing content?** Go to **Content**. **Deploying or tuning
builds?** See **Building**. **Looking up syntax?** Use **Reference**.

:::{cards}
:columns: 2
:gap: medium

:::{card} About
:icon: info
:link: ./about/
:description: Philosophy, benchmarks, and when to choose Bengal
For evaluators comparing SSGs and understanding design trade-offs.
:::{/card}

:::{card} Get Started
:icon: arrow-clockwise
:link: ./get-started/
:description: Install Bengal and create your first site
Install, scaffold, and pick a writer, themer, or contributor path.
:::{/card}

:::{card} Content & Theming
:icon: edit
:link: ./content/
:description: Author, organize, theme, and extend your site
Markdown, directives, templates, plugins, and custom sources.
:::{/card}

:::{card} Building & Shipping
:icon: rocket
:link: ./building/
:description: Configure, validate, optimize, and deploy
Config, SEO, performance, health checks, and CI/CD deployment.
:::{/card}

:::{card} Tutorials
:icon: notepad
:link: ./tutorials/
:description: Guided learning journeys and migration guides
Build a blog, migrate from Hugo or MkDocs, wire up GitHub Actions.
:::{/card}

:::{card} Reference
:icon: bookmark
:link: ./reference/
:description: Directives, CLI, Kida syntax, and architecture
Lookup-oriented specs when you know what you're searching for.
:::{/card}

:::{card} Directive Gallery
:icon: grid
:link: ./reference/directives/kitchen-sink/
:description: See every directive type live on one page
Interactive kitchen sink — copy examples straight into your content.
:::{/card}

:::{/cards}

## By Persona

:::{tab-set}

:::{tab-item} Writer
Start with [[docs/get-started/quickstart-writer|Writer Quickstart]], then
[[docs/content/authoring|Authoring]] and [[docs/content/organization|Organization]].
:::

:::{tab-item} Theme Developer
Start with [[docs/get-started/quickstart-themer|Themer Quickstart]], then
[[docs/theming|Theming]] and [[docs/reference/kida-syntax|Kida Syntax]].
:::

:::{tab-item} Operator
Start with [[docs/building/configuration|Configuration]], then
[[docs/content/validation|Validation]] and [[docs/building/deployment|Deployment]].
:::

:::{tab-item} Migrator
Pick your source SSG in [[docs/tutorials/migration|Migration Guides]].
:::

:::{/tab-set}
