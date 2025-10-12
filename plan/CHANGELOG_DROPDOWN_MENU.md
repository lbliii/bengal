# Dropdown Menu for Release Notes

**Status**: ✅ Complete  
**Date**: 2025-10-12

## What Changed

Added a dropdown menu to the showcase site that nests "Release Notes" under "Documentation".

## Implementation

### Menu Configuration

**File**: `examples/showcase/bengal.toml`

```toml
[[menu.main]]
name = "Documentation"
url = "/docs/"
weight = 2
identifier = "docs"  # Added identifier

[[menu.main]]
name = "Release Notes"
url = "/releases/"
weight = 5
parent = "docs"  # Links to Documentation parent
```

### How It Works

1. **Identifier**: Parent menu item needs an `identifier` field
2. **Parent**: Child menu items reference parent using `parent = "identifier"`
3. **Automatic**: The menu system automatically builds the hierarchy
4. **Template**: `base.html` already renders `item.children` as dropdowns
5. **CSS**: `layouts/header.css` already has dropdown styles
6. **JavaScript**: `mobile-nav.js` already handles mobile toggles

### Result

**Desktop Navigation:**
- Documentation (hover to reveal)
  - Release Notes

**Mobile Navigation:**
- Documentation ▼ (tap to expand)
  - Release Notes

## Menu System Features

Bengal's menu system supports:

- **Hierarchical menus** with parent/child relationships
- **Multiple levels** of nesting (recursive)
- **Active states** for current page and trail
- **Auto-sorting** by weight
- **Hover dropdowns** on desktop
- **Collapsible menus** on mobile
- **Keyboard navigation** (focus-within)
- **ARIA support** for accessibility

## Adding More Dropdowns

To add more items to the Documentation dropdown:

```toml
[[menu.main]]
name = "Tutorials"
url = "/tutorials/"
weight = 6
parent = "docs"

[[menu.main]]
name = "Examples"
url = "/examples/"
weight = 7
parent = "docs"
```

Or create a new dropdown:

```toml
[[menu.main]]
name = "Resources"
url = "/resources/"
weight = 10
identifier = "resources"

[[menu.main]]
name = "Blog"
url = "/blog/"
parent = "resources"

[[menu.main]]
name = "Community"
url = "/community/"
parent = "resources"
```

## Testing

The dropdown is live at:
- http://localhost:8000/
- Hover over "Documentation" to see the dropdown
- On mobile, tap "Documentation" to expand

## Notes

- No code changes needed - everything was already built-in!
- The menu system automatically detects children and renders dropdowns
- Styles and JavaScript were already present in the theme
- This is a standard feature of Bengal's menu system
