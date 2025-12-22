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

Get from zero to published content in 5 minutes. This guide is for content creators who want to focus on writing.

## Prerequisites

:::{checklist} Before You Start
:show-progress:
- [x] Basic knowledge of Markdown
- [ ] [[docs/get-started/installation|Bengal installed]]
- [ ] Terminal or command line access
:::{/checklist}

## Create Your Site

Use the interactive wizard:

```bash
bengal new site myblog
cd myblog
```

The wizard guides you through choosing a preset (Blog, Documentation, Portfolio) and configuring your site.

## Start the Dev Server {#dev-server}

:::{target} hot-reload
:::

```bash
bengal serve
```

Open **http://localhost:5173/** in your browser. The dev server watches for changes and rebuilds automatically. CSS changes apply without a full page refresh.

## Create Your First Post

```bash
bengal new page my-first-post --section blog
```

Edit `content/blog/my-first-post.md`:

```markdown
---
title: My First Post
date: 2025-01-15
tags: [welcome, tutorial]
description: Getting started with Bengal
draft: false
---

# My First Post

Welcome to my new blog! This is my first post using Bengal.

## Why I Chose Bengal

- Fast builds with parallel processing
- Simple Markdown-based workflow
- Customizable themes and templates

Stay tuned for more!
```

**Save the file.** Your new post appears automatically.

## Customize Your Site

Bengal uses a directory-based configuration system. Edit `config/_default/site.yaml`:

```yaml
site:
  title: "My Awesome Blog"
  description: "Thoughts on code, design, and life"
  baseurl: ""
  language: "en"
```

Other configuration files in `config/_default/` control different aspects:

- `build.yaml` — Build settings (parallel, incremental, output directory)
- `theme.yaml` — Theme selection and options
- `features.yaml` — Feature toggles (search, RSS, sitemap)
- `content.yaml` — Content processing options

## Build for Production

```bash
bengal build
```

Your complete site is in `public/`, ready to deploy.

## Deploy

Deploy the `public/` directory to any static hosting:

- **Netlify**: Build command `bengal build`, Publish directory `public`
- **GitHub Pages**: Use the workflow in [[docs/tutorials/automate-with-github-actions|Automate with GitHub Actions]]
- **Vercel**: Build command `bengal build`, Output directory `public`

Bengal auto-detects deployment platforms and adjusts the base URL accordingly.

## Frontmatter Reference {#frontmatter}

Common frontmatter fields:

| Field | Description |
|-------|-------------|
| `title` | Page title (required) |
| `date` | Publication date (ISO format recommended) |
| `description` | SEO description |
| `tags` | Tags for taxonomy (e.g., `[python, web]`) |
| `weight` | Sort order within section (lower = first) |
| `draft` | Set to `true` to exclude from production builds |
| `slug` | Custom URL slug (overrides filename) |
| `type` | Page type for template selection |
| `layout` | Layout variant for the page |
| `lang` | Language code for i18n (e.g., `en`, `es`) |
| `nav_title` | Short title for navigation menus |
| `aliases` | Alternative URLs that redirect to this page |

Custom fields beyond these are stored in `props` and accessible in templates via `page.props.fieldname` or `page.metadata.fieldname`.

## Next Steps

- **[[docs/tutorials/build-a-blog|Build a Blog]]** — Full tutorial
- **[[docs/content/authoring|Content Authoring]]** — Markdown features
- **[[docs/content/organization|Content Organization]]** — Structure your content
- **[[docs/content/component-model#type|Type System]]** — Content types and templates
- **[[docs/theming|Theming]]** — Customize appearance
