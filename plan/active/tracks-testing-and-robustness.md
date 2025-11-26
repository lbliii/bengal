# Tracks Feature: Testing & Robustness Analysis

**Status**: Draft  
**Created**: 2025-01-23  
**Related**: Tracks feature implementation

## Executive Summary

The tracks feature enables curated learning paths by combining multiple pages into sequential tracks. This document outlines required tests and robustness improvements needed for production readiness.

**Critical Gaps Identified**:
- ❌ No tests for tracks feature
- ❌ No validation of track data structure
- ❌ No error handling for missing pages
- ❌ No performance considerations for large tracks
- ⚠️ Potential memory issues with large track pages (parsed_ast/content)

---

## 1. Test Coverage Required

### 1.1 Unit Tests: `get_page()` Function

**File**: `tests/unit/rendering/test_template_functions_get_page.py`

**Test Cases**:

```python
class TestGetPageFunction:
    """Test get_page template function for track page resolution."""

    def test_get_page_by_relative_path(self, site_with_content):
        """Test resolving page by content-relative path."""
        # tracks.yaml uses: "docs/getting-started/installation.md"
        # Should resolve correctly

    def test_get_page_by_path_without_extension(self, site_with_content):
        """Test resolving page when .md extension omitted."""
        # "docs/getting-started/installation" should work

    def test_get_page_nonexistent_path(self, site_with_content):
        """Test None returned for non-existent pages."""
        # Should return None, not raise

    def test_get_page_empty_path(self, site_with_content):
        """Test empty path handling."""
        # Should return None

    def test_get_page_path_normalization(self, site_with_content):
        """Test Windows/Unix path separator normalization."""
        # "docs\\getting-started\\installation.md" should work

    def test_get_page_lookup_map_caching(self, site_with_content):
        """Test that lookup maps are cached on site object."""
        # Verify _page_lookup_maps is created and reused

    def test_get_page_with_content_prefix(self, site_with_content):
        """Test handling of 'content/' prefix in paths."""
        # Currently not supported, document limitation
```

### 1.2 Integration Tests: Track Rendering

**File**: `tests/integration/test_tracks_rendering.py`

**Test Cases**:

```python
class TestTrackRendering:
    """Integration tests for track page rendering."""

    def test_track_single_page_renders_all_sections(self, site_with_tracks):
        """Test that track single page renders all track items."""
        # Verify all sections appear in output

    def test_track_list_page_shows_all_tracks(self, site_with_tracks):
        """Test track list page displays all tracks."""
        # Verify all tracks from tracks.yaml appear

    def test_track_with_missing_page_shows_warning(self, site_with_tracks):
        """Test track with non-existent page shows appropriate message."""
        # Track item pointing to missing page should show warning

    def test_track_section_content_rendering(self, site_with_tracks):
        """Test that track section content renders correctly."""
        # Verify parsed_ast preferred, falls back to content

    def test_track_navigation_links(self, site_with_tracks):
        """Test track section navigation (prev/next) works."""
        # Verify anchor links (#track-section-N) work

    def test_track_sidebar_shows_other_tracks(self, site_with_tracks):
        """Test track sidebar lists other available tracks."""
        # Verify sidebar navigation

    def test_track_with_empty_items_list(self, site_with_tracks):
        """Test track with no items handles gracefully."""
        # Should not crash, show appropriate message

    def test_track_with_duplicate_items(self, site_with_tracks):
        """Test track with duplicate page references."""
        # Should handle gracefully (show same page twice?)
```

### 1.3 Data Loading Tests

**File**: `tests/unit/core/test_site_data_loading.py`

**Test Cases**:

```python
class TestSiteDataLoading:
    """Test site.data loading for tracks.yaml."""

    def test_tracks_yaml_loaded(self, site_with_tracks):
        """Test tracks.yaml is loaded into site.data.tracks."""
        assert hasattr(site.data, 'tracks')
        assert 'getting-started' in site.data.tracks

    def test_tracks_structure_validation(self, site_with_tracks):
        """Test track structure has required fields."""
        track = site.data.tracks['getting-started']
        assert 'title' in track
        assert 'items' in track
        assert isinstance(track['items'], list)

    def test_tracks_missing_yaml_handles_gracefully(self, site_without_tracks):
        """Test site without tracks.yaml doesn't crash."""
        # site.data.tracks should be empty dict or None

    def test_tracks_invalid_yaml_handles_gracefully(self, site_with_invalid_tracks):
        """Test invalid tracks.yaml doesn't crash build."""
        # Should log error, continue build
```

