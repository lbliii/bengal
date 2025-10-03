# Jinja2 Preprocessing Fix

## Issue
Build was failing with "Unrendered Jinja2 syntax" health check error for `api/v2/_index/index.html`. The page used cascade metadata with Jinja2 template variables in markdown content, but the variables weren't being rendered.

## Root Cause
The Jinja2 preprocessing feature in `bengal/rendering/pipeline.py` was already implemented and working correctly. However, documentation pages that show Jinja2 syntax examples (like `template-system.md`) were causing preprocessing errors because they contained unmatched Jinja2 control structures.

## Solutions Implemented

### 1. Added Preprocessing Control (pipeline.py)
Added ability to disable Jinja2 preprocessing on a per-page basis using frontmatter:

```python
# Skip preprocessing if disabled in frontmatter
if page.metadata.get('preprocess') is False:
    return page.content
```

This allows documentation pages that show Jinja2 syntax examples to opt-out of preprocessing.

### 2. Fixed Documentation Page (template-system.md)
- Added `preprocess: false` to frontmatter to disable preprocessing
- Fixed empty Jinja2 braces `{{ }}` → `{{ '{{ }}' }}`
- Escaped unmatched control structures for documentation purposes

### 3. Verified Cascade Metadata Feature
Confirmed that cascade metadata from section `_index.md` files is properly:
- Applied to descendant pages during site initialization
- Accessible via `{{ page.metadata.xxx }}` in markdown content
- Rendered through Jinja2 preprocessing before markdown parsing

## Test Case
The `api/v2/_index.md` file demonstrates the feature:

**Frontmatter (cascade metadata):**
```yaml
cascade:
  product_name: "DataFlow API"
  product_version: "2.0"
  api_base_url: "https://api.dataflow.example.com/v2"
  release_date: "2025-10-01"
  requires_auth: true
```

**Markdown content:**
```markdown
Welcome to the {{ page.metadata.product_name }} {{ page.metadata.product_version }} documentation.

Released {{ page.metadata.release_date }}, this version includes significant improvements.

{% if page.metadata.requires_auth %}
**Note:** All API requests require authentication.
{% endif %}
```

**Rendered output:**
```html
<p>Welcome to the DataFlow API 2.0 documentation.</p>
<p>Released 2025-10-01, this version includes significant improvements.</p>
<p><strong>Note:</strong> All API requests require authentication.</p>
```

## Build Status
✅ Build completes successfully with no errors or warnings
✅ All Jinja2 variables are properly rendered
✅ Cascade metadata propagates correctly through section hierarchy
✅ Documentation pages with Jinja2 examples work with preprocessing disabled

## Files Modified
1. `bengal/rendering/pipeline.py` - Added `preprocess: false` support
2. `examples/quickstart/content/docs/template-system.md` - Added `preprocess: false` and fixed syntax errors

## Next Steps
- Consider documenting the `preprocess: false` frontmatter option in user documentation
- Consider adding this to the template system reference guide

