---
title: Get Started
description: Install Bengal and create your first site
draft: false
weight: 10
lang: en
tags:
- onboarding
- quickstart
keywords:
- getting started
- installation
- quickstart
category: onboarding
icon: arrow-clockwise
---

# Get Started

## Install

```bash
pip install bengal
```

Requires Python 3.14 or later. See [[docs/get-started/installation|installation guide]] for details, including recommended options for faster builds.

## Create a Site

```bash
bengal new site mysite
cd mysite
bengal serve
```

Your site runs at `http://localhost:5173`. The dev server rebuilds automatically when you save changes.

## Pick a Path

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
- [[docs/content|Content]] — Writing and organizing content
- [[docs/theming|Theming]] — Templates and styling
- [[cli|CLI Reference]] — All commands
