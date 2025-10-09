# Relative URLs Implementation Plan

## Problem Statement

Bengal SSG currently generates **absolute paths** (starting with `/`) for all URLs:
- Page URLs: `/docs/`, `/api/`
- Asset URLs: `/assets/css/style.css`
- Menu URLs: `/`, `/docs/`
- Tag URLs: `/tags/python/`
- RSS feed: `/rss.xml`

These absolute paths **fail** when:
1. **Opening HTML files directly** (`file://` protocol) - the `/` refers to filesystem root, not site root
2. **VS Code Live Server** - may serve from wrong base directory
3. **Static hosting in subdirectories** - site deployed at `/subdomain/site/`

## Solution: Relative URLs

Add support for generating **relative URLs** that work anywhere:
- From `index.html`: `assets/css/style.css`, `docs/index.html`
- From `docs/index.html`: `../assets/css/style.css`, `../index.html`
- From `docs/guide/installation.html`: `../../assets/css/style.css`, `../../index.html`

## Implementation Plan

### 1. Configuration Option

Add to `bengal.toml`:

```toml
[build]
relative_urls = false  # Default: false (absolute paths)
                       # Set to true for portable static sites
```

**Behavior:**
- `false` (default): Current behavior - absolute paths starting with `/`
- `true`: Generate relative paths based on page depth

### 2. Core URL Generation Functions

Create new module: `bengal/utils/url_helpers.py`

```python
from pathlib import Path
from typing import Optional

def make_relative_url(from_path: str, to_path: str) -> str:
    """
    Generate relative URL from one page to another.
    
    Args:
        from_path: Current page URL (e.g., "/docs/guide/")
        to_path: Target URL (e.g., "/assets/css/style.css")
    
    Returns:
        Relative URL (e.g., "../../assets/css/style.css")
    
    Examples:
        >>> make_relative_url("/", "/assets/style.css")
        'assets/style.css'
        
        >>> make_relative_url("/docs/", "/assets/style.css")
        '../assets/style.css'
        
        >>> make_relative_url("/docs/guide/", "/assets/style.css")
        '../../assets/style.css'
        
        >>> make_relative_url("/docs/guide/", "/docs/api/")
        '../api/'
    """
    # Implementation using os.path.relpath or custom logic
    pass

def get_url_depth(url: str) -> int:
    """
    Calculate depth of URL (number of directory levels).
    
    Examples:
        >>> get_url_depth("/")
        0
        >>> get_url_depth("/docs/")
        1
        >>> get_url_depth("/docs/guide/installation/")
        3
    """
    pass
```

### 3. Update Page.url Property

Modify `bengal/core/page.py`:

```python
@property
def url(self) -> str:
    """Get the URL path for the page."""
    # ... existing logic to compute absolute URL ...
    
    # If relative_urls enabled, this becomes the canonical absolute path
    # Template functions will convert to relative when needed
    return absolute_url

def relative_url(self, from_url: str) -> str:
    """
    Get relative URL from another page.
    
    Args:
        from_url: URL of the page linking to this one
    
    Returns:
        Relative URL
    """
    from bengal.utils.url_helpers import make_relative_url
    return make_relative_url(from_url, self.url)
```

### 4. Update Template Functions

#### a. Asset URL Function

Modify `bengal/rendering/template_engine.py`:

```python
def _asset_url(self, asset_path: str) -> str:
    """Generate URL for an asset."""
    absolute_url = f"/assets/{asset_path}"
    
    # If relative URLs enabled, convert to relative
    if self.site.config.get('build', {}).get('relative_urls', False):
        current_page_url = self.current_page.url if hasattr(self, 'current_page') else '/'
        from bengal.utils.url_helpers import make_relative_url
        return make_relative_url(current_page_url, absolute_url)
    
    return absolute_url
```

**Challenge:** Need to pass current page context to template engine.

#### b. Menu URLs

Menu URLs are defined in config - need to convert at render time:

```python
# In template_engine.py or menu rendering
def _get_menu(self, menu_name: str = 'main') -> list:
    menu = self.site.menu.get(menu_name, [])
    menu_items = [item.to_dict() for item in menu]
    
    # Convert to relative URLs if needed
    if self.site.config.get('build', {}).get('relative_urls', False):
        current_url = self.current_page.url if hasattr(self, 'current_page') else '/'
        for item in menu_items:
            item['url'] = make_relative_url(current_url, item['url'])
            # Also convert children
    
    return menu_items
```

#### c. Cross-reference URLs

Update `bengal/rendering/template_functions/crossref.py`:

```python
def ref(path: str, index: dict, text: str = None, current_url: str = '/') -> Markup:
    # ... existing lookup logic ...
    
    # Get page URL
    url = page.url
    
    # Convert to relative if needed
    if site.config.get('build', {}).get('relative_urls', False):
        url = make_relative_url(current_url, url)
    
    return Markup(f'<a href="{url}">{link_text}</a>')
```

