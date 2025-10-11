---
title: Taxonomies - Tags and Categories
description: Organize content with tags, categories, and taxonomies
type: doc
weight: 2
tags: ["advanced", "taxonomies", "organization"]
toc: true
---

# Taxonomies: Tags and Categories

**Purpose**: Organize and categorize content with tags and categories.

## What You'll Learn

- Use tags to categorize content
- Understand tags vs categories
- Create taxonomy pages
- Best practices for organization

## What Are Taxonomies?

Taxonomies organize content into groups:

- **Tags** - Specific topics (many per page)
- **Categories** - Broad groups (few per page)

Both auto-generate archive pages listing related content.

## Adding Tags

Add tags in frontmatter:

```yaml
---
title: Python Tutorial
tags: ["python", "tutorial", "beginner"]
---
```

**Result:**
- Tag pages created at `/tags/python/`, `/tags/tutorial/`, `/tags/beginner/`
- Each lists all pages with that tag
- Tag index at `/tags/` lists all tags

## Adding Categories

```yaml
---
title: Web Development Guide
categories: ["Programming", "Web Development"]
---
```

**Result:**
- Category pages at `/categories/programming/`, `/categories/web-development/`
- Category index at `/categories/`

## Tags vs Categories

### Tags

**Purpose:** Specific topics

**Characteristics:**
- Many tags per page (3-7)
- Specific and focused
- Flat structure (no hierarchy)

**Example:**
```yaml
tags: ["python", "flask", "web-api", "tutorial", "beginner"]
```

### Categories

**Purpose:** Broad groupings

**Characteristics:**
- Few categories per page (1-3)
- General and broad
- Can be hierarchical

**Example:**
```yaml
categories: ["Programming", "Web Development"]
```

## How Taxonomies Work

### Automatic Generation

Bengal automatically:

1. **Collects** tags/categories from all pages
2. **Creates** archive pages for each
3. **Generates** index pages listing all
4. **Links** related content together

### URL Structure

```
/tags/                    # All tags index
/tags/python/             # Pages tagged "python"
/tags/tutorial/           # Pages tagged "tutorial"

/categories/              # All categories index
/categories/programming/  # Pages in "Programming"
```

## Tag Best Practices

### Be Specific

```yaml
✅ Good (specific):
tags: ["python-basics", "flask-tutorial", "rest-api"]

❌ Vague:
tags: ["programming", "tutorial", "web"]
```

### Use Consistent Format

```yaml
✅ Consistent:
tags: ["python", "javascript", "ruby"]
tags: ["web-development", "mobile-development"]

❌ Inconsistent:
tags: ["Python", "JavaScript", "ruby"]
tags: ["web development", "mobile-dev", "MobileDevelopment"]
```

### Right Number

```yaml
✅ Good (3-7 tags):
tags: ["python", "flask", "api", "tutorial", "beginner"]

❌ Too few:
tags: ["python"]

❌ Too many:
tags: ["python", "flask", "api", "rest", "json", "http", "web", "backend", "tutorial", "guide"]
```

### Create Tag Strategy

Before tagging, decide:

**Tech tags:** `python`, `javascript`, `go`  
**Type tags:** `tutorial`, `reference`, `guide`  
**Level tags:** `beginner`, `intermediate`, `advanced`  
**Topic tags:** `web-api`, `database`, `security`

## Category Best Practices

### Keep Broad

```yaml
✅ Good (broad categories):
categories: ["Programming", "Design"]

❌ Too specific:
categories: ["Python Flask Web API Development"]
```

### Limit Number

```yaml
✅ Good (1-2 categories):
categories: ["Programming"]

❌ Too many:
categories: ["Programming", "Web Development", "Backend", "API Design"]
```

### Use Hierarchy

```yaml
# Option 1: Flat
categories: ["Web Development"]

# Option 2: Hierarchical
categories: ["Programming", "Web Development"]
```

## Tag Pages

### What's Generated

For each tag, Bengal creates:

**Archive page** (`/tags/python/`):
- Lists all pages with tag
- Usually paginated
- Sorted by date (newest first)

**Tag index** (`/tags/`):
- Lists all tags
- Often shows post counts
- Alphabetically sorted

### Customizing Tag Pages

Configure in `bengal.toml`:

```toml
[taxonomies]
tags = "tags"           # URL path
tags_per_page = 10      # Pagination
```

## Real-World Examples

### Blog Post

```yaml
---
title: Building REST APIs with Flask
type: post
date: 2025-10-11
tags: ["python", "flask", "rest-api", "tutorial"]
categories: ["Programming", "Web Development"]
---
```

**Generated pages:**
- `/tags/python/`
- `/tags/flask/`
- `/tags/rest-api/`
- `/tags/tutorial/`
- `/categories/programming/`
- `/categories/web-development/`

### Documentation Page

```yaml
---
title: Configuration Guide
type: doc
tags: ["configuration", "setup", "admin"]
---
```

### Tutorial

```yaml
---
title: Python for Beginners
type: tutorial
tags: ["python", "beginner", "tutorial"]
categories: ["Programming", "Tutorials"]
---
```

## Related Content

Taxonomies enable "related posts" features:

**Pages with shared tags appear as related:**
- Page A: `tags: ["python", "flask"]`
- Page B: `tags: ["python", "django"]`
- Result: Related via "python" tag

## Template Access

In templates, access taxonomies:

```jinja
{# Show page tags #}
{% for tag in page.tags %}
  <a href="/tags/{{ tag|slugify }}/">{{ tag }}</a>
{% endfor %}

{# Show all site tags #}
{% for tag in site.taxonomies.tags %}
  <a href="{{ tag.url }}">{{ tag.name }} ({{ tag.count }})</a>
{% endfor %}
```

## Migration Strategy

### Starting Fresh

1. Define tag categories upfront
2. Tag consistently from the start
3. Review tags quarterly

### Existing Content

1. Audit current tags
2. Standardize naming
3. Consolidate similar tags
4. Update content gradually

## Quick Reference

**Add tags:**
```yaml
---
tags: ["tag1", "tag2", "tag3"]
---
```

**Add categories:**
```yaml
---
categories: ["Category1", "Category2"]
---
```

**Both:**
```yaml
---
tags: ["python", "tutorial"]
categories: ["Programming"]
---
```

## Next Steps

- **[Navigation](navigation.md)** - Site menus
- **[SEO](seo.md)** - Search optimization
- **[Blog Posts](../content-types/blog-posts.md)** - Using taxonomies in blogs
- **[Frontmatter Guide](../writing/frontmatter-guide.md)** - Metadata

## Related

- [Content Organization](../writing/content-organization.md) - Structure
- [Internal Links](../writing/internal-links.md) - Cross-references
- [Blog Posts](../content-types/blog-posts.md) - Post metadata

