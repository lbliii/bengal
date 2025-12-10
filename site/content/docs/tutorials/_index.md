---
title: Tutorials
description: Guided learning journeys to master Bengal
weight: 15
cascade:
  type: doc
icon: notepad
---
# Tutorials

Hands-on lessons that teach you Bengal step-by-step. Each tutorial starts from scratch and builds to a working result.

## Choose Your Starting Point

:::{cards}
:columns: 1
:gap: medium

:::{card} Build a Blog from Scratch
:icon: pencil
:link: ./build-a-blog/
:description: Go from zero to a deployed personal blog in 15 minutes
:badge: Start Here
:color: blue
The perfect first tutorial for writers and beginners. No prior Bengal knowledge required.
:::{/card}

:::{card} Swizzle and Customize the Default Theme
:icon: palette
:link: ./swizzle-default-theme/
:description: Learn theme inheritance without breaking updates
:color: orange
Copy and customize just the templates you need. Perfect for personalizing your site while staying compatible with theme updates.
:::{/card}

:::{card} Migrate from Hugo
:icon: arrow-right
:link: ./migrate-from-hugo/
:description: Step-by-step migration from existing static site generators
:badge: 30 min
:color: green
Complete migration guide from Hugo, Jekyll, Gatsby, or other SSGs. Includes content, templates, and configuration mapping.
:::{/card}

:::{card} Automate with GitHub Actions
:icon: settings
:link: ./automate-with-github-actions/
:description: Set up CI/CD pipelines for automatic deployment
:color: purple
Configure GitHub Actions for automatic builds, testing, and deployment to GitHub Pages, Netlify, or Vercel.
:::{/card}
:::{/cards}

## Learning Journey

```mermaid
flowchart LR
    A[Build a Blog] --> B[Content Authoring]
    A --> C[Swizzle Theme]
    C --> D[Theming Basics]
    B --> E[Advanced Content]
    D --> F[Custom Themes]
    E --> G[Automation]
    F --> G
```

:::{tip}
**After tutorials**: Move to [Content](../content/) for authoring reference, [Theming](../theming/) for customization, or [Building](../building/) for deployment options.
:::

:::{dropdown} What makes a good tutorial?
:icon: info
Tutorials are **learning-oriented** — they teach skills through guided practice.

Each tutorial:
- **Starts from scratch** — No prior Bengal knowledge assumed
- **Builds progressively** — Each step builds on the previous
- **Provides working code** — Copy, run, and see results
- **Explains the "why"** — Understand concepts as you go

This follows the [Diátaxis](https://diataxis.fr/) documentation framework.
:::
