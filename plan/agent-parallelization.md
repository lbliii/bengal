<!-- markdownlint-disable MD013 MD060 -->

# Agent Parallelization Harness

**Status**: Inventory archive (Waves 1–4 on `main` through #707). Canonical
magnet list + `drive`/`board`/`claim` is [`BACKLOG.md`](BACKLOG.md).
**Created**: 2026-08-14
**Baseline**: `main` @ `ec656b36e` (v0.5.1); inventory closed at `c8788f9a1`
(#707)
**Model**: DORI `plan/BACKLOG.md` — edit-magnet serialize list + usually-safe
parallel pairs. This file is process harness history, not shipped product
behavior.

## Goal

De-risk Bengal's *structure* so several agents can work at once without
colliding on megafiles. Python **3.14t free-threading stays the floor** — do
not loosen `ensure_free_threading_or_confirm`, do not add GIL as a supported
default, do not treat 3.14t as optional.

Real sites (Quito, Chirp, other in-house sites) already run this. Public
contracts, template APIs, and build output must stay byte-stable unless a
peel explicitly proves otherwise.

## Non-goals

- Questioning viability or "getting 3 users"
- Loosening the free-threading gate
- CLI output orchestration epic `#654`–`#691` (wrong backlog for this pass)
- Restoring Site/Page mixins or forwarding wrappers
  (`plan/epic-delete-forwarding-wrappers.md`)
- Mass-deleting local branches that still hold unique commits

## Waves (historical)

Waves 1–4 landed on `main` through #707. Do **not** treat the magnet table
below as current — use [`BACKLOG.md`](BACKLOG.md). This file keeps the
inventory that justified those peels.

| Wave | What | Outcome |
|------|------|---------|
| **1** | Inventory: magnets, peel candidates, brittleness, CI rot | This file |
| **2–4** | Peel magnets; one magnet per PR; serialize | #698–#707 on `main` |

## Caps

| Knob | Default |
|------|---------|
| Parallel workers | ≤3 if any Path overlaps a magnet; ≤5 if Path scopes are disjoint |
| Magnet edits | Never two in-flight Tasks on the same magnet |
| Peel size | New files under ~400 lines (DORI rule) |
| Proof | Focused tests for the peeled unit + `uv run lint-imports` if imports move |

## Edit-magnet serialize list

Do **not** parallelize Tasks that both edit any of these. Fan-in is distinct
importers (prod|test). Churn is commit touches on `origin/main` since 2026-01-01.

| Magnet | loc | churn | fan-in | Peel? | Why |
|--------|----:|------:|--------|:-----:|-----|
| `bengal/core/site/__init__.py` | 1263 | 43 | 55\|171 | later | Highest fan-in; Stop & Ask; forwarding-epic |
| `bengal/rendering/pipeline/core.py` | 1188 | 95 | 25\|24 | **1** | Hottest file; parse→render handoff |
| `bengal/rendering/renderer.py` | 983 | 42 | 36\|30 | **2** | Presentation hub; peel before pipeline if both in flight |
| `bengal/orchestration/build/__init__.py` | 1169 | 68 | 21\|13 | **3** | Hardcoded phases; do not add phases |
| `bengal/server/build_trigger.py` | 1886 | 72 | 10\|7 | **4** | Dev-loop rebuild brain |
| `bengal/orchestration/render/orchestrator.py` | 708 | 54 | 19\|11 | yes | Snapshot handoff consumer |
| `bengal/rendering/engines/kida.py` | 1453 | 49 | 6\|10 | yes | Default engine; strict-undefined |
| `bengal/orchestration/content.py` | 1379 | 43 | 10\|19 | yes | Deferred import from Site |
| provenance pair (see below) | 1143+1321 | 41+45 | — | **5** | One magnet, two files |
| `bengal/server/dev_server.py` | 1428 | 46 | 14\|8 | no | Serve entry; pairs with trigger |
| `bengal/snapshots/render_plan.py` | 1534 | 7 | 7\|3 | no | Frozen plan; cold but load-bearing |
| `bengal/core/page/runtime.py` | 760 | 4 | 1\|0 | no | Sole page body; grep-`Page` clash |
| `bengal/cli/milo_app.py` | 1193 | 17 | 3\|10 | no | Command registration |
| `bengal/errors/suggestions.py` | 1223 | 11 | 7\|2 | no | Error copy fanout |
| `bengal/health/remediation/autofix.py` | 1341 | 5 | 1\|2 | no | `bengal fix` writer |
| `bengal/autodoc/extractors/cli.py` | 1369 | 15 | 2\|2 | no | CLI autodoc leaf |
| `bengal/autodoc/extractors/python/extractor.py` | 1100 | 14 | 1\|2 | no | Python autodoc leaf |

**Dropped from seed:** `core/page/__init__.py` (20 loc), `template_functions/openapi.py`
(leaf), `cli/milo_commands/build.py` (thin CLI over the build magnet).

**Provenance is one magnet:** `build/provenance/filter.py` (engine) +
`orchestration/build/provenance_filter.py` (phase wrapper, imports the engine
at `:23-24`). Opposite-half edits diverge incremental parity.

### Peel order (Wave 2)

Architecture vs fan-in disagree on Site. **Clash rank ≠ peel rank.**

Site is the highest *collision* magnet (fan-in 55|171) so it stays serialized,
but it is **not** peel #1: mixin history, live `.importlinter` ignores, and
Stop & Ask. Peel structurally safer magnets first.

1. `rendering/pipeline/core.py` — parse/render/dependency/output siblings
2. `rendering/renderer.py` — context / template-select / menu-state / batch
   (peel this *before* a second agent touches pipeline)
3. `orchestration/build/__init__.py` — `build()` sequencing → `build/runner.py`
4. `server/build_trigger.py` — classify / debounce / rebuild-plan / gate
5. Provenance pair as a single PR
6. Site HOW-forwarders last (`epic-delete-forwarding-wrappers.md` D2)

### Test twins (travel with the peel)

| magnet | tests |
|--------|-------|
| pipeline `core.py` | `tests/unit/rendering/pipeline/`, `tests/performance/test_post_render_pipeline_budget.py` |
| `renderer.py` | `tests/unit/rendering/test_renderer*` |
| build `__init__.py` | `tests/unit/orchestration/test_build_orchestrator.py` + `tests/unit/orchestration/build/` (**18 files, ~4625 LOC**) |
| provenance pair | `tests/unit/build/provenance/` + `tests/unit/orchestration/build/test_provenance_*` + `tests/integration/test_incremental_cache_stability.py` |
| `build_trigger.py` | `tests/unit/server/test_build_trigger.py` (**2126 LOC — larger than prod**) |
| Site | `tests/unit/core/test_site*` (~2111 LOC), `tests/integration/test_build_snapshot.py` |

### False magnets (large, safe to ignore)

`template_functions/openapi.py` (1611, fan-in 1\|2), Patitas directive builtins
(`embed`/`cards`/`video`), `cli/milo_commands/build.py`, `debug/content_migrator.py`,
`analysis/graph/knowledge_graph.py`, `postprocess/social_cards.py`, `core/version.py`.

### Twin clashes (not duplicates)

| pair | risk |
|------|------|
| provenance engine ↔ orchestration wrapper | two “fix incremental” agents |
| `content/discovery/content_discovery.py` ↔ `orchestration/content.py` | discovery semantics |
| Site ↔ `orchestration/site_runner.py` | forwarding-epic vs resident-site |
| pipeline `core.py` ↔ render orchestrator | handoff boundary |
| `snapshots/render_plan.py` ↔ `snapshots/scheduler.py` | snapshot RFC split |

## Usually-safe parallel pairs

When Path scopes stay inside these pairs **and avoid magnets**:

- `bengal/css/` ∥ `bengal/analysis/`
- `bengal/capabilities/` ∥ `bengal/fonts/` / `bengal/icons/`
- `bengal/scaffolds/` ∥ `bengal/themes/default/` (theme CSS/JS only; not
  `dev_server.py`)
- `bengal/postprocess/output_formats/` ∥ `bengal/health/validators/` (not
  `autofix.py`)
- `bengal/autodoc/extractors/python/` ∥ `bengal/content_types/` (not
  `template_functions/openapi.py`)
- `bengal/config/` ∥ `bengal/protocols/`
- `bengal/audit/` ∥ `bengal/debug/`
- `bengal/plugins/` ∥ `bengal/parsing/backends/patitas/directives/builtins/`
- `tests/roots/` fixture-only ∥ matching unit tests, if production magnets
  are untouched

**Never parallel with anything:** `bengal/core/site/`, `bengal/core/page/`,
`bengal/orchestration/build/`, `bengal/rendering/pipeline/`,
`bengal/rendering/renderer.py`, `bengal/server/`.

## Active-saga clash map

Do not run these pairs in parallel:

| A | B | files |
|---|---|-------|
| forwarding wrappers | snapshot handoff | Site, `runtime.py`, `render_plan.py`, render orchestrator |
| incremental indexes | perf W4·T15 | provenance pair, incremental orchestrator |
| resident site | forwarding wrappers | `site_runner.py`, Site, `content.py`, `build_trigger.py` |
| template view-models | snapshot handoff | `render_plan.py`, pipeline `core.py`, template_functions |

## Steward Path scopes

Prefer Tasks shaped as: one steward tree + matching `tests/` + optional one
docs file. Steward maps live in `**/AGENTS.md`. A Task that would edit a
magnet needs an explicit carve-out or a prior split Task.

Test files larger than their production magnet **are magnets**: serialize
`tests/unit/server/test_build_trigger.py` with `build_trigger.py`.

## Simplification (delete/shrink, not new layers)

From the maintainability pass:

- Site lifecycle shims (`build`/`serve`/`clean`/`prepare_for_rebuild` at
  `core/site/__init__.py:1143-1231`) — **delete after caller migration**, do
  not peel further. ~100 callers.
- Provenance: peel orchestration glue (`provenance_filter.py:229-656`) around
  the engine; do not duplicate `build/provenance/filter.py`.
- Delete legacy CSS minify test twin `tests/unit/utils/test_css_minifier.py`
  (~538 LOC) once `tests/unit/css/` is the suite.
- `errors/suggestions.py` — split ~550 LOC data dict from helpers; do not
  grow helper surface.
- `postprocess/output_formats/__init__.py` — shrink to thin re-exports.
- Exclude `build/lib/**/AGENTS.md` (wheel artifacts) from agent context.
- ~30 leaf `AGENTS.md` files are the same 63–66 LOC skeleton. Later: one
  steward index + per-tree delta bullets. Root + core stewards stay
  load-bearing. Scoped files still say `manual-confirmation-needed` while
  root is `codeowners-routed`.

## Hygiene (Wave 1 — inventory only)

`git worktree prune` was a no-op: **32/32 paths still exist** (mostly
`.claude/worktrees/wf_*` from v0.4.1–v0.5.0 agent sessions).

| Metric | Count |
|--------|------:|
| Local branches | 518 |
| Gone-upstream | 231 |
| Merged-gone (safe to `git branch -d` later) | **40** |
| Unique-gone (**keep**) | **191** |

Do not mass-delete unique-gone. Several unique-gone branches are checked out
in `.claude/worktrees/` (`feat/v05-*`, `docs/v05-*`, `lbliii/v041-*`).
Merged-gone list and the `-d` command live with the hygiene agent return;
run only when explicitly asked.

## CI (Wave 1 — diagnosed)

Weekly jobs fail on freeze SHA `ec656b36e`. `ci-ok` does not `needs` them, so
the required check stays green.

**Stateful (OOM, not product):** Hypothesis + xdist + `--forked` +
`PYTHON_GIL=0` SIGKILL. Fix: `-n 0`, drop `--forked`. Do not skip.

**Slow-tests (mixed):**
- Harness: `@pytest.mark.slow` memory tests leak in because
  `tests/performance/__init__.py` `pytestmark` does not apply to modules.
  Fix: `--ignore=tests/performance` and `-n 0`.
- Product/test-contract on this SHA (would fail locally): strict-mode
  overlay swallows expected errors; incremental second no-op has
  `skipped is False`; config fingerprint missing; parsed-content cache
  stale after edit; no `rss.xml`. Not flake. Needs product/test update,
  not a skip.

**Mutation:** no-op + fail-open. Current mutmut rejects `--paths-to-mutate`;
`|| true` makes the workflow succeed in ~1s. Unpinned `uv pip install mutmut`.

**ci-ok hole:** add `stateful`, `slow-tests`, `performance` to `needs`; on
`schedule` those three must pass.

**Next proof (before any peel claims tests pass):**

```bash
uv run pytest -n 0 -q --tb=short -m stateful tests/integration/stateful/test_build_workflows.py
uv run pytest -n 0 -q --tb=short \
  tests/integration/test_output_quality.py::TestStrictMode \
  tests/integration/test_full_to_incremental_sequence.py::TestIncrementalSequence
```

## FT hazards (add to serialize)

Do not loosen `bengal/cli/utils/free_threading.py`.

| Hazard | Path |
|--------|------|
| `@cached_property` → `list` | `core/section/__init__.py:318,337,344,351,452` |
| `@cached_property` → `list` | `core/page/runtime.py:739` (`authors`) |
| Unlocked module dict | `snapshots/render_plan.py:187-199` `_WORKER_PAGE_CONTENT` |
| Unlocked registry | `rendering/highlighting/__init__.py:98,123,157,304` |
| Unlocked registry | `rendering/engines/__init__.py:87,99` |
| Shared `dict[str, list]` | `rendering/template_functions/i18n.py:406-441` |
| Build-outside-lock | `rendering/template_functions/version_url.py:302-331` |

`core/section/__init__.py` is an FT magnet even when Site/Page are the
named serialize entries. Engine/highlighter registries serialize with any
render-engine peel.

## Invariants for every peel

1. Python 3.14t remains required; FT gate stays.
2. No new mixins on `Site` / `Page` / `Section`.
3. Pipeline records stay frozen.
4. `uv run lint-imports` if imports move.
5. Byte-identical dogfood build unless the peel's proof says otherwise.
6. One magnet per PR.
7. Do not hoist deferred Site imports (`site_runner`, `content`,
   `version_url`) to module level (`.importlinter:52-72`).
8. `Section`/`Site` `@cached_property` values used during parallel render
   must stay immutable (`tuple` not `list`) — `section/__init__.py:336-348`,
   `site/__init__.py:552-564`.

## Architecture notes (Wave 1)

From the architecture pass (2026-08-14):

- `Site` is coordinator + model + upward-import hub. Six live
  `.importlinter` ignores (`:73-80`). Discovery still constructs
  `ContentOrchestrator` from Site methods (`core/site/__init__.py:372-392`).
- `Page` is gone from the package root; `RuntimePage` is the only page body
  (`core/page/__init__.py:1-6`). Agents grepping `Page` will collide on
  `runtime.py`.
- `BuildOrchestrator.build()` still sequences all ~21 phases inline
  (`orchestration/build/__init__.py:143-1060`).
- [BUILD] `Section.sorted_pages` / `regular_pages` return mutable lists via
  `@cached_property`.
- [AGENT] `RuntimePage._global_missing_section_warnings` ClassVar dict
  (`runtime.py:112-113`).

## Wave 1 agent returns

| Agent | Status | Notes |
|-------|--------|-------|
| Magnet hunter | done | 18 serialize magnets; add `renderer.py`; drop openapi/build-cli/`page/__init__`; Site is clash #1 but peel later |
| Architecture | done | magnets confirmed; provenance is one clash; peel pipeline → build spine → provenance twin |
| Maintainability | done | Site shims = delete not peel; test twins can exceed prod (`test_build_trigger.py` 2126); ~30 AGENTS.md are copy-paste |
| Brittleness / FT / CI | done | stateful OOM; slow-tests overlay/incremental/RSS contract drift; mutation no-op; ci-ok hole |
| Hygiene | done | 32 worktrees remain; 40 merged-gone safe later; 191 unique-gone keep |

Wave 1 complete. Wave 2 peels wait for review. First *non-peel* work if
continuing: CI harness (`-n 0`, ignore performance in slow-tests, `ci-ok`
needs, pin/fix mutmut) then the overlay/incremental contract failures.

## Related

- DORI model: `plan/BACKLOG.md` + `plan/issue-lifecycle.md` in the DORI repo
- `plan/epic-delete-forwarding-wrappers.md` — do not re-litigate mixins
- `plan/rfc-snapshot-build-plan-handoff.md` — render-plan magnet
- Root `AGENTS.md` Stop & Ask list still applies
