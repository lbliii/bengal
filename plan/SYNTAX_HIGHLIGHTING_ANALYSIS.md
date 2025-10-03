# Syntax Highlighting Analysis

**Date:** October 3, 2025  
**Status:** 🔍 ANALYSIS COMPLETE  
**Issue:** Syntax highlighting not working with Mistune parser

---

## The Problem

**Symptom:** Code blocks render but have no syntax highlighting (colors for keywords, strings, etc.)

**Root Cause:** **Mismatch between parser output and CSS expectations**

---

## How Syntax Highlighting Works in Bengal

### Option 1: Python-Markdown (Server-Side)

**Parser Output:**
```html
<div class="highlight">
<pre><span></span><code><span class="k">def</span> <span class="nf">hello</span><span class="p">():</span>
    <span class="nb">print</span><span class="p">(</span><span class="s1">&#39;world&#39;</span><span class="p">)</span>
</code></pre>
</div>
```

**How it works:**
1. Python-Markdown has Pygments extension built-in
2. At build time, Pygments parses code and wraps each token in `<span class="X">` 
3. CSS targets these classes (`.highlight .k` for keywords, `.highlight .s1` for strings)

**CSS:** `bengal/themes/default/assets/css/components/code.css`
```css
.highlight .k { color: #e74c3c; font-weight: bold; }  /* Keywords */
.highlight .s1 { color: #2ecc71; }                    /* Strings */
.highlight .nf { color: #3498db; font-weight: bold; } /* Functions */
```

**Pros:**
- ✅ Works immediately (no JavaScript)
- ✅ Consistent across all browsers
- ✅ SEO-friendly (colors in HTML)
- ✅ Works with JS disabled

**Cons:**
- ❌ Slower (Pygments adds ~15ms per code block)
- ❌ Larger HTML files (more `<span>` tags)

---

### Option 2: Mistune (Client-Side)

**Parser Output:**
```html
<pre><code class="language-python">def hello():
    print('world')
</code></pre>
```

**How it should work:**
1. Mistune outputs plain code with `language-X` class
2. Client-side JS library (Prism.js or Highlight.js) runs on page load
3. JS finds all `code.language-X` elements and wraps tokens in `<span>` tags
4. CSS targets those classes

**Current Problem:** Bengal theme has CSS for `.highlight` classes but no client-side JS!

**Current CSS expects:** `.highlight .k`, `.highlight .s1`, etc. (Pygments style)  
**Mistune outputs:** `<code class="language-python">` (Prism/Highlight.js style)  
**Result:** CSS doesn't match, no highlighting

---

## Solutions

### Solution 1: Add Client-Side Highlighting (Recommended for Mistune) ✅

**Add Prism.js or Highlight.js to theme:**

**File:** `bengal/themes/default/templates/base.html`
```html
<!-- Option A: Prism.js -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>

<!-- Option B: Highlight.js -->
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script>hljs.highlightAll();</script>
```

**Update CSS to target Prism/Highlight.js classes:**

**File:** `bengal/themes/default/assets/css/components/code.css`
```css
/* Keep existing .highlight styles for Python-Markdown */

/* ADD: Prism.js styles for Mistune */
.token.keyword { color: #e74c3c; font-weight: bold; }
.token.string { color: #2ecc71; }
.token.function { color: #3498db; font-weight: bold; }
.token.number { color: #e67e22; }
.token.operator { color: #e74c3c; }
.token.comment { color: #6c757d; font-style: italic; }
```

**Pros:**
- ✅ Fast builds (no server-side processing)
- ✅ Smaller HTML files
- ✅ Works great with Mistune
- ✅ Supports 200+ languages
- ✅ Easy to swap themes

**Cons:**
- ❌ Requires JavaScript
- ❌ Flash of unstyled code (FOUC) before JS loads
- ❌ Slightly slower page load

---

### Solution 2: Add Pygments Extension to Mistune

**Create custom Mistune plugin:**

```python
# bengal/rendering/mistune_plugins.py

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

def code_highlight(self, code, lang=None):
    """Override Mistune's code renderer to use Pygments."""
    if lang:
        try:
            lexer = get_lexer_by_name(lang, stripall=True)
            formatter = HtmlFormatter(cssclass='highlight')
            return highlight(code, lexer, formatter)
        except Exception:
            pass
    
    # Fallback to plain code
    return f'<pre><code class="{lang}">{code}</code></pre>'

# In MistuneParser.__init__:
md.renderer.code = code_highlight
```

**Pros:**
- ✅ Reuses existing `.highlight` CSS
- ✅ No JavaScript required
- ✅ Consistent with Python-Markdown output

**Cons:**
- ❌ Slower builds (Pygments is slow)
- ❌ Defeats purpose of using Mistune (which is fast)
- ❌ Larger HTML files

