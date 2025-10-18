# Asset Temporary File Race Condition Fix

## Issue

During parallel asset processing, the system was encountering errors:
```
asset_batch_processing_failed  total_errors=5 total_assets=21 success_rate=76.2%
Failed to process .../favicon-16x16.png: unknown file extension: .tmp
```

## Root Cause Analysis

There were **two related problems**:

### Problem 1: Non-Unique Temp Files in Image Optimization
In `bengal/core/asset.py` line 364, image optimization used a non-unique temp file pattern:
```python
tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
# Example: favicon-16x16.png.tmp (COLLISION RISK!)
```

This caused race conditions when multiple threads optimized images concurrently:
- Thread A creates `favicon-16x16.png.tmp`
- Thread B creates `android-chrome-192x192.png.tmp`
- Both might collide or interfere with each other's operations

### Problem 2: PIL Cannot Determine Format from `.tmp` Extension
When PIL's `Image.save()` is called with a `.tmp` file, it tries to determine the image format from the file extension and fails:
```python
image.save(tmp_path, optimize=True, quality=85)
# ERROR: ValueError: unknown file extension: .tmp
```

### Problem 3: Asset Discovery Picks Up Temp Files
`bengal/discovery/asset_discovery.py` didn't filter out `.tmp` files, so if temporary files existed during discovery (e.g., from a previous failed build), they would be discovered as assets and fail processing.

## Solution Implemented

### Fix 1: Use Unique Temp Files (Like atomic_write.py)
Updated `bengal/core/asset.py` to use the same unique temp file pattern as `atomic_write.py`:
```python
pid = os.getpid()
tid = threading.get_ident()
unique_id = uuid.uuid4().hex[:8]
tmp_path = output_path.parent / f".{output_path.name}.{pid}.{tid}.{unique_id}.tmp"
# Example: .favicon-16x16.png.12345.67890.abc123.tmp (UNIQUE!)
```

### Fix 2: Explicitly Specify Image Format
Determine the image format from the **original file extension** (not `.tmp`) and pass it to PIL:
```python
img_format = None
ext = output_path.suffix.upper().lstrip(".")
if ext in ("JPG", "JPEG"):
    img_format = "JPEG"
elif ext in ("PNG", "GIF", "WEBP"):
    img_format = ext

self._optimized_image.save(tmp_path, format=img_format, optimize=True, quality=85)
```

### Fix 3: Filter `.tmp` Files in Asset Discovery
Added filtering in `bengal/discovery/asset_discovery.py`:
```python
# Skip temporary files (from atomic writes and image optimization)
if file_path.suffix.lower() == ".tmp":
    continue
```

## Files Modified

1. **`bengal/core/asset.py`**:
   - Updated image optimization to use unique temp files (lines 363-385)
   - Added explicit format specification for PIL Image.save()

2. **`bengal/discovery/asset_discovery.py`**:
   - Added `.tmp` file filtering (lines 45-47)

3. **`tests/unit/core/test_parallel_processing.py`**:
   - Added `test_concurrent_image_optimization_no_temp_file_collision()` test

4. **`tests/unit/discovery/test_asset_discovery.py`** (NEW):
   - Created comprehensive test suite for asset discovery
   - Added `test_skips_temp_files()` test
   - Added `test_ignores_temp_files_during_parallel_processing()` test

## Tests

All tests pass ✅:
- **10/10** asset discovery tests pass
- **13/13** parallel processing tests pass
- New regression test verifies concurrent image optimization works without collisions
- Verified no temp files are left behind after processing

## Benefits

1. **Thread-safe**: Multiple threads can optimize images concurrently without collisions
2. **Process-safe**: Multiple processes can work safely (PID included in temp filename)
3. **Crash-safe**: Maintains atomic write guarantees with cleanup on error
4. **Clean**: Temp files are hidden (leading dot) and filtered from discovery
5. **Consistent**: Uses same pattern as `atomic_write.py` for all atomic operations

## Verification Commands

```bash
# Run asset discovery tests
python -m pytest tests/unit/discovery/test_asset_discovery.py -v

# Run parallel processing tests
python -m pytest tests/unit/core/test_parallel_processing.py -v

# Run full test suite
python -m pytest tests/
```
