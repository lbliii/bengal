---
title: Get Started
description: Install Bengal and create your first site
draft: false
weight: 10
lang: en
type: doc
tags:
- onboarding
- quickstart
keywords:
- getting started
- installation
- quickstart
category: onboarding
cascade:
  type: doc
icon: arrow-clockwise
---
# Get Started

## Install

```bash
pip install bengal
```

Requires Python 3.14+. See [[docs/get-started/installation|installation guide]] for details.

## Create a Site

```bash
bengal new site mysite
cd mysite
bengal serve
```

Your site runs at `localhost:5173`.

## Pick a Path

::::{cards}
:columns: 1-2-3
:gap: medium

:::{card} 📝 Writer
:link: /docs/get-started/quickstart-writer/

Write content in Markdown. Use the default theme.
:::

:::{card} 🎨 Themer
:link: /docs/get-started/quickstart-themer/

Customize templates and styles. Build your own theme.
:::

:::{card} 🛠️ Contributor
:link: /docs/get-started/quickstart-contributor/

Hack on Bengal. Fix bugs, add features.
:::
::::

## Next Steps

- [[docs/tutorials|Tutorials]] — Step-by-step guides
- [[docs/content|Content]] — Writing and organizing content
- [[docs/theming|Theming]] — Templates and styling
- [[cli|CLI Reference]] — All commands
