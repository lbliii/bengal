# Plan: Foundation Leaf Hygiene — `utils/primitives` + `utils/concurrency`

**Status**: Draft
**Created**: 2026-04-20
**Target**: v0.4.0 (opportunistic; no blocking dependencies)
**Dependencies**: None
**Estimated Effort**: 8–14h (excluding optional Sprint 3 split)
**Source**: 4-lens layered review of 14 foundational leaf files on 2026-04-20 — `.context/layered-review-foundation-leaves.md`

---

## Context

The 14 files in `bengal/utils/primitives/` (8) and `bengal/utils/concurrency/` (6) are **dependency-graph leaves** — they import nothing from `bengal.*`. They are the bedrock everything else depends on, called from rendering, parsing, and build hot paths. Per-call inefficiencies multiply across thousands of callers.

A four-lens audit (Architecture / Flow / Interaction / Micro) surfaced **16 actionable findings**: 2 Tier-1, 6 Tier-2, 8 Tier-3. Three false positives (PEP 758 `except A, B:` mis-flagged as Python 2) were filtered using project memory.

**Cross-layer signal converged on three files:**
- `text.py` (681 LOC) — flagged by all 4 layers; mixed responsibilities, redundant work in `truncate_words`/`generate_excerpt`.
- `dates.py` — `parse_date` rebuilds an 8-format list on every call; `date_range_overlap` parses 4 dates redundantly.
- `dotdict.py` — `__getattribute__` returns `""` for misses (breaks `hasattr`/`getattr` contract); `from_dict` eager-wraps despite lazy `__getattribute__`.

The remainder are localized cleanups (dead code in `retry.py`, lazy-init globals not lock-guarded in `async_compat.py`, etc.).

This plan is **utility-tier hygiene, not architectural refactor.** No core types change. No public API renames. The Tier-1 wins are 2-line patches.

---

## Evidence Table

| Audit Finding | File:Line | Sprint | Reason |
|---|---|---|---|
| `default_formats` rebuilt per call | `dates.py:79-88` | 1 | Hot path; 2-line fix |
| `truncate_words` joins same slice 2× | `text.py:282-285` | 1 | Verified by direct read; safe |
| Unreachable code after `for` loop | `retry.py:130-134` | 1 | Dead-code removal |
| Backoff calc on final attempt | `retry.py:115` | 1 | Branch-predictable; trivial |
| `reduce(λ a,b: a\|b, args)` | `types.py:160` | 1 | `Union[*args]` is clearer |
| `unicodedata` local import | `text.py:158` | 1 | Style consistency |
| `dotdict.__getattribute__` returns `""` for miss | `dotdict.py:74-79` | 0 → 2 | **Design Q first**: contract or feature? |
| `dotdict.from_dict` eager wrap | `dotdict.py:216-229` | 0 → 2 | **Design Q first**: type stability concern? |
| `lru_cache.get_or_set` duplicate TTL paths | `lru_cache.py:156-203` | 2 | Refactor under existing tests |
| `hash_dict` re-runs `json.dumps` | `hashing.py:115` | 2 | Only if benchmarks justify memo |
| `text.py` mixes 6 concerns (681 LOC) | `text.py:*` | 0 → 3 | **Design Q first**: split worth churn? |
| `generate_excerpt` chains `strip_html`+`truncate_words` | `text.py:389-392` | 3 | Bundle with split if it happens |
| `dotdict` cache-lookup duplicated | `dotdict.py:107-152` | 2 | Helper extract; small |
| `thread_local.py` builds cache_key 3× | `thread_local.py:100-104` | 4 | Free-threading polish bucket |
| `async_compat.py` lazy-init not lock-guarded | `async_compat.py:39-56` | 4 | Matters under Python 3.14 free-threading |
| `code.py` parse_hl_lines small-N sort | `code.py:82` | — | Non-issue; documented in audit, no action |

---

## Invariants

These hold throughout the plan or we stop and reassess:

1. **No caller-observable behavior change** outside Sprint 0 design decisions. The full test suite (`uv run pytest`) is green at every sprint boundary.
2. **No new circular imports.** `uv run lint-imports` green at every sprint boundary.
3. **ty diagnostic floor preserved.** Diagnostic count ≤ 1913 (current floor per project memory). Anything new must be a known ty limitation.
4. **Sprint independence.** Each sprint ships value standalone. Sprint 1 alone closes the audit's "low-risk PR" recommendation; later sprints are additive.

---

