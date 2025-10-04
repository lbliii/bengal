# Section/Page Architecture - Long-Term Analysis

**Date:** October 4, 2025  
**Context:** Analysis of section index generation brittleness and architectural redesign

---

## 🏗️ Current Architecture

### Orchestrator Pattern (Good)

Bengal uses a **Orchestrator Pattern** with clear separation:

```
BuildOrchestrator
    ├── ContentOrchestrator      (discovery)
    ├── TaxonomyOrchestrator     (tags, archives)
    ├── MenuOrchestrator         (navigation)
    ├── RenderOrchestrator       (page rendering)
    ├── AssetOrchestrator        (asset processing)
    ├── PostprocessOrchestrator  (sitemap, RSS)
    └── IncrementalOrchestrator  (caching)
```

**Strengths:**
- ✅ Single responsibility per orchestrator
- ✅ Clear delegation model
- ✅ Easy to understand build pipeline
- ✅ Good for testing (mock orchestrators)
- ✅ Avoids "God object" anti-pattern

### Current Data Flow

```
1. ContentOrchestrator.discover()
   ├─ ContentDiscovery walks content/
   ├─ Creates Section and Page objects
   ├─ Sections have optional index_page
   └─ Pages added to sections

2. TaxonomyOrchestrator.collect_and_generate()
   ├─ Collect tags/categories
   ├─ Generate tag pages
   └─ Generate section archive pages ← PROBLEM HERE

3. RenderOrchestrator.process()
   └─ Render all pages (including archives)
```

---

## 🐛 Architectural Problems

### Problem 1: **Semantic Misplacement**

**Archive pages are NOT taxonomies!**

Current:
```python
class TaxonomyOrchestrator:
    """Handles taxonomies and dynamic page generation."""
    
    def generate_dynamic_pages(self):
        # Generate section archive pages
        for section in self.site.sections:
            if section.pages:  # ← Wrong!
                archive_pages = self._create_archive_pages(section)
```

**Why this is wrong:**
- Tags are **cross-cutting concerns** (cut across sections)
- Archives are **structural** (part of section hierarchy)
- Mixing these creates conceptual confusion
- Archives shouldn't be in same bucket as taxonomies

### Problem 2: **Implicit Contracts**

**No explicit contract for section validity:**

```python
class Section:
    """Represents a folder or logical grouping of pages."""
    
    # No validation that section is navigable!
    # No invariant about index pages!
    # No guarantee section.url will work!
```

**Current behavior is implicit:**
- "Sections maybe have index pages"
- "Archives maybe get generated"
- "URLs maybe work"

**Should be explicit:**
- "Every section MUST have a navigable index"
- "Index is either explicit (_index.md) or auto-generated"
- "section.url ALWAYS resolves to valid HTML"

### Problem 3: **Discovery vs Rendering Gap**

**Two-phase system creates a gap:**

```
Phase 1: Discovery (ContentOrchestrator)
  └─ Creates Sections (may not have index_page)

--- GAP: Sections exist but aren't complete ---

Phase 2: Dynamic Generation (TaxonomyOrchestrator)
  └─ Maybe creates archives (if section.pages is truthy)

--- GAP: Some sections still incomplete ---

Phase 3: Rendering (RenderOrchestrator)
  └─ Renders pages (including archives that exist)
```

**The gap means:**
- Sections can exist in incomplete state
- No validation between phases
- Silent failures possible
- URL generation fragile

### Problem 4: **No Section Lifecycle**

**Sections don't have clear state transitions:**

```python
# Created (incomplete)
section = Section(name="docs", path=Path("content/docs"))

# Populated (still incomplete)
section.add_page(kitchen_sink_page)

# ??? Should have index now but doesn't ???

# Rendered (too late to fix)
render(section.index_page)  # Might be None!
```

**Should have explicit lifecycle:**
1. Created (initial state)
2. Populated (pages added)
3. Validated (ensured complete)
4. Renderable (ready for output)

### Problem 5: **Wrong Abstraction Layer**

**Archive generation is procedural, not object-oriented:**

```python
# Current (procedural)
def _create_archive_pages(section: Section) -> List[Page]:
    """Generate archive pages externally."""
    # Logic lives outside Section
    # Section is passive data structure
    pass

# Better (OO)
class Section:
    def ensure_index_page(self) -> Page:
        """Ensure section has valid index page."""
        if self.index_page:
            return self.index_page
        return self._generate_archive_page()
```

