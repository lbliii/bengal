# RFC: Theme-Aware Icon System

**Status**: Implemented  
**Created**: 2025-12-24  
**Implemented**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: Rendering, Themes  
**Confidence**: 92% 🟢  
**Priority**: P2 (Medium) — Developer ergonomics, enables theme ecosystem  
**Estimated Effort**: 2-3 days (Actual: ~1 day)

---

## Executive Summary

Bengal's icon system is hardcoded to load icons from `bengal/themes/default/assets/icons/`. Theme developers cannot provide custom icons or override defaults. This RFC proposes using Bengal's existing theme asset resolution chain to make icons theme-aware, enabling:

1. **Custom icon libraries** — Theme devs drop in their own icons
2. **Selective overrides** — Replace specific icons while keeping defaults
3. **Site-level additions** — Site authors add icons without forking themes
4. **Inheritance** — Child themes inherit parent icons, can override

**Design**: Icons follow the same layered resolution as CSS/templates—first match wins, falling through to defaults.

---

## Problem Statement

### Current State: Hardcoded Icon Loading

All four icon loading paths are hardcoded to the default theme:

| Location | Lines | Implementation |
|----------|-------|----------------|
| `rendering/template_functions/icons.py` | 48-50 | `_get_icons_directory()` returns hardcoded path |
| `rendering/plugins/inline_icon.py` | 37-42 | Module-level `_get_icons_dir()` hardcoded |
| `directives/_icons.py` | 70-73 | `_get_icons_directory()` hardcoded |
| `directives/icon.py` | 54-56 | Fallback hardcoded when `_icons_dir` is None |

**Example** (`rendering/template_functions/icons.py:48-50`):
```python
def _get_icons_directory() -> Path:
    """Get the icons directory from the default theme."""
    return Path(__file__).parents[2] / "themes" / "default" / "assets" / "icons"
```

### Partial Implementation Exists

`directives/icon.py` has an unused hook that was never connected:

```python
# directives/icon.py:41-45
def _set_icons_directory(path: Path) -> None:
    """Set the icons directory (called during site initialization)."""
    global _icons_dir
    _icons_dir = path
    _icon_cache.clear()
```

This function is never called—the fallback on line 56 always triggers. This RFC will complete this partial work by connecting all icon loading to theme resolution.

### Existing Infrastructure (Unused for Icons)

Bengal already has theme asset resolution that icons don't use:

**`core/site/theme.py:36-67`**:
```python
def _get_theme_assets_dir(self) -> Path | None:
    # Check in site's themes directory first
    site_theme_dir = self.root_path / "themes" / self.theme / "assets"
    if site_theme_dir.exists():
        return site_theme_dir

    # Check in Bengal's bundled themes
    bundled_theme_dir = bengal_dir / "themes" / self.theme / "assets"
    if bundled_theme_dir.exists():
        return bundled_theme_dir
```

**`themes/config.py:187-207`** — `IconConfig` exists but `library` field unused:
```python
class IconConfig:
    library: str = "phosphor"  # Never used!
    aliases: dict[str, str] = field(default_factory=dict)
    defaults: dict[str, str] = field(default_factory=dict)
```

### Pain Points

| Issue | Impact |
|-------|--------|
| Theme devs can't provide custom icons | Blocks custom themes (Heroicons, Material, etc.) |
| Site authors can't add icons | Must fork theme or request Bengal changes |
| No icon inheritance | Child themes can't selectively override |
| T010 warnings unhelpful | Can't suggest "add icon to your theme" |

---

## Goals

1. **Layer icons like other theme assets** — Same resolution order as CSS/templates
2. **Complement by default** — Theme icons merge with defaults, not replace
3. **Zero config for common cases** — Just drop files in `assets/icons/`
4. **Optional full override** — `icons.extend_defaults: false` disables fallback
5. **Improve T010 warnings** — Show which directories were searched

### Non-Goals

- Changing icon SVG format requirements
- Adding icon transformation/optimization
- Supporting non-SVG icon formats
- Runtime icon fetching from CDN

---

## Design

### Resolution Order

Icons resolve using the theme asset chain (first match wins):

```
1. site/themes/{theme}/assets/icons/{name}.svg     ← Site overrides (highest priority)
2. bengal/themes/{theme}/assets/icons/{name}.svg   ← Theme's custom icons
3. bengal/themes/{parent}/assets/icons/{name}.svg  ← Parent theme (if extended)
4. bengal/themes/default/assets/icons/{name}.svg   ← Bengal defaults (lowest priority)
```

