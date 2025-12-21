# RFC: Navigation Tree Architecture

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-20  
**Scope**: Core architecture for version-aware navigation

## Executive Summary

Bengal's current navigation relies on `Section` objects which represent **physical** file structure. For versioned documentation, this creates a mismatch: content in `_versions/v1/docs/` should logically appear as `/docs/` in navigation.

This RFC proposes a **NavTree** abstraction that represents the **logical** navigation structure, computed from physical structure but optimized for user-facing navigation.

## Problem Statement

### Current Issues

1. **Physical vs Logical Mismatch**: `Section.root` returns `_versions` for v1 pages, not `docs`
2. **Template Complexity**: Templates must filter by version at multiple levels
3. **Performance**: Version filtering happens repeatedly during rendering
4. **Maintenance**: Version logic scattered across Section, templates, and discovery

### What Best SSGs Do

| SSG | Approach |
|-----|----------|
| **Docusaurus** | Dedicated sidebar config per version, sidebar is first-class |
| **VuePress** | Sidebar config in `.vuepress/config.js`, version-aware |
| **MkDocs** | `nav:` config in `mkdocs.yml`, mike plugin for versioning |
| **Sphinx** | `toctree` directive, separate builds per version |

**Common pattern**: Navigation is a **computed, cached structure** separate from content hierarchy.

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

```python
# bengal/core/nav_tree.py

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
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
    Cache for NavTree instances per version.

    NavTrees are expensive to build (traverse all sections/pages)
    but cheap to query. We build once per version per build.

    Cache is invalidated on:
    - Full rebuild
    - Content changes that affect navigation
    """
    _trees: dict[str | None, NavTree] = {}
    _site: Site | None = None

    @classmethod
    def get(cls, site: Site, version_id: str | None = None) -> NavTree:
        """Get or build NavTree for a version."""
        # Invalidate if site changed
        if cls._site is not site:
            cls._trees.clear()
            cls._site = site

        if version_id not in cls._trees:
            cls._trees[version_id] = NavTree.build(site, version_id)

        return cls._trees[version_id]

    @classmethod
    def invalidate(cls, version_id: str | None = None) -> None:
        """Invalidate cache (on content changes)."""
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

### Phase 1: Add NavTree (Non-Breaking)

1. Implement `NavNode`, `NavTree`, `NavTreeCache`
2. Add `get_nav_tree()` template function
3. Existing templates continue to work

### Phase 2: Simplify Default Theme

1. Update `docs-nav.html` to use `get_nav_tree()`
2. Remove complex Jinja logic
3. Improve UX with proper active trail

### Phase 3: Deprecate Direct Section Access

1. Add deprecation warnings for `section.pages_for_version()`
2. Update documentation
3. Remove in next major version

## Alternatives Considered

### 1. Virtual Sections

Create virtual `Section` objects for versioned content that map to logical paths.

**Rejected because**:
- Conflates physical and logical concerns
- Section already has too many responsibilities
- Would complicate incremental builds

### 2. Template-Side Transformation

Keep current approach, let templates transform sections to logical structure.

**Rejected because**:
- Complex, repeated logic in templates
- Poor performance (transforms on every render)
- Hard to maintain

### 3. Config-Based Navigation (like MkDocs)

Define navigation explicitly in config file.

**Rejected because**:
- Loses auto-discovery (Bengal's strength)
- Manual maintenance burden
- Could be added later as optional enhancement

## Success Criteria

1. **Template Simplicity**: `docs-nav.html` < 50 lines (currently 140+)
2. **Performance**: < 1ms overhead per page render
3. **Correctness**: Versioned nav nests correctly
4. **Maintainability**: Single source of truth for nav logic

## Open Questions

1. Should NavTree support custom nav ordering beyond weight?
2. Should NavTree include page content snippets (for search)?
3. How does NavTree interact with menu system?

## Related Work

- [Docusaurus Sidebar](https://docusaurus.io/docs/sidebar)
- [VuePress Sidebar](https://vuepress.vuejs.org/theme/default-theme-config.html#sidebar)
- [Sphinx toctree](https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-toctree)

## Appendix: Comparison with Current Approach

| Aspect | Current (Section-based) | Proposed (NavTree) |
|--------|------------------------|-------------------|
| Template complexity | High (version filtering, recursive includes) | Low (single call, macro) |
| Performance | O(n) per render (filtering) | O(1) lookup + O(depth) trail |
| Version awareness | Bolted on | Native |
| Caching | None | Per-version cache |
| Active trail | Template logic | Built-in |
| Testability | Hard (requires full site) | Easy (unit testable) |
