# Dev Server vs Production: Asset Differences

## Key Differences That Could Affect CSS

### 1. **CSS Bundling** ✅ Same in Both
- **Dev**: CSS is bundled (minification disabled)
- **Production**: CSS is bundled (minification enabled)
- **Impact**: The `@layer` preservation bug affects **both** equally
- **Why it might work locally**: You may have rebuilt after the fix, but production hasn't

### 2. **Minification** ⚠️ Different
- **Dev**: `minify_assets = False` (faster rebuilds, easier debugging)
- **Production**: `minify_assets = True` (smaller files)
- **Impact**: If minification breaks CSS, it only affects production
- **Note**: Our fix handles both minified and unminified CSS

### 3. **Fingerprinting** ⚠️ Different
- **Dev**: `fingerprint_assets = False` (stable filenames for hot reload)
- **Production**: `fingerprint_assets = True` (cache busting)
- **Impact**: Filenames differ, but shouldn't affect CSS content

### 4. **Browser Caching** ⚠️ Different
- **Dev**: Sends `Cache-Control: no-cache` headers (always fresh)
- **Production**: May cache CSS files (browser/CDN caching)
- **Impact**: Production might serve **old bundled CSS** from cache
- **Solution**: Hard refresh (Cmd+Shift+R) or clear cache

### 5. **Base URL** ⚠️ Different
- **Dev**: `baseurl = ""` (serves from `/`)
- **Production**: May have `baseurl = "/repo-name"` (serves from subdirectory)
- **Impact**: If CSS uses absolute paths or baseurl-dependent paths, could break
- **Note**: CSS `@import` paths are relative, so shouldn't be affected

### 6. **File Serving** ✅ Same
- **Dev**: Serves from `public/` directory (output_dir)
- **Production**: Serves from `public/` directory
- **Both**: Use bundled CSS files from the build output

### 7. **Asset Manifest & Cleanup** ✅ Now Unified
- **Dev**: Still serves unfingerprinted assets directly for instant reloads
- **Production**: Uses `asset-manifest.json` (written during `bengal site build`) to map logical assets → fingerprinted outputs
- **Impact**: Templates never guess hashes, and stale files such as `style.*.css` are deleted automatically during each build
- **Tip**: Run `bengal assets status` or inspect `public/asset-manifest.json` to confirm what production will serve

## Most Likely Cause of Your Issue

**Browser caching of old bundled CSS** in production.

The `@layer` preservation bug existed in both dev and production. If you:
1. Fixed the bug locally
2. Rebuilt locally (dev server auto-rebuilds)
3. Saw it working locally ✅
4. But production still shows old behavior ❌

Then production is likely serving **cached CSS** from before the fix.

## Solutions

### Immediate Fix
1. **Hard refresh** production site: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
2. **Clear browser cache** for the production domain
3. **Check CDN cache** (if using GitHub Pages CDN, may need to wait for cache expiry)
4. **Rebuild assets from a clean slate**: `bengal site build --clean-output`

### Verification
1. **Check the bundled CSS** in production:
   - Open DevTools → Network tab
   - Reload page
   - Find `style.css` (or `style.{hash}.css`)
   - Check if `@layer tokens` blocks are preserved
   - Check if typography variables (`--font-size-base`, etc.) are present

2. **Compare dev vs production CSS**:
   ```bash
   # Dev (after rebuild)
   curl http://localhost:5173/assets/css/style.css > dev-style.css

   # Production
   curl https://your-site.github.io/assets/css/style.css > prod-style.css

   # Compare
   diff dev-style.css prod-style.css
   ```

3. **Inspect the manifest and CLI status output**:
   ```bash
   bengal assets status                     # Human-friendly summary
   cat public/asset-manifest.json | jq '.'  # Full JSON if you prefer
   ```

### Long-term Fix
1. **Run `bengal site build --clean-output` in CI** so stale fingerprinted bundles never ship
2. **Verify** the bundled CSS includes `@layer` blocks *and* appears in `asset-manifest.json`
3. **Use `bengal assets status`** (locally and/or in pipelines) to confirm logical paths resolve to the expected fingerprints
4. **Add cache headers** to force CSS refresh on new deployments

## Why Dev Might Work But Production Doesn't

1. **You rebuilt locally** after fixing the bug → dev has correct CSS
2. **Production hasn't been rebuilt** → still has old broken CSS
3. **Browser cached** the old production CSS → serves stale version
4. **CDN cached** (GitHub Pages) → serves stale version

## Testing Checklist

- [ ] Verify production CSS includes `@layer tokens` blocks
- [ ] Verify typography variables are defined in production CSS
- [ ] Hard refresh production site
- [ ] Compare dev vs production bundled CSS
- [ ] Rebuild production with `bengal site build --clean-output` if needed
- [ ] Check CDN cache headers
- [ ] Inspect `public/asset-manifest.json` (or `bengal assets status`) for correct mappings
