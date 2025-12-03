# RFC: Wayfinding Directive

**Status**: Draft  
**Created**: 2025-12-03  
**Author**: AI Assistant  
**Related**: `bengal/rendering/plugins/directives/`

---

## Executive Summary

Create a dedicated `{wayfinding}` directive for presenting divergent learning paths, role-based navigation, and "choose your adventure" documentation patterns. Unlike raw tables, this directive provides:

1. **Purpose-built UX** with visual differentiation (icons, colors, progress indicators)
2. **Auto-metadata** pulled from linked pages (title, description, tags)
3. **Semantic markup** that expresses intent ("these are divergent paths")
4. **Reduced maintenance** by dereferencing linked content

---

## Problem Statement

### Current Approach

The existing Getting Started page uses a `list-table` directive:

```markdown
::::{list-table}
:header-rows: 1
:widths: 33 33 34

* - 📝 **Writer Path**
  - 🎨 **Themer Path**
  - 🛠️ **Contributor Path**
* - **Create content, write posts, build a site**
  - **Design and customize site appearance**
  - **Contribute to Bengal itself**
* - Perfect if you want to:
    - Start a blog or documentation site
    - Focus on writing, not code
    - Use templates and themes as-is
  - Perfect if you want to:
    - Create custom themes
    - Override templates and styles
    - Build branded experiences
  - Perfect if you want to:
    - Fix bugs or add features
    - Improve Bengal's core
    - Submit pull requests
* - **[→ Writer Quickstart](./writer-quickstart/)**
  - **[→ Themer Quickstart](./themer-quickstart/)**
  - **[→ Contributor Quickstart](./contributor-quickstart/)**
::::
```

### Problems