---

## 🎯 Architectural Principles for Long-Term Fix

### Principle 1: **Make Invariants Explicit**

**Every section must be navigable:**

```python
class Section:
    """
    Represents a navigable section of the site.
    
    INVARIANTS:
    1. Every section (except root) must have an index page
    2. Index page is either explicit (_index.md) or auto-generated
    3. section.url must resolve to a valid HTML file
    4. Section cannot exist in invalid state
    
    These invariants are enforced by the lifecycle system.
    """
    
    def validate(self) -> List[str]:
        """Validate section invariants."""
        errors = []
        
        if self.name != 'root' and not self.has_index():
            errors.append(f"Section '{self.name}' has no index page")
        
        return errors
    
    def has_index(self) -> bool:
        """Check if section has a valid index."""
        return self.index_page is not None
```

### Principle 2: **Objects Manage Their Own Completeness**

**Sections should ensure they're valid:**

```python
class Section:
    """Section that ensures its own validity."""
    
    def ensure_complete(self, site: 'Site') -> None:
        """
        Ensure section is complete and ready for rendering.
        
        Creates auto-generated index if needed.
        """
        if self.name == 'root':
            return
        
        if not self.index_page:
            # Auto-generate archive page
            self.index_page = self._create_archive_index(site)
    
    def _create_archive_index(self, site: 'Site') -> Page:
        """Create auto-generated archive index."""
        # Logic lives with the object
        pass
```

### Principle 3: **Fail Fast with Validation**

**Validate between phases:**

```python
class BuildOrchestrator:
    def build(self):
        # Phase 1: Discovery
        self.content.discover()
        
        # Phase 2: Complete sections
        self._ensure_sections_complete()
        
        # Phase 3: Validate
        errors = self._validate_structure()
        if errors and self.site.config.get('strict_mode'):
            raise BuildValidationError(errors)
        
        # Phase 4: Continue with render...
```

### Principle 4: **Separate Structural from Cross-Cutting**

**Don't mix sections and taxonomies:**

```python
# Structural (hierarchy-based)
class SectionOrchestrator:
    """Handles section structure and navigation."""
    
    def complete_sections(self):
        """Ensure all sections have index pages."""
        for section in self.site.sections:
            section.ensure_complete(self.site)

# Cross-cutting (tag-based)
class TaxonomyOrchestrator:
    """Handles tags, categories, and taxonomy pages."""
    
    def generate_taxonomy_pages(self):
        """Generate tag and category index pages."""
        # Only taxonomies, no structural stuff
```

### Principle 5: **Explicit Lifecycle with State**

**Sections have explicit states:**

```python
from enum import Enum, auto

class SectionState(Enum):
    CREATED = auto()      # Just created
    POPULATED = auto()    # Pages added
    COMPLETED = auto()    # Index ensured
    VALIDATED = auto()    # Validation passed
    RENDERED = auto()     # Output generated

class Section:
    def __init__(self, ...):
        self._state = SectionState.CREATED
    
    def add_page(self, page):
        if self._state != SectionState.CREATED:
            raise ValueError("Cannot add pages after population")
        # ...
        self._state = SectionState.POPULATED
    
    def ensure_complete(self):
        if self._state != SectionState.POPULATED:
            raise ValueError("Section not populated")
        # ...
        self._state = SectionState.COMPLETED
```

---

## 🏗️ Proposed Architecture (Long-Term)

### Option A: **Object Responsibility** (Recommended)

**Sections manage their own lifecycle:**

