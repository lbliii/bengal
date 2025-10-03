# Cascading Frontmatter Implementation Plan

## Overview

Implement Hugo-style cascading frontmatter to allow section-level metadata to automatically cascade down to child pages and subsections.

## Current State Analysis

### How Content Discovery Works
1. **ContentDiscovery walks directories recursively**
   - `_walk_directory()` processes each directory
   - Creates `Section` objects for directories
   - Creates `Page` objects from markdown files
   - Links pages to sections via `section.add_page(page)`

2. **Section Metadata Currently**
   - Sections have a `metadata` dict (currently unused/empty)
   - `_index.md` files become the section's `index_page`
   - Index page metadata NOT copied to section metadata
   - No inheritance mechanism exists

3. **Page Metadata Currently**
   - Pages have their own `metadata` dict from frontmatter
   - Pages have reference to parent section via `_section`
   - No cascade lookup mechanism

### Content Hierarchy Flow
```
Site.discover_content()
  └─> ContentDiscovery.discover()
      └─> _walk_directory(dir, parent_section)
          ├─> _create_page(file) → Page with metadata
          ├─> parent_section.add_page(page)
          └─> Create child sections recursively
              └─> parent_section.add_subsection(section)

Site._setup_page_references()
  └─> Sets _site and _section on all pages
  └─> Perfect place to apply cascades!
```

## Implementation Strategy

### Phase 1: Basic Cascade Support ✅

#### 1.1 Extract Section Metadata from Index Pages
**Location:** `Section.add_page()` in `bengal/core/section.py`

When an `_index.md` is added as index_page, copy its metadata to section:

```python
def add_page(self, page: Page) -> None:
    """Add a page to this section."""
    self.pages.append(page)
    
    # Set as index page if it's named index.md or _index.md
    if page.source_path.stem in ("index", "_index"):
        self.index_page = page
        # NEW: Extract cascade metadata from index page
        if 'cascade' in page.metadata:
            self.metadata['cascade'] = page.metadata['cascade']
```

#### 1.2 Create Cascade Application Method
**Location:** New method in `bengal/core/site.py`

```python
def _apply_cascades(self) -> None:
    """
    Apply cascading metadata from sections to their child pages and subsections.
    
    This implements Hugo-style cascade functionality where section _index.md files
    can define metadata that automatically applies to all descendant pages.
    
    Called after content discovery but before rendering.
    """
    # Process sections in hierarchical order (parents before children)
    for section in self.sections:
        self._apply_section_cascade(section)

def _apply_section_cascade(self, section: Section, parent_cascade: Dict = None) -> None:
    """
    Recursively apply cascade metadata to a section and its descendants.
    
    Args:
        section: Section to process
        parent_cascade: Cascade metadata from parent sections
    """
    # Merge parent cascade with this section's cascade
    accumulated_cascade = {}
    if parent_cascade:
        accumulated_cascade.update(parent_cascade)
    if 'cascade' in section.metadata:
        accumulated_cascade.update(section.metadata['cascade'])
    
    # Apply cascade to all pages in this section
    for page in section.pages:
        if accumulated_cascade:
            # Merge cascade into page metadata (page values take precedence)
            for key, value in accumulated_cascade.items():
                if key not in page.metadata:
                    page.metadata[key] = value
    
    # Recursively apply to subsections
    for subsection in section.subsections:
        self._apply_section_cascade(subsection, accumulated_cascade)
```

#### 1.3 Integrate into Build Process
**Location:** `Site.discover_content()` in `bengal/core/site.py`

```python
def discover_content(self, content_dir: Optional[Path] = None) -> None:
    """Discover all content (pages, sections) in the content directory."""
    if content_dir is None:
        content_dir = self.root_path / "content"
    
    if not content_dir.exists():
        print(f"Warning: Content directory {content_dir} does not exist")
        return
    
    from bengal.discovery.content_discovery import ContentDiscovery
    
    discovery = ContentDiscovery(content_dir)
    self.sections, self.pages = discovery.discover()
    
    # Set up page references for navigation
    self._setup_page_references()
    
    # NEW: Apply cascading frontmatter
    self._apply_cascades()
```

