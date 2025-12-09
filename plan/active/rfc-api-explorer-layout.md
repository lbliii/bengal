# RFC: API Explorer Layout System

**Status**: Implemented  
**Author**: AI Assistant  
**Created**: 2025-12-07  
**Updated**: 2025-12-07  
**Priority**: High (Strategic Differentiator)

---

## Executive Summary

Replace the current markdown-based autodoc output with a **virtual page** architecture that renders directly to HTML during build. This eliminates intermediate markdown files while providing a premium, app-like "API Explorer" layout.

**Key changes:**
1. **No markdown intermediates** - Autodoc generates virtual Page objects, not `.md` files
2. **HTML templates** - Direct Jinja2 HTML templates, not markdown+directives
3. **Card-based layout** - Collapsible, progressive disclosure design
4. **Menu integration** - Virtual sections work with existing navigation

---

## Problem Statement

### Current Architecture Issues

```
Python source → DocElement → Jinja → Markdown files → Build → HTML
                                          ↓
                              content/api/*.md (500+ files)
```

**Problems:**
1. **500+ generated files** cluttering repo/disk
2. **Markdown parsing quirks** limit layout options
3. **Two-step process** (`bengal autodoc` then `bengal build`)
4. **Workarounds needed** for complex layouts (directives, raw HTML)
5. **Cognitive overload** in output (everything expanded, lots of whitespace)

### Current Layout Issues

- Prose-heavy, reads like a document not an app
- Everything expanded by default, no progressive disclosure
- 50+ line methods become 100+ lines of output
- Generic look, resembles typical SSG output

---

## Proposed Solution

### New Architecture

```
Python source → DocElement → Virtual Pages → HTML templates → HTML
                                  ↓
                         No disk files (memory only)
                         Integrated with site.sections
```

**Benefits:**
- **Zero intermediate files** - API docs are virtual pages
- **Full HTML control** - No markdown limitations
- **Single step** - `bengal build` introspects and renders
- **Faster builds** - Skip markdown parsing for API docs
- **Cleaner repo** - No generated content to manage

### API Explorer Design

**Core Principles:**
1. **Cards, not prose** - Each class/function is a collapsible card
2. **Collapsed by default** - Expand to reveal details
3. **Inline metadata** - Badges in headers, not separate lines
4. **Compact tables** - Parameters in tight, scannable format
5. **Zero filler** - No "No description provided"

**Visual Hierarchy:**

```
Layer 1: Card Header (Always Visible)
├── Icon (◆ class, ƒ function, ⚡ async)
├── Name (monospace)
├── Badges (dataclass, async, deprecated)
└── Toggle (▾/▸)

Layer 2: Quick Summary (First Expansion)
├── One-line description
├── Attributes table (compact)
└── Methods list (names only, clickable)

Layer 3: Method Details (Click to Expand)
├── Signature (syntax highlighted)
├── Parameters table
├── Returns (inline)
└── Raises (inline, colored)

Layer 4: Examples (Collapsed)
└── Code block (click to reveal)
```

---

## Technical Specification

### Virtual Page Model

Add virtual page support to the Page model:

```python
# bengal/core/page/__init__.py

@dataclass
class Page:
    # Existing fields...
    core: PageCore
    content: str
    rendered_html: str | None = None
    
    # NEW: Virtual page support
    _virtual: bool = False
    _render_data: dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_virtual(self) -> bool:
        """True if this is a virtual page (no source file)."""
        return self._virtual
    
    @property
    def source_path(self) -> Path | None:
        """Source path (None for virtual pages)."""
        if self._virtual:
            return None
        return Path(self.core.source_path)
    
    @classmethod
    def create_virtual(
        cls,
        url: str,
        title: str,
        template: str,
        render_data: dict[str, Any],
        section_path: str = "",
    ) -> Page:
        """Create a virtual page for API docs."""
        core = PageCore(
            source_path="",  # No source file
            title=title,
            date=None,
            draft=False,
            weight=0,
            slug=url.rstrip("/").split("/")[-1],
            url=url,
            section_path=section_path,
            relative_url=url,
            output_path=f"public{url}index.html",
            template=template,
            content_hash="",
        )
        return cls(
            core=core,
            content="",  # No markdown content
            _virtual=True,
            _render_data=render_data,
        )
```

### Virtual Section Support

Update Section to support virtual (non-disk) sections:

```python
# bengal/core/section.py

@dataclass
class Section:
    name: str
    path: Path | None  # None for virtual sections
    relative_url: str
    pages: list[Page] = field(default_factory=list)
    subsections: list[Section] = field(default_factory=list)
    index_page: Page | None = None
    
    # NEW: Virtual section support
    _virtual: bool = False
    
    @property
    def is_virtual(self) -> bool:
        """True if this is a virtual section (no disk directory)."""
        return self._virtual or self.path is None
    
    @classmethod
    def create_virtual(
        cls,
        name: str,
        relative_url: str,
    ) -> Section:
        """Create a virtual section for API docs."""
        return cls(
            name=name,
            path=None,
            relative_url=relative_url,
            _virtual=True,
        )
```

### Autodoc Orchestrator (Updated)

Rewrite to generate virtual pages:

```python
# bengal/orchestration/autodoc.py

class AutodocOrchestrator:
    """Generate API documentation as virtual pages."""
    
    def __init__(self, site: Site):
        self.site = site
        self.config = site.config.get("autodoc", {})
        self.template_env = self._create_template_env()
    
    def generate(self) -> tuple[list[Page], list[Section]]:
        """
        Generate API docs as virtual pages.
        
        Returns:
            Tuple of (pages, sections) to add to site
        """
        if not self.config.get("enabled", False):
            return [], []
        
        # 1. Discover Python modules
        source_paths = self.config.get("sources", [])
        doc_elements = self._extract_documentation(source_paths)
        
        # 2. Create virtual section hierarchy
        sections = self._create_sections(doc_elements)
        
        # 3. Create virtual pages
        pages = self._create_pages(doc_elements, sections)
        
        # 4. Create index pages for sections
        self._create_index_pages(sections)
        
        logger.info(
            "autodoc_virtual_pages_created",
            pages=len(pages),
            sections=len(sections),
        )
        
        return pages, sections
    
    def _create_sections(self, elements: list[DocElement]) -> dict[str, Section]:
        """Create virtual section hierarchy from doc elements."""
        sections: dict[str, Section] = {}
        
        # Root API section
        api_section = Section.create_virtual(
            name="api",
            relative_url="/api/",
        )
        sections["api"] = api_section
        
        # Create subsections for each package
        for element in elements:
            if element.element_type == "module":
                path_parts = element.qualified_name.split(".")
                current_path = "api"
                parent_section = api_section
                
                for part in path_parts:
                    section_path = f"{current_path}/{part}"
                    if section_path not in sections:
                        subsection = Section.create_virtual(
                            name=part,
                            relative_url=f"/{section_path}/",
                        )
                        sections[section_path] = subsection
                        parent_section.subsections.append(subsection)
                    
                    parent_section = sections[section_path]
                    current_path = section_path
        
        return sections
    
    def _create_pages(
        self, 
        elements: list[DocElement],
        sections: dict[str, Section],
    ) -> list[Page]:
        """Create virtual pages from doc elements."""
        pages = []
        
        for element in elements:
            # Determine section path
            path_parts = element.qualified_name.split(".")
            section_path = "api/" + "/".join(path_parts[:-1]) if len(path_parts) > 1 else "api"
            
            # Create virtual page
            page = Page.create_virtual(
                url=f"/api/{element.qualified_name.replace('.', '/')}/",
                title=element.name,
                template=self._get_template(element),
                render_data={
                    "element": element,
                    "element_type": element.element_type,
                },
                section_path=section_path,
            )
            
            # Add to section
            section = sections.get(section_path)
            if section:
                section.pages.append(page)
            
            pages.append(page)
        
        return pages
    
    def _get_template(self, element: DocElement) -> str:
        """Get HTML template for element type."""
        templates = {
            "module": "api-explorer/module.html",
            "class": "api-explorer/class.html",
            "function": "api-explorer/function.html",
        }
        return templates.get(element.element_type, "api-explorer/default.html")
    
    def _create_index_pages(self, sections: dict[str, Section]) -> None:
        """Create index pages for all sections."""
        for path, section in sections.items():
            if section.index_page is None:
                index_page = Page.create_virtual(
                    url=section.relative_url,
                    title=f"{section.name} API" if section.name != "api" else "API Reference",
                    template="api-explorer/index.html",
                    render_data={
                        "section": section,
                        "subsections": section.subsections,
                        "pages": section.pages,
                    },
                    section_path=path,
                )
                section.index_page = index_page
```

### Content Orchestrator Integration

Update content discovery to include autodoc:

```python
# bengal/orchestration/content.py

class ContentOrchestrator:
    def discover_content(self, ...) -> None:
        # ... existing discovery code ...
        
        # NEW: Generate autodoc virtual pages
        autodoc = AutodocOrchestrator(self.site)
        autodoc_pages, autodoc_sections = autodoc.generate()
        
        # Add to site
        self.site.pages.extend(autodoc_pages)
        self.site.sections.extend(autodoc_sections)
        
        # Rebuild section registry (includes virtual sections)
        self.site.register_sections()
        
        self.logger.debug(
            "autodoc_integrated",
            pages=len(autodoc_pages),
            sections=len(autodoc_sections),
        )
```