This matches CSS/template resolution exactly.

### Example Scenarios

**Scenario 1: Theme adds domain icons**
```
bengal/themes/medical-docs/assets/icons/
├── stethoscope.svg    ← NEW icon
├── heartbeat.svg      ← NEW icon
└── (nothing else)     ← Falls through to Phosphor defaults

Result:
- {{ icon("stethoscope") }}  → medical-docs icon
- {{ icon("search") }}       → Phosphor default (fallthrough)
```

**Scenario 2: Theme overrides icon style**
```
bengal/themes/heroicons-theme/assets/icons/
├── search.svg         ← OVERRIDE: Heroicons style
├── menu.svg           ← OVERRIDE: Heroicons style
├── close.svg          ← OVERRIDE: Heroicons style
└── (nothing else)     ← Other icons use Phosphor

Result:
- {{ icon("search") }}   → Heroicons version
- {{ icon("warning") }}  → Phosphor default (not overridden)
```

**Scenario 3: Site author adds logo**
```
site/themes/my-site/assets/icons/
└── company-logo.svg   ← Site-specific icon

Result:
- {{ icon("company-logo") }}  → Site's custom icon
- {{ icon("search") }}        → Theme or Phosphor default
```

**Scenario 4: Full replacement (opt-in)**
```yaml
# themes/minimal-theme/theme.yaml
icons:
  extend_defaults: false  # Don't fall through to Phosphor
```
Result: Only icons in `minimal-theme/assets/icons/` are available.

### API Changes

#### 1. New Unified Icon Resolver Module

Create `bengal/icons/resolver.py` as the single source of truth for icon resolution:

```python
# bengal/icons/resolver.py
"""
Unified icon resolution for all Bengal icon consumers.

This module provides centralized icon loading with theme-aware resolution.
All icon loading (template functions, plugins, directives) should use this module.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site

# Module-level state (set during Site initialization)
_search_paths: list[Path] = []
_icon_cache: dict[str, str] = {}
_not_found_cache: set[str] = set()  # Avoid repeated disk checks


def initialize(site: Site) -> None:
    """
    Initialize icon resolver with Site context.

    Called once during Site initialization, before any rendering.
    Sets up search paths based on theme configuration.
    """
    global _search_paths
    _search_paths = _get_icon_search_paths(site)
    _icon_cache.clear()
    _not_found_cache.clear()


def _get_icon_search_paths(site: Site) -> list[Path]:
    """
    Get ordered list of icon directories to search.

    Returns directories from highest to lowest priority:
    1. Site theme icons (site/themes/{theme}/assets/icons)
    2. Theme icons with inheritance chain
    3. Default theme icons (if extend_defaults=True)
    """
    paths = []

    # Get theme asset chain (handles inheritance)
    for assets_dir in site._get_theme_assets_chain():
        icons_dir = assets_dir / "icons"
        if icons_dir.exists():
            paths.append(icons_dir)

    # Add default theme if extending (default behavior)
    if site.theme_config.icons.extend_defaults:
        import bengal
        default_icons = Path(bengal.__file__).parent / "themes" / "default" / "assets" / "icons"
        if default_icons.exists() and default_icons not in paths:
            paths.append(default_icons)

    return paths


def load_icon(name: str) -> str | None:
    """
    Load icon from first matching path in search chain.

    Uses caching to avoid repeated disk I/O:
    - Found icons cached by content
    - Not-found icons cached to skip repeated searches

    Args:
        name: Icon name (without .svg extension)

    Returns:
        SVG content string, or None if not found
    """
    if name in _icon_cache:
        return _icon_cache[name]

    if name in _not_found_cache:
        return None

    for icons_dir in _search_paths:
        icon_path = icons_dir / f"{name}.svg"
        if icon_path.exists():
            try:
                content = icon_path.read_text(encoding="utf-8")
                _icon_cache[name] = content
                return content
            except OSError:
                continue

    _not_found_cache.add(name)
    return None


def get_search_paths() -> list[Path]:
    """Get current search paths (for error messages)."""
    return _search_paths.copy()


def clear_cache() -> None:
    """Clear icon cache (for dev server hot reload)."""
    _icon_cache.clear()
    _not_found_cache.clear()
```

#### 2. Site Initialization Hook

The resolver is initialized during Site setup:

