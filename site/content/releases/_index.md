---
title: Releases
description: Release notes and version history for Bengal SSG
type: changelog
weight: 90
draft: false
lang: en
tags: [releases, changelog, version history]
keywords: [releases, changelog, version, updates]
category: changelog
cascade:
  type: changelog
---

# Release Notes

Welcome to Bengal's release notes! Here you'll find what's new, what's improved, and what's been fixed in each version.

## Installation

To upgrade to the latest version:

```bash
pip install --upgrade bengal
```

## Frontmatter for Release Notes

Release notes use standard Bengal frontmatter. Here's the recommended frontmatter for release pages:

```yaml
---
title: Bengal 0.1.3
description: Performance, stability, theme enhancements, and critical bug fixes
type: changelog
date: 2025-10-20
weight: 10
draft: false
---
```

### Supported Frontmatter Keys

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `title` | `string` | filename-derived | Release title (e.g., `"Bengal 0.1.3"`) |
| `description` | `string` | `""` | Short description for SEO and listings |
| `type` | `string` | `None` | Set to `"changelog"` for release notes |
| `date` | `datetime` | `None` | Release date (used for sorting) |
| `weight` | `integer` | `None` | Sort order (lower = newer releases first) |
| `draft` | `boolean` | `false` | Set to `true` to hide unreleased versions |
| `tags` | `list[string]` | `[]` | Tags for categorization (e.g., `[breaking, performance]`) |
| `category` | `string` | `None` | Single category for taxonomy (e.g., `category: release`) |
| `slug` | `string` | filename-derived | Custom URL override (e.g., `slug: v0.1.3`) |

**Recommended Values:**
- `type: changelog` - Ensures proper template rendering
- `weight: 10` (or lower) - Newer releases appear first
- `draft: false` - Only set to `true` for unreleased versions
- `date` - Use ISO format: `2025-10-20` or `2025-10-20T00:00:00`
