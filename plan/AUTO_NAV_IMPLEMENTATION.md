# Auto-Navigation Implementation Summary

**Date**: 2025-10-12  
**Status**: ✅ Complete

## Overview

Implemented hybrid auto-discovery navigation system for main navigation bar, similar to how sidebars and TOC work in Bengal. The system provides zero-config navigation that "just works" while still supporting manual configuration for power users.

## Problem Statement

When users run `bengal new site` with the wizard to create sections, the navigation bar was empty unless they manually configured `[[menu.main]]` entries in `bengal.toml`. This created a poor first-time user experience.

## Solution: Hybrid Approach

Implemented a **hybrid auto-discovery + manual config** system:

1. **Auto-discovery by default** - Discovers top-level sections automatically
2. **Manual config takes precedence** - When `[[menu.main]]` exists, use it instead
3. **Fine-grained control** - Sections can opt-out via `menu: false` in frontmatter
4. **Progressive enhancement** - Start simple, customize later

## Implementation Details

### 1. Template Function (`get_auto_nav()`)

**File**: `bengal/rendering/template_functions/navigation.py`

```python
def get_auto_nav(site: "Site") -> list[dict[str, Any]]:
    """
    Auto-discover top-level navigation from site sections.

    Features:
    - Auto-discovers all top-level sections in content/
    - Respects section weight for ordering
    - Respects 'menu: false' in section _index.md to hide from nav
    - Returns empty list if manual [[menu.main]] config exists (hybrid mode)
    """
```

**Key behaviors**:
- Only discovers depth-1 sections (direct children of `content/`)
- Respects `weight` in section `_index.md` for ordering
- Checks for `menu: false` to hide sections
- Returns empty if manual config exists (defers to manual)

### 2. Template Updates

**File**: `bengal/themes/default/templates/base.html`

Updated both desktop and mobile nav sections:

```jinja
{# Try manual menu config first, fallback to auto-discovery #}
{% set main_menu = get_menu_lang('main', current_lang()) %}
{% set auto_nav = get_auto_nav() if not main_menu else [] %}

{% if main_menu or auto_nav %}
<ul>
    {# Always show Home first #}
    <li><a href="/">Home</a></li>

    {# Manual menu items (if configured) #}
    {% if main_menu %}
        {% for item in main_menu %}
            ...
        {% endfor %}
    {% endif %}

    {# Auto-discovered nav items (if no manual config) #}
    {% if auto_nav %}
        {% for item in auto_nav %}
            <a href="{{ item.url }}">{{ item.name }}</a>
        {% endfor %}
    {% endif %}
</ul>
{% endif %}
```

### 3. Menu Config Helper (Kept for Wizard)

**File**: `bengal/cli/helpers/menu_config.py`

Still useful for pre-populating config when users want explicit control:

```python
def generate_menu_config(sections: list[str], menu_name: str = "main") -> str:
    """Generate menu configuration entries for given sections."""

def append_menu_to_config(config_path: Path, sections: list[str]) -> bool:
    """Append menu configuration to existing bengal.toml file."""
```

### 4. Wizard Integration

**Files**:
- `bengal/cli/commands/new.py`
- `bengal/cli/commands/init.py`

The wizard now auto-generates menu config by default, but users can delete it to use auto-discovery:

```python
# Auto-generate menu configuration if sections were created
if sections_created:
    from bengal.cli.helpers.menu_config import append_menu_to_config

    menu_added = append_menu_to_config(config_path, section_list)
    if menu_added:
        click.echo("🎯 Navigation menu auto-generated!")
```

## Usage Examples

### Example 1: Zero-Config (Auto-Discovery)

```toml
# bengal.toml - No menu config needed!
[site]
title = "My Site"

[build]
output_dir = "public"
```

With sections: `content/blog/`, `content/about/`, `content/projects/`

**Result**: Nav automatically shows: Home | About | Blog | Projects

### Example 2: Section Opt-Out

```yaml
# content/drafts/_index.md
---
title: Drafts
menu: false  # Hide from navigation
---
```

**Result**: Drafts section exists but doesn't appear in nav

### Example 3: Manual Config (Override)

```toml
# bengal.toml
[[menu.main]]
name = "Projects"
url = "/projects/"
weight = 1

[[menu.main]]
name = "GitHub"
url = "https://github.com/user/repo"
weight = 2
```

**Result**: Manual config takes precedence, auto-discovery disabled

### Example 4: Weight-Based Ordering

```yaml
# content/blog/_index.md
---
title: Blog
weight: 1  # Show first
---

# content/about/_index.md
---
title: About
weight: 10  # Show after blog
---
```

**Result**: Nav shows in weight order

## Testing Results

✅ **Auto-discovery works**: Created site with sections, nav populates automatically  
✅ **Manual config precedence**: When `[[menu.main]]` exists, uses it instead  
✅ **Section opt-out works**: `menu: false` hides sections from nav  
✅ **Weight ordering works**: Sections appear in weight order  
✅ **Mobile nav works**: Same behavior on mobile navigation

## Benefits

1. **Zero-config for beginners** - Sites work immediately
2. **Consistent with Bengal philosophy** - Like sidebar/TOC auto-generation
3. **Power user flexibility** - Manual config when needed
4. **Progressive enhancement** - Start simple, customize later
5. **External link support** - Manual config can add GitHub, social, etc.

## Files Modified

- `bengal/rendering/template_functions/navigation.py` - Added `get_auto_nav()`
- `bengal/themes/default/templates/base.html` - Updated nav sections
- `bengal/cli/helpers/menu_config.py` - New helper for menu config generation
- `bengal/cli/commands/new.py` - Wizard integration
- `bengal/cli/commands/init.py` - Wizard integration
- `bengal/cli/templates/base.py` - Added `menu_sections` field
- `bengal/cli/templates/*/template.py` - Added menu_sections to templates

## Future Enhancements

Potential future improvements:

1. **Smart home detection** - Auto-detect if home page exists, skip "Home" link
2. **Nested menus** - Auto-discover subsections for dropdown menus
3. **Icon support** - Allow icons in section frontmatter
4. **Sort strategies** - title, date, custom field sorting
5. **Section groups** - Group related sections together

## Design Decisions

### Why Hybrid Instead of Only Auto-Discovery?

- **External links**: Manual config needed for GitHub, social links, etc.
- **Custom ordering**: Sometimes alphabetical/weight isn't enough
- **Advanced features**: Dropdowns, icons, translations need manual config
- **Migration path**: Users with existing config shouldn't break

### Why Not Always Auto-Discover + Merge?

- **Explicit > Implicit**: When user configures menu, they want control
- **Performance**: Simpler logic, faster rendering
- **Predictability**: Clear behavior - either auto OR manual

### Why Only Top-Level Sections?

- **Simplicity**: Flat nav is most common pattern
- **Performance**: Less computation
- **Flexibility**: Users can manually configure nested menus if needed

## Conclusion

The hybrid auto-navigation system provides the best of both worlds:
- Beginners get a working nav immediately
- Power users retain full control
- Consistent with Bengal's "zero-config by default" philosophy

The implementation is clean, performant, and extensible for future enhancements.
