# RFC: SiteContext Protocol — Decoupling Page/Section from Site

**Status**: Draft
**Created**: 2026-04-17
**Epic**: [immutable-floating-sun] Track B Sprint B0
**Supersedes**: Complements `plan/epic-architecture-audit-remediation.md` Tasks 2.1/2.3/4.3
**Dependencies**: Current `bengal/core/site/__init__.py` (1,649 LOC)

---

## Context

`bengal.core.site.Site` is a god object. Audit of `bengal/core/page/` and `bengal/core/section/` showed **14 unique Site attributes/methods** consumed by the inner types. Because Page and Section type-hint `Site` directly, the god object is load-bearing — any decomposition must preserve the exact accessor surface Page/Section rely on.

This RFC settles what that surface is, which pieces belong in a minimal `SiteContext` Protocol vs. a `BuildContext`, and calls out one leaky abstraction (`_page_index_cache`) that should move.

Sprint B1 (SiteRunner extraction) and B2 (SiteContext migration) depend on this doc.

---

## Complete Accessor Audit

All 14 unique accesses from Page/Section to Site. File:line references into the current tree.

### Read-Only Data (belongs in SiteContext)

| # | Access | Source site references | Purpose |
|---|---|---|---|
| 1 | `site.root_path` | `page/__init__.py:314,404,413,599` | Absolute project root; for content-path normalization |
| 2 | `site.output_dir` | `page/metadata.py:290-306` | Where rendered HTML is written; for `_path` computation |
| 3 | `site.config` | `page/metadata.py:591` (via `getattr`) | Access to config dict for content-signal defaults |
| 4 | `site.cascade` | `page/__init__.py:306` (via `getattr`) | CascadeSnapshot for frontmatter inheritance |
| 5 | `site.versioning_enabled` | `section/navigation.py:345` (via `getattr`) | Feature flag for version URL transforms |
| 6 | `site.version_config` | `section/navigation.py:348` (via `getattr`) | Versioning config object |

### Page Collection & Queries (belongs in SiteContext)

| # | Access | Source site references | Purpose |
|---|---|---|---|
| 7 | `site.pages` | `page/navigation.py:33,62,76` | All pages for next/prev navigation |
| 8 | `site.get_section_by_path(path)` | `page/__init__.py:672` | Lookup section from Page's `_section_path` |
| 9 | `site.get_section_by_url(url)` | `page/__init__.py:674` | Lookup section from Page's `_section_url` |
| 10 | `site.get_page_path_map()` | `page/computed.py:341` | Source-path → Page map for series neighbors |
| 11 | `site.indexes` | `page/computed.py:327,331` | Access to computed indexes (series, etc.) |
| 12 | `site.registry.epoch` | `page/__init__.py:655` | Registry version for cache invalidation of `_section` memo |

### Build-Time State (belongs in BuildContext — NOT SiteContext)

| # | Access | Source site references | Purpose |
|---|---|---|---|
| 13 | `site.diagnostics` | `section/__init__.py:132-133` (via `getattr`) | Diagnostic sink for structured warnings during build |

### Leaky Abstraction — Flag For Relocation

| # | Access | Source site references | Purpose |
|---|---|---|---|
| 14 | `site._page_index_cache` | `page/navigation.py:33,34,38` (read + write) | Lazy page→index map, built once per registry epoch, cached on Site |

**Problem**: Page's navigation code writes to `site._page_index_cache`. This is Page using Site as a scratch pad — a classic god-object smell. B2 will **move this cache** to either:
- Option A: A dedicated `PageIndexCache` service owned by the registry (preferred)
- Option B: Keep on Site but expose via `SiteContext.page_index_cache` (accessor protocol) — simpler, still isolates the indirection

Recommendation: **Option A** — move to registry. Page/Section code calls `registry.page_index()` which memoizes internally. Removes the `_private` cross-type attribute write entirely.

---

## Proposed `SiteContext` Protocol

### Single Protocol (Simple) — Recommended

One protocol for now. Splitting into `SiteContext` / `QueryContext` / `BuildContext` adds indirection without clear benefit — Page/Section always receive a Site-like thing that has all of these.

```python
# bengal/core/site/context.py  (new, Sprint B2.1)
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from bengal.core.cascade_snapshot import CascadeSnapshot
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site.versioning import VersionConfig


@runtime_checkable
class SiteContext(Protocol):
    """
    Read-only surface of Site consumed by Page and Section types.

    Page and Section type their `site` field as SiteContext (not Site) so
    they cannot reach into orchestration/server/rendering internals by accident.
    Site itself implements this protocol structurally.

    Evolution rule: new Site attributes DO NOT implicitly join this protocol.
    They must be added here explicitly. This keeps the Page/Section coupling
    surface visible and auditable.
    """

    # --- Read-only configuration ---
    @property
    def root_path(self) -> Path: ...
    @property
    def output_dir(self) -> Path: ...
    @property
    def config(self) -> dict: ...
    @property
    def cascade(self) -> CascadeSnapshot: ...
    @property
    def versioning_enabled(self) -> bool: ...
    @property
    def version_config(self) -> VersionConfig | None: ...

    # --- Page collection & queries ---
    @property
    def pages(self) -> list[Page]: ...
    @property
    def indexes(self) -> object: ...   # Tightly typed in B2; `IndexRegistry` protocol

    def get_section_by_path(self, path: Path) -> Section | None: ...
    def get_section_by_url(self, url: str) -> Section | None: ...
    def get_page_path_map(self) -> dict[Path, Page]: ...

    # --- Registry epoch (for memo invalidation) ---
    @property
    def registry(self) -> RegistryContext: ...


@runtime_checkable
class RegistryContext(Protocol):
    """Minimal registry surface for memo invalidation."""
    @property
    def epoch(self) -> int: ...
    def page_index(self) -> dict[int, int]: ...  # replaces _page_index_cache (see below)
```