#### d. Tag URLs

Update `bengal/rendering/template_functions/taxonomies.py`:

```python
def tag_url(tag: str, current_url: str = '/') -> str:
    slug = slugify(tag)
    absolute_url = f"/tags/{slug}/"
    
    if site.config.get('build', {}).get('relative_urls', False):
        return make_relative_url(current_url, absolute_url)
    
    return absolute_url
```

### 5. Pass Current Page Context

**Challenge:** Template functions need access to current page URL.

**Solution:** Enhance template rendering context:

```python
# In template_engine.py render() method
def render(self, template_name: str, context: dict) -> str:
    # Add current_url to global context
    if 'page' in context:
        context['current_url'] = context['page'].url
    else:
        context['current_url'] = '/'
    
    # Render template
    return template.render(context)
```

### 6. Special Cases

#### RSS Feed
```html
<link rel="alternate" type="application/rss+xml" href="/rss.xml">
```

With relative URLs:
- From `/`: `rss.xml`
- From `/docs/`: `../rss.xml`

#### Canonical URLs
```html
<link rel="canonical" href="https://example.com/docs/">
```

**Important:** Canonical URLs should ALWAYS be absolute with domain, regardless of `relative_urls` setting.

#### Open Graph URLs
```html
<meta property="og:url" content="https://example.com/docs/">
<meta property="og:image" content="https://example.com/assets/hero.jpg">
```

**Important:** OG/social meta tags should ALWAYS use absolute URLs with domain.

**Solution:** Keep separate functions:
- `canonical_url()` - always returns full URL with domain
- `og_image()` - always returns full URL with domain
- Regular `asset_url()`, `page.url` - respect `relative_urls` config

### 7. Testing Strategy

```python
# tests/unit/utils/test_url_helpers.py
def test_relative_url_same_level():
    assert make_relative_url('/docs/', '/api/') == '../api/'

def test_relative_url_to_root():
    assert make_relative_url('/docs/', '/') == '../'

def test_relative_url_to_deeper():
    assert make_relative_url('/docs/', '/docs/guide/') == 'guide/'

def test_relative_url_with_assets():
    assert make_relative_url('/docs/', '/assets/style.css') == '../assets/style.css'
    assert make_relative_url('/docs/guide/', '/assets/style.css') == '../../assets/style.css'
```

```python
# tests/integration/test_relative_urls.py
def test_build_with_relative_urls(tmp_path):
    """Test that relative_urls=true generates working site."""
    # Create site with relative_urls = true
    # Build site
    # Verify all links are relative
    # Verify links work when served from any directory
```

### 8. Documentation Updates

#### User Guide: Configuration
```markdown
### Relative URLs

By default, Bengal generates absolute paths (`/docs/`, `/assets/style.css`).
These work great on web servers but fail when opening HTML files directly.

To generate relative URLs suitable for:
- Opening HTML files directly (double-click)
- VS Code Live Server
- Static hosting in subdirectories
- Portable documentation sites

Enable relative URLs:

```toml
[build]
relative_urls = true
```

**Trade-offs:**
- ✅ Site works when opened directly
- ✅ No web server required
- ✅ Can be placed in any subdirectory
- ⚠️ Slightly larger HTML files (more `../`)
- ⚠️ Can't use domain root absolute paths

**Note:** SEO meta tags (canonical, og:url) always use absolute URLs with baseurl.
```

## Implementation Order

1. ✅ **Create plan document** (this file)
2. ⬜ Create `bengal/utils/url_helpers.py` with core functions
3. ⬜ Add unit tests for URL helper functions
4. ⬜ Add `relative_urls` config option and parsing
5. ⬜ Update `Page.url` to support relative conversion
6. ⬜ Update `template_engine._asset_url()` 
7. ⬜ Update template functions (crossref, taxonomies, etc.)
8. ⬜ Pass `current_url` context to all templates
9. ⬜ Add integration tests
10. ⬜ Test with examples/showcase
11. ⬜ Update documentation

## Success Criteria

After implementation, this should work:

1. **Direct file opening:**
   - Double-click `/public/index.html`
   - All CSS, JS, images load correctly
   - All internal links work

2. **Live Server:**
   - Run VS Code Live Server on `/public/`
   - Site works perfectly

3. **Subdirectory hosting:**
   - Copy `/public/` to `/var/www/html/mysite/`
   - Site works at `http://server/mysite/`

4. **SEO preserved:**
   - Canonical URLs still use full domain
   - Open Graph tags still use full domain
   - RSS feed URLs work correctly

## Notes

- This is a **major feature** affecting URL generation throughout the system
- Must maintain backward compatibility (default `relative_urls = false`)
- Consider performance impact (relative path calculation per render)
- May want to cache relative URLs per page pair

