# Menu & TOC Architecture Plan

**Date:** October 3, 2025  
**Status:** Design Phase  
**Priority:** High (Critical for real-world sites)

---

## 🎯 Overview

This document details how navigation menus and tables of contents (TOCs) will be integrated into Bengal's existing architecture, expanding the object model while maintaining the clean, modular design.

---

## 📊 Current State Analysis

### What We Have
- ✅ Clean object model (Site → Sections → Pages)
- ✅ Template system with Jinja2
- ✅ Config system with TOML
- ✅ Parser with TOC extraction capability (unused)
- ✅ Theme with hardcoded menus

### What's Missing
- ❌ No menu configuration system
- ❌ TOC not exposed to templates
- ❌ No hierarchical navigation
- ❌ No active page detection
- ❌ No sidebar/footer menu support

---

## 🏗️ Architecture Integration

### New Components

```
bengal/
  core/
    menu.py          # NEW: MenuItem class, menu building
    site.py          # EXPAND: Build menus, expose via .menu
    section.py       # EXPAND: Auto-generate section menus
    page.py          # EXPAND: Store TOC and menu entries
  config/
    loader.py        # EXPAND: Parse menu configuration
  rendering/
    pipeline.py      # EXPAND: Use parse_with_toc()
    template_engine.py  # EXPAND: Add menu helper functions
```

### Integration Points

```
┌─────────────────────────────────────────────────────┐
│                   CONFIG (TOML)                      │
│  [menu.main]                                         │
│  [menu.footer]                                       │
└─────────────────┬───────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────────┐
│              CONFIG LOADER (EXPAND)                  │
│  Parse menu definitions                              │
│  → List[MenuItemConfig]                              │
└─────────────────┬───────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────────┐
│                SITE OBJECT (EXPAND)                  │
│  .menu: Dict[str, List[MenuItem]]                    │
│  .build_menus() → Merge config + frontmatter         │
└─────────────────┬───────────────────────────────────┘
                  │
                  ├──→ RENDERING PIPELINE (EXPAND)
                  │    - Use parse_with_toc()
                  │    - Store page.toc
                  │
                  └──→ TEMPLATE ENGINE (EXPAND)
                       - Expose site.menu
                       - Add is_active() helper
                       - Current page context
```

---

## 📦 New Data Structures

### MenuItem Class

**Location:** `bengal/core/menu.py`

```python
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass
class MenuItem:
    """
    Represents a single menu item with optional hierarchy.
    
    Can be created from:
    1. Config file (explicit definition)
    2. Page frontmatter (page registers itself in menu)
    3. Section structure (auto-generated)
    """
    name: str
    url: str
    weight: int = 0
    parent: Optional[str] = None
    identifier: Optional[str] = None  # For referencing as parent
    children: List['MenuItem'] = field(default_factory=list)
    
    # Runtime state (set during rendering)
    active: bool = False
    active_trail: bool = False  # Parent of active item
    
    def __post_init__(self):
        """Set identifier from name if not provided."""
        if self.identifier is None:
            self.identifier = self.name.lower().replace(' ', '-')
    
    def add_child(self, child: 'MenuItem') -> None:
        """Add a child menu item and sort by weight."""
        self.children.append(child)
        self.children.sort(key=lambda x: x.weight)
    
    def mark_active(self, current_url: str) -> bool:
        """
        Mark this item as active if URL matches.
        Returns True if this or any child is active.
        """
        if self.url == current_url:
            self.active = True
            return True
        
        # Check children
        for child in self.children:
            if child.mark_active(current_url):
                self.active_trail = True
                return True
        
        return False
    
    def to_dict(self) -> dict:
        """Convert to dict for template access."""
        return {
            'name': self.name,
            'url': self.url,
            'active': self.active,
            'active_trail': self.active_trail,
            'children': [child.to_dict() for child in self.children]
        }


class MenuBuilder:
    """
    Builds hierarchical menu structures from various sources.
    """
    
    def __init__(self):
        self.items: List[MenuItem] = []
    
    def add_from_config(self, menu_config: List[dict]) -> None:
        """Add menu items from config."""
        for item_config in menu_config:
            item = MenuItem(
                name=item_config['name'],
                url=item_config['url'],
                weight=item_config.get('weight', 0),
                parent=item_config.get('parent'),
                identifier=item_config.get('identifier')
            )
            self.items.append(item)
    
    def add_from_page(self, page, menu_name: str, menu_config: dict) -> None:
        """Add a page to menu based on frontmatter."""
        item = MenuItem(
            name=menu_config.get('name', page.title),
            url=page.url,
            weight=menu_config.get('weight', 0),
            parent=menu_config.get('parent'),
            identifier=menu_config.get('identifier')
        )
        self.items.append(item)
    
    def build_hierarchy(self) -> List[MenuItem]:
        """
        Build hierarchical tree from flat list.
        Returns list of root items (no parent).
        """
        # Create lookup by identifier
        by_id = {item.identifier: item for item in self.items}
        
        # Build tree
        roots = []
        for item in self.items:
            if item.parent:
                parent = by_id.get(item.parent)
                if parent:
                    parent.add_child(item)
                else:
                    # Parent not found, treat as root
                    roots.append(item)
            else:
                roots.append(item)
        
        # Sort roots by weight
        roots.sort(key=lambda x: x.weight)
        
        return roots
    
    def mark_active_items(self, current_url: str, menu_items: List[MenuItem]) -> None:
        """Mark active items in menu tree."""
        for item in menu_items:
            item.mark_active(current_url)
```

