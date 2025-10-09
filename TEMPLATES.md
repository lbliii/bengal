# Template System Guide

Bengal's template system is designed to be simple, predictable, and convention-based.

## Template Selection Priority

When rendering a page, Bengal selects a template in this order:

### For Section Index Pages (`_index.md`)

1. **Explicit template in frontmatter** (highest priority)
   ```yaml
   ---
   template: custom.html
   ---
   ```

2. **Section-specific templates** (checked in order):
   - `{section-name}/list.html` (e.g., `docs/list.html`)
   - `{section-name}/index.html` (e.g., `docs/index.html`)
   - `{section-name}-list.html` (e.g., `docs-list.html`)
   - `{section-name}.html` (e.g., `docs.html`)

3. **Default fallback**: `index.html`

### For Regular Pages

1. **Explicit template in frontmatter** (highest priority)
   ```yaml
   ---
   template: custom.html
   ---
   ```

2. **Section-specific templates** (checked in order):
   - `{section-name}/single.html` (e.g., `docs/single.html`)
   - `{section-name}/page.html` (e.g., `docs/page.html`)
   - `{section-name}.html` (e.g., `docs.html`)

3. **Default fallback**: `page.html`

## Content Type System (NEW!)

Bengal now supports **type-based template selection** - a semantic way to define content that's more intuitive than template paths.

### Quick Example

Instead of:
```yaml
---
title: My Tutorial
template: tutorial/single.html   # Implementation detail
---
```

Use:
```yaml
---
title: My Tutorial
type: tutorial                   # Semantic description
---
```

### How It Works

When you set `type: tutorial`, Bengal automatically looks for:
- `tutorial/single.html` (for regular pages)
- `tutorial/list.html` (for index pages)

### Updated Priority Chain

**With type system**, template selection is:

1. **Explicit `template:`** (highest priority)
2. **Type-based selection** (NEW!)
   - Check section's `content_type`
   - Check page's `type` field → map to template family
3. **Section name patterns**
4. **Default fallback**

### Available Types

- `doc` - Documentation (3-column with sidebar)
- `tutorial` - Step-by-step guides
- `blog` - Blog posts
- `api-reference` - API documentation
- `cli-reference` - CLI documentation

See [Content Types Guide](docs/CONTENT_TYPES.md) for full documentation.

### Cascading Types

Set once, applies to all children:

```yaml
# content/tutorials/_index.md
---
type: tutorial
cascade:
  type: tutorial    # All children inherit
---
```

## Template Hierarchy

Bengal uses different templates for different content types:

### `archive.html` - Chronological/Blog Content
**Purpose**: Display time-ordered content with pagination

**Used for**:
- Blog posts
- News articles
- Any dated content

**Features**:
- Reverse chronological order
- Featured posts section
- Pagination support
- Date-based display

**Auto-selected when**:
- Section name is `blog`, `posts`, `news`, or `articles`
- 60%+ of pages have dates in frontmatter

### `index.html` - Generic Section Landing
**Purpose**: Generic fallback for non-chronological sections

**Used for**:
- Documentation sections
- General content groupings
- Any section without specific type

**Features**:
- Lists subsections and pages
- Supports custom content from `_index.md`
- No pagination by default
- Helpful empty states

**Auto-selected when**:
- No specialized template matches
- Section doesn't fit blog/reference patterns

### `{type}/list.html` - Specialized Reference
**Purpose**: Type-specific reference documentation

**Available types**:
- `api-reference/list.html` - API documentation
- `cli-reference/list.html` - CLI commands
- `tutorial/list.html` - Tutorial listings

**Features**:
- Type-specific layouts
- No pagination (reference should be navigable)
- Rich metadata display
- Structured organization

**Auto-selected when**:
- Section name matches patterns (e.g., `api`, `cli`, `tutorials`)
- Page metadata contains type markers

### `page.html` - Single Content Page
**Purpose**: Individual content pages

**Used for**:
- Documentation pages
- Articles
- General content

