# Cohesive URL Strategy for Multi-Deployment Support

**Status**: Active  
**Created**: 2025-10-18  
**Goal**: Establish consistent URL handling across all deployment scenarios

## Deployment Scenarios

Bengal must support these deployment contexts with different URL requirements:

| Scenario | Base URL Example | URL Type | Notes |
|----------|-----------------|----------|-------|
| **Local dev server** | `http://localhost:5000/` | Root domain | No baseurl needed |
| **Offline file system** | `file:///Users/me/site/` | Absolute file path | Special case, baseurl = `file:///Users/me/site` |
| **GitHub Pages (repo)** | `https://user.github.io/repo/` | Subpath | baseurl = `/repo` |
| **GitHub Pages (org)** | `https://org.github.io/` | Root domain | No baseurl needed |
| **Vercel/Netlify** | `https://site.vercel.app/` | Root domain | No baseurl needed |
| **Custom domain** | `https://example.com/` | Root domain | No baseurl needed |
| **Custom subpath** | `https://example.com/blog/` | Subpath | baseurl = `/blog` |
| **AWS Amplify** | `https://branch.app.amplify.aws/` | Root domain | No baseurl needed |

## URL Types in Bengal

### 1. **Relative URLs** (internal representation)
- Format: `/about/`, `/docs/getting-started/`
- Used by: `Page.url`, `Section.url` properties
- Purpose: Canonical form, baseurl-agnostic
- **Where**: Core data model (`bengal/core/page`, `bengal/core/section`)

### 2. **Path URLs** (with baseurl prefix)
- Format: `/repo/about/`, `/blog/docs/getting-started/`
- Used by: HTML `<a href>`, CSS/JS src attributes
- Purpose: Navigation links that work in subpath deployments
- **Where**: Template functions, `url_for()`, HTML output

### 3. **Absolute URLs** (full domain + baseurl + path)
- Format: `https://example.com/repo/about/`
- Used by: RSS feeds, sitemaps, canonical URLs, OpenGraph
- Purpose: External references that need full URLs
- **Where**: SEO functions, RSS/sitemap generation

## Current State Analysis

### ✅ **Correctly Handled**

1. **`url_for(page)` global function** - Applies baseurl
   - `page.url` → `/about/`
   - `url_for(page)` → `/repo/about/` (with baseurl)

2. **`absolute_url` filter** - Applies baseurl + handles absolute URLs
   - `page.url | absolute_url` → `https://example.com/repo/about/`

3. **SEO functions** - Apply baseurl for canonical/OG URLs
   - `canonical_url()`, `og_image()`

4. **Taxonomy functions** - Apply baseurl
   - `tag_url()` returns `/repo/tags/python/`

5. **Crossref functions** - Apply baseurl
   - `ref()`, `anchor()`, `relref()`

6. **Asset URLs** - Apply baseurl via `_asset_url()`

### ❌ **Inconsistently Handled**

1. **Navigation data functions** - Return raw `page.url` without baseurl
   - `get_breadcrumbs()` → URLs like `/docs/`
   - `get_nav_tree()` → URLs like `/about/`
   - `get_pagination_items()` → URLs like `/blog/page/2/`
   - `get_auto_nav()` → URLs like `/docs/`

   **Template burden**: Must use `url_for()` or manually apply baseurl
   ```jinja2
   {% for item in get_breadcrumbs(page) %}
     <a href="{{ url_for(item.url) }}">{{ item.title }}</a>  {# Won't work - item.url is string #}
   {% endfor %}
   ```

2. **Image functions** - Sometimes apply baseurl, sometimes don't
   - `image_url()` accepts `base_url` parameter but doesn't use it consistently

## The Core Problem

**Inconsistency**: Some functions pre-process URLs (add baseurl), others don't.

**Template Confusion**: Authors must know which functions need help:
```jinja2
{# Breadcrumbs - URL is raw, but no way to apply url_for() to string #}
<a href="{{ item.url }}">{{ item.title }}</a>  {# Broken in GitHub Pages! #}

{# Tag URL - already has baseurl applied #}
<a href="{{ tag_url(tag) }}">{{ tag }}</a>  {# Works everywhere #}
```

