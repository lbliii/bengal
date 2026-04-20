# Epic: Delete Forwarding Wrappers — Site Shrinks Because Its API Shrinks

**Status**: Draft
**Created**: 2026-04-20
**Target**: v0.4.0 (supersedes Sprint B3 of `plan/immutable-floating-sun.md`)
**Dependencies**: B1 (SiteRunner) and B2 (SiteContext) from the prior epic — complete and kept.
**Estimated Effort**: 28–40h
**Source**: Three-subagent audit of `bengal/core/site/`, `bengal/core/page/`, `bengal/core/section/`, and `bengal/orchestration/` on 2026-04-20.

---

## Context

Sprint B3 of the prior epic shrank `bengal/core/site/__init__.py` from 1,649 → 467 LOC by extracting 5 mixin files (`accessors.py`, `data.py`, `discovery.py`, `queries.py`, `validation.py`) and inheriting them on Site via multiple inheritance. This directly reversed a deliberate **10+ commit campaign** culminating in PR #194 (`d536880dc`, 2026-04-06):

> *"Decompose the Site god object from 5 mixins to zero inheritance — all methods inlined into a plain @dataclass."*

Same file names resurrected (`accessors.py`, `discovery.py`), same pattern (mixin inheritance), similar bucket split. Total package LOC grew 1,649 → 1,992; the "≤500 LOC" target was met by relocation, not reduction.

Asking "mixins vs. inlined?" is the wrong question — both are legitimate local optima under different value functions, and the historical oscillation between them is the cost. The right question: **why do these methods exist on Site at all?**

Audit answered: **most of them are vestigial pass-throughs.** When composition services (`ConfigService`, `PageCacheManager`, `ContentRegistry`, `VersionService`) were extracted in prior refactors, the old methods on Site were kept as back-compat wrappers. They were never deleted — B3 then "organized" them into mixins, polishing wrappers that shouldn't exist.

### Evidence Table

| Source | Finding | Proposal Impact |
|---|---|---|
| `bengal/core/site/accessors.py` | 17 properties, all pure `return self.config_service.X` forwarding | FIXES — delete; callers use `site.config_service.X` |
| `bengal/core/site/queries.py` | 5 pure `return self._page_cache.X` forwarders | FIXES — delete; promote `_page_cache` → `page_cache` |
| `bengal/core/site/data.py` | `_load_data_directory` delegates to `scan_data_directory()` | FIXES — inline one call to the service |
| `bengal/core/site/discovery.py` | 1 pure forwarder (`registry`), rest is real logic | PARTIAL — delete forwarder, keep real methods inline on Site |
| `bengal/core/site/validation.py` | Real logic, no pure forwarders | KEEP LOGIC — move back inline on Site (no mixin) |
| `bengal/core/page/__init__.py` | 4 pure forwarders: `relative_path`, `template_name`, `is_virtual`, `prerendered_html` | FIXES — delete; callers use direct attr access |
| `bengal/core/section/queries.py` | 1 pure alias: `sections → subsections` | FIXES — delete alias |
| `bengal/orchestration/*` | No pure forwarders; orchestrators are clean | NO ACTION |
| 10+ commits pre-#194 + PR #194 | Deliberate sustained decision to eliminate mixins | GUARDS — write as durable tenet in CLAUDE.md + import-linter rule |

### Invariants

These hold throughout the epic or we stop and reassess:

1. **Byte-identical build output** on `site/` showcase. Verified by `tests/integration/test_build_snapshot.py` at every sprint boundary.
2. **No new circular imports.** `uv run lint-imports` green on both existing contracts + new Contract 3 (forbids `*Mixin` classes in `bengal/core/`).
3. **No user-facing template API breakage.** `site.title`, `site.baseurl`, `site.pages`, `site.versions`, `section.content_pages`, `section.post_count` — these stay addressable from Kida templates, even if their implementation changes.
4. **Sprint independence.** Each sprint ships value standalone; no sprint leaves the tree partial.

---

## Target Architecture

```
bengal/core/site/
├── __init__.py          # Site: plain @dataclass, NO mixins, ~600–800 LOC.
│                        # Real methods inline (discovery, validation).
│                        # User-facing template properties (title, baseurl, pages) inline.
│                        # Composed services exposed as plain attributes (page_cache, config_service).
├── context.py           # SiteContext Protocol (kept from B2)
├── factory.py           # from_config / for_testing (kept)
├── versioning.py        # VersionService (kept — real composed service)
└── [DELETED]: accessors.py, data.py, discovery.py, queries.py, validation.py

bengal/core/page/__init__.py    # Pure forwarders deleted
bengal/core/section/queries.py  # `sections` alias deleted

# Durable commitments:
.importlinter              # Contract 3: no *Mixin classes in bengal/core/
CLAUDE.md                  # Architectural tenet documented
```

