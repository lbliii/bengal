---
title: From Sphinx/RST
nav_title: Sphinx
description: Onboarding guide for Sphinx and reStructuredText users migrating to Bengal
weight: 10
tags:
- tutorial
- migration
- sphinx
- rst
- myst
keywords:
- sphinx
- rst
- restructuredtext
- myst
- migration
- directives
---

# Bengal for Sphinx/RST Users

You're 80% there. Bengal uses MyST-compatible syntax that mirrors what you already know.

## Quick Wins (5 Minutes)

### Your Directives Work (Almost)

The only syntax change: `.. name::` becomes `:::{name}`.

| Sphinx/RST | Bengal | Works? |
|------------|--------|--------|
| `.. note::` | `:::{note}` | ✅ |
| `.. warning::` | `:::{warning}` | ✅ |
| `.. tip::` | `:::{tip}` | ✅ |
| `.. danger::` | `:::{danger}` | ✅ |
| `.. literalinclude::` | `:::{literalinclude}` | ✅ |
| `.. include::` | `:::{include}` | ✅ |

### Side-by-Side Example

:::{tab-set}

:::{tab} Sphinx (RST)
```rst
.. note:: Important

   This is a note with **bold** text.

.. code-block:: python
   :linenos:
   :emphasize-lines: 2

   def hello():
       print("Hello, World!")
```
:::{/tab}

:::{tab} Bengal (MyST)
````markdown
:::{note} Important
This is a note with **bold** text.
:::

```python
def hello():
    print("Hello, World!")
```
````
:::{/tab}

:::{/tab-set}

---

## Complete Feature Mapping

### Admonitions

| Sphinx | Bengal | Notes |
|--------|--------|-------|
| `.. note::` | `:::{note}` | Identical semantics |
| `.. warning::` | `:::{warning}` | Identical semantics |
| `.. tip::` | `:::{tip}` | Identical semantics |
| `.. danger::` | `:::{danger}` | Identical semantics |
| `.. seealso::` | `:::{seealso}` | Supported |
| `.. versionadded::` | `:::{since}` | Semantic versioning directive |
| `.. deprecated::` | `:::{deprecated}` | Semantic deprecation notice |
| `.. versionchanged::` | `:::{changed}` | Version change notice |
| `.. admonition:: Custom` | `:::{note} Custom Title` | Title in directive |

### Code Blocks

| Sphinx | Bengal | Notes |
|--------|--------|-------|
| `.. code-block:: python` | ` ```python ` | Standard fenced |
| `:linenos:` | Not built-in | CSS-based line numbers |
| `:emphasize-lines:` | Not built-in | Use comments to highlight |
| `.. highlight:: python` | Not needed | Each block specifies language |

### File Inclusion

| Sphinx | Bengal | Notes |
|--------|--------|-------|
| `.. literalinclude:: file.py` | `:::{literalinclude} file.py` | ✅ Same |
| `:lines: 1-10` | `:lines: 1-10` | ✅ Same option |
| `:language: python` | `:language: python` | ✅ Same option |
| `.. include:: file.md` | `:::{include} file.md` | ✅ Same |

**Example:**

```markdown
:::{literalinclude} ../examples/hello.py
:language: python
:lines: 5-15
:caption: Hello World Example
:::
```

### Cross-References

| Sphinx | Bengal | Notes |
|--------|--------|-------|
| `:ref:\`label\`` | `[[label]]` or `[text](./file.md)` | Different syntax |
| `:doc:\`path\`` | `[text](./file.md)` | Standard markdown |
| `:term:\`glossary\`` | `:::{glossary}` directive | Data-driven |
| `.. _label:` | `{#label}` in heading | MyST anchor syntax |

**Cross-reference examples:**

```markdown
<!-- Link to another page -->
[Configuration Guide](../reference/configuration.md)

<!-- Link with anchor -->
[Config Options](../reference/configuration.md#options)

<!-- Internal cross-reference -->
[[installation]]
```

### Table of Contents

| Sphinx | Bengal | Notes |
|--------|--------|-------|
| `.. toctree::` | Auto-generated from `weight` | File-system based |
| `:maxdepth: 2` | Sidebar depth in theme config | Theme setting |
| `:caption: Guide` | Section titles in `_index.md` | Content structure |
| `:hidden:` | `hidden: true` frontmatter | Per-page |

Bengal auto-generates navigation from your directory structure. Use `weight` frontmatter to control order:

```yaml
---
title: Installation
weight: 10  # Lower = appears first
---
```

### Configuration

