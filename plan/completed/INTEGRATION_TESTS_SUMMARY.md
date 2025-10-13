# Integration Tests: Full → Incremental Build Sequence

**Status:** ✅ Complete (9/9 tests passing)

## What We Have Now

Created comprehensive integration tests that validate the **critical "full → incremental" build sequence** that was broken before our fixes.

### Test Suite: `test_full_to_incremental_sequence.py`

**Location:** `tests/integration/test_full_to_incremental_sequence.py`

**Coverage:** 9 tests covering:

#### 1. Basic Functionality Tests (6 tests)

1. **`test_full_build_saves_cache`**
   - Validates cache is created after full builds
   - Checks cache contains file hashes and config

2. **`test_incremental_after_full_build`**
   - Tests full → incremental sequence
   - Validates cache hits (50) and misses (0)

3. **`test_incremental_single_page_change`**
   - Modifies one page, checks only it gets rebuilt
   - Validates speedup (≥2x faster)
   - Checks file modification times

4. **`test_config_change_triggers_full_rebuild`**
   - Modifies config, validates full rebuild happens

5. **`test_first_incremental_build_no_cache`**
   - Tests incremental build when no cache exists
   - Validates fallback to full build

6. **`test_multiple_incremental_builds`**
   - Tests sequence: full → incr (no changes) → incr (1 change) → incr (no changes)
   - Validates cache hits/misses at each step

#### 2. Regression Tests (3 tests)

These tests specifically validate the bugs we fixed:

1. **`test_bug_cache_not_saved_after_full_build`** (Bug #1)
   - **Bug:** Cache only saved when `incremental=True`, causing first incremental build to fail
   - **Fix:** Always save cache after successful builds
   - **Test:** Validates cache exists after full build with `incremental=False`

2. **`test_bug_config_hash_not_populated`** (Bug #2)
   - **Bug:** `check_config_changed()` only called when `incremental=True`, so config hash never in cache
   - **Fix:** Always call `check_config_changed()` to populate cache
   - **Test:** Validates config hash in cache after full build

3. **`test_cache_survives_site_reload`** (Integration)
   - **Scenario:** Create Site object, build, destroy object, create new Site, build incrementally
   - **Validates:** Cache persists across Site object recreation (simulates restarts)

---

## Key Metrics Validated

Each test validates these critical metrics:

1. **Cache Hits/Misses**
   - `stats.cache_hits` - number of pages loaded from cache
   - `stats.cache_misses` - number of pages rebuilt
   - Full build (no cache): `hits=0, misses=N`
   - Incremental (no changes): `hits=N, misses=0`
   - Incremental (1 change): `hits=N-1, misses=1`

2. **Build Times**
   - Full build: baseline time
   - Incremental: should be significantly faster (≥2x)

3. **File Modifications**
   - Check actual file mtimes to verify only changed pages were written

4. **Cache Persistence**
   - `.bengal-cache.json` exists after builds
   - Contains file hashes, config hash, parsed content

---

## What These Tests Catch

### Would Have Caught Original Bugs

✅ **Bug #1 (Cache Not Saved):**
- `test_bug_cache_not_saved_after_full_build` would fail
- Error: "BUG: Cache not saved after full build with incremental=False"

✅ **Bug #2 (Config Hash Not Populated):**
- `test_bug_config_hash_not_populated` would fail
- Error: "BUG: Config file hash not in cache after full build"

✅ **Bug #3 (Benchmark Creating New Site Objects):**
- `test_cache_survives_site_reload` would fail
- Error: "New site instance should use persisted cache"

### Protects Against Future Regressions

These tests will immediately fail if:
- Someone changes cache save logic back to conditional
- Config hash checking gets moved to wrong place
- Incremental build logic gets broken
- Cache persistence is compromised

---

## Test Execution

```bash
# Run all integration tests
pytest tests/integration/test_full_to_incremental_sequence.py -v

# Run specific test
pytest tests/integration/test_full_to_incremental_sequence.py::TestFullToIncrementalSequence::test_incremental_after_full_build -v

# Run regression tests only
pytest tests/integration/test_full_to_incremental_sequence.py::TestIncrementalBuildRegression -v
```

**Current Status:** All 9 tests passing in ~18 seconds

---

## Notes on Test Design

### Why `cache_hits/cache_misses` Instead of `skipped`?

The `skipped` flag is only set to `True` when:
1. No pages need rebuilding, AND
2. No assets need processing, AND
3. No taxonomies need regenerating

With tags enabled (which most real sites have), `skipped` will be `False` even when nothing changed, because taxonomy pages need regeneration.

**Better metric:** `cache_hits` and `cache_misses` directly measure whether pages are being reused from cache (the core of incremental builds).

### Why `time.sleep(0.15)`?

File modification times have limited precision (typically 1ms on modern systems, but can be coarser). Adding a small delay ensures mtime changes are detectable by the incremental build system.

Without this, rapid modifications might have the same mtime, causing the cache to think nothing changed.

---

## Integration with CI/CD

These tests should be:

1. **Required for PR approval** - No PR merges without passing these tests
2. **Run on every commit** - Part of standard test suite
3. **Fast enough for local dev** - 18s for 9 tests (2s per test avg)

Add to CI pipeline:

```yaml
# .github/workflows/test.yml
- name: Run integration tests
  run: pytest tests/integration/test_full_to_incremental_sequence.py -v --cov
```

---

## Future Enhancements

Potential additions to the test suite:

1. **Large Scale Tests**
   - Test with 1,000+ pages to validate cache performance at scale

2. **Concurrent Builds**
   - Test cache locking/integrity with parallel builds

3. **Cache Corruption**
   - Test recovery when cache file is corrupted or incomplete

4. **Disk Space**
   - Test behavior when disk is full during cache save

5. **Permission Errors**
   - Test behavior when cache directory is read-only

---

## Conclusion

✅ **We now have comprehensive integration tests for the "full → incremental" sequence.**

These tests:
- Would have caught all 3 bugs we fixed
- Validate cache persistence across builds and Site object recreation
- Protect against future regressions
- Run fast enough for local development
- Are documented with clear bug history and expected behavior

**Status:** Ready for production use and CI/CD integration.