```python
class Section:
    """Self-managing section with explicit lifecycle."""
    
    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.pages = []
        self.subsections = []
        self.index_page = None
        self._state = SectionState.CREATED
    
    def add_page(self, page: Page) -> None:
        """Add a page to this section."""
        self.pages.append(page)
        
        # Automatically set index if it's _index.md
        if page.source_path.stem in ("index", "_index"):
            self.index_page = page
    
    def finalize(self, site: 'Site') -> None:
        """
        Finalize section after all pages added.
        
        Ensures section has valid index page.
        """
        if self._state != SectionState.CREATED:
            return  # Already finalized
        
        # Ensure we have an index
        if not self.index_page and self.name != 'root':
            self.index_page = self._generate_archive_index(site)
        
        # Recursively finalize subsections
        for subsection in self.subsections:
            subsection.finalize(site)
        
        self._state = SectionState.COMPLETED
    
    def validate(self) -> List[str]:
        """Validate section is complete and correct."""
        errors = []
        
        if self.name != 'root' and not self.index_page:
            errors.append(f"Section '{self.name}' has no index page")
        
        # Recursively validate subsections
        for subsection in self.subsections:
            errors.extend(subsection.validate())
        
        return errors
    
    def _generate_archive_index(self, site: 'Site') -> Page:
        """Generate auto-archive index page."""
        from bengal.utils.pagination import Paginator
        
        # Create virtual page for archive
        virtual_path = site.root_path / ".bengal" / "generated" / "archives" / self.name / "index.md"
        
        archive_page = Page(
            source_path=virtual_path,
            content="",
            metadata={
                'title': self.title,
                'template': 'archive.html',
                'type': 'archive',
                '_generated': True,
                '_virtual': True,
                '_section': self,
                '_posts': self.pages,
                '_subsections': self.subsections,
            }
        )
        
        # Set output path
        archive_page.output_path = site.output_dir / self.name / "index.html"
        
        # Add to site pages
        site.pages.append(archive_page)
        
        return archive_page


class BuildOrchestrator:
    """Build coordinator with explicit phases."""
    
    def build(self):
        # Phase 1: Discovery
        print("\n📂 Discovering content:")
        self.content.discover()
        
        # Phase 2: Finalize sections (ensure all have indexes)
        print("\n🔧 Finalizing sections:")
        for section in self.site.sections:
            section.finalize(self.site)
        
        # Phase 3: Validate structure
        print("\n✓ Validating structure:")
        errors = []
        for section in self.site.sections:
            errors.extend(section.validate())
        
        if errors:
            if self.site.config.get('strict_mode'):
                raise BuildValidationError(errors)
            else:
                for error in errors:
                    print(f"⚠️  {error}")
        
        # Phase 4: Taxonomies (only cross-cutting concerns)
        print("\n🏷️  Collecting taxonomies:")
        self.taxonomy.collect_taxonomies()
        self.taxonomy.generate_taxonomy_pages()  # Only tags, not archives!
        
        # Phase 5: Render everything
        print("\n📄 Rendering content:")
        self.render.process(self.site.pages, parallel=True)
        
        # ...rest of build
```

**Benefits:**
- ✅ Sections manage their own state
- ✅ Explicit lifecycle (finalize before render)
- ✅ Validation catches issues early
- ✅ Archives generated where they belong (in Section)
- ✅ No gap between discovery and rendering
- ✅ Clear separation: structural (Section) vs cross-cutting (Taxonomy)

**Drawbacks:**
- ⚠️ Sections now have more responsibility
- ⚠️ Need to refactor existing code
- ⚠️ Slightly more complex Section class

---

### Option B: **Dedicated SectionOrchestrator** (Alternative)

**Extract section logic into dedicated orchestrator:**

