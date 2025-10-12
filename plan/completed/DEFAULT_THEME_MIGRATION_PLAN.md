# Default Theme: Macro Migration Plan

**Date:** 2025-10-12  
**Status:** 🎯 In Progress

## Current State

### Existing Partials (17 files)

```
partials/
├── components.html              ✅ NEW - Has 3 macros
├── reference-header.html        🔄 OLD - Being replaced by macro
├── reference-metadata.html      🔄 OLD - Being replaced by macro
├── article-card.html            📦 → UI component macro
├── breadcrumbs.html             📦 → Navigation component macro
├── child-page-tiles.html        📦 → Layout component macro
├── docs-meta.html               ⚠️  Keep as include (complex)
├── docs-nav-section.html        ⚠️  Keep as include (nested)
├── docs-nav.html                ⚠️  Keep as include (very complex)
├── page-navigation.html         📦 → Navigation component macro
├── pagination.html              📦 → Navigation component macro
├── popular-tags.html            📦 → Content component macro
├── random-posts.html            📦 → Content component macro
├── search.html                  ⚠️  Keep as include (complex)
├── section-navigation.html      📦 → Navigation component macro
├── tag-list.html                📦 → Content component macro
└── toc-sidebar.html             📦 → Navigation component macro
```

**Legend:**
- ✅ New macro file
- 🔄 Old include being replaced
- 📦 Should become macro
- ⚠️  Keep as include

## Analysis: What Should Be a Macro?

### Convert to Macros (11 components)
**Criteria:** Small, reusable, parameter-driven

1. ✅ `reference-header.html` → `reference_header()` (DONE)
2. ✅ `reference-metadata.html` → `reference_metadata()` (DONE)
3. `article-card.html` → `article_card()`
4. `breadcrumbs.html` → `breadcrumbs()`
5. `child-page-tiles.html` → `child_page_tiles()`
6. `page-navigation.html` → `page_navigation()`
7. `pagination.html` → `pagination()`
8. `popular-tags.html` → `popular_tags()`
9. `random-posts.html` → `random_posts()`
10. `section-navigation.html` → `section_navigation()`
11. `tag-list.html` → `tag_list()`
12. `toc-sidebar.html` → `toc()`

### Keep as Includes (5 components)
**Criteria:** Large, complex, deeply context-dependent

1. `docs-nav.html` - Recursive navigation tree, ~100+ lines
2. `docs-nav-section.html` - Helper for docs-nav.html
3. `docs-meta.html` - Complex metadata rendering
4. `search.html` - Search interface with state
5. _(Any new complex components)_

## Component File Organization

### Target Structure

```
partials/
├── reference-components.html    # Reference documentation
│   ├── reference_header()       ✅ EXISTS
│   ├── reference_metadata()     ✅ EXISTS
│   └── [future: api_signature(), cli_usage()]
│
├── navigation-components.html   # Navigation elements
│   ├── breadcrumbs()            ⏳ TODO
│   ├── pagination()             ⏳ TODO
│   ├── page_navigation()        ⏳ TODO
│   ├── section_navigation()     ⏳ TODO
│   └── toc()                    ⏳ TODO
│
├── content-components.html      # Content display
│   ├── article_card()           ⏳ TODO
│   ├── child_page_tiles()       ⏳ TODO
│   ├── tag_list()               ⏳ TODO
│   ├── popular_tags()           ⏳ TODO
│   └── random_posts()           ⏳ TODO
│
├── ui-components.html           # Future UI elements
│   ├── button()                 💭 FUTURE
│   ├── badge()                  💭 FUTURE
│   ├── alert()                  💭 FUTURE
│   └── card()                   💭 FUTURE
│
└── layout-components.html       # Future layout helpers
    ├── grid()                   💭 FUTURE
    ├── sidebar()                💭 FUTURE
    └── container()              💭 FUTURE
```

## Implementation Plan

### Phase 1: Navigation Components ⏳

