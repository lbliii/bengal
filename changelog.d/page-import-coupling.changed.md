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
