# RFC: Site Responsibility Separation

**Status**: Draft  
**Created**: 2024-12-23  
**Updated**: 2024-12-23  
**Author**: AI Assistant  
**Priority**: P1 (High)  
**Subsystems**: `bengal/core/site/`, `bengal/orchestration/`, `bengal/rendering/`  
**Estimated Effort**: ~40-60 hours (phased over multiple releases)

---

## Executive Summary

The `Site` class has grown into a "God Object" with ~50 fields, 7 mixins, and responsibilities spanning data storage, caching, registry management, runtime state, and build coordination. This creates:

- **Testability issues**: Mocking Site requires understanding 50+ interdependent fields
- **Cognitive load**: New contributors must understand the entire Site to modify any part
- **Hidden coupling**: Changes to caching affect discovery, rendering, and orchestration
- **Type safety gaps**: 131 `# type: ignore` comments across the codebase

This RFC proposes extracting four focused subsystems from Site over three phases, preserving backward compatibility while improving separation of concerns.

---

## Problem Statement

### Current State: Site as God Object

`Site` (core/site/core.py + 7 mixin files) has accumulated:

| Category | Count | Examples |
|----------|-------|----------|
| Data fields | 15 | `pages`, `sections`, `assets`, `config`, `taxonomies`, `menu` |
| Cache fields | 12 | `_regular_pages_cache`, `_page_path_map`, `_theme_obj` |
| Registry fields | 4 | `_section_registry`, `_section_url_registry`, `url_registry` |
| Runtime state | 8 | `_asset_manifest_*`, `_bengal_*_cache`, `features_detected` |
| Context fields | 4 | `current_language`, `current_version`, `dev_mode`, `build_time` |
| Mixins | 7 | Properties, Caches, Factories, Theme, Discovery, Data, Registry |

### Evidence of God Object Symptoms

**1. Everything holds a Site reference (51 instances found):**

```python
# Page needs Site for URL computation
class Page:
    _site: Site | None = field(default=None, repr=False)

# Section needs Site for lookups
class Section:
    _site: Site | None = field(default=None, repr=False)

# Template engine needs Site
class TemplateEngine:
    def __init__(self, site: Site): ...

# Every orchestrator needs Site
class ContentOrchestrator:
    def __init__(self, site: Site): ...
```

**2. reset_ephemeral_state() reveals accumulated state:**

```python
def reset_ephemeral_state(self) -> None:
    # 6 content fields
    self.pages = []
    self.sections = []
    self.assets = []
    self.taxonomies = {}
    self.menu = {}
    self.menu_builders = {}

    # 4 registry fields
    self._section_registry = {}
    self._section_url_registry = {}
    self._page_lookup_maps = None
    self.__dict__.pop("indexes", None)

    # 6 cache fields
    self._bengal_theme_chain_cache = None
    self._bengal_template_dirs_cache = None
    self._bengal_template_metadata_cache = None
    self._discovery_breakdown_ms = None
    self._asset_manifest_fallbacks_global.clear()
    self.features_detected.clear()
```

**3. 21-phase build coordinates Site mutations:**

The build process mutates Site state across 21 phases because there's no separation between "what we're building" and "state of the build":

```
Phase 2:  site.pages, site.sections populated (discovery)
Phase 6:  site.sections mutated (auto-index)
Phase 7:  site.taxonomies populated
Phase 9:  site.menu populated
Phase 13: site.assets mutated (fingerprinting)
Phase 14: site.pages[].rendered_html populated
...
```

**4. Type safety erosion:**

131 `# type: ignore[attr-defined]` comments indicate dynamic attribute access patterns that the type system can't verify.

### Pain Points

1. **Unit testing is painful**: Testing any Site method requires constructing the entire object graph
2. **Incremental builds are fragile**: Cache invalidation touches multiple unrelated caches
3. **Parallel builds risk race conditions**: Shared mutable state on Site during rendering
4. **IDE support degrades**: Autocomplete shows 100+ methods/properties
5. **New contributors struggle**: "Where does X go?" → "Just add it to Site"

---

## Goals

1. **Separate data from state**: Immutable content snapshot vs mutable build state
2. **Extract registries**: O(1) lookups as standalone, testable components
3. **Isolate caches**: Clear cache boundaries with explicit invalidation contracts
4. **Preserve API**: Existing code continues working via delegation
5. **Enable incremental adoption**: Each phase is independently valuable

### Non-Goals

- Rewriting the build orchestrator (separate RFC)
- Changing Page/Section data models beyond `_site` narrowing
- Breaking public template APIs (`site.pages`, `site.config`, etc.)

---

## Design

### Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                           Site                                   │
│  (Façade: delegates to focused subsystems, preserves API)       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  SiteData    │  │ BuildState   │  │ ContentRegistry      │  │
│  │  (immutable) │  │ (per-build)  │  │ (O(1) lookups)       │  │
│  ├──────────────┤  ├──────────────┤  ├──────────────────────┤  │
│  │ root_path    │  │ build_time   │  │ pages_by_path        │  │
│  │ config       │  │ dev_mode     │  │ pages_by_url         │  │
│  │ theme_name   │  │ incremental  │  │ sections_by_path     │  │
│  │ output_dir   │  │ current_lang │  │ sections_by_url      │  │
│  │ version_cfg  │  │ current_ver  │  │ taxonomies           │  │
│  └──────────────┘  │ features     │  │ url_ownership        │  │
│                    │ timing_stats │  └──────────────────────┘  │
│                    │ caches       │                             │
│                    └──────────────┘                             │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    SiteContent                            │  │
│  │  (mutable during discovery, frozen before render)         │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ pages: list[Page]                                         │  │
│  │ sections: list[Section]                                   │  │
│  │ assets: list[Asset]                                       │  │
│  │ menu: dict[str, list[MenuItem]]                          │  │
│  │ data: dict[str, Any]                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

