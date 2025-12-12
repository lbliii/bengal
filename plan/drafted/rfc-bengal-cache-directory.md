# RFC: Centralize and Clean Up `.bengal/` Cache Directory

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-11  
**Confidence**: 85% 🟢

---

## Executive Summary

Refactor the `.bengal/` cache directory to:
1. Centralize the hardcoded `.bengal` string into a single constant
2. Standardize directory structure with clear subdirectory organization
3. Relocate the inconsistent `.bengal-cache/templates` from output directory
4. Add documentation and optional configurability for cache location

---

## Problem Statement

### Current Issues

#### 1. Hardcoded `.bengal` String (39+ occurrences)

The string `.bengal` appears hardcoded throughout the codebase:

```python
# bengal/orchestration/incremental.py:122
cache_dir = self.site.root_path / ".bengal"

# bengal/cache/utils.py:28
cache_dir = Path(site_root_path) / ".bengal"

# bengal/cli/commands/clean.py:104
cache_dir = site.root_path / ".bengal"

# ... 36+ more instances
```

This creates maintenance burden and makes it difficult to:
- Change the directory name
- Make it configurable
- Document the convention consistently

#### 2. Inconsistent Template Cache Location

Template bytecode cache lives in a different location:

```python
# bengal/rendering/template_engine/environment.py:230
cache_dir = site.output_dir / ".bengal-cache" / "templates"
```

This places cache inside the `public/` output directory, which:
- Gets deployed with the site (unless manually excluded)
- Is inconsistent with other caches in `.bengal/`
- Uses different naming (`.bengal-cache` vs `.bengal`)

#### 3. No Clear Directory Structure

Current `.bengal/` contents are ad-hoc:

```
.bengal/
├── cache.json              # Build cache
├── page_metadata.json      # Page discovery cache
├── asset_deps.json         # Asset dependencies
├── taxonomy_index.json     # Taxonomy index
├── build_history.json      # Delta analyzer history
├── asset-manifest.json     # Asset manifest (optional)
├── server.pid              # Dev server PID
├── indexes/                # Query indexes
│   └── *.json
├── content_cache/          # Remote content cache
├── js_bundle/              # JS bundle temp files
├── logs/                   # Build/serve logs
│   ├── build.log
│   └── serve.log
├── metrics/                # Performance metrics
│   └── *.json
├── profiles/               # Profiling output
│   └── *.stats
└── themes/                 # Swizzle registry
    └── sources.json
```

Issues:
- No consistent grouping (caches, indexes, logs, temp files mixed)
- Some files at root, some in subdirs
- No documentation of structure

---

## Goals

1. **Single Source of Truth**: One constant for the cache directory name
2. **Consistent Structure**: Clear subdirectory organization
3. **Relocate Template Cache**: Move from output dir to `.bengal/`
4. **Optional Configurability**: Allow users to change cache location
5. **Documentation**: Clear documentation of directory structure
6. **Backwards Compatibility**: Migration path for existing caches

## Non-Goals

- Changing the default name from `.bengal`
- Encrypting or securing cache contents
- Remote cache storage (cloud, network drives)
- Cache sharing across projects

---

## Proposed Directory Structure

```
.bengal/                        # Project state directory (gitignored)
├── README.md                   # Auto-generated structure documentation
│
├── cache/                      # Build caches (hot path, compressed)
│   ├── build.json.zst         # Main build cache (renamed from cache.json)
│   ├── pages.json.zst         # Page metadata cache
│   ├── assets.json.zst        # Asset dependency map
│   └── taxonomy.json.zst      # Taxonomy index
│
├── indexes/                    # Query indexes
│   ├── section.json
│   ├── author.json
│   └── ...
│
├── templates/                  # Jinja bytecode cache (relocated)
│   └── ...
│
├── content/                    # Remote content cache
│   └── ...
│
├── logs/                       # Build and server logs
│   ├── build.log
│   └── serve.log
│
├── metrics/                    # Performance metrics
│   └── *.json
│
├── profiles/                   # Profiling output
│   └── *.stats
│
├── history/                    # Build history and deltas
│   └── builds.json
│
├── temp/                       # Temporary files (safe to delete)
│   └── js_bundle/
│
└── state/                      # Runtime state
    ├── server.pid
    └── themes.json             # Swizzle registry
```

