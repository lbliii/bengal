---
title: Migration Guides
nav_title: Migration
description: Migrate to Bengal from other static site generators
weight: 50
draft: false
type: doc
cascade:
  type: doc
icon: arrow-right-circle
---

# Migration Guides

Step-by-step guides to migrate your site from another static site generator to Bengal.

## Migration Overview

All migrations follow similar patterns, regardless of your source platform:

### Common Migration Steps

1. **Install Bengal**: `pip install bengal` or `uv add bengal`
2. **Create new site**: `bengal new site mysite`
3. **Copy content**: Transfer your markdown files to `content/`
4. **Convert syntax**: Replace platform-specific syntax with Bengal directives
5. **Update configuration**: Convert config files to `bengal.toml`
6. **Test and verify**: Run `bengal build` and `bengal health linkcheck`

### Universal Conversions

Most platforms use similar concepts that map to Bengal directives:

| Source Syntax | Bengal Directive | Common Use Case |
|---------------|------------------|-----------------|
| Shortcodes/Components | `:::{directive}` | Callouts, tabs, cards |
| Code highlighting | ` ```lang ` | Code blocks |
| Includes | `:::{include}` | Reusable content |
| Frontmatter | YAML frontmatter | Page metadata |

### What Stays the Same

- **Markdown files**: Your content files transfer directly
- **YAML frontmatter**: Frontmatter format is compatible
- **Directory structure**: `content/` structure works similarly
- **Static output**: All generators produce static HTML

### What Changes

- **Template syntax**: Each platform's template language → Jinja2
- **Component syntax**: Platform-specific components → Bengal directives
- **Configuration**: Platform config → `bengal.toml`
- **Build process**: Platform CLI → `bengal build`

:::{tip}
**Not sure which guide to follow?** Choose the guide for your current platform. If you're migrating from multiple platforms or a custom setup, start with the guide closest to your syntax (e.g., Hugo for shortcodes, Docusaurus for MDX components).
:::

### Common Issues

**Template variables not working?**
- Check the template variable mapping in your platform's guide
- Hugo users: `{{ .Params.x }}` → `{{ page.metadata.x }}`
- Jekyll users: `{{ page.custom }}` → `{{ page.metadata.custom }}`

**Directives not rendering?**
- Ensure you're using triple colons: `:::{note}` not `:::note`
- Check that directive names match exactly (case-sensitive)
- See the [Directives Reference](/docs/reference/directives/) for all available directives

**Configuration errors?**
- Verify `bengal.toml` syntax (TOML format)
- Check that all required `[site]` fields are present
- See the [Configuration Reference](/docs/building/configuration/) for details

**Links broken after migration?**
- Run `bengal health linkcheck` to find broken links
- Update relative paths if directory structure changed
- Check that asset paths use `/assets/` prefix

---

## Platform-Specific Guides

:::{cards}
:columns: 1-2-3
:gap: medium

:::{card} From Hugo
:icon: arrow-right
:link: ./from-hugo
:description: Hugo to Bengal migration
:::{/card}

:::{card} From Jekyll
:icon: arrow-right
:link: ./from-jekyll
:description: Jekyll to Bengal migration
:::{/card}

:::{card} From MkDocs
:icon: arrow-right
:link: ./from-mkdocs
:description: MkDocs to Bengal migration
:::{/card}

:::{card} From Sphinx
:icon: arrow-right
:link: ./from-sphinx
:description: Sphinx to Bengal migration
:::{/card}

:::{card} From Docusaurus
:icon: arrow-right
:link: ./from-docusaurus
:description: Docusaurus to Bengal migration
:::{/card}

:::{card} From Mintlify
:icon: arrow-right
:link: ./from-mintlify
:description: Mintlify to Bengal migration
:::{/card}

:::{card} From Fern
:icon: arrow-right
:link: ./from-fern
:description: Fern to Bengal migration
:::{/card}
:::{/cards}