### Phase 1: Extract ContentRegistry (Week 1-2)

Extract page/section lookups into a focused registry class.

**New File**: `bengal/core/registry.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from bengal.core.url_ownership import URLRegistry

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section


@dataclass
class ContentRegistry:
    """
    O(1) content lookups by path, URL, and metadata.

    Thread-safe for reads after freeze(). Rebuilt atomically during discovery.

    Lifecycle:
        1. Created empty at Site initialization
        2. Populated during discovery phase (register_page/register_section)
        3. Frozen before rendering phase (freeze())
        4. Cleared on rebuild (clear())

    Thread Safety:
        - Writes (register_*) must happen single-threaded during discovery
        - Reads (get_*) are safe after freeze() for concurrent rendering
        - Frozen registry raises RuntimeError on mutation attempts
    """

    # Path-based lookups (primary keys)
    _pages_by_path: dict[Path, Page] = field(default_factory=dict)
    _sections_by_path: dict[Path, Section] = field(default_factory=dict)

    # URL-based lookups (for virtual content and link resolution)
    _pages_by_url: dict[str, Page] = field(default_factory=dict)
    _sections_by_url: dict[str, Section] = field(default_factory=dict)

    # URL ownership (for collision detection)
    url_ownership: URLRegistry = field(default_factory=URLRegistry)

    # Frozen flag (set after discovery, before rendering)
    _frozen: bool = field(default=False, repr=False)

    def get_page(self, path: Path) -> Page | None:
        """Get page by source path. O(1) lookup."""
        return self._pages_by_path.get(path)

    def get_page_by_url(self, url: str) -> Page | None:
        """Get page by output URL. O(1) lookup."""
        return self._pages_by_url.get(url)

    def get_section(self, path: Path) -> Section | None:
        """Get section by directory path. O(1) lookup."""
        return self._sections_by_path.get(path)

    def get_section_by_url(self, url: str) -> Section | None:
        """Get section by URL (for virtual sections). O(1) lookup."""
        return self._sections_by_url.get(url)

    def register_page(self, page: Page) -> None:
        """
        Register a page. Raises if frozen.

        Args:
            page: Page to register (must have source_path set)

        Raises:
            RuntimeError: If registry is frozen
        """
        if self._frozen:
            raise RuntimeError("Cannot modify frozen registry")
        self._pages_by_path[page.source_path] = page
        if page._path:
            self._pages_by_url[page._path] = page

    def register_section(self, section: Section) -> None:
        """
        Register a section. Raises if frozen.

        Args:
            section: Section to register

        Raises:
            RuntimeError: If registry is frozen
        """
        if self._frozen:
            raise RuntimeError("Cannot modify frozen registry")
        if section.path:
            self._sections_by_path[section.path] = section
        if section._path:
            self._sections_by_url[section._path] = section

    def freeze(self) -> None:
        """
        Freeze registry after discovery. Enables concurrent reads.

        Called at the end of discovery phase, before rendering begins.
        After freezing, any mutation attempt raises RuntimeError.
        """
        self._frozen = True

    def unfreeze(self) -> None:
        """
        Unfreeze registry for dev server rebuilds.

        Called at start of reset_ephemeral_state() to allow re-population.
        """
        self._frozen = False

    def clear(self) -> None:
        """
        Clear all entries for rebuild. Also unfreezes.

        Called by Site.reset_ephemeral_state() before re-discovery.
        """
        self._pages_by_path.clear()
        self._sections_by_path.clear()
        self._pages_by_url.clear()
        self._sections_by_url.clear()
        self.url_ownership = URLRegistry()
        self._frozen = False

    @property
    def page_count(self) -> int:
        """Number of registered pages."""
        return len(self._pages_by_path)

    @property
    def section_count(self) -> int:
        """Number of registered sections."""
        return len(self._sections_by_path)

    def __repr__(self) -> str:
        frozen_str = " (frozen)" if self._frozen else ""
        return f"ContentRegistry(pages={self.page_count}, sections={self.section_count}{frozen_str})"
```

**Site delegation** (backward compatible):

```python
# In Site class
@property
def registry(self) -> ContentRegistry:
    """Content registry for O(1) lookups."""
    if self._registry is None:
        self._registry = ContentRegistry()
    return self._registry

def get_page_by_path(self, path: Path) -> Page | None:
    """Delegate to registry."""
    return self.registry.get_page(path)

def get_section_by_path(self, path: Path) -> Section | None:
    """Delegate to registry."""
    return self.registry.get_section(path)

def get_section_by_url(self, url: str) -> Section | None:
    """Delegate to registry."""
    return self.registry.get_section_by_url(url)
```

**Migration**: Update `_section_registry`, `_section_url_registry`, `url_registry` to use `ContentRegistry`.

---

### Phase 2: Extract BuildState (Week 3-4)

Extract mutable build-time state into a per-build context object.

**New File**: `bengal/orchestration/build_state.py`