```python
class SectionOrchestrator:
    """
    Handles section lifecycle and structure.
    
    Responsibilities:
    - Ensure sections are complete (have indexes)
    - Generate archive pages for sections
    - Validate section hierarchy
    - Manage section state transitions
    """
    
    def __init__(self, site: 'Site'):
        self.site = site
    
    def finalize_sections(self) -> None:
        """Ensure all sections have index pages."""
        for section in self.site.sections:
            self._finalize_section(section)
    
    def _finalize_section(self, section: Section) -> None:
        """Finalize a single section."""
        # Skip root
        if section.name == 'root':
            return
        
        # Ensure index exists
        if not section.index_page:
            section.index_page = self._generate_archive_index(section)
        
        # Recursively finalize subsections
        for subsection in section.subsections:
            self._finalize_section(subsection)
    
    def validate_sections(self) -> List[str]:
        """Validate all sections are complete."""
        errors = []
        for section in self.site.sections:
            errors.extend(self._validate_section(section))
        return errors
    
    def _validate_section(self, section: Section) -> List[str]:
        """Validate a single section."""
        errors = []
        
        if section.name != 'root' and not section.index_page:
            errors.append(f"Section '{section.name}' has no index page")
        
        # Validate index URL is set
        if section.index_page and not section.index_page.output_path:
            errors.append(f"Section '{section.name}' index has no output path")
        
        # Recursively validate subsections
        for subsection in section.subsections:
            errors.extend(self._validate_section(subsection))
        
        return errors
    
    def _generate_archive_index(self, section: Section) -> Page:
        """Generate archive index for section."""
        # Same logic as Option A but in orchestrator
        pass


class BuildOrchestrator:
    """Build coordinator with section orchestrator."""
    
    def __init__(self, site: 'Site'):
        self.site = site
        self.content = ContentOrchestrator(site)
        self.sections = SectionOrchestrator(site)  # ← New!
        self.taxonomy = TaxonomyOrchestrator(site)
        self.menu = MenuOrchestrator(site)
        self.render = RenderOrchestrator(site)
        # ...
    
    def build(self):
        # Phase 1: Discovery
        self.content.discover()
        
        # Phase 2: Complete sections (new!)
        self.sections.finalize_sections()
        
        # Phase 3: Validate (new!)
        errors = self.sections.validate_sections()
        if errors and self.site.config.get('strict_mode'):
            raise BuildValidationError(errors)
        
        # Phase 4: Taxonomies (only tags now!)
        self.taxonomy.collect_and_generate_taxonomies()
        
        # Phase 5: Render
        self.render.process(self.site.pages)
        
        # ...
```

**Benefits:**
- ✅ Maintains orchestrator pattern consistency
- ✅ Section logic centralized in one place
- ✅ Easy to test (mock orchestrator)
- ✅ Sections stay simple (passive data)
- ✅ Clear separation in build phases

**Drawbacks:**
- ⚠️ Another orchestrator to maintain
- ⚠️ Sections less self-contained
- ⚠️ Logic split between Section and SectionOrchestrator

---

### Option C: **Hybrid Approach** (Best of Both)

**Sections have lifecycle methods, orchestrator coordinates:**

```python
class Section:
    """Section with self-management capabilities."""
    
    def needs_auto_index(self) -> bool:
        """Check if section needs auto-generated index."""
        return self.name != 'root' and not self.index_page
    
    def create_auto_index(self, site: 'Site') -> Page:
        """Create auto-generated index page."""
        # Section knows HOW to create its index
        pass
    
    def validate(self) -> List[str]:
        """Validate this section is complete."""
        # Section knows HOW to validate itself
        pass


class SectionOrchestrator:
    """Coordinates section completion."""
    
    def finalize_sections(self) -> None:
        """Ensure all sections are complete."""
        for section in self.site.sections:
            if section.needs_auto_index():
                index_page = section.create_auto_index(self.site)
                self.site.pages.append(index_page)
            
            # Recurse
            for subsection in section.subsections:
                # ... recursive call
    
    def validate_sections(self) -> List[str]:
        """Validate all sections."""
        errors = []
        for section in self.site.sections:
            errors.extend(section.validate())
        return errors
```

**Benefits:**
- ✅ Sections have smart methods (OO)
- ✅ Orchestrator coordinates (separation)
- ✅ Best of both worlds
- ✅ Sections testable in isolation
- ✅ Orchestrator handles site-wide concerns

**This is the recommended approach!**

---

## 🎯 Implementation Plan

### Phase 1: Add SectionOrchestrator (1-2 hours)

```python
# bengal/orchestration/section.py

class SectionOrchestrator:
    """Handles section structure and completeness."""
    
    def __init__(self, site: 'Site'):
        self.site = site
    
    def finalize_sections(self) -> None:
        """Ensure all sections have index pages."""
        for section in self.site.sections:
            self._finalize_recursive(section)
    
    def _finalize_recursive(self, section: Section) -> None:
        """Recursively finalize section and subsections."""
        # Ensure index
        if section.name != 'root' and not section.index_page:
            index_page = self._create_archive_index(section)
            section.index_page = index_page
            self.site.pages.append(index_page)
        
        # Recurse
        for subsection in section.subsections:
            self._finalize_recursive(subsection)
    
    def _create_archive_index(self, section: Section) -> Page:
        """Create archive index for section."""
        # Move logic from TaxonomyOrchestrator here
        pass
    
    def validate_sections(self) -> List[str]:
        """Validate all sections."""
        errors = []
        for section in self.site.sections:
            errors.extend(self._validate_recursive(section))
        return errors
    
    def _validate_recursive(self, section: Section) -> List[str]:
        """Recursively validate section."""
        errors = []
        
        if section.name != 'root' and not section.index_page:
            errors.append(f"Section '{section.name}' missing index")
        
        for subsection in section.subsections:
            errors.extend(self._validate_recursive(subsection))
        
        return errors
```