### What's Explicitly NOT in SiteContext

- `site.build()`, `site.serve()`, `site.clean()` — moved to `SiteRunner` in B1
- `site.diagnostics` — moved to `BuildContext` (currently only read in Section's `_emit_diagnostic` path, which happens during build)
- `site._page_index_cache` — relocated to `Registry.page_index()` (B2 companion)
- Any internal attribute starting with `_` — private to Site's implementation

### Diagnostics: Inject Instead of Pull

Section's `_emit_diagnostic` currently does:
```python
site = getattr(self, "_site", None)
diagnostics = getattr(site, "diagnostics", None)
if diagnostics: diagnostics.emit(...)
```

This is a build-time concern reaching through Section. B2 migration:
- Section stops looking up diagnostics via `_site`
- Diagnostics is passed via `BuildContext` (thread-local or explicit parameter) to the caller that invokes `_emit_diagnostic`
- If that's invasive, acceptable fallback: keep on SiteContext for now with comment marking it for future removal

---

## Migration Strategy (Sprint B2)

### Ordering

1. **B2.1** — Create `bengal/core/site/context.py` with the Protocol. Site class structurally implements it (no `class Site(SiteContext)` needed — Protocols are duck-typed).
2. **B2.2** — Change Page's `_site: Site | None` → `_site: SiteContext | None` (type hint only). Section same.
3. **B2.3** — Change `page.site` / `section.site` property return types to `SiteContext | None`.
4. **B2.4** — Relocate `_page_index_cache` to `Registry.page_index()`. Update the 3 call sites in `page/navigation.py`.
5. **B2.5** — Import-linter contract: `bengal.core.page.*` and `bengal.core.section.*` may not import `bengal.core.site` (the Site class). Only `bengal.core.site.context` is allowed.

### Back-Compat

- Site class remains public and unchanged in shape during B2. Only Page/Section type annotations change.
- External code that passes a `Site` to Page-consuming functions continues to work (Site is structurally a SiteContext).
- No API break in v0.4.0.

### Test Strategy

- Existing Page/Section tests pass without modification (Protocol is structural).
- Add `tests/unit/core/site/test_site_context_protocol.py` verifying `isinstance(site, SiteContext)` at runtime.
- Import-linter baseline catches any regression introducing new Site accesses.

---

## Metrics & Acceptance

### Acceptance for B0.1 (this RFC)

- [x] Every current `page.site.X` / `section.site.X` access enumerated with file:line
- [x] Each access classified: SiteContext / BuildContext / Relocate
- [x] One `SiteContext` Protocol drafted covering 11 of 14 accesses
- [x] Leaky abstraction (`_page_index_cache`) identified with relocation plan
- [x] Migration ordering specified for B2
- [x] Back-compat strategy documented

### Success Metrics (at end of Track B)

| Metric | Pre-B | Target |
|---|---|---|
| `page.site: Site` type hints | ~9 | 0 (all → `SiteContext`) |
| `section.site: Site` type hints | ~4 | 0 (all → `SiteContext`) |
| Writes to `site._*` from outside Site | 1 (`_page_index_cache`) | 0 |
| Import-linter contract `core.page → site.context only` | violations unknown | passes |
| `bengal/core/page/` + `bengal/core/section/` LOC importing Site | N | 0 (only SiteContext) |

---

## Open Questions

1. **Protocol vs. ABC**: `Protocol` is duck-typed; `ABC` would require `class Site(SiteContext)`. Protocol chosen for flexibility + zero-cost structural typing. Downside: `isinstance(x, SiteContext)` is slower (uses `__subclasshook__`). Acceptable — not in hot paths.

2. **Should `diagnostics` stay on SiteContext?**: Recommendation above is "move to BuildContext," but Section's `_emit_diagnostic` is a single call site and migrating it requires threading BuildContext through Section construction. If B2 scope balloons, leave `diagnostics` on SiteContext and mark for later removal.

3. **`indexes` typing**: Currently `object` in the protocol above. B2 should introduce an `IndexRegistry` protocol (series index, tag index, etc.). Scope for a follow-up if it gets messy.

---

## Changelog

- 2026-04-17: Initial draft.
