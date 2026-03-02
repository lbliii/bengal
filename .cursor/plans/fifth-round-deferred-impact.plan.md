---
name: ""
overview: ""
todos: []
isProject: false
---

# Fifth-Round: Deferred Items — Impact Analysis & Planning

## Summary

Exploration of deferred items from fourth-round. Each item assessed for scope, effort, and impact. **Top 2 for planning:** BuildContext Any fields, Shortcodes getattr replacement.

---

## 1. BuildContext Any Fields — **HIGH IMPACT** (recommend plan)

**File:** [bengal/orchestration/build_context.py](bengal/orchestration/build_context.py)

**Problem:** Five fields typed as `Any` with lazy-import comments:

- `api_doc_enhancer: Any` (line 204)
- `write_behind: Any` (line 208)
- `snapshot: Any` (line 212)
- `query_service: Any` (line 215)
- `data_service: Any` (line 216)

**Cause:** Circular imports — these types are created/assigned in other modules and imported lazily.

**Impact:**

- **Reach:** BuildContext is passed to build phases, render pipeline, index generator, postprocess. Every consumer of these fields loses type safety.
- **Risk:** Typos, wrong method calls, and refactors go undetected.
- **Architecture:** Central orchestration object; typing it properly improves the whole build pipeline.

**Solution options:**

1. **Protocols:** Define `APIDocEnhancerProtocol`, `WriteBehindProtocol`, etc. in `bengal/protocols/`. Use `X | None` with protocol types.
2. **TYPE_CHECKING imports:** Import concrete types under `if TYPE_CHECKING` and use `X | None` for fields. Lazy assignment stays; type checker gets full info.
3. **Hybrid:** Protocols for public interfaces; `TYPE_CHECKING` for internal types.

**Effort:** ~2–3 hours (protocols + updates to assigners/consumers)

**Recommendation:** Plan this. Highest architectural impact.

---

## 2. Shortcodes getattr Replacement — **HIGH IMPACT** (recommend plan)

**File:** [bengal/rendering/shortcodes.py](bengal/rendering/shortcodes.py)

**Problem:** ~12 `getattr` calls for page/site attributes:

- `xref_index`, `href`, `source_path`, `_source`, `_raw_content` (lines 128, 135, 139–140, 236, 267, 364, 425, 463, 488)

**Cause:** Shortcodes receive `PageLike`/`SiteLike` from various sources (Page, PageProxy, mocks). Protocols may not declare all attributes; callers pass objects with different shapes.

**Impact:**

- **Reach:** Every page using shortcodes (common for Hugo-style sites). Core rendering path.
- **Risk:** Silent fallbacks (`getattr(..., "")`) can hide bugs. Typos in attribute names return defaults.
- **Clarity:** Direct attribute access documents the contract.

**Solution options:**

1. **Extend PageLike/SiteLike:** Add `source_path`, `href`, `_source` (or `raw_content`) to protocols. Ensure Page, PageProxy implement them.
2. **Shortcode-specific protocol:** `ShortcodePageLike` with required attributes. Callers cast or pass only conforming objects.
3. **Helper module:** `bengal.rendering.shortcode_utils` with `get_page_source(page: PageLike) -> str`, etc., using protocol checks + clear errors.

**Effort:** ~1.5–2 hours (protocol updates + shortcodes.py changes)

**Recommendation:** Plan this. High usage, clear path to fix.

---

## 3. BuildTrigger getattr Replacement — **MEDIUM–HIGH IMPACT**

**Files:** [bengal/server/build_trigger.py](bengal/server/build_trigger.py), [dev_server.py](bengal/server/dev_server.py), [build_executor.py](bengal/server/build_executor.py)

**Problem:** ~20+ `getattr` calls for `site` and `stats`:

- Site: `config`, `versioning_enabled`, `version_config`, `root_path`, `theme`, `_cache` (build_trigger.py: 297, 631, 660, 663, 890, 932, 943, 978, 987)
- Stats: `reload_hint`, `pages_rebuilt` (build_trigger.py: 429; dev_server: 417; build_executor: 189)

**Cause:**

- `site: Any` — BuildTrigger accepts any site-like object for tests/mocks.
- `stats` — Can be full BuildStats (has `reload_hint`) or MinimalStats (does not). DisplayableStats protocol omits `reload_hint` and `pages_rebuilt`.

**Impact:**

- **Reach:** Dev server rebuild pipeline. Critical for `bengal s` experience.
- **Risk:** Medium — server code is well-tested; getattr is defensive for MinimalStats.

**Solution options:**

1. **SiteLike:** Type `site: SiteLike`. Ensure protocol has `config`, `root_path`, `theme`, `versioning_enabled`, `version_config`, `_cache`. May need protocol extension.
2. **Stats protocol:** Add `reload_hint: ReloadHint | None` and `pages_rebuilt: int` to DisplayableStats. Add to MinimalStats with defaults.
3. **BuildTriggerSite protocol:** Narrow protocol for what BuildTrigger needs.

**Effort:** ~2 hours (protocol extensions + server module updates)

**Recommendation:** Plan after BuildContext and Shortcodes. Good impact, more moving parts (SiteLike is shared).

---

## 4. Optional Imports (typer, smartcrop, rosettes) — **LOW IMPACT**

**Pattern:** `try: import X except ImportError:` for optional dependencies.

**Locations:**

- typer: CLI (optional alternative to click)
- smartcrop: Image cropping (optional extra)
- rosettes: Syntax highlighting — **now a core dep** in pyproject.toml; "optional" may be outdated

**Impact:** Low. Optional imports are standard; type checker can't see inside try/except. Usually addressed with `TYPE_CHECKING` or leaving as-is.

**Recommendation:** Defer. Not worth planning unless rosettes is still conditionally imported somewhere.

---

## 5. Kida Protocol Self-Check — **LOW IMPACT** (uncertain)

**Context:** "Kida protocol self-check" from deferred list. No direct `isinstance(..., TemplateEnvironment)` found. May refer to:

- Runtime protocol verification for Kida's Environment
- Or a check that fails when Kida isn't installed

**Current state:** Block cache uses `engine.has_capability(EngineCapability.BLOCK_CACHING)` rather than protocol isinstance. Template engine selection is via `create_engine()`.

**Recommendation:** Defer until we have a concrete bug or requirement. Scope unclear.

---

## Implementation Order (Recommended)


| #   | Task                    | Impact   | Effort  | Notes                       |
| --- | ----------------------- | -------- | ------- | --------------------------- |
| 1   | BuildContext Any fields | High     | 2–3 h   | Protocols + TYPE_CHECKING   |
| 2   | Shortcodes getattr      | High     | 1.5–2 h | Extend PageLike/SiteLike    |
| 3   | BuildTrigger getattr    | Med–High | 2 h     | SiteLike + DisplayableStats |
| 4   | Optional imports        | Low      | —       | Defer                       |
| 5   | Kida protocol           | Low      | —       | Defer (scope unclear)       |


---

## Next Steps

1. **Create RFC/plan** for BuildContext typing (protocols for api_doc_enhancer, write_behind, snapshot, query_service, data_service).
2. **Create plan** for Shortcodes: audit PageLike/SiteLike, add missing attributes, replace getattr with direct access.
3. **Queue** BuildTrigger after 1–2 are done.
