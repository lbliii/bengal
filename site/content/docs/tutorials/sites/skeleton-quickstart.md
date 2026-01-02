---
title: Skeleton YAML Quickstart
nav_title: Skeleton YAML
description: Define your entire site structure in one YAML file
draft: false
weight: 25
lang: en
type: doc
tags:
- onboarding
- skeleton
- yaml
- quickstart
keywords:
- skeleton
- yaml
- site structure
- scaffolding
- templates
category: onboarding
icon: file-text
---

# Skeleton YAML Quickstart

Define your entire site structure in one YAML file. Copy, paste, apply—done.

## The 30-Second Start

Choose the approach that fits your needs:

- **Built-in templates**: Fastest for common site types (blog, docs, portfolio, etc.)
- **Custom skeletons**: Full control over structure when templates don't fit your needs

### Option 1: Built-in Template

Use a built-in template for common site types:

```bash
bengal new site mydocs --template docs
cd mydocs
bengal serve
```

Available templates: `default`, `blog`, `docs`, `landing`, `portfolio`, `product`, `resume`, `changelog`.

### Option 2: Custom Skeleton YAML

Define your own structure when templates don't fit or you need a specific layout. Create a YAML file describing your site structure:

Save this as `my-site.yaml`:

```yaml
name: My Site
description: A simple site with two pages

structure:
  - path: index.md
    props:
      title: Welcome
      description: Home page
    content: |
      # Hello World

      Welcome to my site built with Bengal.

  - path: about.md
    props:
      title: About
      description: About this site
    content: |
      # About

      This site was scaffolded from a skeleton YAML file.
```

Apply it:

```bash
bengal project skeleton apply my-site.yaml
bengal serve
```

Your site is live at `http://localhost:5173`. The dev server automatically rebuilds when you save changes (hot reload).

## Skeleton YAML Structure

Every skeleton has two parts: **metadata** and **structure**.

```yaml
# Metadata
name: My Documentation Site
description: Technical docs with navigation
version: "1.0"

# Optional: cascade settings applied to all pages
cascade:
  type: doc

# Structure: list of pages and sections
structure:
  - path: _index.md
    props:
      title: Documentation
      weight: 100
    content: |
      # Documentation
      Welcome!
```

### Page Definition

Each page in `structure` can have:

| Field | Required | Description |
|-------|----------|-------------|
| `path` | Yes | File path relative to `content/` directory |
| `type` | No | Content type (`doc`, `blog`, `landing`, etc.) |
| `props` | No | Frontmatter fields (title, date, tags, etc.) |
| `content` | No | Markdown content for the page body |
| `cascade` | No | Settings inherited by child pages |
| `pages` | No | Nested pages (makes this a section) |

## Real-World Examples

### Blog Skeleton

```yaml
name: Blog
description: Personal blog with posts

structure:
  - path: index.md
    type: blog
    props:
      title: My Blog
      description: Thoughts and ideas
    content: |
      # Welcome to My Blog

      Check out my latest posts below.

  - path: about.md
    props:
      title: About Me
    content: |
      # About Me

      I write about technology and life.

  - path: posts/first-post.md
    type: blog
    props:
      title: My First Post
      date: "2026-01-15"
      tags: [welcome, intro]
    content: |
      # My First Post

      Hello world! This is my first blog post.
```

### Documentation Skeleton

```yaml
name: Project Docs
description: Technical documentation
cascade:
  type: doc

structure:
  - path: _index.md
    props:
      title: Documentation
      weight: 100
    content: |
      # Documentation

      Welcome! Start with [Getting Started](getting-started/).

  - path: getting-started/_index.md
    props:
      title: Getting Started
      weight: 10
    pages:
      - path: installation.md
        props:
          title: Installation
          weight: 10
        content: |
          # Installation

          ```bash
          pip install your-package
          ```

      - path: quickstart.md
        props:
          title: Quick Start
          weight: 20
        content: |
          # Quick Start

          Get running in 5 minutes.

  - path: api/_index.md
    props:
      title: API Reference
      weight: 30
    content: |
      # API Reference

      Complete API documentation.
```

### Portfolio Skeleton

```yaml
name: Portfolio
description: Developer portfolio

structure:
  - path: index.md
    props:
      title: Portfolio
      layout: home
    content: |
      # Hi, I'm [Your Name]

      I build things for the web.

      [View Projects](/projects) | [About Me](/about)

  - path: projects/_index.md
    props:
      title: Projects
    content: |
      # Projects

      My recent work.

  - path: projects/project-1.md
    props:
      title: E-Commerce Platform
      tags: [react, node]
      featured: true
    content: |
      # E-Commerce Platform

      A full-stack e-commerce solution.

  - path: about.md
    props:
      title: About
    content: |
      # About Me

      Software engineer passionate about great UX.
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `bengal new site NAME --template TEMPLATE` | Create site from built-in template |
| `bengal project skeleton apply FILE.yaml` | Apply custom skeleton |
| `bengal project skeleton apply FILE.yaml --dry-run` | Preview without creating files |
| `bengal project skeleton apply FILE.yaml --force` | Overwrite existing files |

## Tips

:::{tip} Preview First
Use `--dry-run` to see what files will be created before applying:

```bash
bengal project skeleton apply my-site.yaml --dry-run
```

:::

:::{tip} Combine with Templates
Start with a built-in template, then layer your custom skeleton on top:

```bash
bengal new site mysite --template docs
cd mysite
bengal project skeleton apply custom-sections.yaml
```

:::

:::{tip} Share Skeletons
Skeleton YAML files are portable. Share them with your team or publish them for others to use.
:::

## Next Steps

- **[[docs/get-started/scaffold-your-site|Scaffold Tutorial]]** — Detailed walkthrough
- **[[docs/reference/site-templates|Template Reference]]** — All built-in templates
- **[[docs/extending/custom-skeletons|Create Custom Skeletons]]** — Advanced patterns
