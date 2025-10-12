# Template Attribute Access Fix

**Date:** 2025-10-12  
**Status:** ✅ Complete  
**Impact:** Critical - Fixed template rendering errors across all reference docs and special pages

## Problem

Multiple template rendering failures were occurring due to unsafe attribute access:

### Error 1: List Templates (api-reference, cli-reference, tutorial, doc)
```
error='dict object' has no attribute 'image'
```
- Occurred in `api-reference/list.html`, `cli-reference/list.html`, `tutorial/list.html`, `doc/list.html`
- All templates extend `base.html` which was accessing `page.metadata.image` unsafely
- Affected 14+ archive pages

### Error 2: Special Pages (404, search)
```
error='types.SimpleNamespace object' has no attribute 'keywords'
```
- Special pages use `SimpleNamespace` for page context instead of full `Page` objects
- Missing `keywords` attribute caused template failures
- Both 404.html and search.html failed to generate

## Root Causes

1. **Unsafe Attribute Access in base.html**
   - Line 18: `page.keywords` - Not all page objects have this attribute
   - Line 34: `page.metadata.image` - Dict access without existence check
   - Line 46: `page.metadata.image` - Same issue for Twitter cards
   - Line 94: `page.kind`, `page.draft`, `page.tags` - Missing on SimpleNamespace

2. **Incomplete SimpleNamespace in special_pages.py**
   - 404 page context missing `keywords` attribute
   - Search page context missing `keywords` attribute
   - Both missing other optional attributes used in base.html

## Solution

### 1. Fixed base.html Template (4 changes)

**Line 18-22: Safe keyword access**
```jinja2
{# Before #}
{% if page and page.keywords %}

{# After #}
{% if page and page.keywords is defined and page.keywords %}
```

**Line 34-38: Safe metadata.image access**
```jinja2
{# Before #}
{% if page and page.metadata.image %}
<meta property="og:image" content="{{ og_image(page.metadata.image) }}">

{# After #}
{% if page and page.metadata is defined and page.metadata.get('image') %}
<meta property="og:image" content="{{ og_image(page.metadata.get('image')) }}">
```

**Line 46-50: Safe Twitter image access**
```jinja2
{# Before #}
{% if page and page.metadata.image %}
<meta name="twitter:image" content="{{ og_image(page.metadata.image) }}">

{# After #}
{% if page and page.metadata is defined and page.metadata.get('image') %}
<meta name="twitter:image" content="{{ og_image(page.metadata.get('image')) }}">
```

**Line 94: Safe body class attributes**
```jinja2
{# Before #}
<body class="page-kind-{{ page.kind }} {% if page.draft %}draft-page{% endif %} {% if page | has_tag('featured') %}featured-content{% endif %}">

{# After #}
<body class="page-kind-{{ page.kind if page and page.kind is defined else 'page' }} {% if page and page.draft is defined and page.draft %}draft-page{% endif %} {% if page and page.tags is defined and (page | has_tag('featured')) %}featured-content{% endif %}">
```

### 2. Enhanced special_pages.py (2 changes)

**404 Page Context (Line 103-112)**
```python
# Added 'keywords' attribute
page_context = SimpleNamespace(
    title="Page Not Found",
    url="/404.html",
    kind="page",
    draft=False,
    metadata={},
    tags=[],
    keywords=[],  # NEW
    content="",
)
```

**Search Page Context (Line 198-207)**
```python
# Added 'keywords' attribute
page_context = SimpleNamespace(
    title="Search",
    url=raw_path,
    kind="page",
    draft=False,
    metadata={"search_exclude": True},
    tags=[],
    keywords=[],  # NEW
    content="",
)
```

## Files Modified

1. `/bengal/themes/default/templates/base.html` - Fixed unsafe attribute access
2. `/bengal/postprocess/special_pages.py` - Added missing keywords attribute

## Verification

Build test completed successfully:
```bash
$ python -m bengal build examples/showcase
✨ Built 295 pages in 3.0s
```

- ✅ All 14 archive list pages render correctly
- ✅ 404.html generates successfully
- ✅ search.html generates successfully
- ✅ No template rendering errors
- ✅ No undefined variable warnings

## Impact

- **Before:** 16 pages failed to render (14 archives + 404 + search)
- **After:** All 295 pages render successfully
- **Build time:** 3.0s (no performance impact)

## Best Practices Established

### Template Safety Patterns

1. **Always use `is defined` for optional attributes:**
   ```jinja2
   {% if page and page.optional_attr is defined and page.optional_attr %}
   ```

2. **Use `.get()` for dictionary access:**
   ```jinja2
   {% if page.metadata is defined and page.metadata.get('key') %}
   ```

3. **Provide defaults for required attributes:**
   ```jinja2
   {{ page.kind if page and page.kind is defined else 'page' }}
   ```

### SimpleNamespace Requirements

When creating page-like contexts with `SimpleNamespace`, include all attributes that `base.html` expects:
- `title` (required)
- `url` (required)
- `kind` (required, default: 'page')
- `draft` (required, default: False)
- `metadata` (required, default: {})
- `tags` (required, default: [])
- `keywords` (required, default: [])
- `content` (required, default: "")

## Related Issues

This fix resolves the template chain errors that were preventing:
- API reference archive pages from rendering
- CLI reference archive pages from rendering
- Tutorial archive pages from rendering
- Documentation archive pages from rendering
- 404 error page generation
- Search page generation

## Testing Recommendations

Before deploying template changes:
1. Test with full site build (`bengal build`)
2. Verify special pages generate (404.html, search.html)
3. Check archive/list pages in all content types
4. Review build logs for any undefined variable warnings

## Notes

- Jinja2 supports dot notation for dictionary access, but explicit `.get()` is safer
- The `is defined` test prevents AttributeError on SimpleNamespace objects
- These patterns should be applied to all theme templates for consistency
