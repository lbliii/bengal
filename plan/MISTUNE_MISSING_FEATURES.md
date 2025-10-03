# Mistune Parser - Missing Features Analysis

**Date:** October 3, 2025  
**Status:** Bug Investigation

---

## Issues Found

### 1. ❌ Header Anchors (¶) Not Working

**Expected:**
```html
<h2 id="template-context">Template Context<a class="headerlink" href="#template-context" title="Permanent link">¶</a></h2>
```

**Actual:**
```html
<h2>Template Context</h2>
```

**Impact:**
- No clickable anchor links on headings
- No deep linking to sections
- Poor documentation UX

### 2. ✅ Syntax Highlighting Classes (Working)

**Observed:**
```html
<pre><code class="language-jinja2">{{ page.title }}</code></pre>
```

**Status:** Working correctly! The `language-*` class is present for JS highlighter.

---

## Root Cause Analysis

### Header Anchor Injection Bug

**Location:** `bengal/rendering/parser.py`, line 201-205

**Code:**
```python
if not id_attr:
    old_heading = f'<h{level}>{title}</h{level}>'
    new_heading = f'<h{level} id="{slug}">{title}<a class="headerlink" href="#{slug}" title="Permalink">¶</a></h{level}>'
    html = html.replace(old_heading, new_heading, 1)
```

**Problems:**

1. **String Replace is Fragile**
   - Mistune might output: `<h2>\nTemplate Context\n</h2>`
   - Code expects: `<h2>Template Context</h2>`
   - No match → no replacement!

2. **HTML Might Already Have IDs**
   - Mistune adds IDs automatically in some cases
   - The regex pattern at line 188 looks for existing IDs
   - But extraction and injection logic don't match

3. **TOC Extraction vs HTML Modification**
   - TOC extraction: Uses regex to find headings
   - ID injection: Uses string replace
   - These operate on different HTML (before vs after TOC extraction)

### Why This Worked in Python-Markdown

**Python-Markdown:**
- Has built-in TOC extension
- Adds IDs and headerlinks during parsing
- Single-pass, integrated

**Mistune:**
- No built-in TOC support
- We extract TOC post-parsing
- Trying to inject IDs post-hoc
- String manipulation is brittle

---

## Testing the Theory

### Quick Test
```python
import re

# Mistune output (simplified)
html = """<h2>Template Context</h2>
<p>Some content</p>
<h2>Available Templates</h2>"""

# Our regex
heading_pattern = re.compile(r'<h([2-4])(?:\s+id="([^"]*)")?>([^<]+)</h\1>', re.IGNORECASE)
matches = heading_pattern.findall(html)

print(matches)
# [('2', '', 'Template Context'), ('2', '', 'Available Templates')]

# Try to replace
old = '<h2>Template Context</h2>'
new = '<h2 id="template-context">Template Context<a class="headerlink" href="#template-context">¶</a></h2>'
result = html.replace(old, new, 1)

print(result)
# Works IF format matches exactly
```

**Problem:** If Mistune outputs with newlines or whitespace:
```html
<h2>
Template Context
</h2>
```
Our exact string match fails!

---

## Solution Options

### Option 1: Regex Replace (Quick Fix)

```python
def _inject_heading_anchors(self, html: str, headings: list) -> str:
    """Inject ID and headerlink into headings using regex."""
    
    for level, existing_id, title in headings:
        if existing_id:
            continue  # Already has ID
        
        slug = self._slugify(title)
        
        # Use regex to find and replace (handles whitespace)
        old_pattern = re.compile(
            rf'<h{level}>(.*?{re.escape(title)}.*?)</h{level}>',
            re.DOTALL | re.IGNORECASE
        )
        
        new_heading = f'<h{level} id="{slug}">{title}<a class="headerlink" href="#{slug}" title="Permanent link">¶</a></h{level}>'
        
        html = old_pattern.sub(new_heading, html, count=1)
    
    return html
```

### Option 2: Use Mistune Plugin (Proper Fix)

```python
# Custom mistune plugin to add heading IDs during parsing
from mistune.directives import DirectivePlugin

class HeadingAnchorPlugin:
    """Add IDs and headerlinks to headings during parsing."""
    
    def parse(self, block, m, state):
        # Intercept heading parsing
        # Add ID and headerlink during parse, not after
        pass

# Register with mistune
md = mistune.create_markdown(
    plugins=[
        'table',
        'strikethrough', 
        HeadingAnchorPlugin(),  # Add this
    ]
)
```

### Option 3: Use BeautifulSoup (Robust Fix)

