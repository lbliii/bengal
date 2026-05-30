Retire the public `bengal.Page` and `bengal.core.Page` compatibility re-exports
plus the `Page.create_virtual()` compatibility constructor, and reduce internal
concrete `Page` coupling by routing page construction through page-like records
and the remaining SourcePage adapter boundary. Discovery now resolves i18n
metadata before creating `SourcePage` records instead of mutating adapted pages
afterward. Non-compatibility tests no longer use local `Page`-named doubles that
obscure the remaining production adapter/class boundary. The remaining adapter
now lazy-loads the legacy class so importing content discovery helpers does not
load `bengal.core.page`. Tests now import Page submodules directly and guard
against new package-root imports from `bengal.core.page`. Raw source access now
flows through a content-owned helper instead of requiring `_source` on the
`PageLike` protocol. Section access now flows through core section helpers
instead of requiring `_section` on `PageLike`, and directive link collection now
flows through rendering helpers instead of requiring `_directive_links`.
Parsed content caches now stay out of `PageLike`; AST, TOC, excerpt, and meta
description state are handled by compatibility/cache helpers while the legacy
mutable page adapter remains.
Section archive context now stays out of `PageLike`; existing section indexes
receive `_posts`, `_subsections`, `_paginator`, and `_page_num` through metadata
instead of mutable page slots.
Autodoc fallback tagging now stays out of `PageLike`; fallback template markers
are recorded through metadata instead of mutable page slots.
Pre-rendered virtual page HTML now stays out of `PageLike`; rendering helpers
own access to `prerendered_html` while the legacy mutable page adapter remains.
Legacy mutable page site context now stays out of `PageLike`; content discovery
and orchestration use page-site helpers while the compatibility adapter remains.
Analysis graph tests now use hashable page-like mocks instead of constructing
legacy mutable pages for graph-only behavior.
Cache query-index tests now use page-like fixtures instead of constructing
legacy mutable pages for index-only behavior.
Content-type, related-posts, and taxonomy-incremental orchestration tests now
use hashable page-like mocks instead of constructing legacy mutable pages.
Redirect postprocess tests now use local page-like fixtures instead of
constructing legacy mutable pages for alias behavior.
Render, taxonomy, section, and incremental orchestration tests now use the
shared page-like mock instead of constructing legacy mutable pages for
orchestrator inputs.
Nav-tree tests now use the shared page-like mock instead of constructing legacy
mutable pages for navigation behavior.
Section sorting, hashability, index-collision, page-like input, and versioning
tests now use shared page-like mocks instead of constructing legacy mutable
pages for hierarchy behavior.
Cascade and cascade-snapshot tests now use shared page-like mocks instead of
constructing legacy mutable pages for section cascade behavior.
Section ergonomic helper tests now use shared page-like mocks instead of
constructing legacy mutable pages for recent-page, content-page, and
tag-listing behavior.
Page visibility logic now has Page-package-independent helpers used by core
page caches and visibility tests, reducing dependence on legacy Page visibility
properties.
Page visibility tests now use shared page-like mocks and the visibility helper
API instead of constructing the legacy mutable Page adapter.
Href and section page URL tests now use shared page-like URL mocks backed by
rendering URL helpers instead of constructing the legacy mutable Page adapter.
Page URL cache-regression tests now assert the rendering URL helper cache names
through the shared page-like URL mock instead of constructing the legacy mutable
Page adapter.
The standalone section-navigation edge case now exercises navigation helpers
with a shared page-like mock instead of constructing the legacy mutable Page
adapter.
Navigation tests now build breadcrumb and parent assertions through section and
page navigation helpers with shared page-like mocks instead of constructing the
legacy mutable Page adapter.
Component model metadata-normalization tests now exercise `build_page_core()`
directly instead of constructing the legacy mutable Page adapter.
Computed page metadata tests no longer duplicate age, author, and series helper
coverage through the legacy mutable Page adapter.
Page metadata helper tests now cover generated, assigned-template,
content-type, and variant behavior through metadata helpers instead of the
legacy mutable Page adapter.
Page record migration tests now use the canonical SourcePage-backed test-page
adapter for bridge-retirement coverage instead of constructing the legacy
mutable Page adapter directly.
Hashability and deduplication tests now use source-path-hashable page-like
mocks instead of constructing the legacy mutable Page adapter for set and dict
identity behavior.
Obsolete legacy Page cached-property tests were removed; raw source,
word-count, reading-time, meta-description, and excerpt behavior is covered by
the content, computed-function, and rendering helper tests.
Obsolete legacy Page section-reference tests were removed; section helper,
registry, and virtual-section behavior is covered outside the mutable Page
descriptor surface.
PageInitializer tests now build pages through the canonical SourcePage-backed
test-page adapter instead of legacy mutable Page constructor keyword names.
Frontmatter integration tests now build pages through the canonical
SourcePage-backed test-page adapter, leaving the legacy mutable test-page
factory isolated to the shared compatibility helper.
The unused legacy mutable test-page factory was removed; tests now use
SourcePage-backed helpers or page-like mocks.
Production `page_from_source_page()` now returns a SourcePage-backed
`RuntimePage` from the core page compatibility boundary instead of constructing
the legacy mutable `Page` class.
The legacy mutable `Page` class module, `bengal.core.page.legacy`, has been
deleted; `bengal.core.page` remains a helper package and does not export
`Page`.
