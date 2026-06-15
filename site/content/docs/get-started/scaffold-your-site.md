---
title: Scaffold Your First Site
nav_title: Scaffold
description: Create a Bengal site from a template in 5 minutes
weight: 5
draft: false
tags:
- tutorial
- getting-started
- scaffolding
- templates
keywords:
- scaffold
- template
- new site
- init
- setup
category: tutorials
---

# Scaffold Your First Site

Bengal provides built-in templates to quickly create sites with common information architectures. This tutorial covers three ways to scaffold a site.

## Quick Start: Template-Based Creation

The fastest way to start is with a template:

```bash
# Create a documentation site
bengal new site my-docs --template docs

# Navigate and preview
cd my-docs
bengal serve
```

Open `http://localhost:5173` to see your scaffolded site.

## Available Templates

| Template | Best For | Command |
|----------|----------|---------|
| `default` | Minimal single-page site | `bengal new site --template default` |
| `docs` | Technical documentation, knowledge bases | `bengal new site --template docs` |
| `blog` | Personal blogs, news sites | `bengal new site --template blog` |
| `portfolio` | Developer portfolios, project showcases | `bengal new site --template portfolio` |
| `product` | Product showcase sites | `bengal new site --template product` |
| `resume` | CV/Resume with structured data | `bengal new site --template resume` |

## What Gets Created

When you run `bengal new site my-docs --template docs`, Bengal creates:

```tree
my-docs/
├── config/
│   ├── _default/
│   │   ├── site.yaml        # Site identity (title, author, baseurl)
│   │   ├── content.yaml     # Content processing settings
│   │   ├── build.yaml       # Build configuration
│   │   ├── features.yaml    # Feature toggles
│   │   ├── theme.yaml       # Theme configuration
│   │   └── params.yaml      # Custom variables
│   └── environments/
│       ├── local.yaml       # Development overrides
│       └── production.yaml  # Production settings
├── content/
│   ├── index.md             # Home page
│   ├── getting-started/     # Onboarding section
│   │   ├── _index.md
│   │   ├── installation.md
│   │   └── quickstart.md
│   ├── guides/              # How-to guides
│   │   └── _index.md
│   └── api/                 # API reference
│       └── _index.md
└── .gitignore
```

## Method 1: Interactive Wizard

For a guided experience, run without arguments:

```bash
bengal new site
```

The wizard prompts for:
1. **Site name** (creates directory)
2. **Base URL** (for production deployment)
3. **Template** (select from list)

## Method 2: Direct Template Selection

Skip prompts with explicit options:

```bash
# Blog with custom name
bengal new site my-blog --template blog

# Portfolio at specific URL
bengal new site portfolio --template portfolio
```

## Method 3: Add Sections to an Existing Site

Bengal has no command for retrofitting sections into an existing site — content lives in
plain files, so you add a section by creating its directory and an `_index.md`:

```bash
# Add a docs section
mkdir -p content/docs
$EDITOR content/docs/_index.md

# Add a tutorials section
mkdir -p content/tutorials
$EDITOR content/tutorials/_index.md
```

Bengal infers a section's content type from its directory name:

| Name Pattern | Inferred Type | Behavior |
|--------------|---------------|----------|
| blog, posts, articles, news | `blog` | Date-sorted, post-style |
| docs, documentation, guides, tutorials | `doc` | Weight-sorted, doc-style |
| projects, portfolio | `section` | Standard section |
| about, contact | `section` | Standard section |

You can override the inferred type by setting `type:` (or a `cascade.type:`) in the
section's `_index.md` frontmatter.

## Customizing After Scaffolding

:::{steps}
:::{step} Update Site Identity
:description: Replace placeholder values with your project's actual metadata.
:duration: 2 min
Edit `config/_default/site.yaml`:

```yaml
site:
  title: "My Documentation"
  description: "Documentation for my project"
  author: "Your Name"
  baseurl: "https://docs.example.com"
```
:::{/step}

:::{step} Configure Features
:description: Enable RSS feeds, search, sitemaps, and other built-in features.
:duration: 1 min
:optional:
Edit `config/_default/features.yaml`:

```yaml
features:
  rss: true       # Generate RSS feed
  sitemap: true   # Generate sitemap.xml
  search: true    # Enable search
  json: true      # Generate JSON API
  llm_txt: true   # Generate llms.txt
```
:::{/step}

:::{step} Add Your Content
Replace placeholder content in `content/`:

```bash
# Edit home page
$EDITOR content/index.md

# Add new page
touch content/getting-started/configuration.md
```
:::{/step}
:::{/steps}

## Preview and Build

```bash
# Live preview with hot reload
bengal serve

# Production build
bengal build

# Build with specific environment
bengal build --environment production
```

## Skeleton Manifests

Bengal's site templates are powered by **skeleton manifests** — `skeleton.yaml` files that
define a complete site structure (frontmatter, cascades, and content stubs). They are not a
separate CLI step: when you drop a `skeleton.yaml` into a template directory, Bengal
materializes it automatically during `bengal new site`.

```bash
# Scaffold a site from a template backed by a skeleton manifest
bengal new site api-docs --template api-docs
```

See [[docs/extending/custom-skeletons|Create Custom Skeletons]] for the full guide on writing skeleton YAML files.

## Next Steps

- [Configuration Reference](/docs/building/configuration/) - Detailed config options
- [Content Organization](/docs/content/organization/) - Structuring your content
- [Theming Guide](/docs/theming/) - Customize appearance

## Troubleshooting

:::{dropdown} "Directory already exists"
:icon: alert

```bash
# Remove existing directory
rm -rf my-docs

# Or use a different name
bengal new site my-docs-v2 --template docs
```
:::

:::{dropdown} "Section already exists"
:icon: alert

Sections are just directories under `content/`. To replace one, delete the existing
directory and recreate it:

```bash
rm -rf content/blog
mkdir -p content/blog
$EDITOR content/blog/_index.md
```
:::

:::{dropdown} Preview Before Publishing
:icon: info

Build the site and inspect the generated output (default `public/`) before deploying:

```bash
bengal build
```
:::
