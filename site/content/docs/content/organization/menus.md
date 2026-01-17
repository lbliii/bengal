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

:::{note} Core vs. Theme Features
**Bengal Core** builds the menu data structure—this works with any theme. How menus are *rendered* (dropdowns, styling, hover behavior) depends on your theme. The default theme supports all features described here. Custom themes need to implement dropdown rendering themselves.
:::

## Menu Processing Hierarchy

Bengal processes menu configuration in a clear hierarchy (most specific wins):

| Priority | Source | Description | Scope |
|----------|--------|-------------|-------|
| 1 | `[[menu.main]]` in config | Full manual control, disables all auto-magic | Core |
| 2 | `[menu.bundles.xxx]` in config | Define synthetic dropdowns (like Dev) | Core |
| 3 | `menu.dropdown` in frontmatter | Per-section dropdown configuration | Core |
| 4 | Auto-discovery defaults | Dev bundling, section discovery | Core |

## Auto Topbar Menu

If you do not define `[[menu.main]]`, Bengal generates a topbar menu automatically from your content sections.

- **Manual menu overrides auto menu**: If `menu.main` is present and non-empty, Bengal uses it and does not auto-discover.
- **Auto menu only includes "real" sections**: Auto-discovery builds items from sections that exist on disk.

### Dev Dropdown (Default Behavior)

By default, Bengal bundles development-related links into a **Dev** dropdown:

- **GitHub**: If `params.repo_url` is set
- **API Reference**: If an `api` section exists
- **CLI Reference**: If a `cli` section exists

The Dev dropdown appears when **2 or more** eligible items exist. With only one item, it appears as a standalone link.

#### Disable Auto Dev Bundle

```toml
[menu]
auto_dev_bundle = false
```

#### Customize the Dev Bundle

```toml
[menu.bundles.dev]
name = "Developer"     # Custom name (default: "Dev")
items = ["github", "api", "cli"]
min_items = 2          # Minimum items to show dropdown
weight = 90
```

### Add Extra Links (menu.extra)

Add one-off links to the auto-generated menu without replacing it entirely. Perfect for external links like forums, documentation, or social links:

```yaml
# config/_default/menu.yaml (or bengal.toml)
menu:
  extra:
    - name: "Forum"
      url: "https://community.example.com/"
      weight: 100
    - name: "Discord"
      url: "https://discord.gg/example"
      weight: 101
      icon: chat-circle
```

Or in TOML:

```toml
[[menu.extra]]
name = "Forum"
url = "https://community.example.com/"
weight = 100
```

Extra items are appended to the auto-discovered menu and respect the same properties as manual menu items (`name`, `url`, `weight`, `icon`).

## Section Dropdowns

Make any section display its children as a dropdown in the navigation.

:::{info} Theme Support
Bengal Core builds menu items with `children` arrays. The **default theme** renders these as hover dropdowns. Custom themes can access the same data via `item.children` in templates.
:::

### Show Subsections

Add `menu.dropdown: true` to a section's `_index.md`:

```yaml
---
title: Documentation
menu:
  dropdown: true
---
```

This shows the section's subsections as dropdown children.

### Data-Driven Dropdowns

Load dropdown items from a data file:

```yaml
---
title: Learning Tracks
menu:
  dropdown: data:tracks
---
```

This loads items from `data/tracks.yaml`. Each key becomes a dropdown item linking to `/{section}/{key}/`.

:::{example-label} Tracks Data File
:::

```yaml
# data/tracks.yaml
zero-to-deployed:
  title: "Zero to Deployed"
  description: "Build your first site"

content-mastery:
  title: "Content Author Mastery"
  description: "Master advanced features"
```

## Custom Bundles

Create synthetic dropdown menus that bundle multiple items:

```toml
[menu.bundles.resources]
name = "Resources"
url = "#"              # Non-clickable (dropdown only)
items = ["github", "api"]
min_items = 1
weight = 85
```

Available item types:
- `github` - Links to `params.repo_url`
- `api` - Links to `/api/` section
- `cli` - Links to `/cli/` section

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
| `icon` | string | Icon name (e.g., `book`, `folder`) |
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

## Non-Clickable Dropdown Parents

:::{tip} Default Theme Feature
The default theme automatically renders menu items with `url="#"` and children as non-clickable dropdown triggers. Custom themes can check `item.href == '#'` to implement similar behavior.
:::

When a menu item has children but no meaningful destination, use `url = "#"` to make it non-clickable:

```toml
[[menu.main]]
name = "Resources"
url = "#"           # Not a link, just opens dropdown
identifier = "resources"
weight = 80

[[menu.main]]
name = "Blog"
url = "/blog/"
parent = "resources"

[[menu.main]]
name = "Newsletter"
url = "/newsletter/"
parent = "resources"
```

The parent "Resources" will open the dropdown on hover but won't navigate anywhere when clicked.

:::{tip}
Bundles like Dev automatically use `url = "#"` since they're just containers for their children.
:::

## Accessing Menus in Templates

Use the `get_menu_lang()` template function to retrieve menu items with proper localization:

```jinja
{% let main_menu = get_menu_lang('main', current_lang()) %}
{% for item in main_menu %}
  <a href="{{ item.href | absolute_url }}">{{ item.name }}</a>
  {% if item.children %}
    <ul>
    {% for child in item.children %}
      <li><a href="{{ child.href | absolute_url }}">{{ child.name }}</a></li>
    {% end %}
    </ul>
  {% end %}
{% end %}
```

:::{note}
The `get_menu_lang(name, lang)` function returns menu items with active states already computed. Use `item.href` (not `item.url`) and apply `| absolute_url` for proper URL handling.
:::

### Menu Item Properties (Core)

All themes have access to these properties on each menu item:

| Property | Type | Description |
|----------|------|-------------|
| `item.name` | string | Display name |
| `item.href` | string | Link URL (use with `\| absolute_url` filter) |
| `item.children` | list | Child menu items (for dropdowns) |
| `item.active` | bool | True if current page |
| `item.active_trail` | bool | True if ancestor of current page |
| `item.icon` | string | Icon name (if set via frontmatter) |
| `item.identifier` | string | Unique ID for parent references |

### Dropdown-Only Detection

To render non-clickable dropdown triggers (like the default theme does):

```jinja
{% if item.children and item.href == '#' %}
  {# Render as button/span, not link #}
  <span class="dropdown-trigger">{{ item.name }}</span>
{% else %}
  <a href="{{ item.href }}">{{ item.name }}</a>
{% end %}
```
