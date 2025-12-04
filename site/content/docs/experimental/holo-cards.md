---
title: "Holographic Card Effects"
description: "Pokemon TCG-inspired holographic admonitions and card components"
date: 2024-12-03
layout: doc
tags: [experimental, css, components]
toc: true
---

# ✨ Holographic Card Effects

Pokemon TCG-inspired holographic effects for Bengal documentation components.

> **Inspiration**: Based on [simeydotme's Pokemon Cards CSS](https://github.com/simeydotme/pokemon-cards-css) and the [CSS-Tricks article](https://css-tricks.com/holographic-trading-card-effect/).

:::{tip}
**Interactive Demo** — The examples below are interactive. Move your cursor over cards to see the full effect!
:::

---

## Features

- **Rainbow foil shimmer** — Conic gradients that rotate with cursor position
- **3D card tilt** — Cards physically tilt as you move the cursor
- **Multiple variants** — Rainbow, Cosmos, Sunburst, and Gold frames
- **Energy orbs** — Pokémon-style type indicators with inner glow
- **Holographic admonitions** — Apply the holo effect to notes, tips, warnings
- **Dark mode support** — Effects adjust for dark backgrounds
- **Reduced motion** — Respects `prefers-reduced-motion`

---

## Holographic Admonitions (Live)

These admonitions have the `holo` class applied:

:::{note}
:class: holo

**Holographic Note** — Move your cursor around to see the rainbow foil shimmer!
:::

:::{tip}
:class: holo

**Pro Tip** — The effect uses CSS custom properties updated by JavaScript.
:::

:::{warning}
:class: holo

**Caution** — Warning gets an orange-shifted holo effect.
:::

---

## Usage

Add the `holo` class to any admonition:

```markdown
:::{note}
:class: holo

Your holographic content here...
:::
```

---

## How It Works

The holographic effect combines several CSS techniques:

1. **Rainbow gradient** — A repeating linear gradient cycling through spectrum colors
2. **`mix-blend-mode: color-dodge`** — Creates the metallic shine effect
3. **Radial mask** — Focuses the holo intensity around cursor position
4. **3D transforms** — `rotateX` and `rotateY` based on cursor coordinates
5. **CSS custom properties** — JavaScript updates `--pointer-x` and `--pointer-y` on mousemove

---

## Next Steps

- [ ] Package as a Bengal theme variant
- [ ] Add sparkle particle overlay
- [ ] Create full card component with image support
- [ ] Add more rarity effects (reverse holo, texture patterns)
