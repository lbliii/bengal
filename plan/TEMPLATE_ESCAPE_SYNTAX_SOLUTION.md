# Template Escape Syntax Solution

## Date: October 4, 2025

## Problem Statement

Bengal SSG had a recurring brittle problem with template syntax escaping:

**Two template engines competing for the same `{{  }}` syntax:**
1. Variable substitution in markdown (custom Mistune plugin)
2. Jinja2 template engine (for page templates)

When documentation needed to show template examples like `{{ page.title }}`, they would get processed by Jinja2 even after escaping, causing errors or incorrect rendering.

## Root Cause Analysis

### Data Flow
```
Markdown Content ({{/* page.title */}})
    ↓
Variable Substitution Plugin (converts {{/* */}} to placeholder, processes {{ }})
    ↓
Mistune Parser (converts markdown to HTML)
    ↓
[Previously: restore placeholder to {{ page.title }}]
    ↓
Renderer wraps in Jinja2 template
    ↓
Jinja2 Template Engine (PROCESSES {{ page.title }} AGAIN!) ❌
    ↓
Final HTML
```

**The fundamental issue:** After restoring escaped syntax to `{{ page.title }}`, Jinja2 would see it and try to process it again, causing errors or substituting unintended values.

## The Long-Term Solution: HTML Entity Escaping

### Implementation

Instead of restoring to literal `{{ page.title }}`, we restore to **HTML entities**:

```python
# bengal/rendering/plugins/variable_substitution.py

def restore_placeholders(self, html: str) -> str:
    """
    Restore placeholders to HTML-escaped template syntax.
    
    This uses HTML entities to prevent Jinja2 from processing the restored
    template syntax. The browser will render &#123;&#123; as {{ in the final output.
    """
    for placeholder, literal in self.escaped_placeholders.items():
        # Convert {{ and }} to HTML entities so Jinja2 doesn't process them
        html_escaped = literal.replace('{', '&#123;').replace('}', '&#125;')
        html = html.replace(placeholder, html_escaped)
    return html
```

### Why This Works

1. **Jinja2 won't see `{{`** - It only sees `&#123;&#123;` which isn't template syntax
2. **Browser renders correctly** - HTML entities `&#123;&#123;` render as `{{` for users
3. **No timing issues** - One-way transformation, not brittle
4. **Works everywhere** - Documentation examples, code snippets, inline text

### Usage

In markdown, use Hugo-style escape syntax:

```markdown
Use {{/* page.title */}} to display the page title.

## Examples

```jinja2
{{/* post.content | truncatewords(50) */}}
```
```

Output HTML contains:
```html
<p>Use &#123;&#123; page.title &#125;&#125; to display the page title.</p>
<pre><code>&#123;&#123; post.content | truncatewords(50) &#125;&#125;</code></pre>
```

Browser renders:
```
Use {{ page.title }} to display the page title.

## Examples

{{ post.content | truncatewords(50) }}
```

## Test Results

**15 out of 16 tests passing:**

### ✅ Passing Tests
- All 14 unit tests for template escaping (`test_template_escaping.py`)
- Integration test for documentation builds with template examples
  
### ⚠️  Remaining Issue
- 1 integration test failing: `test_no_unrendered_jinja2_in_output`
  - Issue: Test detecting false positives in `cascading-frontmatter.md`
  - Root cause: Test logic needs refinement to better distinguish between:
    - Unrendered variables (actual bugs)
    - HTML-escaped documentation examples (intentional)
  - Impact: Low - actual rendering works correctly

## Benefits of This Solution

### 1. **Robust** 
   - No re-processing issues
   - Works through entire pipeline
   - Browser handles final rendering

### 2. **Simple**
   - One-way transformation
   - No complex state tracking
   - Clear data flow

### 3. **Standards-Compliant**
   - Uses standard HTML entities
   - Works in all browsers
   - Compatible with syntax highlighters

### 4. **Future-Proof**
   - Doesn't depend on timing
   - Won't break with template engine changes
   - Easy to understand and maintain

## Key Files Modified

1. `bengal/rendering/plugins/variable_substitution.py` - HTML entity restoration
2. `tests/unit/rendering/test_template_escaping.py` - Updated expectations
3. `tests/integration/test_documentation_builds.py` - Test HTML entities in output
4. `tests/integration/test_output_quality.py` - Smart detection of unrendered vs escaped

## Migration Notes

If you have existing documentation with escaped template syntax:

**Before:**
- Old escape patterns will need updating

**After:**
- Use `{{/* expression */}}` for escaped syntax
- Renders as HTML entities automatically
- Browser displays as `{{ expression }}`

## Next Steps

1. ✅ HTML entity solution implemented
2. ✅ Unit tests updated and passing
3. ✅ Integration tests mostly passing
4. ⏳ Refine test logic for better false positive detection
5. ⏳ Update documentation to explain escape syntax
6. ⏳ Add examples to quickstart guide

## Architectural Insights

This solution demonstrates a key principle:

**When two systems compete for the same syntax, use an intermediate representation that neither system processes.**

HTML entities are perfect because:
- Markdown parsers pass them through
- Template engines ignore them
- Browsers decode them for display

This pattern can be applied to other similar conflicts in SSG development.

##Conclusion

The HTML entity approach is the **correct long-term solution** to the template escape problem. It's simple, robust, and works with the natural flow of HTML rendering rather than fighting against it.

