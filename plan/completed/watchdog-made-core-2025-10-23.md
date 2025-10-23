# Watchdog Made Core Dependency + python-markdown Removed

**Date**: October 23, 2025  
**Status**: Completed  
**Decision**: Make watchdog core, remove python-markdown

## Rationale

After testing in Python 3.14t, we found that:
1. **Watchdog works** - Hot reload functional with polling backend in free-threaded Python
2. **Average users need hot reload** - Writers want live preview without manual refresh
3. **Two markdown parsers unnecessary** - Mistune is default and performs better

## Changes Made

### 1. Moved watchdog to core dependencies

**Before:**
```toml
[project.optional-dependencies]
server = ["watchdog>=3.0.0"]
```

**After:**
```toml
dependencies = [
    # ... other deps ...
    "watchdog>=3.0.0",  # File watching for dev server (bengal site serve)
]
```

### 2. Removed python-markdown from core

**Before:**
```toml
dependencies = [
    "markdown>=3.5.0",
    "mistune>=3.0.0",
    # ...
]
```

**After:**
```toml
dependencies = [
    "mistune>=3.0.0",  # Only mistune (default, faster)
    # ...
]
```

### 3. Updated parser factory with helpful error

If user explicitly configures `markdown_engine: "python-markdown"` without installing it:
```python
raise ImportError(
    "python-markdown parser requested but not installed. "
    "Install with: pip install markdown"
)
```

### 4. Documentation updates

- **README.md**: Removed `bengal[server]` install instructions
- **INSTALL_FREE_THREADED.md**: Simplified watchdog instructions
- **pyproject.toml**: Removed `[server]` optional dependency group

## Final Dependency Count

**14 core dependencies** (down from 15):
- click, mistune, jinja2, pyyaml, toml, pygments, python-frontmatter
- csscompressor, jsmin, pillow, psutil, rich, questionary, watchdog

**1 optional extra**:
- `css` - lightningcss for advanced CSS optimization

## Benefits

✅ **Simpler install** - No confusion about `bengal[server]` extra  
✅ **Hot reload by default** - Better UX for content writers  
✅ **Works in Python 3.14t** - Polling backend avoids GIL issues  
✅ **One markdown parser** - Clearer choice (mistune is default)  
✅ **python-markdown still available** - Users can manually install if needed

## Testing

Tested scenarios:
- ✅ `bengal site serve` in Python 3.12 (native observer)
- ✅ `bengal site serve` in Python 3.14t (polling observer)
- ✅ Hot reload works in both versions
- ✅ Build without python-markdown installed (uses mistune)
- ✅ Explicit python-markdown config shows helpful error

## GIL Warning Status

**Current behavior in Python 3.14t**:
- GIL warning appears once at import (cosmetic only)
- Polling observer is used automatically
- No functional impact on hot reload
- Can be suppressed with `PYTHONWARNINGS=ignore::RuntimeWarning` if desired

## Related Files

- `pyproject.toml` - Dependency changes
- `bengal/rendering/parsers/__init__.py` - ImportError for python-markdown
- `bengal/server/dev_server.py` - Already had lazy import + GIL detection
- `README.md` - Simplified install instructions
- `INSTALL_FREE_THREADED.md` - Updated watchdog section
