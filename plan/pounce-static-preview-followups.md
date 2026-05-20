# Pounce Static Preview Follow-Ups

**Status**: drafted

## Problem

`bengal preview` now serves completed output through Pounce static handling, but
Bengal does not yet generate precompressed `.gz` or `.zst` sidecars. Serving
existing sidecars is safe because it does not change the build output contract.
Generating sidecars is a separate output feature: it affects stale-output
cleanup, cache/change tracking, manifests, deploy size, and complete-build
readiness.

## Goals

- Keep Bengal pure Python and dependency-light by using stdlib compression for
  gzip and a separately approved strategy for zstd.
- Generate sidecars only from finalized bytes at finalized output paths.
- Write sidecars atomically with `atomic_write_bytes`.
- Remove stale sidecars when the primary output is replaced or deleted.
- Record sidecars in changed-output tracking so buffered rebuilds and preview
  serving see a coherent snapshot.
- Keep sidecars out of logical asset manifests unless a manifest explicitly
  models physical output files.
- Prove sequential and parallel builds produce the same sidecar set.

## Non-Goals

- No build-time precompression in the initial `bengal preview` implementation.
- No new runtime dependency without a separate approval checkpoint.
- No mutation of `SourcePage`, `ParsedPage`, or `RenderedPage`.
- No dev-server-only compressed files that deployment builds do not produce.
- No Pounce metrics or introspection endpoints as part of this work.

## Proposed Contract

Add an explicit output-level setting, not a dev-server setting:

```toml
[output.precompression]
enabled = true
formats = ["gzip"]
```

Open question: zstd requires either a stdlib-free implementation path, an
optional dependency, or a Pounce-side helper. Do not expose `"zstd"` until that
choice is made.

## Implementation Order

1. Asset sidecars only.
   Generate sidecars after the asset pipeline resolves final fingerprinted
   filenames. Clean stale `.gz` and `.zst` siblings when the primary file
   changes or disappears. Add unit tests under `tests/unit/assets`.

2. Site-wide generated artifacts.
   Extend the finalized-output inventory for JSON, XML, TXT, and feed files
   before sidecars are generated. Add integration proof for search indexes,
   feeds, sitemap, robots, and llms output.

3. HTML sidecars.
   Generate only after rendering and postprocess transforms settle. Prove that
   custom 404 pages, nested indexes, and versioned output paths get sidecars
   from final bytes.

4. Preview verification.
   Add end-to-end tests that `bengal preview` serves generated sidecars through
   Pounce with `Content-Encoding`, `Vary`, ETag, `HEAD`, and range behavior.

## Pounce Requests

- Public static middleware constructor that accepts a fallback ASGI app without
  importing `pounce._static.StaticMount`.
- Optional documented helper for generating sidecars with the same encoding
  names and freshness rules Pounce uses when serving.
- A static-serving test fixture or probe API that exposes which physical file
  was selected for a request, useful for downstream contract tests.

## Required Proof

- `uv run pytest tests/unit/assets -q`
- `uv run pytest tests/unit/server tests/integration -q` for the affected
  preview/static paths
- `make ty`
- `uv run bengal build --source site`
- Benchmarks or before/after timing for large static asset sets before enabling
  sidecars by default

## Steward Notes

- Server: keep `serve` and `preview` behavior distinct; preview may consume
  sidecars, but dev serving must not rely on dev-only generated files.
- Build/assets: sidecars are output artifacts and must use atomic writes and
  stale cleanup.
- Rendering: sidecars are derived from finalized bytes and must not mutate
  immutable pipeline records.
- CLI/config/docs: any config key needs defaults, validation, docs, examples,
  tests, and changelog in the same implementation PR.
