---
title: Template Cookbook
description: Common templating patterns and Bengal-specific features
weight: 50
draft: false
lang: en
tags: [cookbook, templates, jinja, examples]
keywords: [cookbook, templates, jinja, examples, bengal]
category: guide
icon: book-open
card_color: orange
aliases:
  - /docs/recipes/
cascade:
  type: doc
---

# Template Cookbook

Practical examples showing how to accomplish common tasks with Bengal's templating system.

## Content Queries

Work with pages, sections, and taxonomies.

| Example | What You'll Learn |
|---------|-------------------|
| [List Recent Posts](./list-recent-posts/) | `where`, `sort_by`, `limit` filters |
| [Group by Category](./group-by-category/) | `group_by` filter, nested loops |
| [Filter by Multiple Tags](./filter-by-tags/) | Chaining filters, `in` operator |

## Page Features

Add features to individual pages.

| Example | What You'll Learn |
|---------|-------------------|
| [Add Table of Contents](./table-of-contents/) | `page.toc`, scroll highlighting |
| [Show Reading Time](./reading-time/) | `reading_time` filter |

---

## Quick Reference

### The Essentials

```jinja2
{# Get pages from a section #}
{% set posts = site.pages | where('section', 'blog') %}

{# Sort by date, newest first #}
{% set recent = posts | sort_by('date', reverse=true) %}

{# Limit to 5 #}
{% set latest = recent | limit(5) %}

{# Or chain it all #}
{% set latest = site.pages
  | where('section', 'blog')
  | sort_by('date', reverse=true)
  | limit(5) %}
```

### Common Filters

| Filter | Purpose | Example |
|--------|---------|---------|
| `where` | Filter by field | `pages \| where('draft', false)` |
| `sort_by` | Sort results | `pages \| sort_by('title')` |
| `limit` | Take first N | `pages \| limit(10)` |
| `group_by` | Group by field | `pages \| group_by('category')` |
| `first` | Get first item | `pages \| first` |

See [Template Functions](/docs/theming/templating/functions/) for the complete reference.