---

### Solution 3: Hybrid Approach

**Make syntax highlighting configurable:**

**File:** `bengal.toml`
```toml
[build]
markdown_engine = "mistune"  # or "python-markdown"
syntax_highlighting = "client"  # or "server" or "none"
```

**Implementation:**
```python
class MistuneParser(BaseMarkdownParser):
    def __init__(self, config):
        # ...
        syntax_mode = config.get('syntax_highlighting', 'client')
        
        if syntax_mode == 'server':
            # Use Pygments plugin
            self.md.renderer.code = self._pygments_code
        # else: use default (client-side with language-X classes)
```

**Pros:**
- ✅ Best of both worlds
- ✅ User choice
- ✅ Easy migration between parsers

**Cons:**
- ⚠️ More complexity
- ⚠️ Need to maintain both paths

---

## Recommendation

### Short-Term (Quick Fix) ✅

**Add Prism.js to default theme for client-side highlighting.**

1. Add Prism.js CDN links to `base.html`
2. Add Prism CSS classes to `code.css`
3. Document in theme README

**Time:** 30 minutes  
**Impact:** Syntax highlighting works immediately

---

### Long-Term (Best Practice) ✅

**Make syntax highlighting configurable per parser:**

1. Python-Markdown → Keep using built-in Pygments (server-side)
2. Mistune → Default to client-side (Prism.js)
3. Allow users to override via config

**Benefits:**
- Each parser uses its optimal approach
- Users can opt-out (e.g., for faster builds)
- Theme works with both parsers

---

## Implementation Plan

### Phase 1: Fix Mistune Theme ✅

```bash
# 1. Update base.html template
# 2. Add Prism.js links
# 3. Update code.css with Prism classes
# 4. Test build
```

### Phase 2: Make Configurable (Optional)

```bash
# 1. Add syntax_highlighting config option
# 2. Update MistuneParser to check config
# 3. Update PythonMarkdownParser to check config
# 4. Document in bengal.toml.example
```

### Phase 3: Optimize (Optional)

```bash
# 1. Bundle Prism.js locally (no CDN)
# 2. Only include needed language packs
# 3. Minify and cache-bust
```

---

## Testing

### Manual Test
```bash
# 1. Create test page with code blocks
echo '```python\ndef test(): pass\n```' > test.md

# 2. Build
bengal build

# 3. Open in browser
# 4. Verify code has colors
```

### Visual Checklist
- [ ] Keywords are red
- [ ] Strings are green
- [ ] Functions are blue
- [ ] Comments are gray/italic
- [ ] Numbers are orange
- [ ] No flash of unstyled code

---

## Current Status

**Python-Markdown:** ✅ Syntax highlighting works (server-side Pygments)  
**Mistune:** ❌ No highlighting (outputs `language-X`, no JS to process it)

**Why tests pass:** Tests only check HTML structure, not visual appearance

---

## Files to Modify

### 1. Theme Template (Add JS)
**File:** `bengal/themes/default/templates/base.html`
```html
<!-- Before </body> -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
<!-- Add other languages as needed -->
```

### 2. Theme CSS (Add Prism Styles)
**File:** `bengal/themes/default/assets/css/components/code.css`
```css
/* Add after existing .highlight styles */

/* Prism.js token colors (for Mistune) */
.token.keyword { color: #e74c3c; font-weight: bold; }
.token.string { color: #2ecc71; }
.token.function { color: #3498db; font-weight: bold; }
/* ... etc ... */
```

### 3. Documentation
**File:** `ARCHITECTURE.md` or theme README
```markdown
## Syntax Highlighting

- **Python-Markdown:** Server-side via Pygments
- **Mistune:** Client-side via Prism.js
- Both use same visual theme
```

---

## Performance Impact

### With Client-Side Highlighting (Prism.js)

**Page Load:**
- Prism.js core: ~10 KB gzipped
- Language pack: ~2 KB each
- Total: ~20 KB for Python + JS

**Rendering:**
- Runs on page load: ~5-10ms per code block
- Imperceptible to users

**Build Time:**
- No impact (highlighting happens in browser)

### With Server-Side Highlighting (Pygments)

**Page Load:**
- No JavaScript needed
- HTML is ~20% larger (all the `<span>` tags)

**Rendering:**
- Instant (already in HTML)

**Build Time:**
- +15ms per code block
- 100 code blocks = +1.5s build time

---

## Conclusion

**Problem:** Mistune outputs `language-X` classes, but theme CSS expects `.highlight` classes

**Solution:** Add Prism.js for client-side highlighting (recommended for Mistune)

**Alternative:** Add Pygments plugin to Mistune (but defeats its speed advantage)

**Best Practice:** Make it configurable, let each parser use its optimal approach