## Proposed Solution: Two-Tier URL System

### **Tier 1: Core Data Model** (baseurl-free)
**Properties on `Page`, `Section`, and related objects**

- `page.url` → `/about/`
- `section.url` → `/docs/`
- `page.next.url` → `/blog/post-2/`

**Purpose**: Canonical representation, used internally

**Rule**: These properties NEVER include baseurl

### **Tier 2: Template-Facing Functions** (baseurl-applied)

**All functions that return URLs for templates MUST apply baseurl**

#### **A. Data Functions** (return structures with URLs)
- `get_breadcrumbs(page)` → URLs with baseurl
- `get_nav_tree(page)` → URLs with baseurl
- `get_pagination_items()` → URLs with baseurl
- `get_auto_nav()` → URLs with baseurl

**Template usage** (no baseurl handling needed):
```jinja2
{% for item in get_breadcrumbs(page) %}
  <a href="{{ item.url }}">{{ item.title }}</a>
{% endfor %}
```

#### **B. Rendering Functions** (return HTML or URLs)
- `ref(path)` → Returns HTML with baseurl'd URL
- `tag_url(tag)` → Returns URL with baseurl
- `canonical_url()` → Returns absolute URL
- `og_image()` → Returns absolute URL

**Template usage** (already works):
```jinja2
{{ ref("my-page") }}
<a href="{{ tag_url('python') }}">Python</a>
```

#### **C. Utility Functions** (explicit baseurl handling)
- `url_for(page)` → Applies baseurl to page object
- `absolute_url` filter → Applies baseurl + domain to any URL
- `with_baseurl(path)` → Helper to apply baseurl to string path

## Implementation Strategy

### Phase 1: Add `with_baseurl()` utility
Create a shared helper in `bengal/rendering/template_functions/urls.py`:

```python
def with_baseurl(path: str, baseurl: str) -> str:
    """
    Apply baseurl prefix to a path.

    Handles:
    - Path-only baseurl: /repo -> /repo/about/
    - Absolute baseurl: https://site.com -> https://site.com/about/
    - File baseurl: file:///path -> file:///path/about/
    """
    if not path.startswith("/"):
        path = "/" + path

    if not baseurl:
        return path

    baseurl = baseurl.rstrip("/")

    # Absolute baseurl (http://, https://, file://)
    if baseurl.startswith(("http://", "https://", "file://")):
        return f"{baseurl}{path}"

    # Path-only baseurl
    base_path = "/" + baseurl.lstrip("/")
    return f"{base_path}{path}"
```

### Phase 2: Update navigation functions
Modify each function to apply baseurl before returning:

```python
# bengal/rendering/template_functions/navigation.py

def register(env: "Environment", site: "Site") -> None:
    """Register navigation functions with Jinja2 environment."""

    # Import shared utility
    from .urls import with_baseurl

    baseurl = site.config.get("baseurl", "") or ""

    # Wrap functions with baseurl application
    def get_breadcrumbs_with_baseurl(page):
        items = get_breadcrumbs(page)
        # Apply baseurl to each item's URL
        for item in items:
            item["url"] = with_baseurl(item["url"], baseurl)
        return items

    env.globals.update({
        "get_breadcrumbs": get_breadcrumbs_with_baseurl,
        "get_toc_grouped": get_toc_grouped,  # No URLs
        "get_pagination_items": lambda *args, **kwargs: apply_baseurl_to_pagination(
            get_pagination_items(*args, **kwargs), baseurl
        ),
        "get_nav_tree": lambda page: apply_baseurl_to_nav_tree(
            get_nav_tree(page), baseurl
        ),
        "get_auto_nav": lambda: apply_baseurl_to_auto_nav(
            get_auto_nav(site), baseurl
        ),
    })
```

### Phase 3: Consolidate baseurl logic
Remove duplicate baseurl application code from:
- `taxonomies.py` - use shared `with_baseurl()`
- `crossref.py` - use shared `with_baseurl()`
- `seo.py` - use shared `with_baseurl()`
- `images.py` - use shared `with_baseurl()`

