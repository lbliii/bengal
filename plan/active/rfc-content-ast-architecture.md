# RFC: Content AST Architecture

**Status**: Draft  
**Created**: 2024-12-02  
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
    def ast(self) -> list[dict]:
        """True AST - list of tokens from markdown parser."""
        if self._ast is None:
            self._ast = self._parse_to_ast()
        return self._ast

    @property
    def html(self) -> str:
        """HTML content rendered from AST."""
        if self._html is None:
            self._html = self._render_ast()
        return self._html

    @property
    def toc(self) -> str:
        """Table of contents extracted from AST."""
        if self._toc is None:
            self._toc = self._extract_toc_from_ast()
        return self._toc

    @property
    def plain_text(self) -> str:
        """Plain text extracted from AST (for search/LLM)."""
        if self._plain_text is None:
            self._plain_text = self._extract_text_from_ast()
        return self._plain_text

    @property
    def links(self) -> list[str]:
        """Links extracted from AST."""
        if self._links is None:
            self._links = self._extract_links_from_ast()
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

    def extract_text(self, ast: list[dict]) -> str:
        """Extract plain text from AST (O(n) tree walk)."""
        text_parts = []

        def walk(tokens):
            for token in tokens:
                if token['type'] == 'text':
                    text_parts.append(token['raw'])
                elif token['type'] == 'paragraph':
                    walk(token.get('children', []))
                    text_parts.append('\n')
                elif token['type'] == 'heading':
                    walk(token.get('children', []))
                    text_parts.append('\n')
                elif token['type'] == 'code_block':
                    text_parts.append(token.get('raw', ''))
                    text_parts.append('\n')
                elif 'children' in token:
                    walk(token['children'])

        walk(ast)
        return ''.join(text_parts).strip()

    def extract_headings(self, ast: list[dict]) -> list[dict]:
        """Extract headings for TOC (O(n) tree walk)."""
        headings = []

        def walk(tokens):
            for token in tokens:
                if token['type'] == 'heading':
                    headings.append({
                        'level': token['attrs']['level'],
                        'text': self._get_heading_text(token),
                        'id': self._generate_id(token),
                    })
                elif 'children' in token:
                    walk(token['children'])

        walk(ast)
        return headings

    def extract_links(self, ast: list[dict]) -> list[str]:
        """Extract all links from AST (O(n) tree walk)."""
        links = []

        def walk(tokens):
            for token in tokens:
                if token['type'] == 'link':
                    links.append(token['attrs']['url'])
                if 'children' in token:
                    walk(token['children'])

        walk(ast)
        return links
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

### Memory Impact

```python
# Current: Store HTML string
page.parsed_ast = "<p>Hello <strong>world</strong></p>"  # ~50 bytes

# With AST: Store token list
page._ast = [
    {'type': 'paragraph', 'children': [
        {'type': 'text', 'raw': 'Hello '},
        {'type': 'strong', 'children': [{'type': 'text', 'raw': 'world'}]}
    ]}
]  # ~200 bytes
```

**Trade-off**: AST uses ~4x more memory per page, but:
- We can discard AST after rendering (optional)
- Memory is cheap, CPU time is expensive
- 700 pages × 200 bytes = 140KB (negligible)

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

### Phase 3: Implement True AST

1. Update `MistuneParser` to expose AST
2. Add AST extraction methods (text, TOC, links)
3. Update rendering pipeline to use AST
4. Update post-processing to use AST

**Timeline**: 1-2 weeks  
**Risk**: Medium (core change)

### Phase 4: Remove `parsed_ast`

Remove deprecated property in next major version.

**Timeline**: Next major release  
**Risk**: Breaking change (documented)

---

## API Changes

### Templates

```jinja2
{# Current (still works) #}
{{ page.parsed_ast }}

{# Recommended #}
{{ page.html }}
```

### Python Code

```python
# Current
content = strip_html(page.parsed_ast or page.content)

# New
content = page.plain_text  # Or page.content for raw markdown
```

### Configuration

No configuration changes required.

---

## Alternatives Considered

### 1. Just Rename `parsed_ast` to `html`

**Pros**: Simple, fixes naming  
**Cons**: Doesn't address performance issues

### 2. Keep Both HTML and AST