---

## 🔧 Site Object Expansion

**Location:** `bengal/core/site.py`

### New Attributes

```python
class Site:
    def __init__(self, config: Dict[str, Any], ...):
        # Existing attributes...
        self.pages: List[Page] = []
        self.sections: List[Section] = []
        
        # NEW: Menu system
        self.menu: Dict[str, List[MenuItem]] = {}
        self.menu_builders: Dict[str, MenuBuilder] = {}
```

### New Methods

```python
def build_menus(self) -> None:
    """
    Build all menus from config and page frontmatter.
    Called during site.build() after content discovery.
    """
    # Get menu definitions from config
    menu_config = self.config.get('menu', {})
    
    for menu_name, items in menu_config.items():
        builder = MenuBuilder()
        
        # Add config-defined items
        if isinstance(items, list):
            builder.add_from_config(items)
        
        # Add items from page frontmatter
        for page in self.pages:
            page_menu = page.metadata.get('menu', {})
            if menu_name in page_menu:
                builder.add_from_page(page, menu_name, page_menu[menu_name])
        
        # Build hierarchy
        self.menu[menu_name] = builder.build_hierarchy()
        self.menu_builders[menu_name] = builder
    
    if self.verbose:
        for menu_name, items in self.menu.items():
            print(f"  ✓ Built menu '{menu_name}': {len(items)} items")

def mark_active_menu_items(self, current_page: Page) -> None:
    """
    Mark active menu items for the current page being rendered.
    Called during rendering for each page.
    """
    current_url = current_page.url
    for menu_name, builder in self.menu_builders.items():
        builder.mark_active_items(current_url, self.menu[menu_name])
```

### Integration into build()

```python
def build(self, parallel: bool = True, incremental: bool = False) -> None:
    """Build the site."""
    # ... existing discovery code ...
    
    # NEW: Build menus after content discovery
    self.build_menus()
    
    # ... existing rendering code ...
```

---

## 📄 Page Object Expansion

**Location:** `bengal/core/page.py`

### New Attributes

```python
class Page:
    def __init__(self, source_path: Path, ...):
        # Existing attributes...
        self.parsed_ast: Optional[str] = None
        
        # NEW: TOC attributes
        self.toc: Optional[str] = None  # HTML TOC
        self.toc_items: List[dict] = []  # Structured TOC data
        
        # NEW: Menu participation
        self.menu_entries: Dict[str, dict] = {}  # Which menus this page is in
```

### Extract Menu Data from Frontmatter

