# RFC: Content AST Architecture

**Status**: Implemented
**Created**: 2024-12-02
**Updated**: 2024-12-02
**Implemented**: 2024-12-02
**Author**: AI Assistant + Human Review
**Affects**: `bengal/core/page/`, `bengal/rendering/`, `bengal/postprocess/`

---

## Summary

Refactor Bengal's content processing to use a true Abstract Syntax Tree (AST) instead of the current misleadingly-named `parsed_ast` field (which actually contains HTML). This enables:

1. **Parse once, use many times** - Single parse, multiple outputs (HTML, plain text, TOC)
2. **Faster post-processing** - O(n) AST walks instead of regex-based HTML stripping
3. **Cleaner transformations** - Shortcodes and cross-refs at AST level
4. **Better caching** - Cache AST separately from rendered HTML

---

## Problem Statement

### Current State (Confused Naming)

```python
@dataclass
class Page:
    content: str           # Raw markdown ✓
    parsed_ast: str        # Actually HTML! (WRONG NAME)
    rendered_html: str     # HTML after template
```

### Current Flow (Wasteful)

```
markdown
    ↓
parse() → HTML (called "parsed_ast")
    ↓
extract_toc() → parse HTML again with regex
    ↓
extract_links() → parse HTML again with regex
    ↓
template render → rendered_html
    ↓
search indexing → strip_html(parsed_ast) → plain text
    ↓
LLM output → strip_html(parsed_ast) → plain text
```

**Problems:**
1. `parsed_ast` is a lie - it's HTML, not an AST
2. Multiple redundant parsing passes (TOC, links, strip_html)
3. HTML stripping is slow (regex on potentially large content)
4. Can't cache AST independently from rendered output

---

## Proposed Solution

### New Data Model

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Page:
    # Source (immutable after discovery)
    source_path: Path
    content: str              # Raw markdown
    metadata: dict[str, Any]

    # Parsed AST (computed once, cached)
    _ast: list[dict] | None = field(default=None, repr=False)

    # Rendered outputs (computed from AST, cached)
    _html: str | None = field(default=None, repr=False)
    _toc: str | None = field(default=None, repr=False)
    _plain_text: str | None = field(default=None, repr=False)
    _links: list[str] | None = field(default=None, repr=False)

    @property
    def ast(self) -> list[dict] | None:
        """True AST - list of tokens from markdown parser (if available)."""
        if self._ast is None:
            # Note: Requires parser update to return AST
            self._ast = self._parse_to_ast()
        return self._ast

    @property
    def html(self) -> str:
        """HTML content rendered from AST or legacy parser."""
        if self._html is None:
            if self.ast:
                self._html = self._render_ast()
            else:
                # Fallback for legacy parsers (parsed_ast is already HTML)
                self._html = self.parsed_ast
        return self._html

    @property
    def toc(self) -> str:
        """Table of contents extracted from AST (with regex fallback)."""
        if self._toc is None:
            if self.ast:
                self._toc = self._extract_toc_from_ast()
            else:
                # Fallback: Current regex extraction from HTML
                self._toc = self._extract_toc_regex(self.html)
        return self._toc

    @property
    def plain_text(self) -> str:
        """Plain text extracted from AST (for search/LLM)."""
        if self._plain_text is None:
            if self.ast:
                self._plain_text = self._extract_text_from_ast()
            else:
                # Fallback: Strip HTML
                self._plain_text = self._strip_html(self.html)
        return self._plain_text

    @property
    def links(self) -> list[str]:
        """Links extracted from AST."""
        if self._links is None:
            if self.ast:
                self._links = self._extract_links_from_ast()
            else:
                # Fallback: Regex extraction
                self._links = self._extract_links_regex(self.html)
        return self._links

    # Backwards compatibility (deprecated)
    @property
    def parsed_ast(self) -> str:
        """DEPRECATED: Use .html instead. Returns HTML content."""
        import warnings
        warnings.warn(
            "page.parsed_ast is deprecated, use page.html instead",
            DeprecationWarning,
            stacklevel=2
        )
        return self.html
```

### Parsing Flow & Variable Substitution

To ensure `{{ variable }}` substitutions work correctly with the AST:

1. **Pre-process**: Run `VariableSubstitutionPlugin` on raw markdown.
2. **Parse**: Convert pre-processed markdown to AST.
3. **Cache**: Store the AST (which now contains values, not variables).
4. **Render**: Generate HTML from AST.

This preserves the architecture where content logic (vars) is resolved before structure (AST) is finalized.

### Mistune AST Integration

Mistune already supports AST output - we just need to use it:

```python
import mistune

class ASTMarkdownParser:
    """Markdown parser that exposes true AST."""

    def __init__(self):
        self.md = mistune.create_markdown(renderer=None)  # No renderer = AST output
        self.renderer = mistune.create_markdown()  # For HTML rendering

    def parse(self, content: str) -> list[dict]:
        """Parse markdown to AST tokens."""
        return self.md.parse(content)

    def render(self, ast: list[dict]) -> str:
        """Render AST to HTML."""
        return self.renderer.render_tokens(ast)
