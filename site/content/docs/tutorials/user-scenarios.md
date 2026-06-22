---
title: "User Scenarios"
description: "Common use cases and patterns for different types of Bengal sites"
weight: 100
tags:
- persona-writer
- persona-operator
---

# User Scenarios

Pick the scenario that matches your site type, then follow the steps below.

:::{note}
**Do I need this?** Use this guide when you know *what* you are building (blog,
docs site, portfolio, etc.) and want scaffold + config patterns. For a faster
first run, start with [[docs/get-started/quickstart-writer|Writer Quickstart]]
or a focused [[docs/tutorials|Tutorial]] instead.
:::

**Prerequisites**: Bengal installed (`pip install bengal`). See [[docs/get-started/installation|Installation]] if needed.

:::{cards}
:columns: 2
:gap: small

:::{card} Blog
:link: "#blog-author-workflow"
:icon: edit
Date-sorted posts, categories, RSS, pagination.
:::

:::{card} Documentation
:link: "#documentation-site"
:icon: book-open
Search, versioning, hierarchical nav.
:::

:::{card} Portfolio
:link: "#portfolio-site"
:icon: image
Project showcases and featured work.
:::

:::{card} Mixed Content
:link: "#mixed-content-site"
:icon: layers
Blog, docs, and portfolio on one site.
:::

:::{card} Multi-Variant
:link: "#multi-variant-site"
:icon: git-branch
One repo, multiple deployed editions.
:::

:::{card} More Scenarios
:link: [[docs/tutorials/user-scenarios-specialized|Specialized Scenarios]]
:icon: ellipsis
i18n, landing pages, resume, changelog.
:::

:::{/cards}

## Blog Author Workflow {#blog-author-workflow}

Build a personal or team blog with posts, categories, and RSS feeds.

**What you'll get**: A blog site with date-sorted posts, category organization, RSS feed, and pagination.

### 1. Scaffold a Blog

```bash
bengal new site myblog --template blog
cd myblog
```

### 2. Configure Pagination

Edit `config/_default/content.yaml`:

```yaml
content:
  default_type: blog
  sort_pages_by: date
  sort_order: desc

pagination:
  per_page: 10
```

### 3. Add Posts

Create posts in `content/posts/` directory. Each post should include a `date` field for sorting and RSS feed inclusion:

```markdown
---
title: "My First Post"
date: 2025-01-15
tags:
  - announcement
  - news
categories:
  - Updates
---

# My First Post

Welcome to my blog!
```

### 4. Enable RSS

In `config/_default/features.yaml`:

```yaml
features:
  rss: true  # Generates rss.xml (limited to 20 most recent posts)
```

### 5. Build and Preview

:::{include} _snippets/scaffold/serve.md
:::

---

## Documentation Site {#documentation-site}

Build technical documentation with search, versioning, and navigation.

**What you'll get**: A documentation site with hierarchical navigation, search functionality, and structured content organization.

### 1. Scaffold Documentation

```bash
bengal new site mydocs --template docs
cd mydocs
```

### 2. Organize Content

Structure your docs in `content/`:

```tree
content/
├── _index.md           # Docs landing page
├── getting-started/
│   ├── _index.md
│   ├── installation.md
│   └── quickstart.md
├── guides/
│   ├── _index.md
│   └── advanced.md
└── reference/
    ├── _index.md
    └── api.md
```

### 3. Configure Search

Search is enabled by default for the docs template (`index.json` output). See
[[docs/building/configuration|Configuration]] to customize search behavior.

### 4. Add Navigation

Configure menu in `config/_default/site.yaml`:

```yaml
menu:
  main:
    items:
      - name: "Getting Started"
        url: "/getting-started/"
        weight: 10
      - name: "Guides"
        url: "/guides/"
        weight: 20
      - name: "Reference"
        url: "/reference/"
        weight: 30
```

---

## Portfolio Site {#portfolio-site}

Showcase projects with a portfolio layout.

**What you'll get**: A portfolio site with project pages, featured project highlighting, and tag-based organization.

### 1. Scaffold Portfolio

```bash
bengal new site myportfolio --template portfolio
cd myportfolio
```

### 2. Add Projects

Create project pages in `content/projects/`:

```markdown
---
title: "Project Alpha"
date: 2025-03-15
tags:
  - python
  - api
featured: true
image: "/images/project-alpha.png"
---

# Project Alpha

Description of your project.

## Technologies

- Python
- FastAPI
- PostgreSQL

## Links

- [GitHub](https://github.com/example/project-alpha)
- [Demo](https://demo.example.com)
```

### 3. Configure Featured Projects

Use the `featured: true` frontmatter field to highlight projects on the homepage. Templates can filter projects by this field to show featured items prominently.

---

## Mixed Content Site {#mixed-content-site}

Combine documentation, blog, and portfolio on a single site.

**What you'll get**: A multi-purpose site with separate sections for different content types, each with appropriate templates and navigation.

### 1. Create Site Structure

```bash
bengal new site mysite --template default
cd mysite
```

### 2. Organize by Section

Create sections with cascade for content types:

```tree
content/
├── _index.md           # Landing page
├── docs/
│   ├── _index.md       # cascade: type: doc
│   └── guide.md
├── blog/
│   ├── _index.md       # cascade: type: blog
│   └── post-1.md
└── projects/
    ├── _index.md       # cascade: type: portfolio
    └── project-a.md
```

### 3. Use Cascade for Content Types

In `content/docs/_index.md`:

```markdown
---
title: "Documentation"
cascade:
  type: doc
---
```

In `content/blog/_index.md`:

```markdown
---
title: "Blog"
cascade:
  type: blog
---
```

### 4. Configure Menu

```yaml
menu:
  main:
    items:
      - name: "Docs"
        url: "/docs/"
        weight: 10
      - name: "Blog"
        url: "/blog/"
        weight: 20
      - name: "Projects"
        url: "/projects/"
        weight: 30
```

---

## Multi-Variant Documentation {#multi-variant-site}

Build separate doc sites (OSS vs Enterprise, brand1 vs brand2) from one content tree. Common when you acquire a product or maintain paid vs free tiers.

**What you'll get**: One content repo, multiple deployed sites with edition-specific pages filtered per build.

### 1. Add Edition to Pages

Mark edition-specific pages in frontmatter:

```markdown
---
# content/enterprise/sso.md
title: "SSO Configuration"
edition: [enterprise]
---

# SSO Configuration

Configure single sign-on for your organization.
```

```markdown
---
# content/oss/contributing.md
title: "Contributing"
edition: [oss]
---

# Contributing

How to contribute to the open-source project.
```

Pages without `edition` are included in all builds.

### 2. Create Environment Configs

`config/environments/oss.yaml`:

```yaml
params:
  edition: oss

site:
  baseurl: "https://docs.example.com"
```

`config/environments/enterprise.yaml`:

```yaml
params:
  edition: enterprise

site:
  baseurl: "https://enterprise.example.com"
```

### 3. Build Each Variant

```bash
bengal build --environment oss
bengal build --environment enterprise
```

### 4. Deploy

Deploy each build to its own URL (e.g., `docs.example.com` and `enterprise.example.com`). Use CI matrix jobs or separate workflows per variant.

:::{seealso}
[[docs/building/configuration/variants|Multi-Variant Builds]] — cascade, CI/CD, and env overrides
:::

## Next Steps

- See [[docs/reference/site-templates|Templates Reference]] for template details
- Read [[docs/building/configuration|Configuration Guide]] for advanced settings
- Explore [[docs/theming|Theming]] for customization