```python
def _parse_frontmatter(self) -> None:
    """Parse frontmatter (existing method, EXPAND)."""
    # ... existing parsing ...
    
    # NEW: Extract menu entries
    if 'menu' in self.metadata:
        self.menu_entries = self.metadata['menu']
```

---

## 🎨 Section Object Expansion

**Location:** `bengal/core/section.py`

### New Attributes & Methods

```python
class Section:
    def __init__(self, path: Path, ...):
        # Existing attributes...
        self.subsections: List['Section'] = []
        self.pages: List[Page] = []
        
        # NEW: Auto-generated menu
        self._menu: Optional[List[MenuItem]] = None
    
    @property
    def menu(self) -> List[MenuItem]:
        """
        Auto-generate navigation menu from section structure.
        Cached after first generation.
        """
        if self._menu is None:
            self._menu = self._generate_menu()
        return self._menu
    
    def _generate_menu(self) -> List[MenuItem]:
        """Generate menu from subsections and pages."""
        items = []
        
        # Add index page if exists
        if self.index_page:
            items.append(MenuItem(
                name="Overview",
                url=self.index_page.url,
                weight=0
            ))
        
        # Add subsections
        for i, subsection in enumerate(self.subsections, start=1):
            item = MenuItem(
                name=subsection.title,
                url=subsection.url,
                weight=i * 10
            )
            # Optionally add subsection pages as children
            for page in subsection.pages:
                item.add_child(MenuItem(
                    name=page.title,
                    url=page.url,
                    weight=0
                ))
            items.append(item)
        
        # Add standalone pages
        for page in self.pages:
            if page != self.index_page:
                items.append(MenuItem(
                    name=page.title,
                    url=page.url,
                    weight=100  # After sections
                ))
        
        return sorted(items, key=lambda x: x.weight)
```

---

## 🔄 Rendering Pipeline Updates

**Location:** `bengal/rendering/pipeline.py`

### Update process_page()

```python
def process_page(self, page: Page) -> None:
    """Process a single page through the entire pipeline."""
    # ... existing tracking code ...
    
    # Stage 1: Parse content WITH TOC
    parsed_content, toc = self.parser.parse_with_toc(page.content, page.metadata)
    page.parsed_ast = parsed_content
    page.toc = toc  # NEW: Store TOC
    page.toc_items = self._extract_toc_structure(toc)  # NEW: Parse TOC HTML
    
    # ... rest of existing code ...

def _extract_toc_structure(self, toc_html: str) -> List[dict]:
    """
    Parse TOC HTML into structured data.
    Useful for custom TOC rendering in templates.
    """
    if not toc_html:
        return []
    
    # Parse HTML to extract headings
    from html.parser import HTMLParser
    
    class TOCParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.items = []
            self.current_item = None
        
        def handle_starttag(self, tag, attrs):
            if tag == 'a':
                attrs_dict = dict(attrs)
                self.current_item = {
                    'id': attrs_dict.get('href', '').lstrip('#'),
                    'title': ''
                }
        
        def handle_data(self, data):
            if self.current_item is not None:
                self.current_item['title'] = data.strip()
        
        def handle_endtag(self, tag):
            if tag == 'a' and self.current_item:
                self.items.append(self.current_item)
                self.current_item = None
    
    parser = TOCParser()
    parser.feed(toc_html)
    return parser.items
```

---

## 🎨 Template Engine Updates

**Location:** `bengal/rendering/template_engine.py`

### Add Global Functions

```python
def __init__(self, site: Any) -> None:
    """Initialize template engine."""
    # ... existing code ...
    
    # NEW: Add menu helper functions
    self.env.globals['get_menu'] = self._get_menu
    self.env.globals['is_active'] = self._is_active
    self.env.globals['has_children'] = self._has_children

def _get_menu(self, menu_name: str = 'main') -> List[dict]:
    """
    Get menu items as dicts for template access.
    """
    menu = self.site.menu.get(menu_name, [])
    return [item.to_dict() for item in menu]

def _is_active(self, item: dict, current_url: str) -> bool:
    """Check if menu item is active."""
    return item.get('active', False) or item.get('active_trail', False)

def _has_children(self, item: dict) -> bool:
    """Check if menu item has children."""
    return len(item.get('children', [])) > 0
```