1. **Manual repetition**: Path descriptions are duplicated (also in each quickstart page's frontmatter)
2. **No visual hierarchy**: Table treats all info equally; paths don't visually "pop"
3. **Rigid layout**: Tables don't adapt well to mobile; fixed widths break
4. **No semantic meaning**: Just a table—search and navigation don't understand these are paths
5. **Missing context**: Can't show estimated time, difficulty, or prerequisites from linked pages

---

## Proposed Solution

### New `{wayfinding}` Directive

```markdown
::::{wayfinding}
:layout: cards  
:columns: 3

:::{path} Writer Path
:icon: pencil
:color: blue
:link: ./writer-quickstart/
:pull-description: true

Perfect for starting a blog or documentation site.
:::

:::{path} Themer Path
:icon: palette
:color: purple
:link: ./themer-quickstart/
:pull-description: true

Design custom themes and branded experiences.
:::

:::{path} Contributor Path
:icon: code
:color: green
:link: ./contributor-quickstart/
:pull-description: true

Fix bugs, add features, improve Bengal's core.
:::
::::
```

### Auto-Metadata from Linked Pages

When `:pull-description: true` (or `:pull: title,description,tags`), the directive fetches metadata from the linked page:

```yaml
# ./writer-quickstart/_index.md frontmatter
---
title: "Writer Quickstart"
description: "Get started writing content with Bengal in under 5 minutes"
estimated_time: "5 min"
difficulty: "beginner"
tags: ["quickstart", "writing", "content"]
---
```

The directive could display this info automatically:

```html
<div class="wayfinding-path" data-difficulty="beginner">
  <span class="path-time">⏱️ 5 min</span>
  <span class="path-difficulty">🟢 Beginner</span>
  ...
</div>
```

---

## Design Options

### Option A: Pull Specific Fields (Recommended)

```markdown
:::{path} Writer Path
:link: ./writer-quickstart/
:pull: description, estimated_time, difficulty

<!-- Content below is fallback if fields missing -->
Perfect for starting a blog or documentation site.
:::
```

**Pros**:
- Explicit about what gets pulled
- Fallback content if page missing
- Clear data flow

**Cons**:
- More verbose syntax

### Option B: Pull Everything (Auto-Magic)

```markdown
:::{path}
:link: ./writer-quickstart/
:::
<!-- No content needed—all pulled from linked page -->
```

**Pros**:
- Minimal syntax
- Single source of truth

**Cons**:
- Less control
- Breaks if linked page changes frontmatter

### Option C: Hybrid with Defaults

```markdown
:::{path} Writer Path
:link: ./writer-quickstart/
:auto: true  <!-- Pull what's available -->

Custom description (overrides if set)
:::
```

**Pros**:
- Best of both worlds
- Override when needed

**Recommendation**: **Option A** for explicit control, with **Option C** as a convenience flag.

---

## Implementation Plan

### Phase 1: Core Directive (MVP)

1. **Create `wayfinding.py`** in `bengal/rendering/plugins/directives/`
2. **Implement `WayfindingDirective`** (container) and **`PathDirective`** (item)
3. **Basic rendering** without auto-pull (static content only)
4. **CSS styling** in themes

### Phase 2: Auto-Metadata Pull

1. **Integrate with `xref_index`** for O(1) page lookup
2. **Implement `:pull:` option** to fetch frontmatter fields
3. **Add fallback behavior** for missing pages/fields
4. **Handle relative/absolute paths** correctly

### Phase 3: Enhanced UX

1. **Difficulty indicators** (beginner/intermediate/advanced)
2. **Estimated time** display
3. **Progress tracking** (if user state available)
4. **Responsive layouts** (horizontal → vertical on mobile)

---

## Technical Design

### Directive Structure

```python
# bengal/rendering/plugins/directives/wayfinding.py

class WayfindingDirective(DirectivePlugin):
    """Container for divergent path options."""
    
    def parse(self, block, m, state):
        options = dict(self.parse_options(m))
        content = self.parse_content(m)
        children = self.parse_tokens(block, content, state)
        
        return {
            "type": "wayfinding",
            "attrs": {
                "layout": options.get("layout", "cards"),
                "columns": options.get("columns", "auto"),
            },
            "children": children,
        }


class PathDirective(DirectivePlugin):
    """Individual path option within wayfinding."""
    
    def parse(self, block, m, state):
        title = self.parse_title(m)
        options = dict(self.parse_options(m))
        content = self.parse_content(m)
        children = self.parse_tokens(block, content, state)
        
        # Extract options
        link = options.get("link", "")
        pull_fields = self._parse_pull_option(options.get("pull", ""))
        
        return {
            "type": "wayfinding_path",
            "attrs": {
                "title": title,
                "link": link,
                "icon": options.get("icon", ""),
                "color": options.get("color", ""),
                "pull": pull_fields,
            },
            "children": children,
        }
```

### Metadata Resolution

```python
def render_wayfinding_path(renderer, text, **attrs):
    """Render path with optional auto-pulled metadata."""
    link = attrs.get("link", "")
    pull_fields = attrs.get("pull", [])
    
    # Get linked page metadata if pull requested
    pulled_meta = {}
    if link and pull_fields:
        # Access xref_index from renderer context
        xref_index = getattr(renderer, "_xref_index", {})
        page = resolve_page_link(link, xref_index)
        
        if page:
            for field in pull_fields:
                if field == "description":
                    pulled_meta["description"] = page.metadata.get("description", "")
                elif field == "estimated_time":
                    pulled_meta["time"] = page.metadata.get("estimated_time", "")
                # ... etc
    
    # Render with pulled or provided content
    return _render_path_html(attrs, pulled_meta, text)
```

---

## CSS/Theme Integration

### Required Theme CSS

```css
/* themes/default/css/components/wayfinding.css */

.wayfinding {
  display: grid;
  gap: var(--spacing-lg);
}

.wayfinding[data-columns="3"] {
  grid-template-columns: repeat(3, 1fr);
}

@media (max-width: 768px) {
  .wayfinding[data-columns="3"] {
    grid-template-columns: 1fr;
  }
}

.wayfinding-path {
  border: 2px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  transition: transform 0.2s, box-shadow 0.2s;
}

.wayfinding-path:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.wayfinding-path[data-color="blue"] {
  border-color: var(--color-blue);
}

/* Metadata badges */
.path-meta {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
}

.path-time, .path-difficulty {
  font-size: var(--font-sm);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--bg-muted);
}
```

---

## Example Usage

### Simple (No Auto-Pull)

```markdown
::::{wayfinding}
:columns: 2

:::{path} Quick Start
:icon: rocket
:link: ./quickstart/

Get up and running in 5 minutes.
:::

:::{path} Full Tutorial
:icon: book
:link: ./tutorial/

Complete walkthrough with examples.
:::
::::
```

### With Auto-Pull

```markdown
::::{wayfinding}
:columns: 3

:::{path} Writer
:link: ./writer-quickstart/
:pull: description, estimated_time
:icon: pencil
:color: blue
:::

:::{path} Themer  
:link: ./themer-quickstart/
:pull: description, estimated_time
:icon: palette
:color: purple
:::

:::{path} Contributor
:link: ./contributor-quickstart/
:pull: description, estimated_time
:icon: code
:color: green
:::
::::
```

### Directory-Based (Future Enhancement)

```markdown
::::{wayfinding}
:from: ./quickstarts/
:pull: title, description, icon, color
:sort: weight
::::
<!-- Auto-discovers all _index.md in subdirectories -->
```

---

## Alternatives Considered

### 1. Enhanced Cards Directive

Could extend existing `{cards}` with `:pull:` option. 

**Rejected**: Cards are for static content; wayfinding has distinct semantics (choice, paths, progression).

### 2. Template Macro

```jinja
{% include "partials/wayfinding.html" with paths=["writer", "themer", "contributor"] %}
```

**Rejected**: Not usable in markdown content; requires template knowledge.

### 3. Custom Shortcode

```markdown
{{< wayfinding paths="writer,themer,contributor" >}}
```

**Rejected**: Less expressive than directive syntax; harder to customize per-path.

---

## Migration Path

1. **Phase 1**: Add directive alongside existing `list-table` usage
2. **Phase 2**: Update Getting Started to use new directive
3. **Phase 3**: Document directive in site docs
4. **Phase 4**: Deprecate raw table approach in style guide

---

## Success Criteria

- [ ] Directive renders correctly in default theme
- [ ] Auto-pull fetches metadata from linked pages
- [ ] Graceful fallback when linked page missing
- [ ] Responsive layout (3-col → 1-col on mobile)
- [ ] Accessible (keyboard navigation, screen reader friendly)
- [ ] CSS customizable via theme variables

---

## Open Questions

1. **Should paths support nested content (like card bodies)?**
   - Current design: Yes, for flexibility
   - Alternative: Only title + description (simpler)

2. **How to handle missing linked pages in strict mode?**
   - Warning + fallback (dev mode)
   - Error (strict mode)

3. **Should `:from:` directory discovery be Phase 1 or later?**
   - Recommend Phase 3 (nice-to-have, not essential)

4. **Naming: `wayfinding` vs `paths` vs `diverge` vs `choose`?**
   - `wayfinding` is descriptive but long
   - `paths` is shorter but generic
   - Recommend: `wayfinding` (explicit intent)

---

## References

- [Cards Directive](bengal/rendering/plugins/directives/cards.py) - Similar pattern
- [Steps Directive](bengal/rendering/plugins/directives/steps.py) - Nested directive example
- [Cross-Reference Plugin](bengal/rendering/plugins/cross_references.py) - Page lookup
- [Template Functions](bengal/rendering/template_functions/crossref.py) - `doc()` function
- [Getting Started Page](site/content/docs/getting-started/_index.md) - Current usage

---

## Appendix: Visual Mockup

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Choose Your Path                               │
├─────────────────────┬─────────────────────┬──────────────────────────┤
│ ┌─────────────────┐ │ ┌─────────────────┐ │ ┌──────────────────────┐ │
│ │ 📝 Writer       │ │ │ 🎨 Themer       │ │ │ 🛠️ Contributor       │ │
│ │                 │ │ │                 │ │ │                      │ │
│ │ Create content, │ │ │ Design custom   │ │ │ Fix bugs, add        │ │
│ │ write posts,    │ │ │ themes and      │ │ │ features, improve    │ │
│ │ build a site    │ │ │ branded         │ │ │ Bengal's core        │ │
│ │                 │ │ │ experiences     │ │ │                      │ │
│ │ ────────────────│ │ │ ────────────────│ │ │ ──────────────────── │ │
│ │ ⏱️ 5 min        │ │ │ ⏱️ 15 min       │ │ │ ⏱️ 30 min            │ │
│ │ 🟢 Beginner     │ │ │ 🟡 Intermediate │ │ │ 🟠 Advanced          │ │
│ │                 │ │ │                 │ │ │                      │ │
│ │ [Get Started →] │ │ │ [Get Started →] │ │ │ [Get Started →]      │ │
│ └─────────────────┘ │ └─────────────────┘ │ └──────────────────────┘ │
└─────────────────────┴─────────────────────┴──────────────────────────┘
```