## Sprint 0 — Design Questions on Paper (no code)

Three questions block Sprint 2 and Sprint 3. Resolve before writing patches.

**Status: Resolved 2026-04-20.** Evidence summarized below; full investigation in PR notes.

### Q1: Is `DotDict.__getattribute__` returning `""` for missing keys intentional?

**Decision: Option A — intentional. Keep behavior. Fix downstream misuse + docstring drift.**

**Evidence:**

- `tests/unit/utils/test_dotdict.py:23-27, 145, 328, 379-393` — explicit assertions that miss returns `""`; tests encode this as the contract.
- `bengal/themes/default/templates/SAFE_PATTERNS.md` — documents the intentional pattern (`{{ resume.name or page.title }}`) that depends on `""`-falsy chaining.
- `bengal/themes/default/templates/.../track-helpers.html:105` (and similar) — template uses `{% if site.data.tracks and ... %}` relying on `""` falsy semantics.
- `bengal/rendering/context/data_wrappers.py:119-122` — `ParamsContext` uses the same `""`-on-miss pattern; the dotdict docstring's "consistent with ParamsContext" claim is accurate.

**Bugs layered on top of correct design (move to Sprint 2):**

1. `bengal/utils/primitives/dotdict.py:89` — docstring says "we return None" but code returns `""`. Docstring drift.
2. `bengal/orchestration/menu.py:278, 809` and `bengal/health/validators/tracks.py:40` — use `hasattr(site.data, key)` to gate behavior, but `hasattr` is **always True** on `DotDict`. These checks are no-ops; they should be `key in site.data` or `bool(site.data.get(key))`.

**Why:** Templates are the load-bearing consumer. Switching to `AttributeError` on miss would force every template to add `is defined` guards — high churn for no template-author benefit. The bug isn't the design; it's downstream code that misread the design.

**Confidence:** High.

### Q2: Should `DotDict.from_dict` stop eagerly wrapping nested dicts/lists?

**Decision: Option C — keep eager wrap. Document why in module docstring.**

**Evidence:**

- `bengal/utils/primitives/dotdict.py:102-113` — `__getattribute__` lazy-wraps top-level dict *values*, but does NOT recurse into list elements. So `wrap_data({"team": [{"name": "..."}, ...]}).team[0].name` would fail without eager wrap.
- `bengal/themes/default/templates/partials/track_nav.html:5-6` — iterates `site.data.tracks | items` and accesses `track.title`, `track.items` on dict-in-list elements. Only works because `from_dict` pre-wraps list items.
- `tests/unit/utils/test_dotdict.py:228-232` — `assert isinstance(data.users[0], DotDict)` after `from_dict`. Encodes the contract.
- `tests/unit/utils/test_dotdict.py:294-295, 411-415` — `wrap_data` and template-simulation tests assert wrapped list items.
- `bengal/core/site/__init__.py:213` — `self.data = wrap_data(data_dict)` is the production caller that templates consume.

**Why:** The lazy wrap path doesn't cover dict-in-list, which templates exercise. Going shallow would silently break templates that iterate lists of dicts. Extending lazy wrap to list elements would add complexity (list-element cache invalidation, mutation hooks) that is more cost than the saved work for the eager-wrap-of-cold-keys case. Sprint 2 will add a one-line comment in `from_dict` referencing this decision.

**Confidence:** High.

### Q3: Is splitting `text.py` worth the churn?

**Decision: Option A — keep monolithic. Add docstring section headers. Skip Sprint 3.**

**Evidence (importer count per proposed split):**

| Function group | Proposed module | Direct importers | Notes |
|---|---|---|---|
| `humanize_bytes` | `humanize.py` | 1 | `rendering/template_functions/strings.py` |
| `humanize_number`, `humanize_slug` | `humanize.py` | 0 direct | re-exported via `bengal/utils/primitives/__init__.py` only |
| `pluralize` | `humanize.py` | 2 | `rendering/template_functions/strings.py`, `rendering/engines/kida.py` |
| `format_path_for_display` | `paths/display.py` | 2 | `core/page/__init__.py`, `orchestration/stats/models.py` |
| HTML / truncate / slugify / excerpt | stays in `text.py` | ~19 | scattered across directives, parsing, rendering |

- Bengal forbids re-export shims (per AGENTS.md). Every importer must update by hand.
- The file has been actively edited recently (Sprint 1 refactor 2026-04-20; taxonomy consolidation 2026-04-02). Splitting now risks rebase friction.
- `bengal/utils/paths/` does not exist as a subpackage; splitting also costs subpackage creation and `__init__.py` plumbing.

