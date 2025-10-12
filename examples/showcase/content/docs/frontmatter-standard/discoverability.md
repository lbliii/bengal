---
title: "Discoverability"
description: "Search enhancements and visibility controls"
type: doc
weight: 30
toc: true
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