```python
# bengal/core/site/core.py (in Site.__post_init__ or similar)

from bengal.icons import resolver as icon_resolver

# After theme config is loaded:
icon_resolver.initialize(self)
```

This ensures all icon consumers have access to resolved paths without needing direct Site access.

#### 3. IconConfig Extension

```python
# bengal/themes/config.py

@dataclass
class IconConfig:
    library: str = "phosphor"
    aliases: dict[str, str] = field(default_factory=dict)
    defaults: dict[str, str] = field(default_factory=dict)
    extend_defaults: bool = True  # NEW: Fall through to Bengal defaults

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IconConfig:
        return cls(
            library=data.get("library", "phosphor"),
            aliases=data.get("aliases", {}),
            defaults=data.get("defaults", {}),
            extend_defaults=data.get("extend_defaults", True),  # NEW
        )
```

#### 4. Enhanced T010 Warning

```python
# bengal/icons/resolver.py or calling code

from bengal.icons import resolver as icon_resolver

def warn_missing_icon(name: str, directive: str = "") -> None:
    """Log warning with searched paths for debugging."""
    logger.warning(
        "icon_not_found",
        icon=name,
        code=ErrorCode.T010.name,
        directive=directive,
        searched=[str(p) for p in icon_resolver.get_search_paths()],
        hint=f"Add icon to your theme: themes/{{theme}}/assets/icons/{name}.svg",
    )
```

### Files to Modify

| File | Change | Complexity |
|------|--------|------------|
| `icons/__init__.py` | NEW: Package init | Trivial |
| `icons/resolver.py` | NEW: Unified resolver module | Medium |
| `core/site/core.py` | Add `icon_resolver.initialize(self)` call | Trivial |
| `themes/config.py` | Add `extend_defaults` to `IconConfig` | Trivial |
| `rendering/template_functions/icons.py` | Use `icon_resolver.load_icon()` | Low |
| `rendering/plugins/inline_icon.py` | Use `icon_resolver.load_icon()` | Low |
| `directives/_icons.py` | Use `icon_resolver.load_icon()` | Low |
| `directives/icon.py` | Use `icon_resolver.load_icon()`, remove `_set_icons_directory()` | Low |

### Preloading Strategy

Current preloading loads ALL icons from default theme at startup. New approach:

**Option A: Lazy loading with cache** (Recommended for dev)
- Don't preload at startup
- Load icons on first use, cache result
- Cache includes "not found" to avoid repeated disk checks
- Pros: Fast startup, memory efficient, hot reload friendly
- Cons: First render slightly slower

**Option B: Preload from all theme paths** (Recommended for production)
- At startup, scan all theme icon directories
- Build combined icon set (first match wins)
- Pros: Fast renders, predictable performance
- Cons: Slower startup, more memory

**Implementation**:

```python
# bengal/icons/resolver.py

def initialize(site: Site, preload: bool = False) -> None:
    """
    Initialize icon resolver.

    Args:
        site: Site instance for theme resolution
        preload: If True, eagerly load all icons (production mode)
    """
    global _search_paths
    _search_paths = _get_icon_search_paths(site)
    _icon_cache.clear()
    _not_found_cache.clear()

    if preload:
        _preload_all_icons()


def _preload_all_icons() -> None:
    """Preload all icons from search paths (production optimization)."""
    seen: set[str] = set()
    for icons_dir in _search_paths:
        for icon_path in icons_dir.glob("*.svg"):
            name = icon_path.stem
            if name not in seen:  # First match wins
                try:
                    _icon_cache[name] = icon_path.read_text(encoding="utf-8")
                    seen.add(name)
                except OSError:
                    pass
```

**Caller decides mode**:
```python
# In bengal/core/site/core.py
icon_resolver.initialize(self, preload=not self.is_dev_server)
```

---

## Migration

### Backward Compatibility

- **Existing sites**: No change. Default theme icons continue working.
- **Existing themes**: No change. Themes without `assets/icons/` fall through to defaults.
- **Existing templates**: `{{ icon("name") }}` syntax unchanged.

### Theme Developer Guide

```markdown
## Adding Custom Icons

1. Create `themes/{your-theme}/assets/icons/` directory
2. Add SVG files (must follow Bengal icon format)
3. Icons automatically available in templates

### Override Default Icons

To replace a default icon, add a file with the same name:

```
themes/my-theme/assets/icons/
└── warning.svg    ← Replaces Phosphor's warning icon
```

### Disable Default Icons

To use ONLY your icons (no Phosphor fallback):

```yaml
# theme.yaml
icons:
  extend_defaults: false
