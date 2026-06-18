# Epic: Knowledge Graph — From Utility to Showcase

**Status**: Proposed
**Created**: 2026-06-18
**Target**: v0.6.0 / v0.7.0 (rides the Pridelands token landing — already merged, so unblocked now)
**Source**: 6-dimension survey of the first-party graph engine shipped in PR #554 (visual design, analysis surfacing, explorer UX, render/layout perf, contextual minimap, a11y/responsive), reconciled against an adversarial critique that was verified file-by-file before this plan.
**Builds on**: `bengal/analysis/graph/` (build-time engine), `bengal-graph-explorer.js` (Canvas2D explorer), `graph-contextual.js` (per-page SVG minimap). Does **not** redo the engine or reintroduce D3.
**Dependencies**: Pridelands refresh #532 — OKLCH (#534/PR#555) and light-dark() (#535/PR#556) are **merged on main as of 2026-06-18**, so the token-migration phase is unblocked and consumes the shipped anchors directly; custom-elements (#537) is in-flight and the graph does not depend on it.

---

## North Star: What Showcase-Great Looks Like

A reader lands on `/graph/` and sees the whole site **as a living map of topics**: distinct, perceptually-uniform colored lobes (communities) fan apart instead of a gray center-piled hairball, the genuinely authoritative pages glow large and bright (PageRank), and orphans drift dim at the rim. The view settles in with a 400ms zoom-ease, the hubs are already labeled so there are landmarks to steer toward, and a hint invites a click. Clicking a node doesn't eject you — it **spotlights that page's neighborhood**, opens a persistent detail card surfacing the rich analysis we already compute (connectivity, in/out refs, reading time, tags, community), and offers a deliberate "Open page →" CTA. The whole thing is keyboard-operable with a drawn focus ring and announced via aria-live, works under touch and on a phone via a bottom-sheet, honors `prefers-reduced-motion`, and — critically — every color is the **same OKLCH + light-dark() token system as the rest of Pridelands**, so the graph reads as one coherent product across all 6 palettes and both modes. On every content page, the sidebar minimap is the same story in miniature: a real card with a header, size-encoded nodes, weighted edges, and a tooltip that matches the explorer. It stays 60fps at 1208 nodes and has headroom to 5–10×, and the build that bakes it all stays bounded and byte-identical warm==cold.

---

## Top 5 Highest-Leverage Moves (most "great" for least risk)

1. **Community-colored, importance-sized graph (the Obsidian "wow").** Wire the already-computed Louvain communities and PageRank into the bake: color nodes by community, size by PageRank. This is the single biggest visual transformation — flat sea of dots → legible topical map. **Hard prerequisite (P0.5): the determinism floor must be fixed first** — Louvain shuffles via the *global* `random` module (`community_detection.py:212`) and renumbers communities by an order-derived key (`:269-272`), and all three analyses (Louvain/PageRank/path) sit on an unsorted `list(self.site.pages)` (`builder.py:122-134`). [P1, bakes new data]

2. **Community-aware baked layout (kills the hairball geometrically).** Feed those same communities into `compute_force_layout` as ring-distributed centroids + per-community gravity, replacing the single global center pull (`layout.py:307-311`). Tends to *reduce* iterations while separating clusters into lobes. [P1.3, its own PR — changes baked coords]

3. **Migrate graph colors onto Pridelands OKLCH + light-dark() tokens.** Delete the ~150-line per-palette region (`graph.css:566-717`) and the 8 scattered `[data-theme="dark"]` panel blocks (`:100,132,204,238,279,314,495,542`); derive `--graph-node-*` and a deterministic OKLCH community palette from the live theme anchors. Coherence win, deletes the maintenance fork, fixes contrast — foundation every other color-touching item depends on. Pure CSS, no bake. [P0]

4. **Click-to-focus spotlight + persistent detail panel + deep-link.** Turn click from "navigate away" into ego-graph isolation with a theme-tokened detail card and a deliberate CTA; mirror it to `#node=` URL state for shareable focused views and free breadcrumb/back. Converts the explorer from a launcher into a browsing surface, reusing existing dim/highlight/`fitToView` machinery. [P2, runtime only]

5. **Real node depth + entrance settle on the canvas.** Cached radial-gradient node bodies + halos for hubs, connectivity-weighted edges, and a 400ms fade/zoom-settle intro — the dead SVG-only glow CSS (`graph.css:359-401`) finally made real on the canvas. The cheapest "premium product" signal. [P2, runtime only]

---

## Design Principles

