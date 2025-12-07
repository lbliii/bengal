# RFC: Centralized Path Resolution Architecture

**Status**: Draft  
**Author**: AI Assistant (based on debugging session 2025-12-07)  
**Created**: 2025-12-07  
**Related**: `rfc-api-explorer-layout.md`, virtual pages implementation

---

## Executive Summary

During implementation of virtual autodoc pages, multiple bugs arose from **inconsistent path resolution** across the codebase. This RFC proposes centralizing path handling to eliminate a class of subtle, hard-to-debug issues.

---

## Problem Statement

### Pain Points Encountered (Session Evidence)

#### 1. Relative `site.root_path` Causes CWD-Dependent Behavior

**Bug**: Virtual pages generated paths like `api/Users/llane/Documents/github/python/bengal/site/bengal/...` instead of `api/bengal/...`

**Root cause**:
```python
# Site.root_path is "." (relative)
site.root_path  # => Path(".")

# Config has relative paths
source_dirs: ["../bengal"]

# Orchestrator joins without resolving
source_path = self.site.root_path / source_path  # => Path("../bengal")

# Extractor resolves relative to CWD (varies!)
self._source_root = source.resolve()  # CWD-dependent!
```

**Result**: When CWD differs from site directory, paths resolve incorrectly.

#### 2. Config Values Used Without Resolution

**Bug**: `source_dirs: ["../bengal"]` passed to extractor, which used it relative to wrong base.

**Evidence**:
```python
# Virtual orchestrator (before fix):
source_dirs = self.config.get("source_dirs", [])
source_path = Path(source_dirs[0])  # Still "../bengal" - relative to what?
```

**Fix required**: Added explicit `.resolve()` in multiple places.

#### 3. Virtual Objects Missing Physical Object Properties

**Bug**: Templates failed with `'Section object' has no attribute 'slug'`

**Root cause**: Virtual sections created via `Section.create_virtual()` lacked properties that templates expected:
- `slug` property
- Proper `path` handling (used `None`, broke registry)
- `relative_url` edge cases

**Evidence**:
```python
# Template expected:
section.slug.replace('-', ' ')  # AttributeError!

# Had to add:
@property
def slug(self) -> str:
    if self._virtual:
        return self.name
    return self.path.name if self.path else self.name
```

#### 4. Section Registry Assumed Non-None Paths

**Bug**: `'NoneType' object has no attribute 'resolve'`

**Root cause**:
```python
def _register_section_recursive(self, section: Section) -> None:
    normalized = self._normalize_section_path(section.path)  # path is None!
```

**Fix required**: Special-case virtual sections with `path=None`.

---

## Current Architecture (Problematic)

```
┌─────────────────────────────────────────────────────────────────┐
│                      Config Loading                              │
│  - Reads relative paths from YAML/TOML                          │
│  - Stores as-is without resolution                              │
│  - Example: source_dirs: ["../bengal"]                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Site Initialization                         │
│  - root_path can be "." (relative!)                             │
│  - No centralized path normalization                            │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Discovery     │ │   Autodoc       │ │   Rendering     │
│                 │ │                 │ │                 │
│ Resolves paths  │ │ Resolves paths  │ │ Resolves paths  │
│ its own way     │ │ its own way     │ │ its own way     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                              │
                              ▼
                    ❌ INCONSISTENT RESULTS
```

### Issues with Current Approach

1. **CWD-dependent**: `Path("../foo").resolve()` depends on working directory
2. **Multiple resolution points**: Each subsystem resolves paths differently
3. **Relative storage**: Config stores relative paths, used later in different contexts
4. **No contracts**: Virtual objects don't guarantee same interface as physical

---

## Proposed Architecture

### Principle: Resolve Once, At Ingestion