```
```

---

## Testing Strategy

### Unit Tests (`tests/unit/icons/test_resolver.py`)

```python
import pytest
from pathlib import Path
from bengal.icons import resolver as icon_resolver


class TestIconResolution:
    """Test icon search path ordering."""

    def test_icon_resolution_order(self, site_with_theme_icons):
        """Site icons take precedence over theme icons."""
        # Setup: site/themes/test/assets/icons/custom.svg exists
        # AND bengal/themes/default/assets/icons/custom.svg exists
        icon_resolver.initialize(site_with_theme_icons)

        # Should load site's version, not default
        content = icon_resolver.load_icon("custom")
        assert "site-version" in content

    def test_icon_fallthrough_to_defaults(self, site_with_empty_theme):
        """Missing icons fall through to Bengal defaults."""
        icon_resolver.initialize(site_with_empty_theme)

        # Theme has no icons, should fall through to Phosphor
        content = icon_resolver.load_icon("warning")
        assert content is not None
        assert "<svg" in content

    def test_icon_extend_defaults_false(self, site_no_extend):
        """When extend_defaults=false, no fallthrough occurs."""
        # Theme config: icons.extend_defaults = false
        icon_resolver.initialize(site_no_extend)

        # Default icon should NOT be available
        content = icon_resolver.load_icon("warning")
        assert content is None

    def test_icon_theme_inheritance(self, site_with_child_theme):
        """Child theme inherits parent theme icons."""
        # Child theme extends parent theme
        icon_resolver.initialize(site_with_child_theme)

        # Parent's icon should be available
        content = icon_resolver.load_icon("parent-only-icon")
        assert content is not None

        # Child's override should win
        content = icon_resolver.load_icon("shared-icon")
        assert "child-version" in content


class TestIconCaching:
    """Test caching behavior."""

    def test_icon_cache_hit(self, site_with_icons):
        """Second load uses cache, no disk I/O."""
        icon_resolver.initialize(site_with_icons)

        # First load
        icon_resolver.load_icon("test")

        # Modify file (simulate)
        # Second load should return cached version
        content = icon_resolver.load_icon("test")
        assert content is not None

    def test_icon_not_found_cache(self, site_with_icons):
        """Not-found icons are cached to avoid repeated disk checks."""
        icon_resolver.initialize(site_with_icons)

        # First miss
        assert icon_resolver.load_icon("nonexistent") is None

        # Second miss should not hit disk (verified via mock)
        assert icon_resolver.load_icon("nonexistent") is None

    def test_clear_cache(self, site_with_icons):
        """clear_cache() allows reloading modified icons."""
        icon_resolver.initialize(site_with_icons)
        icon_resolver.load_icon("test")

        icon_resolver.clear_cache()

        # Cache should be empty
        assert len(icon_resolver._icon_cache) == 0
```

### Integration Tests (`tests/integration/test_theme_icons.py`)