---

## Design Options

### Option A: Constant + Directory Paths Module (Recommended)

Create a dedicated module for all `.bengal` paths:

```python
# bengal/cache/paths.py
"""
Single source of truth for Bengal state directory paths.

The .bengal directory stores all project-specific state:
- Build caches for incremental builds
- Query indexes for fast lookups
- Template bytecode cache
- Logs, metrics, and profiles
- Runtime state (PID files, etc.)

Structure:
    .bengal/
    ├── cache/          # Build caches
    ├── indexes/        # Query indexes
    ├── templates/      # Jinja bytecode
    ├── content/        # Remote content cache
    ├── logs/           # Build/serve logs
    ├── metrics/        # Performance metrics
    ├── profiles/       # Profiling output
    ├── history/        # Build history
    ├── temp/           # Temporary files
    └── state/          # Runtime state
"""
from __future__ import annotations

from pathlib import Path


# Single source of truth
STATE_DIR_NAME = ".bengal"


class BengalPaths:
    """
    Accessor for all .bengal directory paths.

    Usage:
        paths = BengalPaths(site.root_path)
        paths.cache_dir      # .bengal/cache/
        paths.build_cache    # .bengal/cache/build.json.zst
        paths.server_pid     # .bengal/state/server.pid
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_dir = root / STATE_DIR_NAME

    # --- Cache ---
    @property
    def cache_dir(self) -> Path:
        """Build cache directory."""
        return self.state_dir / "cache"

    @property
    def build_cache(self) -> Path:
        """Main build cache file."""
        return self.cache_dir / "build.json.zst"

    @property
    def page_cache(self) -> Path:
        """Page metadata cache file."""
        return self.cache_dir / "pages.json.zst"

    @property
    def asset_cache(self) -> Path:
        """Asset dependency cache file."""
        return self.cache_dir / "assets.json.zst"

    @property
    def taxonomy_cache(self) -> Path:
        """Taxonomy index cache file."""
        return self.cache_dir / "taxonomy.json.zst"

    # --- Indexes ---
    @property
    def indexes_dir(self) -> Path:
        """Query indexes directory."""
        return self.state_dir / "indexes"

    # --- Templates ---
    @property
    def templates_dir(self) -> Path:
        """Jinja bytecode cache directory."""
        return self.state_dir / "templates"

    # --- Content ---
    @property
    def content_dir(self) -> Path:
        """Remote content cache directory."""
        return self.state_dir / "content"

    # --- Logs ---
    @property
    def logs_dir(self) -> Path:
        """Logs directory."""
        return self.state_dir / "logs"

    @property
    def build_log(self) -> Path:
        """Build log file."""
        return self.logs_dir / "build.log"

    @property
    def serve_log(self) -> Path:
        """Serve log file."""
        return self.logs_dir / "serve.log"

    # --- Metrics ---
    @property
    def metrics_dir(self) -> Path:
        """Performance metrics directory."""
        return self.state_dir / "metrics"

    # --- Profiles ---
    @property
    def profiles_dir(self) -> Path:
        """Profiling output directory."""
        return self.state_dir / "profiles"

    # --- History ---
    @property
    def history_dir(self) -> Path:
        """Build history directory."""
        return self.state_dir / "history"

    @property
    def build_history(self) -> Path:
        """Build history file."""
        return self.history_dir / "builds.json"

    # --- Temp ---
    @property
    def temp_dir(self) -> Path:
        """Temporary files directory."""
        return self.state_dir / "temp"

    @property
    def js_bundle_dir(self) -> Path:
        """JS bundle temporary directory."""
        return self.temp_dir / "js_bundle"

    # --- State ---
    @property
    def state_dir_inner(self) -> Path:
        """Runtime state directory."""
        return self.state_dir / "state"

    @property
    def server_pid(self) -> Path:
        """Server PID file."""
        return self.state_dir_inner / "server.pid"

    @property
    def swizzle_registry(self) -> Path:
        """Theme swizzle registry."""
        return self.state_dir_inner / "themes.json"

    # --- Utilities ---
    def ensure_dirs(self) -> None:
        """Create all necessary directories."""
        for prop in dir(self):
            if prop.endswith('_dir') and not prop.startswith('_'):
                getattr(self, prop).mkdir(parents=True, exist_ok=True)
```

