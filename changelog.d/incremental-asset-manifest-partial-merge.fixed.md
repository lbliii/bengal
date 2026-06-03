Incremental builds no longer shrink the asset manifest when only some assets are
reprocessed. `_write_asset_manifest` rebuilt `asset-manifest.json` from just the
assets processed that run, so editing a single asset (a *partial* asset
incremental) dropped every unchanged entry — leaving a manifest with one entry.
That re-introduced the #130 failure class: a small-but-complete manifest makes
`inspect_asset_outputs` report a vacuously "complete" tree, blinding the
incremental reprocess safety net so a later missing CSS/JS output goes
unrecovered until a full rebuild. Incremental builds now *merge* — prior entries
whose output file still exists are carried forward, then the run's freshly
processed assets are overlaid (current entries win). Full builds still rebuild
from scratch, so they stay orphan-free. (#314)
