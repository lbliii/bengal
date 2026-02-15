# Experimental CSS Components

Components in this directory are **experimental** and may change or be removed without notice. Use with caution.

## Holo Cards (`holo-cards-advanced.css`)

**Purpose**: Holographic TCG-style card effects inspired by [pokemon-cards-css](https://github.com/simeydotme/pokemon-cards-css). Uses mouse-tracking via CSS custom properties for dynamic shine and gradient effects.

**Status**: Loaded by default. To scope to specific pages, add `data-style="holo"` to a parent container and ensure card elements use the `.holo-card` class.

**Browser support**: Modern browsers with CSS custom properties and `filter`. Best in Chrome, Firefox, Safari 15+.

**Usage**: Apply `.holo-card` to card elements. Requires companion JavaScript for full mouse-tracking interactivity.

## Holo TCG Admonitions (`holo-tcg-admonitions.css`)

**Purpose**: Admonition blocks (note, warning, tip) styled with holographic borders.

**Status**: Not imported by default. Add `@import url('experimental/holo-tcg-admonitions.css');` to `style.css` if needed.

## Border Demos

- **border-styles-demo.css**: Demo of various border styles
- **border-gradient-theme-aware.css**: Theme-aware gradient borders

**Status**: Demo/reference only. Not for production use without review.

## Enabling Experimental Styles

Experimental components are loaded unconditionally in `style.css`. To make holo effects opt-in site-wide, add `data-experimental="holo"` to the `<html>` element when the theme supports it (e.g., via `theme.yaml`).
