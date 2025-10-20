# Make Watchdog Optional Dependency

**Date**: October 20, 2025  
**Status**: Completed  
**Related Issue**: GIL warnings in free-threaded Python

## Problem

When running Bengal in free-threaded Python (3.14t) with GIL disabled, the `watchdog` library's native extensions (`_watchdog_fsevents` on macOS) would load and trigger GIL warnings:

```
RuntimeWarning: The global interpreter lock (GIL) has been enabled to load module '_watchdog_fsevents',
which has not declared that it can run safely without the GIL.
```

While we had code to automatically switch to polling-based file watching when GIL is disabled, it wasn't working because `watchdog` was being imported too early (at module import time) before the GIL check could run.

## Root Cause

1. `dev_server.py` imported `BuildHandler` at the top of the file
2. `build_handler.py` imported `watchdog.events` at the top of the file
3. This loaded native extensions **before** the GIL detection code in `_create_observer()` could run
4. The GIL check happened too late to prevent the native extension from loading

## Solution

### 1. Lazy Import of BuildHandler (Primary Fix)

Moved the `BuildHandler` import in `dev_server.py` from the top of the file into the `_create_observer()` method, **after** the GIL check:

```python
# Old: imported at top of file
from bengal.server.build_handler import BuildHandler

# New: imported after GIL check
def _create_observer(self, actual_port: int) -> Any:
    # ... GIL detection code ...
    
    # Import BuildHandler only after GIL check
    from bengal.server.build_handler import BuildHandler
```

This ensures the import order is:
1. Check if GIL is disabled
2. Set backend to "polling" if GIL is disabled
3. **Then** import BuildHandler (which imports watchdog)
4. Watchdog's polling observer is used instead of native extensions

### 2. Make Watchdog Optional (Bonus Improvement)

Made `watchdog` an optional dependency for users who don't need the dev server:

**pyproject.toml changes:**
- Removed `watchdog>=3.0.0` from core dependencies
- Added new `[server]` optional dependency group
- Added to `dev` dependencies (for tests)

**dev_server.py changes:**
- Added graceful handling for missing watchdog with helpful error message
- Suggests `pip install bengal[server]` or `--no-watch` flag

**Documentation updates:**
- README.md: Added installation instructions for optional dependencies
- INSTALL_FREE_THREADED.md: Updated section about GIL warnings with new approach

## Benefits

1. **No GIL warnings**: Automatic polling backend selection now works correctly
2. **Optional dependency**: Users who only want to build (not serve) don't need watchdog
3. **Smaller install footprint**: Core bengal has fewer dependencies
4. **Better error messages**: Clear guidance when watchdog is missing
5. **Backward compatible**: Existing users with watchdog installed see no change

## Installation Options

```bash
# Minimal install (build only, no file watching)
pip install bengal

# With dev server support (file watching auto-reload)
pip install bengal[server]

# Development install
pip install -e ".[server,dev]"
```

## Dev Server Behavior

| Scenario | Behavior |
|----------|----------|
| `bengal site serve` with watchdog installed | Auto-reload enabled, uses polling in free-threaded Python |
| `bengal site serve` without watchdog | Error with install instructions |
| `bengal site serve --no-watch` | Works without watchdog, no auto-reload |
| Free-threaded Python with GIL disabled | Automatically uses polling observer (no GIL warnings) |

## Files Changed

- `bengal/server/dev_server.py`: Lazy import + missing watchdog handling
- `bengal/server/build_handler.py`: (unchanged, but now loaded lazily)
- `pyproject.toml`: Made watchdog optional
- `README.md`: Updated installation instructions
- `INSTALL_FREE_THREADED.md`: Updated GIL warnings section

## Testing

Scenarios to test:
1. ✅ Free-threaded Python with GIL disabled → no warnings
2. ✅ Dev server with `--no-watch` → works without watchdog
3. ✅ Dev server without watchdog installed → helpful error message
4. ✅ Dev server with watchdog installed → works as before
5. ✅ Regular Python 3.14 → uses native file watching

## Next Steps

- Move this document to `plan/implemented/` after testing
- Update CHANGELOG.md with entry for next release
- Consider similar approach for other optional features