**Integration with Site**:

```python
# bengal/core/site/core.py
from bengal.cache.paths import BengalPaths

@dataclass
class Site:
    root_path: Path
    ...

    @cached_property
    def paths(self) -> BengalPaths:
        """Access to .bengal directory paths."""
        return BengalPaths(self.root_path)
```

**Usage**:

```python
# Before (39+ places)
cache_dir = self.site.root_path / ".bengal"
cache_path = cache_dir / "cache.json"

# After
cache_path = self.site.paths.build_cache
# or
paths = BengalPaths(root_path)
cache_path = paths.build_cache
```

**Pros**:
- Single source of truth for all paths
- Self-documenting (property names describe purpose)
- Easy to add new paths consistently
- Type-safe (Path objects, not strings)
- Easy to test
- Clear migration path

**Cons**:
- Adds a new module
- Requires updating 39+ call sites

---

### Option B: Simple Constant Only

Just add a constant without restructuring:

```python
# bengal/config/defaults.py
STATE_DIR_NAME = ".bengal"
```

**Pros**:
- Minimal change
- Quick to implement

**Cons**:
- Doesn't address directory structure
- Still have string concatenation throughout codebase
- Doesn't solve template cache location issue

---

### Option C: Configurable via Config

Add `state_dir` to configuration:

```yaml
# bengal.toml
[build]
state_dir = ".bengal"  # or custom path
```

```python
# Usage
state_dir = site.config.get("build", {}).get("state_dir", ".bengal")
```

**Pros**:
- Maximum flexibility
- Users can relocate cache to different drive

**Cons**:
- Adds configuration complexity
- Most users don't need this
- Can combine with Option A

---

## Recommendation

**Option A (Constant + Directory Paths Module)** with optional configuration from Option C.

Implementation order:
1. Create `BengalPaths` class with current structure (no file renames yet)
2. Migrate all 39+ call sites to use `BengalPaths`
3. Add `site.paths` property for convenience
4. Relocate template cache from output dir
5. (Optional) Add configurable `state_dir` to config
6. (Future) Reorganize into proposed structure

---

## Migration Strategy

### Phase 1: Centralize (No Breaking Changes)

1. Create `bengal/cache/paths.py` with `BengalPaths` class
2. Keep current file names/locations for backwards compatibility
3. Update all 39+ call sites to use `BengalPaths`
4. Add deprecation warning for direct `.bengal` string usage

```python
# Before
cache_path = site.root_path / ".bengal" / "cache.json"

# After (Phase 1 - same file locations)
cache_path = site.paths.build_cache  # Still points to .bengal/cache.json
```

### Phase 2: Relocate Template Cache

1. Move template cache from `output/.bengal-cache/templates` to `.bengal/templates`
2. Update `rendering/template_engine/environment.py`
3. Add migration that cleans up old location

### Phase 3: Reorganize (Optional, Future)

1. Introduce new directory structure (cache/, state/, etc.)
2. Add migration logic to move files from old to new locations
3. Keep reading from old locations for N versions

