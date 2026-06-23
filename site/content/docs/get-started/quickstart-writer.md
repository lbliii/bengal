---
title: Writer Quickstart
nav_title: Writers
description: Create your first site and start writing content
draft: false
weight: 20
lang: en
tags:
- onboarding
- writing
- quickstart
- persona-writer
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

:::{note}
**Do I need this?** Yes if you are new to Bengal and want to write Markdown content
with the default theme. Skip if you are customizing templates — see
[[docs/get-started/quickstart-themer|Themer Quickstart]] instead.
:::

## Prerequisites

:::{checklist} Before You Start
:show-progress:
- [x] Basic Markdown knowledge
- [ ] [[docs/get-started/installation|Bengal installed]]
- [ ] Terminal access
:::{/checklist}

## Create Your Site

:::{include} _snippets/scaffold/blog-site.md
:::

:::{dropdown} Or use a custom skeleton YAML
:icon: file-text

Define your site structure in one `skeleton.yaml`, drop it into a template directory, and scaffold from it:

```yaml
name: My Blog
structure:
  - path: index.md
    type: blog
    props:
      title: My Blog
    content: |
      # Welcome to My Blog

  - path: posts/hello-world.md
    type: blog
    props:
      title: Hello World
      date: "2026-01-15"
    content: |
      # Hello World
      My first post!
```

Scaffold a site from it (the manifest lives as `bengal/scaffolds/my-blog/skeleton.yaml`,
or register a custom template with `bengal.scaffolds.register_template`):

```bash
bengal new site myblog --template my-blog
```

See [[docs/examples/sites/skeleton-quickstart|Skeleton YAML Quickstart]] for more examples.
:::

## Start the Dev Server {#dev-server}

:::{target} hot-reload
:::

:::{include} _snippets/scaffold/serve.md
:::

## Create Your First Post

```bash
bengal new page my-first-post --section posts
```

This creates `content/posts/my-first-post.md`. Edit it:

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
:icon: settings

Bengal splits configuration across focused files in `config/_default/`:

| File | Purpose |
|------|---------|
| `build.yaml` | Parallel builds, output directory |
| `theme.yaml` | Theme selection and options |
| `features.yaml` | Search, RSS, sitemap toggles |
| `content.yaml` | Markdown processing options |

See [[docs/ship/configuration|Configuration Reference]] for details.
:::

## Build and Deploy

:::{include} _snippets/deploy/production-build.md
:::

Deploy to any static host:

| Platform | Build Command | Output |
|----------|---------------|--------|
| Netlify | `bengal build` | `public` |
| Vercel | `bengal build` | `public` |
| GitHub Pages | `bengal build` | `public` |

Bengal auto-detects Netlify, Vercel, and GitHub Pages to set `baseurl` automatically. See [[docs/ship/deployment|Deployment Guide]] for CI/CD workflows.

## Frontmatter Essentials {#frontmatter}

Every page starts with YAML frontmatter:

```yaml
---
title: Page Title           # Required
date: 2026-01-15            # Publication date (ISO format)
description: SEO text       # Search/social preview
tags: [tag1, tag2]          # Taxonomy
draft: true                 # Exclude from production
---
```

:::{dropdown} All frontmatter fields
:icon: list

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
| `variant` | Visual presentation variant |
| `lang` | Language code (`en`, `es`, etc.) |
| `nav_title` | Short title for navigation |
| `aliases` | Redirect URLs to this page |

Custom fields are accessible in templates via `page.props.fieldname`, `page.params.fieldname`, or `page.metadata.fieldname` (all equivalent).
:::

## Next Steps

- **[[docs/build-sites/write/authoring|Content Authoring]]** — Markdown features and syntax
- **[[docs/build-sites/structure/organization|Content Organization]]** — Structure your site
- **[[docs/build-sites/customize|Theming]]** — Customize appearance
- **[[docs/examples/sites/build-a-blog|Build a Blog]]** — Complete tutorial
