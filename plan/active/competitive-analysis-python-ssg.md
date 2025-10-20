# Competitive Analysis: Python SSG Landscape (`Sphinx`, `MkDocs`, `Pelican`, `Nikola`, `Lektor`)

### Goal

Assess key Python static site/documentation generators against Bengal’s strengths to guide positioning, roadmap, and go‑to‑market priorities.

### Evaluation Criteria

- Popularity and momentum (GitHub stars, PyPI downloads, community/maintainers)
- Primary use cases fit (docs, blogs, general sites)
- Extensibility (plugins/extensions, theming)
- Developer UX (setup, configuration, error quality, development server, live reload)
- Performance & scale (incremental builds, parallelism, cache strategy)
- Content model (taxonomies, menus, cascading metadata)
- Integrations (`autodoc`, search, i18n, notebooks)

### TL;DR Ranking (by overlap with Bengal’s ambitions)

1) `MkDocs` (docs‑first, Markdown, broad adoption, Material ecosystem)
2) `Sphinx` (docs standard, rich cross‑refs, `MyST` bridges Markdown)
3) `Pelican` (blog/news focus, flexible Jinja theming)
4) `Nikola` (feature‑rich, multilingual, multiple formats including notebooks)
5) `Lektor` (static CMS with admin UI; niche but distinctive)

Rationale: `MkDocs` and `Sphinx` dominate documentation adoption; `Pelican`/`Nikola` are strong for blogs and mixed sites; `Lektor` is unique but narrower. Non‑Python static site generators (e.g., `Hugo`, `Docusaurus`) influence expectations on speed and UX.

### Snapshots (indicative; verify periodically)

- `Sphinx`: dominant for Python API docs; extensive extension ecosystem; reST + `MyST`
- `MkDocs`: Markdown‑first, fast/simple, Material theme drives adoption; `mkdocstrings`
- `Pelican`: Jinja theming, feeds/taxonomy; Python‑focused blogging mainstay
- `Nikola`: multiple input formats, multilingual, notebooks; deeper setup
- `Lektor`: GUI/admin with data models; static CMS experience

### Where Bengal stands out today

- Incremental builds with explicit dependency tracking and parallelism
- Menu/taxonomy object model and cascading metadata
- AST‑based `autodoc` for Python and CLI (no import needed)
- Output quality hardening and health validation
- Theme chain resolution utility, template validation service, progress reporting

### Competitive gaps/opportunities vs each

- `MkDocs`: match simplicity DX; surpass with structured content model, incremental rebuild speed, and richer menus/taxonomies by default. Provide first‑class `mkdocstrings`‑like experience via Bengal `autodoc`.
- `Sphinx`: differentiate on Markdown‑native, speed (incremental/parallel), clearer configuration, modern themes; bridge to Sphinx‑style cross‑refs where possible.
- `Pelican`: compete on performance and DX; offer batteries‑included menus/taxonomy and modern theme pack; keep Jinja flexibility.
- `Nikola`: turn versatility into defaults with sane presets; emphasize faster rebuilds and simpler mental model.
- `Lektor`: offer CLI‑first alternative to GUI with comparable data modeling via simple front matter + collections.

### Strategic Bets (next 1–2 releases)

1. Theme & UX
   - Ship 2–3 polished themes (docs/blog/marketing) with dark mode, a11y, search, and i18n‑ready templates.
   - “Swizzle” experience: safe overrides with upgrade path.
2. Docs‑first ergonomics
   - One‑command setup for docs sites (`MkDocs`‑grade simplicity).
   - `mkdocstrings`‑class experience using Bengal `autodoc`; `MyST`‑compatible MD features where possible.
3. Performance story
   - Benchmarks against `MkDocs`/`Sphinx`/`Pelican` on medium/large sites; publish repeatable scenarios.
   - Default incremental builds; cache corruption resilience and reporting.
4. Extensibility
   - Public plugin API for parsers, render hooks, post‑processors; stable lifecycle events.
   - Template validation and theme discovery tooling in CLI.
5. Migration paths
   - Importers: `MkDocs` (nav, MD, assets), `Sphinx` (`MyST`/reST subset), `Pelican`/`Nikola` content/taxonomy.
   - Guidance docs and code‑mods for common patterns.

### Key metrics

- Time‑to‑first‑page (TTFP) and time‑to‑first‑successful‑build for new users
- Rebuild latency on edits (p50/p95) for 1k/10k page sites
- Theme adoption: installations and swizzled templates per user
- `autodoc` adoption: % projects using Python/CLI `autodoc`
- Plugin ecosystem: number of third‑party plugins within 3–6 months

### Competitive Positioning Statement

“Bengal is a Python SSG for modern docs and content sites that combines `MkDocs`‑level simplicity with `Sphinx`‑grade depth and `Pelican`‑style Jinja flexibility—backed by a fast incremental build pipeline, rich content model, and first‑class `autodoc`.”

### Follow‑ups

- Schedule metric refresh every 3 months (stars/downloads/plugin counts)
- Expand benchmarks in `benchmarks/scenarios/` to mirror real competitor sites
- Publish comparison guide and migration guides in `docs/` once features land