### 1.4 Edge Case Tests

**File**: `tests/integration/test_tracks_edge_cases.py`

**Test Cases**:

```python
class TestTracksEdgeCases:
    """Test edge cases and error conditions."""

    def test_track_item_path_with_spaces(self, site_with_tracks):
        """Test track items with spaces in path."""
        # "docs/getting started/installation.md"

    def test_track_item_path_absolute(self, site_with_tracks):
        """Test track items with absolute paths."""
        # Should handle or reject

    def test_track_item_path_outside_content(self, site_with_tracks):
        """Test track items pointing outside content/."""
        # Should handle gracefully

    def test_track_circular_reference(self, site_with_tracks):
        """Test track that references itself."""
        # Track page in its own items list

    def test_track_very_long_items_list(self, site_with_tracks):
        """Test track with 100+ items."""
        # Performance and rendering

    def test_track_items_with_special_characters(self, site_with_tracks):
        """Test track items with special chars in paths."""
        # Unicode, emoji, etc.

    def test_track_missing_track_id(self, site_with_tracks):
        """Test page with track template but no track_id."""
        # Should handle gracefully

    def test_track_id_mismatch(self, site_with_tracks):
        """Test page track_id doesn't match any track."""
        # Should show appropriate message
```

---

## 2. Robustness Concerns

### 2.1 Data Validation

**Problem**: No validation of `tracks.yaml` structure.

**Impact**:
- Invalid YAML crashes build
- Missing required fields cause template errors
- Invalid paths cause runtime errors

**Solution**:

```python
# bengal/core/site.py - _load_data_directory()
def _validate_tracks_structure(tracks_data: dict) -> dict:
    """Validate tracks.yaml structure."""
    validated = {}
    for track_id, track in tracks_data.items():
        if not isinstance(track, dict):
            logger.warning("invalid_track_structure", track_id=track_id)
            continue

        # Required fields
        if 'items' not in track:
            logger.warning("track_missing_items", track_id=track_id)
            continue

        if not isinstance(track['items'], list):
            logger.warning("track_items_not_list", track_id=track_id)
            continue

        validated[track_id] = track

    return validated
```

### 2.2 Missing Page Handling

**Problem**: Track items may reference non-existent pages.

**Current State**: Template shows warning, but no validation during build.

**Solution**: Add validation phase:

```python
# bengal/health/validators/track_validator.py
class TrackValidator:
    """Validate track definitions."""

    def validate_track_items(self, site: Site) -> list[dict]:
        """Validate all track items exist."""
        issues = []

        if not hasattr(site.data, 'tracks'):
            return issues

        for track_id, track in site.data.tracks.items():
            for item_path in track.get('items', []):
                page = get_page(item_path)  # Use same logic as template
                if not page:
                    issues.append({
                        'type': 'missing_track_item',
                        'track_id': track_id,
                        'item_path': item_path,
                        'severity': 'warning'
                    })

        return issues
```

### 2.3 Performance: Large Tracks

**Problem**: Rendering track single page loads all track item content into memory.

**Impact**:
- Large tracks (50+ pages) cause memory spikes
- Slow rendering for tracks with many items
- No pagination or lazy loading

**Solutions**:

**Option A: Content Limits**
```jinja2
{# Limit content preview in track sections #}
{% if loop.index <= 10 %}
    {{ item_page.content | safe }}
{% else %}
    <div class="track-section-preview">
        <p>{{ item_page.description or 'View full page for content.' }}</p>
        <a href="{{ item_page.url }}">Read Full Article →</a>
    </div>
{% endif %}
```

**Option B: Lazy Content Loading**
- Only render first N sections fully
- Others show preview + link
- Configurable via `bengal.toml`:
```toml
[tracks]
max_sections_full_content = 10
preview_mode = "description"  # or "excerpt" or "none"
```

**Option C: Pagination**
- Split long tracks into multiple pages
- "Track Part 1", "Track Part 2", etc.

### 2.4 Memory: parsed_ast vs content

