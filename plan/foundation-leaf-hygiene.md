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

### Q1: Is `DotDict.__getattribute__` returning `""` for missing keys intentional?

**Why it matters:** Returning `""` instead of raising `AttributeError` breaks `hasattr(d, "x")` (always True) and `getattr(d, "x", default)` (never returns `default`). This may be deliberate to make Jinja2 templates render gracefully on missing frontmatter — or it may be an old bug.

**Inputs:** `git log` on `dotdict.py`; grep for `DotDict` template usage; check Kida template tests.

**Outputs:**
- **Option A — intentional:** Document as deviation in module docstring with rationale; close finding.
- **Option B — bug:** Switch to `__getattr__` (only called on miss) raising `AttributeError`. Audit downstream callers for breakage.

**Acceptance:** ADR-style decision recorded in `plan/foundation-leaf-hygiene.md` (this file) with chosen option and grep-verifiable scope of impact.

### Q2: Should `DotDict.from_dict` stop eagerly wrapping nested dicts/lists?

**Why it matters:** `__getattribute__` already wraps lazily on access. Eager wrap in `from_dict` is wasted work for keys never read — but may exist for type-stability of callers expecting `DotDict` instances inside lists.

**Inputs:** Grep for `from_dict` callers; check if any do `isinstance(item, DotDict)` on nested values.

**Outputs:**
- **Option A — keep eager:** Document why (type-stability for caller X).
- **Option B — go lazy:** Make `from_dict` shallow; lazy wrap propagates.

**Acceptance:** Decision recorded; if Option B, benchmark page-data load to confirm no regression.

### Q3: Is splitting `text.py` worth the churn?

**Why it matters:** 681 LOC, 6 distinct concerns. Layer 1 flagged it. But splitting churns ~20 importers; the file is also already in active use. May be lower-leverage than other work.

**Inputs:** Grep importers of each function group: `humanize_*`, `format_path_for_display`, `slugify*`, HTML helpers.

**Outputs:**
- **Option A — keep monolithic:** Add docstring section headers; close finding as "accepted technical debt with rationale."
- **Option B — split:** Define new module names + migration. Schedule Sprint 3.

**Acceptance:** Decision recorded; if Option B, target module names listed and importer count enumerated.

**Effort:** 1–2h total for all three Q's.

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

## Sprint 2 — Medium Fixes (depends on Sprint 0 Q1, Q2)

| # | File:Line | Change | Depends on |
|---|---|---|---|
| 1 | `dotdict.py:74-79` | Apply Sprint 0 Q1 decision (document or refactor to `__getattr__`). | Q1 |
| 2 | `dotdict.py:216-229` | Apply Sprint 0 Q2 decision. | Q2 |
| 3 | `dotdict.py:107-152` | Extract `_get_cached_value(key)` helper to dedupe `__getattribute__`/`__getitem__`. | — |
| 4 | `lru_cache.py:156-203` | Consolidate `get_or_set` duplicate TTL check paths into single critical section. | — |
| 5 | `hashing.py:115` | **Conditional**: profile `hash_dict` callers; add memo only if benchmark shows >5% wall-clock win on a representative build. | Benchmark first |

**Acceptance:**
- All Sprint 1 acceptance gates still hold.
- Sprint 0 decisions cited in commit messages.
- If `hash_dict` change ships, `benchmarks/` shows the wall-clock delta.

**Effort:** 4–6h depending on Q1/Q2 outcomes.

**Ships independently:** Yes.

---

## Sprint 3 — `text.py` Decomposition (only if Sprint 0 Q3 = Option B)

If Q3 chose to split, execute the decomposition; otherwise skip this sprint entirely.

**Scope (tentative, Q3 finalizes):**
- `bengal/utils/primitives/humanize.py` — `humanize_bytes`, `humanize_number`, `humanize_slug`, `pluralize`.
- `bengal/utils/paths/display.py` — `format_path_for_display`.
- `text.py` retains: HTML escape/unescape, truncation, slugify, excerpt, `_strip_trailing_orphan_markdown`.
- Bundle the `generate_excerpt` fusion (`text.py:389-392`) since we're already touching the file.

**Acceptance:**
- All importers updated; `rg "from bengal.utils.primitives.text import" bengal/` lists only retained symbols.
- `text.py` LOC drops by ≥150.
- Re-export shims **not** added (per AGENTS.md guidance against backwards-compat hacks).
- Full suite green.

**Effort:** 3–5h.

**Ships independently:** Yes (skipped entirely if Q3 = A).

---

## Sprint 4 — Free-Threading Polish

Targets only matter under Python 3.14 free-threaded builds, but are cheap.

| # | File:Line | Change |
|---|---|---|
| 1 | `async_compat.py:39-56` | Wrap `_uvloop_checked` lazy init in `threading.Lock` or `functools.cache` on a getter. |
| 2 | `thread_local.py:100-104` | Bind `cache_key` once at the top of `get()`. |

**Acceptance:**
- `uv run pytest` full suite passes on both default and `--gil=0` invocations (if local Python 3.14t available).
- No regression in `benchmarks/` concurrency benchmarks.

**Effort:** 1–2h.

**Ships independently:** Yes.

---

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Sprint 0 Q1 decision (DotDict miss → `""`) is "bug", but downstream templates rely on it | High | Sprint 0 Q1 explicitly enumerates downstream callers via grep before changing; if any rely on it, choose Option A and document. |
| `hash_dict` memoization adds correctness bug (mutable dict reused) | Medium | Sprint 2 #5 is gated on benchmark justification; if shipped, memo key is the serialized form, not the dict identity. |
| `text.py` split churns active rebases on the file | Medium | Sprint 3 is opt-in via Q3; if multiple feature branches touch `text.py`, defer Sprint 3 to a quiet window. |
| Sprint 1 `Union[*args]` change breaks ty inference | Low | Run `uv run ty check` at Sprint 1 boundary; if diagnostics rise above 1913 floor, revert that one item. |
| `retry.py` dead-code removal hides a real bug (unreachable was defensive) | Low | Audit `git log` of `retry.py` for the "unreachable" block's history before deleting; if added defensively, leave a short comment explaining why we trust the loop's termination. |

---

## Success Metrics

| Metric | Current | After Sprint 1 | After Sprint 2 | After Sprint 4 |
|---|---|---|---|---|
| Audit Tier-1 findings open | 2 | 1 (text.py split pending) | 1 | 1 (or 0 if Sprint 3 ran) |
| Audit Tier-2 findings open | 6 | 5 | 0 (Q1/Q2 dependent) | 0 |
| Audit Tier-3 findings open | 8 | 4 | 3 | 0 |
| `text.py` LOC | 681 | 678 | 678 | 678 (or ~520 after Sprint 3) |
| `parse_date` per-call list allocation | Yes | No | No | No |
| Free-threading lazy-init races in `bengal/utils/concurrency/` | 1 | 1 | 1 | 0 |

---

## Out of Scope

- **Other leaf clusters.** `parsing/` (15 leaves), `rendering/` (15 leaves), `cli/` (13 leaves) deserve their own audits; not bundled here.
- **The orphan `bengal/concurrency.py`** at the package root. Worth a separate question: does it belong under `utils/concurrency/`? Not in this plan.
- **New abstractions or service extractions.** Per CLAUDE.md: don't decompose unless wrappers are deleted first. These are leaves, so the rule doesn't apply directly, but the spirit (avoid premature abstraction) rules out introducing new helpers.
- **Documentation churn.** Docstrings updated only where they're load-bearing for the change.