**Site's shape after:**
- Composition services as public attributes: `site.config_service`, `site.page_cache`, `site.registry`, `site.version_service`.
- Methods that do real work stay (discovery, validation, cascade, lifecycle shims to SiteRunner).
- Template-facing aliases for common things stay (`site.title`, `site.baseurl`, `site.pages`) — these are the API contract, not vestigial.
- No mixins. Plain @dataclass. PR #194's decision honored permanently via CLAUDE.md tenet + lint-imports contract.

---

## Sprint Structure

| Sprint | Focus | Effort | Risk | Ships Independently? |
|---|---|---|---|---|
| S0 | Decide public-attribute names; draft CLAUDE.md tenet | 3h | Low | Yes (doc-only) |
| S1 | Delete Site config-accessor wrappers; migrate callers | 10h | Medium | Yes |
| S2 | Delete Site page-cache wrappers; promote `_page_cache` → `page_cache` | 6h | Low | Yes |
| S3 | Delete Page/Section vestigial forwarders | 3h | Low | Yes |
| S4 | Dissolve `discovery.py`, `validation.py`, `data.py` mixins back into Site inline | 8h | Medium | Yes |
| S5 | Add import-linter Contract 3 (no *Mixin in core); commit CLAUDE.md tenet | 2h | Low | Yes |

Total: **32h**. Sprints independent; any can ship standalone.

---

## Sprint S0: Decide + Document

**Goal:** Answer the naming question before moving code; commit the tenet so future sessions don't re-litigate.

### Task S0.1 — Name the public attributes

Decide the exposed names for the 4 composed services currently private on Site:

| Current | Proposed Public | Notes |
|---|---|---|
| `_config_service` | `config_service` | Already accessed in audit-confirmed 403+ sites |
| `_page_cache` | `page_cache` | 77 call sites |
| `_registry` | `registry` (already public as property) | Just delete the lazy-init property; make field public |
| `_version_service` | `version_service` | Used by ~119 template + Python sites |

**Acceptance:** Decision recorded at top of this plan doc.

### Task S0.2 — Write the architectural tenet

Add a section to `CLAUDE.md` (or create `plan/adr-001-site-composition.md`):

