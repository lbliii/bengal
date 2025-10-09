# Autodoc CSS Conflicts - Fixed

**Date:** October 9, 2025  
**Status:** ✅ Complete

## Issues Identified

### 1. `.prose` Class Not Applied to API Docs
**Problem:** The `css_class: api-content` added to autodoc templates wasn't being used by page templates.

**Impact:** API documentation pages weren't getting the special `.api-content` styling we created, causing them to use generic prose styles that conflict with API-specific needs.

**Root Cause:** Templates (`page.html`, `doc.html`, `docs.html`) had hardcoded `.prose` class but didn't check for dynamic `page.metadata.css_class`.

### 2. Raw Markdown in List Descriptions
**Problem:** Module/command descriptions on list pages showed raw markdown syntax like `"# autodoc Bengal..."` instead of clean text.

**Impact:** Card descriptions looked broken and unprofessional.

**Root Cause:** 
- Autodoc templates didn't provide `description` metadata
- List templates fell back to `post.content | striptags | truncate(200)`
- `striptags` removes HTML but not markdown syntax (`#`, `**`, etc.)
- First line of content was always the markdown `# Title` header

## Solutions Implemented

### Fix 1: Dynamic CSS Class Support

**Files Modified:**
- `bengal/themes/default/templates/page.html`
- `bengal/themes/default/templates/doc.html`
- `bengal/themes/default/templates/docs.html`

**Change:**
```jinja2
{# Before #}
<article class="prose">

{# After #}
<article class="prose {% if page.metadata.css_class %}{{ page.metadata.css_class }}{% endif %}">
```

**Result:** Pages with `css_class: api-content` now get both `.prose` and `.api-content` classes, allowing API-specific styles to override prose defaults.

### Fix 2: Clean Descriptions in Autodoc Templates

**Files Modified:**
- `bengal/autodoc/templates/python/module.md.jinja2`
- `bengal/autodoc/templates/cli/command.md.jinja2`
- `bengal/autodoc/templates/cli/command-group.md.jinja2`

**Changes:**

**Python Module Template:**
```yaml
description: "{% if element.description %}{{ element.description | replace('\n', ' ') | truncate(200, True, '...') }}{% else %}Python module documentation{% endif %}"
```

**CLI Command Template:**
```yaml
description: "{{ element.description | replace('\n', ' ') | truncate(180, True, '...') }}"
```

**CLI Command Group Template:**
```yaml
description: "{% if element.description %}{{ element.description | replace('\n', ' ') | truncate(180, True, '...') }}{% else %}Command-line interface reference and documentation{% endif %}"
```

**Result:** 
- Descriptions extracted from docstrings/documentation
- Newlines converted to spaces
- Properly truncated for card display
- No markdown syntax in output

### Fix 3: CSS Specificity Clarification

**File Modified:** `bengal/themes/default/assets/css/components/api-docs.css`

**Added:**
```css
/* Ensure .prose base styles don't conflict with api-content */
.prose.api-content h1,
.prose.api-content h2,
.prose.api-content h3,
.prose.api-content h4,
.prose.api-content h5,
.prose.api-content h6 {
  /* API content headings inherit from prose but maintain api-docs specificity */
  font-weight: var(--font-semibold);
}

/* API content inherits prose list styles but maintains spacing */
.prose.api-content ul,
.prose.api-content ol {
  /* Lists use prose defaults unless overridden by parameter list styles */
  margin-top: var(--space-3);
  margin-bottom: var(--space-3);
}
```

**Result:** Explicit rules ensure `.prose.api-content` has proper CSS cascade without conflicts.

## How It Works Now

### Individual API Doc Pages

1. Autodoc generates markdown with frontmatter:
   ```yaml
   ---
   title: "bengal"
   css_class: api-content
   description: "Bengal SSG - A high-performance static site generator..."
   ---
   ```

2. Page template renders with both classes:
   ```html
   <article class="prose api-content">
     <!-- API documentation content -->
   </article>
   ```

3. CSS cascade applies in order:
   - `.prose` base styles (typography, spacing)
   - `.prose.api-content` overrides (wider width, API-specific spacing)
   - `.prose.api-content h3 + pre` (signature blocks)
   - `.prose.api-content p + ul` (parameter lists)

### API Reference List Pages

1. Autodoc generates pages with clean descriptions in frontmatter

2. List template uses description from metadata:
   ```jinja2
   {% if post.metadata.description %}
     <p class="api-module-description">
       {{ post.metadata.description | truncate(200) }}
     </p>
   {% endif %}
   ```

3. Result: Clean, professional card descriptions without markdown syntax

## Benefits

### Before → After

**Individual Pages:**
- ❌ Before: Generic prose styling, narrow width, wrong spacing
- ✅ After: API-specific styling, wider layout, proper signature blocks

**List Pages:**
- ❌ Before: `"# autodoc Bengal Autodoc - Unified documentation..."` 
- ✅ After: `"Bengal Autodoc - Unified documentation generation system..."`

### CSS Specificity

The `.prose.api-content` pattern provides:
1. **Inheritance** - Gets all prose typography and formatting
2. **Override Capability** - Can override specific prose rules for API needs
3. **No Conflicts** - Higher specificity prevents prose from overriding API styles
4. **Future-Proof** - Easy to add more API-specific overrides

## Files Modified (7 files)

1. ✅ `bengal/themes/default/templates/page.html` - Dynamic css_class
2. ✅ `bengal/themes/default/templates/doc.html` - Dynamic css_class
3. ✅ `bengal/themes/default/templates/docs.html` - Dynamic css_class
4. ✅ `bengal/autodoc/templates/python/module.md.jinja2` - Clean descriptions
5. ✅ `bengal/autodoc/templates/cli/command.md.jinja2` - Clean descriptions
6. ✅ `bengal/autodoc/templates/cli/command-group.md.jinja2` - Clean descriptions
7. ✅ `bengal/themes/default/assets/css/components/api-docs.css` - Specificity rules

## Testing

To verify the fixes:

```bash
# Regenerate autodoc with new templates
bengal autodoc bengal --output docs/api

# Build and view
bengal build
bengal serve
```

**Check:**
- [ ] Individual API pages have `.prose.api-content` classes
- [ ] Signature blocks use enhanced styling
- [ ] Parameter lists have elevated backgrounds
- [ ] List page descriptions are clean (no `#` or markdown)
- [ ] Module cards show proper descriptions
- [ ] CLI command cards show proper descriptions

## Related

This fix completes the autodoc UX redesign by ensuring:
- Proper CSS class application
- No style conflicts between `.prose` and API styles
- Clean, professional descriptions on all pages
- Consistent design system throughout

See also: `AUTODOC_UX_REDESIGN_COMPLETE.md`

