# RFC: Navigation Tree Architecture

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-20  
**Updated**: 2025-12-20  
**Scope**: Core architecture for version-aware navigation  
**Confidence**: 72% 🟡 (Moderate - pending prior art reconciliation)

---

## Executive Summary

Bengal's navigation templates currently traverse `Section` objects at render time, requiring version-filtering logic in Jinja templates. While the recently-implemented `pages_for_version()` methods have simplified this, templates still manage Section traversal, active trail detection, and URL normalization.

This RFC proposes a **NavTree** abstraction that:
1. Pre-computes the logical navigation structure once per build
2. Caches the result per version for O(1) template access
3. Handles active trail marking automatically
4. Provides a cleaner template API than direct Section manipulation

**Key Distinction**: This RFC builds on the implemented `rfc-version-aware-section-methods.md` as an evolution, not a replacement. NavTree encapsulates version-aware Section methods into a cached, template-optimized structure.

## Prior Art

### Existing Navigation Infrastructure

Bengal already has navigation helpers in `bengal/rendering/template_functions/navigation/`:

| Component | Location | Purpose | Relationship to This RFC |
|-----------|----------|---------|--------------------------|
| `NavTreeItem` | `models.py:149-211` | Dataclass for nav tree nodes | **Superseded** by `NavNode` |
| `get_nav_tree()` | `tree.py:17-178` | Builds flat list with depth | **Replaced** by cached NavTree |
| `get_breadcrumbs()` | `breadcrumbs.py` | Breadcrumb trail | Unchanged |
| `get_auto_nav()` | `auto_nav.py` | Auto-discovered nav items | Unchanged |

### Recently Implemented: Version-Aware Section Methods

`rfc-version-aware-section-methods.md` was **implemented** and added to Section:

```python
# bengal/core/section.py:463-486
def pages_for_version(self, version_id: str | None) -> list[Page]:
    """Get pages matching the specified version."""
    if version_id is None:
        return self.sorted_pages
    return [p for p in self.sorted_pages if getattr(p, "version", None) == version_id]

def subsections_for_version(self, version_id: str | None) -> list[Section]:
    """Get subsections that have content for the specified version."""
    ...
```

The current `docs-nav.html` already uses these methods (lines 57-58):

```jinja
{% set sorted_pages = root_section.pages_for_version(version_filter) %}
{% set sorted_subsections = root_section.subsections_for_version(version_filter) %}
```

**This RFC builds on that foundation** by encapsulating these methods into a cached, pre-computed structure.

---

## Problem Statement

### Current State (Post Version-Aware Methods)

The template has improved but still has 161 lines with:

1. **Section traversal in templates**: Templates still call `root_section.pages_for_version()` and manage iteration
2. **Active trail detection**: Each template render computes URL normalization and matching
3. **No caching**: Same navigation structure recomputed for every page render
4. **Scattered concerns**: URL normalization, version filtering, icon handling all in Jinja

### Remaining Pain Points

```jinja
{# docs-nav.html still requires ~40 lines of boilerplate per navigation context #}
{% set current_version_id = current_version.id if (current_version is defined and current_version) else ... %}
{% set version_filter = current_version_id if site.versioning_enabled else none %}
{% set sorted_pages = root_section.pages_for_version(version_filter) %}
{% set sorted_subsections = root_section.subsections_for_version(version_filter) %}
{% set current_url = page.relative_url.rstrip('/') if (page is defined and page and page.relative_url) else '' %}
{# ... then iterate and check active state for each item ... #}
```

### Physical vs Logical Mismatch (Concrete Example)

For versioned content at `_versions/v1/docs/guide.md`:
- **Physical path**: `_versions/v1/docs/guide.md`
- **Section.root.path**: `_versions` (physical root)
- **Expected nav root**: `docs` (logical root for user)

The `nav_root` metadata (`section.py:279-304`) allows overriding this, but requires manual configuration per versioned section.

### What Best SSGs Do

| SSG | Approach |
|-----|----------|
| **Docusaurus** | Dedicated sidebar config per version, sidebar is first-class |
| **VuePress** | Sidebar config in `.vuepress/config.js`, version-aware |
| **MkDocs** | `nav:` config in `mkdocs.yml`, mike plugin for versioning |
| **Sphinx** | `toctree` directive, separate builds per version |

**Common pattern**: Navigation is a **computed, cached structure** separate from content hierarchy.

## Design Options

### Option A: NavTree with Per-Version Caching (Recommended)

Pre-compute navigation tree once per version, cache for O(1) template access.

