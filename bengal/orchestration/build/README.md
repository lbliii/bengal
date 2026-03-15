# `bengal.orchestration.build` — Build Lifecycle Coordination

This package coordinates the **entire build pipeline** — phases, sequencing, and lifecycle. It delegates to specialized orchestrators and uses types from `bengal.build` for contracts and provenance.

## Contents

| Module | Purpose |
|--------|---------|
| `__init__.py` | `BuildOrchestrator` — main coordinator |
| `initialization.py` | Phases 1–5: fonts, discovery, cache, config, filtering |
| `content.py` | Phases 6–11: sections, taxonomies, menus, related posts, indexes |
| `rendering.py` | Phases 13–16: assets, render, update pages, track dependencies |
| `finalization.py` | Phases 17–21: postprocess, cache save, stats, health, finalize |
| `provenance_orchestration.py` | Phase 5: provenance-based incremental filtering (uses `bengal.build.provenance`) |

## Distinction from `bengal.build`

- **`bengal.build`**: Passive domain — contracts, provenance types, change detection. No I/O, no orchestration.
- **`bengal.orchestration.build`** (this package): Active coordination — phases, lifecycle, sequencing. Orchestrates the build using types from `bengal.build`.
