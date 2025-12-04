---
title: Navigation Menus
description: Configure navigation menus in Bengal
weight: 20
draft: false
lang: en
tags: [menus, navigation, configuration]
keywords: [menus, navigation, sidebar, header, footer]
category: guide
---

# Navigation Menus

Configure and customize navigation menus in Bengal.

## Overview

Bengal supports multiple menu types that can be configured in frontmatter or configuration files.

## Frontmatter Configuration

Add pages to menus directly in frontmatter:

```yaml
---
title: About Us
menu:
  main:
    weight: 10
  footer:
    weight: 5
    name: About  # Override display name
---
```

## Configuration File Menus

Define menus in `bengal.toml` for non-content pages:

```toml
[[menu.main]]
name = "GitHub"
url = "https://github.com/your-org/your-repo"
weight = 100

[[menu.main]]
name = "Documentation"
url = "/docs/"
weight = 10
```

## Menu Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | Display text (defaults to page title) |
| `url` | string | Link destination |
| `weight` | integer | Sort order (lower = first) |
| `pre` | string | HTML before name (icons, etc.) |
| `post` | string | HTML after name |
| `parent` | string | Parent menu item for nesting |
| `identifier` | string | Unique ID for parent references |

## Nested Menus

Create hierarchical menus with `parent` and `identifier`:

```yaml
# Parent item
---
title: Products
menu:
  main:
    identifier: products
    weight: 20
---

# Child item
---
title: Bengal Pro
menu:
  main:
    parent: products
    weight: 10
---
```

## Accessing Menus in Templates

```jinja
{% for item in site.menus.main %}
  <a href="{{ item.url }}">{{ item.name }}</a>
  {% if item.children %}
    <ul>
    {% for child in item.children %}
      <li><a href="{{ child.url }}">{{ child.name }}</a></li>
    {% endfor %}
    </ul>
  {% endif %}
{% endfor %}
```



