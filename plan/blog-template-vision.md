# Blog Template Vision: Analysis & Redesign Plan

**Status:** Draft for planning  
**Scope:** Default theme blog layouts, templates, subcomponents  
**Constraints:** Dogfood CSS/JS, stay DRY, align with Bengal/Kida/Patitas evolution

---

## 1. What's Changed Since the Blog Templates Were Built

### Bengal (0.1.x → 0.2.x)

| Area | Old | New |
|------|-----|-----|
| **Kida** | Basic Jinja | `kida-templates>=0.2.0` — AST-based block recompilation, fragment fast path, structured errors |
| **Patitas** | nbformat for notebooks | `patitas>=0.2.0` — native `parse_notebook()`, zero nbformat dep |
| **Server** | ThreadingTCPServer | Pounce ASGI — SSE live reload, fragment partial updates |
| **Highlight** | Per-block | Rosettes `HighlightCache` — content-hash keyed, batch uncached |
| **Theme** | Static nav | `nav_position`, `sticky`, `autohide` — configurable header behavior |
| **Math** | — | `content.math` feature — KaTeX client-side rendering |
| **Template context** | — | `TEMPLATE-CONTEXT.md` — tests (`is draft`, `is featured`, `is outdated`), shortcuts (`params`, `config`, `theme`) |

### New Shared Components (Blog Doesn't Use)

| Component | Purpose | Used By |
|-----------|---------|---------|
| **card-base.html** | `{% embed %}` slots (badges, icon, header, body, footer, actions) | *Showcase only — no consumers* |
| **article_card()** | Rich article preview with metadata, tags, image | `tag.html` |
| **content_tiles()** | Variants: compact, cards, minimal; children + subsections + related | `index.html` |
| **page-hero** | Dispatcher: editorial, magazine, overview, api, element, section | `doc/single`, autodoc |
| **empty-state** | Reusable empty-state partial | Various |

### Kida Features Available (Underused in Blog)

- `{% embed %}` — include + override blocks (card-base showcases; blog has none)
- `{% match %}` — pattern dispatch (page-hero, content_tiles use; blog uses minimal)
- `{% cache %}` — expensive computation (doc/home, blog/home use)
- `{% capture %}` — string building (page-hero macros)
- `|>` pipeline — filter chains (doc, tutorial use; blog uses some)
- Template tests: `is draft`, `is featured`, `is outdated` — blog doesn't use
- `selectattr`, `rejectattr`, `where`, `where_not`, `take`, `groupby` — blog uses a subset

### Patitas

Patitas is the **markdown parser** (not templates). Bengal uses it for content parsing. The `patitas/site/` is a Bengal site using the default theme. No direct template implications — but Patitas-driven content (e.g. directives) flows into the same templates.

---

## 2. Current Blog Template State

### Structure

```
blog/
├── home.html    # Home page with recent posts (type: blog)
├── list.html    # Blog section index (posts, featured, pagination)
└── single.html  # Individual post
```

### DRY Violations

| Issue | Location | Fix |
|-------|----------|-----|
| **Duplicate card logic** | `blog/list` has `featured_card`, `post_card`, `category_card`; `blog/home` has `post_card`; `blog/single` has `related_card`; `authors/single` has `post_card` | Unify on shared component |
| **article_card exists but blog ignores it** | `partials/components/article.html` | Blog should use or extend it |
| **content_tiles could power blog list** | `index.html` uses it for section index | Blog list could use `variant='cards'` |
| **card-base unused** | Designed for `{% embed %}` | Blog cards could be embed-based |
| **Inconsistent href vs _path** | article_card uses `article.href`; content_tiles uses `item.href` | Standardize on `_path` for internal links |

### CSS Class Fragmentation

Blog uses its own BEM-like classes that overlap with shared components:

| Blog | Shared | Notes |
|------|--------|------|
| `blog-featured-card` | `article-card`, `feature-card` | cards.css has `.article-card`, `.feature-card` |
| `blog-post-card` | `article-card`, `card` | Same `gradient-border fluid-combined` |
| `blog-home-post-card` | `article-card` | Duplicate styling |
| `blog-card-image`, `blog-card-content` | `article-card-image`, `article-card-content` | cards.css defines these |

### What Blog Does Well

- Uses `post_view` filter (PostView) for normalized access
- Uses `{% let %}`, `?.`, `??` for null safety
- Uses `{% def %}` for local card components
- Uses `tag_list` from shared components
- Uses `breadcrumbs`, `pagination`, `page_navigation` from navigation-components
- Uses `action-bar` for breadcrumbs + share

---

## 3. Comparison: Blog vs Doc vs Tutorial

| Aspect | Blog | Doc | Tutorial |
|--------|------|-----|----------|
| **Hero** | Custom `blog-home-hero` | `page-hero` (editorial/overview) | Custom `page-header` |
| **Cards** | Inline `featured_card`, `post_card` | — | Inline `tutorial_card`, `subsection_card` |
| **List layout** | Custom grid | — | Custom grid + stats |
| **Single layout** | `action-bar` + prose + related | `page-hero` + docs-nav + TOC + graph | `action-bar` + prose |
| **Shared components** | `tag_list`, nav | `page-hero`, `docs-nav`, `version-banner`, `stale-content-banner` | `tag_list`, nav |

