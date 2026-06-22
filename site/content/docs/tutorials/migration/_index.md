---
title: Migration Guides
nav_title: Migration
description: Migrate to Bengal from other static site generators
weight: 50
draft: false
icon: arrow-right
tags:
- persona-migrator
---

# Migration Guides

Move from Hugo, Jekyll, MkDocs, Sphinx, Docusaurus, Mintlify, or Fern without
restarting from scratch.

:::{note}
**Do I need this?** Yes when you have an existing site on another SSG. Start
with the guide for your current platform below. For a greenfield site, use
[[docs/get-started|Get Started]] instead.
:::

All migrations share the same high-level flow — install Bengal, copy content,
convert syntax, update config, then verify with `bengal build` and
`bengal check`.

## Common Migration Steps

```{include} _snippets/migration/common-steps.md
```

## Universal Conversions

Most platforms use similar concepts that map to Bengal directives:

| Source Syntax | Bengal Directive | Common Use Case |
|---------------|------------------|-----------------|
| Shortcodes/Components | `:::{directive}` | Callouts, tabs, cards |
| Code highlighting | ` ```lang ` | Code blocks |
| Includes | `:::{include}` | Reusable content |
| Frontmatter | YAML frontmatter | Page metadata |

### What Stays the Same

- **Markdown files** — content transfers directly
- **YAML frontmatter** — compatible format
- **Directory structure** — `content/` works similarly
- **Static output** — all generators produce static HTML

### What Changes

- **Template syntax** — platform template language → Kida
- **Component syntax** — platform components → Bengal directives
- **Configuration** — platform config → `bengal.toml` / `config/`
- **Build process** — platform CLI → `bengal build`

:::{tip}
**Not sure which guide to follow?** Pick your current platform. If you use a
custom setup, start with the guide closest to your syntax (Hugo for shortcodes,
Docusaurus for MDX components, Sphinx for RST directives).
:::

## Platform-Specific Guides

:::{child-cards}
:columns: 2
:include: pages
:fields: title, description, icon
:::

## Troubleshooting Migrations

**Template variables not working?**
- Check the template variable mapping in your platform's guide
- Hugo: `{{ .Params.x }}` → `{{ page.metadata.x }}`
- Jekyll: `{{ page.custom }}` → `{{ page.metadata.custom }}`

**Directives not rendering?**
- Use triple colons: `:::{note}` not `:::note`
- Directive names are case-sensitive
- See [[docs/reference/directives|Directives Reference]] for the full list

**Configuration errors?**
- Verify `bengal.toml` or `config/` layout
- Run `bengal config doctor`
- See [[docs/building/configuration|Configuration Guide]]

**Links broken after migration?**
- Run `bengal check` to find broken links
- Update relative paths if directory structure changed
- Ensure asset paths use the correct prefix for your theme
