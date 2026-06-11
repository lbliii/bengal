# Experimental CSS Components

Components in this directory are **experimental** and may change or be removed without notice. Use with caution.

## Holo Cards (`holo-cards-advanced.css`)

**Purpose**: Holographic TCG-style card effects inspired by [pokemon-cards-css](https://github.com/simeydotme/pokemon-cards-css). Uses mouse-tracking via CSS custom properties for dynamic shine and gradient effects.

**Status**: Not loaded by default. This file is included **only when the build's CSS feature detector finds a holographic class in rendered content** — the regex `holo[-_]?card|holographic` in `bengal/orchestration/feature_detector.py`, mapped to this file via `FEATURE_CSS["holo_cards"]` in `bengal/themes/default/css_manifest.py`. It is also listed in `CSS_EXPERIMENTAL` (opt-in) in the same manifest. To use it, apply the `.holo-card` class to card elements (which triggers detection); to scope effects, add `data-style="holo"` to a parent container.

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

Experimental components are **not** imported unconditionally by `style.css`. Inclusion is driven by the CSS manifest in `bengal/themes/default/css_manifest.py`:

- **Feature-detected** — files in `FEATURE_CSS` (e.g. `holo_cards` → `experimental/holo-cards-advanced.css`) are added automatically when the build's feature detector matches the corresponding pattern in rendered content.
- **Opt-in** — files in `CSS_EXPERIMENTAL` are available for explicit inclusion and are never emitted unless requested.

This keeps experimental, may-be-removed CSS out of every site's bundle by default.
