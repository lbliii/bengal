# Hidden Pages Implementation Plan

## Goal

Add support for `hidden: true` in page frontmatter to create "unlisted" pages that:
- Still render and are accessible via direct URL
- Don't appear in navigation, lists, or search
- Don't appear in sitemaps or RSS feeds
- Are excluded from related posts

## Use Cases

1. **Draft/WIP content** - Work in progress not ready for public consumption
2. **Easter eggs** - Hidden pages accessible via direct link
3. **Private documentation** - Internal docs in public repo
4. **Landing pages** - Campaign pages not in main nav
5. **Deprecated content** - Keep URL working but hide from discovery
6. **Testing pages** - Demo/example pages for development

## Comparison to `draft: true`

| Feature | `draft: true` | `hidden: true` |
|---------|--------------|----------------|
| **Renders** | ✅ Yes | ✅ Yes |
| **Direct URL access** | ✅ Yes | ✅ Yes |
| **Search** | ❌ Excluded | ❌ Excluded |
| **Navigation** | ✅ Shows | ❌ Hidden |
| **Section lists** | ✅ Shows | ❌ Hidden |
| **Sitemap** | ✅ Included | ❌ Excluded |
| **RSS** | ✅ Included | ❌ Excluded |
| **Visual indicator** | ✅ "DRAFT" banner | ❌ None |
| **Semantic** | "Not ready" | "Unlisted" |

**Recommendation:** Keep both! They serve different purposes.

---

## Analysis: Where `hidden` Needs to Be Checked

### 1. Navigation Building ✅ Critical

**Files:**
- `bengal/rendering/template_functions/navigation.py`
- `bengal/orchestration/menu.py`

**Functions to update:**
- `get_nav_tree()` - Section navigation trees
- `get_auto_nav()` - Auto-discovered top nav
- `get_section_pages()` - Section page lists
- `build_menu()` - Menu construction

**Current behavior:**
```python
# get_auto_nav() already checks menu: false
menu_setting = metadata.get("menu", True)
if menu_setting is False:
    section_hidden = True
```

**Need to add:**
```python
# Also check hidden
if metadata.get("hidden", False):
    section_hidden = True
```

**Impact:** High - navigation is primary discovery mechanism

---

### 2. Search Indexing ✅ Critical

**Files:**
- `bengal/postprocess/special_pages.py` (search index generation)
- `bengal/themes/default/assets/js/search.js` (client-side)

**Current behavior:**
```python
# search.js already checks draft
if (!page.search_exclude && !page.draft) {
    this.add(page);
}
```

**Need to add:**
```python
if (!page.search_exclude && !page.draft && !page.hidden) {
    this.add(page);
}
```

**Also check:**
- `_generate_search_index()` in special_pages.py
- Index JSON generation

**Impact:** High - primary discovery after navigation

---

### 3. Sitemap Generation ✅ Critical

**Files:**
- `bengal/postprocess/sitemap.py`

**Current implementation:**
```python
def generate_sitemap(site: Site, output_dir: Path) -> None:
    """Generate sitemap.xml."""
    for page in site.pages:
        # Add to sitemap
```

**Need to add:**
```python
for page in site.pages:
    if page.metadata.get("hidden", False):
        continue  # Skip hidden pages
    # Add to sitemap
```

**Impact:** High - affects SEO and discovery

---

### 4. RSS Feed Generation ✅ Critical

**Files:**
- `bengal/postprocess/rss.py`

**Current implementation:**
```python
def generate_rss(site: Site, output_dir: Path, config: dict) -> None:
    """Generate RSS feed."""
    # Get recent posts
    posts = [p for p in site.pages if p.date]
```

**Need to add:**
```python
posts = [
    p for p in site.pages 
    if p.date and not p.metadata.get("hidden", False)
]
```

**Impact:** High - syndication and notifications

---

### 5. Section Page Lists ✅ High Priority

**Files:**
- `bengal/rendering/template_functions/navigation.py` - `get_section_pages()`
- `bengal/content_types/strategies.py` - `filter_display_pages()`

**Current implementation:**
```python
def filter_display_pages(self, pages, index_page=None):
    """Filter which pages to show in lists."""
    if index_page:
        return [p for p in pages if p != index_page]
    return list(pages)
```

**Need to add:**
```python
def filter_display_pages(self, pages, index_page=None):
    """Filter which pages to show in lists."""
    filtered = [p for p in pages if not p.metadata.get("hidden", False)]
    if index_page:
        filtered = [p for p in filtered if p != index_page]
    return filtered
```