| Sphinx (`conf.py`) | Bengal (`bengal.toml`) |
|--------------------|------------------------|
| `project = 'My Docs'` | `[site]`<br>`title = "My Docs"` |
| `extensions = [...]` | Built-in (no extensions needed) |
| `html_theme = 'sphinx_rtd_theme'` | `[site]`<br>`theme = "bengal"` |
| `html_static_path = ['_static']` | `assets/` directory |
| `templates_path = ['_templates']` | `themes/[name]/templates/` |

**Minimal `bengal.toml`:**

```toml
[site]
title = "My Documentation"
baseurl = "https://docs.example.com"
language = "en"
theme = "bengal"
```

### Directory Structure

| Sphinx | Bengal | Notes |
|--------|--------|-------|
| `source/` | `content/` | Content root |
| `_static/` | `assets/` | Static files |
| `_templates/` | `themes/[name]/templates/` | Template overrides |
| `conf.py` | `bengal.toml` | Configuration |
| `index.rst` | `_index.md` | Section index |
| `Makefile` | `bengal build` | Build command |

---

## What Bengal Adds (Sphinx Doesn't Have)

### Cards for Feature Grids

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

### Tab Sets

```markdown
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

:::{/tab-set}
```

### Visual Steps

```markdown
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

:::{/steps}
```

### Dropdowns (Collapsible Sections)

```markdown
:::{dropdown} Click to expand
:icon: info

Hidden content here. Supports **full markdown**.
:::
```

### Variable Substitution in Content

Bengal supports `{{ variable }}` substitution directly in markdown content:

```markdown
---
title: My Page
version: "2.0"
---

# Welcome to version {{ page.metadata.version }}

The current page is: {{ page.title }}

Site name: {{ site.config.title }}
```

Variables available in content:
- `page.title`, `page.url`, `page.date` - Page properties
- `page.metadata.xxx` - Custom frontmatter fields
- `site.config.xxx` - Site configuration values

### Hot Reload Development Server

```bash
bengal serve
# Live preview at http://localhost:5173
# Auto-reloads on file changes
```

---

## What's Different (Honest Gaps)

| Sphinx Feature | Bengal Status | Workaround |
|----------------|---------------|------------|
| `autodoc` (Python introspection) | Built-in | Configure in `bengal.toml` |
| `intersphinx` (cross-project refs) | Not built-in | Use explicit URLs |
| Custom builders (PDF, ePub) | HTML only | External tools |
| Domain-specific roles | Not built-in | Use directives |
| Numbered figures | Manual numbering | CSS counters |
| Math/LaTeX | Built-in support | KaTeX rendering |

### autodoc Alternative

Bengal has a built-in autodoc system that generates API documentation from Python source:

```yaml
# config/_default/autodoc.yaml
autodoc:
  python:
    enabled: true
    source_dirs: ["src/"]
    output_prefix: "api"  # Pages appear under /api/
```

This generates virtual pages during the build process, unlike Sphinx's runtime introspection. Run `bengal build` to generate API documentation from your Python source.

---

## Migration Checklist

:::{checklist} Before You Start
- [ ] Install Bengal: `pip install bengal`
- [ ] Create new site: `bengal new site mysite`
- [ ] Copy content files (`.rst` → `.md`)
:::

:::{checklist} Content Migration
- [ ] Convert `.. directive::` to `:::{directive}`
- [ ] Convert `:ref:` links to markdown link syntax
- [ ] Update code blocks to fenced syntax
- [ ] Add `weight` frontmatter for ordering
:::

:::{checklist} Configuration Migration
- [ ] Create `bengal.toml` from `conf.py` settings
- [ ] Move `_static/` to `assets/`
- [ ] Move `_templates/` to theme templates
:::

:::{checklist} Verify
- [ ] Build: `bengal build`
- [ ] Check links: `bengal health linkcheck`
- [ ] Preview: `bengal serve`
:::

---

## Quick Reference Card

| Task | Sphinx | Bengal |
|------|--------|--------|
| Create note | `.. note::` | `:::{note}` |
| Create warning | `.. warning::` | `:::{warning}` |
| Include file | `.. include::` | `:::{include}` |
| Include code | `.. literalinclude::` | `:::{literalinclude}` |
| Cross-reference | `:ref:\`label\`` | `[[label]]` |
| Link to doc | `:doc:\`path\`` | Standard markdown links |
| Build | `make html` | `bengal build` |
| Serve | `sphinx-autobuild` | `bengal serve` |
| Check | `sphinx-build -W` | `bengal health linkcheck` |

---

## Next Steps

- [Writer Quickstart](/docs/get-started/quickstart-writer/) - Full markdown reference
- [Directives Reference](/docs/reference/directives/) - All available directives
- [Configuration Reference](/docs/reference/configuration/) - Full config options
- [Cheatsheet](/docs/reference/cheatsheet/) - Quick syntax reference