### Phase 2: Advanced Cascade Features (Future)

#### 2.1 Targeted Cascades (Hugo's _target)
Allow conditional cascades based on path patterns:

```yaml
# content/docs/_index.md
---
title: "Documentation"
cascade:
  - _target:
      kind: page
      path: /docs/api/**
    api_version: "2.0"
    type: "api-doc"
  - _target:
      kind: page
      path: /docs/guides/**
    type: "guide"
    sidebar: true
---
```

#### 2.2 Cascade Override Control
Add `cascade_mode` to control merge behavior:

```yaml
---
cascade:
  type: "blog-post"
  author: "Default Author"
cascade_mode: "merge"  # or "replace", "append"
---
```

## Usage Examples

### Example 1: Product Documentation Section

**Structure:**
```
content/
  products/
    _index.md           # Section cascade
    widget-2000.md      # Inherits cascade
    gadget-pro.md       # Inherits cascade
    legacy/
      _index.md         # Can override/extend
      old-product.md
```

**products/_index.md:**
```yaml
---
title: "Products"
cascade:
  type: "product"
  version: "2.0"
  product_line: "current"
  layout: "product-page"
---
```

**Template Access:**
```jinja2
{# In widget-2000.md template #}
{{ page.metadata.type }}          {# "product" (from cascade) #}
{{ page.metadata.version }}        {# "2.0" (from cascade) #}
{{ page.metadata.product_line }}   {# "current" (from cascade) #}

{# Page can override any cascaded value #}
{{ page.metadata.version }}        {# "3.0" if overridden in frontmatter #}
```

### Example 2: Blog with Multiple Authors

**Structure:**
```
content/
  blog/
    _index.md               # Default author
    my-post.md              # Uses default
    alice/
      _index.md             # Override author
      alice-post.md         # Inherits Alice as author
```

**blog/_index.md:**
```yaml
---
title: "Blog"
cascade:
  type: "post"
  author: "Blog Team"
  show_author: true
---
```

**blog/alice/_index.md:**
```yaml
---
title: "Alice's Posts"
cascade:
  author: "Alice Smith"
  author_bio: "Senior Engineer"
  author_avatar: "/images/alice.jpg"
---
```

**Template:**
```jinja2
<article>
  <h1>{{ page.title }}</h1>
  
  {% if page.metadata.show_author %}
    <div class="author">
      {% if page.metadata.author_avatar %}
        <img src="{{ page.metadata.author_avatar }}" alt="{{ page.metadata.author }}">
      {% endif %}
      <span>By {{ page.metadata.author }}</span>
      {% if page.metadata.author_bio %}
        <p>{{ page.metadata.author_bio }}</p>
      {% endif %}
    </div>
  {% endif %}
  
  {{ content }}
</article>
```

### Example 3: API Documentation Versioning

**Structure:**
```
content/
  api/
    _index.md       # Latest version
    v1/
      _index.md     # v1 cascade
      auth.md
      users.md
    v2/
      _index.md     # v2 cascade
      auth.md
      users.md
```

**api/v2/_index.md:**
```yaml
---
title: "API v2 Documentation"
cascade:
  api_version: "2.0"
  api_status: "stable"
  api_base_url: "https://api.example.com/v2"
  deprecated: false
  template: "api-doc"
---
```

**Template with Cascade:**
```jinja2
<div class="api-doc">
  <div class="version-badge" data-status="{{ page.metadata.api_status }}">
    API Version {{ page.metadata.api_version }}
    {% if page.metadata.deprecated %}
      <span class="deprecated">Deprecated</span>
    {% endif %}
  </div>
  
  <code class="endpoint">
    {{ page.metadata.api_base_url }}{{ page.metadata.endpoint }}
  </code>
  
  {{ content }}
</div>
```

## Benefits

1. **DRY Principle** - Define once, apply to many
2. **Consistency** - Ensure all pages in a section have consistent metadata
3. **Maintainability** - Update metadata in one place
4. **Flexibility** - Pages can still override any cascaded value
5. **Hugo Compatibility** - Familiar pattern for Hugo users