```python
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any


@dataclass
class BuildState:
    """
    Mutable state for a single build execution.

    Created fresh for each build. Passed through orchestration phases.
    Never stored on Site—Site remains the stable data container.

    Lifecycle:
        1. Created at start of BuildOrchestrator.build()
        2. Passed through all 21 build phases
        3. Discarded after build completes (stats extracted first)

    Thread Safety:
        - get_lock() provides named locks for parallel operations
        - Per-build isolation prevents cross-build interference
        - DevServer creates new BuildState for each rebuild
    """

    # Build context
    build_time: datetime = field(default_factory=datetime.now)
    incremental: bool = False
    dev_mode: bool = False

    # Current render context (set per-page during rendering)
    current_language: str | None = None
    current_version: str | None = None

    # Discovery results
    features_detected: set[str] = field(default_factory=set)
    discovery_timing_ms: dict[str, float] = field(default_factory=dict)

    # Caches (cleared per-build)
    template_cache: dict[str, Any] = field(default_factory=dict)
    asset_manifest_cache: dict[str, Any] = field(default_factory=dict)
    theme_chain_cache: list[str] | None = None

    # Template directory caches
    template_dirs_cache: dict[str, Any] | None = None
    template_metadata_cache: dict[str, Any] | None = None

    # Asset manifest state
    asset_manifest_previous: Any = None
    asset_manifest_fallbacks: set[str] = field(default_factory=set)

    # Thread-safe locks (using defaultdict for atomic creation)
    _locks: dict[str, Lock] = field(default_factory=lambda: defaultdict(Lock))

    def get_lock(self, name: str) -> Lock:
        """
        Get or create a named lock for thread-safe operations.

        Thread-safe: defaultdict(Lock) ensures atomic lock creation.

        Args:
            name: Lock identifier (e.g., "asset_write", "template_compile")

        Returns:
            Lock instance for the given name

        Example:
            with state.get_lock("asset_manifest"):
                # Thread-safe manifest updates
                manifest[key] = value
        """
        return self._locks[name]

    def reset_caches(self) -> None:
        """Reset all caches for fresh build."""
        self.template_cache.clear()
        self.asset_manifest_cache.clear()
        self.theme_chain_cache = None
        self.template_dirs_cache = None
        self.template_metadata_cache = None
        self.features_detected.clear()
        self.asset_manifest_fallbacks.clear()

    def set_render_context(self, language: str | None, version: str | None) -> None:
        """
        Set current render context (called per-page during rendering).

        Args:
            language: Current language code (e.g., "en", "es") or None
            version: Current version ID (e.g., "v2", "latest") or None
        """
        self.current_language = language
        self.current_version = version

    def clear_render_context(self) -> None:
        """Clear render context after page rendering."""
        self.current_language = None
        self.current_version = None
```

**Updated BuildOrchestrator**:

```python
class BuildOrchestrator:
    def build(self, options: BuildOptions) -> BuildStats:
        # Create fresh state for this build
        state = BuildState(
            incremental=options.incremental,
            dev_mode=self.site.dev_mode,
        )

        # Attach state to site for template compatibility (temporary bridge)
        self.site._current_build_state = state

        try:
            # Pass state through phases instead of mutating Site
            initialization.phase_discovery(self, state, ...)
            content.phase_taxonomies(self, state, ...)
            rendering.phase_render(self, state, ...)

            return self._collect_stats(state)
        finally:
            # Clear state reference after build
            self.site._current_build_state = None
```

**Site compatibility layer**:

```python
# Site proxies to current build state for template compatibility
@property
def current_language(self) -> str | None:
    """Proxy to build state (for template compatibility)."""
    if self._current_build_state:
        return self._current_build_state.current_language
    # Fallback for direct Site access outside build context
    return self._current_language_fallback

@current_language.setter
def current_language(self, value: str | None) -> None:
    """Set on build state if active, otherwise set fallback."""
    if self._current_build_state:
        self._current_build_state.current_language = value
    else:
        self._current_language_fallback = value

@property
def features_detected(self) -> set[str]:
    """Proxy to build state."""
    if self._current_build_state:
        return self._current_build_state.features_detected
    return self._features_detected_fallback
```

---

### Phase 3: Extract SiteData and SiteContent (Week 5-6)

Extract immutable configuration and mutable content containers.

**New File**: `bengal/core/site_data.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from bengal.core.version import VersionConfig


@dataclass(frozen=True)
class SiteData:
    """
    Immutable site configuration and paths.

    Created once from config, never modified. Enables caching and
    thread-safe access without locks.

    Immutability Guarantees:
        - frozen=True prevents attribute assignment
        - MappingProxyType wraps config dict for read-only access
        - All Path attributes are computed at construction time

    Thread Safety:
        - Fully thread-safe for reads (immutable)
        - No locks required
        - Safe to share across parallel rendering threads
    """

    root_path: Path
    output_dir: Path
    config: MappingProxyType[str, Any]  # Immutable view
    theme_name: str
    version_config: VersionConfig

    # Computed paths
    content_dir: Path
    assets_dir: Path
    data_dir: Path
    cache_dir: Path

    @classmethod
    def from_config(cls, root_path: Path, config: dict[str, Any]) -> SiteData:
        """
        Create from config dict.

        Args:
            root_path: Site root directory (will be resolved to absolute)
            config: Configuration dictionary (will be wrapped as immutable)

        Returns:
            Frozen SiteData instance
        """
        root = root_path.resolve()

        # Extract theme name from nested config
        theme_section = config.get("theme", {})
        if isinstance(theme_section, dict):
            theme_name = theme_section.get("name", "default")
        else:
            theme_name = str(theme_section) if theme_section else "default"

        # Resolve output directory
        output_dir_str = config.get("output_dir", "public")
        output_dir = Path(output_dir_str)
        if not output_dir.is_absolute():
            output_dir = root / output_dir

        return cls(
            root_path=root,
            output_dir=output_dir,
            config=MappingProxyType(config),
            theme_name=theme_name,
            version_config=VersionConfig.from_config(config),
            content_dir=root / config.get("content_dir", "content"),
            assets_dir=root / "assets",
            data_dir=root / "data",
            cache_dir=root / ".bengal",
        )

    @property
    def baseurl(self) -> str:
        """Get baseurl from config."""
        return str(self.config.get("baseurl", ""))

    @property
    def title(self) -> str:
        """Get site title from config."""
        return str(self.config.get("title", ""))

    @property
    def author(self) -> str | None:
        """Get site author from config."""
        author = self.config.get("author")
        return str(author) if author else None

    def get_config_section(self, section: str) -> Mapping[str, Any]:
        """
        Get a config section with type safety.

        Args:
            section: Config section name (e.g., "build", "assets", "i18n")

        Returns:
            Config section as read-only mapping (empty dict if missing)
        """
        value = self.config.get(section)
        if isinstance(value, dict):
            return MappingProxyType(value)
        return MappingProxyType({})
```

