---
title: "Layout & Structure"
description: "Control templates, TOC, ordering, and taxonomy"
type: doc
weight: 20
toc: true
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
