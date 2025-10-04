# Template Error Reporting Improvements

**Current Date:** October 3, 2025  
**Context:** Improving developer experience when template errors occur

---

## Current State

### What Works ✅
- Warnings shown during build
- Graceful fallback rendering
- Pages still build (don't crash)
- Clear error messages about what failed

### Pain Points 😅
- No line numbers in error messages
- Only first error shown (need multiple rebuilds)
- No template inclusion stack trace
- Hard to trace recursive includes
- No syntax validation before rendering

---

## Proposed Improvements

### 1. Enhanced Error Messages with Line Numbers

**Current:**
```
⚠️ Warning: Failed to render page .../index.md with template doc.html:
No filter named 'in_section' found.
```

**Improved:**
```
⚠️ Template Error in doc.html:

  File: bengal/themes/default/templates/partials/docs-nav-section.html
  Line: 16
  
  {% if section | in_section(page) or section == page.parent %}
                   ^^^^^^^^^^
  
  Error: Unknown Jinja2 filter 'in_section'
  
  Available filters: date_iso, dateformat, slugify, time_ago, reading_time, ...
  Did you mean: in_list?
  
  Included from:
    doc.html:20 → partials/docs-nav.html:30 → partials/docs-nav-section.html:16
```

### 2. Multiple Error Collection

Instead of failing on first error, collect ALL errors:

```
⚠️ Template Validation Failed: doc.html (3 errors)

  1. partials/docs-nav-section.html:16
     └─ Unknown filter: in_section
     
  2. partials/docs-nav-section.html:40
     └─ Unknown filter: is_ancestor
     
  3. partials/docs-nav.html:28
     └─ Invalid attribute access: metadata.weight
        Suggestion: Use get_metadata(section, 'weight', default=999)

  Fix all errors above, then rebuild.
```

### 3. Template Inclusion Stack Trace

Show the full include chain:

```
Template Include Chain:
  
  doc.html (line 20)
    └─ include 'partials/docs-nav.html'
         └─ (line 30) include 'partials/docs-nav-section.html'
              └─ (line 47) include 'partials/docs-nav-section.html' [RECURSIVE]
                   └─ ERROR HERE (line 16): Unknown filter 'in_section'
```

### 4. Pre-Render Syntax Validation

Add a `--validate-templates` flag:

```bash
$ bengal build --validate-templates

🔍 Validating templates...

✓ base.html (valid)
✓ page.html (valid)
✗ doc.html (3 errors)
  └─ See errors above
✓ archive.html (valid)

❌ Validation failed. 1 template has errors.
```

### 5. Template Linting

Add a dedicated linter command:

```bash
$ bengal lint templates

📋 Linting templates in: bengal/themes/default/templates/

partials/docs-nav-section.html:
  Line 16: Error - Unknown filter 'in_section'
  Line 40: Error - Unknown filter 'is_ancestor'
  Line 28: Warning - Consider using get_metadata() for safe attribute access

partials/docs-nav.html:
  Line 28: Warning - sort() attribute access may fail if metadata missing

✗ 2 errors, 2 warnings
```

### 6. Available Filters Documentation

When a filter is not found, show what IS available:

```
Error: Unknown filter 'in_section'

Available template filters:
  
  Date/Time:
    - date_iso, dateformat, time_ago
    
  Text:
    - slugify, truncate, capitalize
    
  Content:
    - reading_time, excerpt, meta_description
    
  Navigation:
    - url_for, asset_url, tag_url
    
  Custom:
    - get_menu, related_posts, has_tag
    
  See: https://docs.bengal-ssg.com/template-filters
```

### 7. Better Fallback Notice

**Current fallback page:**
```html
<div class="fallback-notice">
  ⚠️ Notice: This page is displayed in fallback mode due to a template error.
</div>
```

**Improved (in development mode):**
```html
<div class="fallback-notice">
  <strong>⚠️ Template Error (Development Mode)</strong>
  
  <details>
    <summary>Error Details</summary>
    
    <p><strong>Template:</strong> doc.html</p>
    <p><strong>Error:</strong> Unknown filter 'in_section'</p>
    <p><strong>File:</strong> partials/docs-nav-section.html:16</p>
    
    <pre><code>{% if section | in_section(page) %}
                    ^^^^^^^^^^
Unknown filter</code></pre>
    
    <p><a href="/docs/template-errors">Learn how to fix</a></p>
  </details>
</div>
```

### 8. IDE Integration

Generate a `.bengal-lint.json` file for IDE integration:

```json
{
  "errors": [
    {
      "file": "bengal/themes/default/templates/partials/docs-nav-section.html",
      "line": 16,
      "column": 21,
      "severity": "error",
      "message": "Unknown Jinja2 filter: in_section",
      "suggestion": "Did you mean: in_list?"
    }
  ]
}
```

---

## Implementation Priority

### Phase 1: Quick Wins (High Impact, Low Effort)
1. ✅ Add line numbers to error messages
2. ✅ Show template inclusion chain
3. ✅ List available filters on error

### Phase 2: Medium Effort
4. ⏳ Collect multiple errors per template
5. ⏳ Enhanced fallback notice (dev mode)
6. ⏳ Template validation flag

### Phase 3: Nice to Have
7. ⏳ Dedicated lint command
8. ⏳ IDE integration file
9. ⏳ Interactive error fixing suggestions

---

## Code Locations

### Files to Modify

1. **`bengal/core/renderer.py`** - Main rendering logic
   - Add line number tracking
   - Collect multiple errors
   - Generate stack traces

2. **`bengal/utils/template_loader.py`** - Template loading
   - Add syntax pre-validation
   - Track include chains
   - Cache filter availability

3. **`bengal/cli/build.py`** - Build command
   - Add `--validate-templates` flag
   - Pretty-print error summaries

4. **`bengal/cli/lint.py`** - NEW: Linting command
   - Validate all templates
   - Generate lint reports
   - IDE integration output

5. **`bengal/themes/default/templates/error-fallback.html`**
   - Enhanced development mode notice
   - Error details display
   - Helpful documentation links

---

## Error Message Format Standard

Use a consistent format for all template errors:

```
⚠️ Template Error: {error_type}

  File:  {template_path}
  Line:  {line_number}
  
  {code_snippet_with_highlight}
  
  Error: {detailed_message}
  
  {suggestion_if_available}
  
  Included from: {include_chain}
```

---

## Example: Complete Error Message

```
⚠️ Template Error: Unknown Filter

  File:  bengal/themes/default/templates/partials/docs-nav-section.html
  Line:  16
  Column: 21
  
   14 |   <button 
   15 |     class="docs-nav-group-toggle"
   16 |     aria-expanded="{% if section | in_section(page) %}true{% endif %}"
      |                                    ^^^^^^^^^^
   17 |     aria-controls="nav-section-{{ section.url | slugify }}">
   18 |     <svg viewBox="0 0 24 24">
  
  Error: Jinja2 filter 'in_section' not found
  
  Available filters in Bengal: date_iso, dateformat, slugify, time_ago, reading_time, 
  excerpt, url_for, asset_url, tag_url, get_menu, related_posts, has_tag, is_section,
  in_list, meta_description
  
  Suggestion: Did you mean 'is_section' or 'in_list'?
  
  Included from:
    doc.html:20
      → partials/docs-nav.html:30
        → partials/docs-nav-section.html:16 [ERROR]
  
  Docs: https://docs.bengal-ssg.com/template-filters
```

---

## Benefits

### For Developers
- **Faster debugging** - See all errors at once
- **Better error messages** - Line numbers and context
- **Less rebuilding** - Fix all errors in one go
- **Learning tool** - Suggestions help learn the system

### For AI Assistants
- **Easier problem identification** - Clear error locations
- **Better suggestions** - See available alternatives
- **One-shot fixes** - All errors visible upfront
- **Context understanding** - Include chains clarify structure

### For Teams
- **Consistency** - Standard error format
- **Documentation** - Links to relevant docs
- **IDE integration** - Errors shown in editor
- **Onboarding** - New developers learn faster

---

## Testing Strategy

1. **Unit Tests**
   - Test error message formatting
   - Test line number extraction
   - Test include chain tracking

2. **Integration Tests**
   - Test with real templates
   - Test recursive includes
   - Test multiple error collection

3. **Regression Tests**
   - Ensure existing error handling still works
   - Test fallback rendering
   - Test graceful degradation

---

## Documentation Needed

1. **For Users**: Error message guide
2. **For Theme Developers**: Template debugging guide
3. **For Contributors**: Error handling architecture

---

## Alternative: Static Analysis Tool

Consider a separate tool:

```bash
$ bengal-lint templates/

Analyzing templates...

✓ Syntax valid: 45 templates
✗ Errors found: 2 templates
⚠ Warnings:     3 templates

Run 'bengal-lint --fix' to auto-fix common issues
Run 'bengal-lint --explain' for detailed explanations
```

---

## Conclusion

The current error handling is **good** (graceful degradation, clear messages), but with these improvements it could be **excellent**.

Priority: Implement Phase 1 (quick wins) first - they provide the most value for the least effort.

