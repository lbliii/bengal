# RFC-006: Icon System Improvements

**Status**: Draft  
**Created**: 2024-12-08  
**Part of**: [Theme Architecture Series](rfc-theme-architecture-series.md)  
**Priority**: Low  
**Dependencies**: RFC-001 (Theme Configuration)  

---

## Summary

Centralize icon configuration in `theme.yaml`, improve the icon helper function, and support multiple icon libraries with consistent API.

---

## Problem Statement

### Current State

Icons have a **well-designed implementation** with some configuration gaps:

**Template Function** (`bengal/rendering/template_functions/icons.py`):
```python
# icons.py:144-180 - Well-designed icon function
def icon(name: str, size: int = 24, css_class: str = "", aria_label: str = "") -> Markup:
    """Render an SVG icon for use in templates."""
    # Map semantic name to icon name via ICON_MAP
    mapped_name = ICON_MAP.get(name, name)
    # Render with LRU caching
    svg_html = _render_icon_cached(mapped_name, size, css_class, aria_label)
    return Markup(svg_html)
```

**Icon Aliases** (`bengal/rendering/plugins/directives/_icons.py`):
```python
# Already has semantic aliasing!
ICON_MAP = {
    "search": "magnifying-glass",
    "menu": "list",
    "close": "x",
    # ... more aliases
}
```

**Preloading** (`icons.py:46-71`):
```python
def _preload_all_icons() -> None:
    """Pre-load all icons into memory at startup."""
    # ~86 icons, ~50KB, loaded once
```

**Icon Directory**: `themes/default/assets/icons/` contains **86 SVG files** (not 80+)

### What's Working Well

1. ✅ **Icon aliases** - `ICON_MAP` provides semantic names
2. ✅ **Performance** - LRU caching, preloading at startup
3. ✅ **Accessibility** - `aria_label` and `aria-hidden` support
4. ✅ **Consistent API** - `icon(name, size, css_class, aria_label)`

### Problems

1. **Hardcoded paths** - Icons always from `themes/default/assets/icons/`
2. **No theme config** - Icon settings not in theme configuration
3. **No library abstraction** - Can't easily switch icon libraries
4. **ICON_MAP in code** - Aliases defined in Python, not config
5. **JS preload manual** - No auto-generation from config

---

## Proposal

### Centralized Configuration

```yaml
# themes/default/theme.yaml
icons:
  # Primary icon library
  library: phosphor

  # Default icon settings
  defaults:
    size: 20
    weight: regular  # thin, light, regular, bold, fill (phosphor)
    class: icon

  # Icon aliases (semantic names → library-specific names)
  aliases:
    nav-menu: list
    nav-close: x
    external-link: arrow-square-out
    copy: clipboard
    success: check-circle
    warning: warning-circle
    error: x-circle
    info: info

  # Custom icons (site-specific)
  custom:
    path: assets/icons/custom/
    prefix: custom-

  # Icons to preload for JavaScript
  preload:
    - close
    - copy
    - enlarge
    - zoom-in
    - zoom-out
    - reset
    - download
```

### Built-in Icon Libraries

Support multiple icon libraries out of the box:

```python
# bengal/rendering/icons/libraries.py

ICON_LIBRARIES = {
    'phosphor': {
        'cdn': 'https://unpkg.com/@phosphor-icons/core@2.0.2/assets',
        'weights': ['thin', 'light', 'regular', 'bold', 'fill'],
        'default_weight': 'regular',
        'format': '{weight}/{name}.svg',
    },
    'heroicons': {
        'cdn': 'https://unpkg.com/heroicons@2.0.18',
        'variants': ['outline', 'solid', 'mini'],
        'default_variant': 'outline',
        'format': '{variant}/{name}.svg',
    },
    'feather': {
        'cdn': 'https://unpkg.com/feather-icons@4.29.0/dist/icons',
        'format': '{name}.svg',
    },
    'lucide': {
        'cdn': 'https://unpkg.com/lucide-static@0.294.0/icons',
        'format': '{name}.svg',
    },
}
```

### Improved Icon Helper

```python
# bengal/rendering/template_functions/icons.py

def icon(
    name: str,
    size: int | None = None,
    weight: str | None = None,
    css_class: str = '',
    library: str | None = None,
    aria_label: str | None = None,
    aria_hidden: bool = True,
) -> str:
    """
    Render an SVG icon.

    Args:
        name: Icon name (or alias from theme.yaml)
        size: Icon size in pixels (default from theme config)
        weight: Icon weight/variant (library-specific)
        css_class: Additional CSS classes
        library: Override icon library
        aria_label: Accessible label (sets aria_hidden=false)
        aria_hidden: Hide from screen readers (default: true)

    Examples:
        {{ icon('arrow-right') }}
        {{ icon('check', size=16, weight='bold') }}
        {{ icon('github-logo', aria_label='GitHub') }}
        {{ icon('custom-logo', library='custom') }}
    """
    config = get_icon_config()

    # Resolve alias
    resolved_name = config.aliases.get(name, name)

    # Get defaults
    size = size or config.defaults.size
    weight = weight or config.defaults.weight
    library = library or config.library

    # Get SVG content
    svg = load_icon(resolved_name, library, weight)

    # Build attributes
    attrs = {
        'class': f"{config.defaults.class} {css_class}".strip(),
        'width': size,
        'height': size,
        'aria-hidden': 'true' if aria_hidden and not aria_label else 'false',
    }
    if aria_label:
        attrs['aria-label'] = aria_label
        attrs['role'] = 'img'

    return inject_attrs(svg, attrs)
```