## Testing Strategy

### Unit Tests
1. Test cascade application to pages
2. Test cascade accumulation through hierarchy
3. Test page override precedence
4. Test empty/missing cascade handling

### Integration Tests
1. Test multi-level section hierarchies
2. Test cascade + page metadata merging
3. Test template access to cascaded values

### Example Test Cases
```python
def test_basic_cascade():
    """Test cascade applies to child pages."""
    section = Section(metadata={'cascade': {'type': 'doc'}})
    page = Page(metadata={'title': 'Test'})
    # Apply cascade...
    assert page.metadata['type'] == 'doc'
    assert page.metadata['title'] == 'Test'

def test_page_override():
    """Test page values override cascade."""
    section = Section(metadata={'cascade': {'type': 'doc', 'version': '1.0'}})
    page = Page(metadata={'version': '2.0'})
    # Apply cascade...
    assert page.metadata['type'] == 'doc'
    assert page.metadata['version'] == '2.0'  # page wins

def test_nested_cascade():
    """Test cascade accumulates through hierarchy."""
    parent = Section(metadata={'cascade': {'type': 'doc'}})
    child = Section(metadata={'cascade': {'version': '2.0'}})
    page = Page(metadata={})
    # Apply cascade...
    assert page.metadata['type'] == 'doc'      # from parent
    assert page.metadata['version'] == '2.0'   # from child
```

## Files to Modify

1. ✅ `bengal/core/section.py` - Extract cascade from index_page
2. ✅ `bengal/core/site.py` - Add cascade application methods
3. ✅ `tests/unit/test_cascade.py` - NEW: Unit tests
4. ✅ `tests/integration/test_cascade_integration.py` - NEW: Integration tests
5. ✅ `examples/quickstart/content/products/_index.md` - NEW: Example with cascade
6. ✅ `CHANGELOG.md` - Document new feature

## Documentation Updates

1. Add cascade section to template system docs
2. Add cascade examples to quickstart
3. Update frontmatter reference
4. Add cascade to feature comparison (vs Hugo)

## Migration Notes

- **Backward Compatible**: Existing sites work unchanged
- **Opt-in Feature**: Only applies when `cascade:` is in frontmatter
- **No Breaking Changes**: Pages without cascade work exactly as before

## Performance Considerations

- Cascade application happens once after discovery
- No performance impact on rendering
- Minimal memory overhead (just merged dict values)
- No change to build cache logic (cascades resolve before caching)

## Future Enhancements

1. **Cascade Inheritance Modes**
   - `merge` (default): Deep merge dictionaries
   - `replace`: Replace entire values
   - `append`: Append to lists

2. **Conditional Cascades** (Hugo's `_target`)
   - Path-based targeting
   - Kind-based targeting (page vs section)
   - Custom predicate functions

3. **Cascade Debugging**
   - Debug mode to show cascade sources
   - Template function: `{{ page | cascade_source('version') }}`
   - Shows which section provided each cascaded value

## Implementation Timeline

- **Phase 1** (Core Cascade): 2-3 hours
  - Section metadata extraction
  - Cascade application logic
  - Basic tests
  - Documentation

- **Phase 2** (Polish): 1-2 hours
  - Integration tests
  - Example content
  - Edge case handling

- **Phase 3** (Advanced - Optional): Future
  - Targeted cascades
  - Custom merge strategies
  - Debugging tools

## Success Criteria

✅ Section `_index.md` can define `cascade:` metadata  
✅ Child pages automatically inherit cascaded values  
✅ Page frontmatter overrides cascaded values  
✅ Multi-level hierarchies accumulate cascades  
✅ Template access via `page.metadata.property`  
✅ Zero breaking changes to existing sites  
✅ Comprehensive test coverage  
✅ Documentation with examples  

---

**Status**: Ready for Implementation  
**Priority**: High  
**Estimated Effort**: 3-5 hours  
**Dependencies**: None  