**File:** `partials/navigation-components.html`

**Priority: HIGH** - Used everywhere

#### 1. `breadcrumbs(items=None, separator='/')`
Convert `partials/breadcrumbs.html`

**Current usage pattern:**
```jinja2
{% include 'partials/breadcrumbs.html' %}
```

**New pattern:**
```jinja2
{% from 'partials/navigation-components.html' import breadcrumbs %}
{{ breadcrumbs() }}  {# Auto-generates from page context #}
```

**Used in:** All section templates

#### 2. `pagination(current, total, base_url, show_numbers=True)`
Convert `partials/pagination.html`

**Current usage:**
```jinja2
{% include 'partials/pagination.html' %}
```

**New pattern:**
```jinja2
{% from 'partials/navigation-components.html' import pagination %}
{{ pagination(
  current=pagination.current_page,
  total=pagination.total_pages,
  base_url=pagination.base_url
) }}
```

**Used in:** `blog/list.html`, `archive.html`

#### 3. `page_navigation(prev=None, next=None)`
Convert `partials/page-navigation.html`

**Used in:** `blog/single.html`, `doc/single.html`

#### 4. `section_navigation()`
Convert `partials/section-navigation.html`

**Used in:** Various section pages

#### 5. `toc(headings, max_depth=3, title='On This Page')`
Convert `partials/toc-sidebar.html`

**Used in:** `doc/single.html`, long articles

### Phase 2: Content Components ⏳

**File:** `partials/content-components.html`

**Priority: MEDIUM** - Blog and content display

#### 1. `article_card(post, show_excerpt=True, show_image=True)`
Convert `partials/article-card.html`

**Current usage:**
```jinja2
{% for post in posts %}
  {% set post = post %}
  {% include 'partials/article-card.html' %}
{% endfor %}
```

**New pattern:**
```jinja2
{% from 'partials/content-components.html' import article_card %}
{% for post in posts %}
  {{ article_card(post, show_excerpt=True) }}
{% endfor %}
```

**Used in:** `blog/list.html`, `index.html`, `home.html`

#### 2. `child_page_tiles(pages=None, columns=3)`
Convert `partials/child-page-tiles.html`

**Used in:** Section index pages

#### 3. `tag_list(tags, show_count=True)`
Convert `partials/tag-list.html`

**Used in:** `blog/single.html`, `post.html`

#### 4. `popular_tags(limit=20)`
Convert `partials/popular-tags.html`

**Used in:** Sidebar widgets

#### 5. `random_posts(limit=5)`
Convert `partials/random-posts.html`

**Used in:** Sidebar widgets

### Phase 3: Update Templates ⏳

**Priority: HIGH** - Make templates use new macros

Update all section templates to import and use macros:

#### Core Templates (6 files)
1. ✅ `api-reference/single.html` (DONE)
2. ✅ `cli-reference/single.html` (DONE)
3. `blog/single.html`
4. `blog/list.html`
5. `doc/single.html`
6. `doc/list.html`

#### Secondary Templates (10 files)
7. `tutorial/single.html`
8. `tutorial/list.html`
9. `api-reference/list.html`
10. `cli-reference/list.html`
11. `post.html`
12. `page.html`
13. `index.html`
14. `home.html`
15. `archive.html`
16. `tags.html`

### Phase 4: Deprecation ⏳

**Priority: LOW** - Mark old includes as deprecated

1. Add deprecation warnings to old include files
2. Update theme documentation
3. Create migration guide
4. Set removal target: Bengal 1.0

### Phase 5: Future Components 💭

**Priority: LOW** - New components as needed

Create `partials/ui-components.html`:
- `button(text, url, type, size)`
- `badge(text, color)`
- `alert(message, type)`
- `callout(content, type, title)`

Create `partials/layout-components.html`:
- `grid(items, columns)`
- `sidebar(content, position)`
- `card(title, content, footer)`

## Migration Checklist