### Phase 2: Update BuildOrchestrator (30 minutes)

```python
class BuildOrchestrator:
    def __init__(self, site):
        # ...
        self.sections = SectionOrchestrator(site)  # New!
    
    def build(self):
        # Phase 1: Discovery
        self.content.discover()
        
        # Phase 2: Complete sections (NEW!)
        print("\n🔧 Completing sections:")
        self.sections.finalize_sections()
        
        # Validate (NEW!)
        errors = self.sections.validate_sections()
        if errors:
            if self.site.config.get('strict_mode'):
                raise BuildValidationError(errors)
            for error in errors:
                print(f"⚠️  {error}")
        
        # Phase 3: Taxonomies (no longer handles archives!)
        self.taxonomy.collect_and_generate_taxonomies()
        
        # ...rest unchanged
```

### Phase 3: Refactor TaxonomyOrchestrator (30 minutes)

```python
class TaxonomyOrchestrator:
    """Now only handles tags/categories."""
    
    def collect_and_generate_taxonomies(self) -> None:
        """Collect and generate taxonomy pages."""
        self.collect_taxonomies()
        self.generate_taxonomy_pages()  # Not generate_dynamic_pages!
    
    def generate_taxonomy_pages(self) -> None:
        """Generate tag and category pages ONLY."""
        print("\n✨ Generated taxonomy pages:")
        
        # Generate tag pages
        if self.site.taxonomies.get('tags'):
            tag_index = self._create_tag_index_page()
            self.site.pages.append(tag_index)
            
            for tag_slug, tag_data in self.site.taxonomies['tags'].items():
                tag_pages = self._create_tag_pages(tag_slug, tag_data)
                self.site.pages.extend(tag_pages)
        
        # Categories...
    
    # Remove _create_archive_pages method entirely!
```

### Phase 4: Add Tests (1-2 hours)

```python
# tests/unit/orchestration/test_section_orchestrator.py

def test_section_finalization_creates_missing_indexes():
    """Sections without _index.md get auto-generated indexes."""
    site = create_test_site({
        'content/docs/': ['page.md'],  # No _index.md
    })
    
    orchestrator = SectionOrchestrator(site)
    orchestrator.finalize_sections()
    
    docs_section = get_section(site, 'docs')
    assert docs_section.index_page is not None
    assert docs_section.index_page.metadata.get('_generated') is True

def test_section_validation_catches_missing_indexes():
    """Validation detects sections without indexes."""
    section = Section(name='test', path=Path('content/test'))
    section.pages = [create_page('page.md')]
    # No index_page set!
    
    orchestrator = SectionOrchestrator(Mock())
    errors = orchestrator._validate_recursive(section)
    
    assert len(errors) == 1
    assert 'test' in errors[0]
    assert 'missing index' in errors[0].lower()

def test_sections_with_explicit_index_not_modified():
    """Sections with _index.md are left alone."""
    site = create_test_site({
        'content/docs/_index.md': 'title: Docs',
        'content/docs/page.md': 'content',
    })
    
    orchestrator = SectionOrchestrator(site)
    docs_section = get_section(site, 'docs')
    original_index = docs_section.index_page
    
    orchestrator.finalize_sections()
    
    assert docs_section.index_page is original_index
    assert docs_section.index_page.metadata.get('_generated') is not True
```

### Phase 5: Update Documentation (30 minutes)

```markdown
## Section Index Pages

Every section in Bengal must have an index page at its URL.

### Automatic Index Generation

Bengal automatically ensures every section directory has an index page:

1. **Explicit Index**: Create `_index.md` in the directory
2. **Auto-Generated**: Bengal creates an archive page if no `_index.md` exists

### Section Lifecycle

Sections go through a lifecycle during build:

1. **Discovery**: Content files found and sections created
2. **Finalization**: Missing index pages auto-generated
3. **Validation**: Structure verified (fails in --strict mode)
4. **Rendering**: All pages (including indexes) rendered

### Example

```
content/
  docs/
    markdown/
      kitchen-sink.md
    templates/
      _index.md          ← Explicit index
      page.md

