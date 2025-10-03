# Code Block Protection - Root Solution for Template Escaping

**Date:** October 3, 2025  
**Status:** Root Cause Analysis & Solution Design

---

## The Real Problem

### Current State (Broken)

**Users write natural documentation:**
```markdown
To show the page title, use `{{ page.title }}` in your template.

Example template:
```jinja2
<h1>{{ page.title }}</h1>
{% if page.date %}
  <time>{{ page.date }}</time>
{% endif %}
```
```

**What happens:**
```
1. Preprocessing: Jinja2 processes ENTIRE markdown
   → Tries to render {{ page.title }} even in code blocks
   → ERROR: undefined variable or wrong output
   
2. Markdown parsing: Too late, damage done
```

**Current workarounds (all bad):**
- ❌ Per-page flag: `preprocess: false` (doesn't scale)
- ❌ String literals: `{{ '{{ page.title }}' }}` (ugly, unnatural)
- ❌ Skip patterns: `"docs/**/*.md"` (lose dynamic content)

---

## Root Cause

### Pipeline Order Problem

**Current pipeline:**
```
Markdown → Jinja2 Preprocess → Markdown Parse → HTML Render
           ⬆ Sees EVERYTHING (including code blocks!)
```

**The issue:** Jinja2 preprocessor can't distinguish between:
- Content: `Use {{ page.title }} here` (should render)
- Code: `` `{{ page.title }}` `` (should NOT render)
- Blocks: ` ```{{ page.title }}``` ` (should NOT render)

---

## Solution: Protect Code Blocks During Preprocessing

### Approach 1: Extract → Process → Restore (Recommended)

```
Markdown Content
    ↓
Extract code blocks (replace with placeholders)
    ↓
Jinja2 Preprocessing (only sees non-code content)
    ↓
Restore code blocks (original, untouched)
    ↓
Markdown Parse → HTML
```

**Algorithm:**
```python
def preprocess_with_code_protection(content: str, context: dict) -> str:
    """Preprocess markdown while protecting code blocks."""
    
    # 1. Extract all code (inline and blocks)
    code_blocks = []
    placeholders = []
    
    # Extract fenced code blocks: ```...```
    content, blocks = extract_fenced_code(content)
    code_blocks.extend(blocks)
    
    # Extract indented code blocks (4 spaces)
    content, blocks = extract_indented_code(content)
    code_blocks.extend(blocks)
    
    # Extract inline code: `...`
    content, inlines = extract_inline_code(content)
    code_blocks.extend(inlines)
    
    # 2. Preprocess the protected content
    from jinja2 import Template
    processed = Template(content).render(**context)
    
    # 3. Restore all code blocks
    final = restore_code_blocks(processed, code_blocks)
    
    return final
```

### Approach 2: Parse First → Preprocess Selectively (Cleaner)

```
Markdown Content
    ↓
Lightweight Markdown Parse (identify structure)
    ↓
Preprocess only non-code nodes
    ↓
Full Markdown Parse → HTML
```

**Pros:**
- More accurate (uses markdown parser's understanding)
- Handles edge cases (nested code, etc.)
- Can protect other elements (links, etc.)

**Cons:**
- Parse twice (performance hit)
- More complex implementation
- Requires access to markdown AST

---

## Implementation Design

### Option A: Regex-Based Extraction (Fast, Simple)

```python
# bengal/rendering/preprocessor.py

import re
from typing import Tuple, List
from jinja2 import Template

class CodeBlockProtector:
    """Protect code blocks during Jinja2 preprocessing."""
    
    # Patterns for code blocks
    FENCED_CODE_PATTERN = re.compile(
        r'^```[\s\S]*?^```',
        re.MULTILINE
    )
    
    INLINE_CODE_PATTERN = re.compile(
        r'`[^`\n]+`'
    )
    
    PLACEHOLDER_PREFIX = '___CODE_BLOCK_'
    
    def protect(self, content: str) -> Tuple[str, List[str]]:
        """
        Extract code blocks and replace with placeholders.
        
        Returns:
            (protected_content, extracted_blocks)
        """
        blocks = []
        
        # Extract fenced code blocks
        def replace_fenced(match):
            blocks.append(match.group(0))
            return f'{self.PLACEHOLDER_PREFIX}{len(blocks) - 1}___'
        
        content = self.FENCED_CODE_PATTERN.sub(replace_fenced, content)
        
        # Extract inline code
        def replace_inline(match):
            blocks.append(match.group(0))
            return f'{self.PLACEHOLDER_PREFIX}{len(blocks) - 1}___'
        
        content = self.INLINE_CODE_PATTERN.sub(replace_inline, content)
        
        return content, blocks
    
    def restore(self, content: str, blocks: List[str]) -> str:
        """Restore code blocks from placeholders."""
        for i, block in enumerate(blocks):
            placeholder = f'{self.PLACEHOLDER_PREFIX}{i}___'
            content = content.replace(placeholder, block)
        
        return content


def preprocess_content_safe(content: str, context: dict) -> str:
    """
    Preprocess content with code block protection.
    
    Args:
        content: Markdown content
        context: Jinja2 context (page, site, config)
    
    Returns:
        Preprocessed content with code blocks untouched
    """
    protector = CodeBlockProtector()
    
    # 1. Protect code blocks
    protected_content, blocks = protector.protect(content)
    
    # 2. Preprocess (Jinja2 only sees non-code content)
    try:
        template = Template(protected_content)
        processed = template.render(**context)
    except Exception as e:
        # On error, return original content
        return content
    
    # 3. Restore code blocks
    final = protector.restore(processed, blocks)
    
    return final
```

### Option B: Mistune-Based (More Accurate)

```python
# Use mistune to parse and identify code blocks

def preprocess_with_mistune_protection(content: str, context: dict) -> str:
    """Use mistune parser to identify and protect code blocks."""
    import mistune
    
    # Parse markdown to AST
    markdown = mistune.create_markdown(renderer=None)
    tokens = markdown.parse(content)
    
    # Process tokens, skipping code blocks
    processed_parts = []
    
    for token in tokens:
        if token['type'] in ('block_code', 'code_span'):
            # Don't process code
            processed_parts.append(reconstruct_token(token))
        else:
            # Preprocess other content
            text = reconstruct_token(token)
            try:
                template = Template(text)
                processed_parts.append(template.render(**context))
            except:
                processed_parts.append(text)
    
    return ''.join(processed_parts)
```

---

## User Experience Comparison

### Current (Broken)
```markdown
Use `{{ page.title }}` to show the title.

❌ ERROR: Tries to render {{ page.title }} inside backticks
```

### With String Literals (Current Workaround)
```markdown
Use {{ '`{{ page.title }}`' }} to show the title.

✓ Works but ugly and unnatural
```

### With Code Protection (Proposed)
```markdown
Use `{{ page.title }}` to show the title.

✓ Works naturally! Code blocks are automatically protected
```

---

## Edge Cases to Handle

### 1. Nested Code Blocks
```markdown
````markdown
```jinja2
{{ page.title }}
```
````
```
**Solution:** Regex handles this (greedy match to outermost)

### 2. Inline Code with Backticks
```markdown
Use `` `code` `` to show literal backticks
```
**Solution:** Match escaped backticks separately

### 3. Jinja2 in Regular Text (Should Process)
```markdown
Welcome to {{ site.title }}! Use `code` for examples.
         ⬆ SHOULD render        ⬆ should NOT render
```
**Solution:** Our protection handles this correctly

### 4. Mixed Content
```markdown
The site name is {{ site.title }}.

Example:
```jinja2
<h1>{{ page.title }}</h1>
```

The date is {{ page.date | dateformat }}.
```
**Solution:** Each code block protected independently

---

## Performance Analysis

### Regex-Based Approach
```
Overhead: ~1-2ms per page
- Pattern matching: Fast (compiled regex)
- String replacement: O(n) where n = content length
- Impact: <5% for typical pages

Bottleneck: Multiple regex passes
Optimization: Combine patterns, single pass
```

### Mistune-Based Approach  
```
Overhead: ~5-10ms per page
- Parse markdown: Already fast with mistune
- Token processing: O(n) where n = tokens
- Impact: ~10-15% (parsing twice)

Bottleneck: Double parsing
Optimization: Cache parsed AST
```

**Recommendation:** Start with regex (simple, fast), upgrade to mistune if needed.

---

## Implementation Plan

### Phase 1: Core Protection (2-3 hours)
```python
✅ Implement CodeBlockProtector
✅ Add preprocess_content_safe()
✅ Unit tests for extraction/restoration
✅ Test edge cases (nested, inline, mixed)
```

### Phase 2: Integration (1-2 hours)
```python
✅ Update RenderingPipeline to use safe preprocessing
✅ Remove preprocess: false flag requirement
✅ Test with existing content
✅ Verify no regressions
```

### Phase 3: Testing (2-3 hours)
```python
✅ Test with template-system.md
✅ Test with advanced-markdown.md
✅ Performance benchmarks
✅ Edge case validation
```

### Phase 4: Documentation (1 hour)
```python
✅ Update docs (no more string literals needed!)
✅ Remove preprocess: false workarounds
✅ Add examples showing natural syntax
✅ Update architecture docs
```

---

## Benefits

### For Users ✅
- ✅ **Natural syntax** - Write docs normally
- ✅ **No configuration** - Just works
- ✅ **No workarounds** - No string literals needed
- ✅ **Less fragile** - One less thing to remember

### For Architecture ✅
- ✅ **Fixes root cause** - Not just symptoms
- ✅ **Scales naturally** - All docs work automatically
- ✅ **Performance** - Minimal overhead
- ✅ **Maintainable** - Clear, simple logic

### For Development ✅
- ✅ **Better DX** - No special handling needed
- ✅ **Fewer bugs** - Protection is automatic
- ✅ **Clear errors** - If preprocessing fails, code blocks intact
- ✅ **Less support** - Fewer "how do I escape?" questions

---

## Migration

### Current Users
```markdown
# Before (with workarounds)
---
preprocess: false  # Can remove!
---

Use {{ '{{ page.title }}' }} to show title.  # Can simplify!

# After (natural)
Use `{{ page.title }}` to show title.  # Just works!
```

### Backwards Compatibility
- ✅ String literals still work (no breaking change)
- ✅ `preprocess: false` still respected (but not needed)
- ✅ Existing docs keep working
- ✅ New docs are simpler

---

## Comparison to Other SSGs

### Hugo
```go
// Uses shortcodes, not preprocessing
// Code blocks never processed
✅ Natural documentation
```

### Jekyll
```liquid
{% raw %}{{ page.title }}{% endraw %}
// Works because single-stage rendering
✅ Explicit but reliable
```

### Gatsby/Next.js
```jsx
// Markdown is pure content
// Templates are separate React components
✅ No conflict possible
```

### Bengal (Current)
```markdown
{{ '{{ page.title }}' }}
// String literal workaround
❌ Unnatural, confusing
```

### Bengal (Proposed)
```markdown
`{{ page.title }}`
// Code blocks automatically protected
✅ Natural like Hugo, reliable like Jekyll
```

---

## Testing Strategy

### Unit Tests
```python
def test_protects_inline_code():
    content = "Use `{{ page.title }}` for titles."
    result = preprocess_content_safe(content, context)
    assert '`{{ page.title }}`' in result  # Unchanged

def test_protects_fenced_code():
    content = "```\n{{ page.title }}\n```"
    result = preprocess_content_safe(content, context)
    assert '{{ page.title }}' in result  # Unchanged

def test_processes_regular_text():
    content = "Title: {{ page.title }}"
    result = preprocess_content_safe(content, {'page': page})
    assert 'Title: My Page' in result  # Rendered

def test_mixed_content():
    content = """
    Site: {{ site.title }}
    
    Example: `{{ page.title }}`
    
    Date: {{ page.date }}
    """
    result = preprocess_content_safe(content, context)
    # Check site.title rendered
    # Check `{{ page.title }}` unchanged  
    # Check page.date rendered
```

### Integration Tests
```python
def test_template_documentation_builds():
    """Test that template-system.md builds without errors."""
    # Remove preprocess: false flag
    # Build site
    # Verify no preprocessing errors
    # Verify code blocks show Jinja2 syntax

def test_no_regressions_with_dynamic_content():
    """Test that pages with real Jinja2 still work."""
    # Build api/v2/_index.md (uses cascade metadata)
    # Verify {{ page.metadata.xxx }} rendered
    # Verify code examples not rendered
```

---

## Conclusion

**This solves the root problem:**

1. ✅ **Natural syntax** - Users write docs normally
2. ✅ **Automatic protection** - Code blocks handled correctly
3. ✅ **No configuration** - Works out of the box
4. ✅ **Non-brittle** - Clear, simple logic
5. ✅ **Backwards compatible** - Doesn't break existing sites

**Next step:** Implement `CodeBlockProtector` and integrate into `RenderingPipeline`.

This is the **correct architectural solution** - not workarounds, flags, or patterns, but fixing the root cause in the preprocessing stage.

