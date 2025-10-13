# Atomic Write Race Condition Bug - FIXED ✅

## Problem

The `atomic_write_text()` function in `bengal/utils/atomic_write.py` had a race condition when multiple threads write to the same file simultaneously.

## Root Cause

Line 54: `tmp_path = path.with_suffix(path.suffix + ".tmp")`

All threads writing to `index.html` used the **same temp filename**: `index.html.tmp`

### Race Condition Scenario

```
Thread A: Write content to index.html.tmp
Thread A: Rename index.html.tmp → index.html (SUCCESS)
Thread B: Write content to index.html.tmp (new file)
Thread B: Try to rename index.html.tmp → index.html
   ERROR: FileNotFoundError if Thread A already moved it

OR:

Thread A: Start writing to index.html.tmp
Thread B: Overwrites index.html.tmp while A is writing
Thread A: Finishes rename (gets B's content - corruption!)
Thread B: Tries to rename → FileNotFoundError
```

## Solution Implemented ✅

Used **unique temp filenames** with PID + Thread ID + UUID:

```python
pid = os.getpid()
tid = threading.get_ident()
unique_id = uuid.uuid4().hex[:8]
tmp_path = path.parent / f".{path.name}.{pid}.{tid}.{unique_id}.tmp"
```

Example: `.index.html.12345.140735268288512.a3b2c1d4.tmp`

This guarantees:
- No collisions between threads
- No collisions between processes
- Hidden files (leading dot) for cleaner directory listings
- Automatic cleanup on any error

## Changes Made

1. **`bengal/utils/atomic_write.py`**: Updated all three functions:
   - `atomic_write_text()` - Uses unique temp files
   - `atomic_write_bytes()` - Uses unique temp files
   - `AtomicFile.__init__()` - Uses unique temp files

2. **`tests/unit/utils/test_atomic_write.py`**:
   - Fixed `test_temp_file_cleaned_on_error` (directory is now created automatically)
   - Added `test_concurrent_writes_same_file` - Regression test for this exact bug

## Testing

All 19 tests pass ✅:
- Existing tests continue to work
- New race condition test verifies concurrent writes to same file work correctly
- No temp files left behind after concurrent writes

## Evidence

Error from build logs (before fix):
```
page_rendering_error  error=[Errno 2] No such file or directory:
'/Users/llane/Documents/github/python/bengal/examples/showcase/public/api/config/index.html.tmp'
-> '/Users/llane/Documents/github/python/bengal/examples/showcase/public/api/config/index.html'
```

This error should no longer occur with the fix in place.
