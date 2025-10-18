---
title: "Examples & Reference"
description: "Complete examples, optional fields, quick reference, validation, and resources"
type: doc
weight: 50
toc: true
---

## 📊 Complete Example

### Blog Post

```yaml
---
title: "Building Static Sites with Bengal"
description: "Learn how to create static websites using Bengal SSG"
date: 2025-10-08
lastmod: 2025-10-08
author: "Jane Developer"
type: post
tags: ["bengal", "ssg", "tutorial"]
category: "Tutorials"
featured: true
search_keywords: ["static site generator", "jamstack", "websites"]
related:
  - "/docs/getting-started/"
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
title: "bengal site build"
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
