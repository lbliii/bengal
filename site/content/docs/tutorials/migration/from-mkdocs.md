---
title: From MkDocs
nav_title: MkDocs
description: Onboarding guide for MkDocs and Material for MkDocs users migrating to Bengal
weight: 15
tags:
- tutorial
- migration
- mkdocs
- material
keywords:
- mkdocs
- material for mkdocs
- migration
- python documentation
---

# Bengal for MkDocs Users

You're in familiar territory. Both tools are Python-native and use Markdown. The main change: MkDocs extensions become Bengal directives.

## Quick Wins (5 Minutes)

### What Works The Same

| MkDocs | Bengal | Status |
|--------|--------|--------|
| `docs/` structure | `content/` | ✅ Similar |
| Markdown files | Markdown files | ✅ Identical |
| YAML frontmatter | YAML frontmatter | ✅ Identical |
| `mkdocs.yml` | `bengal.toml` | ✅ Similar |
| `pip install` | `pip install` | ✅ Same ecosystem |

### The Key Difference

MkDocs extensions → Bengal directives:

```markdown
<!-- MkDocs (with admonition extension) -->
!!! note "Title"
    This is a note

<!-- Bengal -->
:::{note} Title
This is a note
:::
```

---

## Extension → Directive Translation

### Admonitions

:::{tab-set}

:::{tab} MkDocs
```markdown
!!! note
    This is a note.

!!! warning "Be Careful"
    This is a warning with a custom title.

!!! tip
    A helpful tip.

!!! danger
    Critical warning!

??? note "Collapsible"
    This content is hidden by default.
```
:::{/tab}

:::{tab} Bengal
```markdown
:::{note}
This is a note.
:::

:::{warning} Be Careful
This is a warning with a custom title.
:::

:::{tip}
A helpful tip.
:::

:::{danger}
Critical warning!
:::

:::{dropdown} Collapsible
:icon: note
This content is hidden by default.
:::
```
:::{/tab}

:::{/tab-set}

### Admonition Types Mapping

| MkDocs | Bengal | Notes |
|--------|--------|-------|
| `!!! note` | `:::{note}` | ✅ Same |
| `!!! warning` | `:::{warning}` | ✅ Same |
| `!!! tip` | `:::{tip}` | ✅ Same |
| `!!! danger` | `:::{danger}` | ✅ Same |
| `!!! info` | `:::{info}` | ✅ Same |
| `!!! example` | `:::{example}` | ✅ Same |
| `!!! quote` | `:::{epigraph}` | Different name |
| `!!! bug` | `:::{danger}` | Use danger |
| `!!! abstract` | `:::{note}` | Use note |
| `??? note` (collapsible) | `:::{dropdown}` | Different syntax |
| `???+ note` (open) | `:::{dropdown}` + `:open:` | Different syntax |

### Tabs (with pymdownx.tabbed)

:::{tab-set}

:::{tab} MkDocs
````markdown
=== "Python"

    ```python
    print("Hello")
    ```

=== "JavaScript"

    ```javascript
    console.log("Hello");
    ```
````
:::{/tab}

:::{tab} Bengal
````markdown
:::{tab-set}
:::{tab} Python
```python
print("Hello")
```
:::{/tab}
:::{tab} JavaScript
```javascript
console.log("Hello");
```
:::{/tab}
:::{/tab-set}
````
:::{/tab}

:::{/tab-set}

### Code Blocks

:::{tab-set}

:::{tab} MkDocs
````markdown
```python title="hello.py" linenums="1" hl_lines="2"
def hello():
    print("Hello!")  # highlighted
    return True
```
````
:::{/tab}

:::{tab} Bengal
````markdown
```python
# hello.py
def hello():
    print("Hello!")  # use comments for emphasis
    return True
```
````
:::{/tab}

:::{/tab-set}

### Content Tabs with Code

:::{tab-set}

:::{tab} MkDocs
````markdown
=== "pip"

    ```bash
    pip install mypackage
    ```

=== "conda"

    ```bash
    conda install mypackage
    ```

=== "uv"

    ```bash
    uv add mypackage
    ```
````
:::{/tab}

:::{tab} Bengal
````markdown
:::{tab-set}
:::{tab} pip
```bash
pip install mypackage
```
:::{/tab}
:::{tab} conda
```bash
conda install mypackage
```
:::{/tab}
:::{tab} uv
```bash
uv add mypackage
```
:::{/tab}
:::{/tab-set}
````
:::{/tab}

:::{/tab-set}

---

## Configuration Mapping

### Basic Site Config

:::{tab-set}

:::{tab} MkDocs (mkdocs.yml)
```yaml
site_name: My Documentation
site_url: https://docs.example.com
site_description: My awesome docs

theme:
  name: material
  palette:
    primary: indigo
    accent: indigo

nav:
  - Home: index.md
  - Guide:
    - Getting Started: guide/getting-started.md
    - Installation: guide/installation.md
```
:::{/tab}

