# Research: Premium Icons in Site TOC Sidebar

**Status**: Research  
**Author**: AI Assistant  
**Created**: 2025-12-06  
**Related**: rfc-template-component-props.md

---

## Executive Summary

This research explores options for adding icons to the site TOC (left sidebar navigation) in a premium, app-like manner. The challenge includes supporting both:
1. **Section icons** - visible alongside directory items
2. **Page icons** - visible alongside individual pages
3. **Dropdown visualization** - icons must coexist with the expand/collapse caret

---

## Current State

### Navigation Structure (`docs-nav-section.html`)

```html
<!-- Current structure for expandable sections -->
<div class="docs-nav-group">
  <div class="docs-nav-group-toggle-wrapper">
    <button class="docs-nav-group-toggle">
      {{ icon('caret-right', size=16) }}  <!-- Expand/collapse caret -->
    </button>
    <a href="..." class="docs-nav-group-link">
      {{ section_title }}  <!-- Just text, no icon -->
    </a>
  </div>
  <div class="docs-nav-group-items">...</div>
</div>

<!-- Current structure for leaf pages -->
<a href="..." class="docs-nav-link">
  {{ page.title }}  <!-- Just text, no icon -->
</a>
```

### Icon Data Sources

Icons can be defined in frontmatter:

```yaml
# In _index.md or individual page.md
---
title: API Reference
icon: book  # Phosphor icon name
---
```

Access patterns:
- **Section icon**: `section.index_page.metadata.get('icon')` or `section.metadata.get('icon')`
- **Page icon**: `page.metadata.get('icon')`

### Available Icon Library

Bengal ships with 80+ Phosphor icons in `themes/default/assets/icons/`:
- Navigation: `arrow-*`, `caret-*`, `chevron-*`
- Content: `book`, `file-text`, `folder`, `code`
- Actions: `settings`, `search`, `download`
- UI: `layers`, `compass`, `rocket`, `zap`

---

## Design Options

### Option A: Icon + Text Layout (Linear/Notion Style)

**Visual**:
```
[▶] [📖] API Reference
     [📄] Getting Started
     [📄] Authentication
[▶] [⚙️] Configuration
     [📄] Basic Setup
```

**Implementation**:
```html
<div class="docs-nav-group-toggle-wrapper">
  <button class="docs-nav-group-toggle">
    {{ icon('caret-right', size=16) }}
  </button>
  {% if section.index_page.metadata.get('icon') %}
  <span class="docs-nav-icon">
    {{ icon(section.index_page.metadata.get('icon'), size=16) }}
  </span>
  {% endif %}
  <a href="..." class="docs-nav-group-link">{{ section_title }}</a>
</div>
```

**CSS**:
```css
.docs-nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  color: var(--color-text-tertiary);
}

.docs-nav-group-link:hover .docs-nav-icon,
.docs-nav-group-toggle-wrapper:hover .docs-nav-icon {
  color: var(--color-primary);
}
```

**Pros**:
- Clear visual hierarchy
- Icon complements caret without replacing it
- Familiar pattern (VS Code, Notion, Linear)

**Cons**:
- Takes more horizontal space
- May crowd narrow sidebars

---

### Option B: Icon-Only with Hover Expansion (macOS Sidebar Style)

**Visual (Collapsed)**:
```
[📖] API...
[⚙️] Conf...
```

**Visual (Hover)**:
```
[▶] [📖] API Reference
```

**Implementation**: CSS-only with hover state

```css
.docs-nav-group-toggle {
  opacity: 0;
  width: 0;
  transition: all 0.2s ease;
}

.docs-nav-group-toggle-wrapper:hover .docs-nav-group-toggle {
  opacity: 1;
  width: 30px;
}

.docs-nav-icon {
  opacity: 1;
  transition: opacity 0.2s ease;
}

.docs-nav-group-toggle-wrapper:hover .docs-nav-icon {
  opacity: 0;
  width: 0;
}
```

**Pros**:
- Very clean, minimal
- More space for text
- Modern/premium feel

**Cons**:
- Hidden affordance (caret not visible until hover)
- Accessibility concerns
- May confuse users expecting to click icon to expand

---

### Option C: Badge-Style Icons (GitHub/GitLab Style)

**Visual**:
```
[▶] API Reference      [📖]
     Getting Started   [📄]
     Authentication    [🔐]
```

**Implementation**: Right-aligned icon badges

```html
<a href="..." class="docs-nav-group-link">
  <span class="docs-nav-link-text">{{ section_title }}</span>
  {% if icon_name %}
  <span class="docs-nav-badge">{{ icon(icon_name, size=14) }}</span>
  {% endif %}
</a>
```

