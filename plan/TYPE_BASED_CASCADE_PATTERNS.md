# Type-Based Cascade Patterns

**Feature**: Type-aware template selection with cascading support  
**Status**: Implemented  
**Version**: 2025-10-09

## Overview

Bengal now supports type-based template selection that works with cascading, enabling powerful "template families" that apply consistently across entire sections.

## How It Works

### Template Selection Priority

```
1. template: custom.html        (explicit - highest priority)
2. type: doc                    (semantic type - NEW!)
   ├─ For index: doc/list.html
   └─ For pages: doc/single.html
3. Section name patterns
   ├─ For index: docs/list.html
   └─ For pages: docs/single.html
4. Default fallback
   ├─ For index: index.html
   └─ For pages: page.html
```

### Type Mappings

Built-in mappings (extensible):
```python
type_mappings = {
    'python-module': 'api-reference',    # Autodoc Python
    'cli-command': 'cli-reference',      # Autodoc CLI
    'api-reference': 'api-reference',    # Generic API
    'cli-reference': 'cli-reference',    # Generic CLI
    'doc': 'doc',                        # Documentation
    'tutorial': 'tutorial',              # Tutorials
    'blog': 'blog',                      # Blog posts
}
```

## Usage Patterns

### Pattern 1: Uniform Section Type

Apply one type to an entire section:

```yaml
# content/tutorials/_index.md
---
title: Tutorials
description: Step-by-step guides
type: tutorial           # Index → tutorial/list.html
cascade:
  type: tutorial         # Children → tutorial/single.html
---
```

**Benefits:**
- ✅ Set once, applies to all pages
- ✅ Consistent rendering across section
- ✅ Self-documenting (section IS tutorials)
- ✅ Easy to reorganize (change type, not templates)

### Pattern 2: Documentation Portal

Create a full documentation site with sidebar navigation:

```yaml
# content/docs/_index.md
---
title: Documentation
type: doc
cascade:
  type: doc
---
```

**All pages automatically get:**
- Three-column layout
- Left sidebar navigation
- Right sidebar TOC
- Breadcrumbs
- Prev/next navigation

### Pattern 3: Mixed Content Types

Different types for index vs children:

```yaml
# content/api/_index.md
---
title: API Reference
type: api-reference           # Index → api-reference/list.html (grid)
cascade:
  type: python-module         # Children → api-reference/single.html (details)
---
```

This makes sense because:
- The index is a reference list (grid of modules)
- The children are module documentation (detailed pages)

### Pattern 4: Override When Needed

Default with exceptions:

```yaml
# content/docs/_index.md
---
type: doc
cascade:
  type: doc              # Default for all
---
```

```yaml
# content/docs/tutorial-page.md
---
title: Getting Started Tutorial
type: tutorial           # Override: use tutorial template instead
---
```

### Pattern 5: Multi-Level Cascade

Nested sections can override:

```yaml
# content/guides/_index.md
---
type: tutorial
cascade:
  type: tutorial
---
```

```yaml
# content/guides/advanced/_index.md
---
title: Advanced Guides
type: doc                # Different type for this subsection
cascade:
  type: doc              # Override parent cascade
---
```

## Theme Development

### Creating Template Families

Structure templates by content type:

```
themes/my-theme/templates/
  
  # Documentation family
  doc/
    list.html       # Simple list of docs
    single.html     # 3-column with sidebar
  
  # Tutorial family  
  tutorial/
    list.html       # Grid with difficulty ratings
    single.html     # Step-by-step layout
  
  # Blog family
  blog/
    list.html       # Reverse-chrono with pagination
    single.html     # Article layout with author
  
  # API reference family
  api-reference/
    list.html       # Module grid with stats
    single.html     # 3-column with API nav
```

### Template Family Design

Each family should be **thematically consistent**:

**Documentation Family:**
- Focus: Clarity, navigation, reference
- Layout: Multi-column, sidebars, hierarchical
- Features: TOC, breadcrumbs, search, prev/next

**Tutorial Family:**
- Focus: Learning, progression, steps
- Layout: Linear flow, prominent next/prev
- Features: Progress indicator, difficulty, time estimate

**Blog Family:**
- Focus: Engagement, discovery, chronology
- Layout: Featured posts, cards, author info
- Features: Dates, tags, related posts, comments

**API Reference Family:**
- Focus: Scannability, hierarchy, examples
- Layout: 3-column, tree navigation, anchor links
- Features: Source links, copy buttons, syntax highlighting

## Real-World Examples

### Example 1: Documentation Site

```
content/
  docs/
    _index.md          (type: doc, cascade: type: doc)
    getting-started.md (inherits type: doc)
    installation.md    (inherits type: doc)
    configuration.md   (inherits type: doc)
    advanced/
      _index.md        (inherits type: doc)
      plugins.md       (inherits type: doc)
```

**Result:** Entire docs section uses doc template family, consistent sidebar navigation.

### Example 2: Product Site

```
content/
  docs/
    _index.md          (type: doc, cascade: type: doc)
    *.md               (all get doc templates)
  
  tutorials/
    _index.md          (type: tutorial, cascade: type: tutorial)
    *.md               (all get tutorial templates)
  
  blog/
    _index.md          (type: blog, cascade: type: blog)  
    *.md               (all get blog templates)
  
  api/
    _index.md          (type: api-reference, autodoc)
    *.md               (autodoc sets type: python-module)
```

**Result:** 
- 4 distinct content types
- 4 different template families
- Each section has appropriate layout
- Zero `template:` fields in individual pages

### Example 3: Multi-Language Docs