:::{tab} Bengal (bengal.toml)
```toml
[site]
title = "My Documentation"
baseurl = "https://docs.example.com"
description = "My awesome docs"
theme = "bengal"

# Navigation is auto-generated from directory structure
# Use weight frontmatter to control order
```
:::{/tab}

:::{/tab-set}

### Navigation

MkDocs requires explicit nav configuration in `mkdocs.yml`. Bengal auto-generates navigation from your directory structure using `weight` frontmatter:

```yaml
---
title: Getting Started
weight: 10  # Lower = appears first
---
```

:::{tip}
This is a major simplification. Add a page, and it appears in nav automatically. No config file edits needed.
:::

### Extensions → Built-in

| MkDocs Extension | Bengal | Notes |
|-----------------|--------|-------|
| `admonition` | Built-in | `:::{note}`, `:::{warning}`, etc. |
| `pymdownx.tabbed` | Built-in | `:::{tab-set}` |
| `pymdownx.details` | Built-in | `:::{dropdown}` |
| `pymdownx.superfences` | Built-in | Fenced code blocks |
| `pymdownx.highlight` | Built-in | Syntax highlighting |
| `pymdownx.inlinehilite` | Built-in | Inline code highlighting |
| `toc` | Built-in | Auto-generated TOC |
| `tables` | Built-in | Standard markdown tables |
| `attr_list` | Limited | Use directive options |
| `def_list` | Built-in | Standard markdown |
| `footnotes` | Built-in | Standard markdown |
| `meta` | Built-in | YAML frontmatter |
| `pymdownx.emoji` | Not built-in | Use unicode emoji |
| `pymdownx.arithmatex` | Built-in | KaTeX math support |

---

## Directory Structure Comparison

| MkDocs | Bengal | Notes |
|--------|--------|-------|
| `docs/` | `content/` | Content root |
| `docs/index.md` | `content/_index.md` | Home page |
| `docs/assets/` | `assets/` | Static files |
| `mkdocs.yml` | `bengal.toml` | Configuration |
| `overrides/` | `themes/[name]/templates/` | Template overrides |
| `custom_theme/` | `themes/[name]/` | Custom themes |

---

## What Bengal Adds (MkDocs Doesn't Have Built-in)

:::::{tab-set}

::::{tab} Cards Grid
```markdown
:::{cards}
:columns: 3

:::{card} Quick Start
:icon: rocket
:link: quickstart

Get started in 5 minutes
:::{/card}

:::{card} API Reference
:icon: book
:link: api/

Complete API docs
:::{/card}

:::{/cards}
```
::::{/tab}

::::{tab} Visual Steps
````markdown
:::{steps}

:::{step} Install Dependencies
```bash
pip install bengal
```
:::{/step}

:::{step} Create Site
```bash
bengal new site mysite
```
:::{/step}

:::{step} Start Server
```bash
bengal serve
```
:::{/step}

:::{/steps}
````
::::{/tab}

::::{tab} Data Tables
```markdown
:::{data-table}
:source: data/products.yaml
:columns: name, price, stock
:sortable: true
:filterable: true
:::
```
::::{/tab}

::::{tab} Variables in Content
Bengal supports `{{ variable }}` substitution directly in markdown:

```markdown
---
title: Release Notes
version: "2.5.0"
---

# {{ page.title }}

Current version: **{{ page.metadata.version }}**

Site: {{ site.config.title }}
```
::::{/tab}

::::{tab} Built-in Autodoc
```yaml
# config/_default/autodoc.yaml
autodoc:
  python:
    enabled: true
    source_dirs: ["src/"]
    output_prefix: "api"
```

No external plugins needed for Python API docs.
::::{/tab}

:::::{/tab-set}

---

## What's Different (Honest Gaps)

| MkDocs Feature | Bengal Status | Workaround |
|----------------|---------------|------------|
| Material theme features | Different theme | Bengal has its own theme |
| `mkdocs-material` insiders | Not applicable | Use Bengal's built-in features |
| Explicit nav ordering | Auto from `weight` | Add frontmatter |
| Plugin ecosystem | Built-in features | Most common plugins built-in |
| `mkdocstrings` | Built-in autodoc | Different configuration |
| Search (Lunr.js) | Built-in search | Similar functionality |
| Social cards | Not built-in | Use external tools |
| Blog plugin | Built-in blog | Different configuration |

### Material for MkDocs Specific

If you're using Material for MkDocs, here's what to expect:

| Material Feature | Bengal Equivalent |
|------------------|-------------------|
| Instant loading | Not built-in (static HTML) |
| Dark/light toggle | Built-in theme toggle |
| Search suggestions | Built-in search |
| Content tabs | `:::{tab-set}` |
| Annotations | Use `:::{note}` |
| Icons/emojis | Built-in icons (Phosphor) |
| Code copy button | Built-in |
| Navigation tabs | Theme configuration |
| Back to top | Built-in |

---

## Migration Steps

