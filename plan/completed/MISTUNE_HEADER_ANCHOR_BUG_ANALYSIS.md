# Mistune Header Anchor Bug - Root Cause Analysis

**Date:** October 3, 2025  
**Status:** Bug Found - Critical

---

## The Bug

### Location
`bengal/rendering/parser.py`, lines 166-175

### Code
```python
def parse_with_toc(self, content: str, metadata: Dict[str, Any]) -> tuple[str, str]:
    """Parse Markdown content and extract table of contents."""
    html = self.md(content)
    toc = self._extract_toc(html)  # ← Modifies html internally but...
    return html, toc                # ← Returns ORIGINAL html!
```

### The Problem

**`_extract_toc()` modifies `html` in place** (line 205):
```python
html = html.replace(old_heading, new_heading, 1)
```

**BUT** Python strings are **immutable**! The local variable `html` inside `_extract_toc()` gets reassigned, but the `html` variable in `parse_with_toc()` is NOT modified.

### Proof

```python
def extract_toc(html):
    html = html.replace('foo', 'bar')  # Local reassignment
    return ''

original = 'foo'
result = extract_toc(original)
print(original)  # Still 'foo'! Not modified!
```

---

## Why It Seemed to Work

The string replacement logic IS correct:
```python
old = '<h2>Test Heading</h2>'
new = '<h2 id="test-heading">Test Heading<a>¶</a></h2>'
html = html.replace(old, new, 1)
```

**This works!** But only in the local scope.

---

## The Fix (Simple)

### Option 1: Return Modified HTML
```python
def parse_with_toc(self, content: str, metadata: Dict[str, Any]) -> tuple[str, str]:
    """Parse Markdown content and extract table of contents."""
    html = self.md(content)
    html, toc = self._extract_toc(html)  # ← Get modified HTML back
    return html, toc

def _extract_toc(self, html: str) -> tuple[str, str]:
    """Extract TOC and return modified HTML."""
    # ... extract headings ...
    
    # Modify HTML
    for level, id_attr, title in headings:
        if not id_attr:
            old = f'<h{level}>{title}</h{level}>'
            new = f'<h{level} id="{slug}">{title}<a class="headerlink">¶</a></h{level}>'
            html = html.replace(old, new, 1)
    
    # Build TOC
    toc_html = '...'
    
    return html, toc_html  # ← Return BOTH
```

### Option 2: BeautifulSoup (More Robust)

```python
def parse_with_toc(self, content: str, metadata: Dict[str, Any]) -> tuple[str, str]:
    """Parse Markdown and extract TOC with proper heading anchors."""
    html = self.md(content)
    html = self._inject_heading_anchors(html)
    toc = self._extract_toc_from_anchored_html(html)
    return html, toc

def _inject_heading_anchors(self, html: str) -> str:
    """Inject IDs and headerlinks into headings."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        for level in [2, 3, 4]:
            for heading in soup.find_all(f'h{level}'):
                if heading.get('id'):
                    continue
                
                title = heading.get_text().strip()
                slug = self._slugify(title)
                
                heading['id'] = slug
                anchor = soup.new_tag('a', href=f'#{slug}', **{'class': 'headerlink'})
                anchor.string = '¶'
                heading.append(anchor)
        
        return str(soup)
    except ImportError:
        return html
```

---

## Architectural Comparison

### Current (Broken)
```
Parse Markdown → Extract TOC (modifies local copy) → Return original HTML
                    ↓ (lost!)
                 Modified HTML with anchors
```

### Option 1: Return Modified HTML ✅
```
Parse Markdown → Extract TOC → Return modified HTML + TOC
                    ↓
                 Modifies and returns
```

**Pros:**
- ✅ Minimal change (1 line)
- ✅ Fast (string operations)
- ✅ No new dependencies
- ✅ Follows current pattern

**Cons:**
- ⚠️ String replacement still fragile for edge cases
- ⚠️ Tightly couples TOC extraction with HTML modification

### Option 2: Separate Concerns ✅✅
```
Parse Markdown → Inject Anchors → Extract TOC from anchored HTML
                    ↓                  ↓
                 HTML with IDs      Parse IDs for TOC
```

**Pros:**
- ✅ Clear separation of concerns
- ✅ Each function does one thing
- ✅ Robust (HTML parser understands HTML)
- ✅ Handles edge cases (whitespace, attributes, etc.)
- ✅ BeautifulSoup already a dependency

