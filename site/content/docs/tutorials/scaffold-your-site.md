---
title: Scaffold Your First Site
description: Create a Bengal site from a template in 5 minutes
weight: 5
type: doc
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

Open `http://localhost:8000` to see your scaffolded site.

## Available Templates

| Template | Best For | Command |
|----------|----------|---------|
| `docs` | Technical documentation, knowledge bases | `bengal new site --template docs` |
| `blog` | Personal blogs, news sites | `bengal new site --template blog` |
| `portfolio` | Developer portfolios, project showcases | `bengal new site --template portfolio` |
| `resume` | CV/Resume with structured data | `bengal new site --template resume` |
| `landing` | Marketing landing pages | `bengal new site --template landing` |
| `changelog` | Version history, release notes | `bengal new site --template changelog` |

## What Gets Created

When you run `bengal new site my-docs --template docs`, Bengal creates:

```text
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

## Method 3: Add Sections to Existing Site

Already have a site? Add sections without recreating:

```bash
# Add docs and tutorials sections
bengal init --sections docs --sections tutorials

# Add sections with sample content
bengal init --sections blog --with-content --pages-per-section 5
```

### Section Type Inference

Bengal infers section types from names:

| Name Pattern | Inferred Type | Behavior |
|--------------|---------------|----------|
| blog, posts, articles, news | `blog` | Date-sorted, post-style |
| docs, documentation, guides, tutorials | `doc` | Weight-sorted, doc-style |
| projects, portfolio | `section` | Standard section |
| about, contact | `section` | Standard section |

## Customizing After Scaffolding

:::{steps}
:::{step} Update Site Identity
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

## Coming Soon: Skeleton Manifests

Bengal will soon support **skeleton manifests** - shareable YAML files that define complete site structures with frontmatter, cascades, and content stubs.

```bash
# Apply a community skeleton
bengal skeleton apply @bengal/api-docs-starter

# Export your site's structure for others
bengal skeleton export --output my-pattern.yaml

# Browse available skeletons
bengal skeleton list --category documentation
```

Skeletons will enable:
- **Community patterns** - Browse and use proven site structures
- **Org standards** - Enforce consistent IA across projects
- **Theme compatibility** - Find skeletons optimized for your theme

See [RFC: Skeleton Manifests](https://github.com/bengal-ssg/bengal/blob/main/plan/active/rfc-shareable-site-skeletons.md) for the full proposal.

## Next Steps

- [Configuration Reference](/docs/about/concepts/configuration/) - Detailed config options
- [Content Organization](/docs/content/organization/) - Structuring your content
- [Theming Guide](/docs/theming/) - Customize appearance

## Troubleshooting

### "Directory already exists"

```bash
# Remove existing directory
rm -rf my-docs

# Or use a different name
bengal new site my-docs-v2 --template docs
```

### "Section already exists"

Use `--force` to overwrite:

```bash
bengal init --sections blog --force
```

### Preview Without Creating

Use `--dry-run` to see what would be created:

```bash
bengal init --sections api --sections guides --dry-run
```