**Problem**: Track template uses `parsed_ast` if available, falls back to `content`. Both can be large.

**Current Code**:
```jinja2
{% if item_page.parsed_ast %}
    {{ item_page.parsed_ast | safe }}
{% elif item_page.content %}
    {{ item_page.content | safe }}
```

**Concerns**:
- `parsed_ast` may be HTML string (large)
- `content` is raw markdown (smaller but needs parsing)
- No size limits

**Solution**: Add content size checks:

```python
# In template or validator
MAX_TRACK_SECTION_SIZE = 100_000  # 100KB

def should_render_full_content(page: Page) -> bool:
    """Check if page content is small enough to render inline."""
    if hasattr(page, 'parsed_ast') and page.parsed_ast:
        size = len(str(page.parsed_ast))
    elif hasattr(page, 'content') and page.content:
        size = len(str(page.content))
    else:
        return False

    return size < MAX_TRACK_SECTION_SIZE
```

### 2.5 Path Resolution Robustness

**Problem**: `get_page()` has multiple lookup strategies but no comprehensive tests.

**Edge Cases**:
1. Paths with/without `.md` extension
2. Windows vs Unix path separators
3. Paths outside `content/` directory
4. Relative paths (`../other-section/page.md`)
5. Absolute paths (should be rejected)

**Solution**: Enhance `get_page()` with validation:

```python
def get_page(path: str) -> Page | None:
    """Get page with robust path validation."""
    if not path:
        return None

    # Reject absolute paths
    if Path(path).is_absolute():
        logger.warning("get_page_absolute_path", path=path)
        return None

    # Reject paths outside content/
    if path.startswith('../') or '/../' in path:
        logger.warning("get_page_path_traversal", path=path)
        return None

    # ... existing lookup logic ...
```

### 2.6 Template Error Handling

**Problem**: Template errors in track rendering can crash entire build.

**Current State**: Jinja2 errors propagate up.

**Solution**: Add error boundaries in templates:

```jinja2
{# Wrap track section rendering in error handling #}
{% for item_slug in track.items %}
    {% try %}
        {% set item_page = get_page(item_slug) %}
        {# ... render section ... #}
    {% except %}
        <div class="alert alert-danger">
            <p><strong>Error rendering track section</strong></p>
            <p>Item: {{ item_slug }}</p>
            <p>Error: {{ exception }}</p>
        </div>
    {% endtry %}
{% endfor %}
```

**Note**: Jinja2 doesn't have `{% try %}`. Use Python-level error handling instead.

### 2.7 Track ID Resolution

**Problem**: Track ID resolution logic is duplicated:

```jinja2
{% set track_id = page.metadata.get('track_id') or page.slug %}
```

**Issues**:
- Logic duplicated in multiple templates
- No validation that track_id exists
- No fallback handling

**Solution**: Create template macro:

```jinja2
{# partials/track_helpers.html #}
{% macro get_track_id(page) %}
    {% set track_id = page.metadata.get('track_id') or page.slug %}
    {% if site.data.tracks and track_id in site.data.tracks %}
        {{ track_id }}
    {% else %}
        {{ none }}
    {% endif %}
{% endmacro %}
```

---

## 3. Long-Term Maintenance

### 3.1 Documentation

**Required**:
- [ ] API documentation for `get_page()` function
- [ ] Track data structure schema documentation
- [ ] Troubleshooting guide for common track issues
- [ ] Performance tuning guide for large tracks

### 3.2 Monitoring & Observability

**Add Logging**:
```python
# Track when pages can't be resolved
logger.warning("track_item_not_found",
    track_id=track_id,
    item_path=item_path,
    available_pages=[p.relative_path for p in site.pages[:10]]
)

# Track performance
logger.debug("track_rendering_time",
    track_id=track_id,
    item_count=len(track.items),
    render_time_ms=elapsed_ms
)
```

### 3.3 Backward Compatibility

**Considerations**:
- Track structure changes (add new fields)
- Path format changes (relative vs absolute)
- Template API changes (`get_page()` signature)

**Solution**: Version tracks.yaml:

```yaml
# tracks.yaml
_version: "1.0"
getting-started:
  title: "Bengal Essentials"
  # ...
```

### 3.4 Migration Path

