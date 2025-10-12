# Auto-Navigation Feature - Summary

**Date**: 2025-10-12  
**Status**: ✅ Complete

## What Was Built

Implemented **hybrid auto-discovery navigation** for the main navigation bar, making Bengal sites work out-of-the-box without requiring manual menu configuration.

## Key Features

### 1. Auto-Discovery (Default Behavior)
- Automatically discovers top-level sections from `content/`
- Shows in navigation automatically (Home + all sections)
- Respects `weight` in section frontmatter for ordering
- Supports `menu: false` to hide sections

### 2. Manual Override (Power Users)
- When `[[menu.main]]` exists in config, uses that instead
- Allows external links (GitHub, social, etc.)
- Supports nested menus and custom ordering
- Manual config takes full precedence

### 3. Zero Maintenance
- **Wizard doesn't generate menu config anymore**
- Add new sections → they appear automatically
- Delete sections → they disappear automatically
- No manual maintenance required!

## User Experience

### New Site Workflow
```bash
$ bengal new site my-site --init-preset blog
# Creates sections: blog, about
# Navigation works immediately: Home | About | Blog
# No config needed! ✅
```

### Manual Customization (Optional)
```toml
# Only add if you need external links or custom ordering
[[menu.main]]
name = "GitHub"
url = "https://github.com/user/repo"
weight = 100
```

### Section Control
```yaml
# content/drafts/_index.md
---
title: Drafts
menu: false  # Hide from nav
weight: 10
---
```

## Implementation Files

- `bengal/rendering/template_functions/navigation.py` - `get_auto_nav()` function
- `bengal/themes/default/templates/base.html` - Hybrid nav template
- `bengal/cli/commands/{new,init}.py` - Removed menu config generation
- `bengal/cli/helpers/menu_config.py` - Kept for future use cases

## Design Decisions

### Why Auto-Discovery by Default?
- **Better UX**: Sites work immediately
- **Less maintenance**: No manual updates needed
- **Consistent**: Matches sidebar/TOC behavior

### Why Keep Manual Config?
- **External links**: GitHub, social media, etc.
- **Advanced features**: Nested menus, icons
- **Custom ordering**: Sometimes needed
- **Power users**: Full control when needed

### Why Hybrid Approach?
- **Explicit > Implicit**: Manual config takes full precedence
- **Progressive enhancement**: Start simple, customize later
- **Backward compatible**: Existing sites with config still work

## Benefits

✅ Zero-config navigation for 90% of use cases  
✅ No manual maintenance when adding/removing sections  
✅ Consistent with Bengal's "works out-of-the-box" philosophy  
✅ Power users can still customize everything  
✅ Backward compatible with existing sites

## Related

- Similar to Hugo's automatic menu generation
- Follows Bengal's sidebar/TOC auto-generation pattern
- Part of the wizard/scaffolding improvements
