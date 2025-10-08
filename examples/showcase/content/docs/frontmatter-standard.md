---
title: "Frontmatter Standard"
description: "Standardized frontmatter fields for optimal search, navigation, and content organization"
date: 2025-10-08
weight: 5
tags: ["frontmatter", "metadata", "documentation", "search"]
toc: true
---

# Frontmatter Standard

This document defines the **standardized frontmatter fields** used throughout the Bengal Showcase documentation. Following this standard ensures optimal search functionality, proper navigation, and consistent content organization.

```{success} Search-Optimized
All fields in this standard are indexed in `index.json` for client-side search with Lunr.js!
```

---

## 🎯 Core Fields (Required/Recommended)

### `title` (Required)
**Type:** String  
**Purpose:** Page title displayed in navigation, search results, and HTML `<title>` tag

```yaml
title: "Getting Started with Bengal"
```

### `description` (Recommended)
**Type:** String  
**Purpose:** Short description for meta tags, search results, and page summaries

```yaml
description: "Quick start guide to installing and using Bengal SSG"
```

**Best practices:**
- Keep under 160 characters for SEO
- Make it descriptive and action-oriented
- Include relevant keywords naturally

### `date` (Recommended for content)
**Type:** Date (YYYY-MM-DD)  
**Purpose:** Publication date for sorting and display

```yaml
date: 2025-10-08
```

### `tags` (Recommended)
**Type:** List of strings  
**Purpose:** Taxonomy, filtering, and search keywords

```yaml
tags: ["tutorial", "beginner", "installation"]
```

**Best practices:**
- Use 3-7 tags per page
- Use lowercase, hyphenated slugs
- Be specific and consistent

---

## 📐 Layout & Structure

### `type`
**Type:** String  
**Purpose:** Content type for template selection and filtering

**Common values:**
- `page` - Standard page
- `post` - Blog post
- `doc` - Documentation page
- `tutorial` - Tutorial content
- `api-reference` - API documentation
- `cli-reference` - CLI documentation
- `guide` - How-to guide

```yaml
type: tutorial
```

### `layout`
**Type:** String  
**Purpose:** Alternative layout/template override

```yaml
layout: api-reference
```

### `template`
**Type:** String  
**Purpose:** Explicit template file override

```yaml
template: custom-layout.html
```

### `weight`
**Type:** Integer  
**Purpose:** Sort order within a section (lower = higher priority)

```yaml
weight: 10
```

### `toc`
**Type:** Boolean  
**Purpose:** Enable/disable table of contents sidebar

```yaml
toc: true
```

---

## 👤 Authorship

### `author`
**Type:** String  
**Purpose:** Primary author name

```yaml
author: "Jane Developer"
```

### `authors`
**Type:** List of strings  
**Purpose:** Multiple authors for collaborative content

```yaml
authors: ["Jane Developer", "John Contributor"]
```

---

## 📂 Categories & Taxonomy

### `category`
**Type:** String  
**Purpose:** Primary category (alternative to sections)

```yaml
category: "Tutorials"
```

### `categories`
**Type:** List of strings  
**Purpose:** Multiple categories

```yaml
categories: ["Tutorials", "Python", "Web Development"]
```

---

## 🔍 Search Enhancement

### `search_keywords`
**Type:** List of strings  
**Purpose:** Additional keywords for search (not displayed)

```yaml
search_keywords: ["ssg", "static site generator", "jamstack"]
```

**Use cases:**
- Acronyms and abbreviations
- Alternative terminology
- Common misspellings

### `search_exclude`
**Type:** Boolean  
**Purpose:** Exclude page from search index

```yaml
search_exclude: true
```

**Use for:**
- Generated pages (404, etc.)
- Index/listing pages
- Private/draft content

---

## 🚩 Status & Visibility

### `draft`
**Type:** Boolean  
**Purpose:** Mark content as draft (excluded from production builds)

```yaml
draft: true
```

### `featured`
**Type:** Boolean  
**Purpose:** Mark content as featured (highlighted in listings)

```yaml
featured: true
```

### `lastmod`
**Type:** Date (YYYY-MM-DD)  
**Purpose:** Last modification date (for changelogs, freshness)

```yaml
lastmod: 2025-10-08
```

---

## 🎓 Tutorial/Guide Fields

### `difficulty`
**Type:** String  
**Purpose:** Content difficulty level

**Common values:** `beginner`, `intermediate`, `advanced`, `expert`

```yaml
difficulty: beginner
```

### `level`
**Type:** String (alternative to difficulty)  
**Purpose:** Skill level required

```yaml
level: intermediate
```

### `estimated_time`
**Type:** String  
**Purpose:** Estimated completion time

```yaml
estimated_time: "15 minutes"
```

### `prerequisites`
**Type:** List of strings  
**Purpose:** Required knowledge or setup

```yaml
prerequisites:
  - "Basic Python knowledge"
  - "Bengal SSG installed"
```

---

## 🔗 API/CLI Documentation

