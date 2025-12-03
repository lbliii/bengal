# RFC: Cards Directive Enhancements

**Status**: Draft  
**Created**: 2025-12-03  
**Author**: AI Assistant  
**Location**: `bengal/rendering/plugins/directives/cards.py`

---

## Executive Summary

Enhance the existing `{cards}` directive with two high-value features:

1. **`:pull:` option** — Auto-fetch metadata from linked pages (title, description, etc.)
2. **`:layout:` option** — Support horizontal and portrait card layouts

Both features leverage existing infrastructure (xref_index, CSS classes) and provide broad utility across documentation patterns.

---

## Problem Statement

### Problem 1: Content Duplication

When creating cards that link to other pages, authors duplicate content:

```markdown
<!-- In cards grid -->
:::{card} Writer Quickstart
:link: ./writer-quickstart/

Get started writing content with Bengal in under 5 minutes.
:::
```

```yaml
# In ./writer-quickstart/_index.md frontmatter
---
title: "Writer Quickstart"
description: "Get started writing content with Bengal in under 5 minutes"
---
```

**Issue**: Same text in two places. When one changes, the other becomes stale.

### Problem 2: Missing Layout Options

The CSS already supports `.card-horizontal` (line 358-377 in `cards.css`), but the directive doesn't expose it:

```python
# Current options in cards.py
style = options.get("style", "default")  # default, minimal, bordered
variant = options.get("variant", "navigation")  # navigation, info, concept
# No layout option!
```

**Issue**: Users can't create horizontal cards (image left, content right) or portrait cards (TCG/phone style) without custom CSS hacks.

---

## Proposed Solution

### Feature 1: `:pull:` Option

#### Syntax

```markdown
:::{card}
:link: ./writer-quickstart/
:pull: title, description
:::
```

#### Supported Fields

| Field | Source | Fallback |
|-------|--------|----------|
| `title` | `page.title` | Card title or link text |
| `description` | `page.metadata.description` | Card body content |
| `icon` | `page.metadata.icon` | None |
| `date` | `page.date` | None |
| `tags` | `page.tags` | None |
| `estimated_time` | `page.metadata.estimated_time` | None |
| `difficulty` | `page.metadata.difficulty` | None |

#### Lookup Strategies

Leverages existing `xref_index` with O(1) lookups:

```markdown
<!-- By path (relative to content/) -->
:link: docs/getting-started/writer-quickstart

<!-- By slug -->
:link: writer-quickstart

<!-- By custom ID (RST-style ref target) -->
:link: id:writer-qs
```

#### Fallback Behavior

```markdown
:::{card} Fallback Title
:link: ./maybe-missing/
:pull: title, description

This content shows if page not found or description missing.
:::
```

- If page found: pulled fields override card content
- If page missing: card renders with provided fallback content
- If specific field missing: that field falls back, others still pull

#### Examples

**Minimal (auto everything)**:
```markdown
:::{card}
:link: id:writer-qs
:pull: title, description
:::
```

**With overrides**:
```markdown
:::{card} Custom Title Here
:link: ./writer-quickstart/
:pull: description, estimated_time

<!-- title not pulled, uses "Custom Title Here" -->
:::
```

**Blog recent posts**:
```markdown
::::{cards}
:columns: 3

:::{card}
:link: /blog/performance-tips/
:pull: title, description, date
:::

:::{card}
:link: /blog/theme-customization/
:pull: title, description, date
:::
::::
```

---

### Feature 2: `:layout:` Option

#### Syntax

```markdown
::::{cards}
:columns: 3
:layout: portrait

:::{card} Title
:image: /images/hero.png
:::
::::
```

#### Layout Values

| Layout | Description | Use Case |
|--------|-------------|----------|
| `default` | Vertical, content stacked | General purpose |
| `horizontal` | Image left, content right | Feature lists, team bios |
| `portrait` | Tall aspect ratio (2:3) | TCG-style, app screenshots |
| `compact` | Minimal padding, dense | Reference lists |

#### CSS Implementation