```python
# Migration helper
def migrate_cache_layout(paths: BengalPaths) -> None:
    """Migrate from flat to organized structure."""
    # Move cache.json → cache/build.json.zst
    old_cache = paths.state_dir / "cache.json"
    if old_cache.exists() and not paths.build_cache.exists():
        paths.cache_dir.mkdir(parents=True, exist_ok=True)
        # Decompress old, recompress to new location
        ...
```

---

## Files to Update

### High Priority (Core paths)

| File | Usage | Instances |
|------|-------|-----------|
| `orchestration/incremental.py` | Build cache | 3 |
| `orchestration/build/__init__.py` | Build cache | 1 |
| `orchestration/build/initialization.py` | Page cache, build cache | 4 |
| `cache/utils.py` | Build cache utility | 1 |
| `cli/commands/clean.py` | Cache cleaning | 2 |
| `cli/commands/debug.py` | Cache inspection | 3 |
| `cli/commands/validate.py` | Cache loading | 3 |

### Medium Priority (Indexes and caches)

| File | Usage | Instances |
|------|-------|-----------|
| `orchestration/build/rendering.py` | Asset deps | 1 |
| `orchestration/build/content.py` | Taxonomy index | 1 |
| `orchestration/taxonomy.py` | Taxonomy index | 2 |
| `core/site/properties.py` | Query indexes | 1 |
| `orchestration/asset.py` | JS bundle temp | 1 |

### Lower Priority (Logs, metrics, state)

| File | Usage | Instances |
|------|-------|-----------|
| `utils/paths.py` | Logs, profiles | 4 |
| `utils/performance_collector.py` | Metrics | 1 |
| `utils/performance_report.py` | Metrics | 1 |
| `debug/delta_analyzer.py` | Build history | 2 |
| `server/pid_manager.py` | PID file | 3 |
| `utils/swizzle.py` | Swizzle registry | 1 |
| `cli/commands/sources.py` | Content cache | 3 |
| `content_layer/manager.py` | Content cache | 2 |

### Special Case (Template cache - different location)

| File | Current Location | New Location |
|------|------------------|--------------|
| `rendering/template_engine/environment.py` | `output/.bengal-cache/templates` | `.bengal/templates` |
| `rendering/template_engine/core.py` | (docstring only) | Update docs |
| `utils/paths.py` | `output/.bengal-cache/templates` | `.bengal/templates` |

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_bengal_paths.py
def test_paths_are_consistent():
    """All paths should be under state_dir."""
    paths = BengalPaths(Path("/project"))
    for name in dir(paths):
        if not name.startswith('_'):
            value = getattr(paths, name)
            if isinstance(value, Path) and name != 'root':
                assert str(value).startswith("/project/.bengal")


def test_ensure_dirs_creates_all():
    """ensure_dirs should create all *_dir paths."""
    with tempfile.TemporaryDirectory() as tmp:
        paths = BengalPaths(Path(tmp))
        paths.ensure_dirs()
        assert paths.cache_dir.exists()
        assert paths.logs_dir.exists()
        # etc.
```

### Integration Tests

```python
def test_build_uses_centralized_paths(tmp_site):
    """Build should use BengalPaths for all cache access."""
    site = Site.from_config(tmp_site)
    site.build()

    # Cache files should exist at centralized locations
    assert site.paths.build_cache.exists()
    assert site.paths.page_cache.exists()
