# Bengal Icon System

All icons use **Phosphor Icons** from the [Phosphor Icons](https://phosphoricons.com/) collection.

## Usage

### In Templates (Jinja2)

```jinja
{{ icon("search", size=24) }}
{{ icon("menu", size=20, css_class="nav-icon") }}
{{ icon("close", size=18, aria_label="Close menu") }}
```

### In Python/Directives

```python
from bengal.directives._icons import render_icon

icon_html = render_icon("terminal", size=20)
```

### In JavaScript

```javascript
// Icons are loaded via window.BENGAL_ICONS
const iconSvg = await BengalUtils.loadIcon('close');
```

## Icon Naming

Icons use semantic names that map to Phosphor icon names via `ICON_MAP` in `_icons.py`.

### Common Icons

- **Navigation**: `menu`, `search`, `close`, `chevron-up`, `chevron-down`, `arrow-up`, `arrow-right`
- **Metadata**: `user`, `clock`, `calendar`, `file-text`, `arrow-clockwise`
- **Status**: `info`, `warning`, `error`, `success`, `check`
- **Files**: `file`, `folder`, `code`, `copy`, `download`
- **UI**: `settings`, `star`, `heart`, `bookmark`, `tag`
- **Admonitions**: `info`, `warning`, `error`, `success`, `tip`, `example`

## Adding New Icons

1. Download from Phosphor: https://phosphoricons.com/
2. Save to `bengal/themes/default/assets/icons/{name}.svg`
3. Normalize SVG:
   - `viewBox="0 0 256 256"`
   - `fill="none"` on root `<svg>`
   - `fill="currentColor"` on all `<path>` elements
   - Include `<title>` for accessibility
4. Add to `ICON_MAP` in `_icons.py` if using semantic name

## Icon Format

All icons must:
- Use `viewBox="0 0 256 256"` (Phosphor's native viewBox)
- Have `fill="none"` on root `<svg>` tag
- Use `fill="currentColor"` on paths for theme compatibility
- Include `<title>` tag for accessibility
- No `width`/`height` attributes (handled by CSS/template function)

## Icon Management

- **Source**: Phosphor Icons (Regular weight)
- **Location**: `bengal/themes/default/assets/icons/`
- **Format**: SVG with `currentColor` for theme awareness
- **System**: Centralized via `icon()` template function and `render_icon()` Python function
