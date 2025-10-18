# Race Condition Fix Summary

## Issue Identified

**Error**: `FileNotFoundError` when trying to rename temp files during parallel page rendering:
```
page_rendering_error  error=[Errno 2] No such file or directory:
'...public/api/config/index.html.tmp' -> '...public/api/config/index.html'
```

## Root Cause

The atomic write function used **the same temp filename** for all concurrent writes to a file:
- Multiple threads writing to `index.html` all used `index.html.tmp`
- When Thread A renames the temp file, Thread B's rename fails with FileNotFoundError
- Classic race condition in parallel builds

## Solution

**Changed temp file naming** from:
```python
tmp_path = path.with_suffix(path.suffix + ".tmp")
# Example: index.html.tmp (COLLISION!)
```

**To unique filenames** per thread:
```python
pid = os.getpid()
tid = threading.get_ident()
unique_id = uuid.uuid4().hex[:8]
tmp_path = path.parent / f".{path.name}.{pid}.{tid}.{unique_id}.tmp"
# Example: .index.html.12345.140735268288512.a3b2c1d4.tmp (UNIQUE!)
```

## Files Modified

1. **`bengal/utils/atomic_write.py`**:
   - Updated `atomic_write_text()`
   - Updated `atomic_write_bytes()`
   - Updated `AtomicFile.__init__()`
   - Added imports: `threading`, `uuid`

2. **`tests/unit/utils/test_atomic_write.py`**:
   - Fixed `test_temp_file_cleaned_on_error` (mocked error instead of relying on missing directory)
   - Added `test_concurrent_writes_same_file` (regression test for this bug)

## Verification

✅ **All 19 unit tests pass**
✅ **Full build completes successfully** (394 pages in 3.4s)
✅ **No temp files left behind** after build
✅ **No race condition errors** in build logs
✅ **api/config/index.html** created successfully (42KB)

## Benefits

1. **Thread-safe**: Multiple threads can write to same file without collisions
2. **Process-safe**: Multiple processes can write safely
3. **Crash-safe**: Maintains original atomic write guarantees
4. **Clean**: Temp files are hidden (leading dot) and always cleaned up
5. **Fast**: No locks or synchronization needed

## Impact

This fix eliminates a critical bug in parallel builds that could cause:
- Random FileNotFoundError during builds
- Missing output files
- Inconsistent build results
- Build failures in CI/CD pipelines

The error was intermittent and only occurred when multiple threads tried to write the same file simultaneously (e.g., API documentation pages being regenerated or updated).
