# Dynamic Page Architecture - Deep Analysis & Long-Term Design

**Date:** October 4, 2025  
**Goal:** Design a robust, ergonomic, and performant system for dynamically created pages

---

## 📋 Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Problem Statement](#problem-statement)
3. [Requirements](#requirements)
4. [Design Principles](#design-principles)
5. [Proposed Architecture](#proposed-architecture)
6. [Implementation Strategy](#implementation-strategy)
7. [Migration Path](#migration-path)
8. [Future Extensibility](#future-extensibility)

---

## 🔍 Current State Analysis

### Types of Dynamic Pages

Currently, we create dynamic pages in **3 places**:

| Type | Created By | Phase | Example |
|------|-----------|-------|---------|
| **Archive pages** | `SectionOrchestrator` | Phase 2 | `/docs/index.html` |
| **Tag index** | `TaxonomyOrchestrator` | Phase 3 | `/tags/index.html` |
| **Tag pages** | `TaxonomyOrchestrator` | Phase 3 | `/tags/python/index.html` |

### Current Creation Patterns

#### Pattern 1: SectionOrchestrator (Archive Pages)

```python
# bengal/orchestration/section.py:109
archive_page = Page(
    source_path=virtual_path,
    content="",
    metadata={...}
)
# ✓ Sets output_path manually
archive_page.output_path = computed_path
# ✓ Sets _site reference (after bug fix)
archive_page._site = self.site
archive_page._section = section
```

**Pros:**
- Complete initialization
- Computes output_path from section hierarchy

**Cons:**
- Manual initialization (easy to forget steps)
- No validation
- Duplicated logic for path computation

#### Pattern 2: TaxonomyOrchestrator (Tag Pages)

```python
# bengal/orchestration/taxonomy.py:142
tag_index = Page(
    source_path=virtual_path,
    content="",
    metadata={...}
)
# ✓ Sets output_path manually
tag_index.output_path = self.site.output_dir / "tags" / "index.html"
# ❌ DOESN'T set _site reference!
```

**Pros:**
- Simple, direct

**Cons:**
- Missing _site reference (same bug!)
- No standardization
- Hardcoded paths

#### Pattern 3: ContentDiscovery (Regular Pages)

```python
# bengal/discovery/content_discovery.py:102
page = Page(
    source_path=file_path,
    content=content,
    metadata=metadata
)
# ✓ _site set later by ContentOrchestrator
# ❌ output_path NOT set (happens in Phase 6)
```

**Pros:**
- Simple creation
- References set in centralized place

**Cons:**
- Incomplete at creation
- URL doesn't work until Phase 6
- Timing-dependent

### Lifecycle Timeline

```
Phase 1: Discovery
├─ Regular pages created
├─ _site references set ✓
└─ output_path NOT set ✗

Phase 2: Section Finalization  
├─ Archive pages created
├─ output_path set manually ✓
├─ _site reference set (after fix) ✓
└─ page.url works ✓

Phase 3: Taxonomies
├─ Tag pages created
├─ output_path set manually ✓
├─ _site reference NOT set ✗ (BUG!)
└─ page.url falls back to slug ✗

Phase 6: Rendering
├─ _set_output_paths_for_all_pages() called
├─ Sets output_path for regular pages ✓
├─ Skips pages with output_path already set
└─ page.url works for all ✓
```

### The Core Problems

1. **Inconsistent Initialization**
   - 3 different patterns for creating pages
   - Easy to forget `_site` or `output_path`
   - No single source of truth

2. **Silent Failures**
   - Missing references → fallback URL (wrong)
   - No errors, just incorrect behavior
   - Hard to debug

3. **Timing Dependencies**
   - page.url works differently at different phases
   - Theme developers can't rely on consistent behavior
   - Makes testing difficult

4. **Scattered Logic**
   - Output path computation duplicated
   - URL generation logic in Page class
   - No centralized control

5. **No Extensibility**
   - Adding new dynamic page types requires copying pattern
   - No framework for ensuring correctness
   - Risk of bugs with each new type

---

## 🎯 Problem Statement

**Core Issue:** Dynamic pages have complex initialization requirements that are easy to get wrong, leading to silent failures and incorrect URLs.

**User Impact:**
- Theme developers get inconsistent `page.url` values
- Internal links break silently
- Hard to debug why URLs are wrong
- Fear of using dynamic pages

**Developer Impact:**
- Easy to introduce bugs when adding new page types
- Must remember implicit initialization contract
- Testing is difficult (timing-dependent)
- Code duplication across orchestrators

---

## 📐 Requirements

### Functional Requirements

1. **All pages must have working URLs at all times**
   - No "sometimes works" behavior
   - Predictable across build phases

2. **Consistent initialization**
   - Single way to create pages
   - Impossible to create incomplete pages

3. **Clear contracts**
   - Explicit about what's required
   - Type-safe where possible
   - Self-documenting

4. **Extensible**
   - Easy to add new dynamic page types
   - Reusable patterns
   - Framework, not copy-paste

### Non-Functional Requirements

1. **Performance**
   - No redundant computation
   - Lazy evaluation where beneficial
   - Fast URL generation

2. **Ergonomic**
   - Intuitive for theme developers
   - Simple for common cases
   - Powerful for advanced cases

3. **Reliable**
   - Fail fast on errors
   - Clear error messages
   - Impossible to create invalid state

4. **Maintainable**
   - Clear separation of concerns
   - Easy to understand
   - Hard to misuse

---

## 🏗️ Design Principles

### 1. **Make Illegal States Unrepresentable**

Don't allow incomplete pages to exist. If a page exists, its URL must work.

### 2. **Explicit Over Implicit**

Don't rely on "just remember to set these fields." Make requirements explicit in the API.

### 3. **Single Responsibility**

Each component does one thing well:
- Factory creates pages correctly
- Page holds data
- URL generator computes URLs

### 4. **Fail Fast**

Errors at creation time, not at access time. Better to crash the build than serve broken links.

### 5. **Convention Over Configuration**

Smart defaults for common cases, customization for edge cases.

---

## 🎨 Proposed Architecture

### Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PageFactory                              │
│  Single place to create all pages (regular + dynamic)      │
│  - Ensures complete initialization                         │
│  - Computes output paths                                   │
│  - Sets all references                                     │
│  - Validates correctness                                   │
└─────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
┌───────────▼────┐  ┌──────▼──────┐  ┌─────▼────────┐
│ Regular Pages  │  │ Archive     │  │ Taxonomy     │
│ from files     │  │ Pages       │  │ Pages        │
│                │  │ (virtual)   │  │ (virtual)    │
└────────────────┘  └─────────────┘  └──────────────┘
            │               │               │
            └───────────────┼───────────────┘
                            │
                    ┌───────▼────────┐
                    │  Page Object   │
                    │  - Always valid│
                    │  - URL works   │
                    │  - Complete    │
                    └────────────────┘
```

### Core Components

#### 1. PageFactory (New)

Centralized page creation with guaranteed correctness:

```python
class PageFactory:
    """
    Factory for creating pages with guaranteed correct initialization.
    
    All pages MUST be created through this factory to ensure:
    - _site reference is set
    - output_path is computed and set
    - metadata is validated
    - URLs work immediately
    """
    
    def __init__(self, site: 'Site'):
        self.site = site
        self.url_strategy = URLStrategy(site)
    
    def create_regular_page(
        self, 
        source_path: Path, 
        content: str, 
        metadata: Dict[str, Any]
    ) -> Page:
        """
        Create a regular content page from a file.
        
        Returns fully initialized page with working URL.
        """
        page = Page(
            source_path=source_path,
            content=content,
            metadata=metadata
        )
        
        # Complete initialization
        page._site = self.site
        page.output_path = self.url_strategy.compute_output_path(page)
        
        return page
    
    def create_archive_page(
        self,
        section: 'Section',
        posts: List[Page],
        page_num: int = 1
    ) -> Page:
        """
        Create section archive page.
        
        Args:
            section: Section to create archive for
            posts: Posts to list in archive
            page_num: Page number (for pagination)
            
        Returns:
            Fully initialized archive page
        """
        # Compute paths using section hierarchy
        virtual_path = self._make_virtual_path("archives", section.name)
        output_path = self._compute_archive_output_path(section, page_num)
        
        page = Page(
            source_path=virtual_path,
            content="",  # Archives use templates, no markdown
            metadata={
                'title': section.title,
                'template': 'archive.html',
                'type': 'archive',
                '_generated': True,
                '_virtual': True,
                '_section': section,
                '_posts': posts,
                '_page_num': page_num,
            }
        )
        
        # Complete initialization (guaranteed)
        page._site = self.site
        page._section = section
        page.output_path = output_path
        
        # Validate before returning
        self._validate_page(page)
        
        return page
    
    def create_tag_page(
        self,
        tag_slug: str,
        tag_name: str,
        posts: List[Page],
        page_num: int = 1
    ) -> Page:
        """
        Create tag listing page.
        
        Args:
            tag_slug: URL-safe tag identifier
            tag_name: Display name
            posts: Posts with this tag
            page_num: Page number (for pagination)
            
        Returns:
            Fully initialized tag page
        """
        virtual_path = self._make_virtual_path("tags", tag_slug)
        output_path = self._compute_tag_output_path(tag_slug, page_num)
        
        page = Page(
            source_path=virtual_path,
            content="",
            metadata={
                'title': f"Posts tagged '{tag_name}'",
                'template': 'tag.html',
                'type': 'taxonomy',
                '_generated': True,
                '_virtual': True,
                '_tag': tag_slug,
                '_tag_name': tag_name,
                '_posts': posts,
                '_page_num': page_num,
            }
        )
        
        # Complete initialization
        page._site = self.site
        page.output_path = output_path
        
        # Validate
        self._validate_page(page)
        
        return page
    
    def _compute_archive_output_path(
        self, 
        section: 'Section', 
        page_num: int
    ) -> Path:
        """
        Compute output path for archive page using section hierarchy.
        
        Examples:
            section='docs', page_num=1 → public/docs/index.html
            section='docs', page_num=2 → public/docs/page/2/index.html
            section='docs/markdown', page_num=1 → public/docs/markdown/index.html
        """
        # Get full hierarchy (excluding 'root')
        hierarchy = [h for h in section.hierarchy if h != 'root']
        
        # Build path
        path = self.site.output_dir
        for segment in hierarchy:
            path = path / segment
        
        # Add pagination if needed
        if page_num > 1:
            path = path / "page" / str(page_num)
        
        return path / "index.html"
    
    def _compute_tag_output_path(self, tag_slug: str, page_num: int) -> Path:
        """Compute output path for tag page."""
        path = self.site.output_dir / "tags" / tag_slug
        
        if page_num > 1:
            path = path / "page" / str(page_num)
        
        return path / "index.html"
    
    def _make_virtual_path(self, *parts: str) -> Path:
        """Create virtual source path for generated pages."""
        return (
            self.site.root_path / 
            ".bengal" / 
            "generated" / 
            Path(*parts) / 
            "index.md"
        )
    
    def _validate_page(self, page: Page) -> None:
        """
        Validate page is fully initialized.
        
        Raises:
            ValueError: If page is incomplete
        """
        if not page._site:
            raise ValueError(f"Page {page.title} missing _site reference")
        
        if not page.output_path:
            raise ValueError(f"Page {page.title} missing output_path")
        
        if not page.output_path.is_absolute():
            raise ValueError(f"Page {page.title} has relative output_path: {page.output_path}")
        
        # Verify URL works
        try:
            url = page.url
            if not url.startswith('/'):
                raise ValueError(f"Page {page.title} generated invalid URL: {url}")
        except Exception as e:
            raise ValueError(f"Page {page.title} URL generation failed: {e}")
```

#### 2. URLStrategy (New)

Separate URL computation from page logic:

```python
class URLStrategy:
    """
    Computes URLs and output paths for pages.
    
    Centralizes all path computation logic:
    - Output path from source path
    - URL from output path
    - Pretty URLs vs legacy URLs
    - Custom permalink patterns (future)
    """
    
    def __init__(self, site: 'Site'):
        self.site = site
        self.pretty_urls = site.config.get('pretty_urls', True)
        self.output_dir = site.output_dir
        self.content_dir = site.root_path / "content"
    
    def compute_output_path(self, page: Page) -> Path:
        """
        Compute output path for a page.
        
        Handles:
        - Regular pages (about.md → about/index.html)
        - Index pages (_index.md → index.html)
        - Pretty URLs vs flat URLs
        - Nested sections
        """
        # For generated pages, output_path should be set by factory
        if page.metadata.get('_generated'):
            raise ValueError("Generated pages shouldn't use compute_output_path")
        
        # Compute relative path from content dir
        try:
            rel_path = page.source_path.relative_to(self.content_dir)
        except ValueError:
            # Not under content_dir (shouldn't happen)
            rel_path = Path(page.source_path.name)
        
        # Change extension
        output_rel_path = rel_path.with_suffix('.html')
        
        # Apply URL rules
        if self.pretty_urls:
            if output_rel_path.stem in ("index", "_index"):
                # _index.md → index.html
                output_rel_path = output_rel_path.parent / "index.html"
            else:
                # about.md → about/index.html
                output_rel_path = output_rel_path.parent / output_rel_path.stem / "index.html"
        else:
            # Flat URLs: about.md → about.html
            if output_rel_path.stem == "_index":
                output_rel_path = output_rel_path.parent / "index.html"
        
        return self.output_dir / output_rel_path
    
    def url_from_output_path(self, output_path: Path) -> str:
        """
        Generate URL from output path.
        
        Examples:
            public/about/index.html → /about/
            public/docs/guide.html → /docs/guide/
            public/index.html → /
        """
        try:
            rel_path = output_path.relative_to(self.output_dir)
        except ValueError:
            raise ValueError(f"Output path {output_path} not under {self.output_dir}")
        
        # Convert to URL parts
        url_parts = list(rel_path.parts)
        
        # Remove index.html (implicit)
        if url_parts and url_parts[-1] == 'index.html':
            url_parts = url_parts[:-1]
        elif url_parts and url_parts[-1].endswith('.html'):
            # Non-index: remove .html
            url_parts[-1] = url_parts[-1][:-5]
        
        # Build URL
        if not url_parts:
            return '/'
        
        url = '/' + '/'.join(url_parts)
        
        # Trailing slash
        if not url.endswith('/'):
            url += '/'
        
        return url
```

#### 3. Updated Page Class

Simplified, with validation:

```python
@dataclass
class Page:
    """
    Represents a content page.
    
    Pages should be created via PageFactory to ensure correct initialization.
    Direct construction is discouraged (but not prevented for testing).
    """
    
    source_path: Path
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Required references (should be set by factory)
    _site: Optional[Any] = field(default=None, repr=False)
    _section: Optional[Any] = field(default=None, repr=False)
    output_path: Optional[Path] = None
    
    # Computed/rendered content
    parsed_ast: Optional[Any] = None
    rendered_html: str = ""
    toc: Optional[str] = None
    
    # Other fields...
    
    @property
    def url(self) -> str:
        """
        Get page URL.
        
        URL is computed from output_path, which MUST be set.
        If not set, raises error (fail fast).
        """
        if not self.output_path:
            # FAIL FAST instead of fallback
            raise ValueError(
                f"Page '{self.title}' has no output_path set. "
                f"Pages must be created via PageFactory."
            )
        
        if not self._site:
            raise ValueError(
                f"Page '{self.title}' has no _site reference. "
                f"Pages must be created via PageFactory."
            )
        
        # Delegate to URLStrategy
        from bengal.utils.url_strategy import URLStrategy
        strategy = URLStrategy(self._site)
        return strategy.url_from_output_path(self.output_path)
    
    def _fallback_url(self) -> str:
        """
        DEPRECATED: Remove fallback behavior.
        
        Keeping for now to ease migration, but should be removed.
        """
        import warnings
        warnings.warn(
            f"Page '{self.title}' using fallback URL. "
            "This indicates improper initialization.",
            DeprecationWarning
        )
        return f"/{self.slug}/"
```

---

## 🔄 Usage Examples

### Example 1: Creating Archive Page (New Way)

```python
class SectionOrchestrator:
    def __init__(self, site: 'Site'):
        self.site = site
        self.page_factory = PageFactory(site)  # ← Use factory
    
    def _finalize_recursive(self, section: 'Section') -> None:
        if section.name == 'root':
            return
        
        if not section.index_page:
            # Use factory - guaranteed correct
            archive_page = self.page_factory.create_archive_page(
                section=section,
                posts=section.pages,
                page_num=1
            )
            
            section.index_page = archive_page
            self.site.pages.append(archive_page)
            
            # URL works immediately!
            print(f"Created archive: {archive_page.url}")
```

### Example 2: Creating Tag Pages (New Way)

```python
class TaxonomyOrchestrator:
    def __init__(self, site: 'Site'):
        self.site = site
        self.page_factory = PageFactory(site)  # ← Use factory
    
    def _create_tag_pages(self, tag_slug: str, tag_data: dict) -> List[Page]:
        pages = []
        posts = tag_data['pages']
        
        # Paginate if needed
        per_page = self.site.config.get('pagination', {}).get('per_page', 10)
        
        for page_num in range(1, num_pages + 1):
            start = (page_num - 1) * per_page
            end = start + per_page
            
            # Use factory - guaranteed correct
            tag_page = self.page_factory.create_tag_page(
                tag_slug=tag_slug,
                tag_name=tag_data['name'],
                posts=posts[start:end],
                page_num=page_num
            )
            
            pages.append(tag_page)
            
            # URL works immediately!
            print(f"Created tag page: {tag_page.url}")
        
        return pages
```

### Example 3: Creating Regular Pages (Updated)

```python
class ContentDiscovery:
    def __init__(self, content_dir: Path, site: 'Site'):
        self.content_dir = content_dir
        self.page_factory = PageFactory(site)  # ← Use factory
    
    def _create_page(self, file_path: Path) -> Page:
        # Parse file
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
        
        # Use factory - guaranteed correct
        page = self.page_factory.create_regular_page(
            source_path=file_path,
            content=post.content,
            metadata=dict(post.metadata)
        )
        
        # URL works immediately!
        return page
```

### Example 4: Theme Developer Usage

```jinja2
{# Theme developers can always trust page.url #}
{% for post in posts %}
  <article>
    <h2>
      <a href="{{ post.url }}">{{ post.title }}</a>
    </h2>
  </article>
{% endfor %}

{# Works for sections too #}
{% for subsection in section.sections %}
  <div class="subsection">
    <a href="{{ subsection.url }}">{{ subsection.title }}</a>
  </div>
{% endfor %}

{# No need to worry about timing or initialization #}
```

---

## 🚀 Implementation Strategy

### Phase 1: Add Factory (Non-Breaking)

1. Create `bengal/utils/page_factory.py`
2. Create `bengal/utils/url_strategy.py`
3. Add comprehensive tests
4. Document usage

**Status:** New code, no breaking changes

### Phase 2: Migrate Orchestrators

1. Update `SectionOrchestrator` to use factory
2. Update `TaxonomyOrchestrator` to use factory
3. Update `ContentDiscovery` to use factory
4. Run full test suite

**Status:** Internal changes, no API changes

### Phase 3: Add Validation

1. Update `Page.url` to fail fast (raise errors)
2. Add deprecation warnings for fallback behavior
3. Add build-time validation
4. Update documentation

**Status:** May expose existing bugs (good!)

### Phase 4: Remove Legacy Code

1. Remove fallback URL logic
2. Remove scattered output_path computation
3. Consolidate in URLStrategy
4. Major version bump

**Status:** Breaking change (but cleaner)

---

## 🔀 Migration Path

### For Internal Code

```python
# OLD (before)
archive_page = Page(source_path=..., content="", metadata={...})
archive_page.output_path = computed_path
archive_page._site = self.site

# NEW (after)
archive_page = self.page_factory.create_archive_page(
    section=section,
    posts=posts
)
```

### For Theme Developers

**No changes required!** `page.url` still works, just more reliably.

### For Plugin Developers (Future)

```python
# If creating custom dynamic pages
from bengal.utils.page_factory import PageFactory

class MyPluginOrchestrator:
    def __init__(self, site):
        self.factory = PageFactory(site)
    
    def create_custom_page(self):
        # Extend factory with custom method
        # OR use create_regular_page with custom metadata
        pass
```

---

## 🔮 Future Extensibility

### Custom Permalink Patterns

```python
# bengal.toml
[permalinks]
posts = "/:year/:month/:slug/"
docs = "/documentation/:slug/"

# Implemented in URLStrategy
class URLStrategy:
    def compute_output_path(self, page: Page) -> Path:
        # Check for custom permalink pattern
        if page._section:
            pattern = self.site.config.get('permalinks', {}).get(page._section.name)
            if pattern:
                return self._apply_permalink_pattern(page, pattern)
        
        # Default behavior
        return self._default_output_path(page)
```

### Multi-Language Support

```python
class PageFactory:
    def create_translated_page(
        self,
        source_page: Page,
        language: str,
        translated_content: str
    ) -> Page:
        """Create translated version of a page."""
        # Compute language-specific path
        output_path = self._compute_i18n_output_path(source_page, language)
        
        page = Page(...)
        page._site = self.site
        page.output_path = output_path
        page.metadata['language'] = language
        page.metadata['translation_of'] = source_page
        
        return page
```

### RSS/Sitemap as Pages

```python
class PageFactory:
    def create_feed_page(
        self,
        feed_type: str,  # 'rss', 'atom', 'json'
        posts: List[Page]
    ) -> Page:
        """Create RSS/Atom/JSON feed as a page."""
        output_path = self.site.output_dir / f"feed.{feed_type}"
        
        page = Page(
            source_path=self._make_virtual_path("feeds", feed_type),
            content="",
            metadata={
                'template': f'feed.{feed_type}',
                '_generated': True,
                '_posts': posts,
            }
        )
        
        page._site = self.site
        page.output_path = output_path
        
        return page
```

### Search Index Generation

```python
class PageFactory:
    def create_search_index(self, pages: List[Page]) -> Page:
        """Create search index page."""
        import json
        
        # Build search index
        index = {
            'pages': [
                {
                    'title': p.title,
                    'url': p.url,
                    'content': strip_html(p.rendered_html)
                }
                for p in pages
            ]
        }
        
        page = Page(
            source_path=self._make_virtual_path("search", "index"),
            content=json.dumps(index),
            metadata={
                'template': None,  # No template - output JSON directly
                '_generated': True,
                '_format': 'json',
            }
        )
        
        page._site = self.site
        page.output_path = self.site.output_dir / "search.json"
        
        return page
```

---

## 📊 Benefits Summary

### Before (Current)

❌ 3 different page creation patterns  
❌ Easy to forget initialization steps  
❌ Silent failures (wrong URLs)  
❌ Timing-dependent behavior  
❌ Duplicated path computation logic  
❌ Hard to add new dynamic page types

### After (Proposed)

✅ Single page creation pattern (factory)  
✅ Impossible to create incomplete pages  
✅ Fail fast (errors at creation)  
✅ Consistent behavior at all phases  
✅ Centralized path computation  
✅ Framework for new page types

### For Theme Developers

✅ `page.url` always works  
✅ No timing concerns  
✅ Predictable behavior  
✅ Clear error messages  
✅ Works the same in templates, plugins, tests

### For Core Developers

✅ Easy to add new dynamic page types  
✅ Single place to fix bugs  
✅ Testable in isolation  
✅ Clear separation of concerns  
✅ Self-documenting code

---

## 🎯 Success Metrics

1. **Zero URL bugs** - All pages have correct URLs
2. **Fast failure** - Bad initialization caught immediately
3. **Easy extension** - New page types in < 50 lines
4. **Theme confidence** - Developers trust `page.url`
5. **Code quality** - Less duplication, more clarity

---

## 📝 Next Steps

### Immediate (This Session)

1. ✅ Analyzed current state
2. ✅ Identified problems
3. ✅ Designed solution
4. ⏳ Get feedback on design
5. ⏳ Decide on implementation timeline

### Short Term (Next Week)

1. Implement PageFactory
2. Implement URLStrategy
3. Write comprehensive tests
4. Update SectionOrchestrator
5. Update TaxonomyOrchestrator

### Medium Term (Next Month)

1. Add validation/fail-fast behavior
2. Update documentation
3. Add migration guide
4. Deprecate old patterns

### Long Term (Next Release)

1. Remove legacy code
2. Add permalink patterns
3. Add i18n support
4. Add search index generation

---

## 🤔 Open Questions

1. **Should PageFactory be part of Site?**
   - Pro: Easy access (`site.create_page()`)
   - Con: Couples Site to page creation

2. **Should we make Page construction private?**
   - Pro: Forces use of factory
   - Con: Breaks existing code/tests

3. **How to handle plugin-created pages?**
   - Expose factory to plugins?
   - Plugin registration system?

4. **Performance impact of validation?**
   - Only in debug mode?
   - Skip in production builds?

5. **Backward compatibility?**
   - Keep fallback for 1-2 versions?
   - Immediate breaking change?

---

## 🔗 Related Documents

- [URL Architecture Analysis](URL_ARCHITECTURE_ANALYSIS.md)
- [Section Validation Fix](SECTION_VALIDATION_FIX.md)
- [Section Architecture Analysis](completed/SECTION_ARCHITECTURE_ANALYSIS.md)
- [Architecture Document](../ARCHITECTURE.md)