**Cons:**
- ⚠️ Slightly more code (~15 lines)
- ⚠️ BeautifulSoup overhead (parsing HTML twice)

---

## Performance Analysis

### Option 1: String Replace
```python
# For a 1000-line document:
- Regex match: ~0.1ms
- String replace: ~0.05ms per heading
- Total: ~0.5ms for 10 headings
```

### Option 2: BeautifulSoup
```python
# For a 1000-line document:
- Parse HTML: ~2-3ms
- Modify DOM: ~0.1ms per heading
- Serialize: ~1ms
- Total: ~4ms for 10 headings
```

**Overhead:** ~3.5ms per page
**Impact:** For 100 pages: ~350ms total (~0.5% of build time)

**Verdict:** Negligible for better robustness

---

## Recommendation: Option 2 (Separate Concerns)

### Why

1. **Follows Bengal Architecture**
   - Clear separation: inject anchors, then extract TOC
   - Single responsibility per method
   - Testable in isolation

2. **More Robust**
   - Handles all HTML variations
   - No edge cases with whitespace/formatting
   - Works with existing IDs

3. **Future-Proof**
   - Easy to add h1, h5, h6 support
   - Easy to customize anchor format
   - Can add options (anchor position, symbol, etc.)

4. **Already a Dependency**
   - BeautifulSoup used in health checks
   - No new dependency to add
   - Well-tested, reliable

---

## Implementation

### Step 1: Fix the Return Bug (5 min)
```python
def parse_with_toc(self, content: str, metadata: Dict[str, Any]) -> tuple[str, str]:
    html = self.md(content)
    html, toc = self._extract_toc(html)  # ← Get modified HTML
    return html, toc

def _extract_toc(self, html: str) -> tuple[str, str]:  # ← Return tuple
    # ... existing logic ...
    return html, toc_html  # ← Return both
```

### Step 2: Refactor to BeautifulSoup (30 min)
```python
def parse_with_toc(self, content: str, metadata: Dict[str, Any]) -> tuple[str, str]:
    """Parse Markdown and extract TOC."""
    html = self.md(content)
    html = self._inject_heading_anchors(html)
    toc = self._extract_toc_from_html(html)
    return html, toc

def _inject_heading_anchors(self, html: str) -> str:
    """Add IDs and headerlinks to headings."""
    # BeautifulSoup implementation
    pass

def _extract_toc_from_html(self, html: str) -> str:
    """Extract TOC from HTML with IDs."""
    # Parse headings that now have IDs
    pass
```

---

## Testing Strategy

### Unit Tests
```python
def test_heading_anchors_added():
    parser = MistuneParser()
    html, toc = parser.parse_with_toc("## Test\n\nContent", {})
    assert 'id="test"' in html
    assert 'class="headerlink"' in html
    assert '¶' in html or '&para;' in html

def test_toc_extraction():
    parser = MistuneParser()
    html, toc = parser.parse_with_toc("## One\n\n### Two\n\n## Three", {})
    assert 'href="#one"' in toc
    assert 'href="#two"' in toc
    assert 'href="#three"' in toc

def test_existing_ids_preserved():
    parser = MistuneParser()
    # If Mistune adds IDs in future, don't duplicate
    pass

def test_special_chars_in_headings():
    parser = MistuneParser()
    html, toc = parser.parse_with_toc("## Test & Code", {})
    # Should handle & and other special chars
    pass
```

### Integration Tests
```python
def test_full_build_has_anchors():
    # Build site
    site.build()
    
    # Check output
    with open('public/docs/template-system/index.html') as f:
        html = f.read()
        assert 'class="headerlink"' in html
        assert 'id="template-context"' in html
```

---

## Migration

### Backwards Compatibility
- ✅ No API changes (same input/output)
- ✅ No config changes needed
- ✅ Works with both parsers (python-markdown, mistune)
- ✅ Output format identical to python-markdown

### Testing
- ✅ Run full test suite
- ✅ Visual check of quickstart site
- ✅ Verify anchor links work in browser
- ✅ Check TOC navigation

---

## Summary

**Bug:** `_extract_toc()` modifies local variable, doesn't return modified HTML

**Quick Fix:** Change return signature to `tuple[str, str]`

**Better Fix:** Separate anchor injection from TOC extraction using BeautifulSoup

**Impact:** ~4ms per page, negligible overhead for much better robustness

**Effort:** 
- Quick fix: 5 minutes
- Proper fix: 30-45 minutes including tests

**Recommendation:** Implement proper fix (Option 2) for long-term maintainability

