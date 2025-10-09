# What Needs to Change for Static File Serving

## The Problem

When you **click on an HTML file** or **open with "Run Live Server"**, Bengal SSG sites don't work because:

```html
<!-- Current output in index.html -->
<link rel="stylesheet" href="/assets/css/style.css">
<a href="/" class="logo">Bengal SSG</a>
<a href="/docs/">Documentation</a>
```

All URLs start with `/` (absolute paths). This breaks because:

1. **File:// protocol** (double-clicking HTML):
   - `/assets/css/style.css` → looks for `file:///assets/css/style.css` (filesystem root)
   - Should be: `assets/css/style.css` (relative to the HTML file)

2. **VS Code Live Server**:
   - Serves at `http://127.0.0.1:5500/public/index.html`
   - `/assets/css/style.css` → looks for `http://127.0.0.1:5500/assets/css/style.css`
   - Should be: `assets/css/style.css` or `http://127.0.0.1:5500/public/assets/css/style.css`

## The Solution: Relative URLs

Generate URLs **relative to the current page**:

```html
<!-- From index.html -->
<link rel="stylesheet" href="assets/css/style.css">
<a href="index.html" class="logo">Bengal SSG</a>
<a href="docs/index.html">Documentation</a>

<!-- From docs/index.html -->
<link rel="stylesheet" href="../assets/css/style.css">
<a href="../index.html" class="logo">Bengal SSG</a>
<a href="index.html">Documentation</a>

<!-- From docs/guide/installation.html -->
<link rel="stylesheet" href="../../assets/css/style.css">
<a href="../../index.html" class="logo">Bengal SSG</a>
<a href="../index.html">Documentation</a>
```

## Required Changes

### 1. Configuration Option (User-Facing)

Add to `bengal.toml`:

```toml
[build]
relative_urls = true  # Enable relative URLs for portable sites
```

### 2. Core Changes (Code)

#### A. New URL Helper Module
**File:** `bengal/utils/url_helpers.py`

Creates `make_relative_url(from_path, to_path)` function that calculates relative paths.

#### B. Template Engine Updates
**File:** `bengal/rendering/template_engine.py`

- Pass current page URL to template context
- Update `_asset_url()` to generate relative paths when enabled
- Update `_get_menu()` to convert menu URLs to relative

#### C. Page URL Generation
**File:** `bengal/core/page.py`

- Keep `page.url` as absolute path (source of truth)
- Add method to convert to relative on-demand

#### D. Template Functions
Update all URL-generating functions:
- **crossref.py**: `ref()`, `relref()`, `anchor()`
- **taxonomies.py**: `tag_url()`
- **pagination_helpers.py**: `page_url()`
- **images.py**: `image_url()` (when not using baseurl)

#### E. Templates
**Files:** `bengal/themes/default/templates/*.html`

- RSS feed link: `{{ asset_url('rss.xml') }}`
- All hardcoded URLs updated to use template functions

### 3. Special Cases to Handle

#### SEO Meta Tags (Always Absolute)
These MUST remain absolute with full domain:

```html
<!-- Always use baseurl, ignore relative_urls -->
<link rel="canonical" href="https://example.com/docs/">
<meta property="og:url" content="https://example.com/docs/">
<meta property="og:image" content="https://example.com/assets/hero.jpg">
```

Social media crawlers and search engines require full URLs.

#### Edge Cases
- Empty URLs (`/` → `index.html`)
- Anchors (`/docs/#installation` → `docs/index.html#installation`)
- External links (unchanged)
- Asset URLs in CSS (already relative by default)

## How It Works

### URL Calculation Algorithm

```python
def make_relative_url(from_url: str, to_url: str) -> str:
    """
    Calculate relative path between two URLs.
    
    Example:
        from_url = "/docs/guide/"
        to_url = "/assets/style.css"
        result = "../../assets/style.css"
    """
    # 1. Parse URLs to path components
    from_parts = [p for p in from_url.split('/') if p]
    to_parts = [p for p in to_url.split('/') if p]
    
    # 2. Find common prefix
    common = 0
    for f, t in zip(from_parts, to_parts):
        if f == t:
            common += 1
        else:
            break
    
    # 3. Calculate ups (..)
    ups = len(from_parts) - common
    
    # 4. Calculate remaining path
    remaining = to_parts[common:]
    
    # 5. Build relative URL
    return '../' * ups + '/'.join(remaining)
```

### Render-Time Context

Every page render needs to know "where am I?":

```python
# In template_engine.render()
context = {
    'page': page,
    'site': site,
    'current_url': page.url,  # NEW: needed for relative URL calculation
}

template.render(context)
```

Template functions can then use `current_url` to calculate relative paths.

## Benefits

✅ **Works everywhere:**
- Double-click HTML files
- VS Code Live Server
- Any local file server
- Subdirectory deployments
- USB drives / offline docs

✅ **Backward compatible:**
- Default is `relative_urls = false` (current behavior)
- Existing sites unaffected

✅ **SEO preserved:**
- Canonical URLs still absolute
- Social meta tags still absolute

## Trade-offs

⚠️ **Slightly larger HTML:**
- More `../` in deeply nested pages
- Minimal impact (~50-200 bytes per page)

⚠️ **Computation cost:**
- Relative path calculation on every render
- Negligible performance impact (simple string operations)

⚠️ **Can't use root paths:**
- Can't write `<a href="/">` in custom HTML
- Must use template functions: `<a href="{{ '/' | page_url }}">`

## Testing

### Validation Checklist

After building with `relative_urls = true`:

1. ✅ Double-click `public/index.html` - everything loads
2. ✅ Click through all navigation - no broken links
3. ✅ CSS/JS/images all load correctly
4. ✅ Works in nested pages (3+ levels deep)
5. ✅ Tag/category pages work
6. ✅ RSS feed link works
7. ✅ Canonical URLs still absolute in HTML

### Test Commands

```bash
# Build with relative URLs
cd examples/showcase
# Edit bengal.toml: relative_urls = true
bengal build

# Test 1: Open directly
open public/index.html

# Test 2: Live Server
cd public
python -m http.server 8000
# Visit http://localhost:8000/

# Test 3: Subdirectory
mkdir -p /tmp/subdir/site
cp -r public/* /tmp/subdir/site/
cd /tmp/subdir/site
python -m http.server 8000
# Visit http://localhost:8000/ - should work
```

## Migration Guide for Users

### For New Sites
```toml
[build]
relative_urls = true  # Recommended for portable sites
```

### For Existing Production Sites
```toml
[build]
relative_urls = false  # Keep absolute paths (default)
```

Use absolute paths if:
- Site deployed to domain root
- Using CDN
- Need cleaner URLs in HTML source

Use relative paths if:
- Creating documentation for distribution
- Want offline-capable sites
- Deploying to unknown subdirectories
- Users will download and open locally

## Implementation Status

- ✅ Problem analysis complete
- ✅ Solution designed
- ⬜ Core URL helpers implementation
- ⬜ Template engine updates
- ⬜ Template function updates
- ⬜ Testing
- ⬜ Documentation

**See:** `RELATIVE_URLS_IMPLEMENTATION.md` for detailed implementation plan.

