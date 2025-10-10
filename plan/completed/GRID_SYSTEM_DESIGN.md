# Grid System Design for Bengal

**Date**: 2025-10-10  
**Context**: Analyzing Sphinx-Design grid system for Bengal implementation  
**Goal**: Design a grid system that makes sense for Bengal, not just copy Sphinx

## Current Sphinx-Design Syntax

```markdown
::::{grid} 1 2 2 2
:gutter: 1 1 1 2

:::{grid-item-card} {octicon}`book` Title
:link: docs/page
:link-type: doc
Card content here
:::

:::{grid-item-card} Another Card
:link: other/page
More content
:::
::::
```

### What the Numbers Mean
- `grid 1 2 2 2` = columns at different breakpoints: mobile, tablet, desktop, wide
- `gutter 1 1 1 2` = spacing at different breakpoints

### Problems with This Approach
1. **Cryptic syntax** - What do those numbers mean?
2. **Verbose nesting** - 4 colons for grid, 3 for items
3. **Tight coupling** - Grid and card are separate but always used together
4. **CSS Grid wasn't mature** when Sphinx-Design was created (2020)

## Bengal's Opportunity: Modern CSS Grid

We can leverage **CSS Grid** (2017+, universal support) which is:
- More powerful than what Sphinx-Design uses
- Declarative and simple
- Responsive by default
- Better browser support now

## Design Options

### Option A: Direct 1:1 Port (Not Recommended)
Just replicate Sphinx-Design exactly.

**Pros:**
- Easy migration
- Familiar to Sphinx users

**Cons:**
- Perpetuates bad design
- Confusing syntax
- Doesn't leverage modern CSS

### Option B: Simplified Grid System (Recommended)

Make it **dead simple** with sensible defaults:

```markdown
:::{card-grid}
:columns: auto  # or 2, 3, 4, or "1-2-3" for responsive

:::{card} Documentation
:icon: book
:link: /docs/

Learn how to use Bengal.
:::

:::{card} API Reference
:icon: code
:link: /api/

Complete API documentation.
:::

:::{card} Tutorials
:icon: graduation-cap
:link: /tutorials/

Step-by-step guides.
:::
::::
```

**Key simplifications:**
1. **Auto-layout by default** - CSS Grid figures out optimal columns
2. **Simple responsive** - `columns: "1-2-3"` means 1 col mobile, 2 tablet, 3 desktop
3. **Icons built-in** - Use simple names, not complex octicon syntax
4. **Cards are the default** - Grid items are always cards
5. **Smart defaults** - Works great with no options

### Option C: Hybrid Approach (Best of Both Worlds)

Support BOTH syntaxes:

1. **New, simple syntax** (recommended):
```markdown
:::{cards}
:columns: 3

:::{card} Title
:icon: book
:link: /page/
Content
:::
::::
```

2. **Sphinx-Design compatibility** (for migration):
```markdown
::::{grid} 1 2 2 2
:::{grid-item-card} Title
:link: page
Content
:::
::::
```

Map the old syntax to the new implementation under the hood.

## Proposed Bengal Implementation

### 1. Directive: `cards` (primary)

Simple card grid with sensible defaults:

```markdown
:::{cards}
# Defaults to auto-layout, responsive columns

:::{card} Getting Started
:link: /docs/intro/
Quick introduction to Bengal.
:::

:::{card} API Reference  
:link: /api/
Complete API documentation.
:::
::::
```

**Options:**
- `:columns: N` - Fixed number of columns (1-6)
- `:columns: auto` - Auto-layout based on card count (default)
- `:columns: "1-2-3-4"` - Responsive: mobile-tablet-desktop-wide
- `:gap: small|medium|large` - Spacing between cards (default: medium)
- `:style: default|minimal|bordered` - Card visual style

### 2. Directive: `card` (nested in cards)

Individual card with rich features:

```markdown
:::{card} Title
:icon: book           # Icon name (we'll support common icon sets)
:link: /page/         # Makes whole card clickable
:color: blue          # Accent color
:image: /img/hero.jpg # Optional header image
:footer: Updated 2025 # Optional footer text

Card content with **full markdown** support.

- List items
- Code blocks
- Anything!
:::
```

### 3. Compatibility: `grid` + `grid-item-card` (secondary)

For Sphinx migration, we accept the old syntax:

```markdown
::::{grid} 1 2 2 2
:gutter: 1

:::{grid-item-card} Title
:link: page
:link-type: doc
Content
:::
::::
```

**But internally**, we map it:
- `grid` → `cards` with columns extracted from numbers
- `grid-item-card` → `card`
- We auto-convert the confusing options to simple ones

## Implementation Architecture

```python
# bengal/rendering/plugins/directives/cards.py

class CardsDirective(DirectivePlugin):
    """Simple, modern card grid system."""
    
    def parse(self, block, m, state):
        options = self.parse_options(m)
        
        # Default to auto-layout
        columns = options.get('columns', 'auto')
        gap = options.get('gap', 'medium')
        style = options.get('style', 'default')
        
        # Parse nested cards
        content = self.parse_content(block, m, state)
        
        return {
            'type': 'card_grid',
            'columns': self._normalize_columns(columns),
            'gap': gap,
            'style': style,
            'children': content,
        }

class CardDirective(DirectivePlugin):
    """Individual card within a grid."""
    
    def parse(self, block, m, state):
        title = self.parse_title(m)
        options = self.parse_options(m)
        content = self.parse_content(block, m, state)
        
        return {
            'type': 'card',
            'title': title,
            'icon': options.get('icon'),
            'link': options.get('link'),
            'color': options.get('color'),
            'image': options.get('image'),
            'footer': options.get('footer'),
            'content': content,
        }

class GridDirective(DirectivePlugin):
    """Sphinx-Design compatibility layer."""
    
    def parse(self, block, m, state):
        # Parse old Sphinx syntax: "1 2 2 2"
        title = self.parse_title(m)  # "1 2 2 2"
        breakpoints = title.split()
        
        # Convert to our simple format
        if len(breakpoints) >= 4:
            columns = f"{breakpoints[0]}-{breakpoints[1]}-{breakpoints[2]}-{breakpoints[3]}"
        else:
            columns = breakpoints[-1]  # Use last value
        
        # Map to CardsDirective internally
        return self._convert_to_cards(columns, block, m, state)
```

