---
title: "Core Fields"
description: "Required and recommended frontmatter fields, plus authorship"
type: doc
weight: 10
toc: true
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
