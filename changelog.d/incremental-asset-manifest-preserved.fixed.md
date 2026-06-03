Incremental builds no longer corrupt the asset manifest. When a build had no
assets to process (e.g. a content-only edit during `bengal serve`), the asset
phase overwrote `asset-manifest.json` with an empty manifest. A present-but-empty
manifest makes the output-integrity check (`inspect_asset_outputs`) report a
vacuously "complete" asset tree (manifest present, zero entries, zero missing),
which blinded the incremental reprocess safety net on later builds — so if a CSS
or JS output went missing it was never regenerated until a full rebuild
(restart). The asset phase now preserves the existing manifest when there is
nothing to reprocess (the output tree is unchanged, so the manifest is still
accurate); the empty baseline is only written when no prior manifest exists.
Adds theme-provided-CSS hot-reload regression coverage. (#130)