### Phase 4: Update templates
Remove any manual baseurl handling from templates:

**Before**:
```jinja2
{# Manual baseurl handling #}
<a href="{{ site.baseurl }}{{ item.url }}">{{ item.title }}</a>
```

**After**:
```jinja2
{# Baseurl already applied #}
<a href="{{ item.url }}">{{ item.title }}</a>
```

### Phase 5: Add tests
Test all deployment scenarios:

```python
@pytest.mark.parametrize("baseurl,expected", [
    ("", "/about/"),
    ("/repo", "/repo/about/"),
    ("/blog", "/blog/about/"),
    ("https://example.com", "https://example.com/about/"),
    ("file:///Users/me/site", "file:///Users/me/site/about/"),
])
def test_navigation_urls_with_baseurl(baseurl, expected):
    site = create_test_site(baseurl=baseurl)
    breadcrumbs = get_breadcrumbs(page)
    assert breadcrumbs[0]["url"] == expected
```

## Benefits

### ✅ **Consistency**
- All template functions behave the same way
- One rule: "URLs from functions have baseurl applied"

### ✅ **Simplicity**
- Template authors never think about baseurl
- No need to remember which functions need help

### ✅ **Deployment Flexibility**
- Change baseurl in config → works everywhere
- Same templates work for all deployment scenarios

### ✅ **SEO/RSS Compatibility**
- Absolute URLs built on top of baseurl'd paths
- `absolute_url` filter adds domain to any path

### ✅ **Offline Support**
- `file:///` baseurl works transparently
- No special cases in templates

## Migration Guide

### For Theme Authors

**Before** (inconsistent):
```jinja2
{# Some functions need help, some don't #}
{% for item in get_breadcrumbs(page) %}
  <a href="{{ item.url }}">{{ item.title }}</a>  {# Broken! #}
{% endfor %}

<a href="{{ tag_url('python') }}">Python</a>  {# Works! #}
```

**After** (consistent):
```jinja2
{# All functions work the same #}
{% for item in get_breadcrumbs(page) %}
  <a href="{{ item.url }}">{{ item.title }}</a>  {# Works! #}
{% endfor %}

<a href="{{ tag_url('python') }}">Python</a>  {# Still works! #}
```

### For Advanced Users

If you need raw URLs without baseurl for some reason:
```jinja2
{# Access raw page.url property #}
{{ page.url }}  {# /about/ without baseurl #}

{# Use url_for() to apply baseurl #}
{{ url_for(page) }}  {# /repo/about/ with baseurl #}
```

## Testing Matrix

| Deployment | Config | Link Test | RSS Test | Asset Test |
|------------|--------|-----------|----------|------------|
| Local dev | `baseurl = ""` | `/about/` works | `http://localhost:5000/about/` | `/assets/style.css` |
| GitHub Pages | `baseurl = "/repo"` | `/repo/about/` works | `https://user.github.io/repo/about/` | `/repo/assets/style.css` |
| Vercel | `baseurl = ""` | `/about/` works | `https://site.vercel.app/about/` | `/assets/style.css` |
| Offline | `baseurl = "file:///path"` | `file:///path/about/` | Not applicable | `file:///path/assets/style.css` |
| Custom subpath | `baseurl = "/blog"` | `/blog/about/` works | `https://example.com/blog/about/` | `/blog/assets/style.css` |

## Decision: APPROVED

**Implementation Priority**: HIGH  
**Breaking Change**: NO (templates without manual baseurl handling continue working)  
**Migration Required**: Only for templates with manual baseurl concatenation  
**Timeline**: Can be implemented incrementally, function by function

## Next Steps

1. ✅ Document strategy (this file)
2. ⏳ Implement `with_baseurl()` shared utility
3. ⏳ Update `get_breadcrumbs()` to apply baseurl
4. ⏳ Update remaining navigation functions
5. ⏳ Consolidate baseurl logic across all modules
6. ⏳ Add comprehensive tests
7. ⏳ Update default theme templates
8. ⏳ Add migration guide to docs