**Why:** All ~10 public functions in `text.py` serve text *transformation* or *presentation*. The 6-concern grouping is real but cohesive. The benefit of split (clearer module boundaries) is not worth the migration cost given how few real importers the movable groups have, the no-shim rule, and active churn on the file. Sprint 2 will add docstring section headers (`# --- Humanize ---`, etc.) to make the internal grouping discoverable without churning callers.

**Confidence:** Medium-High. Revisit if a future audit finds `text.py` growing past ~900 LOC or if a humanize function gains many new callers that would justify a dedicated module.

**Effort actual:** ~2h (three parallel Explore agents + synthesis).

---

## Sprint 1 — Quick Wins (single PR, ~20 LOC)

Bundle six low-risk patches from the audit's "clean win" recommendation.

| # | File:Line | Change |
|---|---|---|
| 1 | `dates.py:79-88` | Hoist `default_formats` to module-level `_DEFAULT_DATE_FORMATS` tuple. |
| 2 | `text.py:282-285` | Compute `before_suffix` once; reuse. |
| 3 | `retry.py:130-134` | Delete unreachable post-loop block. |
| 4 | `retry.py:115` | Skip backoff calculation when `attempt == retries`. |
| 5 | `types.py:160` | Replace `reduce(lambda a,b: a\|b, args)` with `Union[*args]`. |
| 6 | `text.py:158` | Move `import unicodedata` to module top. |

**Acceptance:**
- `uv run pytest tests/unit/utils/` passes.
- `uv run pytest` full suite passes.
- `uv run lint-imports` green.
- `rg "default_formats = \[" bengal/utils/primitives/dates.py` returns zero hits inside `parse_date`.
- `rg "reduce\(lambda" bengal/utils/primitives/types.py` returns zero hits.
- One PR, six commits or one squashed commit per maintainer preference.

**Effort:** 2–3h.

**Ships independently:** Yes.

---

## Sprint 2 — Medium Fixes (Sprint 0 decisions baked in)