**If tracks structure changes**:
- Provide migration script
- Support both old and new formats during transition
- Clear deprecation warnings

---

## 4. Implementation Priority

### Phase 1: Critical (Immediate)
1. ✅ Fix template content rendering (already done)
2. ⚠️ Add `get_page()` unit tests
3. ⚠️ Add track rendering integration tests
4. ⚠️ Add missing page validation

### Phase 2: Important (Next Sprint)
5. Add track data structure validation
6. Add error handling for template failures
7. Add performance limits for large tracks
8. Add comprehensive logging

### Phase 3: Nice to Have (Future)
9. Add track pagination
10. Add track preview modes
11. Add track analytics/monitoring
12. Add track migration tools

---

## 5. Test Fixtures Needed

### 5.1 `site_with_tracks` Fixture

```python
@pytest.fixture
def site_with_tracks(tmp_path):
    """Create site with tracks.yaml and track content."""
    # Create tracks.yaml
    tracks_yaml = tmp_path / "data" / "tracks.yaml"
    tracks_yaml.parent.mkdir(parents=True)
    tracks_yaml.write_text("""
getting-started:
  title: "Getting Started"
  items:
    - docs/getting-started/page1.md
    - docs/getting-started/page2.md
""")

    # Create track pages
    content_dir = tmp_path / "content" / "docs" / "getting-started"
    content_dir.mkdir(parents=True)
    (content_dir / "page1.md").write_text("# Page 1")
    (content_dir / "page2.md").write_text("# Page 2")

    # Create track landing page
    track_page = tmp_path / "content" / "tracks" / "getting-started.md"
    track_page.parent.mkdir(parents=True)
    track_page.write_text("""---
title: Getting Started Track
template: tracks/single.html
track_id: getting-started
---
# Getting Started Track
""")

    # Build site
    site = Site(root_path=tmp_path)
    # ... build process ...
    return site
```

### 5.2 `site_without_tracks` Fixture

```python
@pytest.fixture
def site_without_tracks(tmp_path):
    """Create site without tracks.yaml."""
    # Just content, no tracks
    return Site(root_path=tmp_path)
```

### 5.3 `site_with_invalid_tracks` Fixture

```python
@pytest.fixture
def site_with_invalid_tracks(tmp_path):
    """Create site with invalid tracks.yaml."""
    tracks_yaml = tmp_path / "data" / "tracks.yaml"
    tracks_yaml.parent.mkdir(parents=True)
    tracks_yaml.write_text("""
invalid:
  # Missing 'items' field
  title: "Invalid Track"
""")
    return Site(root_path=tmp_path)
```

---

## 6. Checklist

### Testing
- [ ] Unit tests for `get_page()` function
- [ ] Integration tests for track rendering
- [ ] Edge case tests
- [ ] Performance tests for large tracks
- [ ] Error handling tests

### Robustness
- [ ] Track data validation
- [ ] Missing page handling
- [ ] Path resolution edge cases
- [ ] Template error handling
- [ ] Memory limits for large content

### Documentation
- [ ] Track data structure docs
- [ ] `get_page()` API docs
- [ ] Troubleshooting guide
- [ ] Performance tuning guide

### Monitoring
- [ ] Logging for track issues
- [ ] Performance metrics
- [ ] Error tracking

---

## 7. Related Files

**Implementation**:
- `bengal/bengal/themes/default/templates/tracks/single.html`
- `bengal/bengal/themes/default/templates/tracks/list.html`
- `bengal/bengal/rendering/template_functions/get_page.py`
- `bengal/bengal/core/site.py` (data loading)

**Test Files to Create**:
- `tests/unit/rendering/test_template_functions_get_page.py`
- `tests/integration/test_tracks_rendering.py`
- `tests/integration/test_tracks_edge_cases.py`
- `tests/unit/core/test_site_data_loading.py`

**Documentation**:
- `site/content/docs/guides/curated-tracks.md` (already exists)
- `site/content/docs/reference/tracks-api.md` (to create)
- `site/content/docs/troubleshooting/tracks.md` (to create)

---

## Next Steps

1. **Immediate**: Create test files and fixtures
2. **This Week**: Implement critical robustness improvements
3. **Next Sprint**: Add performance optimizations
4. **Ongoing**: Monitor and iterate based on usage
