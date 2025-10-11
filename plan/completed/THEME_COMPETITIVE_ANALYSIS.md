## Bengal Theming: Competitive Analysis (Hugo, Jekyll, MkDocs/Material, Docusaurus, Eleventy)

### Executive summary
- Bengal’s theming is strong for documentation-style sites: clean Jinja2 templating, predictable override rules, extensive template helper API (~75+ functions), and a modern default theme with design tokens and dark mode.
- Biggest gaps vs top SSGs: no built-in CSS/JS pipeline (SCSS/PostCSS/bundling), fewer ready-made themes, smaller plugin/theme ecosystem.
- Dev experience is competitive (profiles, live reload, strict mode, template bytecode caching), with simple mental model for template resolution and overrides.

### How theming works in Bengal
- Theme selection: configured via `theme` in config; default is `"default"`.
- Template resolution order (override-friendly):
  1) project `templates/` → 2) selected theme `themes/<theme>/templates/` → 3) bundled `themes/default/templates/`.
- Per-page template selection: explicit `template` in frontmatter, then `type` (api-reference, cli-reference, doc, tutorial, blog), then section-based, then fallback to `page.html` / `index.html`.
- Theme assets: theme assets are discovered first; site assets override theme assets by path/name. Fingerprinting and minification available (pipeline-lite; no SCSS/PostCSS).
- Template helper API: 70+ functions across 16–17 modules (strings, collections, dates, urls, images, SEO, taxonomies, pagination, navigation, crossref, etc.).
- Markdown plugins: directives (admonitions, tabs, dropdown, code-tabs), variable substitution, cross-references; post-processing injects anchors/TOC/xrefs.
- Dev experience: build profiles (`writer`, `theme-dev`, `dev`), live reload via SSE, template bytecode cache, strict/validate flags, incremental/parallel builds.

### Competitive matrix (high level)

| Capability | Bengal | Hugo | Jekyll | MkDocs/Material | Docusaurus | Eleventy |
|---|---|---|---|---|---|---|
| Templating engine | Jinja2 | Go templates | Liquid | Jinja2 | React (MDX) | Multiple (Nunjucks/Liquid/etc.) |
| Template overrides | Project > Theme > Default | Project > Theme | Project > Theme (gem) | Project > Theme | Custom swizzles / shadowing | Project > Theme |
| Per-page template selection | template/type/section/fallback | kind/layout/type (complex) | layouts via front matter | theme layouts/partials | React components, layouts | layout chain per engine |
| Theme assets precedence | Site overrides theme | Site overrides theme | Site overrides theme | Site overrides theme | Project overrides theme | Site overrides theme |
| CSS/JS pipeline | Minify + fingerprint only | Full pipeline (SCSS, PostCSS, esbuild) | Minimal (plugins) | Minimal; usually external | Full web tooling (Node) | External or plugin-based |
| Dark mode & tokens | Built-in tokens + toggle | Theme-specific | Theme-specific | Material has robust system | Theme-specific | Theme-specific |
| Theme ecosystem | Default + custom | Huge | Large | Strong (Material) | Strong | Growing |
| Plugin ecosystem | Moderate (Bengal features) | Huge | Large | Large (plugins) | Large | Large |
| Live reload/dev UX | Built-in SSE reload, profiles | Fast dev server | `jekyll serve` w/ reload | `mkdocs serve` reload | Hot reload via Node | `eleventy --serve` reload |
| Autodoc docs/API styling | Built-in reference templates | Varies by theme | Varies by theme | Excellent with Material | Possible via MDX/components | Possible via templates |

Key takeaways:
- Bengal outperforms on template helper richness and doc-focused theme defaults; ties or wins on override clarity and DX.
- Hugo sets the bar for built-in asset pipeline; Bengal defers to external tools.
- MkDocs/Material dominates out-of-the-box docs UX ecosystem; Bengal’s default theme is close but ecosystem is smaller.

### Strengths
- Clear override model and predictable template resolution.
- Extensive template helper functions (~75+) and doc-friendly directives.
- Modern default theme: design tokens, dark mode, scoped CSS architecture, accessibility focus.
- Good DX: live reload, build profiles, template bytecode cache, strict/validate options.

### Gaps
- No integrated SCSS/PostCSS/JS bundling; requires external tooling.
- Smaller theme/plugin ecosystem and marketplace; fewer off-the-shelf themes.
- Limited multi-theme composition (single active theme vs theme layering).

### Recommendations (to match or surpass competitors)
- Add optional integrated asset pipeline: SCSS → CSS, PostCSS, esbuild for JS/TS, source maps.
- Introduce theme composition/inheritance (theme extends base, selective overrides).
- Publish 3–5 official themes (Docs, Blog, Marketing, API Reference, Minimal) and a theme starter kit.
- Add “swizzle” CLI for copying/overriding theme partials safely with diff-aware updates.
- Enhance component library docs with copy-paste examples and Storybook-style preview for theme developers.

### References to current implementation (highlights)
- Theme selection and default: site config `theme = "default"`.
- Template resolution: project → theme → bundled default.
- Per-page template selection: explicit → type → section → fallback.
- Asset precedence: site assets override theme assets.


