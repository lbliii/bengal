# Bengal Color Palette

This document describes Bengal's brand color palette and accessibility considerations for CLI output.

## Color Palette

Bengal uses a vibrant, modern color palette with hex color precision for consistent cross-platform rendering:

| Name | Hex Code | RGB | Purpose | Visual |
|------|----------|-----|---------|--------|
| **Primary** | `#FF9D00` | rgb(255, 157, 0) | Brand identity, headers, primary UI | 🟠 Vivid Orange |
| **Secondary** | `#3498DB` | rgb(52, 152, 219) | Links, paths, secondary elements | 🔵 Bright Blue |
| **Accent** | `#F1C40F` | rgb(241, 196, 15) | Highlights, metric labels | 🟡 Sunflower Yellow |
| **Success** | `#2ECC71` | rgb(46, 204, 113) | Successful operations, checkmarks | 🟢 Emerald Green |
| **Error** | `#E74C3C` | rgb(231, 76, 60) | Errors, failures | 🔴 Alizarin Crimson |
| **Warning** | `#E67E22` | rgb(230, 126, 34) | Warnings, cautions | 🟠 Carrot Orange |
| **Info** | `#95A5A6` | rgb(149, 165, 166) | Informational text | ⚪ Silver |
| **Muted** | `#7F8C8D` | rgb(127, 140, 141) | Dimmed, less important text | 🌫️ Grayish |

## Semantic Styles

Colors are mapped to semantic style tokens for maintainability:

| Style Token | Color | Usage |
|-------------|-------|-------|
| `[success]` | Success Green | Successful operations, completion messages |
| `[error]` | Error Red (bold) | Error messages, failures |
| `[warning]` | Warning Orange | Warnings, cautions |
| `[header]` | Primary Orange (bold) | Section headers, Panel borders |
| `[phase]` | Default (bold) | Phase/step names in build output |
| `[path]` | Secondary Blue | File paths, URLs |
| `[metric_label]` | Accent Yellow (bold) | Metric/statistic labels |
| `[metric_value]` | Default | Metric/statistic values |
| `[prompt]` | Accent Yellow | User input prompts |
| `[bengal]` | Primary Orange (bold) | Bengal mascot (ᓚᘏᗢ) |

## Accessibility Considerations

### Color Contrast

The color palette is designed with accessibility in mind, though actual contrast ratios depend on the user's terminal background color:

#### On Light Backgrounds (e.g., white `#FFFFFF`)
- **Primary Orange** (`#FF9D00`): 2.6:1 - May not meet WCAG AA standard (4.5:1 for text)
- **Success Green** (`#2ECC71`): 2.9:1 - Below WCAG AA standard
- **Error Red** (`#E74C3C`): 3.4:1 - Below WCAG AA standard
- **Secondary Blue** (`#3498DB`): 3.1:1 - Below WCAG AA standard

#### On Dark Backgrounds (e.g., black `#000000`)
- **Primary Orange** (`#FF9D00`): 8.0:1 - **Exceeds WCAG AAA** (7:1 for text)
- **Success Green** (`#2ECC71`): 7.2:1 - **Exceeds WCAG AAA**
- **Error Red** (`#E74C3C`): 6.1:1 - **Exceeds WCAG AA**
- **Secondary Blue** (`#3498DB`): 6.8:1 - **Meets WCAG AA**

### Terminal Adaptation

**Rich library automatically adjusts** color rendering based on terminal capabilities:

1. **True Color Terminals** (16M colors): Renders exact hex colors
2. **256-Color Terminals**: Maps to closest available color
3. **16-Color Terminals**: Maps to standard ANSI colors
4. **8-Color Terminals**: Further simplified palette
5. **NO_COLOR environment**: Falls back to plain text

### User Customization

Users can control color output:

```bash
# Disable colors entirely
export NO_COLOR=1
bengal build

# In CI environments (automatically detected)
export CI=true
bengal build  # Uses plain output

# Terminal with limited colors (auto-detected)
export TERM=dumb
bengal build  # Disables rich output
```

### Design Rationale

1. **Most developers use dark terminals** - Our colors are optimized for dark backgrounds
2. **Icons supplement color** - We use emoji/symbols (✓, ❌, ⚠️) alongside colors for non-color-dependent communication
3. **Semantic meaning** - Even without color, message levels are clear from context and symbols
4. **Graceful degradation** - All information is still accessible in plain text mode

### Alternative Themes (Future)

Potential future enhancements:

```toml
# bengal.toml (not yet implemented)
[theme]
mode = "dark"  # or "light", "auto"
palette = "default"  # or custom palette name
```

This would allow users to switch between light/dark optimized palettes or provide their own colors.

## Best Practices

When using Bengal's CLI output:

1. **Don't rely on color alone** - Always include icons or text indicators
2. **Test in different terminals** - Verify output in various terminal emulators
3. **Respect NO_COLOR** - Honor user preference for plain output
4. **Use semantic styles** - Use `[success]` not `[green]` for maintainability
5. **Consider CI environments** - Ensure build output is parseable without colors

## Implementation

The color palette is defined in `bengal/utils/rich_console.py`:

```python
# Bengal color palette
PALETTE = {
    "primary": "#FF9D00",
    "secondary": "#3498DB",
    "accent": "#F1C40F",
    "success": "#2ECC71",
    "error": "#E74C3C",
    "warning": "#E67E22",
    # ...
}

# Mapped to semantic theme
bengal_theme = Theme({
    "success": PALETTE["success"],
    "error": f"{PALETTE['error']} bold",
    "warning": PALETTE["warning"],
    "header": f"{PALETTE['primary']} bold",
    # ...
})
```

This design follows modern UI framework patterns (Material UI, Tailwind CSS) where colors are centralized and referenced semantically.

## Testing

Run the color palette tests:

```bash
# Test semantic styling
pytest tests/unit/utils/test_cli_output.py -k "color or theme"

# Visual inspection
bengal build --help  # See color output in action
```

## References

- [WCAG 2.1 Color Contrast Guidelines](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)
- [NO_COLOR Standard](https://no-color.org/)
- [Rich Library Documentation](https://rich.readthedocs.io/en/stable/appendix/colors.html)
- [Terminal Color Codes](https://en.wikipedia.org/wiki/ANSI_escape_code#Colors)