### Update Renderer Context

**Location:** `bengal/rendering/renderer.py`

```python
def render_page(self, page: Page, content: Optional[str] = None) -> str:
    """Render a complete page with template."""
    # ... existing code ...
    
    # NEW: Mark active menu items for this page
    self.template_engine.site.mark_active_menu_items(page)
    
    # Build context
    context = {
        'page': page,
        'content': content,
        'title': page.title,
        'metadata': page.metadata,
        'toc': page.toc,  # NEW: TOC HTML
        'toc_items': page.toc_items,  # NEW: Structured TOC
    }
    
    # ... rest of existing code ...
```

---

## ⚙️ Config Format

**Location:** User's `bengal.toml`

### Menu Configuration

```toml
[site]
title = "My Site"
baseurl = "https://example.com"

# Define main navigation menu
[[menu.main]]
name = "Home"
url = "/"
weight = 1

[[menu.main]]
name = "Blog"
url = "/posts/"
weight = 2

[[menu.main]]
name = "Docs"
url = "/docs/"
weight = 3
identifier = "docs"  # For nesting

[[menu.main]]
name = "Getting Started"
url = "/docs/getting-started/"
parent = "docs"
weight = 1

[[menu.main]]
name = "API Reference"
url = "/docs/api/"
parent = "docs"
weight = 2

# Footer menu
[[menu.footer]]
name = "About"
url = "/about/"

[[menu.footer]]
name = "Contact"
url = "/contact/"

[[menu.footer]]
name = "RSS"
url = "/rss.xml"

# Optional: TOC settings
[toc]
enabled = true
min_level = 2
max_level = 4
```

### Page Frontmatter

```yaml
---
title: "Getting Started"
date: 2025-01-15

# Add this page to menus
menu:
  main:
    weight: 10
    parent: docs
    name: "Quick Start"  # Override title
  sidebar:
    weight: 1

# TOC control
toc:
  enabled: true  # Override global setting
  max_depth: 3
---

Your content here...
```

---

## 🎨 Template Usage

### Base Template with Menu

**Location:** `bengal/themes/default/templates/base.html`

```html
<header role="banner">
    <nav role="navigation" aria-label="Main navigation">
        <div class="container">
            <a href="/" class="logo">{{ site.config.title }}</a>
            
            <div class="nav-main hidden-mobile">
                <ul>
                    {% for item in get_menu('main') %}
                        <li class="{{ 'active' if item.active else '' }} {{ 'active-trail' if item.active_trail else '' }}">
                            <a href="{{ item.url }}">{{ item.name }}</a>
                            
                            {% if item.children %}
                                <ul class="submenu">
                                    {% for child in item.children %}
                                        <li class="{{ 'active' if child.active else '' }}">
                                            <a href="{{ child.url }}">{{ child.name }}</a>
                                        </li>
                                    {% endfor %}
                                </ul>
                            {% endif %}
                        </li>
                    {% endfor %}
                </ul>
                
                <button class="theme-toggle" aria-label="Toggle dark mode">
                    <!-- existing theme toggle -->
                </button>
            </div>
        </div>
    </nav>
</header>
```

### Page Template with TOC

**Location:** `bengal/themes/default/templates/page.html`

```html
{% extends "base.html" %}

{% block content %}
<article class="page">
    {% include 'partials/breadcrumbs.html' %}
    
    <div class="page-layout">
        <!-- Main content -->
        <div class="page-content">
            <h1>{{ page.title }}</h1>
            
            {% if page.metadata.date %}
                <time datetime="{{ page.metadata.date }}">{{ page.metadata.date }}</time>
            {% endif %}
            
            {{ content|safe }}
        </div>
        
        <!-- Sidebar with TOC -->
        {% if page.toc %}
        <aside class="page-sidebar">
            <nav class="toc" aria-label="Table of contents">
                <h2>On This Page</h2>
                {{ page.toc|safe }}
            </nav>
        </aside>
        {% endif %}
    </div>
</article>
{% endblock %}
```

