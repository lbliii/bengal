# Bengal Default Theme — Design System

**Status:** Active (Pridelands refresh, #532)  
**Last updated:** 2026-06-16

## Scope decision: lift the feature freeze

The 2026-06-09 strategy labeled the default theme a *feature-frozen, zero-dependency baseline*. **That freeze is lifted for one scoped, deliberate, presentation-layer refresh** — with the zero-new-runtime-dependency rule kept absolutely intact.

| Rule | Status |
|------|--------|
| Zero new runtime dependencies | **Enforced** — standing CI guard (`test_zero_external_origin`) |
| Manifest covers every shipped component | **Enforced** — standing CI guard (`test_css_manifest_coverage`) |
| Core/theme boundary | Theme owns presentation; core owns parsing, extraction, contracts |
| Byte-output determinism | Existing sitemap/agent.json/manifest-count tests run on every saga |

This is **not** a `chirp_theme` parity effort. Chirp's component-library/Alpine/htmx coupling is exactly what the default theme must not adopt.

## North star

> An empty Bengal site, zero config, renders a finished-looking product — fully offline, zero new dependencies, WCAG 2.2 AA across all palettes.

## Architecture

### CSS layers (`@layer`)

```
tokens → base → utilities → components → pages
```

Entry point: `assets/css/style.css`. Tree-shaking manifest: `css_manifest.py`.

### Design tokens (two-tier)

1. **Foundation** (`tokens/foundation.css`, `tokens/typography.css`) — primitives, never used directly in components.
2. **Semantic** (`tokens/semantic.css`) — purpose-based tokens consumed by components.
3. **Palettes** (`tokens/palettes/*.css`) — named, switchable via `data-palette`.

### JavaScript model

Progressive enhancement via `data-bengal` attributes and the `Bengal.enhance` registry (`bengal-enhance.js`). Heavy libraries (Mermaid, D3, KaTeX) are **opt-in, self-hosted capabilities** — never loaded from CDN in default output. Enable in `bengal.toml`:

```toml
[capabilities]
mermaid = true   # downloads vendor/mermaid.min.js at build time
d3 = true
katex = true
iconify = true   # Mermaid diagram icons (requires mermaid)
```

See `bengal/capabilities/` and issue #550.

### Template dialect

One Kida-native dialect. Navigation macros live inline in `base.html` (Jinja `{% from … import %}` does not survive template inheritance). Reference-only partials are not shipped.

## Quality gates

- **Zero external origin:** Default build makes zero runtime network requests to third-party origins.
- **Manifest coverage:** Every `@import` in `style.css` appears in `css_manifest.py`.
- **Determinism:** Content-hashed IDs; no `Math.random` / `Date.now` in shipped output.

## Related docs

- `assets/COMPONENT-PATTERNS.md` — interaction patterns (dialog, popover, CSS state)
- `assets/css/CSS_SCOPING_RULES.md` — component scoping rules
- `plan/epic-default-theme-refresh.md` — full Pridelands epic plan (when present)
