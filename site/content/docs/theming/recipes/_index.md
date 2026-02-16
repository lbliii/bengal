---
title: Template Cookbook
nav_title: Recipes
description: Common templating patterns and Bengal-specific features
draft: false
weight: 50
lang: en
tags:
- cookbook
- templates
- kida
- examples
keywords:
- cookbook
- templates
- kida
- examples
- bengal
category: guide
icon: book-open
card_color: orange
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
| [Archive Page](./archive-page/) | `group_by_year`, `group_by_month` filters |
| [Featured Posts](./featured-posts/) | `section.featured_posts`, highlighting content |
| [Template Views](./template-views/) | `EndpointView`, `SchemaView`, `TagView` normalized objects |

## Page Features

Add features to individual pages.

| Example | What You'll Learn |
|---------|-------------------|
| [Add Table of Contents](./table-of-contents/) | `page.toc`, scroll highlighting |
| [Show Reading Time](./reading-time/) | `page.reading_time` property and filter |
| [Content Freshness](./content-freshness/) | `age_days`, `age_months`, "new" badges |
| [Author Byline](./author-byline/) | `page.author`, avatars, social links |
| [Series Navigation](./series-navigation/) | `prev_in_series`, `next_in_series` |
| [Social Sharing Buttons](./social-sharing-buttons/) | `share_url()`, platform share links |
| [Section Statistics](./section-statistics/) | `post_count`, `word_count`, totals |
| [Blog Comments](./blog-comments/) | `params.comments`, Giscus, Disqus, Utterances |

---

## Quick Reference

### The Essentials

```kida
{# Get pages from a section #}
{% let posts = site.pages |> where('section', 'blog') %}

{# Sort by date, newest first #}
{% let recent = posts |> sort_by('date', reverse=true) %}

{# Limit to 5 #}
{% let latest = recent |> limit(5) %}

{# Or chain it all #}
{% let latest = site.pages
  |> where('section', 'blog')
  |> sort_by('date', reverse=true)
  |> limit(5) %}
```

### Common Filters

| Filter | Purpose | Example |
|--------|---------|---------|
| `where` | Filter by field | `pages \|> where('draft', false)` |
| `sort_by` | Sort results | `pages \|> sort_by('title')` |
| `limit` | Take first N | `pages \|> limit(10)` |
| `group_by` | Group by field | `pages \|> group_by('category')` |
| `first` | Get first item | `pages \|> first` |

Both `\|>` (Kida pipeline) and `\|` (Jinja-style) work. Examples use `\|>` for consistency.

See [Template Functions](/docs/theming/templating/functions/) for the complete reference.