Doc is the most componentized; blog and tutorial are more self-contained.

---

## 4. Proposed Vision

### Principles

1. **Unify on shared components** — Use `article_card`, `content_tiles`, `card-base`, or a new `post_card` that wraps them.
2. **Use page-hero for blog** — Blog home and list can use `hero_overview` or a blog-specific hero variant.
3. **Standardize on _path** — All internal links use `_path` (or PostView.path) for static-build portability.
4. **Consolidate CSS** — Blog cards use `.article-card` or `.card` + variants; remove `blog-*` duplicates where possible.
5. **Leverage Kida** — `{% embed %}`, `{% match %}`, `{% cache %}`, template tests.
6. **Feature flags** — Respect `theme.features` (e.g. `content.author`, `content.reading_time`, `content.excerpts`) like article_card does.

### Component Hierarchy (Proposed)

```
partials/components/
├── card-base.html       # {% embed %} base — keep, add blog usage
├── article.html         # article_card() — extend for blog (path, PostView)
├── tiles.html           # content_tiles() — use for blog list optional layout
└── post-card.html       # NEW: post_card(post, variant='default'|'featured'|'compact')
    └── Uses card-base via {% embed %} OR article_card with blog-specific options
```

### Template Changes

| Template | Current | Proposed |
|----------|---------|----------|
| **blog/home.html** | Custom hero, inline post_card, cache | Use `page-hero` (hero_editorial or hero_overview), `post_card(post)` from components, keep `{% cache %}` |
| **blog/list.html** | featured_card, post_card, category_card inline | Use `post_card(post, variant='featured')` and `post_card(post, variant='default')`; category_card → `content_tiles` or new `subsection_card` |
| **blog/single.html** | related_card inline | Use `post_card(post, variant='compact')` from components |
| **authors/single.html** | post_card inline | Use shared `post_card` |
| **tag.html** | article_card | Keep; fix `article.href` → `article._path` in article_card |

### New/Updated Components

1. **post_card(post, variant, show_image, show_excerpt)**  
   - Wraps PostView or raw page.  
   - Variants: `featured`, `default`, `compact`.  
   - Uses `p.path` for links.  
   - Can be implemented via `{% embed 'card-base.html' %}` or by extending `article_card` with a blog mode.

2. **article_card fixes**  
   - Add `path` support (from `article._path ?? article.href`).  
   - Use for tag pages and optionally blog.

3. **content_tiles fixes**  
   - Use `_path` for item links.  
   - Add optional `post_view` mode for blog-style metadata (date, reading time, author).

4. **page-hero blog variant**  
   - `hero_overview` already supports `_posts`, `_subsections`.  
   - Blog home could use it with `hero_style: overview` and pass `posts`/`subsections`.

### CSS Strategy

- Keep `gradient-border`, `fluid-combined`, `fluid-bg` — they're shared.
- Map blog cards to `.article-card` or `.card` + modifier (e.g. `article-card--featured`).
- Add `.blog-*` only for blog-specific layout (e.g. `blog-home-recent`, `blog-posts-grid`).
- Ensure `cards.css` covers blog card variants.

### Migration Path

1. **Phase 1 — Fix links & shared bugs**  
   - Fix `article_card` and `content_tiles` to use `_path`.  
   - Ensure PostView.path is used everywhere.

2. **Phase 2 — Extract post_card**  
   - Create `partials/components/post-card.html` with `post_card(post, variant)`.  
   - Implement via `{% embed 'card-base.html' %}` or by extending article_card.  
   - Swap blog templates to use it.

3. **Phase 3 — Unify hero**  
   - Add blog to page-hero cascade (e.g. `hero_style: overview` for blog home).  
   - Or add `hero_blog` variant.

4. **Phase 4 — Consolidate CSS**  
   - Replace `blog-*-card` with `article-card` + modifiers.  
   - Remove redundant rules.

---

## 5. Open Questions

1. **card-base vs article_card** — Should `post_card` use `{% embed 'card-base.html' %}` (more flexible) or extend `article_card` (simpler)?
2. **content_tiles for blog list** — Can `content_tiles(children=posts, variant='cards')` replace the custom blog grid, or is blog layout too different (featured vs regular, pagination)?
3. **Tutorial alignment** — Should tutorial_card/subsection_card also move to shared components for consistency?
4. **Authors** — authors/single is blog-adjacent; should it live under a `blog/` or `content/` namespace?

---

## 6. Summary

The blog templates are **out of date** relative to:

- New shared components (card-base, article_card, content_tiles, page-hero)
- Kida features (`{% embed %}`, `{% match %}`, template tests)
- Consistent use of `_path` for internal links
- CSS consolidation (article-card, card variants)

The vision is to **refactor blog onto shared components**, adopt **page-hero** where it fits, introduce a **post_card** component, and **standardize links and CSS** while keeping the existing design language (gradient borders, fluid layouts) and dogfooding the default theme's CSS/JS.