```

---

## Documentation Updates

1. **Add `.bengal/README.md` generator**: Auto-generate on first build
2. **Update QUICKSTART.md**: Document `.bengal/` directory
3. **Update architecture docs**: Add section on state management
4. **Add to `.gitignore` templates**: Ensure `.bengal/` is always ignored

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Migration breaks existing caches | Medium | Low | Keep backwards-compat reading |
| Performance overhead from Path objects | Low | Low | Paths are cached, minimal overhead |
| Users have custom scripts expecting old paths | Low | Medium | Document in changelog, deprecation period |
| Template cache move breaks dev server | Medium | Medium | Test thoroughly, gradual rollout |

---

## Success Criteria

1. ✅ No raw `.bengal` strings in codebase (except constant definition)
2. ✅ All tests pass
3. ✅ Template cache in `.bengal/` not `output/`
4. ✅ `site.paths` provides convenient access
5. ✅ Documentation clearly explains structure
6. ✅ Existing sites migrate seamlessly

---

## Timeline

| Phase | Description | Effort |
|-------|-------------|--------|
| Phase 1 | Create `BengalPaths`, migrate call sites | 2-3 hours |
| Phase 2 | Relocate template cache | 1 hour |
| Phase 3 | Add documentation, README generator | 1 hour |
| Phase 4 | (Future) Reorganize directory structure | 2-3 hours |

**Total**: ~5-7 hours for Phases 1-3

---

## References

- **Codebase audit**: 39+ instances of hardcoded `.bengal` found
- **Template cache issue**: `output/.bengal-cache/templates` inconsistent location
- **Similar patterns**: Hugo uses `.hugo_build.lock`, Jekyll uses `.jekyll-cache`
- **Related RFC**: `rfc-autodoc-output-prefix.md` (similar centralization pattern)

---

## Appendix: Full Audit of `.bengal` Usage

<details>
<summary>Click to expand full list of 39+ occurrences</summary>

### Cache Files
- `orchestration/incremental.py:123` - `.bengal/cache.json`
- `orchestration/incremental.py:1075` - `.bengal/cache.json`
- `orchestration/build/__init__.py:192` - `.bengal/cache.json`
- `orchestration/build/initialization.py:219` - `.bengal/page_metadata.json`
- `orchestration/build/initialization.py:272` - `.bengal/page_metadata.json`
- `orchestration/build/initialization.py:350` - `.bengal/cache.json`
- `orchestration/build/rendering.py:358` - `.bengal/asset_deps.json`
- `orchestration/build/content.py:165` - `.bengal/taxonomy_index.json`
- `orchestration/taxonomy.py:100` - `.bengal/taxonomy_index.json`
- `orchestration/taxonomy.py:177` - `.bengal/taxonomy_index.json`
- `cache/utils.py:28` - `.bengal/cache.json`
- `cli/commands/debug.py:94,214,334` - `.bengal/cache.json`
- `cli/commands/validate.py:139,159,261` - `.bengal/cache.json`
- `cli/commands/explain.py:120` - `.bengal/cache.json`

### Index Files
- `core/site/properties.py:177` - `.bengal/indexes/`

### Temp Files
- `orchestration/asset.py:551` - `.bengal/js_bundle/`

### Log/Metric Files
- `utils/paths.py:88,103` - `.bengal/profiles/`, `.bengal/logs/`
- `utils/performance_collector.py:71` - `.bengal/metrics/`
- `utils/performance_report.py:99` - `.bengal/metrics/`

### History Files
- `debug/delta_analyzer.py:342,436` - `.bengal/build_history.json`

### State Files
- `server/pid_manager.py:67` - `.bengal/server.pid`
- `utils/swizzle.py:45` - `.bengal/themes/sources.json`

### Content Cache
- `cli/commands/sources.py:144,222,267` - `.bengal/content_cache/`
- `content_layer/manager.py:67` - `.bengal/content_cache/`

### Asset Manifest
- `analysis/graph_visualizer.py:329` - `.bengal/asset-manifest.json`

### Template Cache (Different Location!)
- `rendering/template_engine/environment.py:230` - `output/.bengal-cache/templates`
- `utils/paths.py:188` - `output/.bengal-cache/templates`

### CLI/Server Ignores
- `server/build_handler.py:48,199,209` - Documentation/ignore patterns
- `cli/commands/validate.py:301` - Path filtering

</details>