```python
def test_theme_with_custom_icons(tmp_path, build_site):
    """Build site with theme that provides custom icons."""
    # Create theme with custom icon
    theme_dir = tmp_path / "themes" / "custom" / "assets" / "icons"
    theme_dir.mkdir(parents=True)
    (theme_dir / "logo.svg").write_text('<svg><!-- custom --></svg>')

    # Build site using theme
    site = build_site(tmp_path, theme="custom")

    # Template using {{ icon("logo") }} should render custom icon
    output = (tmp_path / "_site" / "index.html").read_text()
    assert "<!-- custom -->" in output


def test_site_level_icon_override(tmp_path, build_site):
    """Site-level icon overrides theme icon."""
    # Create site-level override
    site_icons = tmp_path / "themes" / "default" / "assets" / "icons"
    site_icons.mkdir(parents=True)
    (site_icons / "warning.svg").write_text('<svg><!-- site override --></svg>')

    site = build_site(tmp_path)

    # Should use site's warning icon, not Phosphor default
    output = (tmp_path / "_site" / "index.html").read_text()
    assert "<!-- site override -->" in output


def test_t010_shows_searched_paths(tmp_path, build_site, caplog):
    """Warning includes all directories that were searched."""
    # Use nonexistent icon
    (tmp_path / "content" / "index.md").write_text('{{ icon("nonexistent") }}')

    build_site(tmp_path)

    # Warning should include search paths
    assert "searched" in caplog.text
    assert "assets/icons" in caplog.text
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (Day 1, ~2 hours)

**Goal**: Create unified resolver and config extension

1. **Create `bengal/icons/` package**:
   - `__init__.py` — Package exports
   - `resolver.py` — Unified icon resolution (see API Changes section)

2. **Update `themes/config.py`**:
   - Add `extend_defaults: bool = True` to `IconConfig`
   - Update `from_dict()` to parse new field

3. **Wire up Site initialization**:
   - Add `icon_resolver.initialize(self)` in Site setup
   - Determine `preload` mode from build context

**Verification**: Unit test that `icon_resolver.get_search_paths()` returns expected chain.

### Phase 2: Migrate Icon Consumers (Day 1, ~3 hours)

**Goal**: All icon loading uses unified resolver

1. **Update `rendering/template_functions/icons.py`**:
   - Replace `_get_icons_directory()` with `icon_resolver.load_icon()`
   - Keep LRU cache for rendered output (not raw SVG)
   - Remove `_preloaded_icons` dict (resolver handles caching)

2. **Update `rendering/plugins/inline_icon.py`**:
   - Replace `_get_icons_dir()` and `_load_icon()` with resolver
   - Keep `_warned_icons` deduplication

3. **Update `directives/_icons.py`**:
   - Replace `_get_icons_directory()` and `_load_icon()` with resolver
   - Keep `ICON_MAP` for semantic aliasing (resolver handles file loading only)

4. **Update `directives/icon.py`**:
   - Remove orphaned `_set_icons_directory()` function
   - Replace fallback loading with resolver

**Verification**: Existing tests pass with no icon loading changes visible to users.

### Phase 3: Enhanced Error Messages (Day 1, ~1 hour)

**Goal**: T010 warnings show actionable debugging info

1. **Update warning calls in all consumers**:
   ```python
   logger.warning(
       "icon_not_found",
       icon=name,
       code=ErrorCode.T010.name,
       searched=[str(p) for p in icon_resolver.get_search_paths()],
       hint=f"Add to theme: themes/{{theme}}/assets/icons/{name}.svg",
   )
   ```

2. **Update `site/content/docs/reference/errors/t010.md`**:
   - Add "Adding Custom Icons" section
   - Show theme override examples

**Verification**: Build with missing icon shows searched paths in warning.

### Phase 4: Testing (Day 2, ~2 hours)

**Goal**: Comprehensive test coverage for new functionality

1. **Unit tests** (`tests/unit/icons/test_resolver.py`):
   - `test_icon_resolution_order` — Site → theme → parent → default
   - `test_icon_fallthrough_to_defaults` — Missing icons use defaults
   - `test_icon_extend_defaults_false` — No fallthrough when disabled
   - `test_icon_theme_inheritance` — Multi-level inheritance works
   - `test_icon_cache_not_found` — Repeated misses don't hit disk

2. **Integration tests** (`tests/integration/test_theme_icons.py`):
   - `test_theme_with_custom_icons` — Build site with theme icons
   - `test_site_level_icon_override` — Site icons override theme
   - `test_t010_shows_searched_paths` — Warning includes paths

### Phase 5: Documentation (Day 2, ~1 hour)

**Goal**: Theme developers know how to use custom icons

1. **Update Icon Reference** (`site/content/docs/reference/icons/`):
   - Add "Custom Icons" section
   - Show override examples

2. **Update Theming Guide** (`site/content/docs/guides/theming/`):
   - Add icon customization section
   - Document `extend_defaults` option

3. **Add to Theme Developer Guide**:
   - Icon directory structure
   - SVG format requirements
   - Inheritance behavior

---

## Open Questions

### 1. Should we validate icon format on load?

**Current**: Icons loaded as-is without validation.

**Options**:
- A) No validation (current) — Fast, trusts theme developers
- B) Warn on missing `viewBox` — Helps catch sizing issues
- C) Full validation (viewBox, no inline styles) — Strictest

**Recommendation**: Option A for now. Add optional validation in future RFC if needed.

### 2. Icon aliasing across themes

**Problem**: Different icon libraries use different names for the same concept:
- Phosphor: `magnifying-glass`
- Heroicons: `magnifying-glass` (same!)
- Material: `search`

**Current behavior**: `ICON_MAP` in `_icons.py` provides semantic aliases (`search` → `magnifying-glass`). Theme `icons.aliases` in theme.yaml can override.

**Resolution order** (already implemented in `icons.py:182-207`):
1. Theme `icons.aliases` (highest priority)
2. `ICON_MAP` fallback
3. Literal name

**Recommendation**: No change needed. Existing alias system handles this. Document in Theming Guide.

### 3. Dev server hot reload

**Question**: Should adding/removing icons trigger rebuild?

**Options**:
- A) No hot reload — User must restart dev server
- B) Watch `assets/icons/` directories — Auto-reload on change
- C) Clear cache on any asset change — Simpler but broader

**Recommendation**: Option C initially (clear `icon_resolver.clear_cache()` when any theme asset changes). Dev server already watches theme directories. Add targeted icon watching in future if needed.

**Implementation**:
```python
# In dev server asset watcher
if changed_path.match("**/assets/**"):
    icon_resolver.clear_cache()