:::{steps}
:::{step} Install Bengal
```bash
pip install bengal
# or with uv
uv add bengal
```
:::{/step}

:::{step} Create New Site
```bash
bengal new site mysite
cd mysite
```
:::{/step}

:::{step} Copy Content
```bash
# Copy your MkDocs content
cp -r /path/to/mkdocs/docs/* content/

# Rename index.md to _index.md for sections
find content -name "index.md" -exec sh -c 'mv "$1" "$(dirname "$1")/_index.md"' _ {} \;
```
:::{/step}

:::{step} Convert Admonitions
Search for `!!!` and convert to directives:

```bash
# Find all admonition usages
grep -r "!!!" content/
```

| Find | Replace With |
|------|--------------|
| `!!! note` | `:::{note}` |
| `!!! warning` | `:::{warning}` |
| `!!! tip` | `:::{tip}` |
| `??? note` | `:::{dropdown}` |
:::{/step}

:::{step} Convert Tabs
Replace `=== "Tab Name"` syntax with Bengal's tab directives. Tabs must be wrapped in `:::{tab-set}`:

**MkDocs**:
````markdown
=== "Python"

    ```python
    print("Hello")
    ```

=== "JavaScript"

    ```javascript
    console.log("Hello");
    ```
````

**Bengal**:
````markdown
:::{tab-set}
:::{tab} Python
```python
print("Hello")
```
:::{/tab}
:::{tab} JavaScript
```javascript
console.log("Hello");
```
:::{/tab}
:::{/tab-set}
````
:::{/step}

:::{step} Add Weight Frontmatter
Add ordering to pages:

```yaml
---
title: Getting Started
weight: 10
---
```
:::{/step}

:::{step} Update Config
Create `bengal.toml` based on your `mkdocs.yml`:

```toml
[site]
title = "My Documentation"
baseurl = "https://docs.example.com"
theme = "bengal"
```
:::{/step}

:::{step} Test
```bash
bengal build
bengal health linkcheck
bengal serve
```
:::{/step}
:::{/steps}

---

## Migration Checklist

:::{checklist} Before You Start
- [ ] Install Bengal: `pip install bengal`
- [ ] Backup your MkDocs site
- [ ] Create new Bengal site: `bengal new site mysite`
:::

:::{checklist} Content Migration
- [ ] Copy `docs/` to `content/`
- [ ] Rename `index.md` to `_index.md` for sections
- [ ] Convert `!!! note` to `:::{note}`
- [ ] Convert `=== "Tab"` to `:::{tab}` syntax
- [ ] Add `weight` frontmatter for ordering
:::

:::{checklist} Assets Migration
- [ ] Copy `docs/assets/` to `assets/`
- [ ] Update asset paths if needed
:::

:::{checklist} Config Migration
- [ ] Create `bengal.toml` from `mkdocs.yml`
- [ ] Remove extension references (built-in)
- [ ] Update theme settings
:::

:::{checklist} Verify
- [ ] Build: `bengal build`
- [ ] Check: `bengal health linkcheck`
- [ ] Preview: `bengal serve`
:::

---

## Quick Reference Card

| Task | MkDocs | Bengal |
|------|--------|--------|
| New site | `mkdocs new` | `bengal new site` |
| Build | `mkdocs build` | `bengal build` |
| Serve | `mkdocs serve` | `bengal serve` |
| Note | `!!! note` | `:::{note}` |
| Warning | `!!! warning` | `:::{warning}` |
| Collapsible | `??? note` | `:::{dropdown}` |
| Tabs | `=== "Tab"` | `:::{tab}` Tab |
| Config | `mkdocs.yml` | `bengal.toml` |

---

## Common Questions

:::{dropdown} Can I keep my Material theme?
:icon: question

No. Bengal has its own theme designed for technical documentation. Many Material features have Bengal equivalents (dark mode, search, code copy, tabs), but the visual design is different.
:::

:::{dropdown} What about mkdocstrings for API docs?
:icon: question

Bengal has built-in autodoc that generates Python API documentation. Configure it in `config/_default/autodoc.yaml`. It works at build time, scanning your source code directly.
:::

:::{dropdown} Can I use MkDocs plugins?
:icon: question

MkDocs plugins are not compatible. However, most popular plugin functionality is built into Bengal: search, tags, blog, API docs, diagrams (Mermaid), math (KaTeX). Check the directives reference for equivalents.
:::

:::{dropdown} What about the explicit nav in mkdocs.yml?
:icon: question

Bengal auto-generates navigation from your directory structure. Use `weight` frontmatter to control order and `hidden: true` to exclude pages. This is simpler once you're used to it—no config file updates when adding pages.
:::

---

## Next Steps

- [Writer Quickstart](/docs/get-started/quickstart-writer/) - Full markdown reference
- [Directives Reference](/docs/reference/directives/) - All available directives
- [Configuration Reference](/docs/building/configuration/) - Full config options
- [Cheatsheet](/docs/reference/cheatsheet/) - Quick syntax reference
