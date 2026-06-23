---


title: Skeleton YAML Quickstart
nav_title: Skeleton YAML
description: Define your entire site structure in one YAML file
draft: false
weight: 25
lang: en
tags:
- onboarding
- skeleton
- yaml
- quickstart
- persona-writer
keywords:
- skeleton
- yaml
- site structure
- scaffolding
- templates
category: onboarding
icon: file-text
aliases:
  - /docs/tutorials/sites/skeleton-quickstart/
aliases:
  - /docs/examples/sites/skeleton-quickstart/
  - /docs/tutorials/sites/skeleton-quickstart/
---

# Skeleton YAML Quickstart

Define your entire site structure in one YAML file, then scaffold a site from it with `bengal new site`.

:::{note}
**Do I need this?** Yes when you need a repeatable site blueprint or custom
scaffold beyond built-in templates. For a standard blog or docs site, use
[[docs/get-started/scaffold-your-site|Scaffold Your First Site]] or
`bengal new site --template docs` instead.
:::

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

Save it as `skeleton.yaml` inside a template directory (for example
`bengal/scaffolds/my-site/skeleton.yaml`, or register a custom template at runtime with
`bengal.scaffolds.register_template`):

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

Scaffold a site from it:

```bash
bengal new site mysite --template my-site
cd mysite
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

Skeletons are materialized by `bengal new site`, not by a standalone apply command:

| Command | Description |
|---------|-------------|
| `bengal new site NAME --template TEMPLATE` | Create a site from a built-in or registered template |
| `bengal new site NAME` | Launch the interactive wizard and pick a template |

## Tips

:::{tip} Try It in a Throwaway Directory
Scaffold into a temporary directory first to confirm the structure renders as expected:

```bash
bengal new site /tmp/skeleton-check --template my-site
```

:::

:::{tip} Start From a Built-in Template
Begin with a built-in template, then edit the scaffolded structure by hand:

```bash
bengal new site mysite --template docs
cd mysite
# Add or edit sections directly under content/
```

:::

:::{tip} Share Skeletons
Skeleton YAML files are portable. Share them with your team or publish them for others to use.
:::

## Next Steps

- **[[docs/get-started/scaffold-your-site|Scaffold Tutorial]]** — Detailed walkthrough
- **[[docs/reference/site-templates|Template Reference]]** — All built-in templates
- **[[docs/build-sites/extend/custom-skeletons|Create Custom Skeletons]]** — Advanced patterns