### Menu Integration

The existing menu system will work automatically because:

```python
# bengal/orchestration/menu.py

def _find_section_by_name(self, name: str) -> Section | None:
    """Find section by name - works for virtual sections too."""
    for section in self.site.sections:
        if section.name == name:
            return section
        # Also check subsections
        found = self._find_in_subsections(section, name)
        if found:
            return found
    return None
```

**Key insight:** Menu system uses `section.name` and `section.relative_url`, both of which are set on virtual sections.

### Renderer Updates

Update renderer to handle virtual pages:

```python
# bengal/rendering/renderer.py

def render_page(self, page: Page, template_env: Environment) -> str:
    """Render a page to HTML."""
    
    # Get template
    template_name = page.core.template
    template = template_env.get_template(template_name)
    
    # Build context
    if page.is_virtual:
        # Virtual page: use render_data directly
        context = {
            "page": page,
            "site": self.site,
            **page._render_data,  # Element data for API docs
        }
    else:
        # Normal page: parse markdown content
        context = {
            "page": page,
            "site": self.site,
            "content": self._render_markdown(page.content),
        }
    
    return template.render(**context)
```

---

## HTML Templates

### Template Structure

```
bengal/themes/default/templates/api-explorer/
├── base.html           # Base layout with API Explorer chrome
├── index.html          # Section index (list of modules)
├── module.html         # Module page (classes + functions)
├── class.html          # Class detail page
├── function.html       # Function detail page
└── partials/
    ├── card.html       # Reusable card component
    ├── signature.html  # Signature display
    ├── params.html     # Parameter table
    ├── badges.html     # Badge components
    └── method-list.html # Compact method list
```

### Example: Class Template

```html
{# api-explorer/class.html #}
{% extends "api-explorer/base.html" %}

{% block content %}
<div class="api-explorer">
  
  {# Class Card #}
  <details class="api-card api-card--class" open>
    <summary class="api-card__header">
      <span class="api-card__icon">◆</span>
      <code class="api-card__name">{{ element.name }}</code>
      <span class="api-card__badges">
        {% if element.metadata.is_dataclass %}
        <span class="api-badge--compact api-badge--dataclass">dataclass</span>
        {% endif %}
        <span class="api-badge--compact api-badge--class">class</span>
      </span>
      <span class="api-card__toggle">▾</span>
    </summary>
    
    <div class="api-card__body">
      {% if element.description %}
      <p class="api-card__description">{{ element.description | first_sentence }}</p>
      {% endif %}
      
      {# Attributes Section #}
      {% if element.attributes %}
      <section class="api-section">
        <header class="api-section__header">
          <span>Attributes</span>
          <span class="api-section__count">{{ element.attributes | length }}</span>
        </header>
        <table class="api-table">
          <thead>
            <tr><th>Name</th><th>Type</th><th>Description</th></tr>
          </thead>
          <tbody>
            {% for attr in element.attributes %}
            <tr>
              <td class="api-table__name">{{ attr.name }}</td>
              <td class="api-table__type"><code>{{ attr.type_annotation | default('-') }}</code></td>
              <td class="api-table__desc">{{ attr.description | default('-') | truncate(80) }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </section>
      {% endif %}
      
      {# Methods Section #}
      {% if element.methods %}
      <section class="api-section">
        <header class="api-section__header">
          <span>Methods</span>
          <span class="api-section__count">{{ element.methods | length }}</span>
        </header>
        <ul class="api-method-list">
          {% for method in element.methods %}
          <li class="api-method-row" data-target="#method-{{ method.name }}">
            <span class="api-method-row__name">{{ method.name }}</span>
            <span class="api-method-row__signature">{{ method.signature | truncate(40) }}</span>
            <span class="api-method-row__arrow">→</span>
          </li>
          {% endfor %}
        </ul>
      </section>
      {% endif %}
    </div>
  </details>
  
  {# Method Cards (Collapsed by Default) #}
  {% for method in element.methods %}
  {% include "api-explorer/partials/method-card.html" %}
  {% endfor %}
  
</div>
{% endblock %}
```

### Example: Method Card Partial