```css
/* Default - already exists */
.card {
  flex-direction: column;
}

/* Horizontal - CSS exists, needs directive support */
.card-layout-horizontal {
  flex-direction: row;
}

.card-layout-horizontal .card-image {
  width: 200px;
  height: auto;
  flex-shrink: 0;
}

/* Portrait - new */
.card-layout-portrait {
  aspect-ratio: 2 / 3;
  max-width: 280px;
}

.card-layout-portrait .card-image {
  aspect-ratio: 3 / 2;
  height: auto;
}

/* Compact - new */
.card-layout-compact .card-header,
.card-layout-compact .card-content {
  padding: var(--space-3);
}

.card-layout-compact .card-title {
  font-size: var(--text-sm);
}
```

#### Applied At Grid or Card Level

```markdown
<!-- Grid-level: all cards get layout -->
::::{cards}
:layout: horizontal

:::{card} ... :::
:::{card} ... :::
::::

<!-- Card-level: individual override -->
::::{cards}
:::{card} Normal Card
:::

:::{card} Horizontal Card
:layout: horizontal
:::
::::
```

---

## Implementation Plan

### Phase 1: `:pull:` Option (Priority)

**Effort**: 1-2 days

1. **Modify `CardDirective.parse()`** to extract `:pull:` option
2. **Add `_resolve_linked_page()`** helper using xref_index
3. **Modify `render_card()`** to merge pulled fields with provided attrs
4. **Handle fallbacks** gracefully (missing page, missing fields)
5. **Add tests** for pull scenarios

#### Code Changes

```python
# cards.py - CardDirective.parse()
def parse(self, block, m, state):
    # ... existing code ...
    
    # NEW: Parse pull option
    pull_str = options.get("pull", "")
    pull_fields = [f.strip() for f in pull_str.split(",") if f.strip()]
    
    return {
        "type": "card",
        "attrs": {
            "title": title,
            "link": link,
            "pull": pull_fields,  # NEW
            # ... rest
        },
        "children": children,
    }
```

```python
# cards.py - render_card()
def render_card(renderer, text, **attrs):
    link = attrs.get("link", "")
    pull_fields = attrs.get("pull", [])
    
    # NEW: Resolve linked page and pull fields
    if link and pull_fields:
        pulled = _pull_from_linked_page(renderer, link, pull_fields)
        # Merge: pulled values fill in missing attrs
        if "title" in pull_fields and not attrs.get("title"):
            attrs["title"] = pulled.get("title", "")
        if "description" in pull_fields and not text:
            text = pulled.get("description", "")
        # ... etc
    
    # ... rest of existing render code
```

```python
# cards.py - new helper
def _pull_from_linked_page(renderer, link: str, fields: list[str]) -> dict:
    """Pull metadata from linked page via xref_index."""
    xref_index = getattr(renderer, "_xref_index", None)
    if not xref_index:
        return {}
    
    # Resolve page using existing strategies
    page = None
    if link.startswith("id:"):
        page = xref_index.get("by_id", {}).get(link[3:])
    elif "/" in link or link.endswith(".md"):
        clean = link.replace(".md", "").strip("/")
        page = xref_index.get("by_path", {}).get(clean)
    else:
        pages = xref_index.get("by_slug", {}).get(link, [])
        page = pages[0] if pages else None
    
    if not page:
        return {}
    
    # Extract requested fields
    result = {}
    for field in fields:
        if field == "title":
            result["title"] = getattr(page, "title", "")
        elif field == "description":
            result["description"] = page.metadata.get("description", "")
        elif field == "date":
            result["date"] = getattr(page, "date", None)
        elif field == "tags":
            result["tags"] = getattr(page, "tags", [])
        elif field == "icon":
            result["icon"] = page.metadata.get("icon", "")
        elif field == "estimated_time":
            result["estimated_time"] = page.metadata.get("estimated_time", "")
        elif field == "difficulty":
            result["difficulty"] = page.metadata.get("difficulty", "")
    
    return result
```

### Phase 2: `:layout:` Option

**Effort**: 0.5-1 day