1. **Compose with Pridelands, don't fork it.** Every color is an OKLCH primitive or palette semantic token resolved through `light-dark()`. No new hardcoded hex, no new `[data-theme=dark]` override blocks. The graph follows the theme; it never runs a parallel system.
2. **Surface what we already compute.** The engine computes communities, PageRank, betweenness, bridges, link suggestions. The bias is to *show* baked analysis, not invent new analysis.
3. **Determinism is load-bearing — and it is not currently guarded.** Anything baked into `graph.json` / `index.json` `.graph` must use a local seeded PRNG (never global `random`), iterate over a **sorted, build-stable node-id order**, and round to fixed precision — mirroring `layout.py` (`_Rng`, `_COORD_PRECISION=4`, `_round`). There is **no existing live `graph.json` parity gate** (the build-snapshot fixture is skipped-by-default and stale, `test_build_snapshot.py:131`; `test_graph_layout.py` only exercises `compute_force_layout` in isolation). Building that gate is part of P0.5, not an assumed backstop.
4. **Compute once, consume everywhere.** Heavy analysis (Louvain, PageRank, path) is cached on `KnowledgeGraph` (`_pagerank_results:141`, `_community_results:142`) and reused for `graph.json` and the ×1208 per-page `.graph` block, so the minimap path pays zero extra compute.
5. **60fps now and at 5–10×.** Per-frame work is the budget. New visual richness is cached/bucketed/LOD-gated; build-time layout cost stays bounded.
6. **Operable without a mouse, motion-safe, mobile-first-capable.** Keyboard focus + aria-live + reduced-motion + touch are first-class, not afterthoughts.

---

## Invariants (stop and reassess if violated)

1. **Byte parity**: warm==cold `graph.json` and every page `index.json` `.graph` block remain byte-identical across two cold builds and warm vs cold. **This must be made true and CI-guarded by P0.5** — today it is asserted-but-unguarded.
2. **Zero external dependencies** for default builds — no CDN, no npm, no vendored libs. Runtime JS stays vanilla.
3. **Build-time layout cost stays bounded** for the 5–10× target. *(The previously circulated 6.2s@1208 / 54s@6000 figures are unsourced — they appear nowhere in the repo. P5 must **re-measure** on the docs site before any of them are used as a gate; until then, acceptance is stated relatively, not against those numbers.)*
4. **Explorer stays ~60fps** at 1208 nodes and degrades gracefully (LOD) at 5–10×.

---

## Roadmap

Each phase is independently shippable. Phases that bake new data or change baked coordinates are flagged **[BAKES DATA]** and carry the full seeded/sorted/rounded determinism treatment plus an in-PR fixture re-record. The determinism floor (P0.5) is a hard gate on every bake.

---

### P0 — Token Migration + Coherence Foundation (CSS-only, no bake)

