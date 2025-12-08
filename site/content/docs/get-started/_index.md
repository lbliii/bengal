---
title: Get Started
description: Install Bengal and create your first site
draft: false
weight: 10
aliases:
  - /docs/getting-started/
lang: en
type: doc
tags: [onboarding, quickstart]
keywords: ["getting started", installation, quickstart]
category: onboarding
cascade:
  type: doc
params:
  icon: arrow-clockwise
---
# Get Started

## Install

```bash
pip install bengal
```

Requires Python 3.14+. See [installation guide](/docs/get-started/installation/) for details.

## Create a Site

```bash
bengal new site mysite
cd mysite
bengal site serve
```

Your site runs at `localhost:8000`.

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

- [Tutorials](/docs/tutorials/) — Step-by-step guides
- [Content](/docs/content/) — Writing and organizing content
- [Theming](/docs/theming/) — Templates and styling
- [CLI Reference](/cli/) — All commands