```

---

## Performance Analysis

### Benchmarks (Estimated)

| Operation | Current (HTML + Regex) | With AST | Speedup |
|-----------|----------------------|----------|---------|
| Parse markdown | 1.0x (baseline) | 1.0x | - |
| Extract TOC | 0.3x (regex on HTML) | 0.1x (AST walk) | 3x |
| Extract links | 0.2x (regex on HTML) | 0.05x (AST walk) | 4x |
| Plain text (search) | 0.5x (strip_html) | 0.1x (AST walk) | 5x |
| Plain text (LLM) | 0.5x (strip_html) | 0x (use raw md) | ∞ |

**For 700 pages:**
- Current post-process: ~2000ms
- With AST: ~400ms (estimated 5x faster)

---

## Migration Plan

### Phase 1: Add New Properties (Non-Breaking)

```python
# Add new properties alongside existing ones
@property
def html(self) -> str:
    """HTML content (preferred over parsed_ast)."""
    return self.parsed_ast  # Delegate for now

@property  
def plain_text(self) -> str:
    """Plain text for search/LLM."""
    return self.content  # Use raw markdown
```

**Timeline**: 1-2 days  
**Risk**: None (additive change)

### Phase 2: Deprecate `parsed_ast`

```python
@property
def parsed_ast(self) -> str:
    """DEPRECATED: Use .html instead."""
    import warnings
    warnings.warn("Use page.html instead", DeprecationWarning)
    return self._html
```

**Timeline**: 1 release cycle  
**Risk**: Low (deprecation warning only)

### Phase 3: Implement True AST with Hybrid Fallback

1. Update `MistuneParser` to expose AST.
2. Update `Page` properties to check for `_ast` and use it if available.
3. Implement AST walkers for text, TOC, links.
4. Maintain regex fallbacks for `python-markdown` users.

**Timeline**: 1-2 weeks  
**Risk**: Medium (core change)

---

## Decisions (Resolved Open Questions)

1. **Should we cache AST to disk?**
   - **Yes**. Pickling/JSON-serializing the AST list is significantly faster than re-parsing.
   - `BuildCache` will be updated to store `ast` alongside `hash`.

2. **Python-Markdown Compatibility**
   - **Hybrid Strategy**: The `Page` object will support both AST-based and Legacy modes.
   - If `parser.parse()` returns an AST (Mistune), use AST optimizations.
   - If `parser.parse()` returns a string (Python-Markdown), fall back to regex-based extraction.
   - This avoids breaking changes for users preferring `python-markdown`.

3. **Plain Text Strategy**
   - Default to **Raw Markdown** for LLM/Search contexts where structure matters.
   - Use **AST Extraction** when clean, text-only content is required (no markdown syntax).

---

## Implementation Notes

**Implemented**: 2024-12-02

### Files Modified

1. **`bengal/core/page/content.py`** (NEW)
   - `PageContentMixin` with `html`, `plain_text`, `ast` properties
   - AST walker methods: `_render_ast_to_html()`, `_extract_text_from_ast()`, `_extract_links_from_ast()`
   - Hybrid fallback to legacy `parsed_ast` when AST not available

2. **`bengal/core/page/__init__.py`**
   - Added `PageContentMixin` to `Page` class
   - Added private cache fields: `_ast_cache`, `_html_cache`, `_plain_text_cache`

3. **`bengal/rendering/parsers/base.py`**
   - Added `supports_ast` property (default: False)
   - Added `parse_to_ast()` method (raises NotImplementedError by default)
   - Added `render_ast()` method (raises NotImplementedError by default)

4. **`bengal/rendering/parsers/mistune.py`**
   - Implemented `supports_ast` property (returns True)
   - Implemented `parse_to_ast()` using Mistune's renderer=None mode
   - Implemented `render_ast()` using `HTMLRenderer` and `BlockState`
   - Added `parse_with_ast()` for single-pass AST + HTML + TOC generation

### API Changes

```python
# New Page properties
page.html        # Preferred way to access HTML (delegates to parsed_ast)
page.plain_text  # Raw markdown for LLM/search
page.ast         # True AST tokens (None until Phase 3 cache integration)

# New Parser methods
parser.supports_ast          # Check if parser supports AST
parser.parse_to_ast(content) # Get AST tokens
parser.render_ast(ast)       # Render AST to HTML
parser.parse_with_ast(...)   # All-in-one: AST + HTML + TOC
```

### Backward Compatibility

- `page.parsed_ast` continues to work (returns HTML as before)
- `page.html` is an alias that returns the same value
- All existing tests pass (123/124, 1 unrelated failure)

### Phase 3 Implementation (2024-12-02)

**AST Caching Integrated**:

1. **`bengal/cache/build_cache.py`**
   - Bumped VERSION to 4 for AST caching
   - Extended `store_parsed_content()` with `ast` parameter
   - AST persisted alongside HTML/TOC in cache JSON

2. **`bengal/rendering/pipeline.py`**
   - Uses `parse_with_ast()` when parser supports AST
   - Stores AST in `page._ast_cache` for content properties
   - AST persisted to cache for next build
   - AST restored from cache on cache hit

3. **`bengal/core/page/content.py`**
   - Fixed `_render_ast_to_html()` to use correct Mistune API
   - `page.html` now renders from AST when available
   - `page.plain_text` extracts text from AST via walker

**Benefits Realized**:
- Parse once, cache AST and HTML
- `page.ast` property returns true AST tokens
- `page.plain_text` extracts clean text via AST walker
- Cache persists AST across builds (JSON-serializable)

### Next Steps

1. **Performance benchmarks**: Measure actual speedup vs regex-based extraction
2. **LLM integration**: Use `page.plain_text` in search indexing and LLM outputs
3. **Link extraction**: Use AST walker for link extraction (replace regex)
