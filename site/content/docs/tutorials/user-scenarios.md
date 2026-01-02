---
title: "User Scenarios"
description: "Common use cases and patterns for different types of Bengal sites"
weight: 100
---

# User Scenarios

This guide covers common use cases for Bengal, with patterns and examples for each scenario.

**When to use this guide**: Choose a scenario that matches your site type, then follow the step-by-step instructions to scaffold and configure your site. Each scenario includes complete examples you can copy and adapt.

**Prerequisites**: Bengal installed (`pip install bengal-ssg`). See [[docs/get-started/installation|Installation]] if needed.

## Blog Author Workflow

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

```bash
bengal serve
```

---

## Documentation Site

Build technical documentation with search, versioning, and navigation.

**What you'll get**: A documentation site with search functionality, hierarchical navigation, and organized content structure.

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

Search is enabled by default for docs template. Output includes `index.json` for search.

To customize search settings, edit `config/_default/features.yaml`:

```yaml
features:
  search: true  # Generates search index (index.json)

# Optional: customize search behavior in config/_default/site.yaml
search:
  enabled: true
  lunr:
    max_results: 50
    min_query_length: 2
```

See [Search Documentation](/docs/reference/search/) for full configuration options.

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

**Note**: Menu items can also reference pages by path. If a page exists at `content/getting-started/_index.md`, you can use `url: "/getting-started/"` or reference it directly.

---

## Portfolio Site

Showcase projects with a portfolio layout.

**What you'll get**: A portfolio site with project showcases, featured project highlighting, and organized project pages.

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

## Mixed Content Site

Combine documentation, blog, and portfolio on a single site.

**What you'll get**: A single site with multiple content types, each with appropriate sorting and display logic using cascade configuration.

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

## Multi-Language Site

Create content in multiple languages using directory-based structure.

**What you'll get**: A multilingual site with language-specific content directories, SEO-friendly hreflang tags, and language switcher support.

### Content Organization

Bengal supports directory-based i18n for content organization:

```tree
content/
├── en/
│   ├── _index.md       # lang: en
│   ├── about.md
│   └── docs/
│       └── guide.md
└── fr/
    ├── _index.md       # lang: fr
    ├── about.md
    └── docs/
        └── guide.md
```

### Configuration

In `bengal.toml` or `config/_default/i18n.yaml`:

```yaml
i18n:
  default_language: en
  content_structure: dir
  languages:
    - code: en
      name: English
      weight: 1
    - code: fr
      name: Français
      weight: 2
```

### Template Functions

Use these in templates for language switching:

- `languages()` - Get list of configured languages
- `alternate_links(page)` - Generate hreflang tags for SEO (takes optional page parameter)

### Limitations

- UI translation (strings) requires separate i18n YAML files
- See [[docs/content/i18n|i18n documentation]] for full details

---

## Landing Page

Build a marketing or product landing page.

**What you'll get**: A single-page marketing site with hero section, feature highlights, and call-to-action elements.

### 1. Scaffold Landing

```bash
bengal new site mylanding --template landing
cd mylanding
```

### 2. Customize Hero Section

Edit `content/index.md`:

```markdown
---
title: "Welcome to MyProduct"
type: landing
layout: landing
hero:
  title: "Build Faster"
  subtitle: "The modern way to create static sites"
  cta:
    text: "Get Started"
    url: "/docs/getting-started/"
---
```

### 3. Add Sections

Use shortcodes and directives for landing page sections:

```markdown
:::{features}
- title: Fast
  icon: rocket
  description: Builds in seconds

- title: Flexible
  icon: puzzle
  description: Customize everything
:::
```

---

## Resume/CV Site

Build a professional resume or CV site.

**What you'll get**: A professional resume site with structured data for experience, education, and contact information.

### 1. Scaffold Resume

```bash
bengal new site myresume --template resume
cd myresume
```

### 2. Edit Resume Data

Update `data/resume.yaml` with your information:

```yaml
name: "Jane Developer"
title: "Senior Software Engineer"
contact:
  email: "jane@example.com"
  github: "janedeveloper"
  linkedin: "in/janedeveloper"

experience:
  - title: "Senior Engineer"
    company: "Tech Corp"
    dates: "2022 - Present"
    description: "Led development of..."

education:
  - degree: "B.S. Computer Science"
    school: "University"
    year: 2018
```

---

## Changelog Site

Maintain a project changelog with releases.

**What you'll get**: A changelog site with versioned releases, categorized changes (added, fixed, changed), and chronological organization.

### 1. Scaffold Changelog

```bash
bengal new site mychangelog --template changelog
cd mychangelog
```

### 2. Add Releases

Update `data/changelog.yaml`:

```yaml
releases:
  - version: "1.2.0"
    date: 2025-06-15
    changes:
      - type: added
        description: "New feature X"
      - type: fixed
        description: "Bug in Y"
      - type: changed
        description: "Updated Z"

  - version: "1.1.0"
    date: 2025-05-01
    changes:
      - type: added
        description: "Initial feature set"
```

---

## Next Steps

- See [[docs/reference/site-templates|Templates Reference]] for template details
- Read [[docs/building/configuration|Configuration Guide]] for advanced settings
- Explore [[docs/theming|Theming]] for customization
- Check out [[docs/tutorials|Tutorials]] for step-by-step guides