```html
{# api-explorer/partials/method-card.html #}
<details class="api-card api-card--method api-card--nested" id="method-{{ method.name }}">
  <summary class="api-card__header">
    <span class="api-card__icon">ƒ</span>
    <code class="api-card__name">{{ method.name }}</code>
    <span class="api-card__badges">
      {% if method.metadata.is_async %}
      <span class="api-badge--compact api-badge--async">async</span>
      {% endif %}
      {% if method.metadata.is_property %}
      <span class="api-badge--compact api-badge--property">property</span>
      {% endif %}
    </span>
    <span class="api-card__toggle">▾</span>
  </summary>
  
  <div class="api-card__body">
    {# Signature #}
    <pre class="api-signature">{{ method.signature }}</pre>
    
    {# Description #}
    {% if method.description %}
    <p class="api-card__description">{{ method.description }}</p>
    {% endif %}
    
    {# Parameters #}
    {% if method.parameters | length > 1 %}
    <table class="api-table">
      <thead>
        <tr><th>Param</th><th>Type</th><th>Default</th><th>Description</th></tr>
      </thead>
      <tbody>
        {% for param in method.parameters if param.name != 'self' %}
        <tr>
          <td class="api-table__name">{{ param.name }}</td>
          <td class="api-table__type"><code>{{ param.type_annotation | default('-') }}</code></td>
          <td class="api-table__default">
            {% if param.default_value %}<code>{{ param.default_value }}</code>{% else %}-{% endif %}
          </td>
          <td class="api-table__desc">{{ param.description | default('-') }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% endif %}
    
    {# Returns #}
    {% if method.return_type and method.return_type != 'None' %}
    <div class="api-returns">
      <span class="api-returns__label">Returns</span>
      <code class="api-returns__type">{{ method.return_type }}</code>
      {% if method.return_description %}
      <span class="api-returns__desc">{{ method.return_description }}</span>
      {% endif %}
    </div>
    {% endif %}
    
    {# Raises #}
    {% for exc in method.raises %}
    <div class="api-raises">
      <span class="api-raises__label">Raises</span>
      <code class="api-raises__type">{{ exc.type }}</code>
      <span class="api-raises__desc">{{ exc.description | default('') }}</span>
    </div>
    {% endfor %}
    
    {# Examples #}
    {% if method.examples %}
    <details class="api-example">
      <summary class="api-example__trigger">Example</summary>
      <div class="api-example__code">
        <pre><code class="language-python">{{ method.examples[0] }}</code></pre>
      </div>
    </details>
    {% endif %}
  </div>
</details>
```

---

## CSS Components

CSS already created in `api-explorer.css`. Key components:

| Component | Class | Purpose |
|-----------|-------|---------|
| Card | `.api-card` | Collapsible container |
| Header | `.api-card__header` | Always-visible card header |
| Body | `.api-card__body` | Expandable content area |
| Badge | `.api-badge--compact` | Inline type indicators |
| Table | `.api-table` | Compact parameter tables |
| Signature | `.api-signature` | Syntax-highlighted code |
| Returns | `.api-returns` | Inline return info |
| Raises | `.api-raises` | Exception info (danger color) |
| Example | `.api-example` | Collapsed code block |
| Method List | `.api-method-list` | Compact method index |

---

## Configuration

```toml
# bengal.toml

[autodoc]
enabled = true
sources = ["bengal"]  # Python packages to document

[autodoc.layout]
style = "explorer"    # "explorer" (new) or "classic" (deprecated)
expand_first = true   # Expand first class/function by default
show_inherited = true # Show inherited members
show_source = true    # Show source code links

[autodoc.exclude]
patterns = ["**/test_*", "**/_*"]  # Skip test files and private modules
```

---

## Migration Path

### Phase 1: Parallel Implementation (Week 1)
- [ ] Add `_virtual` field to Page model
- [ ] Add `_virtual` field to Section model  
- [ ] Create `Page.create_virtual()` factory method
- [ ] Create `Section.create_virtual()` factory method
- [ ] Write unit tests for virtual pages

### Phase 2: Autodoc Integration (Week 1-2)
- [ ] Rewrite `AutodocOrchestrator` for virtual pages
- [ ] Update `ContentOrchestrator` to integrate autodoc
- [ ] Verify menu system finds virtual "api" section
- [ ] Test navigation (prev/next) with virtual pages
- [ ] Test breadcrumbs with virtual pages

### Phase 3: HTML Templates (Week 2)
- [ ] Create `api-explorer/base.html`
- [ ] Create `api-explorer/index.html`
- [ ] Create `api-explorer/module.html`
- [ ] Create `api-explorer/class.html`
- [ ] Create `api-explorer/function.html`
- [ ] Create all partials

