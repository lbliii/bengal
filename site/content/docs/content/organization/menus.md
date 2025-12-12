---
title: Navigation Menus
nav_title: Menus
description: Configure navigation menus in Bengal
weight: 20
draft: false
lang: en
tags:
- menus
- navigation
- configuration
keywords:
- menus
- navigation
- sidebar
- header
- footer
category: guide
---

# Navigation Menus

Configure and customize navigation menus in Bengal.

## Overview

Bengal supports multiple menu types that can be configured in frontmatter or configuration files.

## Auto topbar menu (when `menu.main` is not defined)

If you do not define `menu.main`, Bengal generates a topbar menu automatically.

- **Manual menu overrides auto menu**: If `menu.main` is present and non-empty, Bengal uses it and does not auto-discover topbar items. (`bengal/orchestration/menu.py:401-406`, `bengal/rendering/template_functions/navigation.py:904-915`)
- **Auto menu only includes “real” sections**: Auto-discovery builds items from sections that exist on disk (virtual sections do not participate). (`bengal/rendering/template_functions/navigation.py:918-926`)

### Dev dropdown bundling

In auto mode, Bengal can bundle development-related links into a **Dev** dropdown in the topbar:

- **GitHub**: If `params.repo_url` is set, it is eligible to appear in Dev (or as a standalone link). (`bengal/orchestration/menu.py:221-226`, `bengal/themes/default/templates/base.html:272-286`)
- **API Reference**: If an `api` section exists, it is eligible to appear under Dev.
- **CLI Reference**: If a `cli` section exists, it is eligible to appear under Dev.
- **Bundling rule**: Dev dropdown appears when 2 or more eligible items exist. If only one eligible item exists, it appears as a normal top-level menu entry.

If you want a specific layout, define `menu.main` explicitly.

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
