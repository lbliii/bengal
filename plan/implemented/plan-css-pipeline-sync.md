## Title
CSS pipeline parity between dev and production

## Status
- Owner: AI assistant
- Created: 2025-11-23
- State: Implemented (2025-11-23)

## Problem
- Repeated incidents show GitHub Pages still serving stale fingerprinted bundles (e.g., `style.95230091.css`) after local fixes
- Dev mode bypasses fingerprinting/minification, so regressions stay hidden until production deploys
- `asset_url()` currently glob-matches any `stem.*.suffix` under `public/assets`, so old hashes remain indefinitely if the directory isn’t cleaned
- Missing typography tokens in stale bundles caused headings to collapse to default sizes despite correct code in source

## Goals
1. Guarantee that every production deploy serves the same CSS that developers verified locally
2. Eliminate manual cache-busting steps (rm public/assets, hard refresh) from the release checklist
3. Provide deterministic mapping between logical assets and fingerprinted output so templates never guess
4. Keep dev ergonomics (fast rebuilds, unfingerprinted CSS) intact

## Non-Goals
- Replacing the Node-based optional asset pipeline
- Redesigning theme CSS
- Delivering alternative CDN tooling

## Proposed Solution

### 1. Deterministic asset manifest
- During `AssetOrchestrator.process`, emit `public/asset-manifest.json` that records `{ "css/style.css": "css/style.<hash>.css" }`
- Use exact entry metadata (hash, mtime, size) to avoid ambiguity and capture future fields (integrity hashes, CDN URLs)
- Update `TemplateEngine._asset_url()` to consult the manifest first; only fall back to globbing for backward compatibility (warn when used)
- Manifest file doubles as a deploy artifact for downstream automation (CI can diff to confirm rebuild)

### 2. Remove stale fingerprinted artifacts automatically
- Before writing a new fingerprinted file, delete prior siblings that match the same logical stem (`style.*.css`)
- Avoid global `rm -rf public/assets` by scoping cleanup per asset type; safe even in incremental builds
- Preserve non-fingerprinted files (`fonts.css`, images) unless `optimize_assets` rewrites them

### 3. Enforce clean output in CI
- Extend publish workflow to run `bengal site clean && bengal build` (or equivalent `--clean-output` flag) so manual `rm` isn’t needed
- CI can verify the manifest matches the working tree (`git diff --exit-code public/asset-manifest.json`)

### 4. Visibility tooling
- Add `bengal assets status` CLI command to print which logical assets map to which fingerprint, along with last modified time
- Developer docs: new “Dev vs Production CSS” section that explains how to diff `asset-manifest.json` and troubleshoot mismatches

## Work Breakdown
1. **Asset manifest**
   - Add dataclass + serializer under `bengal/assets/manifest.py`
   - Persist JSON in `site.output_dir`
   - Unit tests proving deterministic ordering and stable hashes
2. **Template resolver upgrades**
   - Inject manifest into `TemplateEngine` (lazy-loaded with cache invalidation)
   - Emit warning when a lookup falls back to globbing so we can fix stragglers
3. **Stale fingerprint cleanup**
   - Extend `Asset.copy_to_output()` (or orchestrator wrapper) to delete previous hashed siblings before copying new one
   - Regression test that two consecutive builds leave only one hashed file on disk
4. **CI / CLI support**
   - Provide `bengal site clean` (if missing) or add `--clean-output` flag
   - New CLI command to inspect manifest
   - Update docs/DEV_VS_PRODUCTION_ASSETS.md with the new workflow

## Testing Strategy
- Unit tests for manifest writer/reader
- Integration test in `tests/integration/assets` that builds twice and asserts:
  - `asset-manifest.json` exists and maps `css/style.css`
  - Only one fingerprinted CSS exists after the second build
  - `asset_url('css/style.css')` outputs the manifest entry
- End-to-end test in CI (GitHub Actions) that caches is invalidated by checking manifest hash

## Risks and Mitigations
- **Risk:** Manifest gets out of sync during failed builds → Mitigation: write to temp file + atomic rename only after success
- **Risk:** Cleaning hashed siblings during incremental build might delete files still referenced by currently served pages → Mitigation: cleanup happens immediately before writing the new file, so replacement is atomic
- **Risk:** Template changes may still reference raw `style.css` while manifest expects hashed path → Mitigation: `asset_url` signature unchanged; manifest is internal detail
