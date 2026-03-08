---
name: bengal-content-migration
description: Migrates content from Markdown, Jekyll, Hugo, or other SSGs to Bengal. Use when converting a site, importing posts, or restructuring content.
---

# Bengal Content Migration

Migrate content from other static site generators or plain Markdown to Bengal.

## Procedure

### Step 1: Map Frontmatter

Bengal uses YAML frontmatter. Map source fields:

| Source (Jekyll/Hugo) | Bengal | Notes |
|----------------------|--------|-------|
| title | title | Same |
| date | date | Use ISO format: '2026-01-01' |
| description | description | Same |
| tags | tags | List: `[a, b]` or `- a\n- b` |
| categories | category | Single string, or use tags |
| layout | type | e.g., type: blog |
| permalink | (omit) | Bengal derives from path |
| draft | draft | bool |
| author | params.author | Custom fields go in params |

### Step 2: Create Section Structure

Bengal uses `_index.md` for sections. For each content directory:

- Create `_index.md` with section metadata
- Use `type: blog` for blog sections
- Move individual posts as `*.md` files

### Step 3: Convert Shortcodes to Directives

| Jekyll/Hugo | Bengal |
|-------------|--------|
| `{% include file %}` | `:::{include} path/to/file.md` |
| `{{< highlight python >}}` | `:::{code-block} python` |
| `{{< note >}}` | `:::{note}` |
| Custom shortcodes | Map to Bengal directives or create custom |

### Step 4: Handle Assets

- Copy images to `static/` or theme `assets/`
- Update paths: use `asset_url('path')` in templates
- For content-relative images, place in `content/` alongside markdown (theme-dependent)

### Step 5: Taxonomy

- Add `tags` and `category` to frontmatter
- Bengal builds tag/category indexes automatically
- Use `site.indexes.section`, `site.indexes.category` in templates

## Checklist

- [ ] Frontmatter mapped (title, date, tags, description)
- [ ] _index.md created for each section
- [ ] Shortcodes converted to MyST directives
- [ ] Assets moved and paths updated
- [ ] Run bengal build and verify output

## Additional Resources

See [references/frontmatter-schema.md](references/frontmatter-schema.md) for frontmatter fields.
