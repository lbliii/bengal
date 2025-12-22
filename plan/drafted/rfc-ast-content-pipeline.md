# RFC: AST-Based Content Pipeline

**Status**: Drafted  
**Created**: 2024-12-22  
**Author**: Type System Hardening follow-up  
**Depends On**: Type System Hardening RFC (completed)

---

## Summary

Migrate Bengal's content processing from the current HTML-centric model to a true AST-based pipeline. This enables parse-once-use-many semantics, faster post-processing, and cleaner content transformations.

## Problem Statement

### Current State (Legacy)

Despite its name, `Page.parsed_ast` currently stores **rendered HTML**, not an AST:

```python
# Current reality (misleading)
page.parsed_ast = "<h1>Title</h1><p>Content...</p>"  # HTML string!
```

This creates several problems:

1. **Parse Twice**: TOC extraction re-parses HTML with regex/HTMLParser (`toc.py:80-136`)
2. **Regex Fragility**: Link transformation uses regex on HTML (`link_transformer.py:88-92`)
3. **No Structural Access**: Cannot answer "what headings are in this page?" without parsing
4. **Cache Inefficiency**: Cannot cache AST separately from rendered HTML
5. **Type Confusion**: The field name lies about its contents

### Existing Infrastructure

The Type System Hardening RFC already established:

- `ASTNode` TypedDict union in `bengal/rendering/ast_types.py`
- Mistune AST support in `bengal/rendering/parsers/mistune/ast.py`
- AST cache fields on Page: `_ast_cache`, `_html_cache`, `_plain_text_cache`
- Partial implementation in `PageContentMixin` (`content.py:93-140`)

### Desired State

```python
# True AST-based model
page.ast = [
    {"type": "heading", "level": 1, "children": [{"type": "text", "raw": "Title"}]},
    {"type": "paragraph", "children": [{"type": "text", "raw": "Content..."}]},
]
page.html  # Rendered on-demand from AST (cached)
```

## Goals

1. **Parse Once**: Single markdown parse produces AST, all outputs derive from it
2. **Type Safety**: Use `ASTNode` types from `bengal.rendering.ast_types`
3. **Performance**: AST walks replace regex scans with better constant factors
4. **Clarity**: Field names match their contents
5. **Backward Compatibility**: Existing templates continue working

## Non-Goals

- Changing the markdown parser (Mistune stays)
- Supporting multiple AST formats
- Real-time AST editing

---

## Design

### Phase 1a: Extend AST Types (0.5 hours)

Add `RawHTMLNode` for directive output and pre-rendered content:

```python
# bengal/rendering/ast_types.py

class RawHTMLNode(TypedDict):
    """Pre-rendered HTML block (directives, embeds, virtual pages)."""
    type: Literal["raw_html"]
    content: str


# Update the union
type ASTNode = (
    TextNode
    | CodeSpanNode
    | HeadingNode
    # ... existing types ...
    | RawHTMLNode  # NEW
)
```

This handles:
- Directive output (code blocks, admonitions, tabs)
- Virtual page content (`page._prerendered_html`)
- External embeds

### Phase 1b: Dual-Mode Pipeline (3.5 hours)

Add true AST storage alongside existing HTML flow:

```python
@dataclass
class Page:
    # NEW: True AST from parser
    _ast_cache: list[ASTNode] | None = field(default=None, init=False)

    # EXISTING: Keep for backward compatibility (deprecated)
    parsed_ast: Any | None = None  # Still stores HTML

    @property
    def ast(self) -> list[ASTNode] | None:
        """True AST - list of tokens from markdown parser."""
        return self._ast_cache

    @property
    def html(self) -> str:
        """Rendered HTML (from AST or legacy parsed_ast)."""
        if self._ast_cache:
            return self._render_ast()
        return self.parsed_ast or ""
```

**Pipeline Changes**:

```python
# In RenderPipeline._parse_page()
def _parse_page(self, page: Page) -> None:
    # Parse to AST (new)
    ast_tokens = self.parser.parse_to_ast(page.content, page.metadata)
    page._ast_cache = ast_tokens

    # Render to HTML (existing, but from AST)
    html = self.parser.render_ast(ast_tokens)
    page.parsed_ast = html  # Deprecated, but kept for compatibility
```

**Thread Safety**: AST caches must be thread-safe for parallel builds. Use the existing cache pattern with per-page isolation (no shared mutable state).

### Phase 2: AST Utilities and Extractors (4 hours)

Add tree-walking utilities and replace regex-based extraction:

```python
# bengal/rendering/ast_utils.py

from typing import Iterator
from bengal.rendering.ast_types import ASTNode, is_heading, is_text

def walk_ast(ast: list[ASTNode]) -> Iterator[ASTNode]:
    """
    Recursively walk all nodes in an AST.

    Yields each node in depth-first order, enabling O(n) traversal
    for extraction operations.

    Args:
        ast: Root-level AST nodes

    Yields:
        Each ASTNode in the tree
    """
    for node in ast:
        yield node
        if "children" in node:
            yield from walk_ast(node["children"])


def extract_toc_from_ast(ast: list[ASTNode]) -> list[dict[str, Any]]:
    """Extract TOC structure from AST (replaces HTMLParser in toc.py)."""
    toc_items = []
    for node in walk_ast(ast):
        if is_heading(node):
            toc_items.append({
                "id": generate_heading_id(node),
                "title": extract_text(node),
                "level": node["level"],
            })
    return toc_items


def extract_links_from_ast(ast: list[ASTNode]) -> list[str]:
    """Extract all links from AST."""
    links = []
    for node in walk_ast(ast):
        if node.get("type") == "link":
            links.append(node["url"])
    return links


def extract_plain_text(ast: list[ASTNode]) -> str:
    """Extract plain text for search indexing (replaces regex strip in content.py)."""
    return "".join(
        node["raw"] for node in walk_ast(ast)
        if is_text(node)
    )
```

**Migration Notes for PageContentMixin**:

Update `bengal/core/page/content.py` to use AST extractors:

```python
@property
def plain_text(self) -> str:
    """Plain text content for search and LLM indexing."""
    if self._plain_text_cache is not None:
        return self._plain_text_cache

    # Phase 2: Use AST extraction if available
    if self._ast_cache is not None:
        text = extract_plain_text(self._ast_cache)
        self._plain_text_cache = text
        return text

    # Fallback: Regex-based extraction from HTML
    return self._strip_html_to_text(self.parsed_ast or "")
```

### Phase 3: AST-Level Transformations (3 hours)

Move link transformation from HTML regex to AST manipulation:

```python
# bengal/rendering/ast_transforms.py

def transform_links_in_ast(
    ast: list[ASTNode],
    transformer: Callable[[str], str]
) -> list[ASTNode]:
    """
    Transform links at AST level (replaces regex in link_transformer.py).

    Benefits over regex:
    - No risk of matching href inside code blocks
    - Handles edge cases (quotes, escapes) correctly
    - Type-safe: operates on structured data
    """
    def transform_node(node: ASTNode) -> ASTNode:
        if node.get("type") == "link":
            return {**node, "url": transformer(node["url"])}
        if "children" in node:
            return {**node, "children": [transform_node(c) for c in node["children"]]}
        return node

    return [transform_node(n) for n in ast]


def normalize_md_links_in_ast(ast: list[ASTNode]) -> list[ASTNode]:
    """Convert .md links to clean URLs at AST level."""
    def normalize(url: str) -> str:
        if url.endswith(".md"):
            if url.endswith("_index.md"):
                return url[:-9] or "./"
            return url[:-3] + "/"
        return url

    return transform_links_in_ast(ast, normalize)


def add_baseurl_to_ast(ast: list[ASTNode], baseurl: str) -> list[ASTNode]:
    """Prepend baseurl to internal links at AST level."""
    def add_base(url: str) -> str:
        if url.startswith("/") and not url.startswith(baseurl):
            return f"{baseurl}{url}"
        return url

    return transform_links_in_ast(ast, add_base)
```

### Phase 4: Deprecation and Cleanup (2 hours)

1. Add deprecation warning to `parsed_ast` access:

```python
@property
def parsed_ast(self) -> Any | None:
    """
    DEPRECATED: Use page.html for rendered content or page.ast for AST.

    This property will be removed in Bengal 1.0.
    """
    import warnings
    warnings.warn(
        "Page.parsed_ast is deprecated. Use page.html for HTML content "
        "or page.ast for AST access.",
        DeprecationWarning,
        stacklevel=2,
    )
    return self._parsed_ast_internal
```

2. Update all internal consumers to use `ast` / `html` properties
3. Remove `parsed_ast` in next major version

---

## Benefits

### Performance

| Operation | Current | Proposed | Expected Improvement |
|-----------|---------|----------|---------------------|
| TOC extraction | HTMLParser + regex | AST walk | ~1.5x faster |
| Link transformation | Regex on HTML | AST map | ~2x faster (no backtracking) |
| Plain text extraction | Regex strip tags | AST walk | ~1.5x faster |
| Multiple outputs | N parses | 1 parse, N walks | Nx faster |

**Note**: Both approaches are O(n), but AST walks have better constant factors due to no regex compilation, no string allocation from re.sub, and cache-friendly sequential access.

### Code Quality

```python
# BEFORE: Fragile regex on HTML (link_transformer.py:90)
pattern = r'(href|src)=(["\'])(/(?!/)(?:[^"\'#][^"\']*)?)\2'
links = re.sub(pattern, replace_link, page.parsed_ast)

# AFTER: Type-safe AST extraction  
links = extract_links_from_ast(page.ast)
```

### Caching

```python
# Can cache AST and HTML separately
cache = {
    "ast": page.ast,           # Reusable for any output (JSON serialized)
    "html": page.html,         # Rendered output
    "toc": page.toc_items,     # Derived from AST
    "plain_text": page.plain_text,  # Derived from AST
}
```

