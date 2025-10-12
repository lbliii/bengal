# API Link Index System - Implementation Plan

**Status**: 📋 Planning  
**Owner**: TBD  
**Target Version**: v0.2.0  
**Created**: 2025-10-12  
**Priority**: High (Core Feature)

## Overview

Implement a high-performance API link index system that enables fast, validated cross-references between documentation and API reference pages. This provides **80% of Sphinx's semantic linking value with 20% of the complexity**, while maintaining Bengal's speed advantage.

### Goals

1. **Fast linking**: O(1) lookups via pre-computed index
2. **Simple syntax**: `[[api:Symbol]]` or `[[api:module.Class.method]]`
3. **Auto-detection**: Optional auto-linking of `` `ClassName.method()` `` patterns
4. **Build-time validation**: Catch broken API references early
5. **Cache-friendly**: Index persists across incremental builds
6. **Minimal overhead**: < 1% build time increase

### Non-Goals

- Full Sphinx `:role:` system compatibility (too complex)
- Multiple output formats besides HTML (future)
- Runtime link generation (all compile-time)
- Domain system (Python-only for now)

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Build Pipeline                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Autodoc Generation                                      │
│     └─> content/api/*.md (with type: api-reference)        │
│                                                             │
│  2. Content Discovery                                       │
│     └─> All pages discovered (including autodoc)           │
│                                                             │
│  3. API Index Building ⭐ NEW                               │
│     └─> Scan autodoc pages                                 │
│     └─> Extract symbols (classes, functions, methods)      │
│     └─> Build symbol → URL mapping                         │
│     └─> Store in site.api_index                            │
│                                                             │
│  4. Page Rendering                                          │
│     ├─> Parse markdown with APILinkPlugin ⭐ NEW           │
│     │   └─> [[api:Symbol]] → O(1) lookup in index         │
│     │   └─> Generate <a href="/api/...">Symbol</a>        │
│     └─> Optional: Auto-link code blocks ⭐ NEW             │
│                                                             │
│  5. Link Validation ⭐ NEW                                  │
│     └─> Report broken [[api:...]] references              │
│                                                             │
│  6. Cache Update                                            │
│     └─> Persist API index to .bengal-cache.json           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Data Structures

```python
# Core index structure
APILinkIndex {
    symbols: dict[str, str]           # symbol → URL
    methods: dict[str, dict[str, str]]  # class → {method → URL}
    modules: dict[str, str]           # module path → URL
    cache_key: str                    # Hash of autodoc sources
}

# Symbol examples:
symbols = {
    # Short names
    "Site": "/api/bengal/core/site/",
    "BuildCache": "/api/bengal/cache/build-cache/",

    # Qualified names
    "bengal.core.site.Site": "/api/bengal/core/site/",

    # Methods with anchors
    "Site.build": "/api/bengal/core/site/#build",
    "bengal.core.site.Site.build": "/api/bengal/core/site/#build",

    # Functions
    "render_page": "/api/bengal/rendering/renderer/#render-page",
}
```

## Implementation Phases

### Phase 1: Core Index (Week 1)

**Goal**: Build and cache API symbol index

#### Tasks

**1.1 Create APILinkIndex Class**
- File: `bengal/autodoc/link_index.py`
- Features:
  - `build(site)` - Extract symbols from autodoc pages
  - `lookup(symbol)` - O(1) symbol → URL resolution
  - `to_dict()` / `from_dict()` - Serialization for cache
  - `validate()` - Check for duplicate symbols

```python
# Pseudocode structure
class APILinkIndex:
    def __init__(self):
        self.symbols: dict[str, str] = {}
        self.ambiguous: dict[str, list[str]] = {}  # Track conflicts

    def build(self, site: Site) -> None:
        """Scan autodoc pages and build index."""
        for page in site.pages:
            if page.metadata.get('type') != 'api-reference':
                continue

            module = page.metadata.get('module')
            elements = page.metadata.get('api_elements', [])

            for element in elements:
                self._index_element(element, module, page.url)

    def lookup(self, symbol: str) -> str | None:
        """O(1) lookup. Returns URL or None."""
        return self.symbols.get(symbol)

    def _index_element(self, element, module, base_url):
        """Index a class/function with all name variants."""
        # Short name, qualified name, methods, etc.
        pass
```

**1.2 Integrate into Build Pipeline**
- File: `bengal/orchestration/build.py`
- Add index building after content discovery, before rendering
- Store index in `site.api_index`

```python
# In BuildOrchestrator.build()
def build(self, site: Site) -> BuildStats:
    # Existing phases...
    self._discover_content(site)

    # NEW: Build API index
    if self._has_autodoc_pages(site):
        api_index = APILinkIndex()
        api_index.build(site)
        site.api_index = api_index
        logger.info(f"Built API index: {len(api_index.symbols)} symbols")

    # Continue with rendering...
    self._render_pages(site)
```

**1.3 Cache Integration**
- File: `bengal/cache/build_cache.py`
- Add `api_index` field to cache
- Save/load index between builds
- Invalidate when autodoc sources change

```python
# In BuildCache
def save_api_index(self, index: APILinkIndex) -> None:
    """Persist API index for next build."""
    self.cache['api_index'] = {
        'symbols': index.symbols,
        'timestamp': time.time(),
        'cache_key': self._compute_autodoc_hash()
    }

def load_api_index(self) -> APILinkIndex | None:
    """Load cached index if valid."""
    if 'api_index' not in self.cache:
        return None

    # Check if autodoc sources changed
    cached_key = self.cache['api_index']['cache_key']
    current_key = self._compute_autodoc_hash()

    if cached_key == current_key:
        return APILinkIndex.from_dict(self.cache['api_index'])

    return None
```

**Deliverables:**
- ✅ `bengal/autodoc/link_index.py` with tests
- ✅ Integration in build pipeline
- ✅ Cache save/load functionality
- ✅ Unit tests (target: 90%+ coverage)

**Testing:**
```bash
# Unit tests
pytest tests/unit/autodoc/test_link_index.py -v

# Integration test
pytest tests/integration/test_api_linking.py -v
```

---

### Phase 2: Markdown Syntax (Week 2)

**Goal**: Parse and resolve `[[api:...]]` links

#### Tasks

**2.1 Create APILinkPlugin for Mistune**
- File: `bengal/rendering/plugins/api_links.py`
- Parse `[[api:Symbol]]` at markdown parse time
- Integrate with existing cross-reference plugin

```python
# Plugin implementation
class APILinkPlugin:
    """Mistune plugin for [[api:...]] syntax."""

    PATTERN = re.compile(r'\[\[api:([^\]]+)\]\]')

    def __init__(self, api_index: APILinkIndex):
        self.index = api_index
        self.unresolved: list[tuple[str, str]] = []  # (symbol, page_path)

    def parse(self, inline, m, state):
        """Parse [[api:symbol]] and resolve immediately."""
        symbol = m.group(1).strip()

        # O(1) lookup
        url = self.index.lookup(symbol)

        if url:
            return 'api_link', {'url': url, 'symbol': symbol}
        else:
            # Track for validation
            page = state.env.get('current_page')
            self.unresolved.append((symbol, page))
            # Return as plain text (or error marker)
            return 'text', f"[[api:{symbol}]]"

    def render_api_link(self, renderer, url, symbol):
        """Render as HTML link."""
        return f'<a href="{url}" class="api-link"><code>{symbol}</code></a>'
```

**2.2 Integrate Plugin into Parser**
- File: `bengal/rendering/parser.py`
- Add APILinkPlugin to Mistune plugin chain
- Pass `site.api_index` to plugin

```python
# In MistuneParser
def create_markdown(self, site: Site):
    plugins = [
        'table',
        'strikethrough',
        # ... existing plugins
    ]

    # Add API link plugin if index exists
    if hasattr(site, 'api_index') and site.api_index:
        api_plugin = APILinkPlugin(site.api_index)
        plugins.append(api_plugin)
        self.api_plugin = api_plugin  # Store for validation

    return mistune.create_markdown(plugins=plugins)
```

**2.3 Link Resolution Logging**
- Log resolved links in verbose mode
- Track resolution rate (for optimization)

```python
# Example verbose output
# [[api:Site.build]] → /api/bengal/core/site/#build ✓
# [[api:InvalidClass]] → unresolved ✗
```

**Deliverables:**
- ✅ `bengal/rendering/plugins/api_links.py` with tests
- ✅ Integration in Mistune parser
- ✅ Comprehensive tests for syntax variants
- ✅ Unit tests (target: 95%+ coverage)

**Testing:**
```python
# Test cases
test_simple_class_reference()       # [[api:Site]]
test_qualified_reference()          # [[api:bengal.core.site.Site]]
test_method_reference()             # [[api:Site.build]]
test_function_reference()           # [[api:render_page]]
test_unresolved_reference()         # [[api:DoesNotExist]]
test_ambiguous_reference()          # Multiple matches
```

---

### Phase 3: Validation (Week 3)

**Goal**: Catch and report broken API references

#### Tasks

**3.1 Create APILinkValidator**
- File: `bengal/health/validators/api_links.py`
- Check for broken `[[api:...]]` references
- Report missing symbols with suggestions

```python
class APILinkValidator(BaseValidator):
    """Validate API link references."""

    def validate(self, site: Site) -> list[CheckResult]:
        results = []

        # Get unresolved links from parser
        if not hasattr(site, 'api_plugin'):
            return results

        unresolved = site.api_plugin.unresolved

        for symbol, page_path in unresolved:
            # Find similar symbols (fuzzy matching)
            suggestions = self._find_similar(symbol, site.api_index)

            result = CheckResult(
                status=CheckStatus.ERROR,
                message=f"Unresolved API reference: [[api:{symbol}]]",
                location=page_path,
                recommendation=self._format_suggestions(suggestions)
            )
            results.append(result)

        return results

    def _find_similar(self, symbol: str, index: APILinkIndex) -> list[str]:
        """Fuzzy match for suggestions."""
        from difflib import get_close_matches
        return get_close_matches(symbol, index.symbols.keys(), n=3, cutoff=0.6)
```

**3.2 Integrate with Health Check**
- File: `bengal/health/health_check.py`
- Add APILinkValidator to validator list
- Run after build if `validate_api_links` enabled

**3.3 CLI Output for Errors**
- Pretty-print broken links with context
- Show suggestions for typos

```bash
# Example output
❌ API Link Validation

  content/docs/architecture.md:15
    Unresolved reference: [[api:BuildOrchestrator]]

    Did you mean one of these?
      • BuildOrchestrator (bengal.orchestration.build)
      • RenderOrchestrator
      • TaxonomyOrchestrator

  Found 1 broken API link
```

**Deliverables:**
- ✅ `bengal/health/validators/api_links.py`
- ✅ Integration with health check system
- ✅ Fuzzy matching for suggestions
- ✅ CLI output formatting
- ✅ Tests for validation logic

---

### Phase 4: Auto-Linking (Week 4) - OPTIONAL

**Goal**: Auto-detect and link code in backticks

#### Tasks

**4.1 Create Code Auto-Linker**
- File: `bengal/rendering/plugins/auto_link_code.py`
- Post-process HTML to detect linkable code
- Make it opt-in (performance consideration)

```python
class CodeAutoLinker:
    """Auto-link backticked code to API docs."""

    # Match: `ClassName` or `ClassName.method()`
    CODE_PATTERN = re.compile(
        r'<code>(?!<a)([A-Z]\w+(?:\.[a-z_]\w+)?(?:\(\))?)</code>'
    )

    def __init__(self, api_index: APILinkIndex):
        self.index = api_index
        self.linked_count = 0

    def process(self, html: str) -> str:
        """Auto-link code blocks to API docs."""
        def replace(match: re.Match) -> str:
            code = match.group(1)
            symbol = code.rstrip('()')

            # O(1) lookup
            if url := self.index.lookup(symbol):
                self.linked_count += 1
                return f'<a href="{url}"><code>{code}</code></a>'

            return match.group(0)  # No match, leave as-is

        return self.CODE_PATTERN.sub(replace, html)
```

**4.2 Configuration Option**
- Add to `bengal.toml`
- Default: disabled (opt-in for performance)

```toml
[autodoc]
auto_link_code = true  # Default: false

# Alternative: per-page opt-in
# ---
# auto_link_code: true
# ---
```

**4.3 Performance Testing**
- Measure overhead on 100+ page site
- Ensure < 3ms per page

**Deliverables:**
- ✅ `bengal/rendering/plugins/auto_link_code.py`
- ✅ Configuration options
- ✅ Performance benchmarks
- ✅ Tests for auto-detection patterns

---

### Phase 5: Autodoc Integration (Week 5)

**Goal**: Ensure autodoc pages export correct metadata for indexing

#### Tasks

**5.1 Update Autodoc Templates**
- File: `bengal/autodoc/templates/python/module.md.jinja2`
- Ensure `type: api-reference` in frontmatter
- Export `api_elements` with full metadata

```jinja2
---
title: "{{ element.name }}"
type: api-reference
module: "{{ element.qualified_name }}"
api_elements:
  - name: "{{ element.name }}"
    type: "{{ element.element_type }}"
    methods:
      {% for method in element.children %}
      - name: "{{ method.name }}"
        signature: "{{ method.metadata.signature }}"
      {% endfor %}
---

# {{ element.name }}

...
```

**5.2 Update PythonExtractor**
- File: `bengal/autodoc/extractors/python.py`
- Ensure all symbols are extracted with correct names
- Handle edge cases (nested classes, decorators)

**5.3 Generate Anchor IDs**
- Ensure method headers have stable IDs
- Format: `<h2 id="method-name">method_name()</h2>`

**Deliverables:**
- ✅ Updated autodoc templates
- ✅ Anchor ID generation
- ✅ Tests for template output
- ✅ Validation that index can parse autodoc pages

---

## Testing Strategy

### Unit Tests (Target: 95%+ coverage)

```
tests/unit/autodoc/
├── test_link_index.py          # Index building, lookup, caching
│   ├── test_build_index
│   ├── test_lookup_variants
│   ├── test_ambiguous_symbols
│   └── test_cache_serialization
│
tests/unit/rendering/plugins/
├── test_api_links.py            # [[api:...]] parsing
│   ├── test_parse_simple_ref
│   ├── test_parse_qualified_ref
│   ├── test_parse_method_ref
│   └── test_unresolved_ref
│
└── test_auto_link_code.py       # Auto-linking (optional)
    ├── test_detect_class_names
    ├── test_detect_methods
    └── test_no_false_positives

tests/unit/health/validators/
└── test_api_links.py            # Validation
    ├── test_detect_broken_links
    └── test_fuzzy_suggestions
```

### Integration Tests

```
tests/integration/
└── test_api_linking_workflow.py
    ├── test_full_autodoc_link_flow  # autodoc → index → render → validate
    ├── test_incremental_cache       # Index persists across builds
    ├── test_broken_link_detection   # Catches invalid refs
    └── test_cross_page_linking      # Docs → API, API → docs
```

### Performance Tests

```
tests/performance/
└── test_api_index_performance.py
    ├── test_index_build_speed       # < 50ms for 100 modules
    ├── test_lookup_speed            # < 0.1ms per lookup
    ├── test_render_overhead         # < 1% build time increase
    └── test_auto_link_overhead      # < 3ms per page (if enabled)
```

### Test Data

```
tests/fixtures/api_linking/
├── autodoc_pages/              # Sample autodoc output
│   ├── module_a.md
│   ├── module_b.md
│   └── class_with_methods.md
├── content_with_refs/          # Pages with [[api:...]] links
│   ├── valid_refs.md
│   ├── broken_refs.md
│   └── ambiguous_refs.md
└── expected_output/            # Expected HTML
    ├── valid_refs.html
    └── broken_refs_errors.txt
```

## Performance Targets

| Metric | Target | Measured How |
|--------|--------|--------------|
| **Index Build Time** | < 50ms for 100 modules | `pytest tests/performance/test_api_index_performance.py` |
| **Symbol Lookup** | < 0.1ms per lookup | Direct timing in test |
| **Render Overhead** | < 1% build time | Compare with/without API linking |
| **Cache Hit** | < 1ms to load index | Time cache load operation |
| **Auto-link Overhead** | < 3ms per page | Optional feature benchmark |
| **Memory Overhead** | < 5MB for 1000 symbols | Memory profiling |

## Configuration

### bengal.toml

```toml
[autodoc.python]
enabled = true
source_dirs = ["bengal"]
output_dir = "content/api"

[autodoc]
# Enable API link index (default: true)
link_index = true

# Auto-link code blocks (default: false, opt-in for performance)
auto_link_code = false

# Cache index between builds (default: true)
cache_index = true

[build]
# Validate API links during build (default: true)
validate_api_links = true

# Fail build on broken API links (default: false, warns only)
strict_api_links = false
```

## Migration Path

### For Existing Bengal Sites

No breaking changes - this is purely additive:

1. **Opt-in**: Use `[[api:...]]` syntax where desired
2. **No change**: Existing sites continue to work
3. **Gradual adoption**: Add API links incrementally

### For Sphinx Users

Provide migration script:

```python
# scripts/migrate_sphinx_refs.py
def convert_sphinx_roles_to_bengal(content: str) -> str:
    """Convert Sphinx :role:`ref` to Bengal [[api:ref]]."""
    conversions = {
        r':func:`([^`]+)`': r'[[api:\1]]',
        r':class:`([^`]+)`': r'[[api:\1]]',
        r':meth:`([^`]+)`': r'[[api:\1]]',
        r':mod:`([^`]+)`': r'[[api:\1]]',
    }

    for pattern, replacement in conversions.items():
        content = re.sub(pattern, replacement, content)

    return content
```

## Documentation

### User-Facing Docs

Create/update these pages:

1. **docs/features/api-linking.md** - Overview and usage
2. **docs/reference/link-syntax.md** - Complete syntax reference
3. **docs/guides/documenting-code.md** - Best practices
4. **docs/migration/from-sphinx.md** - Migration guide

### Example Content

```markdown
# docs/features/api-linking.md

## API Linking

Link to API documentation from any page using `[[api:...]]` syntax.

### Basic Usage

```markdown
The [[api:Site.build]] method orchestrates the build.
Use [[api:BuildCache]] for incremental builds.
```

### Syntax Variants

- `[[api:ClassName]]` - Link to class
- `[[api:function_name]]` - Link to function
- `[[api:Class.method]]` - Link to method
- `[[api:module.Class.method]]` - Fully qualified

### Auto-Linking

Enable auto-linking to convert `ClassName` in backticks to links:

```toml
[autodoc]
auto_link_code = true
```

Then writing `Site` automatically links to the API docs.
```

## Timeline

### Week 1: Core Index (Jan 15-19)
- ✅ APILinkIndex class
- ✅ Build pipeline integration
- ✅ Cache integration
- ✅ Unit tests

### Week 2: Markdown Syntax (Jan 22-26)
- ✅ APILinkPlugin for Mistune
- ✅ Parser integration
- ✅ Tests for syntax variants

### Week 3: Validation (Jan 29 - Feb 2)
- ✅ APILinkValidator
- ✅ Health check integration
- ✅ CLI error reporting

### Week 4: Auto-Linking (Feb 5-9) - Optional
- ✅ CodeAutoLinker
- ✅ Configuration options
- ✅ Performance tests

### Week 5: Autodoc Integration (Feb 12-16)
- ✅ Template updates
- ✅ Anchor ID generation
- ✅ Integration tests
- ✅ Documentation

**Total: 4-5 weeks** (can skip Week 4 if not needed)

## Success Criteria

- ✅ Index builds in < 50ms for 100 modules
- ✅ O(1) lookup performance
- ✅ < 1% build time overhead
- ✅ 95%+ test coverage for new code
- ✅ All integration tests pass
- ✅ Broken links caught at build time
- ✅ Fuzzy matching provides helpful suggestions
- ✅ Documentation complete with examples
- ✅ Cache invalidation works correctly
- ✅ Incremental builds benefit from cached index

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Performance regression** | High | Benchmark continuously, cache aggressively |
| **Ambiguous symbol names** | Medium | Warn on conflicts, prefer qualified names |
| **Cache invalidation bugs** | Medium | Hash autodoc sources, validate on load |
| **Complex nested classes** | Low | Test edge cases, handle gracefully |
| **Memory usage on large sites** | Low | Use efficient data structures, test at scale |

## Future Enhancements (Post-v0.2.0)

1. **Multiple languages** - JavaScript, TypeScript via TSDoc
2. **External linking** - Link to other projects' docs
3. **Hover tooltips** - Show signatures on hover
4. **IDE integration** - Language server for autocomplete
5. **Link analytics** - Track which APIs are most referenced

## Questions / Open Issues

1. **Ambiguous short names**: How to handle `build` (multiple classes have it)?
   - **Decision**: Warn and suggest qualified name

2. **Performance threshold**: What's acceptable overhead?
   - **Decision**: < 1% build time, < 50ms index build

3. **Auto-linking defaults**: Enable by default or opt-in?
   - **Decision**: Opt-in to avoid surprises

4. **Anchor format**: `#method-name` vs `#method_name` vs `#method`?
   - **Decision**: Use `#method-name` (slugified) for consistency

## References

- [Sphinx Intersphinx](https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html)
- [MkDocs Autorefs](https://mkdocstrings.github.io/autorefs/)
- [Hugo Cross References](https://gohugo.io/content-management/cross-references/)
- Bengal Architecture: `/ARCHITECTURE.md`
- Bengal Autodoc: `/bengal/autodoc/`

---

**Next Steps:**
1. Review and approve this plan
2. Create GitHub issue tracking implementation
3. Begin Phase 1 development
4. Set up performance benchmarking infrastructure