**New File**: `bengal/core/site_content.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.core.asset import Asset
    from bengal.core.menu import MenuBuilder, MenuItem
    from bengal.core.page import Page
    from bengal.core.section import Section


@dataclass
class SiteContent:
    """
    Mutable content container populated during discovery.

    Lifecycle:
        1. Created empty at Site initialization
        2. Populated during discovery phase (pages, sections, assets)
        3. Extended during taxonomy/menu phases
        4. Frozen before rendering (optional, for safety)
        5. Cleared on rebuild via clear()

    Separation from Site:
        - Contains ONLY content data (pages, sections, assets)
        - No caches (those go in BuildState or derived properties)
        - No registries (those go in ContentRegistry)
        - No config (that goes in SiteData)

    Thread Safety:
        - Mutations during discovery are single-threaded
        - After freeze(), reads are safe for parallel rendering
        - Dev server calls clear() before re-discovery
    """

    # Core content
    pages: list[Page] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)

    # Derived content (populated after discovery)
    taxonomies: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Menu structures
    menu: dict[str, list[MenuItem]] = field(default_factory=dict)
    menu_builders: dict[str, MenuBuilder] = field(default_factory=dict)
    menu_localized: dict[str, dict[str, list[MenuItem]]] = field(default_factory=dict)
    menu_builders_localized: dict[str, dict[str, MenuBuilder]] = field(default_factory=dict)

    # Data directory content
    data: dict[str, Any] = field(default_factory=dict)

    # Frozen flag
    _frozen: bool = field(default=False, repr=False)

    # Cached derived lists (invalidated on changes)
    _regular_pages_cache: list[Page] | None = field(default=None, repr=False)
    _generated_pages_cache: list[Page] | None = field(default=None, repr=False)
    _listable_pages_cache: list[Page] | None = field(default=None, repr=False)

    def freeze(self) -> None:
        """Freeze content before rendering phase."""
        self._frozen = True

    def unfreeze(self) -> None:
        """Unfreeze for dev server rebuilds."""
        self._frozen = False

    def clear(self) -> None:
        """
        Clear all content for rebuild.

        Called by Site.reset_ephemeral_state() before re-discovery.
        """
        self.pages = []
        self.sections = []
        self.assets = []
        self.taxonomies = {}
        self.menu = {}
        self.menu_builders = {}
        self.menu_localized = {}
        self.menu_builders_localized = {}
        # Note: data is typically reloaded, not cleared
        self._frozen = False
        self.invalidate_caches()

    def invalidate_caches(self) -> None:
        """Invalidate derived page caches."""
        self._regular_pages_cache = None
        self._generated_pages_cache = None
        self._listable_pages_cache = None

    @property
    def regular_pages(self) -> list[Page]:
        """Get non-generated pages (cached)."""
        if self._regular_pages_cache is None:
            self._regular_pages_cache = [
                p for p in self.pages if not p.metadata.get("_generated")
            ]
        return self._regular_pages_cache

    @property
    def generated_pages(self) -> list[Page]:
        """Get generated pages (cached)."""
        if self._generated_pages_cache is None:
            self._generated_pages_cache = [
                p for p in self.pages if p.metadata.get("_generated")
            ]
        return self._generated_pages_cache

    @property
    def listable_pages(self) -> list[Page]:
        """Get pages visible in listings (cached)."""
        if self._listable_pages_cache is None:
            self._listable_pages_cache = [p for p in self.pages if p.in_listings]
        return self._listable_pages_cache

    def __repr__(self) -> str:
        frozen_str = " (frozen)" if self._frozen else ""
        return (
            f"SiteContent(pages={len(self.pages)}, "
            f"sections={len(self.sections)}, "
            f"assets={len(self.assets)}{frozen_str})"
        )
```

**Updated Site**:

```python
@dataclass
class Site:
    # Immutable data (set once)
    data: SiteData

    # Mutable content (populated during discovery)
    content: SiteContent

    # Registry (for lookups)
    registry: ContentRegistry

    # Current build state (set during build)
    _build_state: BuildState | None = None

    @classmethod
    def from_config(cls, root_path: Path) -> Site:
        config = ConfigLoader(root_path).load()
        return cls(
            data=SiteData.from_config(root_path, config),
            content=SiteContent(),
            registry=ContentRegistry(),
        )

    # Compatibility: delegate to data
    @property
    def root_path(self) -> Path:
        return self.data.root_path

    @property
    def config(self) -> Mapping[str, Any]:
        return self.data.config

    # Compatibility: delegate to content
    @property
    def pages(self) -> list[Page]:
        return self.content.pages

    @pages.setter
    def pages(self, value: list[Page]) -> None:
        self.content.pages = value
        self.content.invalidate_caches()
```

---

## Page/Section `_site` Reference Strategy

Currently, Page and Section objects hold `_site: Site | None` references for URL computation and lookups. This creates tight coupling.

### Strategy: Gradual Narrowing

**Phase 1 (Immediate)**: Keep `_site` reference as-is.

- No breaking changes
- Site façade still works

**Phase 2 (After BuildState)**: Add `_registry` as alternative.

```python
class Page:
    _site: Site | None = field(default=None, repr=False)
    _registry: ContentRegistry | None = field(default=None, repr=False)

    @property
    def section(self) -> Section | None:
        """Get section via registry (preferred) or site (fallback)."""
        if self._registry:
            return self._registry.get_section_by_url(self._section_url)
        if self._site:
            return self._site.get_section_by_url(self._section_url)
        return None
```

**Phase 3 (Long-term)**: Deprecate `_site`, prefer `_registry`.

```python
class Page:
    _registry: ContentRegistry  # Required
    _site: Site | None = field(default=None, repr=False)  # Deprecated

    def __post_init__(self):
        if self._site and not self._registry:
            warnings.warn(
                "Page._site is deprecated. Use _registry instead.",
                DeprecationWarning,
            )
            self._registry = self._site.registry
```

### Migration Path for Existing Code

1. Update `page._site = site` → `page._registry = site.registry`
2. Add compatibility shim in Page for transition period
3. Grep for `._site` assignments (51 found) and migrate incrementally

---

## DevServer Lifecycle Considerations

The dev server is a long-lived process that rebuilds on file changes. This RFC must preserve correct behavior.

### Current Pattern: reset_ephemeral_state()

```python
def reset_ephemeral_state(self) -> None:
    """Called by DevServer before each rebuild."""
    self.pages = []
    self.sections = []
    self.assets = []
    # ... 15+ more field resets
```

### New Pattern: Coordinated Reset

```python
def reset_ephemeral_state(self) -> None:
    """
    Clear ephemeral state for dev server rebuild.

    Coordinates clearing across all subsystems:
    - SiteContent: pages, sections, assets, menus
    - ContentRegistry: lookups and URL ownership
    - BuildState: (not cleared - new state created per build)
    """
    # Clear content container
    self.content.clear()

    # Clear and unfreeze registry for re-population
    self.registry.clear()

    # Clear derived caches (already handled by content.clear())
    # Note: BuildState is per-build, no clearing needed

    # Reset template caches (theme may have changed)
    self._theme_obj = None
```

### Invariant: Fresh BuildState Per Build

```python
# DevServer.trigger_rebuild()
def trigger_rebuild(self) -> None:
    self.site.reset_ephemeral_state()

    # BuildOrchestrator creates fresh BuildState
    # No stale state from previous build
    stats = self.site.build(incremental=True)
```

### What Persists Across Dev Server Rebuilds

| Subsystem | Persists? | Reason |
|-----------|-----------|--------|
| SiteData | ✅ Yes | Immutable config doesn't change |
| SiteContent | ❌ No | Rebuilt from disk |
| ContentRegistry | ❌ No | Rebuilt from content |
| BuildState | ❌ No | Fresh per build |
| BengalPaths | ✅ Yes | Derived from root_path |

---

## Migration Strategy

### Phase 1: ContentRegistry (Low Risk)

1. Create `ContentRegistry` class with tests
2. Add `Site.registry` property (lazy initialization)
3. Migrate `_section_registry` → `registry._sections_by_path`
4. Migrate `_section_url_registry` → `registry._sections_by_url`
5. Migrate `url_registry` → `registry.url_ownership`
6. Update `register_sections()` to use registry
7. Add `freeze()`/`clear()` calls in build phases
8. Deprecate direct registry field access

### Phase 2: BuildState (Medium Risk)

1. Create `BuildState` class with tests
2. Update `BuildOrchestrator.build()` to create/pass state
3. Add `Site._current_build_state` bridge property
4. Migrate `current_language`, `current_version` to state
5. Migrate `features_detected`, timing fields to state
6. Migrate `_bengal_*_cache` fields to state
7. Migrate `_asset_manifest_*` fields to state
8. Update template engine to accept state
9. Add Site proxy properties for template compatibility

### Phase 3: SiteData + SiteContent (Low Risk)

1. Create `SiteData` frozen dataclass with tests
2. Create `SiteContent` mutable container with tests
3. Update `Site.from_config()` to use new structure
4. Add delegation properties for backward compatibility
5. Update `reset_ephemeral_state()` to use `content.clear()`
6. Update tests to use new constructors
7. Deprecate direct field mutation on Site

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing tests | High | High | Preserve all public APIs via delegation; 380 test files may need updates |
| Performance regression | Low | Medium | Registry uses same dict lookups; benchmark before/after |
| Thread safety issues | Medium | High | BuildState uses defaultdict(Lock); registry freezes before render |
| DevServer regressions | Medium | High | Test rebuild cycles; preserve reset_ephemeral_state() semantics |
| Incomplete migration | Medium | Low | Each phase is independently valuable |
| Import cycles | Low | Medium | Keep new classes in separate modules |