### Template Usage

```jinja2
{# Basic usage (uses theme defaults) #}
{{ icon('arrow-right') }}

{# Custom size #}
{{ icon('check', size=16) }}

{# Custom weight (phosphor) #}
{{ icon('warning', weight='fill') }}

{# Semantic alias #}
{{ icon('nav-menu') }}  {# Resolves to 'list' #}

{# Accessible icon (visible to screen readers) #}
{{ icon('github-logo', aria_label='View on GitHub') }}

{# Custom icon from site #}
{{ icon('custom-logo') }}

{# Different library #}
{{ icon('heart', library='heroicons') }}
```

### JavaScript Icon Access

Auto-generated from config:

```jinja2
{# Automatically in base.html #}
<script>
  window.Bengal = window.Bengal || {};
  window.Bengal.icons = {
    {% for name in theme.icons.preload %}
    '{{ name }}': '{{ icon_url(name) }}',
    {% endfor %}
  };

  // Helper function
  window.Bengal.getIcon = async function(name) {
    if (this.icons[name]) {
      return await fetch(this.icons[name]).then(r => r.text());
    }
    console.warn(`Icon not preloaded: ${name}`);
    return null;
  };
</script>
```

Usage in JavaScript:
```javascript
// Get preloaded icon URL
const closeIconUrl = Bengal.icons.close;

// Fetch icon SVG
const svg = await Bengal.getIcon('copy');
button.innerHTML = svg;
```

### Icon Preview Page

Auto-generated at `/dev/icons/` in development:

```jinja2
{# Auto-generated icon gallery #}
<div class="icon-gallery">
  <h2>Theme Icons</h2>

  <h3>Available Icons</h3>
  <div class="icon-grid">
    {% for icon_name in available_icons %}
    <div class="icon-item">
      {{ icon(icon_name) }}
      <code>{{ icon_name }}</code>
    </div>
    {% endfor %}
  </div>

  <h3>Aliases</h3>
  <table>
    <tr><th>Alias</th><th>Icon</th><th>Preview</th></tr>
    {% for alias, name in theme.icons.aliases.items() %}
    <tr>
      <td><code>{{ alias }}</code></td>
      <td><code>{{ name }}</code></td>
      <td>{{ icon(alias) }}</td>
    </tr>
    {% endfor %}
  </table>

  <h3>Weights</h3>
  <div class="icon-weights">
    {% for weight in ['thin', 'light', 'regular', 'bold', 'fill'] %}
    <div>
      {{ icon('heart', weight=weight) }}
      <code>{{ weight }}</code>
    </div>
    {% endfor %}
  </div>
</div>
```

### Custom Icons

Site-specific icons in designated directory:

```
my-site/
└── assets/
    └── icons/
        └── custom/
            ├── logo.svg
            └── mascot.svg
```

Usage:
```jinja2
{{ icon('custom-logo') }}
{{ icon('custom-mascot', size=48) }}
```

---

## Benefits

1. **Centralized config** - All icon settings in `theme.yaml`
2. **Library agnostic** - Easy to switch icon libraries
3. **Semantic aliases** - Use meaningful names, map to icons
4. **Consistent API** - Same helper works for all libraries
5. **Discoverable** - Icon gallery shows all available icons
6. **Accessible** - Built-in aria support

---

## Implementation

### Phase 1: Configuration
- [ ] Add `icons` section to RFC-001's `theme.yaml` schema
- [ ] Move `ICON_MAP` aliases to theme.yaml
- [ ] Support custom icon directory in config

### Phase 2: Enhance Existing Infrastructure
- [x] ~~Refactor icon() function~~ (already well-designed)
- [x] ~~Add alias resolution~~ (ICON_MAP exists)
- [x] ~~Add accessibility attributes~~ (aria_label, aria-hidden exist)
- [ ] Add library switching (phosphor, heroicons, feather)
- [ ] Support theme-chain icon resolution

### Phase 3: JavaScript Integration
- [ ] Auto-generate icon preload from config
- [ ] Add `Bengal.getIcon()` helper
- [ ] Remove manual icon listing from base.html

### Phase 4: Developer Experience
- [ ] Add icon gallery page generator (dev mode)
- [ ] Add icon search in dev mode
- [ ] Document icon usage and available icons

**Note**: The existing implementation in `bengal/rendering/template_functions/icons.py` is well-architected. This RFC focuses on moving hardcoded values to configuration, not rewriting the core.

---

## Migration

### Backward Compatibility

Existing `icon()` calls continue to work:
```jinja2
{{ icon('arrow-right', size=20) }}  {# Still works #}
```

New features are opt-in:
```jinja2
{{ icon('arrow-right', weight='bold') }}  {# New feature #}
```

### Configuration Migration

```bash
bengal theme migrate-icons themes/default
# Generates icons config from existing icon files
```

---

## Open Questions

1. **Should we bundle icons or use CDN?**  
   Proposal: Bundle by default, CDN optional for size

2. **Support for icon sprites?**  
   Proposal: Future enhancement, inline SVG works well

3. **Icon color customization?**  
   Proposal: Use `currentColor` in SVGs, style via CSS
