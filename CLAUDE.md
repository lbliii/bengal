# CLAUDE.md

Project-specific guidance for AI coding assistants working on Bengal.

## Architecture: Site, Page, Section composition

Bengal favors **composition over inheritance** for its core domain types.

`Site`, `Page`, and `Section` are plain `@dataclass` containers with no core
mixin inheritance. Functionality should be organized by:

1. **Composed services** — public attributes holding a service instance
   (`site.config_service`, `site.page_cache`, `site.registry`).
2. **Inline methods** that do real domain work (discovery, validation, lifecycle).
3. **Domain-facet properties** — thin `@property` exposing a genuine facet of
   the entity at the right level of abstraction (`site.title`, `site.regular_pages`,
   `section.content_pages`).

For `Page`, there is one extra compatibility rule: template-facing properties
may remain on `Page`, but rendering-derived behavior belongs behind helpers in
`bengal/rendering/`. `Page.content`, `Page.html`, `Page.plain_text`,
`Page.toc_items`, `Page.excerpt`, `Page.meta_description`, `Page.href`,
`Page._path`, `Page.absolute_href`, `Page.extract_links()`, and
`Page.HasShortcode()` are compatibility shims, not permission to put parser,
template, shortcode, or URL presentation logic back into core.

`Section` follows the same boundary for theme-facing ergonomics:
`Section.recent_pages()`, `Section.pages_with_tag()`, `Section.featured_posts()`,
section content stats, and section template application are compatibility shims
over `bengal/rendering/section_ergonomics.py`.
Section URL properties (`Section.href`, `Section._path`, `Section.absolute_href`,
subsection index URL sets, and version-path transforms) are compatibility shims
over `bengal/rendering/section_urls.py`.

### Forbidden

- **New mixin inheritance on core types** (`class Site(SomeMixin, OtherMixin): ...`).
  Enforced by `tests/unit/core/test_no_core_mixins.py` — CI fails if a new
  `*Mixin` class is added under `bengal/core/`. The allow-list is empty.
- **Rendering behavior inside core Page** — parser calls, HTML extraction,
  shortcode/link extraction, TOC parsing, excerpt/meta-description derivation,
  and template URL construction belong in rendering-side helpers.
- **Theme ergonomic behavior inside core Section** — rendered-content stats,
  template collection views, and section template application belong in
  `bengal/rendering/section_ergonomics.py`.
- **URL presentation inside core Section** — baseurl/origin application,
  template-ready section paths, subsection index URL sets, and versioned URL
  transforms belong in `bengal/rendering/section_urls.py`.
- **Vestigial forwarders** — a property whose body is `return self._service.X`
  and whose name is just a convenience rename for internal wiring. If the name
  wouldn't be designed this way greenfield, the property is a vestige. Delete
  it in the same PR as the underlying service extraction; migrate callers to
  talk to the composed service directly (`site.config_service.paths`, not
  `site.paths`).

### The greenfield-design test

When evaluating any property or method on a core domain type, ask:

> Would I design this property greenfield, naming it exactly this, given the
> domain model?

- **Yes** → it's a genuine domain facet. Keep it. The fact that it delegates
  to a composed service is an implementation detail, not a smell.
- **No** → it's a vestige from a past service extraction. Delete it and
  migrate callers.

### History (do not re-litigate)

Mixin-vs-inline has been litigated twice before this file existed.

- **First removal** (2026-Q1): 10+ commit campaign culminating in PR #194
  (`d536880dc`, "eliminate Site mixin hierarchy").
- **First revert**: Sprint B3 of `plan/immutable-floating-sun.md` re-introduced
  5 Site mixins for "organization."
- **Second removal**: `plan/epic-delete-forwarding-wrappers.md` (2026-04-20)
  dissolved them again using the greenfield-design test as the decision rule.

The decision is enforced by:

- `tests/unit/core/test_no_core_mixins.py` — blocks new mixins in `bengal/core/`.
- `.importlinter` Contract 2 — Page/Section use `SiteContext` protocol only.
- Page-specific guard tests in `tests/unit/core/test_no_core_mixins.py` — block
  module-level rendering helper imports and parser/text rendering work from
  returning to core Page computed helpers.

Before proposing a mixin split or decomposition on `Site`, `Page`, or `Section`,
read `plan/epic-delete-forwarding-wrappers.md` and run the greenfield-design
test on each method. Decomposition treats the symptom (class is large); the
root cause is usually accumulated wrappers that should be deleted.