---

## Success Criteria

### Phase 1 Complete

- [ ] `ContentRegistry` class exists in `bengal/core/registry.py`
- [ ] Unit tests: 100% coverage of ContentRegistry
- [ ] `Site.registry` property delegates correctly
- [ ] `Site.get_section_by_path()` delegates to registry
- [ ] `Site.get_section_by_url()` delegates to registry
- [ ] `register_sections()` uses registry internally
- [ ] `reset_ephemeral_state()` calls `registry.clear()`
- [ ] All existing tests pass
- [ ] **Performance**: `registry.get_section_by_path()` < 1µs (benchmark)
- [ ] **Memory**: No regression in 1000-page site peak memory

### Phase 2 Complete

- [ ] `BuildState` class exists in `bengal/orchestration/build_state.py`
- [ ] Unit tests: 100% coverage of BuildState
- [ ] `BuildOrchestrator.build()` creates fresh state per build
- [ ] `current_language`/`current_version` on state, proxied via Site
- [ ] `features_detected` on state, proxied via Site
- [ ] Template/asset caches moved from Site to BuildState
- [ ] Template engine receives state parameter
- [ ] DevServer rebuilds work correctly (no stale state)
- [ ] All existing tests pass
- [ ] **Thread safety**: Parallel render tests pass with BuildState

### Phase 3 Complete

- [ ] `SiteData` frozen dataclass exists in `bengal/core/site_data.py`
- [ ] `SiteContent` container exists in `bengal/core/site_content.py`
- [ ] Unit tests: 100% coverage of SiteData and SiteContent
- [ ] `Site.from_config()` uses new structure internally
- [ ] Config access is read-only (MappingProxyType)
- [ ] `reset_ephemeral_state()` uses `content.clear()`
- [ ] Delegation properties work for backward compatibility
- [ ] All existing tests pass
- [ ] **Code size**: Site class < 200 lines (down from 720+)
- [ ] **Type safety**: Reduce `# type: ignore` by 20+

---

## Appendix: Field Inventory

Current Site fields categorized by extraction target:

| Field | Target | Notes |
|-------|--------|-------|
| `root_path` | SiteData | Immutable |
| `config` | SiteData | Wrap in MappingProxyType |
| `output_dir` | SiteData | Immutable |
| `theme` | SiteData | Immutable |
| `version_config` | SiteData | Immutable |
| `pages` | SiteContent | Mutable during discovery |
| `sections` | SiteContent | Mutable during discovery |
| `assets` | SiteContent | Mutable during discovery |
| `taxonomies` | SiteContent | Mutable during discovery |
| `menu` | SiteContent | Mutable during discovery |
| `menu_builders` | SiteContent | Mutable during discovery |
| `menu_localized` | SiteContent | Mutable during discovery |
| `data` | SiteContent | Loaded from data/ |
| `build_time` | BuildState | Per-build |
| `dev_mode` | BuildState | Per-build |
| `current_language` | BuildState | Per-page during render |
| `current_version` | BuildState | Per-page during render |
| `features_detected` | BuildState | Per-build |
| `_discovery_breakdown_ms` | BuildState | Per-build timing |
| `_bengal_theme_chain_cache` | BuildState | Per-build cache |
| `_bengal_template_dirs_cache` | BuildState | Per-build cache |
| `_bengal_template_metadata_cache` | BuildState | Per-build cache |
| `_asset_manifest_previous` | BuildState | Per-build state |
| `_asset_manifest_fallbacks_global` | BuildState | Per-build state |
| `_section_registry` | ContentRegistry | O(1) lookups |
| `_section_url_registry` | ContentRegistry | O(1) lookups |
| `url_registry` | ContentRegistry | URL ownership |
| `_page_path_map` | ContentRegistry | O(1) lookups |
| `_regular_pages_cache` | SiteContent | Derived from pages |
| `_generated_pages_cache` | SiteContent | Derived from pages |
| `_listable_pages_cache` | SiteContent | Derived from pages |

---

## Related RFCs

- `rfc-mixin-composition.md` - Existing mixin patterns to follow
- `rfc-site-runtime-state-formalization.md` - Prior work on runtime state
- `rfc-modularize-large-files.md` - File size guidelines

---

## Implementation Plan

### Phase 1: Extract ContentRegistry (Detailed Tasks)

**Estimated Effort**: 12-16 hours

#### Task 1.1: Create ContentRegistry Class
- **File**: `bengal/core/registry.py` (new)
- **Dependencies**: None
- **Implementation**:
  - Create `ContentRegistry` dataclass with frozen support
  - Implement `_pages_by_path`, `_pages_by_url`, `_sections_by_path`, `_sections_by_url` dicts
  - Implement `register_page()`, `register_section()` methods
  - Implement `get_page()`, `get_page_by_url()`, `get_section()`, `get_section_by_url()` methods
  - Implement `freeze()`, `unfreeze()`, `clear()` lifecycle methods
  - Include `url_ownership: URLRegistry` composition

#### Task 1.2: Add Site.registry Property
- **File**: `bengal/core/site/core.py`
- **Dependencies**: Task 1.1
- **Implementation**:
  - Add `_registry: ContentRegistry | None` field
  - Add `@property def registry` with lazy initialization
  - Initialize in `__post_init__`