### Phase 4: CSS & Polish (Week 2-3)
- [ ] Finalize `api-explorer.css` ✅ (done)
- [ ] Add dark mode support
- [ ] Add responsive breakpoints
- [ ] Add print styles
- [ ] Add keyboard navigation (optional)

### Phase 5: Testing & Documentation (Week 3)
- [ ] Test with Bengal's own API
- [ ] Test with external package
- [ ] Performance benchmarks
- [ ] Write user documentation
- [ ] Update CHANGELOG

### Phase 6: Cleanup (Week 3)
- [ ] Remove old markdown templates (optional, keep for fallback)
- [ ] Remove `content/api/` from git
- [ ] Update `.gitignore`
- [ ] Deprecate `bengal autodoc` CLI command (now automatic)

---

## Decisions Made

### Q: Expand first item by default?
**A: Yes.** The first class or function in a module should be expanded so users see content immediately. Subsequent items are collapsed.

### Q: Show inherited members?
**A: Yes, in collapsed section.** Inherited methods appear in a "Inherited Members" collapsible at the bottom of the class card.

### Q: Source links?
**A: In card header badge.** A small "src" badge in the header links to the source file on GitHub.

### Q: Mobile behavior?
**A: Stack cards.** On mobile, cards stack vertically. The collapse/expand behavior remains the same.

### Q: What about existing `content/api/` files?
**A: Delete them.** After migration, the `content/api/` directory should be removed. Virtual pages don't create files.

### Q: What about `bengal autodoc` CLI command?
**A: Deprecate with fallback.** The command will still work but print a deprecation warning. API docs are now generated automatically during build.

### Q: LLM.txt generation?
**A: Works automatically.** The `llm.txt` generator reads from `site.pages`, which includes virtual pages. No changes needed.

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Vertical space reduction | 60-70% | Compare line counts of old vs new HTML |
| Time to find method | < 3 seconds | User testing with task |
| Build time | Same or faster | Benchmark with/without markdown step |
| File count reduction | 100% | Zero files in `content/api/` |
| Menu integration | Works | "Dev > API Reference" appears correctly |
| AI parsing accuracy | 95%+ | LLM.txt extraction test |

---

## Files to Create/Modify

### New Files
```
bengal/themes/default/templates/api-explorer/
├── base.html
├── index.html
├── module.html
├── class.html
├── function.html
└── partials/
    ├── card.html
    ├── signature.html
    ├── params.html
    ├── badges.html
    └── method-list.html
```

### Modified Files
```
bengal/core/page/__init__.py      # Add _virtual support
bengal/core/section.py            # Add _virtual support
bengal/orchestration/autodoc.py   # Rewrite for virtual pages
bengal/orchestration/content.py   # Integrate autodoc
bengal/rendering/renderer.py      # Handle virtual page rendering
```

### Files to Delete (After Migration)
```
content/api/                      # All generated markdown files
bengal/autodoc/templates/python/  # Old markdown templates (optional)
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Menu breaks with virtual sections | High | Test `_find_section_by_name` early in implementation |
| Navigation (prev/next) breaks | Medium | Ensure virtual pages have proper `section_path` |
| Breadcrumbs break | Medium | Virtual pages set `relative_url` correctly |
| TOC generation fails | Low | Virtual pages don't need markdown TOC extraction |
| Cache invalidation issues | Low | Virtual pages have `content_hash=""` (always rebuild) |
| Theme override breaks | Low | Keep template names consistent for swizzling |

---

## Timeline

| Week | Tasks | Deliverable |
|------|-------|-------------|
| 1 | Virtual page model, autodoc rewrite | Working virtual pages |
| 2 | HTML templates, CSS polish | Rendered API Explorer |
| 3 | Testing, docs, cleanup | Production ready |

**Total: 3 weeks**

---

## References

- [Stripe API Docs](https://stripe.com/docs/api) - Information density inspiration
- [Swagger UI](https://petstore.swagger.io/) - Expand/collapse patterns
- [FastAPI Docs](https://fastapi.tiangolo.com/) - Readability inspiration
- [Diataxis Framework](https://diataxis.fr/) - Reference documentation principles

---

## Appendix: Created Files

### Already Created
- `bengal/themes/default/assets/css/components/api-explorer.css` ✅
- `bengal/autodoc/templates/python/partials/class_explorer.md.jinja2` ✅ (prototype, will be replaced)

### Commits
- `autodoc: add css_class: api-content to base template frontmatter`
- `autodoc: fix invalid {div} directive and heading hierarchy; add container directive`
- `autodoc: add API Explorer CSS and prototype template`
- `docs(plan): add RFC for API Explorer layout system`
