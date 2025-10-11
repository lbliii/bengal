---
title: Variable Substitution
description: Use dynamic variables in markdown content
type: doc
weight: 1
tags: ["advanced", "variables", "dynamic-content"]
toc: true
---

# Variable Substitution

**Purpose**: Insert dynamic values from frontmatter and site config into your markdown content.

## What You'll Learn

- Use variables in markdown
- Access page metadata
- Reference site configuration
- When to use variables vs templates

## Basic Syntax

Use `{{ variable }}` in your markdown:

```markdown
---
title: Product Guide
version: "2.0"
api_url: "https://api.example.com"
---

# {{ page.metadata.title }}

Welcome to version {{ page.metadata.version }}.

Connect to {{ page.metadata.api_url }} for API access.
```

**Result:**
```
# Product Guide

Welcome to version 2.0.

Connect to https://api.example.com for API access.
```

## Available Variables

### Page Metadata

Access frontmatter fields:

```markdown
---
product_name: "Bengal SSG"
version: "0.2.0"
author: "Jane Developer"
---

## {{ page.metadata.product_name }}

Version: {{ page.metadata.version }}  
Author: {{ page.metadata.author }}
```

### Page Properties

Built-in page properties:

```markdown
This page: {{ page.title }}  
URL: {{ page.url }}  
Date: {{ page.date }}
```

### Site Configuration

Access `bengal.toml` values:

```markdown
Site: {{ site.config.site.title }}  
URL: {{ site.config.site.baseurl }}
```

## Use Cases

### Product Documentation

```markdown
---
product: "Bengal"
version: "0.2.0"
min_python: "3.8"
---

# {{ page.metadata.product }} Documentation

**Version:** {{ page.metadata.version }}  
**Requires:** Python {{ page.metadata.min_python }}+
```

### API References

```markdown
---
api_version: "v2"
base_url: "https://api.example.com"
---

## API Endpoint

Connect to {{ page.metadata.base_url }}/{{ page.metadata.api_version }}/users
```

### Reusable Content

```markdown
---
company: "Acme Corp"
email: "support@acme.com"
phone: "+1-555-0100"
---

Contact {{ page.metadata.company }}:

- Email: {{ page.metadata.email }}
- Phone: {{ page.metadata.phone }}
```

## What's Supported

### ✅ Supported

- `{{ page.metadata.xxx }}` - Frontmatter values
- `{{ page.title }}` - Page title
- `{{ page.date }}` - Page date
- `{{ site.config.xxx }}` - Site configuration

### ❌ Not Supported

- `{% if condition %}` - Conditionals (use templates)
- `{% for item %}` - Loops (use templates)
- Complex Jinja2 logic (use templates)

**Why:** Separation of concerns - content (markdown) vs logic (templates)

## Code Blocks Stay Literal

Variables in code blocks remain literal:

````markdown
Use `{{ page.title }}` to display the page title.

\`\`\`python
# This {{ var }} stays literal in code
print("{{ page.title }}")
\`\`\`
````

**Result:**
```
Use `{{ page.title }}` to display the page title.

```python
# This {{ var }} stays literal in code
print("{{ page.title }}")
```
```

No escaping needed!

## Best Practices

### Use for DRY Content

**Good:** Repeated values

```markdown
---
product: "Bengal"
---

{{ page.metadata.product }} is fast.
{{ page.metadata.product }} is easy.
Learn {{ page.metadata.product }} today!
```

**Avoid:** One-off values
```markdown
---
single_use: "value"
---

This value appears once: {{ page.metadata.single_use }}
(Just write "value" directly)
```

### Keep Simple

```markdown
✅ Good (simple):
Version: {{ page.metadata.version }}
Author: {{ page.metadata.author }}

❌ Complex (use templates instead):
{% if page.metadata.beta %}
  Beta version
{% endif %}
```

### Use Descriptive Names

```markdown
✅ Good:
product_name: "Bengal"
api_version: "v2"
contact_email: "support@example.com"

❌ Vague:
name: "Bengal"
version: "v2"
email: "support@example.com"
```

## Escaping Variables

To show literal `{{ }}` syntax:

```markdown
Use {{/* page.title */}} to display the title.
```

**Result:**
```
Use {{ page.title }} to display the title.
```

## Variables vs Templates

### Use Variables For

✅ Simple value substitution in content:
- Product names and versions
- API endpoints
- Contact information
- Repeated text

### Use Templates For

✅ Logic and conditionals:
- Showing/hiding sections
- Loops over collections
- Complex formatting
- Layout decisions

**Example template:**
```jinja
<!-- templates/page.html -->
{% if page.metadata.beta %}
  <div class="beta-badge">Beta</div>
{% endif %}

{{ content }}  <!-- Markdown with variables renders here -->
```

## Quick Reference

**Access frontmatter:**
```markdown
{{ page.metadata.field_name }}
```

**Access page properties:**
```markdown
{{ page.title }}
{{ page.date }}
{{ page.url }}
```

**Access site config:**
```markdown
{{ site.config.site.title }}
{{ site.config.site.baseurl }}
```

## Next Steps

- **[Taxonomies](taxonomies.md)** - Tags and categories
- **[Navigation](navigation.md)** - Menus and links
- **[Frontmatter Guide](../writing/frontmatter-guide.md)** - Metadata

## Related

- [Markdown Basics](../writing/markdown-basics.md) - Markdown syntax
- [Content Types](../content-types/) - Page layouts
- [Writing Guide](../writing/) - Content creation

