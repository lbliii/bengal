The dev server no longer lets `asset-manifest.json` drift between its two output
buffers. The double buffer seeds the next staging buffer from the active one
using only the previous build's changed outputs, but the asset manifest describes
the *currently served* buffer and is never rewritten on a content-only rebuild —
so it never appeared in the changed-output delta and could fall a generation
behind. A buffer that became active carrying a stale manifest could omit entries
for assets it actually held (`asset_url` failing to resolve them) and make
`inspect_asset_outputs` mis-report completeness — the residual dev-server
mechanism behind #130's intermittent "unstyled, fixed by restart" symptom that
the build-API fix (#313) did not cover. `prepare_delta_staging` now takes an
`always_sync` set and the dev server passes `asset-manifest.json`, so the manifest
is re-seeded from the active buffer on every rebuild and both buffers stay
consistent. Adds the first dev-server-realistic buffer/swap/delta integration
harness. (#315)
