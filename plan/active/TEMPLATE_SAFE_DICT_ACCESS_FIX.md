# Template Safe Dictionary Access Fix

**Date:** 2025-10-12  
**Status:** 🔴 Critical - Blocking `bengal serve`  
**Priority:** P0 - Must fix before macro plan

## Problem

Templates are accessing `page.metadata.key` directly, which throws `UndefinedError` when keys don't exist. This only shows up in `bengal serve` (not `build`) because serve rebuilds on every request.

### Error Pattern
```
error='dict object' has no attribute 'og_image'
Template Chain:
  ├─ single.html:2
    └─ base.html:36
```

### Root Cause
Jinja2 dot notation (`dict.key`) raises `UndefinedError` for missing keys.

## Affected Templates (15 files)

1. ✅ `base.html` - FIXED (keywords, image)
2. ⚠️  `cli-reference/single.html` - NEEDS FIX
3. ⚠️  `api-reference/single.html` - NEEDS FIX  
4. ⚠️  `partials/reference-header.html` - NEEDS FIX
5. ⚠️  `partials/reference-components.html` - NEEDS FIX
6. ⚠️  `partials/reference-metadata.html` - NEEDS FIX
7. ⚠️  `tutorial/single.html` - NEEDS FIX
8. ⚠️  `post.html` - NEEDS FIX
9. ⚠️  `partials/toc-sidebar.html` - NEEDS FIX
10. ⚠️  `page.html` - NEEDS FIX
11. ⚠️  `index.html` - NEEDS FIX
12. ⚠️  `home.html` - NEEDS FIX
13. ⚠️  `doc/single.html` - NEEDS FIX
14. ⚠️  `doc/list.html` - NEEDS FIX
15. ⚠️  `blog/single.html` - NEEDS FIX

## Safe Access Patterns

### Pattern 1: Check before access (preferred for conditionals)
```jinja2
{# BAD #}
{% if page.metadata.css_class %}

{# GOOD #}
{% if page.metadata.get('css_class') %}
```

### Pattern 2: Default filter (preferred for output)
```jinja2
{# BAD #}
{{ page.metadata.description }}

{# GOOD #}
{{ page.metadata.get('description', '') }}
```

### Pattern 3: Explicit check (when you need to distinguish None vs missing)
```jinja2
{# BAD #}
{% if page.metadata.author %}

{# GOOD #}
{% if 'author' in page.metadata and page.metadata.author %}
```

## Strategy

1. Search each file for `page.metadata.KEY` patterns
2. Replace with `.get('KEY')` or `.get('KEY', default)`
3. Test with `bengal serve`
4. Verify no `UndefinedError` messages

## Not Related To

- Macro component architecture (separate initiative)
- Component migration plan (can proceed independently)

This is a **prerequisite fix** that must be done first.