### ✅ Completed
- [x] Created `partials/components.html` (now `reference-components.html`)
- [x] Migrated `reference_header()` macro
- [x] Migrated `reference_metadata()` macro
- [x] Updated `api-reference/single.html`
- [x] Updated `cli-reference/single.html`
- [x] Added `StrictUndefined` in strict mode

### ⏳ In Progress
- [ ] Rename `partials/components.html` → `partials/reference-components.html`
- [ ] Create `partials/navigation-components.html`
- [ ] Create `partials/content-components.html`

### 📋 To Do

**Week 1: Navigation Components**
- [ ] Convert `breadcrumbs.html` to macro
- [ ] Convert `pagination.html` to macro
- [ ] Convert `page-navigation.html` to macro
- [ ] Convert `section-navigation.html` to macro
- [ ] Convert `toc-sidebar.html` to macro

**Week 2: Content Components**
- [ ] Convert `article-card.html` to macro
- [ ] Convert `child-page-tiles.html` to macro
- [ ] Convert `tag-list.html` to macro
- [ ] Convert `popular-tags.html` to macro
- [ ] Convert `random-posts.html` to macro

**Week 3: Template Updates**
- [ ] Update `blog/single.html`
- [ ] Update `blog/list.html`
- [ ] Update `doc/single.html`
- [ ] Update `doc/list.html`
- [ ] Update remaining templates

**Week 4: Documentation & Cleanup**
- [ ] Create `COMPONENTS.md` documentation
- [ ] Add deprecation warnings to old includes
- [ ] Create migration guide for theme developers
- [ ] Test with showcase example site

## Testing Strategy

### Manual Testing
```bash
cd examples/showcase
bengal build --strict-mode
bengal serve
```

Check:
- [ ] All pages render correctly
- [ ] No undefined variable errors
- [ ] Icons and headers display properly
- [ ] Navigation works (breadcrumbs, pagination)
- [ ] Cards display in lists
- [ ] TOC appears on long pages

### Regression Testing
Create test to ensure macros produce same HTML as includes:

```python
def test_reference_header_macro_matches_include():
    # Render with old include
    old_html = render_include('reference-header.html', {...})

    # Render with new macro
    new_html = render_macro('reference_header', {...})

    # Should produce same output
    assert normalize_html(old_html) == normalize_html(new_html)
```

## Success Metrics

### Code Quality
- [ ] Template files < 150 lines each
- [ ] Macro files organized by domain
- [ ] No duplicate HTML between includes and macros

### Developer Experience
- [ ] Clear component documentation
- [ ] Easy to find relevant macros
- [ ] Obvious which pattern to use (macros vs includes)
- [ ] Better error messages with StrictUndefined

### Performance
- [ ] Build time unchanged or faster
- [ ] Template cache effectiveness maintained
- [ ] No scope pollution overhead

## Files to Create

```
partials/
├── reference-components.html       # Rename from components.html
├── navigation-components.html      # NEW
├── content-components.html         # NEW
├── ui-components.html              # FUTURE
└── layout-components.html          # FUTURE

docs/
├── COMPONENTS.md                   # NEW - Component documentation
└── MIGRATION_GUIDE.md              # NEW - For theme developers
```

## Next Steps

1. **Immediate:** Rename `components.html` → `reference-components.html`
2. **This Week:** Create `navigation-components.html` with 5 macros
3. **Next Week:** Create `content-components.html` with 5 macros
4. **Week 3:** Update all templates to use new macros
5. **Week 4:** Documentation and cleanup

## Decision Summary

**Architecture:** Domain-grouped component files in `partials/`
- `partials/{domain}-components.html` for macros
- Keep complex includes during migration
- Deprecate old includes gradually
- Complete migration for Bengal 1.0

**No new directory layer** - everything stays in `partials/`, just organized by clear naming convention.

This gives theme developers:
✅ Clear organization
✅ Easy discovery
✅ Gradual migration
✅ Backwards compatibility
✅ Long-term maintainability