### Section Sidebar Menu

```html
{# In docs section template #}
<aside class="docs-sidebar">
    <nav aria-label="Documentation navigation">
        <ul>
            {% for item in section.menu %}
                <li class="{{ 'active' if item.active else '' }}">
                    <a href="{{ item.url }}">{{ item.name }}</a>
                    
                    {% if item.children %}
                        <ul>
                            {% for child in item.children %}
                                <li class="{{ 'active' if child.active else '' }}">
                                    <a href="{{ child.url }}">{{ child.name }}</a>
                                </li>
                            {% endfor %}
                        </ul>
                    {% endif %}
                </li>
            {% endfor %}
        </ul>
    </nav>
</aside>
```

---

## 📊 Data Flow Summary

```
┌──────────────────────────────────────────────────────────┐
│ 1. CONFIG LOADING                                         │
│    bengal.toml → Config.menu → MenuItemConfig[]          │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│ 2. CONTENT DISCOVERY                                      │
│    Discover pages → Parse frontmatter → Page.menu_entries│
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│ 3. MENU BUILDING                                          │
│    MenuBuilder.add_from_config(config)                    │
│    MenuBuilder.add_from_page(page.menu_entries)           │
│    MenuBuilder.build_hierarchy() → Site.menu              │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│ 4. PAGE PARSING                                           │
│    Parser.parse_with_toc() → Page.toc, Page.toc_items    │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│ 5. RENDERING                                              │
│    For each page:                                         │
│      Site.mark_active_menu_items(page)                    │
│      Render with context(page, toc, site.menu)            │
└───────────────────────────────────────────────────────────┘
```

---

## 🎯 Implementation Plan

### Phase 1: Page TOC (2 hours) ⭐ QUICK WIN

**Files to modify:**
1. `bengal/rendering/pipeline.py`
   - Change `parser.parse()` to `parser.parse_with_toc()`
   - Store TOC in page
   - Extract structured TOC data

2. `bengal/rendering/renderer.py`
   - Add TOC to template context

3. `bengal/themes/default/templates/page.html`
   - Add TOC sidebar
   - Update layout for two-column design

4. `bengal/themes/default/assets/css/layouts/page.css`
   - Style TOC sidebar
   - Make responsive

**Deliverables:**
- ✅ Page TOC displayed on all content pages
- ✅ JavaScript highlighting already works
- ✅ Responsive design

**Testing:**
- View example quickstart pages
- Verify TOC appears and highlights

---

### Phase 2: Config-Driven Menus (4 hours)

**Files to create:**
1. `bengal/core/menu.py`
   - MenuItem class
   - MenuBuilder class

**Files to modify:**
2. `bengal/config/loader.py`
   - Parse `[menu.*]` sections from TOML

3. `bengal/core/site.py`
   - Add `menu` and `menu_builders` attributes
   - Add `build_menus()` method
   - Add `mark_active_menu_items()` method
   - Call `build_menus()` in `build()`

4. `bengal/rendering/template_engine.py`
   - Add `get_menu()` global function
   - Add menu helper functions

5. `bengal/rendering/renderer.py`
   - Call `mark_active_menu_items()` before rendering

6. `bengal/themes/default/templates/base.html`
   - Replace hardcoded menu with `get_menu('main')`
   - Add active state classes

**Deliverables:**
- ✅ Menus configurable in bengal.toml
- ✅ Hierarchical menu support (parent/child)
- ✅ Active page detection
- ✅ Multiple menu support (main, footer, etc.)

**Testing:**
- Add menu config to example site
- Verify hierarchy and active states
- Test mobile menu

---

### Phase 3: Page Menu Frontmatter (2 hours)

**Files to modify:**
1. `bengal/core/page.py`
   - Parse `menu` from frontmatter
   - Store in `menu_entries`

2. `bengal/core/site.py`
   - Update `build_menus()` to include page entries

**Deliverables:**
- ✅ Pages can add themselves to menus
- ✅ Override display name
- ✅ Set custom weights

