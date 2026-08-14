# Backlog harness (`drive` / `board` / `claim`)

**Lifecycle: Active**

Process harness for burning down Bengal GitHub work **beside** steward
`AGENTS.md` maps. See [`issue-lifecycle.md`](issue-lifecycle.md) for the issue
tree and lease rules. Magnet inventory from the 2026-08-14 peel campaign lives
in [`agent-parallelization.md`](agent-parallelization.md); **this file is the
serialize list agents must obey**.

`no collateral: contributor process experiment; not user-facing product`

## Simple invokes

| You say | Mode | What happens |
| --- | --- | --- |
| **`drive`** / **`orchestrate`** | Orchestrator (default) | Parent stays in chat; board → plan/unblock → delegate workers; loops until cap |
| **`drive epic #N`** / **`drive saga #N`** | Orchestrator scoped | Same, limited to that subtree |
| **`board`** / **`status`** | Read-only | Counts + ready list; no edits |
| **`burndown`** / **`unblock`** | Planner-only | Unblock queue; may be a subagent |
| **`plan #N`** | Planner-only | Investigation / freeze |
| **`claim #N`** / **`work #N`** | Worker escape hatch | Single Task in-process or one subagent |
| **`triage #N`** | Planner escape hatch | Make one issue swarm-ready (Path scope + Acceptance + `lifecycle-ready`) |
| **`ask stewards`** / **`review swarm`** | Contract review | Not backlog drive |

Prefer **`drive`** over bare `swarm`. `review swarm` is steward synthesis
(root `AGENTS.md`).

## Orchestrator contract

1. **Board** — ready / blocked / open investigations; pick active saga/epic.
2. **Plan gate** — If the ready queue is empty or Tasks lack Path scope /
   Acceptance, planner work first (`triage #N`).
3. **Delegate workers** — Claimable Tasks only; parallel when Path scopes do
   **not** overlap the edit-magnet list below.
4. **Integrate** — Track PRs; merge only when the user asks; drop
   `lifecycle-ready` on close.
5. **Stop** — Cap hit, empty ready queue, path conflict, or user interrupt.
   Never fake-unblock. Close a wave only when its PRs are on `main` with
   `lint-and-type` + `fast-check` green.

### Caps (per orchestrator turn unless the user overrides)

| Knob | Default |
| --- | --- |
| Planner unblocks | ≤5 Tasks → `lifecycle-ready`, or ≤2 investigations closed |
| Parallel workers | ≤3 if any Path overlaps a magnet; ≤5 if Path scopes are disjoint |
| Tasks closed this drive | ≤5 unless the user says keep going |
| Peel size | New files under ~400 lines |
| Megafile conflict | Serialize overlapping Path scopes; never two in-flight Tasks on the same magnet |

## Subagent briefs

**Planner**

```text
You are a Bengal planner. Read plan/issue-lifecycle.md + plan/BACKLOG.md.
No product runtime implementation under bengal/ except docs-only fixes.
Goal: <GOAL>.
Return: ready now / newly unblocked / still blocked (why) / paths touched.
```

**Worker**

```text
You are a Bengal worker. Claim only issues labeled task + lifecycle-ready.
Path scope is the allowlist — do not expand it.
Run Acceptance checks named on the issue.
Stop and report on Stop & Ask from nearest AGENTS.md.
Author/committer email: 25370251+lbliii@users.noreply.github.com (GH007).
Do not merge; leave the PR open unless the user explicitly asked.
PR body must include ## Performance Evidence (or skip-changelog + Not applicable).
```

## Edit-magnet serialize list

Do **not** parallelize Tasks that both edit any of these. LOC is
`origin/main` @ `c8788f9a1` (#707).

| Magnet | loc | Peel? | Why |
|--------|----:|:-----:|-----|
| `bengal/core/site/__init__.py` | 1245 | delete, don't peel | Highest fan-in; lifecycle shims `build`/`serve`/`clean` remain; Stop & Ask |
| `bengal/orchestration/content.py` | 1379 | **yes** | Last structural peel; twin with `content/discovery/` |
| `bengal/orchestration/build/` | pkg | serialize | Provenance wrapper + runner live here; opposite-half incremental edits diverge |
| `bengal/build/provenance/` | pkg | serialize with build/ | Engine + invalidation; one magnet with the phase wrapper |
| `bengal/rendering/pipeline/` | pkg | serialize | Coordinator + stages |
| `bengal/rendering/renderer/` | pkg | serialize | Facade + fallback |
| `bengal/server/` | pkg | serialize | `build_trigger/` + `dev_server.py` (1428, no peel) |
| `bengal/core/page/runtime.py` | 760 | no | Sole page body; grep-`Page` clash |
| `bengal/snapshots/render_plan.py` | 1534 | no | Frozen plan; unlocked `_WORKER_PAGE_CONTENT` is an FT hazard |
| `bengal/cli/milo_app.py` | 1193 | no | Command registration |
| `bengal/errors/suggestions.py` | 1223 | split | Data dict vs helpers; do not grow helper surface |
| `bengal/health/remediation/autofix.py` | 1341 | no | `bengal fix` writer |
| `bengal/autodoc/extractors/cli.py` | 1369 | no | CLI autodoc leaf |
| `bengal/autodoc/extractors/python/extractor.py` | 1100 | no | Python autodoc leaf |

**Peeled (serialize the package, do not re-split casually):** pipeline
`core.py` (575), renderer facade (326), build `__init__.py` (245),
`build_trigger/` facade (383), kida facade (400), render `orchestrator.py`
(200), provenance engine (736) + phase wrapper (583).

**Never parallel with anything:** `bengal/core/site/`, `bengal/core/page/`,
`bengal/orchestration/build/`, `bengal/rendering/pipeline/`,
`bengal/rendering/renderer/`, `bengal/server/`.

## Usually-safe parallel pairs

When Path scopes stay inside these pairs **and avoid magnets**:

- `bengal/css/` ∥ `bengal/analysis/`
- `bengal/capabilities/` ∥ `bengal/fonts/` / `bengal/icons/`
- `bengal/scaffolds/` ∥ `bengal/themes/default/` (CSS/JS only; not `dev_server.py`)
- `bengal/postprocess/output_formats/` ∥ `bengal/health/validators/` (not `autofix.py`)
- `bengal/autodoc/extractors/python/` ∥ `bengal/content_types/`
- `bengal/config/` ∥ `bengal/protocols/`
- `bengal/audit/` ∥ `bengal/debug/`
- `bengal/plugins/` ∥ `bengal/parsing/backends/patitas/directives/builtins/`
- `tests/roots/` fixture-only ∥ matching unit tests, if production magnets are untouched

**Disjoint leftovers after the 2026-08 peels** (first `drive` candidates):

- `orchestration/content.py` peel (solo — that magnet)
- `errors/suggestions.py` data/helper split
- `Section` / `Page.authors` `@cached_property` → `list` (FT; `core/section/` + `runtime.py` — serialize `runtime.py` if both)

Site `build`/`serve`/`clean` last (public API, caller migration).

## Status lines

Emit one short line before major steps, e.g.:

- `Orchestrator: board — 3 ready, 12 blocked`
- `Orchestrator: planner — unblock #N`
- `Orchestrator: worker ×2 — #A, #B`
- `Orchestrator: integrate — PR #…`

## Pilot

Until GitHub has a `lifecycle-ready` Task queue, Path-scoped work may be a
markdown checklist in a saga issue or in
[`agent-parallelization.md`](agent-parallelization.md). The lease is still
Path scope + machine Acceptance + no overlapping magnets — not chat memory.
