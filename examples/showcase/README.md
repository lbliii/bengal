# Bengal Theme Showcase

Live gallery of the default (Pridelands) theme. Demonstrates every component, layout,
and interactive state — doubles as the visual-regression baseline and manual quality
gate for the Pridelands epic (#545).

## Build

```bash
cd examples/showcase
bengal build
bengal serve
```

Open `/showcase/` and walk the quality-gate checklist at the bottom of the page.

## What it exercises

- All directive categories (admonitions, cards, tabs, code blocks, badges, steps)
- Interactive features (search modal, palette switcher, view transitions, action bar)
- Metadata/PWA (favicon set, webmanifest, OG tags, sitemap, RSS)
- Copy-for-LLM affordance and design-token manifest (action bar share menu)
- Image intrinsic dimensions (CLS prevention)