**Testing:**
- Add menu frontmatter to test pages
- Verify integration with config menus

---

### Phase 4: Auto Section Menus (3 hours)

**Files to modify:**
1. `bengal/core/section.py`
   - Add `menu` property
   - Add `_generate_menu()` method

2. Create section sidebar partial
   - `bengal/themes/default/templates/partials/section-menu.html`

3. Update docs template to use section menu

**Deliverables:**
- ✅ Automatic sidebar navigation for sections
- ✅ Hierarchical display
- ✅ Active page highlighting

**Testing:**
- Test with multi-level sections
- Verify active state propagation

---

### Phase 5: Documentation & Examples (2 hours)

**Files to create/modify:**
1. Add menu examples to quickstart
2. Update ARCHITECTURE.md
3. Add menu/TOC guide to docs
4. Add screenshots to README

**Deliverables:**
- ✅ Complete documentation
- ✅ Working examples
- ✅ Migration guide

---

## 🎯 Success Criteria

### Functional
- ✅ TOC displayed on all content pages
- ✅ Menus configurable via TOML
- ✅ Pages can self-register in menus
- ✅ Hierarchical menus work correctly
- ✅ Active states highlight correctly
- ✅ Section menus auto-generate

### Non-Functional
- ✅ Backward compatible (sites without menus still work)
- ✅ Performance: < 1ms overhead per page
- ✅ Maintains clean architecture
- ✅ Well documented
- ✅ Tested (unit + integration)

---

## 🚀 Timeline

**Total Effort:** ~13 hours

- **Week 1, Day 1-2:** Phase 1 (TOC) + Phase 2 (Config menus)
- **Week 1, Day 3:** Phase 3 (Frontmatter) + Phase 4 (Section menus)
- **Week 1, Day 4:** Phase 5 (Documentation)
- **Week 1, Day 5:** Testing, polish, examples

---

## 🎨 Architecture Principles Maintained

### ✅ No God Objects
- MenuItem is self-contained
- MenuBuilder has single responsibility
- Site orchestrates, doesn't do everything

### ✅ Clean Dependencies
- Menu system is optional
- Templates work with or without menus
- Backward compatible

### ✅ Performance
- Menus built once during discovery
- Active state marked once per render
- No template-time computation

### ✅ Extensibility
- Easy to add new menu types
- Custom menu builders possible
- Plugin hooks available

---

## 🤔 Open Questions

### 1. Menu Caching?
Currently menus are built once per build. With incremental builds, should we cache menu state?

**Answer:** Not initially. Menu building is fast (<1ms). Can optimize later if needed.

### 2. Breadcrumb Integration?
Should breadcrumbs use menu data or stay auto-generated from URL?

**Answer:** Keep auto-generated by default, but allow override via menu data if available.

### 3. Mobile Menu?
How should nested menus behave on mobile?

**Answer:** Accordion-style expansion, maintain active trail highlighting.

### 4. TOC Depth Control?
Should TOC depth be configurable per-page?

**Answer:** Yes, via frontmatter `toc.max_depth` override.

---

## 📚 References

### SSG Implementations Studied
- **Hugo:** Config-driven with weights and identifiers
- **Jekyll:** Hybrid config + frontmatter filtering
- **11ty:** Plugin-based with flexible frontmatter
- **Astro:** Component-based with data files

### Bengal Design Choices
- Hybrid approach: Config (global) + Frontmatter (page-specific)
- Python-native: No plugins needed for core functionality
- Template-friendly: Simple Jinja2 access patterns
- Performance-first: Built once, cached

---

## ✅ Next Steps

1. **Review this architecture** - Get feedback on approach
2. **Start Phase 1** - Quick TOC win (2 hours)
3. **Implement Phase 2** - Core menu system (4 hours)
4. **Test with real content** - Use Bengal docs as dogfooding
5. **Iterate based on usage** - Refine API based on experience

---

*This architecture maintains Bengal's clean, modular design while adding essential navigation capabilities. Each component has a single responsibility, and the system remains optional and backward compatible.*

