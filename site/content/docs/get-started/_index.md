---
title: Get Started
description: Install Bengal and create your first site
draft: false
weight: 10
lang: en
tags:
- onboarding
- quickstart
- persona-writer
- persona-themer
- persona-contributor
keywords:
- getting started
- installation
- quickstart
category: onboarding
icon: arrow-clockwise
---

# Get Started

New to Bengal? Start here. This section takes you from install to a running site
in minutes — no theming or Python required for the writer path.

**Sizing it up?** Skim [[docs/about|About]] first. **Already building?** Jump to
[[docs/ship/configuration|Configure]] or [[docs/build-sites/write/authoring|Author
content]]. **Shipping to production?** See [[docs/ship/deployment|Deploy]].

Read the cards below: pick a quickstart path that matches your role, or follow the install steps first.

## Install

```bash
pip install bengal
```

Requires Python 3.14 or later. See [[docs/get-started/installation|installation guide]] for details, including recommended options for faster builds.

## Create a Site

:::{include} _snippets/scaffold/new-site.md
:::

## Pick a Path {#pick-a-path}

:::{cards}
:columns: 1-2-3
:gap: medium

:::{card} Writer
:icon: pencil
:link: ./quickstart-writer
:description: Write content in Markdown with the default theme
:badge: Start Here
Get up and running in 5 minutes with Bengal's writer-focused workflow.
:::{/card}

:::{card} Theme Developer
:icon: palette
:link: ./quickstart-themer
:description: Customize templates and styles to match your brand
Build your own theme or override just the parts you want to change.
:::{/card}

:::{card} Contributor
:icon: code
:link: ./quickstart-contributor
:description: Hack on Bengal core, fix bugs, add features
Set up your development environment and start contributing.
:::{/card}
:::{/cards}

## Next Steps

- [[docs/tutorials|Tutorials]] — Step-by-step guides
- [[docs/build-sites|Content]] — Writing and organizing content
- [[docs/build-sites/customize|Theming]] — Templates and styling
- [[docs/reference/architecture|Architecture Overview]] — Contributor orientation