**Sequencing:** unblocked now (#534/#535 merged). Lands the one correct color foundation that every later color-touching item builds on. Its standalone label-token fix can ship even earlier (see Issues).

**Deliverables**
- **Pull-forward, standalone bug fix:** `bengal-graph-explorer.js:90-91` reads `--color-text` / `--color-bg`, which **do not exist** as Pridelands tokens — labels always fall back to `#222`/`#fff` (broken in every dark palette). Switch to `--color-text-primary` / `--color-bg-primary`. Ship this independently first; it has zero dependency on the palette work.
- Replace the parallel per-palette region (`graph.css:566-717`, ~150 lines, currently `[data-palette=…]` × `[data-theme=dark]`) with a single `:root` definition of `--graph-node-*` / `--graph-link-*` as `light-dark(...)` over the palette's own semantic tokens: hub → `var(--color-accent)`, orphan → `var(--color-error)`, generated → `var(--color-success)`/`--color-info`, regular → `color-mix(in oklab, var(--color-text-secondary), var(--color-bg-primary) 35%)`. Derive glows via `color-mix(... transparent 60%)` (retire the `--graph-node-*-glow` hex vars at `:359-401`). Per-palette hue + dark mode now come for free.
- Define a deterministic **OKLCH categorical community palette** as tokens `--graph-community-0..N`, generated by rotating the Pridelands accent hue in OKLCH hue space (even hue steps → perceptually-balanced, light-dark()-adaptive). Communities beyond the palette fall to a muted "other" token. (Consumed by P1; the color-index assignment must use the same stable rank-sort as the ids — see P1.1.)
- **Fix regular-node contrast**: ensure `--graph-node-regular` clears ≥3:1 non-text contrast against each palette's actual `--color-bg-primary` in both schemes. Add an optional 1px node rim stroke in `--color-bg-primary` drawn in `draw()` for robustness on any background.
- Modernize control/legend/tooltip panels (`graph.css:108-143, 292-325, 460-506`) onto `--color-bg-elevated`/`--color-surface`, `--elevation-popover/modal`, `--radius-soft-*`, `--space-*`; tie `backdrop-filter` tint to `color-mix(in oklab, var(--color-bg-elevated), transparent 12%)`; delete the **8 scattered** `[data-theme="dark"]` panel blocks (`:100,132,204,238,279,314,495,542`).
- Migrate `graph-contextual.css` (minimap) in lockstep: kill `#1976d2` and the literal `drop-shadow` glows and the `[data-theme=dark]` dependence; express current-node emphasis via a `--graph-current` token.

**Files**: `bengal/themes/default/assets/css/components/graph.css`, `graph-contextual.css`, `bengal/themes/default/assets/js/bengal-graph-explorer.js`

**Constraints**: C3 (this *is* the adoption) · C2 (pure CSS/one-line JS) · **C1: none — runtime-resolved, nothing baked**.

**New baked data**: none.

**Landmines**:
- **#535 cascade tie-break** (memory: ~16% of "redundant" dark-override deletions are actually unsafe — base token loses to a later equal-specificity dark sibling). This applies to **all** the scattered panel blocks, not just the per-palette region. Land token definitions first, switch consumers in lockstep, run the conservative second-pass verify before deleting any dark block; keep hex fallbacks in `v(name, fallback)` during transition.
- **Canvas color-string support floor (named, not hand-waved):** `ctx.fillStyle` must accept the `getComputedStyle`-resolved string. Modern engines evaluate `oklch()`/`color-mix()` in `getComputedStyle` output, so the canvas gets a concrete color — but if Bengal's support matrix includes an engine that returns an unevaluated string, nodes silently fall back to the hex `v()` defaults P0 is deleting. **Action: keep the `v()` hex fallbacks in the JS color table (do not delete them) and confirm the canvas path against the theme's stated minimum browser before removing any.**
- light-dark() is color-only — node glow *shadows* stay in a retained `[data-theme=dark]` block.

**Acceptance**: all 6 palettes × {light,dark} render the graph from theme tokens; explorer labels are palette/dark-correct; regular nodes pass ≥3:1 contrast per palette; panels match other Pridelands surfaces; CSS minifier round-trips the OKLCH/color-mix; only the color-only-exempt shadow block remains as a `[data-theme=dark]` graph block; JS retains hex fallbacks but hardcodes no live colors.

---

### P0.5 — Determinism Floor (build-only, no new fields shipped) **[GATE for all of P1/P4 bakes]**

This is the non-negotiable prerequisite the previous draft folded into "P1.0." It is promoted to its own phase because the hazard is **broader than Louvain** and because the proof harness it relies on **does not exist yet**.

**Root cause (verified):** all three analyses pull pages through `KnowledgeGraph.get_analysis_pages()` → `GraphBuilder.get_analysis_pages()` → `list(self.site.pages)` (`builder.py:122-134`, `knowledge_graph.py:240-248`), which is **never sorted**. On top of that:
- Louvain shuffles via the **global** `random` module (`community_detection.py:212`) and only `random.seed`s when a seed is passed (`:167`) — **no build caller passes one** — and renumbers communities by an `enumerate(pages)`-derived integer key (`:186,269-272`), so ids inherit page order.
- PageRank power-iterates over that same unsorted list (`page_rank.py:184,217,224,234`); its dict order and float-accumulation order ride on it.
- Path analysis (P4's source) selects pivots via `rng.sample(pages, …)` over the same unsorted list (`path_analysis.py:321-322`) — `random.Random(42)` is fixed but `sample` output is *input-order-sensitive*, so which pivots (and thus betweenness scores) are chosen is non-reproducible.

**Deliverables**
- **Establish one build-stable canonical page order.** Either sort `get_analysis_pages()` by the baked node-id (`visualizer.py:_get_page_id`, verified build-stable: site-relative-path hash, `:148-193`), or prove `site.pages` iteration order is itself build-deterministic and document that as a shared precondition. Prefer the explicit sort — it removes the dependency entirely. Every downstream analysis iterates this order.
- **Louvain → local seeded PRNG + stable ids.** Replace global `random.shuffle` with a local PRNG seeded from a fixed constant (mirror `layout.py:_Rng`); shuffle through it; renumber communities by **`(size desc, min member node-id)`** keyed on the baked node-ids (not on `Page` identity or enumerate order); round any emitted float.
- **PageRank → sorted iteration + round-before-serialize.** Iterate the canonical order; round scores at fixed precision before any are baked.
- **Path pivots → sort before sample.** Sort `pages` (or node-ids) before `rng.sample` in the approximate path (`path_analysis.py:321`); round emitted scores. (1208 > the `auto_approximate_threshold=500`, so the approximate path *will* run on the docs site.)
- **Build the missing live parity gate.** Add a test that does two cold builds of a fixed root and asserts the **emitted `graph.json` is byte-identical**, exercising the *real unseeded build path* with communities + PageRank + (when P4 lands) path top-N. Add an id-level community-stability assertion. Do **not** rely on `test_community_detection.py:test_random_seed_reproducibility` — it is vacuous for this epic: it only asserts equal community *count* + modularity, always passes `random_seed=42` (the path the build never takes), and never asserts stable ids.

**Files**: `community_detection.py`, `page_rank.py`, `path_analysis.py`, `builder.py`/`knowledge_graph.py` (page-order), new test under `tests/` (live `graph.json` parity).

**Constraints**: **C1 (the whole point)** · C4 (sorting is O(N log N), negligible vs Louvain's per-pass edge scan).

**New baked data**: none yet — this phase changes *internal* determinism only; field/coordinate changes ship in P1. Shipping the parity gate before any consumer means P1 lands against a real backstop.

**Acceptance**: two cold builds of the docs site produce byte-identical `graph.json`; community ids are stable across runs on the unseeded build path; the new parity test fails loudly if global `random` or an unsorted page list is reintroduced (assertion proven to discriminate, not vacuous).

---

### P1 — Surface the Analysis: Community + PageRank (the visual transformation) **[BAKES DATA]**

The single biggest "wow." Gated on P0 (community palette tokens) and P0.5 (determinism floor + parity gate). Split into independently-bakeable, separately-reviewable PRs — field additions (P1.1/P1.2) are distinct byte-parity events from the geometry change (P1.3) and must **not** share one fixture re-record.

**P1.1 — Bake community id + community color per node:**
- Wire `detect_communities()` (cached, `knowledge_graph.py:647-684`) into `generate_graph_data()` (`visualizer.py:195`). Add `community` (stable int id from P0.5) + `community_color` (index into the P0 `--graph-community-*` tokens, **assigned by the same `(size desc, min member node-id)` rank-sort** so which communities get a distinct color vs the "other" bucket is itself deterministic). Color nodes by community; keep type as a secondary signal (ring/stroke for hub/orphan). Emit a `communities` stats block (id, label, size, color). Derive labels deterministically (most-frequent shared tag with sorted tie-break, or highest-PageRank member title). Explorer `nodeColor` (`bengal-graph-explorer.js:94`) switches to `n.community_color`, still resolved from CSS tokens.

**P1.2 — Bake PageRank → importance sizing:**
- Wire `compute_pagerank()` (cached, `:514-551`) into `generate_graph_data()`. Add `pagerank` per node, **rounded to fixed precision** (iteration is deterministic *given* P0.5's sorted order — round before serialize to also guard cross-platform float drift). Recompute `size` (currently degree-based, `visualizer.py:234-241`) from normalized PageRank (dominant) blended with reading_time (depth). Keep connectivity/in/out refs for tooltips.
- **Cross-effect flag:** `size` is copied straight through into the per-page `.graph` block by `json_generator.py` (`_get_page_connections`, ~`:176-179/331-334`). The ×1208 minimap currently **hardcodes** its node radius (`graph-contextual.js:110`, `n.isCurrent ? 8 : …`), so this P1.2 change does **not** alter the minimap's appearance — but it *does* re-bake all 1208 `.graph` blocks (fixture churn) and changes the value the minimap *will* read once P4 rewires it. Note this explicitly in the PR.

**P1.3 — Community-aware baked layout (kills the hairball) — SEPARATE PR, after P1.1/P1.2 stabilize:**
- Extend `compute_force_layout` to accept the community map + scores. Scatter each community around a **deterministic ring centroid** (`angle = 2π · sorted_index / num_communities`); replace the single global gravity (`layout.py:308-311`) with per-community gravity + a weak global cohesion. Cap centroids (merge sub-min-size communities into a "misc" ring).
- **Edge-weight springs:** pass `(s,t,weight)` (sorted incl. weight) and scale attraction by `min(weight,3)` so bidirectional pairs sit adjacent (`layout.py:239,293-305`; weights already emitted by the visualizer).
- This is a pure geometry change → its own fixture re-record, reviewed as one coordinate diff, not entangled with P1.1/P1.2 field additions.

**Files**: `visualizer.py`, `layout.py`, `bengal-graph-explorer.js`, `graph_visualizer.html` (+ the P0.5-fixed analysis modules, consumed, not re-edited)

**Constraints**: **C1 (load-bearing)** — every sub-item rounds + iterates the P0.5 canonical order; **each baked-field/coord change re-records fixtures + passes the P0.5 parity gate in the same PR**. C4 — Louvain/PageRank computed once via the shared cache; community seeding *may* converge the layout faster (**measure once, in P1.3 — do not also bank this speedup in P5**). C3 — community colors come only from P0 OKLCH tokens.

**New baked data**: per-node `community` (int), `community_color` (int index), `pagerank` (rounded float); recomputed `size`; `communities` stats block; revised normalized `(x,y)` (P1.3 only). Determinism: stable ids/rank-sort from P0.5, rounded floats, sorted iteration, centroid angles from sorted index.

**Landmines**: community color-index rank-sort must match the id rank-sort or color/label desync; keep `pagerank` precision tight to bound ×1208 `.graph` JSON growth; cap Louvain passes if 1208-node build cost spikes.

**Acceptance**: graph renders as distinct colored topical lobes (not a center-piled blob); `x_std`/`y_std` *improves* after P1.3; hubs visually dominate by size; the P0.5 parity test stays green after each re-record; ×1208 minimap build cost unchanged (no new compute on that path).

---

### P2 — Explorer Interaction + Depth (runtime only, no bake)

Turns the pretty map into a browsing surface and lands the visual-depth polish. All runtime — zero byte-parity exposure. **Every motion added here ships with its own reduced-motion gate in the same PR** (see P3 note).

**Deliverables**
- **Click-to-focus spotlight + detail panel** (`bengal-graph-explorer.js:329-334`): click PINS a node and enters focus state (generalize the hover dim path to `activeSet = focused ? adjacency[focused.id] : …`), eases camera to center the ego-graph (reuse `fitToView` math, `:230-245`). New `.graph-detail` aside (theme-tokened) shows title, type badge, reading_time, in/out counts, connectivity, tags, clickable neighbor list, **community label** ("Part of: Performance · 47 pages"), and an "Open page →" CTA. Escape/empty-space exits.
- **Deep-link focus** via `#node=<id>` (and `?focus=`): read on boot alongside the existing `?tag=` path (`:383`); `replaceState` on hover-driven change, `pushState` only on explicit click-focus; `popstate` gives breadcrumb/back for free. Validate id against `nodeById`, fall back to `fitToView`.
- **Community/tag exploration affordances**: clickable legend filters a cluster (reuse `?tag=` machinery); add `?community=` mirroring `?tag=`; minimap tints the current page's ring by community color.
- **Node depth on canvas** (`draw()` `:183-212`): per-type radial-gradient body + halo for hubs and the hovered/focused set, scaled by baked `connectivity`. **Cache gradient templates per type+radius bucket** (not per node); LOD fallback to flat fill above ~4000 visible or when nodes render <3px. Finally uses the depth `graph.css:359-401` faked for the never-created SVG.
- **Entrance settle**: replace the dead `graphFadeIn` CSS animation with a real 350–450ms rAF tween (global alpha 0→1 + camera ease 0.85→fit), optionally staggering node alpha by connectivity. Cancel on first interaction. **Gate behind `matchMedia('(prefers-reduced-motion: reduce)')` → snap to final frame.**
- **Edge depth**: map base-edge alpha/width to `edge.weight` + endpoint connectivity (low base alpha ~0.25 so structure reads as a constellation); two-stop gradient strokes for the **highlighted subset only** (never global — frame budget).

**Files**: `bengal-graph-explorer.js`, `graph_visualizer.html`, `graph.css`, `graph-contextual.js`

**Constraints**: C2 (vanilla Canvas/DOM/History) · **C1: none baked** · C3 — all new chrome from P0 tokens · C4 — per-node `createRadialGradient` is the classic Canvas trap: bucketed caching + LOD are **mandatory**; profile at 1208 and 5–10×.

**New baked data**: none.

**Landmines**: camera-ease + entrance tween must check reduced-motion and snap to final frame; focus state must clear on themechange/resize redraw or panel desyncs; full-graph per-edge gradients blow the budget — highlighted subset only.

**Acceptance**: click isolates ego-graph + opens a populated theme-tokened panel without navigating; focused views are shareable via `#node=`, back/forward works; hubs read luminous, orphans dim; 1208-node draw ~60fps with depth on; LOD verified at 5–10×; the reduced-motion path is the literal final frame.

---

### P3 — Accessibility, Motion-Safety, Mobile (runtime/CSS, no bake)

Closes the headline operability gaps. Keyboard nav + aria-live consume the `focused`-node concept P2 introduces, so they follow P2 — **but the reduced-motion gate for P2's specific animations ships inside P2, not here** (anything else is a live vestibular regression in the interim). P3 owns the *global* reduced-motion block (incl. the pre-existing `nodeGlow` hazard) and the operability surface.

**Deliverables**
- **Keyboard-navigable canvas + focus ring**: `tabindex=0` + `role=application` on the canvas (`boot()` `:451`); Tab/Shift-Tab cycles visible nodes (reuse `buildA11yList` order); arrows move to nearest visible neighbor (adjacency first, then picking grid `:100`); Enter/Space navigates; Home/End jump first/last; snap-center (no motion). Draw a focus ring in `--color-accent` around `focused`, driving the existing highlight path off `focused || hovered`. Scope node-nav keys to `document.activeElement === canvas` so they don't fight the search box.
- **aria-live status region**: add `<div role="status" aria-live="polite" class="sr-only">` to `graph_visualizer.html`; on focus change announce "Spelling Rules — hub, 12 incoming, 4 outgoing, 6 min read" from the already-formatted tooltip fields; debounce ~120ms; announce filter/search counts.
- **Global reduced-motion gate**: add `@media (prefers-reduced-motion: reduce)` to `graph.css` and `graph-contextual.css` (currently **none exist**) — `animation:none` on `graphFadeIn`, `tooltipFadeIn`, and especially the **four infinite `nodeGlow` hover rules** (`:412,417,422,427`). **Gate, don't delete** — confirm the SVG minimap still consumes the `.graph-node-*` classes first (it does, `graph-contextual.js:110-123`). Update the stale JS comment.
- **Responsive bottom-sheet**: add `@media (max-width:768px)` (currently **none** in graph.css); convert the free-floating absolute `.graph-controls`/`.graph-legend` into one bottom sheet (max-height ~45vh, scrollable, toggle handle with `aria-expanded`), eliminating the controls/legend collision; desktop unchanged; surfaces from P0 tokens.
- **Touch pan/pinch**: `setupInteraction()` (`:302-356`) wires no touch despite `touch-action:none` (`:31`) killing native gestures — the canvas is **dead on mobile today**. Add touchstart/move/end (or Pointer Events): one-finger pan, two-finger pinch → `zoomAt` midpoint, tap → pick+navigate. Non-passive touchmove for `preventDefault`.
- **Camera controls**: bind the already-defined-but-unbound `fitToView` to a Fit button; add +/− zoom buttons (reuse `zoomAt`); Escape steps out of focus then fits.
- **Onboarding + hub labels at fit scale**: always label top ~15–20 hubs by connectivity even below `LABEL_SCALE` (precompute sorted once, screen-space spacing skip) so first paint has landmarks; dismissible hint overlay auto-hiding on first interaction.

**Files**: `bengal-graph-explorer.js`, `graph.css`, `graph-contextual.css`, `graph_visualizer.html`

**Constraints**: C2 (vanilla) · **C1: none baked** · C3 (chrome from P0 tokens) · C4 — focus ring is one arc/frame; key-nav reuses the picking grid; touch reuses rAF coalescing; hub labels capped + precomputed.

**New baked data**: none.

**Landmines**: scope key handling to canvas focus (don't capture while typing in search); pinch/tap/pan disambiguation is fiddly — test on real iOS/Android, not emulation; gate `nodeGlow`, never delete (SVG minimap consumes the classes).

**Acceptance**: graph fully operable by keyboard with a visible focus ring; SR announces focused-node analysis; zero un-gated animations under reduced-motion; phone shows a usable bottom-sheet with no panel collision and working touch pan/pinch; first paint shows labeled hub landmarks + a hint.

---

### P4 — Minimap Parity + Insights Panel (mixed; one optional bake)

Brings the per-page minimap up to explorer parity and surfaces site-structure intelligence. Mostly zero-bake; the Insights node lists inherit P0.5 ordering; one optional flagged 2-hop bake.

**Deliverables (no new coordinates)**
- **Minimap as a real card** (`graph-contextual.js:78-141`): node radius from baked `n.size` (a real renderer change — currently hardcoded `8/6/5` at `:110`; the data already ships, but post-P1 that value is PageRank-based, so the minimap node sizing *changes* the moment this rewire lands); edge stroke-width from baked `e.weight`; replace native `<title>` with the **already-styled-but-dead** `.graph-contextual-tooltip` (`graph-contextual.css:173-194`) populated like the explorer (reading_time + in/out refs + tag chips); render the **already-styled-but-dead** `.graph-contextual-section-header` with page title + "N connected pages." Clean up listeners in `cleanup()`.
- **Inline "Related pages" list** beside the minimap: ranked `<a>` links (sorted by connectivity) with role/affinity hints; doubles as the visible surface on narrow sidebars and the a11y fallback; capped at the existing ≤15.
- **Orphan empty-state**: instead of hiding on the 348 orphan pages (`graph-contextual.js:156-159` style early-return), render a small "This page isn't linked from elsewhere yet" card (keyed off baked `type==='orphan'`) linking to `/graph/` or the section index — surfacing orphan-detection exactly where it matters.
- **Insights panel on `/graph/` (stats-only bake):** extend the `stats` block with deterministically-sorted top-N lists from `reporter.py`/`analyzer.py` — top hubs, top PageRank, bridge pages (betweenness), modularity/community count — as a collapsible linked "Insights" panel. Top-N is bounded so JSON growth is trivial. **The betweenness/bridge list inherits P0.5's pivot-sort fix as a hard dependency** (it is the same `path_analysis.py:321` approximate path) — sort all lists by `(score desc, node-id)`, round emitted scores, and add them to the P0.5 parity test.

**Deliverable (optional, flagged, default-off) [BAKES DATA]**
- **2-hop minimap neighborhood**: optional faint outer ring of neighbors-of-neighbors in the baked `.graph` block + `compute_radial_layout` (`layout.py:362` already two-ring-capable). **Strictly cap** (15 direct + ≤10 second-hop); seed/sort/round exactly like the existing radial path; gate behind `theme.features` default-off; extend the P0.5 parity test to the new fields before enabling.

**Files**: `graph-contextual.js`, `graph-contextual.css`, `partials/graph-contextual.html`, `visualizer.py`, `reporter.py`, `json_generator.py`, `layout.py`, `graph_visualizer.html`

**Constraints**: C2 (vanilla) · C4 — ≤15 elements/page, trivial ×1208; Insights computed once via the shared cache; 2-hop hard-capped · C3 (P0 tokens) · **C1** — minimap card/list/orphan + Insights lists ship **no new coordinates** (Insights = bounded rounded scalar lists, gated on P0.5 ordering); **2-hop is the only new-coordinate bake** → full `_Rng`/sorted/`_round` + parity test, default-off.

**New baked data**: Insights top-N scalar lists in `stats` (rounded, P0.5-ordered); optionally 2-hop neighborhood coords in `.graph` (capped, seeded, default-off).

**Acceptance**: minimap shows header + count, size-encoded nodes, weighted edges, styled tooltip matching the explorer; orphan pages show a meaningful card instead of vanishing; Insights lists deterministically-sorted key pages as working links and pass the parity gate; 2-hop (if enabled) passes parity and stays under its node cap.

---

### P5 — Scale Headroom (5–10×) (runtime + bounded build)

Pure scale work; lands once the 1208 experience is great. **Re-measure the build-layout baseline first** — the circulated 6.2s/54s figures are unsourced. Each coordinate-changing layout tweak is a **separate, separately-revertable PR** so an `x_std` regression is attributable.

**Deliverables**
- **Edge LOD + path batching (runtime, no bake)** (`draw()` `:159-181`): batch same-style edges into `Path2D`/`beginPath..stroke` split into a few alpha tiers (weight-1 / weight-2 / highlighted) instead of per-edge `beginPath`; fade (don't hard-cut) non-highlighted edges when sub-pixel; additive low-alpha density for a "mass" read. Hoist `isVisible()` into a precomputed `visibleSet` recomputed only on query/filter change (currently called twice per edge per frame, `:165`).
- **Bounded build-layout cost — three SEPARATE measured PRs [each BAKES DATA]:** (a) rebuild the Barnes-Hut quadtree every K=2–4 iterations and reuse repulsion between (`force_on` is the hot path; tree rebuilt every iter `:257-266`); (b) lower the iteration formula (`:247`, `30·ln N` → tunable, capped) — **only if P1.3's measurement showed convergence headroom actually remains** (do not assume it; the speedup banks once); (c) deterministic early-exit when summed displacement < epsilon (`:313-321`). All constants fixed; convergence sum in sorted order; each re-records fixtures + passes the parity gate independently.
- **PageRank-driven min on-screen radius (runtime)**: keep hubs/high-PageRank nodes above a minimum radius when zoomed out (cap to the ~88 hubs) so the zoomed-out view reads as a labeled constellation (`bengal-graph-explorer.js:201`).

**Files**: `bengal-graph-explorer.js`, `layout.py`

**Constraints**: C4 (this *is* the scale lever) · **C1** — edge LOD/batching: none baked; the three layout PRs each change coords → re-record + parity in the same PR · C2 (Canvas only).

**New baked data**: revised normalized `(x,y)` from each of the three layout PRs (constants fixed, sums sorted, rounded).

**Landmines**: one `Path2D` can't vary per-edge alpha — split into tiers; edge LOD must fade not pop; early-exit epsilon too large → under-converged hairball, so validate `x_std` *improves*, not just that build is faster; any iteration/K change fails every pinned `graph.json` fixture — re-record in the same PR.

**Acceptance**: explorer holds ~60fps at 5–10× with edge batching + LOD; **re-measured** build-layout baseline drops and the superlinear curve flattens; parity holds after each re-record; zoomed-out view shows a legible hub constellation.

---

## Dependency / Sequencing Summary

```
P0 (tokens, unblocked now) ──┐
                             ├─> P1 (community/PageRank bake)   [palette needs P0; bake needs P0.5]
P0.5 (determinism floor) ────┘        ├─ P1.1 community id+color   [field bake]
   = HARD GATE + builds the           ├─ P1.2 pagerank→size        [field bake]
     missing live parity test         └─ P1.3 community-aware layout + weight springs  [SEPARATE PR, geometry bake]
                             │
P0 ──> P2 (focus/depth/deep-link)  [community label/color needs P1; tokens need P0; motion gated in-PR]
              └──> P3 (a11y/motion/mobile)  [keyboard nav consumes P2 focused-node]
P0 ──> P4 (minimap parity + insights)  [tokens P0; community tint needs P1; betweenness list needs P0.5 pivot-sort]
P1.3 ──> P5 (scale)  [measure P1.3 convergence BEFORE banking it for P5(b); ships last]
```

- **P0 is unblocked now** (#534/#535 merged). The explorer label-token fix can ship even ahead of the full migration.
- **P0.5 is the non-negotiable gate** before any community/PageRank/path data is baked, and it must *build* the live `graph.json` parity test (it does not exist today).
- **P1.3 and the three P5 layout tweaks are each their own coordinate-bake PR** — never bundled.
- P2/P3/P4 proceed after their listed deps; P5 ships last.

## Cross-Cutting Risks

1. **No existing parity backstop (P0.5)** — the build-snapshot fixture is skipped/stale; the layout test is isolated. P0.5 must construct a real two-cold-build `graph.json` parity gate before P1 bakes anything.
2. **Determinism root cause is the shared unsorted `site.pages` (P0.5)** — Louvain, PageRank, and path-pivot sampling all ride on it; fix the page order once and apply consistently, or P1.2/P4 bake non-reproducible fields too.
3. **Vacuous existing test** — `test_community_detection.py:test_random_seed_reproducibility` proves nothing for the unseeded build path; the new assertion must discriminate at the id level.
4. **#535 cascade tie-break (P0)** — applies to all 8 scattered dark panel blocks; conservative second-pass verify before deleting any.
5. **Canvas gradient/edge perf traps (P2/P5)** — bucketed caching + LOD mandatory; profile at 1208 and 5–10×.
6. **Coordinate-bake fixture churn (P1.3, P5×3)** — every baked-coord change re-records its fixture in the same PR; never bundle with unrelated drift.
7. **Convergence-speedup double-count (P1.3 vs P5b)** — measure after P1.3; P5's iteration-cap cut is conditional on remaining headroom, not assumed.
8. **P1 silently re-bakes the ×1208 `.graph` blocks and changes the size the minimap will read (P1.2 → P4)** — declared as a cross-effect in both phases.

---

## Proposed Issues / Sagas (issues-first)

**Epic:** "Knowledge graph: from utility to showcase" (parent; references #532 Pridelands for the color foundation).

**P0 — token migration (siblings under #532):**
- `graph: fix explorer label tokens (--color-text → --color-text-primary)` — standalone, ship first, no deps.
- `graph: migrate node/link palette to OKLCH + light-dark() tokens` (delete graph.css:566-717).
- `graph: migrate control/legend/tooltip panels to elevation tokens` (delete the 8 dark panel blocks).
- `graph: define deterministic OKLCH community palette tokens`.
- `graph: regular-node contrast + rim stroke`.
- `graph: minimap CSS → theme tokens (--graph-current)`.

**P0.5 — determinism floor (GATE):**
- `graph: canonical build-stable page order for all analyses` (sort by node-id).
- `graph: Louvain local PRNG + stable community renumber` (fixes community_detection.py:167,212,269-272).
- `graph: PageRank sorted iteration + round-before-serialize`.
- `graph: path-analysis sort pages before pivot sample` (fixes path_analysis.py:321).
- `graph: add live two-cold-build graph.json byte-parity test + id-stability assertion` (the missing gate).

**P1 — analysis surfacing [bakes data]:**
- `graph: bake community id + color, color graph by cluster` (P1.1).
- `graph: bake PageRank → node size` (P1.2).
- `graph: community-aware layout + edge-weight springs` (P1.3, separate PR, geometry re-record).

**P2 — interaction + depth (runtime):**
- `graph: click-to-focus spotlight + detail panel` (top pick).
- `graph: deep-linkable #node= focus + popstate back`.
- `graph: canvas node depth (cached bucketed gradients + LOD)`.
- `graph: entrance settle animation (reduced-motion gated)`.
- `graph: community/legend filter affordances (?community=)`.
- `graph: edge depth weighting (highlighted-subset gradients)`.

**P3 — a11y / motion / mobile (runtime/CSS):**
- `graph: keyboard nav + focus ring + aria-live status` (ship together).
- `graph: global reduced-motion gate (graph.css/graph-contextual.css, incl. nodeGlow)`.
- `graph: mobile bottom-sheet panels (@media max-width:768px)`.
- `graph: touch pan/pinch (canvas is dead on mobile today)`.
- `graph: camera control cluster (Fit / zoom buttons / Escape)`.
- `graph: hub labels at fit scale + onboarding hint`.

**P4 — minimap parity + insights:**
- `graph: minimap real card (size/weight/tooltip/header)` (top pick for this dimension).
- `graph: minimap related-pages list`.
- `graph: minimap orphan empty-state`.
- `graph: Insights/site-health panel on /graph/` (betweenness list depends on P0.5 pivot-sort).
- `graph: 2-hop minimap ring (feature-flagged, default-off)` [optional, bakes data].

**P5 — scale headroom:**
- `graph: edge LOD + Path2D batching + visibleSet hoist` (runtime).
- `graph: re-measure build-layout baseline on docs site` (prerequisite; no figures exist).
- `graph: bound BH rebuild cadence (K)` [bakes coords].
- `graph: iteration-cap cut` [bakes coords; conditional on P1.3 convergence measurement].
- `graph: layout early-exit epsilon` [bakes coords].
- `graph: PageRank min on-screen radius for zoomed-out legibility` (runtime).