1. **Add `:layout:` option** to `CardsDirective` (grid-level)
2. **Add `:layout:` option** to `CardDirective` (card-level)
3. **Modify renderers** to output layout class
4. **Add CSS** for portrait and compact layouts
5. **Add tests**

#### Code Changes

```python
# cards.py - CardsDirective.parse()
def parse(self, block, m, state):
    # ... existing code ...
    
    # NEW: Layout option
    layout = options.get("layout", "default")
    if layout not in ("default", "horizontal", "portrait", "compact"):
        layout = "default"
    
    return {
        "type": "cards_grid",
        "attrs": {
            "columns": ...,
            "gap": ...,
            "style": ...,
            "variant": ...,
            "layout": layout,  # NEW
        },
        "children": children,
    }
```

```python
# cards.py - render_cards_grid()
def render_cards_grid(renderer, text, **attrs):
    layout = attrs.get("layout", "default")
    
    html = (
        f'<div class="card-grid" '
        f'data-columns="{columns}" '
        f'data-gap="{gap}" '
        f'data-style="{style}" '
        f'data-variant="{variant}" '
        f'data-layout="{layout}">\n'  # NEW
        f"{text}"
        f"</div>\n"
    )
    return html
```

```css
/* cards.css - new layouts */

/* Horizontal layout */
.card-grid[data-layout="horizontal"] .card,
.card.card-layout-horizontal {
  flex-direction: row;
}

.card-grid[data-layout="horizontal"] .card-image,
.card.card-layout-horizontal .card-image {
  width: 200px;
  height: auto;
  aspect-ratio: 1;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .card-grid[data-layout="horizontal"] .card,
  .card.card-layout-horizontal {
    flex-direction: column;
  }
  
  .card-grid[data-layout="horizontal"] .card-image,
  .card.card-layout-horizontal .card-image {
    width: 100%;
    aspect-ratio: 16 / 9;
  }
}

/* Portrait layout (TCG/phone style) */
.card-grid[data-layout="portrait"] .card,
.card.card-layout-portrait {
  aspect-ratio: 2 / 3;
  max-width: 280px;
  margin: 0 auto;
}

.card-grid[data-layout="portrait"] .card-image,
.card.card-layout-portrait .card-image {
  aspect-ratio: 4 / 3;
  flex-shrink: 0;
}

/* Compact layout */
.card-grid[data-layout="compact"] .card,
.card.card-layout-compact {
  /* Tighter spacing */
}

.card-grid[data-layout="compact"] .card-header,
.card-grid[data-layout="compact"] .card-content,
.card.card-layout-compact .card-header,
.card.card-layout-compact .card-content {
  padding: var(--space-3);
}

.card-grid[data-layout="compact"] .card-title,
.card.card-layout-compact .card-title {
  font-size: var(--text-sm);
}

.card-grid[data-layout="compact"] .card-content p,
.card.card-layout-compact .card-content p {
  font-size: var(--text-xs);
}
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/rendering/test_cards_directive.py

def test_card_pull_title_from_linked_page(site_with_pages, markdown_parser):
    """Card pulls title from linked page."""
    md = """
    :::{card}
    :link: docs/quickstart
    :pull: title
    :::
    """
    html = markdown_parser(md)
    assert "Quickstart Guide" in html  # Title from page frontmatter


def test_card_pull_fallback_when_page_missing(markdown_parser):
    """Card falls back to provided content when page not found."""
    md = """
    :::{card} Fallback Title
    :link: docs/nonexistent
    :pull: title
    
    Fallback description.
    :::
    """
    html = markdown_parser(md)
    assert "Fallback Title" in html
    assert "Fallback description" in html


def test_card_pull_by_id(site_with_pages, markdown_parser):
    """Card pulls via id: reference target."""
    md = """
    :::{card}
    :link: id:quickstart
    :pull: title, description
    :::
    """
    html = markdown_parser(md)
    assert "Quickstart Guide" in html


def test_cards_layout_horizontal(markdown_parser):
    """Cards grid applies horizontal layout."""
    md = """
    ::::{cards}
    :layout: horizontal
    
    :::{card} Test
    :::
    ::::
    """
    html = markdown_parser(md)
    assert 'data-layout="horizontal"' in html


def test_card_layout_override(markdown_parser):
    """Individual card can override grid layout."""
    md = """
    ::::{cards}
    :layout: default
    
    :::{card} Normal
    :::
    
    :::{card} Horizontal
    :layout: horizontal
    :::
    ::::
    """
    html = markdown_parser(md)
    assert 'card-layout-horizontal' in html
```