```python
def _inject_heading_anchors(self, html: str) -> str:
    """Inject heading anchors using HTML parsing."""
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html, 'html.parser')
    
    for level in [2, 3, 4]:  # h2-h4
        for heading in soup.find_all(f'h{level}'):
            # Skip if already has ID
            if heading.get('id'):
                continue
            
            # Create slug from text
            title = heading.get_text()
            slug = self._slugify(title)
            
            # Add ID
            heading['id'] = slug
            
            # Add headerlink anchor
            anchor = soup.new_tag('a', 
                                 href=f'#{slug}',
                                 title='Permanent link',
                                 **{'class': 'headerlink'})
            anchor.string = '¶'
            heading.append(anchor)
    
    return str(soup)
```

---

## Comparison

| Approach | Pros | Cons |
|----------|------|------|
| **String Replace (Current)** | Simple, fast | ❌ Brittle, fails with whitespace |
| **Regex Replace** | Handles whitespace | ⚠️ Still hacky, edge cases |
| **Mistune Plugin** | Proper integration | 🔧 Requires plugin dev |
| **BeautifulSoup** | Robust, reliable | 📦 New dependency |

---

## Recommendation

### Short Term: Option 3 (BeautifulSoup)

**Why:**
- ✅ Reliable (HTML parser understands HTML)
- ✅ Handles all edge cases
- ✅ We already use BeautifulSoup (in health checks)
- ✅ ~10 lines of code
- ✅ Easy to test

**Implementation:**
```python
# In bengal/rendering/parser.py, MistuneParser class

def parse_with_toc(self, content: str, metadata: Dict[str, Any]) -> tuple[str, str]:
    """Parse Markdown and extract TOC with proper heading anchors."""
    html = self.md(content)
    
    # Inject heading anchors (robust)
    html = self._inject_heading_anchors(html)
    
    # Extract TOC from modified HTML
    toc = self._extract_toc(html)
    
    return html, toc

def _inject_heading_anchors(self, html: str) -> str:
    """Inject IDs and headerlinks into headings."""
    try:
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        for level in [2, 3, 4]:  # h2-h4
            for heading in soup.find_all(f'h{level}'):
                if heading.get('id'):
                    continue
                
                title = heading.get_text().strip()
                slug = self._slugify(title)
                
                heading['id'] = slug
                
                # Add headerlink
                anchor = soup.new_tag('a',
                                     href=f'#{slug}',
                                     title='Permanent link',
                                     **{'class': 'headerlink'})
                anchor.string = '¶'
                heading.append(anchor)
        
        return str(soup)
    
    except ImportError:
        # Fallback if BeautifulSoup not available
        return html
```

### Long Term: Option 2 (Mistune Plugin)

Build a proper mistune plugin for heading anchors to avoid post-processing entirely.

---

## What About Syntax Highlighting?

### Status: ✅ Working!

**Evidence:**
```html
<pre><code class="language-jinja2">{{ page.title }}</code></pre>
```

The `language-*` class is present, which means:
- ✅ Mistune is detecting language from fenced code blocks
- ✅ Theme's JavaScript highlighter can use this
- ✅ No action needed

**If highlighting isn't showing visually:**
- Check theme CSS/JS is loading
- Check browser console for JS errors
- Verify highlighter library is included

---

## Implementation Plan

### Phase 1: Fix Header Anchors (1-2 hours)
```python
✅ Implement _inject_heading_anchors() with BeautifulSoup
✅ Update parse_with_toc() to use new method
✅ Remove brittle string replace code
✅ Test with various heading formats
```

### Phase 2: Verify Syntax Highlighting (30 min)
```python
✅ Check theme JS loads Prism/Highlight.js
✅ Verify language classes are correct
✅ Test in browser
```

### Phase 3: Testing (1 hour)
```python
✅ Unit tests for heading anchor injection
✅ Test with edge cases (special chars, long titles)
✅ Integration test with full build
✅ Visual verification in browser
```

---

## Verification

### Check Header Anchors
```bash
# Should find headerlinks
grep 'class="headerlink"' public/docs/template-system/index.html

# Should find heading IDs
grep '<h2 id=' public/docs/template-system/index.html
```

### Check Syntax Highlighting
```bash
# Should find language classes
grep 'class="language-' public/docs/template-system/index.html

# Check in browser
open http://localhost:8000/docs/template-system/
# Click on heading → URL should include #anchor
# Code blocks should have syntax colors
```

---

## Summary

**Issue:** Mistune parser's heading anchor injection is broken due to brittle string replacement.

**Impact:** 
- ❌ No ¶ links on headings
- ❌ No deep linking

**Fix:** Use BeautifulSoup for robust HTML manipulation

**Syntax highlighting:** Already working, no fix needed

**Effort:** ~2-3 hours to implement and test