**Pros**: Maximum flexibility  
**Cons**: Memory overhead, complexity

### 3. Use Raw Markdown for Plain Text

**Pros**: Zero overhead  
**Cons**: Includes frontmatter syntax, shortcode syntax

**Decision**: Hybrid approach - use raw markdown by default, AST walk when needed.

---

## Testing Strategy

### Unit Tests

```python
def test_ast_parsing():
    """Test AST is correctly parsed from markdown."""
    parser = ASTMarkdownParser()
    ast = parser.parse("# Hello\n\nWorld")

    assert ast[0]['type'] == 'heading'
    assert ast[1]['type'] == 'paragraph'

def test_text_extraction():
    """Test plain text extraction from AST."""
    parser = ASTMarkdownParser()
    ast = parser.parse("**Bold** and *italic*")
    text = parser.extract_text(ast)

    assert text == "Bold and italic"

def test_toc_extraction():
    """Test TOC extraction from AST."""
    parser = ASTMarkdownParser()
    ast = parser.parse("# H1\n## H2\n### H3")
    headings = parser.extract_headings(ast)

    assert len(headings) == 3
    assert headings[0]['level'] == 1
```

### Integration Tests

```python
@pytest.mark.bengal(testroot="test-basic")
def test_page_html_property(site, build_site):
    """Test page.html returns rendered content."""
    build_site()
    page = site.pages[0]

    assert "<p>" in page.html
    assert page.html == page.parsed_ast  # Backwards compatible

@pytest.mark.bengal(testroot="test-basic")  
def test_page_plain_text(site, build_site):
    """Test page.plain_text extraction."""
    build_site()
    page = site.pages[0]

    assert "<p>" not in page.plain_text
    assert len(page.plain_text) > 0
```

### Performance Tests

```python
@pytest.mark.slow
def test_ast_extraction_performance(benchmark, site_factory):
    """Benchmark AST-based text extraction."""
    site = site_factory("test-large")  # 1000 pages

    def extract_all_text():
        return [page.plain_text for page in site.pages]

    result = benchmark(extract_all_text)
    assert result < 1.0  # Must complete in <1 second
```

---

## Success Criteria

1. **Performance**: Post-processing time reduced by 50%+
2. **Correctness**: All existing tests pass
3. **Backwards Compatibility**: `parsed_ast` still works (with deprecation warning)
4. **Clean API**: New properties are intuitive and well-documented

---

## Open Questions

1. **Should we cache AST to disk?**
   - Pro: Faster incremental builds
   - Con: Cache invalidation complexity

2. **Should `plain_text` use raw markdown or AST extraction?**
   - Raw markdown: Faster, preserves structure (headers, lists)
   - AST extraction: Cleaner, no markdown syntax
   - **Proposed**: Default to raw markdown, option for AST extraction

3. **What about Python-Markdown compatibility?**
   - Python-Markdown also has AST (Element Tree)
   - Need adapter for both parsers

---

## References

- [Mistune AST Documentation](https://mistune.lepture.com/en/latest/advanced.html#abstract-syntax-tree)
- [Python-Markdown Extensions](https://python-markdown.github.io/extensions/api/)
- Current implementation: `bengal/rendering/parsers/mistune.py`
- Related RFC: `plan/active/rfc-render-performance-optimization.md`

---

## Appendix: AST Token Examples

### Mistune AST Format

```python
# Input: "# Hello **world**"
# Output:
[
    {
        'type': 'heading',
        'attrs': {'level': 1},
        'children': [
            {'type': 'text', 'raw': 'Hello '},
            {
                'type': 'strong',
                'children': [{'type': 'text', 'raw': 'world'}]
            }
        ]
    }
]
```

### Common Token Types

| Type | Description | Has Children |
|------|-------------|--------------|
| `paragraph` | Block paragraph | Yes |
| `heading` | H1-H6 | Yes |
| `text` | Plain text | No |
| `strong` | Bold text | Yes |
| `emphasis` | Italic text | Yes |
| `code_span` | Inline code | No |
| `code_block` | Code block | No |
| `link` | Hyperlink | Yes |
| `image` | Image | No |
| `list` | Ordered/unordered list | Yes |
| `list_item` | List item | Yes |
| `blockquote` | Quote block | Yes |