## CSS Implementation

Use modern CSS Grid with custom properties:

```css
/* bengal/themes/default/components/cards.css */

.card-grid {
    display: grid;
    gap: var(--card-gap, 1.5rem);
    grid-template-columns: repeat(
        var(--card-columns, auto-fit),
        minmax(min(100%, 280px), 1fr)
    );
}

/* Auto-responsive without media queries! */
.card-grid[data-columns="auto"] {
    --card-columns: auto-fit;
}

/* Fixed columns */
.card-grid[data-columns="2"] {
    --card-columns: 2;
}

.card-grid[data-columns="3"] {
    --card-columns: 3;
}

/* Responsive columns with container queries (modern) */
.card-grid[data-columns~="1-2-3"] {
    --card-columns: 1;
}

@container (min-width: 640px) {
    .card-grid[data-columns~="1-2-3"] {
        --card-columns: 2;
    }
}

@container (min-width: 1024px) {
    .card-grid[data-columns~="1-2-3"] {
        --card-columns: 3;
    }
}

/* Card styling */
.card {
    display: flex;
    flex-direction: column;
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    padding: 1.5rem;
    background: var(--card-bg);
    transition: transform 0.2s, box-shadow 0.2s;
}

.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

/* Clickable cards */
a.card {
    text-decoration: none;
    color: inherit;
}

.card-icon {
    font-size: 2rem;
    margin-bottom: 0.5rem;
}

.card-title {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
}

.card-content {
    flex: 1;
}

.card-footer {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border-color);
    font-size: 0.875rem;
    color: var(--text-muted);
}
```

## Icon System

Instead of coupling to octicons, support multiple icon sets:

```markdown
:::{card} Title
:icon: book              # Auto-detect from common names
:icon: lucide:book       # Explicit: Lucide icons
:icon: heroicons:book    # Explicit: Heroicons
:icon: octicons:book     # Explicit: Octicons (for Sphinx compat)
:::
```

**Implementation:**
- Ship with Lucide icons (MIT license, 1000+ icons)
- Support octicons for Sphinx migration
- Allow custom icon sets via config

## Migration Path

### Step 1: Automatic Conversion Tool

```bash
bengal migrate-sphinx path/to/docs/
```

Converts:
- `grid` → `cards`
- `grid-item-card` → `card`
- Simplifies syntax
- Preserves behavior

### Step 2: Side-by-Side Support

Both syntaxes work during transition:

```markdown
# Old (still works)
::::{grid} 1 2 2 2
:::{grid-item-card} Title
:::
::::

# New (recommended)
:::{cards}
:columns: 2-3

:::{card} Title
:::
::::
```

### Step 3: Deprecation (Bengal 2.0+)

Eventually deprecate `grid`/`grid-item-card`, keep only `cards`/`card`.

## Advantages of This Approach

1. **Simpler mental model** - "I want cards in a grid"
2. **Modern CSS** - Leverages CSS Grid properly
3. **Better defaults** - Works great with no configuration
4. **Progressive enhancement** - Add options as needed
5. **Migration friendly** - Old syntax still works
6. **Future-proof** - Based on web standards

## Examples in Practice

### Simple: Auto-Layout

```markdown
:::{cards}
:::{card} One
:::
:::{card} Two
:::
:::{card} Three
:::
::::
```

Result: 3 cards, automatically sized and responsive.

### Medium: Responsive Columns

```markdown
:::{cards}
:columns: 1-2-3-4

# 1 column mobile, 2 tablet, 3 desktop, 4 wide
:::{card} Card 1
:::
:::{card} Card 2
:::
:::{card} Card 3
:::
:::{card} Card 4
:::
::::
```

### Advanced: Rich Cards

```markdown
:::{cards}
:columns: 3
:gap: large

:::{card} Getting Started
:icon: rocket
:link: /docs/intro/
:color: blue

Quick start guide to get you up and running.
:::

:::{card} API Reference
:icon: code
:link: /api/
:color: green
:image: /img/api-hero.jpg

Complete API documentation with examples.

**Updated**: October 2025
:::

:::{card} Community
:icon: users
:link: /community/
:footer: 1,234 members

Join our vibrant community!
:::
::::
```

## Recommendation

**Start with Option C (Hybrid)**:
1. Implement the **simple `cards`/`card` system** first
2. Add **compatibility layer** for `grid`/`grid-item-card`
3. Focus on making the **new syntax delightful**
4. Let users migrate naturally

This gives us:
- ✅ Modern, simple API
- ✅ Sphinx migration support
- ✅ Better than original
- ✅ Future-proof design

## Next Steps

1. **Prototype the `cards` directive** (~2 days)
2. **Test with real content** from experiments/docs
3. **Add `grid` compatibility layer** (~1 day)
4. **Polish CSS and icons** (~1 day)
5. **Document thoroughly** with examples

What do you think? Should we go with the simplified `cards` approach?