**Cache Format**: JSON (not pickle) for:
- Debuggability (human-readable cache files)
- Cross-Python-version compatibility
- Consistency with existing `.bengal/` cache format
- Security (no arbitrary code execution on deserialize)

---

## Migration Path

### For Bengal Internal Code

1. Phase 1: Add AST properties (non-breaking)
2. Phase 2: Switch extractors to AST-based versions
3. Phase 3: Switch transformers to AST-based versions
4. Phase 4: Add deprecation warnings, update tests

### For Theme Authors

No changes required — templates use `page.html` (property) which works in both modes.

### For Plugin Authors

```python
# Old way (still works during deprecation period)
html = page.parsed_ast  # Triggers deprecation warning

# New way (recommended)
html = page.html  # Property that renders from AST
ast = page.ast    # Direct AST access for advanced use
```

---

## Implementation Plan

| Phase | Scope | Time | Deliverables |
|-------|-------|------|--------------|
| 1a | Extend `ast_types.py` with `RawHTMLNode` | 0.5h | Updated type union |
| 1b | Dual-mode pipeline, `ast`/`html` properties | 3.5h | Working hybrid pipeline |
| 2 | `walk_ast()` helper, AST extractors, update `PageContentMixin` | 4h | New extractors, migrated mixin |
| 3 | AST-level link/URL transformations | 3h | Replacement for regex transforms |
| 4 | Deprecation warnings, test updates, cleanup | 2h | Deprecation complete |

**Total**: ~13 hours (2 days)

### Commit Sequence

1. `types(ast): add RawHTMLNode for directive/prerendered content`
2. `core(page): add ast property with dual-mode support`
3. `rendering(pipeline): populate _ast_cache during parsing`
4. `rendering: add walk_ast() and AST extraction utilities`
5. `core(page): migrate PageContentMixin to AST extractors`
6. `rendering: add AST-level link transformations`
7. `core(page): deprecate parsed_ast property`
8. `tests: add AST pipeline unit tests`

---

## Testing Strategy

### Unit Tests (Phase 2)

```python
def test_walk_ast_traverses_all_nodes():
    """Verify walk_ast visits every node."""
    ast = [
        {"type": "heading", "level": 1, "children": [
            {"type": "text", "raw": "Title"}
        ]},
        {"type": "paragraph", "children": [
            {"type": "text", "raw": "Content"}
        ]},
    ]
    nodes = list(walk_ast(ast))
    assert len(nodes) == 4  # 2 containers + 2 text nodes


def test_extract_toc_from_ast():
    """Verify TOC extraction matches HTMLParser output."""
    ast = parse_to_ast("# One\n## Two\n### Three")
    toc = extract_toc_from_ast(ast)
    assert toc == [
        {"id": "one", "title": "One", "level": 1},
        {"id": "two", "title": "Two", "level": 2},
        {"id": "three", "title": "Three", "level": 3},
    ]
```

### Integration Tests (Phase 3)

```python
def test_ast_pipeline_matches_legacy_output():
    """Verify AST pipeline produces identical HTML."""
    page = Page(source_path=Path("test.md"), content="# Hello\n\nWorld")

    # Parse both ways
    legacy_html = legacy_parse(page.content)
    ast = parse_to_ast(page.content)
    ast_html = render_ast(ast)

    assert normalize_html(ast_html) == normalize_html(legacy_html)
```

---

## Alternatives Considered

### 1. Keep HTML-Centric Model

**Rejected**: Regex on HTML is fragile and slow. The Type System Hardening RFC created `ASTNode` types specifically for this migration.

### 2. Switch to mdast/unist Format

**Rejected**: Would require changing parser. Mistune's AST format is suitable, and we already have typed definitions for it.

### 3. Big-Bang Migration

**Rejected**: Too risky. Phased approach allows gradual migration with backward compatibility and easy rollback.

### 4. Pickle for Cache Format

**Rejected**: JSON provides debuggability, security, and cross-version compatibility. Performance difference is negligible for our cache sizes.

---

## Success Criteria

- [ ] `page.ast` returns typed `list[ASTNode]`
- [ ] `page.html` renders from AST (with fallback to legacy)
- [ ] `RawHTMLNode` handles directive output correctly
- [ ] `walk_ast()` utility implemented and tested
- [ ] TOC extraction uses AST walk (no HTMLParser)
- [ ] Link transformation uses AST manipulation (no regex)
- [ ] `PageContentMixin.plain_text` uses AST extraction
- [ ] All existing tests pass
- [ ] No template changes required
- [ ] Deprecation warning on `parsed_ast` access

---

## References

- Type System Hardening RFC: `plan/ready/plan-type-system-hardening.md`
- ASTNode types: `bengal/rendering/ast_types.py`
- Mistune AST support: `bengal/rendering/parsers/mistune/ast.py`
- Current TOC extraction: `bengal/rendering/pipeline/toc.py`
- Current link transformation: `bengal/rendering/link_transformer.py`
- Page content mixin: `bengal/core/page/content.py`
