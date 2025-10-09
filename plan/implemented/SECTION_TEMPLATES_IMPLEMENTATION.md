# Section Templates and Index Files Implementation

**Status**: ✅ Complete  
**Date**: 2025-10-09

## Overview

Clarified template behavior, index file semantics, and archive page role to improve UX for both readers and writers. Enhanced auto-generation capabilities and added helpful empty states.

## Changes Implemented

### 1. Index File Collision Detection

**Problem**: Both `index.md` and `_index.md` could exist in the same section, causing undefined behavior.

**Solution**: Added collision detection that prefers `_index.md` (Hugo convention) and logs a warning when both exist.

**Files Modified**:
- `bengal/core/section.py` - Added collision detection in `add_page()` method
  - Detects when both index files exist
  - Prefers `_index.md` over `index.md`
  - Logs warning with helpful message

**Behavior**:
```
WARNING: index_file_collision
  section: docs
  existing_file: index.md  
  new_file: _index.md
  action: preferring_underscore_version
  suggestion: Remove one of the index files - only _index.md or index.md should exist
```

### 2. Archive Page Role Clarification

**Problem**: `archive.html` was used as catch-all for all auto-generated sections, conflating chronological content with generic section listings.

**Solution**: Differentiated archive from generic list pages with smarter content type detection.

**Files Modified**:
- `bengal/orchestration/section.py` - Enhanced `_detect_content_type()` method
  - Added `list` as distinct content type (uses `index.html`)
  - Archive now specifically for chronological/dated content
  - Date-based heuristic (60%+ pages with dates → archive)
  - Explicit blog/post section name detection
  - Default changed from `archive` to `list`

**New Content Type Hierarchy**:
- `archive` - Chronological content with pagination (blog, posts, news)
- `list` - Generic section landing page (uses `index.html`)  
- `api-reference` - API documentation (uses `api-reference/list.html`)
- `cli-reference` - CLI commands (uses `cli-reference/list.html`)
- `tutorial` - Tutorial sections (uses `tutorial/list.html`)

**Template Selection Updated**:
```python
template_map = {
    'api-reference': 'api-reference/list.html',
    'cli-reference': 'cli-reference/list.html',
    'tutorial': 'tutorial/list.html',
    'archive': 'archive.html',
    'list': 'index.html',  # Generic fallback
}
```

### 3. Enhanced Empty States

**Problem**: Empty sections showed minimal guidance for writers.

**Solution**: Added helpful empty states with specific file path suggestions.

**Files Modified**:
- `bengal/themes/default/templates/index.html` - Complete rewrite
  - Added header documentation
  - Shows child pages and subsections
  - Helpful empty state with specific paths
  - Uses article-card partial for rich display
  
- `bengal/themes/default/templates/archive.html` - Enhanced documentation
  - Added header documentation clarifying purpose
  - Better empty state with specific guidance
  - Instructions for adding dated posts

**Empty State Examples**:

```html
<!-- Generic Section (index.html) -->
<div class="empty-state">
    <p class="empty-message">This section doesn't have any content yet.</p>
    <div class="empty-help">
        <p><strong>To add content:</strong></p>
        <ul>
            <li>Create a page: <code>content/docs/my-page.md</code></li>
            <li>Add a custom index: <code>content/docs/_index.md</code></li>
            <li>Create a subsection: <code>content/docs/subsection/</code></li>
        </ul>
    </div>
</div>

<!-- Archive (archive.html) -->
<div class="empty-state">
    <p class="empty-message">No posts in this archive yet.</p>
    <div class="empty-help">
        <p><strong>To add posts:</strong></p>
        <ul>
            <li>Create a post with a date: <code>content/blog/my-post.md</code></li>
            <li>Add frontmatter with <code>date: 2025-01-01</code></li>
        </ul>
        <p class="empty-hint">💡 Posts in this section will be displayed in reverse chronological order.</p>
    </div>
</div>
```

### 4. Comprehensive Documentation

**File Created**: `TEMPLATES.md` - Complete template system guide

**Contents**:
- Template selection priority (explicit → section-specific → fallback)
- Template hierarchy explanation
- Index file semantics (`_index.md` vs `index.md`)
- Auto-generation behavior
- Content type detection rules
- Customization options
- Common patterns
- Troubleshooting guide

### 5. Test Coverage

**Files Created**:
- `tests/unit/core/test_section_index_collision.py` - 6 tests
  - Index file collision detection
  - Preference for `_index.md`
  - Cascade metadata handling
  
- `tests/unit/orchestration/test_content_type_detection.py` - 21 tests
  - Content type detection by name
  - Content type detection by metadata
  - Date-based heuristics
  - Template selection
  - Pagination decisions

**Test Results**: ✅ 27 tests, all passing

## Migration Impact

### Breaking Changes

None - all changes are additive or improve existing behavior.

### Deprecations

None

### New Warnings

- `index_file_collision` - Logged when both `index.md` and `_index.md` exist

## Benefits

### For Readers

1. **Better organized content** - Appropriate templates for different content types
2. **Improved navigation** - Clear section hierarchies with child cards
3. **Faster discovery** - Rich previews with excerpts, dates, tags
4. **Consistent experience** - Predictable template selection

### For Writers

1. **Less confusion** - Clear warning when index files collide
2. **Better guidance** - Helpful empty states with specific paths
3. **Smart defaults** - Automatic detection of content type
4. **More control** - Explicit `content_type` override available
5. **Clear documentation** - Comprehensive TEMPLATES.md guide

### For Maintainers

1. **Better separation of concerns** - Archive vs list distinction
2. **More testable** - Comprehensive test coverage
3. **Clearer codebase** - Better documentation and comments
4. **Easier debugging** - Structured logging

## Example Scenarios

### Scenario 1: Blog Section

```
content/
  blog/
    post-1.md    # date: 2025-01-15
    post-2.md    # date: 2025-01-10
```

**Result**:
- Detected as `archive` (name pattern)
- Uses `archive.html` template
- Reverse chronological order
- Pagination enabled (if > 20 posts)

### Scenario 2: Documentation Section

```
content/
  docs/
    _index.md    # Custom overview
    guide.md
    tutorial.md
```

**Result**:
- Detected as `list` (no dates, not blog)
- Uses `index.html` template (generic fallback)
- Shows custom content from `_index.md`
- Lists child pages as cards
- No pagination

### Scenario 3: API Reference Section

```
content/
  api/           # Or 'reference', 'api-reference'
    module-1.md
    module-2.md
```

**Result**:
- Detected as `api-reference` (name pattern)
- Uses `api-reference/list.html` template
- Structured layout with metadata
- No pagination (reference docs)

### Scenario 4: Collision Detected

```
content/
  docs/
    index.md     # Added first
    _index.md    # Added second
```

**Result**:
- Warning logged
- `_index.md` becomes the index page
- Both files added to section.pages
- Suggestion to remove one

## Future Enhancements

Potential improvements for future versions:

1. **Section-level card configuration**
   - Grid vs list layout
   - Excerpt length
   - Image display options

2. **Enhanced content type detection**
   - Machine learning-based detection
   - More sophisticated heuristics
   - Per-page type voting

3. **Template suggestions**
   - Analyze section content
   - Suggest optimal template
   - Generate template stubs

4. **Interactive empty states**
   - "Create page" buttons
   - Template selection wizard
   - Content type picker

## Related Issues

None - proactive improvement

## References

- Plan: `plan/section-templates-review.plan.md`
- Documentation: `TEMPLATES.md`
- Tests: `tests/unit/core/test_section_index_collision.py`
- Tests: `tests/unit/orchestration/test_content_type_detection.py`

