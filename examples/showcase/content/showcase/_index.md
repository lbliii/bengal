---
title: Theme Showcase Gallery
nav_title: Showcase
description: Every default-theme component, layout, and interactive state on one page
type: doc
weight: 1
icon: star
tags: [showcase, theme, quality-gate]
edit_url: https://github.com/lbliii/bengal/edit/main/examples/showcase/content/showcase/_index.md
---

# Theme Showcase Gallery

The Pridelands default theme, fully exercised. Use this page as a visual-regression
baseline and manual quality gate. Switch palettes via the header appearance menu,
open search with {kbd}`Cmd+K` / {kbd}`Ctrl+K`, and use the action-bar share menu
for copy-for-LLM and design-token export.

:::{note}
**Interactive demos:** palette switcher (header), search modal ({kbd}`Cmd+K`), view
transitions (navigate to another page), copy-for-LLM (action-bar share menu),
feedback widget (action-bar), and theme-token copy (action-bar share menu).
:::

## Admonitions

:::{tip}
Helpful suggestion — shortcuts and best practices.
:::

:::{warning} Warning
Something may break or needs attention before you proceed.
:::

:::{danger}
Critical — data loss, security, or irreversible action possible.
:::

## Layout

::::{cards}
:columns: 2

:::{card} Cards
:icon: star
Two-column card grid for navigation and feature highlights.
:::

:::{card} Code Blocks
:icon: code
Premium code blocks with copy, language label, and line highlights.
:::

::::{/cards}

::::{tab-set}

:::{tab-item} Tab A
First panel content with **markdown** support.
:::

:::{tab-item} Tab B
:selected:
Second panel, selected by default.
:::

::::{/tab-set}

:::{dropdown} Dropdown / Details
:icon: chevron-down

Collapsed content for advanced options or long prose you do not want above the fold.
:::

## Formatting & UI

{bdg-primary}`New` {bdg-secondary}`Beta`

:::{checklist} Example checklist
:show-progress:
- [x] Install Bengal
- [x] Open this showcase
- [ ] Walk the quality gate below
:::

:::{steps}

:::{step} Switch palettes
Use the appearance menu in the header — try all five named palettes in light and dark.
:::

:::{step} Test search
Press {kbd}`Cmd+K` (macOS) or {kbd}`Ctrl+K` (Windows/Linux) to open the command palette.
:::

:::{step} Copy for LLM
Open the action-bar share menu and copy the page LLM text or design tokens.
:::

:::{/steps}

:::{button} Quality Gate
:link: /showcase/#quality-gate
:style: primary
:::

## Code & Data

:::{code-tabs}

```python hello.py
def greet(name: str) -> str:
    """Premium code block with syntax highlighting."""
    return f"Hello, {name}!"
```

```javascript hello.js
function greet(name) {
  console.log(`Hello, ${name}!`);
}
```

:::

```python {1,3-4} title="Line highlights"
# Line 1 highlighted
x = 1
y = 2  # lines 3-4 highlighted
z = 3
```

## Versioning

:::{since} 0.5.1
Pridelands Phase 0–2 shipped: OKLCH palettes, light-dark(), custom elements, command-palette search.
:::

:::{deprecated} 0.4.0
The in-repo `chirpui` bridge theme — use external theme packages instead.
:::

## Roles & Cross-References

- Keyboard: {kbd}`Ctrl+C`
- Abbreviation: {abbr}`SSG (Static Site Generator)`
- Inline math: {math}`E = mc^2`

## Image (CLS-safe)

:::{figure} /assets/images/kida-avatar.png
:alt: Kida template engine mascot
:caption: Figure with intrinsic width/height attributes for zero CLS
:width: 128px
:height: 128px
:::

## Quality Gate {#quality-gate}

Manual checklist for the Pridelands theme quality bar. Automated Lighthouse/Playwright
enforcement is deferred — verify each item by hand on this page.

:::{important} Quality Gate v1 (manual)

**Tooling decision:** v1 is a documented manual checklist on this gallery page.
Automated visual-regression / Lighthouse CI is an explicit follow-on.

### Accessibility (WCAG 2.2 AA)

- [ ] All 5 palettes render correctly in **light** and **dark** mode
- [ ] Focus indicators visible and not obscured by sticky header (`focus-not-obscured`)
- [ ] Interactive targets ≥ 24×24 CSS px (`target-size`)
- [ ] Reduced motion honored (`prefers-reduced-motion: reduce`)
- [ ] Skip link reaches main content
- [ ] Search modal is keyboard-trap safe and dismissible with Escape

### Performance & Layout

- [ ] Images have intrinsic `width`/`height` attributes (CLS = 0)
- [ ] No layout shift when fonts load (self-hosted fonts opt-in only)
- [ ] View transitions do not flash on first paint

### Metadata & PWA

- [ ] Favicon set (ico + 16/32 PNG + apple-touch-icon)
- [ ] `site.webmanifest` linked in `<head>`
- [ ] Open Graph + Twitter Card meta tags present
- [ ] `sitemap.xml` and `rss.xml` generated at build time
- [ ] Canonical URL and `lang` attribute on `<html>`

### AI Readiness

- [ ] Action-bar **Copy LLM text** copies per-page `index.txt`
- [ ] Action-bar **Copy theme tokens** copies `design-tokens.json`
- [ ] Site-wide `/llms.txt` linked in `<head>`

### Interactive Features

- [ ] Search modal opens with {kbd}`Cmd+K` / {kbd}`Ctrl+K`
- [ ] Palette switch persists across page loads (localStorage)
- [ ] Same-origin navigation has view transitions (when enabled)
- [ ] Code-block copy button works and announces to screen readers
- [ ] Feedback widget fires `CustomEvent` (no default telemetry)
:::

## Next Steps

- Browse the [Bengal docs](https://bengal-ssg.dev/docs/) for theme customization
- See the [directive reference](https://bengal-ssg.dev/docs/reference/directives/) for exhaustive option lists
- Read [SEO & discovery](https://bengal-ssg.dev/docs/ship/seo/) for metadata and content signals
