# Incremental Build Bug - Root Cause & Fix

## Root Cause Identified ✅

The problem is a **timing issue in config change detection**.

### The Flow

1. **Full build** (line 223 in benchmark):
   ```python
   site = Site.from_config(site_root)
   stats = site.build(parallel=True, incremental=False)
   ```
   - Config file hash: `ABC123`
   - Cache is saved with hash: `ABC123`

2. **Incremental build** (line 261 in benchmark):
   ```python
   stats = site.build(parallel=True, incremental=True)
   ```
   - `check_config_changed()` is called
   - Loads cache with hash: `ABC123`
   - Reads config file, computes hash: `ABC123`
   - Compares: `ABC123 == ABC123`? **YES, they match!**
   - Returns `False` (config NOT changed) ✅

3. **BUT** - line 100 in `incremental.py`:
   ```python
   changed = self.cache.is_changed(config_file)
   # Always update config file hash (for next build)
   self.cache.update_file(config_file)  # <-- THIS!
   ```

   Updates the hash anyway!

4. **The REAL problem**:
   The issue is that after the incremental build finishes, the cache is saved with the updated hash. But if the BUILD FAILS or is interrupted before `cache.save()`, the next build loads the OLD hash and detects a change!

Actually wait... let me re-read the benchmark output. It says "Config file changed" on the incremental build, which means `check_config_changed()` returned `True`.

Let me check if there's a cache persistence issue...