**Pros**:
- Single function call in templates (`get_nav_tree(page)`)
- Automatic active trail marking
- O(1) cache lookup per render
- Clear separation: Python builds structure, templates render it
- Leverages existing `pages_for_version()` methods

**Cons**:
- New abstraction layer to maintain
- Memory overhead for cached trees (~200KB per 1000 pages per version)
- Cache invalidation complexity for incremental builds

### Option B: Enhanced Template Functions (Minimal Change)

Keep Section-based approach but add more helper functions.

**Pros**:
- Smaller change surface
- No new core data structures
- Familiar patterns

**Cons**:
- Still requires Section traversal in templates
- No caching benefit
- Active trail logic remains template-side

### Option C: Config-Based Navigation (like MkDocs)

Define navigation explicitly in YAML config.

**Pros**:
- Full control over navigation structure
- No auto-discovery complexity

**Cons**:
- Loses Bengal's auto-discovery strength
- Manual maintenance burden
- Diverges from existing patterns

### Recommendation: Option A

Option A provides the best balance of template simplicity, performance, and maintainability. It builds naturally on the existing `pages_for_version()` infrastructure while providing a clean abstraction for templates.

---

## Proposed Architecture

### Design Principles

1. **Separation of Concerns**: Physical structure (Section) vs logical navigation (NavTree)
2. **Compute Once, Use Many**: NavTree built once per version, cached
3. **Version-Native**: Versioning is first-class, not bolted on
4. **Template Simplicity**: Single function call, clean API
5. **Performance**: O(1) tree lookup, cached per version

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        Template Layer                            │
│                                                                  │
│  {% set nav = get_nav_tree(page) %}                             │
│  {% for item in nav.children %}...{% endfor %}                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      NavTree (Logical)                           │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                   │
│  │ NavNode  │───▶│ NavNode  │───▶│ NavNode  │                   │
│  │ "docs"   │    │ "about"  │    │ "guide"  │                   │
│  └──────────┘    └──────────┘    └──────────┘                   │
│                                                                  │
│  • Computed from Section + Version config                        │
│  • Cached per version (NavTreeCache)                            │
│  • Active trail marked per-page                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Section (Physical)                           │
│                                                                  │
│  _versions/v1/docs/about/guide.md                                │
│                                                                  │
│  • Represents file system                                        │
│  • Used for discovery, watching, incremental builds              │
│  • Contains Page objects                                         │
└─────────────────────────────────────────────────────────────────┘
```

### Data Models

> **Note**: `NavNode` supersedes the existing `NavTreeItem` in `models.py`.
> The existing `get_nav_tree()` function will be updated to return `NavTree` instead of `list[dict]`.

```python
# bengal/core/nav_tree.py

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from threading import Lock
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.core.section import Section
    from bengal.core.site import Site
    from bengal.core.version import Version