#### Task 1.3-1.5: Migrate Existing Registries
- **Files to modify**:
  - `bengal/core/site/section_registry.py` - Delegate to registry
  - `bengal/core/site/core.py` - Remove redundant fields
- **Migration mapping**:
  - `_section_registry` → `registry._sections_by_path`
  - `_section_url_registry` → `registry._sections_by_url`
  - `url_registry` → `registry.url_ownership`
- **Backward compatibility**: Keep original method signatures, delegate internally

#### Task 1.6: Update SectionRegistryMixin
- **File**: `bengal/core/site/section_registry.py`
- **Changes**:
  - `register_sections()` → call `registry.register_section()`
  - `get_section_by_path()` → delegate to `registry.get_section()`
  - `get_section_by_url()` → delegate to `registry.get_section_by_url()`
  - `_normalize_section_path()` → move to registry or keep as utility

#### Task 1.7: Add Freeze/Unfreeze in Build Phases
- **File**: `bengal/orchestration/build/__init__.py`
- **Changes**:
  - Call `site.registry.freeze()` after Phase 5 (before rendering)
  - Call `site.registry.unfreeze()` at start of `reset_ephemeral_state()`

#### Task 1.8: Update reset_ephemeral_state()
- **File**: `bengal/core/site/core.py`
- **Changes**:
  - Replace manual registry clearing with `self.registry.clear()`
  - Verify `url_registry` is recreated via `registry.clear()`

#### Task 1.9: Unit Tests
- **File**: `tests/unit/core/test_content_registry.py` (new)
- **Coverage targets**:
  - Registration (page, section, virtual section)
  - Lookups (by path, by URL)
  - Freeze/unfreeze lifecycle
  - Clear behavior
  - URL ownership integration

#### Task 1.10: Add Page Registration
- **Files**:
  - `bengal/core/registry.py` - Add `register_page()` method
  - `bengal/orchestration/content.py` - Call registry during discovery
- **Note**: Pages currently don't have a registry; this enables future O(1) page lookups

---

### Phase 2: Extract BuildState (Detailed Tasks)

**Estimated Effort**: 16-20 hours

#### Task 2.1: Create BuildState Class
- **File**: `bengal/orchestration/build_state.py` (new)
- **Dependencies**: None
- **Implementation**:
  - Create `BuildState` dataclass
  - Include: `build_time`, `dev_mode`, `incremental`, `current_language`, `current_version`
  - Include: `features_detected`, `discovery_timing_ms`
  - Include: Template caches (`template_cache`, `theme_chain_cache`, etc.)
  - Include: Asset state (`asset_manifest_previous`, `asset_manifest_fallbacks`)
  - Implement `get_lock(name)` using `defaultdict(Lock)`
  - Implement `reset_caches()`, `set_render_context()`, `clear_render_context()`

#### Task 2.2: Update BuildOrchestrator.build()
- **File**: `bengal/orchestration/build/__init__.py`
- **Changes**:
  - Create `BuildState()` at start of `build()`
  - Attach as `self.site._current_build_state = state`
  - Pass `state` through phase functions
  - Clear `self.site._current_build_state = None` in `finally` block

#### Task 2.3: Add Site Bridge Property
- **File**: `bengal/core/site/core.py`
- **Changes**:
  - Add `_current_build_state: BuildState | None` field
  - Property proxies for template compatibility

#### Task 2.4: Migrate current_language/current_version
- **Files to modify** (23 files use these):
  - `bengal/core/site/core.py` - Add proxy properties
  - `bengal/rendering/pipeline/autodoc_renderer.py`
  - `bengal/rendering/template_engine/environment.py`
  - `bengal/rendering/template_functions/i18n.py`
  - `bengal/orchestration/taxonomy.py`
  - (and 18 more files)
- **Strategy**: Site properties proxy to `_current_build_state`, fallback to instance field

#### Task 2.5: Migrate features_detected
- **Files to modify** (7 files):
  - `bengal/core/site/core.py` - Proxy property
  - `bengal/orchestration/feature_detector.py`
  - `bengal/orchestration/css_optimizer.py`
  - `bengal/orchestration/content.py`
  - `bengal/core/site/discovery.py`

#### Task 2.6: Migrate Template Caches
- **Files**:
  - `bengal/core/site/core.py` - Remove `_bengal_*_cache` fields
  - `bengal/rendering/template_engine/environment.py` - Use BuildState caches

#### Task 2.7: Migrate Asset Manifest State
- **Files**:
  - `bengal/core/site/core.py` - Remove `_asset_manifest_*` fields
  - `bengal/orchestration/asset.py` - Use BuildState for manifest tracking

#### Task 2.8: Site Proxy Properties
```python
# Pattern for each proxied field
@property
def current_language(self) -> str | None:
    if self._current_build_state:
        return self._current_build_state.current_language
    return self._current_language_fallback

@current_language.setter
def current_language(self, value: str | None) -> None:
    if self._current_build_state:
        self._current_build_state.current_language = value
    else:
        self._current_language_fallback = value
```

#### Task 2.9: Unit Tests
- **File**: `tests/unit/orchestration/test_build_state.py` (new)
- **Coverage targets**:
  - Lock management (`get_lock`)
  - Cache reset behavior
  - Render context management
  - Thread safety of lock creation

---

### Phase 3: Extract SiteData & SiteContent (Detailed Tasks)

**Estimated Effort**: 12-16 hours

