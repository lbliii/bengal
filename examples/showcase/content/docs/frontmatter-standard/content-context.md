---
title: "Content Context"
description: "Tutorial/guide fields, API/CLI fields, and relationships"
type: doc
weight: 40
toc: true
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