Output:
  docs/
    index.html           ← Auto-generated archive
    markdown/
      index.html         ← Auto-generated archive
      kitchen-sink/
        index.html       ← From kitchen-sink.md
    templates/
      index.html         ← From _index.md
      page/
        index.html       ← From page.md
```

All section URLs are guaranteed to work.
```

---

## 📊 Architecture Comparison

| Aspect | Current | Option A (Object) | Option B (Orchestrator) | **Option C (Hybrid)** |
|--------|---------|-------------------|------------------------|----------------------|
| **Responsibility** | Split/unclear | Section | Orchestrator | Shared |
| **Testability** | Hard | Easy | Easy | Very easy |
| **Separation** | Poor | Good | Excellent | Excellent |
| **Complexity** | Low | Medium | Medium | Medium |
| **Maintainability** | Poor | Good | Good | Excellent |
| **Extensibility** | Limited | Good | Excellent | Excellent |
| **Hugo Compat** | Broken | Fixed | Fixed | Fixed |
| **Validation** | None | Partial | Complete | Complete |

**Recommended: Option C (Hybrid)**

---

## 🎓 Design Lessons

### 1. **Orchestrators for Coordination, Objects for Logic**

- Orchestrators coordinate site-wide operations
- Objects (Section, Page) know how to manage themselves
- Don't make orchestrators do everything

### 2: **Make Lifecycles Explicit**

- Objects go through phases: created → populated → finalized → validated
- Enforce lifecycle with validation
- Don't allow invalid intermediate states to persist

### 3. **Separate Structural from Cross-Cutting**

- Section indexes are structural (part of hierarchy)
- Tags are cross-cutting (span multiple sections)
- Don't mix these concerns

### 4. **Validation is Not Optional**

- Validate structure between phases
- Fail fast with helpful errors
- --strict mode for CI/CD

### 5. **Single Responsibility Principle**

- Each orchestrator has ONE job:
  - ContentOrchestrator: Discover content
  - SectionOrchestrator: Ensure sections complete
  - TaxonomyOrchestrator: Handle tags/categories
  - RenderOrchestrator: Render pages

---

## 🚀 Migration Path

### Immediate (1 week)

1. Create SectionOrchestrator
2. Move archive generation from TaxonomyOrchestrator
3. Add section finalization phase
4. Add validation phase
5. Update tests

### Short-term (1 month)

1. Add lifecycle states to Section
2. Implement strict mode validation
3. Add health check for section indexes
4. Update documentation
5. Add integration tests

### Long-term (3 months)

1. Consider formal state machine for Section
2. Add plugin hooks for section finalization
3. Support custom section types
4. Performance optimization for large sites

---

## ✅ Success Criteria

A successful architecture should:

- [ ] **No silent failures** - All issues detected and reported
- [ ] **Explicit contracts** - Clear invariants documented and enforced
- [ ] **Separation of concerns** - Structural vs cross-cutting separated
- [ ] **Object responsibility** - Objects manage their own validity
- [ ] **Validation built-in** - Checked between phases
- [ ] **Hugo compatible** - Matches Hugo's behavior
- [ ] **Testable** - Easy to test in isolation
- [ ] **Extensible** - Easy to add new section types
- [ ] **Maintainable** - Clear code organization
- [ ] **Documented** - Architecture and design explained

---

## 🎯 Recommendation

**Implement Option C (Hybrid Approach):**

1. Add `SectionOrchestrator` to coordinate section completion
2. Add validation methods to `Section` class for self-validation
3. Insert finalization and validation phases in `BuildOrchestrator`
4. Move archive generation from `TaxonomyOrchestrator` to `SectionOrchestrator`
5. Add comprehensive tests for section lifecycle
6. Document the architecture and lifecycle

**Timeline:** 1 week for implementation, 1 week for testing and documentation

**Benefits:**
- ✅ Fixes immediate bug (missing index pages)
- ✅ Makes architecture more robust long-term
- ✅ Maintains existing orchestrator pattern
- ✅ Adds validation and fail-fast behavior
- ✅ Separates structural from cross-cutting concerns
- ✅ Enables future enhancements (state machines, plugins)

This is the architecturally sound, maintainable, long-term solution.