**Impact:** High - affects all section list pages

---

### 6. Related Posts ✅ Medium Priority

**Files:**
- `bengal/orchestration/related_posts.py`

**Current implementation:**
```python
def compute_related_posts(site: Site, limit: int = 5) -> None:
    """Compute related posts based on tag overlap."""
    for page in site.pages:
        candidates = [p for p in site.pages if p != page and p.tags]
```

**Need to add:**
```python
candidates = [
    p for p in site.pages 
    if p != page 
    and p.tags 
    and not p.metadata.get("hidden", False)
]
```

**Impact:** Medium - improves content discovery quality

---

### 7. Archive Pages ✅ Medium Priority

**Files:**
- `bengal/postprocess/special_pages.py` - Archive generation
- Templates: `themes/default/templates/archive.html`

**Current implementation:**
```python
def _generate_archives(self, site: Site) -> None:
    """Generate archive pages."""
    posts = [p for p in site.pages if p.date]
```

**Need to add:**
```python
posts = [
    p for p in site.pages 
    if p.date and not p.metadata.get("hidden", False)
]
```

**Impact:** Medium - chronological listings

---

### 8. Taxonomy Pages (Tags/Categories) ✅ Medium Priority

**Files:**
- `bengal/orchestration/taxonomy.py`

**Current implementation:**
```python
def build_taxonomy_pages(site: Site) -> list[Page]:
    """Build tag/category pages."""
    for page in site.pages:
        for tag in page.tags:
            taxonomy[tag].append(page)
```

**Need to add:**
```python
for page in site.pages:
    if page.metadata.get("hidden", False):
        continue
    for tag in page.tags:
        taxonomy[tag].append(page)
```

**Impact:** Medium - tag clouds and category pages

---

### 9. Template Functions ✅ Low Priority

**Files:**
- `bengal/rendering/template_functions/*.py`

**Functions to check:**
- `get_pages()` - Get all pages
- `get_recent_posts()` - Recent content
- `get_pages_by_tag()` - Tagged content
- `get_section_children()` - Child pages

**Example:**
```python
def get_recent_posts(site, limit=10):
    """Get recent posts."""
    posts = [
        p for p in site.pages 
        if p.date and not p.metadata.get("hidden", False)
    ]
    return sorted(posts, key=lambda p: p.date, reverse=True)[:limit]
```

**Impact:** Low - template helpers

---

### 10. Health Checks/Validators ⚠️ Consider

**Files:**
- `bengal/health/validators/*.py`

**Consideration:**
Should hidden pages be checked for:
- Broken links? (Probably yes)
- Missing metadata? (Probably yes)
- Accessibility? (Probably yes)

Hidden pages still render, so they should still pass validation.

**Decision:** Keep validation, just exclude from discovery.

---

## Implementation Strategy

### Phase 1: Core Filtering (Day 1)

**Priority: Critical paths**

1. **Add helper property to Page**
   ```python
   # bengal/core/page/metadata.py
   @property
   def hidden(self) -> bool:
       """Check if page is hidden from listings."""
       return self.metadata.get("hidden", False)
   ```

2. **Navigation filtering**
   - Update `get_section_pages()` 
   - Update `get_nav_tree()`
   - Update `get_auto_nav()`

3. **Content type strategies**
   - Update `filter_display_pages()` in base strategy

4. **Search indexing**
   - Update `_generate_search_index()`
   - Update `search.js` client-side

### Phase 2: Discovery Exclusion (Day 1-2)

**Priority: SEO and syndication**

5. **Sitemap generation**
   - Filter hidden pages from sitemap.xml

6. **RSS generation**
   - Filter hidden pages from RSS feeds

7. **Related posts**
   - Exclude hidden from candidates

### Phase 3: Polish (Day 2)

**Priority: Nice to have**

8. **Taxonomy pages**
   - Don't include hidden pages in tag aggregation

9. **Archive pages**
   - Exclude from date-based archives

10. **Template functions**
    - Add filters to all listing helpers

### Phase 4: Documentation (Day 2)

11. **User documentation**
    - Add to frontmatter guide
    - Add examples
    - Explain vs draft

12. **Tests**
    - Unit tests for property
    - Integration tests for filtering
    - E2E test for full flow

---

## Implementation Details

### 1. Page Property (Core)