> **Site, Page, Section: composition over inheritance, API over vestige.**
>
> - `Site`, `Page`, `Section` are plain `@dataclass` containers. They do not inherit from mixin classes.
> - Functionality is organized by **composed services** (attributes holding a service instance) or **inline methods** that do real work. Never by mixin inheritance.
> - A method on one of these classes that does nothing but `return self._service.X` is **vestigial back-compat** from a prior extraction. Delete it in the same PR as the extraction. If it's reached this codebase as a wrapper, it's a bug to fix, not a structure to preserve.
> - Exception: template-facing API surface (`site.title`, `site.baseurl`, `section.post_count`) may be thin properties, because Kida templates are the API contract.
>
> **Why:** Mixin-vs-inline has been litigated twice (2026-Q1 elimination campaign → PR #194 final cut; Sprint B3 of `immutable-floating-sun` epic restored mixins; this epic eliminated them again). Refactor cost compounds. Pick one and hold.

**Acceptance:** CLAUDE.md contains the tenet; PR description references PR #194 and this epic to make the history visible.

---

## Sprint S1: Delete Config-Accessor Wrappers

**Goal:** Remove the 17 pure forwarders in `accessors.py`. `site.title` → `site.config_service.title`.

### Task S1.1 — Promote `_config_service` → `config_service`

Rename the field on Site and update all `self._config_service` to `self.config_service` inside `bengal/core/site/`.

**Acceptance:** `rg 'self\._config_service' bengal/` returns zero. Existing tests green.

### Task S1.2 — Delete the 17 pure-forwarding properties

From `bengal/core/site/accessors.py`, delete: `paths`, `title`, `baseurl`, `content_dir`, `author`, `favicon`, `logo_image`, `logo_text`, `logo`, `config_hash`, `assets_config`, `build_config`, `i18n_config`, `menu_config`, `content_config`, `output_config`, and others the audit flagged as pure forwarding.

**Keep** (real logic, not forwarders): `description`, `theme_config`, `build_badge`, `document_application`, `link_previews`.

### Task S1.3 — Migrate callers

Ripgrep-driven migration: `rg 'site\.title\b'` → replace with `site.config_service.title`, etc. Scope per audit: ~403 call sites across ~120 files.

**Scope note:** Kida templates access `site.title` from user-authored content. The template API stays — we add back `title`, `baseurl`, `description`, `author` as `@cached_property` on Site (`return self.config_service.X`). These 4 are the template API surface, not vestigial wrappers — they're small, justified, and documented as the surface.

**Acceptance:**
- `rg '@property\s+def title' bengal/core/site/accessors.py` returns zero.
- `bengal build` on `site/` produces byte-identical output.
- Full unit suite green.

### Task S1.4 — Delete `accessors.py` entirely

After S1.2 the file contains only real-logic methods (`description`, `theme_config`, etc.). Move those inline into `bengal/core/site/__init__.py` as plain methods on Site. Delete `accessors.py`. Remove `SiteAccessorsMixin` from Site's class declaration.

**Acceptance:**
- `ls bengal/core/site/accessors.py` → not found.
- `grep SiteAccessorsMixin bengal/core/site/__init__.py` returns zero.

---

## Sprint S2: Delete Page-Cache Wrappers

**Goal:** Remove the 5 pure forwarders in `queries.py`. `site.regular_pages` → `site.page_cache.regular_pages`.

### Task S2.1 — Promote `_page_cache` → `page_cache`

Make the PageCacheManager attribute public.

**Acceptance:** `rg 'self\._page_cache' bengal/` returns zero.

### Task S2.2 — Delete pure forwarders + migrate callers

Delete `regular_pages`, `generated_pages`, `listable_pages`, `page_by_source_path`, `get_page_path_map`. Migrate ~77 call sites to `site.page_cache.X`.

**Keep:** `root_section` (has fallback logic), `invalidate_page_caches()`, `invalidate_regular_pages_cache()` — move inline to Site.

### Task S2.3 — Delete `queries.py`

Remove `SitePageCacheMixin` from Site's class declaration. Move surviving methods (`root_section`, invalidation methods) inline to `bengal/core/site/__init__.py`.

**Acceptance:**
- `ls bengal/core/site/queries.py` → not found.
- Snapshot build byte-identical.

---

## Sprint S3: Delete Page/Section Vestigial Forwarders

**Goal:** Smaller cleanup; same pattern as S1/S2.

### Task S3.1 — Delete Page pure forwarders

From `bengal/core/page/__init__.py`, delete:
- `relative_path` (use `str(page.source_path)`)
- `template_name` (use `page._template_name` or rename field)
- `is_virtual` (use `page._virtual` or rename field)
- `prerendered_html` (use `page._prerendered_html` or rename field)

**Alternative:** promote the underscored fields to public (`page.virtual`, `page.template`, `page.prerendered`) and keep short public names. Decide in S0.

### Task S3.2 — Delete Section alias

From `bengal/core/section/queries.py`, delete `sections` property (alias for `subsections`). Migrate callers to `section.subsections`.

**Acceptance:** `rg '\.sections\b' bengal/ | grep -v subsections` shows no callers hitting the deleted alias. Full suite green.

---

## Sprint S4: Dissolve Remaining Mixins

**Goal:** With `accessors.py` and `queries.py` gone (S1+S2), dissolve the three remaining mixins (`discovery.py`, `validation.py`, `data.py`) back into Site. Plain @dataclass with no mixins.

### Task S4.1 — Inline `data.py`

`_load_data_directory` is 8 lines. Move it inline to `Site.__post_init__`-adjacent logic in `__init__.py`. Delete `data.py` and `SiteDataMixin`.

### Task S4.2 — Inline `validation.py`

Validation methods are real logic but only ~2 public methods. Move them inline to `bengal/core/site/__init__.py`. Delete `validation.py` and `SiteValidationMixin`.

### Task S4.3 — Dissolve `discovery.py`

~448 LOC of real methods (content discovery, asset discovery, section registry build, cascade). Two options:

- **S4.3-Option-A: Inline into Site.** `__init__.py` grows to ~900 LOC. Biggest, but zero indirection. Recommended.
- **S4.3-Option-B: Extract as DiscoveryService composed on Site.** Creates `bengal/core/site/discovery_service.py` with a proper class Site *holds* (not inherits). No MRO. But one more indirection per call.

Decide in S0 based on whether the discovery methods are genuinely cohesive as a service (they're called in sequence by `SiteRunner`) or just a grab-bag.

**Acceptance:**
- `bengal/core/site/` contains only `__init__.py`, `context.py`, `factory.py`, `versioning.py` (+ DiscoveryService if Option B).
- Site's class declaration: `@dataclass class Site:` (no mixin inheritance).
- `rg 'class Site.*Mixin' bengal/` returns zero.
- Snapshot byte-identical.

---

## Sprint S5: Guard Against Regression

**Goal:** Make the decision stick so next year's Claude doesn't revert it again.

### Task S5.1 — Import-linter Contract 3

Add to `.importlinter`:

```ini
[importlinter:contract:no-core-mixins]
name = bengal.core classes must not inherit from *Mixin classes
type = forbidden
source_modules =
    bengal.core
forbidden_modules =
    # Any module defining a class whose name ends in 'Mixin'
# (Represent via a custom checker if import-linter's built-ins can't express
# it directly; otherwise enforce via grep in CI.)
```

If import-linter can't express "class name ends in Mixin", a simpler CI grep suffices:

```bash
! rg 'class \w+Mixin' bengal/core/
```

**Acceptance:** CI fails if anyone adds a `*Mixin` class in `bengal/core/` in the future.

### Task S5.2 — Commit CLAUDE.md tenet

From S0.2. Final merge.

**Acceptance:** `grep -c "composition over inheritance" CLAUDE.md` ≥ 1.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Template breakage from deleting `site.title` etc. | High | High | S1.3 keeps 4 template-facing aliases as thin @cached_property; snapshot test gates every sprint |
| Callers missed by ripgrep (dynamic `getattr`) | Medium | Medium | Full test suite must pass; `bengal build` on showcase + real site (if available) must succeed |
| Discovery inline bloats `__init__.py` to ~900 LOC | Medium | Low | Accept — the audit showed discovery is real logic and cohesive with lifecycle; alternative is DiscoveryService composition (S4.3-Option-B) |
| `_page_cache → page_cache` rename breaks pickling / cached state | Low | Medium | Cache-state test suite catches any serialization drift; migration done in one commit |
| Future Claude reverts this again | Medium | High | S5.1 (import-linter rule) + S5.2 (CLAUDE.md tenet) + PR description naming both prior incidents |

---

## Success Metrics

| Metric | Current (post-B3) | After S3 | After S5 (done) |
|---|---|---|---|
| `bengal/core/site/*.py` total LOC | 1,992 | ~1,600 | ~900 |
| Files in `bengal/core/site/` | 9 | 8 | 4 (+ context.py) |
| Mixins inherited by Site | 5 | 3 | **0** |
| Pure forwarding methods on Site | 22+ | 5 | **0** |
| Pure forwarding methods on Page/Section | 5 | 0 | 0 |
| Template API stability (`site.title` etc. work) | ✓ | ✓ | ✓ |
| Import-linter contracts passing | 2/2 | 2/2 | **3/3** |
| `class *Mixin` count in `bengal/core/` | 5 | 3 | **0** |

---

## Relationship to Existing Work

- **`plan/immutable-floating-sun.md` Sprint B3** — **SUPERSEDED.** B3's tasks (B3.1–B3.5) are reverted by S4 of this epic. B1 (SiteRunner) and B2 (SiteContext) stand; they are real architectural wins.
- **PR #194 (`d536880dc`)** — **HONORED.** This epic's S5 makes PR #194's decision durable via lint-imports + CLAUDE.md.
- **`plan/rfc-site-context-protocol.md`** — **COMPLEMENTARY.** SiteContext stays as the read-only surface for Page/Section.

---

## S0 Decisions (locked)

All decisions driven by one principle:

> **A property on Site / Page / Section is either a WHAT (a genuine domain facet of that entity) or it does not exist.**
> If the property exposes build machinery, routes through a service for convenience, or mirrors internal wiring, it's a HOW — delete it and let callers address the composed service directly.
> The test: would you design this property greenfield, naming it exactly this, given the domain? If no, it's vestige.

### D1 — Public composed-service attribute names

Final names:

| Field | Type | Rationale |
|---|---|---|
| `site.config_service` | `ConfigService` | Clear intent; `config` is already a Site field |
| `site.page_cache` | `PageCacheManager` | Concise; idiomatic Python (attr name ≠ class name) |
| `site.registry` | `ContentRegistry` | Already the public property name |
| `site.version_service` | `VersionService` | Explicit; `versions` stays as template-facing @property |

No abbreviations, no clashes.

### D2 — Which Site properties survive (the WHAT-vs-HOW split)

**SURVIVE** on `Site` (thin `@cached_property` or `@property` — genuine domain API):

| Property | Implementation | Why it's a WHAT |
|---|---|---|
| `title`, `baseurl`, `description`, `author` | `return self.config_service.X` | The site's identity — passes greenfield test |
| `regular_pages`, `generated_pages`, `listable_pages` | `return self.page_cache.X` | Content slices of the site |
| `page_by_source_path` | `return self.page_cache.page_by_source_path` | The site's lookup index |
| `versioning_enabled`, `versions`, `latest_version` | `return self.version_service.X` | The site's version surface (template-heavy) |
| `pages`, `sections`, `assets`, `output_dir`, `theme` | field | What the site *is* |

**DELETE** from `Site` (HOW — implementation leakage):

`paths`, `content_dir`, `assets_config`, `build_config`, `i18n_config`, `menu_config`, `content_config`, `output_config`, `logo_image`, `logo_text`, `favicon`, `logo`, `config_hash`, `get_page_path_map()`.

Callers: `site.config_service.paths`, `site.config_service.assets_config`, `site.page_cache.get_page_path_map()`, etc. The build/orchestration layer knows the service it needs; forwarding through Site obscures that dependency.

**The distinction isn't "no forwarders" — it's "no vestigial forwarders."** A surviving forwarder earns its place by being the domain's correct name at Site's level of abstraction. An internal implementation detail forwarded as convenience is a vestige.

### D3 — Discovery: inline, not extracted as a service

Discovery is a **phase of Site construction**, not an independent service. It mutates Site's fields (populates `pages`, `sections`, `assets`, the registry). A "service" that mutates its owner is a bad abstraction — you'd invent a factory pattern or frozen-record returns to clean it up, which is a separate epic.

**S4.3 → inline.** `Site.__init__.py` grows to ~900 LOC. The growth is honest: Site IS the construction phase. If a future refactor extracts discovery into a pure function returning frozen records (`build_discovery(root_path) -> DiscoveryResult`) and Site consumes the result, that's the correct path forward — but not as a Site-owning-service half-step.

### D4 — Page internal fields: rename to public, delete property wrappers

| Current (property over underscored field) | After |
|---|---|
| `page._virtual` + `page.is_virtual` @property | `page.virtual: bool` (field only) |
| `page._template_name` + `page.template_name` @property | `page.template: str` (field only) |
| `page._prerendered_html` + `page.prerendered_html` @property | `page.prerendered_html: str` (field, no underscore) |
| `page.relative_path` @property (returns `str(source_path)`) | **Delete.** Callers use `str(page.source_path)`. |

No dual naming. No "private field + public wrapper." Fields are either public (API) or private (`_` prefix, not accessed externally). The property wrappers existed because of a past refactor; they're now vestigial.

### D5 — Architectural tenet (for CLAUDE.md + S0.2)

```markdown
## Architecture: Site, Page, Section composition

`Site`, `Page`, `Section` are plain `@dataclass` containers. They do not inherit
from mixin classes. Functionality is organized by:

1. **Composed services** — public attributes holding a service instance
   (`site.config_service`, `site.page_cache`, `site.registry`).
2. **Inline methods** that do real domain work (discovery, validation, lifecycle).
3. **Domain-facet properties** — thin `@property` exposing a genuine facet of the
   entity at the right level of abstraction (`site.title`, `site.regular_pages`,
   `section.content_pages`).

**Forbidden:**
- Mixin inheritance on core types (`class Site(SomeMixin, OtherMixin): ...`).
- Vestigial forwarders — a property whose body is `return self._service.X` and
  whose name is just a convenience rename for internal wiring. If the name
  wouldn't be designed this way greenfield, the property is vestige. Delete it
  in the same PR as the underlying service extraction.

**History:** Mixin-vs-inline was litigated twice before this file was written.
First removal: 2026-Q1 campaign culminating in PR #194 ("eliminate Site mixin
hierarchy"). First revert: Sprint B3 of `plan/immutable-floating-sun.md`.
Second removal: `plan/epic-delete-forwarding-wrappers.md` (this epic). The
decision is now enforced by CI via `.importlinter` Contract 3 — do not re-open.
```

This goes into `CLAUDE.md` at merge-time (S5.2).

---

## Changelog

- 2026-04-20: Initial draft. Supersedes Sprint B3 of `immutable-floating-sun.md`.