```

---

## Alternatives Considered

### Alternative A: Config-Based Icon Paths

```yaml
# bengal.toml
[icons]
paths = ["site/icons", "themes/my-theme/icons"]
```

**Rejected**: Too verbose for common case. Theme asset chain already exists.

### Alternative B: Icon Providers/Plugins

```python
# Plugin system for icon libraries
class HeroiconsProvider(IconProvider):
    def get_icon(self, name: str) -> str: ...
```

**Rejected**: Over-engineered. File-based resolution is simpler and matches theme pattern.

### Alternative C: CDN/External Icons

```yaml
icons:
  cdn: "https://unpkg.com/heroicons@2.0.0/24/outline/"
```

**Rejected**: Adds network dependency, offline builds would fail.

---

## Success Criteria

### Functional Requirements

- [ ] **Theme custom icons**: Theme dev creates `themes/{name}/assets/icons/custom.svg` → `{{ icon("custom") }}` renders it
- [ ] **Site icon additions**: Site author creates `site/themes/{theme}/assets/icons/logo.svg` → available without theme fork
- [ ] **Icon override**: Same filename in higher-priority path overrides lower → site > theme > parent > default
- [ ] **Disable defaults**: `icons.extend_defaults: false` in theme.yaml → only theme icons available, no Phosphor fallback
- [ ] **Inheritance chain**: Child theme without icon falls through to parent theme's icon

### Error Handling

- [ ] **T010 warning**: Missing icon warning includes `searched: [list of paths checked]`
- [ ] **Actionable hint**: Warning includes `hint: "Add to theme: themes/{theme}/assets/icons/{name}.svg"`

### Backward Compatibility

- [ ] **Existing sites**: Sites without custom themes build identically (same output hash)
- [ ] **Existing templates**: `{{ icon("name") }}` syntax unchanged
- [ ] **Existing theme.yaml**: Themes without `icons.extend_defaults` default to `true`

### Performance

- [ ] **Build time**: < 5% increase on 1000-page benchmark site
- [ ] **Memory**: < 10% increase in peak memory (lazy loading should improve this)
- [ ] **Dev server startup**: No regression (lazy loading)

### Code Quality

- [ ] **Single source of truth**: All icon loading goes through `bengal/icons/resolver.py`
- [ ] **No duplicate caches**: Remove `_icon_cache` from `inline_icon.py`, `_icons.py`, `icon.py`
- [ ] **Test coverage**: > 90% coverage on new `resolver.py` module

---

## References

### Source Files

| File | Relevance |
|------|-----------|
| `bengal/core/site/theme.py:69-111` | `_get_theme_assets_chain()` — reuse for icons |
| `bengal/themes/config.py:186-224` | `IconConfig` class — add `extend_defaults` |
| `bengal/rendering/template_functions/icons.py` | Template `icon()` function — migrate to resolver |
| `bengal/rendering/plugins/inline_icon.py` | Inline `{icon}` syntax — migrate to resolver |
| `bengal/directives/_icons.py` | Shared icon utilities — migrate to resolver |
| `bengal/directives/icon.py:41-45` | Orphaned `_set_icons_directory()` — remove |

### External

- [Phosphor Icons](https://phosphoricons.com/) — Default icon library (MIT license)
- [Heroicons](https://heroicons.com/) — Popular alternative library
- [Material Symbols](https://fonts.google.com/icons) — Google's icon set

### Related RFCs

- None currently. This RFC enables future work on:
  - Icon sprite sheets for performance
  - CDN-hosted icon libraries
  - Icon optimization/minification