@dataclass(slots=True)
class NavNode:
    """
    Node in the navigation tree.

    Represents a single navigation item (section or page) with its children.
    Designed for efficient template rendering with dict-compatible access.

    Attributes:
        id: Unique identifier (URL path without leading/trailing slashes)
        title: Display title for navigation
        url: Full URL path
        icon: Optional icon name (from frontmatter)
        weight: Sort weight (lower = earlier)
        children: Child navigation nodes
        page: Associated Page object (for leaf nodes)
        section: Associated Section object (for container nodes)
        is_index: True if this represents a section's index page
        is_current: True if this is the currently viewed page
        is_in_trail: True if this node is in the path to current page
        is_expanded: True if this node should be expanded in UI
    """
    id: str
    title: str
    url: str
    icon: str | None = None
    weight: int = 0
    children: list[NavNode] = field(default_factory=list)
    page: Page | None = field(default=None, repr=False)
    section: Section | None = field(default=None, repr=False)
    is_index: bool = False
    is_current: bool = False
    is_in_trail: bool = False
    is_expanded: bool = False

    @property
    def has_children(self) -> bool:
        """Whether this node has child nodes."""
        return len(self.children) > 0

    @property
    def depth(self) -> int:
        """Depth of this node (computed from URL path segments)."""
        return len(self.id.strip('/').split('/')) if self.id else 0

    def __getitem__(self, key: str) -> Any:
        """Dict-style access for Jinja template compatibility."""
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style get for Jinja template compatibility."""
        return getattr(self, key, default)

    def walk(self) -> Iterator[NavNode]:
        """Iterate over this node and all descendants."""
        yield self
        for child in self.children:
            yield from child.walk()

    def find(self, url: str) -> NavNode | None:
        """Find node by URL in this subtree."""
        normalized_url = url.rstrip('/')
        for node in self.walk():
            if node.url.rstrip('/') == normalized_url:
                return node
        return None


@dataclass
class NavTree:
    """
    Version-aware navigation tree.

    This is the primary navigation abstraction in Bengal. It represents
    the user-facing navigation structure, which may differ from the
    physical file structure (especially for versioned content).

    NavTree is:
    - Computed once during build (cached per version)
    - Version-aware (one tree per version)
    - Independent of physical file structure
    - Optimized for template rendering

    Example:
        # In template function
        def get_nav_tree(page: Page) -> NavTree:
            version_id = page.version
            return NavTreeCache.get(page._site, version_id)

        # In Jinja template
        {% set nav = get_nav_tree(page) %}
        <nav>
          <h2>{{ nav.root.title }}</h2>
          {% for item in nav.root.children %}
            {% include 'nav-item.html' %}
          {% endfor %}
        </nav>
    """
    root: NavNode
    version_id: str | None = None
    versions: list[dict] = field(default_factory=list)
    current_version: dict | None = None

    @cached_property
    def flat_nodes(self) -> list[NavNode]:
        """All nodes as a flat list (for search, indexing)."""
        return list(self.root.walk())

    @cached_property
    def urls(self) -> set[str]:
        """Set of all URLs in this tree (for O(1) membership checks)."""
        return {node.url.rstrip('/') for node in self.flat_nodes}

    def find(self, url: str) -> NavNode | None:
        """Find node by URL."""
        return self.root.find(url)

    def with_active_trail(self, current_page: Page) -> NavTree:
        """
        Return a copy with active trail marked.

        This creates a new NavTree with is_current and is_in_trail
        set appropriately for the given page. The original tree
        is not modified (allows caching).
        """
        # Implementation would deep-copy and mark trail
        ...

    @classmethod
    def build(cls, site: Site, version_id: str | None = None) -> NavTree:
        """
        Build navigation tree for a version.

        This is the main factory method. It:
        1. Finds the logical root section for the version
        2. Builds NavNode tree from sections/pages
        3. Filters by version
        4. Sorts by weight
        5. Resolves logical URLs (strips _versions prefix)

        Args:
            site: Site instance
            version_id: Version to build for (None = all/latest)

        Returns:
            Complete NavTree for the version
        """
        ...


class NavTreeCache:
    """
    Thread-safe cache for NavTree instances per version.

    NavTrees are expensive to build (traverse all sections/pages)
    but cheap to query. We build once per version per build.

    Thread Safety:
        Uses a lock to protect cache access during parallel builds.
        The lock is fine-grained: held only during dict operations,
        not during tree building (which can be slow).

    Cache is invalidated on:
    - Full rebuild (site object changes)
    - Content changes that affect navigation
    - Incremental builds with structural changes
    """
    _trees: dict[str | None, NavTree] = {}
    _site: Site | None = None
    _lock: Lock = Lock()

    @classmethod
    def get(cls, site: Site, version_id: str | None = None) -> NavTree:
        """Get or build NavTree for a version (thread-safe)."""
        with cls._lock:
            # Invalidate if site changed
            if cls._site is not site:
                cls._trees.clear()
                cls._site = site

            if version_id in cls._trees:
                return cls._trees[version_id]

        # Build outside lock (expensive operation)
        tree = NavTree.build(site, version_id)

        with cls._lock:
            # Double-check: another thread may have built it
            if version_id not in cls._trees:
                cls._trees[version_id] = tree
            return cls._trees[version_id]

    @classmethod
    def invalidate(cls, version_id: str | None = None) -> None:
        """Invalidate cache (thread-safe)."""
        with cls._lock:
            if version_id is None:
                cls._trees.clear()
            else:
                cls._trees.pop(version_id, None)
```

### Template API

```python
# bengal/rendering/template_functions/navigation/nav_tree.py

def register(env: Environment, site: Site) -> None:
    """Register nav tree functions."""

    def get_nav_tree(page: Page | None = None) -> NavTree:
        """
        Get navigation tree for the current page's version.

        This is the recommended way to get navigation in templates.
        The tree is cached per version, and the active trail is
        marked based on the current page.

        Example:
            {% set nav = get_nav_tree(page) %}

            {# Root section #}
            <a href="{{ nav.root.url }}">{{ nav.root.title }}</a>

            {# Navigation items #}
            {% for item in nav.root.children %}
              <a href="{{ item.url }}"
                 class="{{ 'active' if item.is_current }} {{ 'in-trail' if item.is_in_trail }}">
                {{ item.title }}
              </a>
              {% if item.has_children and item.is_in_trail %}
                {# Render children #}
              {% endif %}
            {% endfor %}

            {# Version selector #}
            {% if nav.versions | length > 1 %}
              <select onchange="location.href = this.value">
                {% for v in nav.versions %}
                  <option value="{{ v.url }}" {{ 'selected' if v.id == nav.version_id }}>
                    {{ v.label }}
                  </option>
                {% endfor %}
              </select>
            {% endif %}
        """
        version_id = page.version if page else None
        tree = NavTreeCache.get(site, version_id)

        if page:
            return tree.with_active_trail(page)
        return tree

    env.globals["get_nav_tree"] = get_nav_tree
```

### Simplified Template

```jinja
{# partials/docs-nav.html - SIMPLIFIED #}

{% set nav = get_nav_tree(page) %}

<nav class="docs-nav" aria-label="Documentation pages">
  {# Version Selector #}
  {% if nav.versions | length > 1 %}
    {% include 'partials/version-selector.html' %}
  {% endif %}

  {# Navigation Tree #}
  <div class="docs-nav-tree">
    {# Root link #}
    <a href="{{ nav.root.url }}"
       class="docs-nav-link docs-nav-link--root {{ 'active' if nav.root.is_current }}">
      {{ nav.root.title }}
    </a>

    {# Navigation items - recursive macro #}
    {% macro render_nav_item(item, depth=0) %}
      <div class="docs-nav-group" data-depth="{{ depth }}">
        <a href="{{ item.url }}"
           class="docs-nav-link {{ 'active' if item.is_current }} {{ 'in-trail' if item.is_in_trail }}">
          {% if item.icon %}{{ icon(item.icon) }}{% endif %}
          {{ item.title }}
        </a>

        {% if item.has_children %}
          <div class="docs-nav-children {{ 'expanded' if item.is_in_trail }}">
            {% for child in item.children %}
              {{ render_nav_item(child, depth + 1) }}
            {% endfor %}
          </div>
        {% endif %}
      </div>
    {% endmacro %}

    {% for item in nav.root.children %}
      {{ render_nav_item(item) }}
    {% endfor %}
  </div>
</nav>
```

## Performance Characteristics

### Build Time

- **NavTree.build()**: O(n) where n = total pages/sections
- Called once per version per build
- Result cached in `NavTreeCache`

### Render Time

- **get_nav_tree()**: O(1) cache lookup
- **with_active_trail()**: O(depth) where depth = page nesting level
- Template rendering: O(m) where m = visible nav items

### Memory

- One NavTree per version (typical: 1-5 versions)
- NavNode uses `__slots__` for memory efficiency
- ~200 bytes per node (title + url + refs)
- 1000-page site ≈ 200KB per version

### Incremental Builds

- NavTreeCache invalidated when:
  - New pages added/removed
  - Page metadata changes (title, weight, icon)
  - Section structure changes
- NOT invalidated for content-only changes

## Migration Path

### Phase 1: Add NavTree Core (Non-Breaking)

1. Implement `NavNode`, `NavTree`, `NavTreeCache` in `bengal/core/nav_tree.py`
2. Add thread-safe caching with `Lock`
3. **Update existing** `get_nav_tree()` in `navigation/tree.py` to return `NavTree`
4. Deprecate `NavTreeItem` in `navigation/models.py` (mark for removal in v2.0)
5. Existing templates continue to work (backward compatible)

**Files Changed**:
- `bengal/core/nav_tree.py` (new)
- `bengal/rendering/template_functions/navigation/tree.py` (update)
- `bengal/rendering/template_functions/navigation/models.py` (deprecation notice)

### Phase 2: Simplify Default Theme

1. Update `docs-nav.html` to use new `get_nav_tree(page)` API
2. Remove version-filtering boilerplate (~40 lines)
3. Use `NavNode.is_current` and `is_in_trail` instead of URL comparisons
4. Simplify recursive rendering with `NavNode.children`

**Target**: `docs-nav.html` reduced from 161 lines to <60 lines

### Phase 3: Deprecate Legacy Patterns

1. Keep `section.pages_for_version()` (no deprecation - still useful for custom templates)
2. Remove deprecated `NavTreeItem` in v2.0
3. Update documentation to recommend `get_nav_tree()` for all navigation needs

## Alternatives Considered

### 1. Keep Current Section-Based Approach (Status Quo)

Continue using `section.pages_for_version()` directly in templates.

**Why not chosen**:
- Templates still manage traversal and active trail detection
- No caching benefit
- 161 lines in docs-nav.html vs target of <60

**Note**: The version-aware methods remain valuable for custom templates; this RFC doesn't deprecate them.

### 2. Virtual Sections

Create virtual `Section` objects for versioned content that map to logical paths.

**Why not chosen**:
- Conflates physical and logical concerns
- Section already has many responsibilities
- Would complicate incremental builds and caching

### 3. Config-Based Navigation (like MkDocs)

Define navigation explicitly in config file.

**Why not chosen**:
- Loses auto-discovery (Bengal's strength)
- Manual maintenance burden
- Could be added later as optional enhancement on top of NavTree

### 4. Extend Existing NavTreeItem

Enhance the existing `NavTreeItem` dataclass instead of creating `NavNode`.

**Why not chosen**:
- `NavTreeItem` is in `rendering/` (template layer), not `core/`
- NavTree needs core-layer access for Section/Page relationships
- Clean break allows better API design

## Success Criteria

| Criterion | Target | Current | Measurement |
|-----------|--------|---------|-------------|
| Template simplicity | `docs-nav.html` < 60 lines | 161 lines | Line count |
| Render overhead | < 1ms per page | ~5ms (estimate) | Benchmark with 100-page site |
| Cache hit rate | > 99% for same-version pages | N/A | Logging in dev mode |
| Test coverage | > 90% for NavTree | N/A | pytest-cov |
| Backward compatibility | All existing templates work | N/A | Integration tests |

### Test Requirements

1. **Unit tests** for `NavNode`, `NavTree`, `NavTreeCache`
2. **Thread-safety test** for concurrent cache access
3. **Integration test** with versioned site (`tests/roots/test-versioned/`)
4. **Regression test** for existing `get_nav_tree()` callers

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Template regression during migration | Medium | High | Keep backward compat in Phase 1; thorough testing |
| Cache invalidation bugs in incremental builds | Medium | Medium | Clear invalidation on structural changes; test with file watcher |
| Thread contention on cache lock | Low | Low | Lock held only for dict access, not tree building |
| Memory pressure with many versions | Low | Low | ~200KB per 1000 pages per version; acceptable |
| Confusion between NavNode and NavTreeItem | Medium | Low | Clear deprecation notice; remove NavTreeItem in v2.0 |

---

## Open Questions

1. **Custom nav ordering**: Should NavTree support ordering beyond weight (e.g., alphabetical, date)?
   - **Recommendation**: Start with weight only; add ordering options in Phase 2 if needed

2. **Search integration**: Should NavTree include content snippets for client-side search?
   - **Recommendation**: No, keep NavTree focused on navigation; search is separate concern

3. **Menu system interaction**: How does NavTree relate to the existing menu builder?
   - **Recommendation**: NavTree handles auto-discovered nav; menus remain for custom navigation

4. **Incremental build integration**: How does cache invalidation work with `IncrementalOrchestrator`?
   - **Recommendation**: Invalidate on `structural_changed=True` flag (already tracked)

## Related Work

- [Docusaurus Sidebar](https://docusaurus.io/docs/sidebar)
- [VuePress Sidebar](https://vuepress.vuejs.org/theme/default-theme-config.html#sidebar)
- [Sphinx toctree](https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-toctree)

## Appendix: Comparison with Current Approach

| Aspect | Current (Section + pages_for_version) | Proposed (NavTree) |
|--------|--------------------------------------|-------------------|
| Template complexity | 161 lines with boilerplate | <60 lines, single call |
| Render performance | O(n) filtering per render | O(1) cache lookup |
| Active trail | URL string comparison in Jinja | Pre-computed `is_in_trail` |
| Version filtering | `pages_for_version()` call in template | Built into tree structure |
| Caching | None | Per-version, thread-safe |
| Testability | Requires template rendering | Unit testable Python |
| Existing infra | Uses Section directly | Wraps Section methods |

### Template Code Comparison

**Current** (docs-nav.html:52-66):
```jinja
{% set current_version_id = current_version.id if (current_version is defined and current_version) else (page.version if (page is defined and page and page.version) else none) %}
{% set version_filter = current_version_id if site.versioning_enabled else none %}
{% set sorted_pages = root_section.pages_for_version(version_filter) %}
{% set sorted_subsections = root_section.subsections_for_version(version_filter) %}
{% set current_url = page.relative_url.rstrip('/') if (page is defined and page and page.relative_url) else '' %}
...
{% set p_is_active = (page is defined and page and current_url == p_url_normalized) %}
```

**Proposed**:
```jinja
{% set nav = get_nav_tree(page) %}
{% for item in nav.root.children %}
  <a href="{{ item.url }}" class="{{ 'active' if item.is_current }}">
    {{ item.title }}
  </a>
{% endfor %}
```
