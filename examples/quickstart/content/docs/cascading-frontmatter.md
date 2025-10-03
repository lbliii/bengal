---
title: "Cascading Frontmatter"
date: 2025-10-03
tags: ["features", "frontmatter", "organization"]
categories: ["Documentation", "Features"]
type: "documentation"
description: "Learn how to use cascading frontmatter to apply metadata across sections"
author: "Bengal Documentation Team"
---

# Cascading Frontmatter

Cascading frontmatter allows you to define metadata in a section's `_index.md` file that automatically applies to all child pages and subsections. This is a powerful way to maintain consistent metadata across your content.

## How It Works

Define a `cascade` field in your section's `_index.md` frontmatter:

```yaml
---
title: "Products"
cascade:
  type: "product"
  show_price: true
  category: "catalog"
---
```

All pages under this section will automatically inherit these values!

## Basic Usage

### 1. Define Cascade in Section Index

Create a section with cascading metadata:

```markdown
# content/products/_index.md
---
title: "Products"
cascade:
  type: "product"
  product_line: "current"
  show_price: true
---

# Products

All our products.
```

### 2. Child Pages Inherit Automatically

Any page in the `products/` directory automatically gets the cascaded values:

```markdown
# content/products/widget-2000.md
---
title: "Widget 2000"
price: "$299.99"
---

# Widget 2000

Great product!
```

In your template, you can access:
```jinja2
{{ page.metadata.type }}          {# "product" (from cascade) #}
{{ page.metadata.product_line }}   {# "current" (from cascade) #}
{{ page.metadata.show_price }}     {# true (from cascade) #}
{{ page.metadata.price }}          {# "$299.99" (from page) #}
```

## Technical Writer Use Case: Documentation Versioning

**Scenario:** You're documenting software and want every page to display the current version and product name without repeating it in every file.

### Step 1: Set Up Cascade in Section Index

Create a `_index.md` file for your section:

```markdown
# content/docs/v2/_index.md
---
title: "SuperApp v2.0 Documentation"
cascade:
  product_name: "SuperApp"
  product_version: "2.0"
  release_date: "2025-10-01"
  status: "stable"
---

# SuperApp v2.0 Documentation

Welcome to the SuperApp documentation.
```

**Note:** Use `_index.md` for section indexes (recommended for sections with cascade). Bengal also supports `index.md` - both work identically, but `_index.md` is clearer for sections with child pages.

### Step 2: Write Your Documentation

As a technical writer, you can use cascaded values **directly in your markdown**:

```markdown
# content/docs/v2/installation.md
---
title: "Installation Guide"
---

# Installation Guide

This guide covers installing {{ page.metadata.product_name }} version {{ page.metadata.product_version }}.

## System Requirements

{{ page.metadata.product_name }} {{ page.metadata.product_version }} requires:

- Python 3.8+
- 4GB RAM minimum
- Released {{ page.metadata.release_date }}
```

**Result:** The variables are automatically replaced when the page is built!

### Step 3: Access in Templates

In your page template, display cascaded values:

```html
<!-- In your template (e.g., doc.html) -->
<div class="doc-header">
  <span class="product-name">{{ page.metadata.product_name }}</span>
  <span class="version-badge">v{{ page.metadata.product_version }}</span>
  {% if page.metadata.status == 'stable' %}
    <span class="badge-stable">Stable</span>
  {% endif %}
</div>

<article>
  {{ content }}
</article>

<footer class="doc-footer">
  <p>{{ page.metadata.product_name }} {{ page.metadata.product_version }} 
     - Released {{ page.metadata.release_date }}</p>
</footer>
```

### Step 4: Using Variables Inline in Content

**Your exact use case:** Use cascaded values directly in your article body!

```markdown
# content/api/v2/quickstart.md
---
title: "Quick Start Guide"
---

# Quick Start

## Introduction

Today we're going to talk about {{ page.metadata.product_name }} 
version {{ page.metadata.product_version }}.

## Installation

First, install Docker Compose version {{ page.metadata.docker_compose_version }}:

```bash
docker-compose --version
# Should show: {{ page.metadata.docker_compose_version }}
```

## Your First API Call

Connect to {{ page.metadata.api_base_url }}:

```bash
curl {{ page.metadata.api_base_url }}/health
```

Released {{ page.metadata.release_date }}, this is the 
{% if page.metadata.status == 'stable' %}
**stable** production version
{% else %}
beta version
{% endif %}
of {{ page.metadata.product_name }}.
```