```
content/
  en/docs/_index.md  (type: doc, cascade: type: doc)
  es/docs/_index.md  (type: doc, cascade: type: doc)
  fr/docs/_index.md  (type: doc, cascade: type: doc)
```

**Result:** All languages use same template family, consistent UX.

## Migration Guide

### From Section-Based Templates

**Before:**
```
content/
  docs/
    page-1.md
    page-2.md

themes/default/templates/
  docs/
    single.html
```

Pages got `docs/single.html` based on section name.

**After (optional enhancement):**
```yaml
# content/docs/_index.md
---
type: doc
cascade:
  type: doc
---
```

```
themes/default/templates/
  doc/              # Note: singular, semantic
    single.html
  
  docs/             # Keep for backward compatibility
    single.html     # Could extend doc/single.html
```

**Benefits:**
- Type is portable (works in any section)
- More semantic (`type: doc` vs section named `docs`)
- Can have multiple doc sections (guides, reference, manual)

### From Template Frontmatter

**Before:**
```yaml
# Every page had to specify
---
title: My Page
template: doc.html
---
```

**After:**
```yaml
# In _index.md, set once
---
cascade:
  type: doc
---

# Individual pages are clean
---
title: My Page
# type is inherited, template is automatic
---
```

## Best Practices

### 1. Use Semantic Types

✅ **Good:**
```yaml
type: doc           # What it IS
type: tutorial      # Content type
type: api-reference # Semantic meaning
```

❌ **Avoid:**
```yaml
type: three-column  # Layout detail
type: with-sidebar  # Implementation
```

### 2. Cascade at Section Root

Set type in `_index.md` for consistency:

```yaml
# content/section/_index.md
---
type: tutorial
cascade:
  type: tutorial    # Applies to all children
---
```

### 3. Override Sparingly

Most pages should inherit type. Override only when truly different:

```yaml
# content/docs/special.md
---
title: Interactive Demo
type: tutorial      # This one is different
---
```

### 4. Document Your Types

Create a conventions doc:

```markdown
# Content Types

- `doc` - Reference documentation (3-column, sidebar)
- `tutorial` - Step-by-step guides (linear flow)
- `blog` - Blog posts (article layout, dates)
- `api-reference` - API documentation (auto nav)
```

### 5. Keep Fallbacks

Always provide fallback templates:

```
templates/
  doc/
    single.html
  page.html    # Fallback for untyped content
  index.html   # Fallback for untyped indexes
```

## Advanced Patterns

### Pattern: Type-Based Styling

Use type as a CSS class:

```jinja2
{# templates/base.html #}
<body class="page-type-{{ page.metadata.get('type', 'default') }}">
```

Then style differently:

```css
.page-type-doc { --primary-color: blue; }
.page-type-tutorial { --primary-color: green; }
.page-type-blog { --primary-color: purple; }
```

### Pattern: Type-Based Navigation

Show different nav based on type:

```jinja2
{% if page.metadata.type == 'doc' %}
  {% include 'partials/docs-nav.html' %}
{% elif page.metadata.type == 'tutorial' %}
  {% include 'partials/tutorial-nav.html' %}
{% endif %}
```

### Pattern: Type Inheritance Chains

```yaml
# Root cascade
---
cascade:
  layout_style: modern
  type: doc
---

# Child can add to it
---
type: doc
cascade:
  type: doc
  difficulty: advanced  # Add new fields
---
```

## Troubleshooting

### Type Not Working

**Check:**
1. Is type spelled correctly in mapping?
2. Does the template exist? (`doc/single.html`)
3. Is it a reserved word conflicting with other metadata?

**Debug:**
```yaml
# Add to page temporarily
---
template: doc/single.html  # Force it to see if template works
---
```

### Cascade Not Applying

**Ensure:**
- `cascade:` is in the parent `_index.md`
- Child pages are actually children (same section)
- No explicit override in child frontmatter

**Test:**
```yaml
# Child page - check if cascade works
{{ page.metadata.type }}  # Should show cascaded value
```

### Template Fallback Unexpected

Template selection is lenient. If `doc/single.html` doesn't exist:
1. Tries `doc/page.html`
2. Falls back to section name (`docs/single.html`)
3. Falls back to `page.html`

Check template directories and naming.

## Why This Matters

### Separation of Concerns

```yaml
# Content author thinks: "This is a tutorial"
type: tutorial

# Theme developer thinks: "Tutorials need step indicators"
templates/tutorial/single.html
```

Perfect separation - content describes itself, theme handles presentation.

### Maintainability

Changing 50 pages from one template to another:

**Before:**
```bash
# Edit 50 files, change template: field
```

**After:**
```yaml
# Edit 1 file (_index.md), change cascade type
---
cascade:
  type: new-type
---
```

### Portability

Content with types is portable between themes:

```yaml
---
type: tutorial
---
```

Works with any theme that implements `tutorial/single.html`.

### Discoverability

New users understand:
- ✅ `type: doc` - "I'm writing documentation"
- ❌ `template: themes/default/templates/docs/single.html` - "What?"

## Conclusion

Type-based cascading enables:
- **Less boilerplate** - set once per section
- **More semantics** - describe content, not presentation
- **Better portability** - types work across themes
- **Easier maintenance** - change types, not template paths
- **Clear intent** - self-documenting content structure

This is **not strictly necessary** but makes Bengal significantly more ergonomic for:
- Large documentation sites (100s of pages)
- Multi-section sites (docs + tutorials + blog + API)
- Teams (consistent conventions)
- Theme developers (create families, not one-offs)