**Features**:
- Full content display
- Table of contents sidebar
- Reading time
- Tag display
- Related content

## Index Files: `_index.md` vs `index.md`

Both `_index.md` and `index.md` are treated as section index files.

### Semantics
- **No functional difference** - both become the section's index page
- **Prefer `_index.md`** - follows Hugo convention and clearly indicates "section index"
- **Collision handling**: If both exist, `_index.md` takes precedence (with warning logged)

### Best Practice
Use **only one** index file per section:
```
content/
  docs/
    _index.md          ✅ Section index
    getting-started.md ✅ Regular page
    # NOT both _index.md AND index.md
```

### When Neither Exists
Bengal **auto-generates** an index page:
- Detects content type (archive, api, cli, etc.)
- Uses appropriate template
- Automatically lists child pages and subsections
- Adds helpful empty states

## Auto-Generated Index Pages

When a section has no `_index.md` or `index.md`, Bengal creates one automatically.

### Content Type Detection

Bengal analyzes the section to determine the best template:

1. **Explicit override** (highest priority):
   ```yaml
   # In _index.md frontmatter or cascade
   content_type: archive
   ```

2. **Section name patterns**:
   - `api`, `reference`, `api-reference` → `api-reference`
   - `cli`, `commands`, `cli-reference` → `cli-reference`
   - `tutorials`, `guides`, `how-to` → `tutorial`
   - `blog`, `posts`, `news`, `articles` → `archive`

3. **Content analysis**:
   - Checks page metadata for type markers
   - Counts pages with dates (60%+ → archive)

4. **Default**: `list` → uses `index.html`

### What Auto-Generated Pages Include

All auto-generated pages automatically show:
- ✅ Child pages as cards (with excerpts, dates, tags, images)
- ✅ Subsections with descriptions and counts
- ✅ Featured post separation (for archives)
- ✅ Empty states with helpful guidance
- ✅ Appropriate pagination (archives only)

## Customization

### Custom Templates
Place templates in `templates/` directory:
```
templates/
  custom.html        # Use with template: custom.html
  docs/
    single.html      # Auto-used for docs/ section pages
    list.html        # Auto-used for docs/ section index
```

### Override Content Type
```yaml
---
# In section _index.md
content_type: archive  # Force archive template
---
```

### Disable Auto-Generation
Create an empty `_index.md`:
```yaml
---
title: My Section
---
```

### Control Pagination
```yaml
---
# In section _index.md or cascade
paginate: true        # Force pagination
per_page: 20         # Items per page
---
```

## Common Patterns

### Blog Section
```
content/
  blog/
    _index.md        # Optional: custom intro
    post-1.md        # Must have date: in frontmatter
    post-2.md
```
Result: Uses `archive.html`, reverse chronological, paginated

### Documentation Section
```
content/
  docs/
    _index.md        # Optional: overview
    guide-1.md
    guide-2.md
    advanced/
      _index.md
      topic-1.md
```
Result: Uses `index.html`, hierarchical, no pagination

### API Reference Section
```
content/
  api/               # Or name it 'reference', 'api-reference'
    module-1.md
    module-2.md
```
Result: Uses `api-reference/list.html`, structured layout

## Troubleshooting

### Both `index.md` and `_index.md` exist
**Symptom**: Warning in logs
**Solution**: Remove one (prefer keeping `_index.md`)

### Wrong template being used
**Check**:
1. Frontmatter `template` field (overrides everything)
2. Section name matches patterns
3. Content type detection heuristics
4. Template exists in theme

**Force specific template**:
```yaml
---
template: archive.html
---
```

### Empty section shows no content
**This is expected** - Bengal shows helpful guidance
**To populate**:
- Add pages to the section directory
- Create `_index.md` with custom content
- Add subsections

### Archive not paginating
**Check**: Content type must be `archive` and page count must exceed threshold
**Force pagination**:
```yaml
---
content_type: archive
paginate: true
---
```