```python
# bengal/core/page/metadata.py

@property
def hidden(self) -> bool:
    """
    Check if page is marked as hidden.
    
    Hidden pages:
    - Still render and are accessible via direct URL
    - Don't appear in navigation, lists, or search
    - Don't appear in sitemaps or RSS feeds
    - Are excluded from related posts
    
    Returns:
        True if page is hidden
    
    Example:
        ---
        title: "Secret Page"
        hidden: true
        ---
        
        # This page is accessible via direct link
        # but won't appear in any listings
    """
    return self.metadata.get("hidden", False)
```

### 2. Content Type Strategy (Base Class)

```python
# bengal/content_types/base.py

def filter_display_pages(
    self, pages: list["Page"], index_page: "Page | None" = None
) -> list["Page"]:
    """
    Filter which pages to show in list views.
    
    Excludes:
    - Hidden pages (hidden: true)
    - The index page itself
    
    Args:
        pages: All pages in the section
        index_page: The section's index page (to exclude from lists)
    
    Returns:
        Filtered list of pages
    """
    # Filter out hidden pages
    filtered = [p for p in pages if not p.hidden]
    
    # Filter out index page
    if index_page:
        filtered = [p for p in filtered if p != index_page]
    
    return filtered
```

### 3. Navigation Functions

```python
# bengal/rendering/template_functions/navigation.py

def get_section_pages(section: "Section", sort: bool = True) -> list["Page"]:
    """
    Get all pages in a section, excluding hidden pages.
    
    Args:
        section: Section to get pages from
        sort: Whether to sort by weight/title
    
    Returns:
        List of visible pages
    """
    # Filter out hidden pages
    pages = [p for p in section.pages if not p.hidden]
    
    if sort:
        pages = sorted(pages, key=lambda p: (p.metadata.get("weight", 999), p.title))
    
    return pages
```

### 4. Search Index

```python
# bengal/postprocess/special_pages.py

def _generate_search_index(self, site: Site) -> dict:
    """Generate search index JSON."""
    pages_data = []
    
    for page in site.pages:
        # Skip hidden pages
        if page.hidden:
            continue
        
        # Skip pages marked search_exclude
        if page.metadata.get("search_exclude", False):
            continue
        
        # Skip drafts
        if page.draft:
            continue
        
        pages_data.append({
            "url": page.url,
            "title": page.title,
            "content": page.plain_text[:500],  # Preview
        })
    
    return {"pages": pages_data}
```

### 5. Sitemap

```python
# bengal/postprocess/sitemap.py

def generate_sitemap(site: Site, output_dir: Path) -> None:
    """Generate sitemap.xml."""
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    
    for page in site.pages:
        # Skip hidden pages
        if page.hidden:
            continue
        
        # Add to sitemap
        url_elem = ET.SubElement(urlset, "url")
        loc = ET.SubElement(url_elem, "loc")
        loc.text = site.base_url + page.url
```

### 6. RSS Feed

```python
# bengal/postprocess/rss.py

def generate_rss(site: Site, output_dir: Path, config: dict) -> None:
    """Generate RSS feed."""
    # Get recent posts (excluding hidden)
    posts = [
        p for p in site.pages 
        if p.date 
        and not p.hidden 
        and not p.draft
    ]
    posts.sort(key=lambda p: p.date, reverse=True)
    posts = posts[:config.get("rss_limit", 20)]
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_hidden_pages.py

def test_page_hidden_property():
    """Test page.hidden property."""
    page = Page(
        source_path=Path("test.md"),
        content="test",
        metadata={"hidden": True}
    )
    assert page.hidden is True

def test_filter_display_pages_excludes_hidden():
    """Test content strategy filters hidden pages."""
    from bengal.content_types.strategies import PageStrategy
    
    visible = Page(source_path=Path("visible.md"), metadata={})
    hidden = Page(source_path=Path("hidden.md"), metadata={"hidden": True})
    
    strategy = PageStrategy()
    filtered = strategy.filter_display_pages([visible, hidden])
    
    assert visible in filtered
    assert hidden not in filtered
```

### Integration Tests

```python
# tests/integration/test_hidden_integration.py

def test_hidden_pages_not_in_search(tmp_path):
    """Test hidden pages excluded from search index."""
    # Build site with hidden page
    # Check search index JSON
    # Assert hidden page not in index

def test_hidden_pages_not_in_sitemap(tmp_path):
    """Test hidden pages excluded from sitemap."""
    # Build site with hidden page
    # Parse sitemap.xml
    # Assert hidden page not in URLs

def test_hidden_pages_not_in_navigation(tmp_path):
    """Test hidden pages don't appear in nav."""
    # Build site with hidden page
    # Check rendered HTML
    # Assert hidden page not in nav links
```

