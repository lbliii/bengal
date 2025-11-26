# RFC: Improve BaseURL Pattern for Templates

**Status**: Draft  
**Date**: 2025-01-XX  
**Author**: AI Assistant  
**Related**: Issue with tracks/graph/search pages missing baseurl

---

## Problem Statement

Bengal currently has two URL properties:
- `page.url` - Relative URL (e.g., `/docs/page/`)
- `page.permalink` - URL with baseurl (e.g., `/bengal/docs/page/`)

**The Problem**:
1. Templates inconsistently use `url` vs `permalink`
2. Easy to forget and use the wrong one (we keep making this mistake)
3. The distinction is subtle and error-prone
4. Comment says "use .url for comparisons, .permalink for href/src" but this is confusing

**Current Usage**:
- `page.url` used for: comparisons (`page.url == '/docs/'`), active state detection
- `page.permalink` used for: display in `<a href>`, `<link rel="canonical">`

**Why It's Hacky**:
- Requires developers to remember which to use when
- No compile-time or runtime enforcement
- Easy to miss in code review
- The "identity vs display" pattern is not intuitive

---

## Current Pattern Analysis

### Where `page.url` (relative) is Used

1. **Comparisons** (docs-nav.html:48, 64, 84):
   ```jinja2
   {% set current_url = page.url.rstrip('/') %}
   {% if current_url == p_url_normalized %}
   ```

2. **Filtering** (docs-nav.html:64):
   ```jinja2
   {% if p.url != root_index_url %}
   ```

3. **Active state detection** (base.html:191, 196):
   ```jinja2
   {% if page.url == '/' %}
   {% if page.url.startswith(item.url) %}
   ```

### Where `page.permalink` (with baseurl) is Used

1. **Display URLs** (docs-nav.html:54, 66):
   ```jinja2
   <a href="{{ page.permalink }}">
   ```

2. **Canonical URLs** (base.html:36, 66):
   ```jinja2
   <link rel="canonical" href="{{ canonical_url(page.url) }}">
   ```

---

## Proposed Solutions

### Option 1: Template Context Wrapper (Recommended)

**Approach**: Wrap page objects in template context so `page.url` automatically includes baseurl when accessed in templates.

**Implementation**:
```python
class TemplatePageWrapper:
    """Wrapper that makes page.url include baseurl in templates."""

    def __init__(self, page: Page, baseurl: str):
        self._page = page
        self._baseurl = baseurl.rstrip("/") if baseurl else ""

    @property
    def url(self) -> str:
        """URL with baseurl applied (for templates)."""
        rel = self._page.url
        if not self._baseurl:
            return rel
        base_path = "/" + self._baseurl.lstrip("/")
        return f"{base_path}{rel}"

    def __getattr__(self, name: str):
        """Delegate all other attributes to wrapped page."""
        return getattr(self._page, name)
```

**Pros**:
- ✅ Templates always use `page.url` (intuitive)
- ✅ No breaking changes to existing templates
- ✅ Comparisons still work (they compare relative URLs internally)
- ✅ Single source of truth: `page.url` in templates

**Cons**:
- ⚠️ Need to wrap pages in template context
- ⚠️ Comparisons might need adjustment (but they already normalize)

**Migration**: Minimal - templates already use `page.url` for comparisons, just need to ensure wrapper is applied.

---

### Option 2: Make `url_for()` Standard

**Approach**: Deprecate direct `page.url` access in templates, require `url_for(page)`.

**Implementation**:
- `url_for()` already exists and applies baseurl
- Add linting rule to warn about direct `page.url` in templates
- Update all templates to use `url_for(page)`

**Pros**:
- ✅ Explicit and clear
- ✅ Already implemented
- ✅ Consistent with other template functions

