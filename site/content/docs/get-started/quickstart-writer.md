---
title: Writer Quickstart
nav_title: Writers
description: Create your first site and start writing content
draft: false
weight: 20
lang: en
type: doc
tags:
- onboarding
- writing
- quickstart
keywords:
- writing
- content
- markdown
- frontmatter
category: onboarding
id: writer-qs
icon: pencil
---

# Writer Quickstart

Create your first Bengal site and publish content in 5 minutes. No theming or code required.

## Prerequisites

:::{checklist} Before You Start
:show-progress:
- [ ] Basic Markdown knowledge
- [ ] [[docs/get-started/installation|Bengal installed]]
- [ ] Terminal access
:::{/checklist}

## Create Your Site

```bash
bengal new site myblog
cd myblog
```

The wizard prompts for a preset (Blog, Docs, Portfolio) and base URL. Accept defaults to continue.

## Start the Dev Server {#dev-server}

:::{target} hot-reload
:::

```bash
bengal serve
```

Your browser opens automatically at `http://localhost:5173/`. The server rebuilds on save—CSS changes apply instantly without page refresh.

## Create Your First Post

```bash
bengal new page my-first-post --section blog
```

This creates `content/blog/my-first-post.md`. Edit it:

```markdown
---
title: My First Post
date: 2026-01-15
tags: [welcome]
description: Getting started with Bengal
---

# My First Post

Welcome to my blog! Bengal makes publishing simple.

## What's Next

- Add more posts with `bengal new page`
- Customize your theme
- Deploy to the web
```

**Save.** The page appears instantly in your browser.

## Customize Your Site

Edit `config/_default/site.yaml`:

```yaml
site:
  title: "My Awesome Blog"
  description: "Thoughts on code, design, and life"
  language: "en"
```

:::{dropdown} Other config files
:icon: gear

Bengal splits configuration across focused files in `config/_default/`:

| File | Purpose |
|------|---------|
| `build.yaml` | Parallel builds, output directory |
| `theme.yaml` | Theme selection and options |
| `features.yaml` | Search, RSS, sitemap toggles |
| `content.yaml` | Markdown processing options |

See [[docs/building/configuration|Configuration Reference]] for details.
:::

## Build and Deploy

```bash
bengal build
```

Output goes to `public/`. Deploy to any static host:

| Platform | Build Command | Output |
|----------|---------------|--------|
| Netlify | `bengal build` | `public` |
| Vercel | `bengal build` | `public` |
| GitHub Pages | `bengal build` | `public` |

Bengal auto-detects Netlify, Vercel, and GitHub Pages to set `baseurl` automatically. See [[docs/building/deployment|Deployment Guide]] for CI/CD workflows.

## Frontmatter Essentials {#frontmatter}

Every page starts with YAML frontmatter:

```yaml
---
title: Page Title      # Required
date: 2026-01-15       # Publication date
description: SEO text  # Search/social preview
tags: [tag1, tag2]     # Taxonomy
draft: true            # Exclude from production
---
```

:::{dropdown} All frontmatter fields
:icon: list-unordered

| Field | Description |
|-------|-------------|
| `title` | Page title (required) |
| `date` | Publication date (ISO format) |
| `description` | SEO/social preview text |
| `tags` | Taxonomy tags (e.g., `[python, web]`) |
| `weight` | Sort order in section (lower = first) |
| `draft` | `true` excludes from production builds |
| `slug` | Custom URL (overrides filename) |
| `type` | Page type for template selection |
| `layout` | Layout variant |
| `lang` | Language code (`en`, `es`, etc.) |
| `nav_title` | Short title for navigation |
| `aliases` | Redirect URLs to this page |

Custom fields are accessible via `page.props.fieldname` in templates.
:::

## Next Steps

| Goal | Resource |
|------|----------|
| Learn Markdown features | [[docs/content/authoring|Content Authoring]] |
| Organize content | [[docs/content/organization|Content Organization]] |
| Customize appearance | [[docs/theming|Theming]] |
| Full blog tutorial | [[docs/tutorials/build-a-blog|Build a Blog]] |