#### Task 3.1: Create SiteData Frozen Dataclass
- **File**: `bengal/core/site_data.py` (new)
- **Implementation**:
  - `@dataclass(frozen=True)` for immutability
  - Fields: `root_path`, `output_dir`, `config` (MappingProxyType), `theme_name`
  - Fields: `content_dir`, `assets_dir`, `data_dir`, `cache_dir`
  - `@classmethod from_config(cls, root_path, config)`
  - Properties: `baseurl`, `title`, `author`, `get_config_section()`

#### Task 3.2: Create SiteContent Container
- **File**: `bengal/core/site_content.py` (new)
- **Implementation**:
  - Mutable dataclass for content storage
  - Fields: `pages`, `sections`, `assets`
  - Fields: `taxonomies`, `menu`, `menu_builders`, `menu_localized`, `menu_builders_localized`
  - Fields: `data`
  - Cached derived lists: `_regular_pages_cache`, `_generated_pages_cache`, `_listable_pages_cache`
  - Methods: `freeze()`, `unfreeze()`, `clear()`, `invalidate_caches()`
  - Properties: `regular_pages`, `generated_pages`, `listable_pages`

#### Task 3.3: Update Site.from_config()
- **File**: `bengal/core/site/factories.py`
- **Changes**:
  - Create `SiteData.from_config(root_path, config)`
  - Create `SiteContent()`
  - Initialize `Site` with new structure

#### Task 3.4: Delegation Properties
- **File**: `bengal/core/site/core.py`
- **Add properties delegating to data/content**:
  - `@property def root_path` → `self.data.root_path`
  - `@property def config` → `self.data.config`
  - `@property def pages` → `self.content.pages`
  - `@pages.setter def pages` → `self.content.pages = value; self.content.invalidate_caches()`

#### Task 3.5: Update reset_ephemeral_state()
- **File**: `bengal/core/site/core.py`
- **Change**: Replace manual clearing with `self.content.clear()`

#### Task 3.6: Move Cached Page Lists
- **File**: `bengal/core/site/page_caches.py`
- **Strategy**:
  - Keep mixin for backward compatibility
  - Delegate to `self.content.regular_pages`, etc.
  - Or inline into SiteContent (preferred)

#### Task 3.7: Unit Tests
- **Files**:
  - `tests/unit/core/test_site_data.py` (new)
  - `tests/unit/core/test_site_content.py` (new)
- **Coverage**: Immutability, config access, content lifecycle

#### Task 3.8: Page/Section _site Migration (Deferred)
- **Files** (7 files with `_site` references):
  - `bengal/core/page/__init__.py`
  - `bengal/core/page/metadata.py`
  - `bengal/core/page/navigation.py`
  - `bengal/core/page/proxy.py`
  - `bengal/core/section/navigation.py`
  - `bengal/core/nav_tree.py`
  - `bengal/core/asset/asset_core.py`
- **Strategy**: Add `_registry` field alongside `_site` for gradual migration

---

### Testing Strategy

#### Unit Tests (Per Phase)
| Phase | Test File | Key Scenarios |
|-------|-----------|---------------|
| 1 | `test_content_registry.py` | Registration, lookups, freeze lifecycle |
| 2 | `test_build_state.py` | Lock safety, cache reset, context |
| 3 | `test_site_data.py` | Immutability, config wrapping |
| 3 | `test_site_content.py` | Clear, invalidation, caches |

#### Integration Tests
- **File**: `tests/integration/test_site_refactor.py` (new)
- **Scenarios**:
  - Full build with new structure matches old behavior
  - Dev server rebuild cycle
  - Incremental build cache behavior
  - Parallel rendering thread safety

#### Regression Tests
- Run full test suite after each phase (380 test files)
- Benchmark 1000-page site before/after each phase
- Memory profiling to verify no regression

---

### Rollback Plan

Each phase can be reverted independently:

**Phase 1 Rollback**:
- Remove `ContentRegistry` class
- Restore direct dict usage in `SectionRegistryMixin`
- ~2 hours to rollback

**Phase 2 Rollback**:
- Remove `BuildState` class
- Restore direct field access on Site
- Update 23 files to remove proxy pattern
- ~4 hours to rollback

**Phase 3 Rollback**:
- Remove `SiteData` and `SiteContent` classes
- Restore direct field initialization
- ~3 hours to rollback

---

### Performance Benchmarks

Execute before and after each phase:

```bash
# 1000-page benchmark
uv run python -m pytest benchmarks/test_build.py -k "test_build_time" -v

# Memory profiling
uv run python -m pytest benchmarks/test_build.py -k "test_memory" -v

# Registry lookup performance (Phase 1)
uv run python -m pytest tests/performance/test_registry_perf.py -v
```

**Phase 1 Targets**:
- `registry.get_section_by_path()` < 1µs average
- No memory regression on 1000-page site

**Phase 2 Targets**:
- No build time regression
- Thread safety: parallel render tests pass

**Phase 3 Targets**:
- Site class < 200 lines (down from 720+)
- Config access via MappingProxyType < 10ns overhead

---

## Changelog

### 2024-12-23 - Revision 2
- Added `SiteContent` implementation details
- Fixed thread-safety issue in `BuildState.get_lock()` (now uses defaultdict)
- Added Page/Section `_site` reference migration strategy
- Added DevServer lifecycle considerations section
- Added performance benchmarks to success criteria
- Updated risk assessment with realistic likelihood ratings
- Expanded field inventory with all discovered fields

### 2024-12-23 - Initial Draft
- Problem analysis with field inventory
- Three-phase extraction plan
- Backward compatibility strategy