### Integration Tests

```python
# tests/integration/test_cards_pull.py

def test_cards_pull_in_full_site_build(test_site):
    """Cards with :pull: resolve correctly in full build."""
    test_site.build()
    
    output = test_site.read_output("docs/getting-started/index.html")
    # Cards should have pulled titles from linked pages
    assert "Writer Quickstart" in output
    assert "Themer Quickstart" in output
```

---

## Migration Path

### Backward Compatibility

Both features are **additive** — existing cards work unchanged:

- Cards without `:pull:` render as before
- Cards without `:layout:` use default layout
- No breaking changes to existing syntax

### Documentation Updates

1. Update `site/content/docs/reference/directives/cards.md` with new options
2. Add examples for `:pull:` and `:layout:` usage
3. Document supported pull fields and layout values

---

## Alternatives Considered

### Alternative 1: New `{wayfinding}` Directive

**Rejected**: Low usage frequency (1-2 pages), cards already handle this pattern. Better to enhance cards than create a new directive.

### Alternative 2: Template-Only Solution

```jinja
{% set page = doc('docs/quickstart') %}
{% if page %}
  <div class="card">{{ page.title }}</div>
{% endif %}
```

**Rejected**: Not usable in markdown content. Cards directive is the right abstraction level.

### Alternative 3: Pull All Fields Automatically

```markdown
:::{card}
:link: ./quickstart/
:pull: auto  <!-- Pull everything available -->
:::
```

**Rejected**: Too magical, unclear what gets pulled. Explicit field list is safer.

---

## Success Criteria

- [ ] `:pull:` option fetches metadata from linked pages
- [ ] `:pull:` falls back gracefully when page/field missing
- [ ] `:pull:` works with path, slug, and id: references
- [ ] `:layout:` supports horizontal, portrait, compact
- [ ] `:layout:` works at grid and card level
- [ ] Responsive behavior for all layouts
- [ ] All tests pass
- [ ] Documentation updated

---

## Open Questions

1. **Should `:pull:` work without `:link:`?**
   - Current design: No, requires link to know which page
   - Alternative: Could pull from "current" page context

2. **Should we support `:pull: all`?**
   - Pro: Convenient for "just give me everything"
   - Con: Unclear what "all" means, harder to maintain

3. **Portrait card max-width: 280px or configurable?**
   - Could add `:width:` option but adds complexity

4. **Grid-level vs card-level layout precedence?**
   - Current design: Card-level overrides grid-level
   - Seems intuitive, needs documentation

---

## References

- [Cards Directive](bengal/rendering/plugins/directives/cards.py) — Current implementation
- [Cards CSS](bengal/themes/default/assets/css/components/cards.css) — Existing styles
- [Cross-Reference Plugin](bengal/rendering/plugins/cross_references.py) — xref_index usage
- [Template Functions](bengal/rendering/template_functions/crossref.py) — `doc()` function pattern

---

## Appendix: Full Syntax Reference

### Cards Container

```markdown
::::{cards}
:columns: 3              # 1-6, auto, or 1-2-3-4 (responsive)
:gap: medium             # small, medium, large
:style: default          # default, minimal, bordered
:variant: navigation     # navigation, info, concept
:layout: default         # default, horizontal, portrait, compact (NEW)

[card directives...]
::::
```

### Individual Card

```markdown
:::{card} Optional Title
:link: path/or/id:ref    # Link target
:pull: title, description # Fields to pull from linked page (NEW)
:layout: horizontal      # Override grid layout (NEW)
:icon: book              # Icon name
:color: blue             # Accent color
:image: /path/to/img.png # Header image
:footer: Footer text     # Footer content

Optional body content (markdown supported).
:::
```