---

## Documentation Updates

### 1. Frontmatter Guide

```markdown
# docs/writing/frontmatter-guide.md

## Page Visibility

### `hidden`

Hide pages from navigation, search, and listings while keeping them accessible via direct URL.

\```yaml
---
title: "Internal Documentation"
hidden: true
---
\```

**Effects:**
- ❌ Won't appear in navigation menus
- ❌ Won't appear in section page lists  
- ❌ Won't appear in search results
- ❌ Won't appear in sitemaps or RSS feeds
- ✅ Still renders and is accessible via direct URL
- ✅ Internal links still work

**Use cases:**
- Landing pages for campaigns
- Internal documentation  
- Deprecated content (keep URL, hide from discovery)
- Easter eggs or hidden features
- Work-in-progress content

### `hidden` vs `draft`

| Use Case | Recommended |
|----------|-------------|
| Not ready for public | `draft: true` |
| Ready but unlisted | `hidden: true` |
| Internal docs | `hidden: true` |
| WIP content | `draft: true` |

Both can be used together if needed.
```

### 2. Examples

```markdown
# examples/hidden-pages/

content/
├── _index.md
├── public-page.md
├── hidden-landing.md      # hidden: true
└── internal/
    ├── _index.md          # hidden: true (hides whole section)
    └── team-docs.md       # Inherits hidden from section
```

---

## Migration Strategy

### Backwards Compatibility

✅ **No breaking changes** - `hidden` is opt-in

Existing sites:
- All pages visible by default (hidden: false)
- No behavior changes unless explicitly set

### Gradual Rollout

1. **Phase 1**: Add property and core filtering
2. **Phase 2**: Update discovery mechanisms
3. **Phase 3**: Polish and edge cases
4. **Phase 4**: Document and announce

---

## Edge Cases to Consider

### 1. Hidden Sections

If `_index.md` has `hidden: true`, should all child pages be hidden?

**Recommendation:** Yes, cascade by default.

```python
# Check if any parent section is hidden
def is_hidden_cascade(page: Page) -> bool:
    if page.hidden:
        return True
    
    section = page.section
    while section:
        if section.index_page and section.index_page.hidden:
            return True
        section = section.parent
    
    return False
```

### 2. Hidden + Draft

What if both are set?

**Recommendation:** Treat independently. Both exclude from different things.

### 3. Direct Links in Content

If I link to a hidden page from a visible page, should it warn?

**Recommendation:** No warning. Hidden pages are intentionally linkable.

### 4. Search from Hidden Page

If I'm viewing a hidden page and use search, should it show hidden pages?

**Recommendation:** No. Search results should be consistent.

---

## Performance Considerations

**Impact:** Minimal

- Property access: O(1) dict lookup
- Filtering: O(n) list comprehension (already doing this)
- No additional database queries
- No caching needed

**Optimization:**
Could cache `page.hidden` result if metadata is immutable.

---

## Success Metrics

✅ **Functionality**
- [ ] Pages with hidden: true don't appear in navigation
- [ ] Hidden pages don't appear in search
- [ ] Hidden pages excluded from sitemap/RSS
- [ ] Hidden pages still accessible via direct URL
- [ ] Hidden pages pass link validation

✅ **Quality**
- [ ] >80% test coverage for hidden logic
- [ ] Documentation complete
- [ ] Examples provided
- [ ] No performance regression

✅ **User Experience**
- [ ] Clear documentation
- [ ] Intuitive behavior
- [ ] No surprises

---

## Summary

**Scope:** 10 files to modify, ~200 lines of code

**Time estimate:** 2 days

**Priority:** Medium-High (nice QoL feature)

**Complexity:** Low (straightforward filtering)

**Risk:** Low (no breaking changes, additive only)

**Value:** High (common use case, frequently requested)

---

## Next Steps

1. ✅ Create implementation plan (this document)
2. ⏳ Review and approve plan
3. ⏳ Implement Phase 1 (core filtering)
4. ⏳ Implement Phase 2 (discovery exclusion)
5. ⏳ Test thoroughly
6. ⏳ Document feature
7. ⏳ Ship it! 🚀

