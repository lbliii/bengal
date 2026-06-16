# RFC: Persistent Resident Site (warm-rebuild architecture)

**Status**: Draft / proposed
**Created**: 2026-06-16
**Author**: Claude (Opus 4.8)
**Related**: `rfc-snapshot-build-plan-handoff.md`, `rfc-incremental-dependency-indexes.md`,
`rfc-effect-traced-incremental-builds.md`; issues #330, #332, #521, #310 (warm-build arc);
#350 (orthogonal — cold render-at-scale).

## Why this RFC exists

Per-phase profiling of the warm dev-loop (2026-06-16, free-threaded 3.14t, committed
`benchmarks/baselines/warm_build.json` harness) established two things:

1. The warm single-page rebuild scales with **total site size**, not change size
   (1.7s @100p → 6.2s @1000p baseline; ~1.8s @800p on the synthetic harness).
2. The cost is spread across *every* build phase — Discovery ~16%, plus
   Config/filter, Initialization, Post-process, Health (~66% combined). **No single
   phase is a dominant target, and none has a safe quick proportional win** (see #521:
   each does heavy O(total) per-page work or its incremental machinery conservatively
   bails). Discovery-pass proportionality (#332) addresses ~6%; the dominant phases are
   near their per-phase floor for a content edit.

The root cause is structural: **every warm rebuild tears the Site down and rebuilds it
from disk.** `SiteRunner.prepare_for_rebuild()` (`bengal/orchestration/site_runner.py`)
clears `site.pages`, `site.sections`, `site.taxonomies`, `site.menu*`, `site.xref_index`,
`site._cascade_snapshot`, `site.registry`, and `site.url_registry` to empty; the build
then re-discovers (full content-dir walk), reconstructs/re-parses pages, rebuilds every
derived index, re-serializes site-wide outputs, and re-validates the whole site. The
work is O(total pages) *by construction* — the changed file is one row in a full rebuild.

No amount of per-phase tuning escapes this. The lever is architectural: **keep the built
Site resident in memory across warm rebuilds and surgically mutate only what changed.**

## Goals

- Warm edit-to-reload latency **proportional to the change**, not total site size, for
  the common dev-loop edits (content body, frontmatter, single data file, template).
- **Byte-identical** output vs a full cold rebuild on the same final state — proven per
  change-type before that type is enabled.
- A **conservative fallback to the current full teardown** on any change the surgical
  path cannot prove it handles. Never trade correctness for latency.
- Build on the existing incremental contracts (`DependencyReadIndex`, the effect tracer,
  the snapshot `IncrementalPlan` shape) rather than inventing parallel machinery.

## Non-Goals

- Cold-build / render-at-scale parallelism — that is #350 (shard / heap isolation),
  which is **orthogonal**: #350 forks workers to escape free-threading's coherency tax
  on large *cold* builds; this RFC keeps a Site resident for *warm* in-process edits.
  A dev server can use the resident model for warm edits and (eventually) shard for the
  initial cold build.
- Changing the cold-build path. The first build of a session is unchanged; the resident
  model only governs subsequent warm rebuilds.
- Removing `prepare_for_rebuild()`. It remains the safety-net fallback.

## What already exists (build on these)

- **Reactive single-page handler** (`bengal/server/reactive/handler.py`,
  `ReactiveContentHandler.handle_content_change`) is the existing proof that surgical
  in-place mutation works: it re-reads one file's body, `clear_parsed_page_state(page)`,
  re-renders only that page against the resident Site, writes, and returns — no rebuild.
  Its hard limit: **body-only, single page, no rendered dependents** (it `return None`s
  to a full warm build on `_has_rendered_dependents`, frontmatter changes, etc.).
- **Dependency read-index** (`bengal/build/contracts/dependency_index.py`, persisted at
  `.bengal/provenance/dependency-index.json`) already answers "which pages/outputs depend
  on dependency X?" — the query that drives *which* resident state to touch.
- **Effect tracer** (`bengal/effects/`) captures *what* changed (files/computations).
- **Snapshot handoff** (`rfc-snapshot-build-plan-handoff.md`) already specifies an
  `IncrementalPlan(changed_inputs, affected_pages, affected_outputs, fallback_reasons)`
  record — the natural shape for a surgical rebuild plan.
- **The dev-server decision gate** (`bengal/server/build_trigger.py`) already classifies
  changes three ways: structural → subprocess full; content-only-no-dependents → reactive;
  else → `_run_warm_build()` which calls `prepare_for_rebuild()` (L629). The new path slots
  in as a fourth, between reactive and full teardown.

**Correction to note:** `ContentDiscovery._discover_surgical()` is *not* affected-only — it
still walks the whole content dir and reconstructs every unchanged page from cache (returns
the full page set). The resident model's win is avoiding that walk entirely by keeping
`site.pages` resident; surgical discovery is a fallback, not the mechanism.

## Proposed model

Keep the Site object resident across warm rebuilds (the dev server already holds it). On a
change, instead of `prepare_for_rebuild()` + full build, run a **surgical mutation**:

```
BuildTrigger._run_warm_build(changed_paths, event_types):
  if not _surgical_eligible(changed_paths, event_types):   # NEW gate
      site.prepare_for_rebuild(); full warm build           # unchanged fallback
  else:
      plan = SiteStateMutator(site, dep_index).apply(changed_paths)   # NEW
      if plan.fallback_reasons:                              # mutator couldn't prove it
          site.prepare_for_rebuild(); full warm build        # fallback
      else:
          render(plan.affected_pages); postprocess(plan.affected_outputs)
```

The net-new component is **`SiteStateMutator`** (`bengal/orchestration/incremental/`):
given the resident `site` + the changed paths + the dependency index, it mutates *in place*
only the affected slices of each derived structure, and returns an `IncrementalPlan`-shaped
result (or non-empty `fallback_reasons` to bail):

| Resident structure | Today (teardown) | Surgical mutation |
| --- | --- | --- |
| `site.pages` | cleared + full re-walk/reparse | re-parse only changed pages; replace those entries |
| `site.taxonomies` | cleared + recomputed | add/remove only the changed pages' tags |
| `site.menu*` | cleared + rebuilt | rebuild only menus whose member pages changed |
| `site.xref_index` | cleared + rebuilt | re-index only changed pages (ordering caveat below) |
| `site._cascade_snapshot` | nulled + rebuilt | recompute only affected section subtrees |
| `site.registry` / `url_registry` | cleared + rebuilt | update only affected sections/URLs |
| post-process (sitemap/RSS/index.json/llm) | regenerated wholesale | regenerate only if the affected output's input set changed |
| health validators | re-run over all pages | re-validate changed pages + genuinely-global checks |

## The hard part (be honest)

Byte-parity of *incremental global-state mutation* is the entire difficulty, and it is the
same landmine class that sank earlier spikes (the xref `by_anchor` collision-order
dependence; the parsed-content reconstruction that broke the provenance filter, #332). Each
derived structure has cross-page, order-sensitive semantics that a naive "patch the changed
rows" will get subtly wrong:

- **xref `by_anchor`** resolves collisions by page-processing order and heading-vs-target
  precedence *across pages* — a removed/re-added page can change which entry wins.
- **taxonomies / menu** have weight/title/date ordering that a changed page can reorder.
- **cascade** is inherited down section subtrees — a changed `_index.md` affects descendants.
- **deletes and moves** must remove resident state (and the orphaned output file) correctly.

Therefore the model is only safe with two invariants:

1. **Fallback is part of the contract.** The mutator emits a `fallback_reason` and the
   caller does a full teardown rebuild whenever it cannot *prove* the surgical result equals
   a full rebuild (unknown change type, ambiguous dependency, structural move, config/theme
   change). A fast miss is only valid when proven; otherwise rebuild.
2. **Per-change-type byte-parity gate.** A change type is enabled only after a committed
   test proves `surgical_output == full_rebuild_output` (HTML + sitemap/RSS/index.json +
   the changed-output set) across the warm fixtures — the discriminating-assertion standard,
   not page-count checks.

## Phased rollout (safest change-types first)

1. **Foundation** — `SiteStateMutator` skeleton + the `_surgical_eligible` gate + the
   byte-parity harness (full vs surgical on the same final state). Everything still falls
   back to teardown; zero behavior change until a type is enabled.
2. **Frontmatter-only edit** (no nav/cascade keys) — re-parse one page, patch its pages
   entry + taxonomy membership + xref entry; render it + its dependents. Extends the
   reactive handler past body-only.
3. **Single data-file edit** — use the dependency index to find affected pages; re-render
   them; mutate nothing global. (Index already supports `data` kind.)
4. **Template edit** — re-render the index-resolved affected pages; no content re-parse.
5. **Multi-page content edits** — generalize 2–3 to a set.
6. **Structural (add / delete / move)** — the hardest; resident add/remove + menu/xref/
   taxonomy/cascade repair + orphan output cleanup. May stay on full-teardown fallback
   indefinitely if parity can't be cheaply proven.

Post-process and health proportionalization (#521) ride along: once the affected-page set
is authoritative, site-wide outputs regenerate via per-page chunk reuse and health
validates only changed pages + global checks.

## Proof matrix

| Surface | Required proof |
| --- | --- |
| Unit | mutator updates each derived index correctly for a single changed page |
| Parity | per change-type: surgical output byte-identical to full rebuild on same final state (HTML + sitemap + RSS + index.json + changed-output set) |
| Fallback | every non-enabled / ambiguous change type falls back to full teardown with a named reason; no silent surgical attempt |
| Scaling | warm edit latency flat vs site size for enabled types, measured against `warm_build.json` |
| Free-threading | resident mutation runs on the dev-server control thread; render still parallel — assert no shared-state races introduced |
| Memory | resident Site does not grow unbounded across a long session (adds/deletes pruned) |

## Risks

- **Byte-parity** (primary) — gated per change-type; fallback on any doubt.
- **Resident-state drift** — the in-memory Site silently diverging from disk (the failure
  mode behind the dead reconstruction path, #332). Mitigation: the mutator derives strictly
  from re-read changed inputs + the dependency index; never trusts stale resident derived
  state for the changed slice.
- **Free-threading** — resident mutable state mutated between parallel renders; keep mutation
  single-threaded (control thread) and treat the resident Site as frozen during render.
- **Scope creep into #350** — keep cold-render parallelism out; this is warm in-process only.
- **Memory** — a long dev session accumulates resident state; prune on delete/move.

## Relationship to the existing warm-build arc

This RFC reframes the warm-build epic. #332 (proportional discovery) and #521 (dominant-phase
proportionality) are *components* of the surgical path, not standalone goals — they only reach
the sub-second dev loop inside a resident-Site model that stops tearing the Site down. #330
becomes the umbrella; this RFC is its architecture. #350 is unaffected (cold render-at-scale).

## Not now

- Persisting the resident Site across *process* restarts (in-process / dev-server session only).
- Merging with #350 shard workers.
- Incremental search-backend (lunr) index updates beyond regenerate-if-affected.