**CSS**:
```css
.docs-nav-group-link {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.docs-nav-badge {
  opacity: 0.5;
  transition: opacity 0.2s;
}

.docs-nav-group-link:hover .docs-nav-badge {
  opacity: 1;
}
```

**Pros**:
- Clean, doesn't interfere with caret
- Good for status indicators
- Works well at any sidebar width

**Cons**:
- Icons may feel like secondary info
- Right alignment can look odd

---

### Option D: Caret Replacement on Hover (Elegant Transition)

**Visual (Default)**:
```
[📖] API Reference
[⚙️] Configuration
```

**Visual (Hover)**:
```
[▶] API Reference
```

**Implementation**: Icon morphs into caret on hover

```css
.docs-nav-icon-container {
  position: relative;
  width: 24px;
  height: 24px;
}

.docs-nav-icon,
.docs-nav-caret {
  position: absolute;
  transition: all 0.2s ease;
}

.docs-nav-icon {
  opacity: 1;
  transform: scale(1);
}

.docs-nav-caret {
  opacity: 0;
  transform: scale(0.8);
}

.docs-nav-group-toggle-wrapper:hover .docs-nav-icon {
  opacity: 0;
  transform: scale(0.8);
}

.docs-nav-group-toggle-wrapper:hover .docs-nav-caret {
  opacity: 1;
  transform: scale(1);
}
```

**Pros**:
- Maximally clean - one icon per row
- Elegant transition
- Premium feel
- Accessible (caret appears on hover)

**Cons**:
- More complex implementation
- Animation might be distracting
- Non-hoverable on touch devices (needs fallback)

---

### Option E: Indented Icons with Visual Hierarchy (VS Code Style)

**Visual**:
```
📂 API Reference
   📄 Getting Started
   📄 Authentication
   📂 Endpoints
      📄 Users
      📄 Items
```

**Implementation**: Replace caret entirely, use folder/file icons

```html
<div class="docs-nav-group">
  <button class="docs-nav-item">
    {{ icon('folder', size=16) if section.has_children else icon('file', size=16) }}
    <span>{{ title }}</span>
    {% if section.has_children %}
    <span class="docs-nav-chevron">{{ icon('chevron-right', size=12) }}</span>
    {% endif %}
  </button>
</div>
```

**CSS**:
```css
.docs-nav-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.5rem;
  padding-left: calc(var(--depth) * 1rem + 0.5rem);
}

.docs-nav-chevron {
  margin-left: auto;
  transition: transform 0.2s ease;
}

.docs-nav-item[aria-expanded="true"] .docs-nav-chevron {
  transform: rotate(90deg);
}
```

**Pros**:
- Familiar file explorer metaphor
- Very clear hierarchy
- Works with any depth

**Cons**:
- Loses custom section icons
- May feel less "unique"

---

## Recommended Approach: Hybrid (Option A + D)

**Rationale**: Combine the best of both worlds

1. **Default state**: Show content icon before text (Option A layout)
2. **Collapsed sections**: Show caret (rotates on expand)
3. **Premium touch**: Subtle glow on active icon

**Visual**:
```
[▶] [📖] API Reference        <- Caret + Icon + Text
      [📄] Getting Started    <- Indent + Icon + Text
      [🔐] Authentication
[▸] [⚙️] Configuration        <- Collapsed
```

**Implementation Sketch**:

```html
<div class="docs-nav-group-toggle-wrapper">
  <!-- Expand/collapse caret (for sections with children) -->
  {% if section.has_nav_children %}
  <button class="docs-nav-group-toggle" aria-expanded="false">
    {{ icon('caret-right', size=14) }}
  </button>
  {% endif %}

  <!-- Content icon (from frontmatter) -->
  {% set section_icon = section.index_page.metadata.get('icon') if section.index_page else none %}
  <span class="docs-nav-icon" {% if not section_icon %}data-default="true"{% endif %}>
    {{ icon(section_icon or 'folder', size=16) }}
  </span>

  <!-- Section title -->
  <a href="..." class="docs-nav-group-link">{{ section_title }}</a>
</div>
```

**CSS Additions**:

```css
/* Icon styling */
.docs-nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  min-width: 20px;
  height: 20px;
  color: var(--color-text-tertiary);
  transition: color var(--transition-fast), transform var(--transition-fast);
}

/* Default folder icon gets muted styling */
.docs-nav-icon[data-default="true"] {
  opacity: 0.6;
}

/* Icon color on hover */
.docs-nav-group-toggle-wrapper:hover .docs-nav-icon {
  color: var(--color-primary);
}

/* Active section icon gets glow */
.docs-nav-group:has(.docs-nav-link.active) .docs-nav-icon,
.docs-nav-group-toggle-wrapper:has(.docs-nav-group-link.active) .docs-nav-icon {
  color: var(--color-primary);
  filter: drop-shadow(0 0 4px color-mix(in srgb, var(--color-primary) 30%, transparent));
}

/* Page icons (within sections) */
.docs-nav-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.docs-nav-link .docs-nav-icon {
  width: 16px;
  min-width: 16px;
  height: 16px;
}
```

---

## Props Integration

Per the RFC, the sidebar component should accept props:

```jinja2
{% macro sidebar_nav(
    show_icons=true,
    icon_size=16,
    icon_style='inline',  # 'inline', 'badge', 'hover-reveal'
    default_icon='folder',
    show_page_icons=true,
    default_page_icon='file-text',
    collapsible=true,
    max_depth=none
) %}
```

**Usage**:
```jinja2
{{ sidebar_nav(show_icons=true, icon_style='inline') }}
{{ sidebar_nav(show_icons=false) }}  {# Disable icons #}
{{ sidebar_nav(icon_style='badge') }}  {# Right-aligned badges #}
```

---

## Data Model Considerations

### Section Icon Access

Currently: `section.index_page.metadata.get('icon')`

**Proposed enhancement**: Add `section.icon` property

```python
# In bengal/core/section.py
@property
def icon(self) -> str | None:
    """Get section icon from index page metadata."""
    if self.index_page and self.index_page.metadata:
        return self.index_page.metadata.get('icon')
    return self.metadata.get('icon')
```

### Fallback Icons by Content Type

Consider automatic icon assignment based on `type`:

```python
TYPE_ICONS = {
    'api-reference': 'book',
    'cli-reference': 'terminal',
    'tutorial': 'graduation-cap',
    'guide': 'compass',
    'doc': 'file-text',
}
```

---

## Accessibility Considerations

1. **Icons must not be the only indicator** - Text labels required
2. **Aria-hidden on decorative icons** - Already handled by `icon()` function
3. **Hover states need keyboard equivalent** - Focus states should match
4. **Touch devices** - Caret must be tappable, not just on hover

---

## Performance Considerations

1. **SVG inlining** - Current approach (good for caching)
2. **Icon sprite alternative** - Consider for very large nav trees (>100 items)
3. **Lazy rendering** - Current CSS `content-visibility: auto` helps

---

## Next Steps

1. **Prototype Option A** (inline icons) in current templates
2. **Add `section.icon` property** to Section class
3. **Update RFC** with `sidebar_nav` component props
4. **Implement CSS** for icon styling and transitions
5. **Add `show_icons` prop** to component macro
6. **Test with various icon densities**

---

## Appendix: Reference Implementations

### Linear
- Inline icons, 16px, subtle colors
- No folder icons - all items have content icons
- Caret on right side (chevron style)

### Notion
- Emoji-based icons (user customizable)
- 18px size, inline before text
- Caret replaced by toggle triangle

### VS Code
- File tree metaphor
- Folder/file icons based on type
- Chevron on left for expand/collapse
- File type icons determined by extension

### GitBook
- Minimal - no icons by default
- Section headers have optional icons
- Clean, text-focused

### Docusaurus
- Category icons supported
- Uses emojis or custom icons
- Caret + icon layout

---

## Decision Matrix

| Criterion                  | A (Inline) | B (Hover) | C (Badge) | D (Morph) | E (VS Code) |
|---------------------------|------------|-----------|-----------|-----------|-------------|
| Visual clarity            | ★★★★☆     | ★★★☆☆    | ★★★☆☆    | ★★★★☆    | ★★★★★      |
| Premium feel              | ★★★★☆     | ★★★★★    | ★★★☆☆    | ★★★★★    | ★★★☆☆      |
| Implementation complexity | ★★☆☆☆     | ★★★☆☆    | ★★☆☆☆    | ★★★★☆    | ★★★☆☆      |
| Accessibility             | ★★★★★     | ★★☆☆☆    | ★★★★☆    | ★★★☆☆    | ★★★★★      |
| Touch-friendly            | ★★★★★     | ★★☆☆☆    | ★★★★☆    | ★★☆☆☆    | ★★★★★      |
| Space efficiency          | ★★★☆☆     | ★★★★★    | ★★★★☆    | ★★★★★    | ★★★☆☆      |

**Recommendation**: Start with **Option A (Inline)** for Phase 1, with CSS hooks to easily switch to **Option D (Morph)** for a future premium enhancement.
