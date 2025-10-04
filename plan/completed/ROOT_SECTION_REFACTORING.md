# Root Section Refactoring Plan

## Problem

The "root" section is a leaky abstraction that requires special handling in 5+ places:

1. **docs-nav.html:29** - Template unwraps it to hide from UI
2. **breadcrumbs.html:10** - Template filters it out: `{% if ancestor.name != 'root' %}`
3. **section.py:124** - URL generation checks: `if self.parent.name != 'root'`
4. **taxonomy.py:133** - Health validator skips: `if section.name == 'root': continue`
5. **section.hierarchy** - Includes "root" in the list, exposed to users

This is a sharp edge that users will encounter when:
- Writing custom templates that iterate over `site.sections`
- Using `page.ancestors` or `section.hierarchy` in templates
- Creating navigation or directory listings

## Why It Exists

The root section was created as a **container** to hold:
- Top-level pages (e.g., `content/about.md`, `content/contact.md`)
- Top-level sections (e.g., `content/docs/`, `content/api/`)

This simplified the discovery code but created a leaky abstraction.

## Proposed Solution

### Option A: Eliminate Root Section (Recommended)

**Change content discovery to NOT create a root section:**

```python
# bengal/discovery/content_discovery.py
def discover(self) -> Tuple[List[Section], List[Page]]:
    """Discover all content in the content directory."""
    
    # Walk the content directory directly
    for item in sorted(self.content_dir.iterdir()):
        if item.name.startswith(('.', '_')) and item.name not in ('_index.md', '_index.markdown'):
            continue
        
        if item.is_file() and self._is_content_file(item):
            # Top-level page
            page = self._create_page(item)
            self.pages.append(page)
        
        elif item.is_dir():
            # Top-level section
            section = Section(name=item.name, path=item)
            self._walk_directory(item, section)
            
            if section.pages or section.subsections:
                self.sections.append(section)
    
    return self.sections, self.pages
```

**Benefits:**
- No more special "root" checks scattered through code
- Cleaner API for users
- `site.sections` directly contains user-visible sections
- Simpler mental model

**Changes Required:**
1. ✅ Remove root section creation in `content_discovery.py`
2. ✅ Remove special "root" check in `section.py:124` (URL generation)
3. ✅ Remove special "root" check in `taxonomy.py:133`
4. ✅ Remove special "root" unwrapping in `docs-nav.html:29`
5. ✅ Remove special "root" filter in `breadcrumbs.html:10`
6. ⚠️ Handle top-level pages (those without a section) - store separately or create minimal sections

**Tradeoffs:**
- Need to handle pages without sections (top-level pages)
- Slightly more complex discovery logic

### Option B: Hide Root Section (Current Approach)

Keep the root section but provide helper properties/filters to hide it:

```python
# bengal/core/site.py
@property
def visible_sections(self) -> List[Section]:
    """Get user-visible sections (excludes internal root section)."""
    return [s for s in self.sections if s.name != 'root' or s.parent is not None]

# bengal/core/page.py
@property
def visible_ancestors(self) -> List[Any]:
    """Get visible ancestor sections (excludes internal root section)."""
    return [a for a in self.ancestors if a.name != 'root']
```

**Benefits:**
- Minimal changes to existing code
- Backward compatible

**Tradeoffs:**
- Still a leaky abstraction
- Users can still encounter root section if they use `site.sections` directly
- Requires documentation: "use `visible_sections`, not `sections`"

## Recommendation

**Go with Option A** - eliminate the root section entirely. It's cleaner, more user-friendly, and removes the sharp edge permanently.

## Implementation Priority

- **Priority: Medium** - Not urgent, but should be done before 1.0
- **Risk: Low** - Internal implementation detail, no API breaking changes
- **Effort: 4-6 hours** - Touch 5-6 files, write tests, verify builds

## Testing Checklist

- [ ] Top-level pages work correctly (about.md, contact.md)
- [ ] Top-level sections work correctly (docs/, api/, posts/)
- [ ] Nested sections work correctly (api/v2/)
- [ ] Breadcrumbs don't show "root"
- [ ] Navigation sidebar works correctly
- [ ] URL generation is correct for all levels
- [ ] Health validators work correctly
- [ ] Page ancestors work correctly
- [ ] Section hierarchy works correctly

## Related Files

- `bengal/discovery/content_discovery.py` - Create sections
- `bengal/core/section.py` - URL generation, hierarchy
- `bengal/themes/default/templates/partials/docs-nav.html` - Navigation
- `bengal/themes/default/templates/partials/breadcrumbs.html` - Breadcrumbs  
- `bengal/health/validators/taxonomy.py` - Health checks