### `cli_name`
**Type:** String  
**Purpose:** CLI command or tool name

```yaml
cli_name: bengal
```

### `api_module`
**Type:** String  
**Purpose:** Python module or API endpoint name

```yaml
api_module: bengal.core.site
```

### `source_file`
**Type:** String  
**Purpose:** Source code file path

```yaml
source_file: "../../bengal/core/site.py"
```

---

## 🔗 Relationships

### `related`
**Type:** List of strings (URLs or slugs)  
**Purpose:** Related content links

```yaml
related:
  - "/docs/configuration/"
  - "/tutorials/advanced-features/"
```

### `series`
**Type:** String  
**Purpose:** Content series name

```yaml
series: "Getting Started"
```

### `series_order`
**Type:** Integer  
**Purpose:** Order within a series

```yaml
series_order: 3
```

---

## 📊 Complete Example

### Blog Post

```yaml
---
title: "Building Fast Static Sites with Bengal"
description: "Learn how to create lightning-fast static websites using Bengal SSG and modern best practices"
date: 2025-10-08
lastmod: 2025-10-08
author: "Jane Developer"
type: post
tags: ["bengal", "ssg", "performance", "tutorial"]
category: "Tutorials"
featured: true
search_keywords: ["static site generator", "jamstack", "fast websites"]
related:
  - "/docs/getting-started/"
  - "/tutorials/optimization/"
---
```

### Documentation Page

```yaml
---
title: "Configuration Reference"
description: "Complete reference for Bengal SSG configuration options"
date: 2025-10-08
type: doc
weight: 20
toc: true
tags: ["configuration", "reference", "docs"]
search_keywords: ["config", "settings", "bengal.toml"]
---
```

### Tutorial

```yaml
---
title: "Building Your First Bengal Site"
description: "Step-by-step tutorial for creating your first static site with Bengal"
date: 2025-10-08
type: tutorial
difficulty: beginner
estimated_time: "30 minutes"
tags: ["tutorial", "beginner", "quickstart"]
series: "Getting Started"
series_order: 1
prerequisites:
  - "Python 3.8 or higher"
  - "Basic command line knowledge"
toc: true
---
```

### API Documentation

```yaml
---
title: "Site Class"
description: "Core Site class for managing the static site build process"
type: api-reference
layout: api-reference
api_module: bengal.core.site
source_file: "../../bengal/core/site.py"
tags: ["api", "core", "site"]
weight: 10
---
```

### CLI Reference

```yaml
---
title: "bengal build"
description: "Build command reference and options"
type: cli-reference
template: cli-reference/list.html
cli_name: build
tags: ["cli", "command", "build"]
weight: 10
---
```

---

## 🎨 Optional/Custom Fields

You can add custom fields for your specific needs:

```yaml
---
# ... standard fields ...

# Custom fields
version: "2.0"
platforms: ["linux", "macos", "windows"]
license: "MIT"
contributors: ["Alice", "Bob", "Charlie"]
---
```

**Notes:**
- Custom fields won't be indexed for search by default
- They're available in templates via `page.metadata.field_name`
- Keep field names lowercase with underscores

---

## 📋 Quick Reference Table

| Field | Type | Required | Searchable | Purpose |
|-------|------|----------|------------|---------|
| `title` | string | ✅ Yes | ✅ Yes | Page title |
| `description` | string | 🟡 Recommended | ✅ Yes | Short description |
| `date` | date | 🟡 Recommended | ⚪ No | Publication date |
| `tags` | list | 🟡 Recommended | ✅ Yes | Taxonomy tags |
| `type` | string | ⚪ Optional | ✅ Yes | Content type |
| `author` | string | ⚪ Optional | ✅ Yes | Author name |
| `category` | string | ⚪ Optional | ✅ Yes | Primary category |
| `weight` | integer | ⚪ Optional | ⚪ No | Sort order |
| `toc` | boolean | ⚪ Optional | ⚪ No | TOC display |
| `draft` | boolean | ⚪ Optional | ⚪ No | Draft status |
| `featured` | boolean | ⚪ Optional | ⚪ No | Featured flag |
| `difficulty` | string | ⚪ Optional | ✅ Yes | Tutorial level |
| `search_keywords` | list | ⚪ Optional | ✅ Yes | Extra keywords |
| `search_exclude` | boolean | ⚪ Optional | ⚪ No | Exclude from search |

---

## 🔧 Validation

Bengal validates frontmatter during build. Common errors:

- **Missing title:** Every page must have a title
- **Invalid date format:** Use `YYYY-MM-DD`
- **Invalid type:** Check your type against available templates
- **Duplicate tags:** Tags should be unique

---

## 📚 Resources

- [Output Formats Documentation](/docs/output/output-formats/) - How index.json is generated
- [Search Implementation](/docs/search/) - Client-side search with Lunr.js
- [Template Functions](/docs/templates/function-reference/) - Using metadata in templates

---

**Last Updated:** October 8, 2025  
**Status:** Standard for Bengal Showcase documentation