**Cons**:
- ❌ Breaking change (all templates need updates)
- ❌ More verbose: `{{ url_for(page) }}` vs `{{ page.url }}`
- ❌ Comparisons still need `page.url` (can't use `url_for()`)

---

### Option 3: Make `page.url` Always Include Baseurl

**Approach**: Change `page.url` to always include baseurl, add `page.relative_url` for comparisons.

**Implementation**:
```python
@property
def relative_url(self) -> str:
    """Relative URL for comparisons (without baseurl)."""
    # Current page.url logic

@property  
def url(self) -> str:
    """URL with baseurl (for display)."""
    # Current page.permalink logic
```

**Pros**:
- ✅ Most intuitive: `page.url` is what you use in templates
- ✅ Matches user expectations

**Cons**:
- ❌ Breaking change (all comparisons need to change to `relative_url`)
- ❌ More confusing: "why is url not relative?"
- ❌ Comparisons become less intuitive

---

### Option 4: Template Filter Auto-Apply

**Approach**: Create a template filter that auto-applies baseurl, make it the default.

**Implementation**:
```jinja2
{# Old way #}
<a href="{{ page.url }}">

{# New way - filter auto-applies baseurl #}
<a href="{{ page.url | url }}">
```

**Pros**:
- ✅ Explicit when baseurl is applied
- ✅ Can still use `page.url` for comparisons

**Cons**:
- ❌ Still requires remembering to use filter
- ❌ Easy to forget
- ❌ Doesn't solve the root problem

---

## Recommendation: Option 1 (Template Context Wrapper)

**Why**:
1. **Intuitive**: Templates always use `page.url` - no confusion
2. **Non-breaking**: Existing templates work without changes
3. **Safe**: Comparisons still work (they normalize URLs anyway)
4. **Consistent**: Single pattern across all templates

**Implementation Plan**:

1. **Create `TemplatePageWrapper`**:
   ```python
   # bengal/rendering/template_context.py
   class TemplatePageWrapper:
       """Wraps Page objects to auto-apply baseurl to .url in templates."""
       # ... implementation ...
   ```

2. **Update TemplateEngine to wrap pages**:
   ```python
   # In TemplateEngine.render()
   if isinstance(context.get('page'), Page):
       context['page'] = TemplatePageWrapper(
           context['page'],
           self.site.config.get('baseurl', '')
       )
   ```

3. **Update comparisons to use relative URLs**:
   - Comparisons already normalize URLs, so they should still work
   - If needed, add `page.relative_url` property for explicit comparisons

4. **Update documentation**:
   - Templates: Always use `page.url` (it includes baseurl automatically)
   - Comparisons: Use normalized URLs or `page.relative_url` if needed

**Migration**:
- Templates: No changes needed (they already use `page.url`)
- Comparisons: May need minor adjustments if they break (unlikely)
- Tests: Update to verify wrapper behavior

---

## Alternative: Hybrid Approach

If Option 1 is too complex, we could:

1. **Keep current pattern** but make it more explicit:
   - Rename `permalink` → `url` (deprecate old `url`)
   - Add `relative_url` for comparisons
   - Update all templates to use new names

2. **Add linting**:
   - Warn when `page.url` is used in `<a href>` without baseurl
   - Suggest using `page.permalink` or `url_for(page)`

3. **Documentation**:
   - Clear examples showing when to use which
   - Template best practices guide

---

## Questions

1. **Should comparisons use relative URLs?**
   - Current: Yes, they normalize and compare relative URLs
   - With wrapper: Still yes, wrapper doesn't affect comparisons

2. **What about `url_for()` function?**
   - Keep it for flexibility
   - But make `page.url` the default in templates

3. **What about special pages (404, search, graph)?**
   - They create SimpleNamespace objects with hardcoded URLs
   - Need to ensure they also get baseurl applied

---

## Success Criteria

✅ Templates always use `page.url` (intuitive)  
✅ Baseurl automatically applied (no manual steps)  
✅ Comparisons still work (no breaking changes)  
✅ No confusion about which property to use  
✅ Easy to remember and hard to get wrong  

---

## Next Steps

1. Review this RFC
2. Choose approach (recommend Option 1)
3. Implement chosen approach
4. Update all templates if needed
5. Add tests
6. Update documentation