**Result:** All variables are replaced during build:
- `{{ page.metadata.product_name }}` → "DataFlow API"
- `{{ page.metadata.product_version }}` → "2.0"
- `{{ page.metadata.api_base_url }}` → "https://api.dataflow.example.com/v2"

**To update v2.0 → v2.1:** Change ONE line in `_index.md` cascade, rebuild, done!

## Nested Sections

Cascades accumulate through section hierarchies:

```markdown
# content/api/_index.md
---
title: "API"
cascade:
  type: "api-doc"
  api_base: "https://api.example.com"
---

# content/api/v2/_index.md
---
title: "API v2"
cascade:
  version: "2.0"
  stable: true
---

# content/api/v2/auth.md
---
title: "Authentication"
---
```

The `auth.md` page will have:
- `type: "api-doc"` (from parent)
- `api_base: "https://api.example.com"` (from parent)
- `version: "2.0"` (from immediate section)
- `stable: true` (from immediate section)

## Override Cascade Values

Pages can override any cascaded value by defining it in their own frontmatter:

```markdown
# content/products/custom-item.md
---
title: "Custom Item"
type: "custom-product"  # Override cascade
price: "$999.99"
---
```

**Priority Order (highest to lowest):**
1. Page's own frontmatter
2. Immediate section's cascade
3. Parent section's cascade
4. Grandparent section's cascade
5. ... and so on

## Real-World Examples

### Example 1: Product Catalog

```yaml
# content/products/_index.md
---
cascade:
  type: "product"
  show_price: true
  warranty: "1-year"
  support: "email"
---
```

All product pages automatically get these fields!

### Example 2: Blog with Authors

```yaml
# content/blog/_index.md
---
cascade:
  type: "post"
  author: "Blog Team"
---

# content/blog/alice/_index.md
---
cascade:
  author: "Alice Smith"
  author_bio: "Senior Engineer"
  author_avatar: "/images/alice.jpg"
---
```

Posts in `blog/alice/` will have Alice's information automatically.

### Example 3: API Documentation Versioning

```yaml
# content/api/v1/_index.md
---
cascade:
  api_version: "1.0"
  deprecated: true
  deprecation_date: "2025-12-31"
---

# content/api/v2/_index.md
---
cascade:
  api_version: "2.0"
  stable: true
  recommended: true
---
```

Perfect for managing different API versions!

## Template Usage

Access cascaded values just like any other metadata:

```jinja2
{# Check if product should show price #}
{% if page.metadata.show_price and page.metadata.price %}
  <div class="price">{{ page.metadata.price }}</div>
{% endif %}

{# Display API version badge #}
{% if page.metadata.api_version %}
  <span class="version-badge">
    v{{ page.metadata.api_version }}
    {% if page.metadata.deprecated %}
      <span class="deprecated">Deprecated</span>
    {% endif %}
  </span>
{% endif %}

{# Author information #}
{% if page.metadata.author %}
  <div class="author">
    {% if page.metadata.author_avatar %}
      <img src="{{ page.metadata.author_avatar }}" alt="{{ page.metadata.author }}">
    {% endif %}
    <span>By {{ page.metadata.author }}</span>
  </div>
{% endif %}
```

## Benefits

1. **DRY Principle** - Define metadata once, apply to many pages
2. **Consistency** - Ensure all pages in a section have required fields
3. **Maintainability** - Update metadata in one place
4. **Flexibility** - Pages can still override when needed
5. **Organization** - Logical grouping of related content

## Tips and Best Practices

### ✅ Do

- Use cascade for metadata common to all pages in a section
- Define sensible defaults that pages can override
- Use nested cascades to build up metadata hierarchically
- Document your cascade structure in comments

### ❌ Don't

- Don't put page-specific data in cascade
- Don't create overly deep cascades (3-4 levels max recommended)
- Don't forget that pages can override cascade values

## Comparison with Hugo

Bengal's cascade implementation is inspired by Hugo and works very similarly:

**Hugo:**
```yaml
cascade:
  type: "docs"
  featured: true
```

**Bengal:**
```yaml
cascade:
  type: "docs"
  featured: true
```

The syntax and behavior are nearly identical, making migration from Hugo straightforward!

## See Also

- [Frontmatter Reference](/docs/configuration-reference/)
- [Template System](/docs/template-system/)
- [Section Organization](/posts/working-with-sections/)