```
┌─────────────────────────────────────────────────────────────────┐
│                      Config Loading                              │
│  1. Determine config file location (absolute)                   │
│  2. Resolve ALL paths relative to config location               │
│  3. Store only absolute paths                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Site Initialization                         │
│  - root_path ALWAYS absolute: Path(root).resolve()              │
│  - All config paths already absolute                            │
│  - PathResolver utility for any additional resolution           │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Discovery     │ │   Autodoc       │ │   Rendering     │
│                 │ │                 │ │                 │
│ Uses absolute   │ │ Uses absolute   │ │ Uses absolute   │
│ paths directly  │ │ paths directly  │ │ paths directly  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                              │
                              ▼
                    ✅ CONSISTENT RESULTS
```

---

## Implementation Plan

### Phase 1: Site.root_path Always Absolute (Low Risk)

**File**: `bengal/core/site.py`

```python
# Current
@classmethod
def from_config(cls, root_path: Path, ...) -> Site:
    # root_path used as-is (may be relative)
    
# Proposed
@classmethod  
def from_config(cls, root_path: Path, ...) -> Site:
    root_path = root_path.resolve()  # Always absolute
```

**Impact**: Minimal - just ensures consistent base.

### Phase 2: Config Path Resolution (Medium Risk)

**File**: `bengal/config/loader.py`

```python
class ConfigLoader:
    def __init__(self, root_path: Path):
        self.root_path = root_path.resolve()  # Absolute reference point
    
    def _resolve_config_paths(self, config: dict) -> dict:
        """Resolve all path-like config values to absolute paths."""
        path_keys = {
            "autodoc.python.source_dirs",
            "autodoc.python.output_dir",
            "content.dir",
            "output.dir",
            # ... enumerate all path config keys
        }
        # Walk config and resolve matching keys
```

**Alternatively**: Explicit path resolution at each config access point (current approach, more scattered).

### Phase 3: PathResolver Utility (Optional, Clean)

**New file**: `bengal/utils/path_resolver.py`

```python
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site


class PathResolver:
    """
    Centralized path resolution utility.
    
    All paths resolved relative to a fixed base (site root).
    Eliminates CWD-dependent behavior.
    
    Usage:
        resolver = PathResolver(site.root_path)
        abs_path = resolver.resolve("../bengal")  # Always absolute
    """
    
    def __init__(self, base: Path):
        """
        Initialize resolver with absolute base path.
        
        Args:
            base: Base path for resolution (must be absolute)
        
        Raises:
            ValueError: If base is not absolute
        """
        if not base.is_absolute():
            raise ValueError(f"PathResolver base must be absolute, got: {base}")
        self.base = base
    
    def resolve(self, path: str | Path) -> Path:
        """
        Resolve path to absolute, relative to base.
        
        Args:
            path: Path to resolve (absolute or relative)
        
        Returns:
            Absolute path
        """
        p = Path(path)
        if p.is_absolute():
            return p
        return (self.base / p).resolve()
    
    def resolve_many(self, paths: list[str | Path]) -> list[Path]:
        """Resolve multiple paths."""
        return [self.resolve(p) for p in paths]
    
    @classmethod
    def from_site(cls, site: Site) -> PathResolver:
        """Create resolver from site instance."""
        return cls(site.root_path.resolve())
```

### Phase 4: Virtual Object Contracts (Medium Effort)

**Ensure virtual objects satisfy same interface as physical**:

```python
# bengal/core/section.py

class Section:
    """
    Section - represents a content directory OR virtual section.
    
    INTERFACE CONTRACT:
    ===================
    All sections (physical and virtual) MUST provide:
    - name: str
    - slug: str  
    - title: str
    - relative_url: str
    - path: Path | None  # None for virtual, Path for physical
    - is_virtual: bool
    
    Templates should handle path=None gracefully.
    """
    
    @classmethod
    def create_virtual(cls, ...) -> Section:
        """
        Create virtual section satisfying full interface.
        
        Virtual sections have path=None but all other properties
        must be properly initialized.
        """
```

**Add property completeness check**:

```python
def _validate_section_interface(section: Section) -> None:
    """Validate section satisfies template interface."""
    required = ['name', 'slug', 'title', 'relative_url', 'is_virtual']
    for attr in required:
        if not hasattr(section, attr):
            raise ValueError(f"Section missing required attribute: {attr}")
```

---

## Migration Path

### Step 1: Non-Breaking Preparation
- Add `PathResolver` utility
- Add `slug` property to Section (done)
- Add virtual section handling in registry (done)

### Step 2: Site.root_path Change
- Change `Site.from_config` to always resolve root_path
- Update tests expecting relative paths

### Step 3: Config Resolution (Optional)
- Add config path resolution in loader
- Or document that subsystems must resolve paths themselves

---

## Testing Strategy

### New Test Cases

```python
def test_site_root_path_always_absolute():
    """Site.root_path should always be absolute regardless of input."""
    site = Site.from_config(Path("."))
    assert site.root_path.is_absolute()
    
    site = Site.from_config(Path("relative/path"))
    assert site.root_path.is_absolute()


def test_autodoc_source_dirs_resolved_correctly():
    """Autodoc source_dirs should resolve relative to site root."""
    # Given config with relative source_dirs
    config = {"autodoc": {"python": {"source_dirs": ["../src"]}}}
    
    # When autodoc runs
    orchestrator = VirtualAutodocOrchestrator(site)
    
    # Then paths should be absolute
    for source_path in orchestrator._get_source_paths():
        assert source_path.is_absolute()


def test_virtual_section_satisfies_interface():
    """Virtual sections should have all template-required properties."""
    section = Section.create_virtual(name="api", relative_url="/api/")
    
    # All required properties exist
    assert hasattr(section, 'slug')
    assert hasattr(section, 'title')
    assert hasattr(section, 'relative_url')
    assert hasattr(section, 'is_virtual')
    
    # Properties have correct values
    assert section.slug == "api"
    assert section.is_virtual == True
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Breaking existing relative path usage | Add deprecation warnings first |
| Performance of resolve() calls | Resolve once at ingestion, not repeatedly |
| Config file portability | Store relative in files, resolve on load |
| Test fixtures with relative paths | Update fixtures to use absolute or mock |

---

## Success Criteria

1. **No CWD-dependent behavior**: Running build from any directory produces same output
2. **Virtual objects work like physical**: Templates don't need special cases
3. **Single resolution point**: Paths resolved once, at config/ingestion time
4. **Clear error messages**: Path issues report absolute paths for debugging

---

## Appendix: Bug Session Timeline

| Time | Issue | Root Cause | Fix |
|------|-------|-----------|-----|
| 14:01 | Paths like `api/Users/llane/...` | Extractor used raw config paths | Resolve in orchestrator |
| 14:18 | `'NoneType' has no attribute 'resolve'` | Virtual section path=None | Special case in registry |
| 14:24 | `'Section' has no attribute 'slug'` | Virtual sections missing property | Add slug property |
| 14:26 | Template startswith failed | Undefined relative_url | Add type check in template |
| 14:29 | Paths still wrong after fix | site.root_path was "." | Explicit resolve() |
| 15:01 | Still wrong in actual build | Orchestrator didn't resolve | Add resolve() in orchestrator |

Each bug required tracing through multiple files to find the resolution point. Centralized handling would have prevented all of these.

---

## Decision

- [ ] Implement Phase 1 (Site.root_path always absolute)
- [ ] Implement Phase 2 (Config path resolution)
- [ ] Implement Phase 3 (PathResolver utility)
- [ ] Implement Phase 4 (Virtual object contracts)
- [ ] Defer to future work
- [ ] Reject (document current behavior instead)

---

## References

- `bengal/core/site.py` - Site initialization
- `bengal/config/loader.py` - Config loading
- `bengal/autodoc/virtual_orchestrator.py` - Virtual page generation
- `bengal/autodoc/extractors/python.py` - Module extraction
- `bengal/core/section.py` - Section model

