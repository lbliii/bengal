# `bengal.build` — Incremental Build Domain

This package owns **contracts, types, and provenance data** for incremental builds. It intentionally contains no I/O orchestration logic (see `bengal.orchestration`) and no cache storage logic (see `bengal.cache`).

## Contents

| Subpackage | Purpose |
|------------|---------|
| `contracts/` | Key functions, protocols, result types for build contracts |
| `provenance/` | Provenance types, filter logic, and store for content-addressed change detection |

## Distinction from `bengal.orchestration.build`

- **`bengal.build`** (this package): Passive domain logic — contracts, provenance data structures, change detection algorithms. No I/O, no orchestration.
- **`bengal.orchestration.build`**: Active coordination — phases, lifecycle, sequencing. Orchestrates the build pipeline using types from this package.