| # | File:Line | Change |
|---|---|---|
| 1 | `dotdict.py:89` | Q1 follow-up: fix docstring drift — replace "we return None instead of raising AttributeError" with the actual contract ("we return `''` for Jinja2 falsy-chain ergonomics"). |
| 2 | `orchestration/menu.py:278, 809` and `health/validators/tracks.py:40` | Q1 follow-up: replace `hasattr(site.data, key)` with `key in site.data` (or `bool(site.data.get(key))` where the value's truthiness matters). `hasattr` on a `DotDict` is always True, so these checks are no-ops today. |
| 3 | `dotdict.py:204-229` | Q2 follow-up: add a one-line comment above `from_dict` referencing the Sprint 0 decision (eager wrap is required because lazy wrap-on-access doesn't cover dict-in-list — see plan Q2). |
| 4 | `dotdict.py:107-152` | Extract `_get_cached_wrapped_value(key)` helper to dedupe the cache-wrap branch shared by `__getattribute__` and `__getitem__`. Mechanical refactor; no contract change. |
| 5 | `text.py` | Q3 follow-up: add docstring section headers (`# --- Humanize ---`, `# --- HTML ---`, `# --- Slugify ---`, `# --- Truncation ---`, `# --- Excerpt ---`, `# --- Path display ---`) so the 6-concern grouping is discoverable without splitting the module. |
| 6 | `lru_cache.py:156-203` | Consolidate `get_or_set` duplicate TTL check paths into single critical section. |
| 7 | `hashing.py:115` | **Conditional**: profile `hash_dict` callers; add memo only if benchmark shows >5% wall-clock win on a representative build. |

**Acceptance:**
- All Sprint 1 acceptance gates still hold.
- Sprint 0 decisions cited in commit messages for items 1–3, 5.
- `rg "hasattr\(.*\.data" bengal/` returns zero hits in `orchestration/` and `health/validators/`.
- If `hash_dict` change ships, `benchmarks/` shows the wall-clock delta.

**Effort:** 4–5h.

**Ships independently:** Yes. Items 1–3 + 5 are doc/comment/grep-replace and could split into a tiny PR if the helper extract or `lru_cache` work blocks.

---

## Sprint 3 — `text.py` Decomposition

**Status: Skipped.** Q3 resolved to Option A (keep monolithic). Section headers will be added in Sprint 2 item 5 instead.

The `generate_excerpt` fusion (`text.py:389-392`) flagged in the audit is moved to Sprint 4 as a free-threading-adjacent micro-opt, since we're no longer bundling it with a structural split.

---

## Sprint 4 — Free-Threading Polish + Bundled Micro-Opts

Targets only matter under Python 3.14 free-threaded builds (1, 2), or are cheap micro-opts that lost their bundling vehicle when Sprint 3 was skipped (3).

| # | File:Line | Change |
|---|---|---|
| 1 | `async_compat.py:39-56` | Wrap `_uvloop_checked` lazy init in `threading.Lock` or `functools.cache` on a getter. |
| 2 | `thread_local.py:100-104` | Bind `cache_key` once at the top of `get()`. |
| 3 | `text.py:389-392` (`generate_excerpt`) | Inline the `strip_html` + `truncate_words` chain to avoid double-traversal of long markdown bodies. |

**Acceptance:**
- `uv run pytest` full suite passes on both default and `--gil=0` invocations (if local Python 3.14t available).
- No regression in `benchmarks/` concurrency benchmarks.

**Effort:** 1–2h.

**Ships independently:** Yes.

---

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| ~~Sprint 0 Q1 decision (DotDict miss → `""`) is "bug", but downstream templates rely on it~~ | ~~High~~ | **Resolved Sprint 0:** Q1 = Option A (intentional). Templates and SAFE_PATTERNS rely on `""`-falsy chaining. Sprint 2 fixes the docstring drift + `hasattr` misuse downstream, not the `DotDict` contract. |
| ~~`text.py` split churns active rebases on the file~~ | ~~Medium~~ | **Resolved Sprint 0:** Q3 = Option A (keep monolithic). Risk neutralized; section headers added in Sprint 2 instead. |
| Sprint 2 `hasattr → in` migration in `menu.py`/`tracks.py` changes runtime behavior in subtle ways (since `hasattr` was always True, replacing with `in` may now skip code paths that were silently entering them) | Medium | For each call site, read the surrounding code to confirm what should happen when the key is *truly* missing. If the previous always-True behavior was masking a missing-data bug, the fix is the goal — but call out the change in the PR body and add tests for the missing-data branch. |
| `hash_dict` memoization adds correctness bug (mutable dict reused) | Medium | Sprint 2 #7 is gated on benchmark justification; if shipped, memo key is the serialized form, not the dict identity. |
| ~~Sprint 1 `Union[*args]` change breaks ty inference~~ | ~~Low~~ | **Resolved Sprint 1:** S1.5 was deferred (Ruff UP007 rejects the runtime form); current `reduce(lambda)` retained. Risk neutralized. |
| ~~`retry.py` dead-code removal hides a real bug (unreachable was defensive)~~ | ~~Low~~ | **Resolved Sprint 1:** Verified loop invariant before deletion (`range(retries+1)` always yields ≥1 iteration; body returns or raises). Sentinel `AssertionError` retained in case the invariant ever breaks. |

---

## Success Metrics

| Metric | Current | After Sprint 1 | After Sprint 2 | After Sprint 4 |
|---|---|---|---|---|
| Audit Tier-1 findings open | 2 | 1 (text.py split closed as A) | 0 | 0 |
| Audit Tier-2 findings open | 6 | 5 | 1 (`hash_dict` if benchmark justifies) | 0 |
| Audit Tier-3 findings open | 8 | 4 | 2 | 0 |
| `text.py` LOC | 681 | 678 | 678 + section headers | 678 |
| `parse_date` per-call list allocation | Yes | No | No | No |
| Stale `hasattr(site.data, x)` no-ops | 3 | 3 | 0 | 0 |
| `DotDict` docstring drift (line 89) | 1 | 1 | 0 | 0 |
| Free-threading lazy-init races in `bengal/utils/concurrency/` | 1 | 1 | 1 | 0 |

---

## Out of Scope

- **Other leaf clusters.** `parsing/` (15 leaves), `rendering/` (15 leaves), `cli/` (13 leaves) deserve their own audits; not bundled here.
- **The orphan `bengal/concurrency.py`** at the package root. Worth a separate question: does it belong under `utils/concurrency/`? Not in this plan.
- **New abstractions or service extractions.** Per CLAUDE.md: don't decompose unless wrappers are deleted first. These are leaves, so the rule doesn't apply directly, but the spirit (avoid premature abstraction) rules out introducing new helpers.
- **Documentation churn.** Docstrings updated only where they're load-bearing for the change.
