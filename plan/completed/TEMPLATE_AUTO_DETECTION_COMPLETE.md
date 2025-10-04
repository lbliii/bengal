# Template Auto-Detection - Implementation Complete

**Date:** October 4, 2025  
**Status:** ✅ Complete

## Summary

Implemented section-based template auto-detection for Bengal SSG, providing a simpler alternative to Hugo's confusing `type`/`kind`/`layout` hierarchy.

## Design Philosophy

**"Simple but powerful, not confusing"**

We intentionally avoided Hugo's complexity:
- ❌ Hugo: `type`, `kind`, `layout`, `baseof`, archetype inheritance
- ✅ Bengal: `template` (explicit) or section-based auto-detection

## Implementation

### Template Selection Priority

```python
# 1. Explicit template (highest priority)
template: doc.html

# 2. Section-based auto-detection
# For /docs/my-page.md:
#   ✓ templates/docs.html
#   ✓ templates/docs/single.html
#   ✓ templates/docs/page.html

# For /docs/_index.md:
#   ✓ templates/docs.html
#   ✓ templates/docs/list.html
#   ✓ templates/docs/index.html
#   ✓ templates/docs-list.html

# 3. Default fallback
#   - page.html (regular pages)
#   - index.html (section indexes)
```

### File: `bengal/rendering/renderer.py`

**Key Changes:**
1. Fixed bug: `page.section` → `page._section` (correct attribute name)
2. Removed confusing `type` → template mapping
3. Simplified fallback logic
4. Added clear documentation

```python
def _get_template_name(self, page: Page) -> str:
    """
    Priority order:
    1. Explicit template in frontmatter (`template: doc.html`)
    2. Section-based auto-detection (e.g., `docs.html`)
    3. Default fallback (`page.html` or `index.html`)
    
    Note: We intentionally avoid Hugo's confusing type/kind/layout hierarchy.
    """
```

## Testing

### Before Fix
```bash
# Only 3 of 10 docs pages using doc.html
$ grep -l 'class="docs-layout"' public/docs/**/*.html | wc -l
3
```

### After Fix
```bash
# All 10 docs pages using doc.html via auto-detection
$ grep -l 'class="docs-layout"' public/docs/**/*.html | wc -l
10
```

## Template Organization

Bengal supports **two organization styles**:

### Style 1: Flat (Recommended for Simple Sites)
```
templates/
  base.html
  page.html
  index.html
  docs.html           ← Auto-detected for /docs/ pages
  blog.html           ← Auto-detected for /blog/ pages
  tutorials.html      ← Auto-detected for /tutorials/ pages
```

### Style 2: Directory (Hugo-Compatible)
```
templates/
  base.html
  page.html
  index.html
  docs/
    single.html       ← Auto-detected for /docs/page.md
    list.html         ← Auto-detected for /docs/_index.md
  blog/
    single.html
    list.html
```

## Benefits vs Hugo

| Feature | Hugo | Bengal |
|---------|------|--------|
| **Complexity** | High (`type`, `kind`, `layout`, `baseof`) | Low (explicit or section-based) |
| **Learning Curve** | Steep | Gentle |
| **Flexibility** | Very high | High enough |
| **Explicitness** | Implicit cascading | Clear priority order |
| **Debugging** | "Where is this template coming from?" | Easy to trace |

## User Feedback Integration

**User:** *"i think thats something also confusing about hugo is type vs kind vs layout etc. id like to avoid that"*

**Response:** Removed all `type`-based template mapping. Now it's just:
1. Explicit `template:` in frontmatter (if you want control)
2. Section name auto-detection (convention over configuration)
3. Default fallback (sensible defaults)

No `type`, no `kind`, no `layout` confusion. Just simple, predictable behavior.

## Documentation for Users

### Quick Start

**No configuration needed!** Just create a template with your section name:

```bash
# Your content structure
content/
  docs/
    _index.md         ← Will use templates/docs.html
    page1.md          ← Will use templates/docs.html
    page2.md          ← Will use templates/docs.html

# Your template
templates/
  docs.html           ← Automatically applied to all /docs/ pages
```

### Override for Specific Pages

```yaml
---
title: "Special Page"
template: custom.html    # Explicit override
---
```

### Hugo Compatibility

Bengal supports Hugo's `single.html`/`list.html` pattern:

```bash
templates/
  docs/
    single.html    # Regular pages in /docs/
    list.html      # /docs/_index.md
```

But also supports simpler flat naming:

```bash
templates/
  docs.html        # All /docs/ pages
```

## Next Steps

- [x] Implement section-based auto-detection
- [x] Test with quickstart example
- [x] Document behavior
- [ ] Add to user documentation (QUICKSTART.md)
- [ ] Add examples to theme guide
- [ ] Consider cascade template inheritance (future)

## Conclusion

**Success!** We've implemented a template system that is:
- ✅ **Simpler than Hugo** (no type/kind/layout confusion)
- ✅ **Powerful enough** (section-based auto-detection)
- ✅ **Ergonomic** (convention over configuration)
- ✅ **Flexible** (explicit override when needed)
- ✅ **Hugo-compatible** (for users migrating)

The system is production-ready and successfully handles the quickstart example with all 10 docs pages automatically using the correct template.

