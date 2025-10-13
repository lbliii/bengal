# API Link Index System - Refined Implementation Plan

**Status**: 📋 Ready for Implementation  
**Owner**: TBD  
**Target Version**: v0.2.0  
**Created**: 2025-10-12  
**Refined**: 2025-10-12  
**Priority**: High (Core Feature)

## Overview

Implement a high-performance API link index system that enables fast, validated cross-references between documentation and API reference pages. This provides **80% of Sphinx's semantic linking value with 20% of the complexity**, while maintaining Bengal's speed advantage.

### Key Design Decisions (From Analysis)

1. ✅ **Extend existing CrossReferencePlugin** instead of creating new plugin (reduces overhead)
2. ✅ **Merge into xref_index** instead of separate api_index (single source of truth)
3. ✅ **Build in Phase 2.5** (after section finalization, before taxonomies)
4. ✅ **Incremental cache invalidation** for autodoc-only changes
5. ✅ **Auto-linking stays optional** with caching for performance

### Goals

1. **Fast linking**: O(1) lookups via unified xref_index
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
│     └─> content/api/*.md (with type: python-module)        │
│                                                             │
│  2. Content Discovery                                       │
│     └─> All pages discovered (including autodoc)           │
│                                                             │
│  2.5 API Index Building ⭐ NEW                              │
│     └─> Scan autodoc pages                                 │
│     └─> Extract symbols (classes, functions, methods)      │
│     └─> Build symbol → URL mapping                         │
│     └─> Merge into site.xref_index['api_symbols'] ⭐       │
│                                                             │
│  3. Section Finalization                                    │
│                                                             │
│  4. Taxonomies                                              │
│                                                             │
│  5. Menus                                                   │
│                                                             │
│  6. Incremental Filtering                                   │
│                                                             │
│  7. Page Rendering                                          │
│     ├─> Parse markdown with CrossReferencePlugin ⭐        │
│     │   └─> [[api:Symbol]] → O(1) lookup in xref_index    │
│     │   └─> Generate <a href="/api/...">Symbol</a>        │
│     └─> Optional: Auto-link code blocks ⭐ NEW             │
│                                                             │
│  8. Post-processing                                         │
│                                                             │
│  9. Link Validation ⭐ ENHANCED                             │
│     └─> Report broken [[api:...]] references              │
│                                                             │
│  10. Cache Update                                           │
│     └─> Persist unified xref_index to cache               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Data Structures

```python
# UNIFIED xref_index structure (extends existing)
site.xref_index = {
    # Existing cross-reference indices
    'by_path': {...},           # [[docs/page]] lookups
    'by_id': {...},             # [[id:my-page]] lookups
    'by_heading': {...},        # [[#heading]] lookups

    # NEW: API symbol index
    'api_symbols': {
        # Short names (unambiguous only)
        "Site": {
            "url": "/api/bengal/core/site/",
            "qualified_name": "bengal.core.site.Site",
            "type": "class",
        },

        # Qualified names (always unambiguous)
        "bengal.core.site.Site": {
            "url": "/api/bengal/core/site/",
            "qualified_name": "bengal.core.site.Site",
            "type": "class",
        },

        # Methods with anchors
        "Site.build": {
            "url": "/api/bengal/core/site/#build",
            "qualified_name": "bengal.core.site.Site.build",
            "type": "method",
        },

        # Fully qualified methods
        "bengal.core.site.Site.build": {
            "url": "/api/bengal/core/site/#build",
            "qualified_name": "bengal.core.site.Site.build",
            "type": "method",
        },
    },

    # NEW: Track ambiguous symbols
    'api_ambiguous': {
        'build': [  # Multiple classes have 'build' method
            'bengal.core.site.Site.build',
            'bengal.rendering.pipeline.RenderingPipeline.build',
        ],
    },

    # NEW: Cache key for invalidation
    'api_index_hash': 'sha256_hash_of_autodoc_files',
}
```

## Implementation Phases

### Phase 1: Core Index (Week 1)

**Goal**: Build and cache API symbol index integrated with existing xref system

#### Tasks

**1.1 Create API Index Builder**
- File: `bengal/autodoc/api_index.py` ⭐ NEW
- Features:
  - `build_api_index(site)` - Extract symbols from autodoc pages
  - `_extract_symbols(page)` - Parse autodoc markdown for symbols
  - `_resolve_ambiguity(symbols)` - Detect symbol name conflicts
  - Integration with existing xref_index structure

```python
# bengal/autodoc/api_index.py
from typing import Any
from pathlib import Path
from bengal.core.site import Site
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class APIIndexBuilder:
    """
    Build API symbol index from autodoc-generated pages.

    Integrates with existing xref_index for unified cross-referencing.
    """

    def __init__(self):
        self.symbols: dict[str, dict[str, Any]] = {}
        self.ambiguous: dict[str, list[str]] = {}

    def build(self, site: Site) -> dict[str, Any]:
        """
        Scan autodoc pages and build API symbol index.

        Args:
            site: Site instance with discovered pages

        Returns:
            Dict with 'api_symbols' and 'api_ambiguous' keys
        """
        logger.info("api_index_build_start", total_pages=len(site.pages))

        for page in site.pages:
            # Only process autodoc-generated pages
            if page.metadata.get('type') != 'python-module':
                continue

            # Extract symbols from this page
            page_symbols = self._extract_symbols_from_page(page)

            # Merge into index, tracking ambiguity
            for symbol, info in page_symbols.items():
                self._add_symbol(symbol, info)

        logger.info(
            "api_index_build_complete",
            total_symbols=len(self.symbols),
            ambiguous_symbols=len(self.ambiguous),
        )

        return {
            'api_symbols': self.symbols,
            'api_ambiguous': self.ambiguous,
        }

    def _extract_symbols_from_page(self, page: Page) -> dict[str, dict[str, Any]]:
        """
        Extract API symbols from an autodoc page.

        Parses the page content to find class/function/method definitions.
        Uses heading structure to infer symbol hierarchy.

        Args:
            page: Autodoc page to parse

        Returns:
            Dict of symbol_name -> symbol_info
        """
        symbols = {}
        module = page.metadata.get('module', '')
        base_url = page.url

        # Parse markdown headings to extract symbols
        # Format: ## Classes / ### `ClassName` / #### `method_name`
        content = page.content
        current_class = None

        import re

        # Match class definitions: ### `ClassName`
        class_pattern = re.compile(r'^###\s+`([A-Z][a-zA-Z0-9_]*)`', re.MULTILINE)
        for match in class_pattern.finditer(content):
            class_name = match.group(1)
            qualified_name = f"{module}.{class_name}" if module else class_name

            # Add both short and qualified names
            info = {
                'url': base_url,
                'qualified_name': qualified_name,
                'type': 'class',
                'page': page.source_path,
            }

            symbols[class_name] = info
            symbols[qualified_name] = info
            current_class = class_name

        # Match method definitions: #### `method_name`
        method_pattern = re.compile(r'^####\s+`([a-z_][a-zA-Z0-9_]*)`', re.MULTILINE)
        for match in method_pattern.finditer(content):
            if not current_class:
                continue

            method_name = match.group(1)
            anchor = method_name.lower().replace('_', '-')

            # Class.method shorthand
            short_name = f"{current_class}.{method_name}"
            qualified_name = f"{module}.{current_class}.{method_name}" if module else short_name

            info = {
                'url': f"{base_url}#{anchor}",
                'qualified_name': qualified_name,
                'type': 'method',
                'page': page.source_path,
            }

            symbols[short_name] = info
            symbols[qualified_name] = info

        # Match function definitions: ### `function_name`
        func_pattern = re.compile(r'^###\s+`([a-z_][a-zA-Z0-9_]*)`', re.MULTILINE)
        for match in func_pattern.finditer(content):
            func_name = match.group(1)
            if func_name.startswith('_'):  # Skip private
                continue

            qualified_name = f"{module}.{func_name}" if module else func_name
            anchor = func_name.lower().replace('_', '-')

            info = {
                'url': f"{base_url}#{anchor}",
                'qualified_name': qualified_name,
                'type': 'function',
                'page': page.source_path,
            }

            symbols[func_name] = info
            symbols[qualified_name] = info

        return symbols

    def _add_symbol(self, symbol: str, info: dict[str, Any]) -> None:
        """
        Add symbol to index, tracking ambiguity.

        If symbol already exists with different qualified name,
        mark as ambiguous and remove from main index.
        """
        if symbol in self.symbols:
            existing = self.symbols[symbol]
            if existing['qualified_name'] != info['qualified_name']:
                # Ambiguous! Track both
                if symbol not in self.ambiguous:
                    self.ambiguous[symbol] = [existing['qualified_name']]
                self.ambiguous[symbol].append(info['qualified_name'])
                # Remove from main index (force qualified usage)
                del self.symbols[symbol]
                return

        self.symbols[symbol] = info


def build_api_index(site: Site) -> dict[str, Any]:
    """
    Build API index from autodoc pages.

    Convenience function for use in orchestrator.
    """
    builder = APIIndexBuilder()
    return builder.build(site)
```

**1.2 Integrate into Build Pipeline**
- File: `bengal/orchestration/content.py` ⭐ MODIFY
- Add index building in Phase 2.5 (after content discovery)
- Merge into existing `site.xref_index`

```python
# In ContentOrchestrator.discover()
def discover(self) -> None:
    """Discover all content and build cross-reference indices."""
    # Existing content discovery
    self._discover_content()
    self._discover_assets()
    self._setup_page_references()
    self._apply_cascades()
    self._build_xref_index()

    # NEW: Build API symbol index if autodoc pages exist
    self._build_api_index()

def _build_api_index(self) -> None:
    """
    Build API symbol index from autodoc pages.

    Integrates with existing xref_index structure.
    """
    from bengal.autodoc.api_index import build_api_index

    # Check if we have any autodoc pages
    autodoc_pages = [
        p for p in self.site.pages
        if p.metadata.get('type') == 'python-module'
    ]

    if not autodoc_pages:
        logger.debug("no_autodoc_pages", message="Skipping API index build")
        return

    logger.info("building_api_index", page_count=len(autodoc_pages))

    # Build API index
    api_data = build_api_index(self.site)

    # Merge into existing xref_index
    self.site.xref_index['api_symbols'] = api_data['api_symbols']
    self.site.xref_index['api_ambiguous'] = api_data['api_ambiguous']

    # Compute hash for cache invalidation
    import hashlib
    autodoc_hash = hashlib.sha256()
    for page in autodoc_pages:
        autodoc_hash.update(str(page.source_path).encode())
        autodoc_hash.update(str(page.source_path.stat().st_mtime).encode())

    self.site.xref_index['api_index_hash'] = autodoc_hash.hexdigest()

    logger.info(
        "api_index_built",
        symbols=len(api_data['api_symbols']),
        ambiguous=len(api_data['api_ambiguous']),
    )
```

**1.3 Cache Integration**
- File: `bengal/cache/build_cache.py` ⭐ MODIFY
- Add `xref_index` field to cache (already includes api_symbols)
- Save/load index between builds
- Invalidate when autodoc sources change

```python
# In BuildCache
def save_xref_index(self, xref_index: dict[str, Any]) -> None:
    """
    Persist cross-reference index (including API symbols).

    Args:
        xref_index: Complete xref index with api_symbols
    """
    # Store in cache (xref_index is already JSON-serializable)
    self.cache['xref_index'] = xref_index

    logger.debug(
        "xref_index_cached",
        paths=len(xref_index.get('by_path', {})),
        api_symbols=len(xref_index.get('api_symbols', {})),
        ambiguous=len(xref_index.get('api_ambiguous', {})),
    )

def load_xref_index(self) -> dict[str, Any] | None:
    """
    Load cached cross-reference index.

    Returns:
        Cached xref_index or None if not cached or invalid
    """
    if 'xref_index' not in self.cache:
        return None

    xref_index = self.cache['xref_index']

    # Check if API index is still valid
    cached_hash = xref_index.get('api_index_hash')
    if cached_hash:
        # TODO: Compute current hash and compare
        # For now, always rebuild API index (safe)
        logger.debug("xref_index_loaded_from_cache")
        return xref_index

    return xref_index
```

**Deliverables:**
- ✅ `bengal/autodoc/api_index.py` with tests
- ✅ Integration in content orchestrator
- ✅ Cache save/load functionality
- ✅ Unit tests (target: 90%+ coverage)

**Testing:**
```bash
# Unit tests
pytest tests/unit/autodoc/test_api_index.py -v

# Integration test
pytest tests/integration/test_api_linking.py -v
```

---

### Phase 2: Enhanced Cross-Reference Plugin (Week 2)

**Goal**: Extend existing CrossReferencePlugin to support `[[api:...]]` syntax

#### Tasks

**2.1 Extend CrossReferencePlugin**
- File: `bengal/rendering/plugins/cross_references.py` ⭐ MODIFY
- Add support for `api:` prefix in pattern
- Integrate with `xref_index['api_symbols']`

```python
# Modified CrossReferencePlugin
class CrossReferencePlugin:
    """
    Mistune plugin for inline cross-references with [[link]] syntax.

    Syntax:
        [[docs/installation]]           -> Page link
        [[id:my-page]]                  -> ID-based link
        [[#heading-name]]               -> Anchor link
        [[api:Symbol]]                  -> API symbol link ⭐ NEW
        [[api:Class.method]]            -> API method link ⭐ NEW
    """

    def __init__(self, xref_index: dict[str, Any]):
        """Initialize with unified xref_index (includes api_symbols)."""
        self.xref_index = xref_index
        # Updated pattern to support api: prefix
        self.pattern = re.compile(
            r"\[\[(api:|id:)?([^\]|]+)(?:\|([^\]]+))?\]\]"
        )
        # Track unresolved for validation
        self.unresolved: list[tuple[str, str, str]] = []  # (ref, type, page)

    def _substitute_xrefs(self, text: str) -> str:
        """Substitute [[link]] patterns including [[api:...]]."""
        if "[[" not in text:
            return text

        def replace_xref(match: Match) -> str:
            prefix = match.group(1)  # 'api:', 'id:', or None
            ref = match.group(2).strip()
            text = match.group(3).strip() if match.group(3) else None

            # Route based on prefix
            if prefix == 'api:':
                return self._resolve_api_symbol(ref, text)
            elif prefix == 'id:':
                return self._resolve_id(ref, text)
            elif ref.startswith('#'):
                return self._resolve_heading(ref, text)
            else:
                return self._resolve_path(ref, text)

        return self.pattern.sub(replace_xref, text)

    def _resolve_api_symbol(self, symbol: str, text: str | None = None) -> str:
        """
        Resolve API symbol reference to link.

        Args:
            symbol: API symbol (e.g., 'Site', 'Site.build', 'bengal.core.site.Site')
            text: Optional custom link text

        Returns:
            HTML link or broken reference markup
        """
        api_symbols = self.xref_index.get('api_symbols', {})

        # Try direct lookup
        if symbol in api_symbols:
            info = api_symbols[symbol]
            link_text = text or symbol
            url = info['url']

            logger.debug(
                "api_symbol_resolved",
                symbol=symbol,
                qualified_name=info['qualified_name'],
                url=url,
            )

            return f'<a href="{url}" class="api-link"><code>{link_text}</code></a>'

        # Check if ambiguous
        ambiguous = self.xref_index.get('api_ambiguous', {})
        if symbol in ambiguous:
            # Track for validation report
            self.unresolved.append((symbol, 'api_ambiguous', ''))

            logger.debug(
                "api_symbol_ambiguous",
                symbol=symbol,
                matches=len(ambiguous[symbol]),
            )

            return (
                f'<span class="broken-ref api-ref-ambiguous" '
                f'data-symbol="{symbol}" '
                f'title="Ambiguous symbol: {symbol}">'
                f'<code>[{text or symbol}]</code></span>'
            )

        # Not found
        self.unresolved.append((symbol, 'api_not_found', ''))

        logger.debug(
            "api_symbol_not_found",
            symbol=symbol,
            available_symbols=len(api_symbols),
        )

        return (
            f'<span class="broken-ref api-ref-broken" '
            f'data-symbol="{symbol}" '
            f'title="API symbol not found: {symbol}">'
            f'<code>[{text or symbol}]</code></span>'
        )
```

**2.2 Update Parser Integration**
- File: `bengal/rendering/parser.py` ⭐ MODIFY
- Ensure CrossReferencePlugin gets complete xref_index with api_symbols

```python
# In MistuneParser.enable_cross_references()
def enable_cross_references(self, xref_index: dict[str, Any]) -> None:
    """
    Enable cross-reference plugin with unified index.

    Args:
        xref_index: Complete cross-reference index including:
            - by_path: Page path lookups
            - by_id: ID-based lookups
            - by_heading: Heading anchor lookups
            - api_symbols: API symbol lookups ⭐ NEW
            - api_ambiguous: Ambiguous symbols ⭐ NEW
    """
    from bengal.rendering.plugins import CrossReferencePlugin

    self._xref_plugin = CrossReferencePlugin(xref_index)
    self._xref_enabled = True

    logger.debug(
        "xref_plugin_enabled",
        paths=len(xref_index.get('by_path', {})),
        ids=len(xref_index.get('by_id', {})),
        headings=len(xref_index.get('by_heading', {})),
        api_symbols=len(xref_index.get('api_symbols', {})),
    )
```

**2.3 Link Resolution Logging**
- Enhanced logging for `[[api:...]]` resolution
- Track resolution rate for optimization

**Deliverables:**
- ✅ Enhanced `CrossReferencePlugin` with API support
- ✅ Parser integration updated
- ✅ Comprehensive tests for API syntax variants
- ✅ Unit tests (target: 95%+ coverage)

**Testing:**
```python
# tests/unit/rendering/plugins/test_cross_references.py

def test_api_simple_class():
    """Test [[api:Site]] resolves to class page."""

def test_api_qualified_class():
    """Test [[api:bengal.core.site.Site]] resolves."""

def test_api_method():
    """Test [[api:Site.build]] resolves to method anchor."""

def test_api_function():
    """Test [[api:render_page]] resolves to function."""

def test_api_unresolved():
    """Test [[api:DoesNotExist]] marked as broken."""

def test_api_ambiguous():
    """Test [[api:build]] marked as ambiguous when multiple matches."""

def test_api_with_custom_text():
    """Test [[api:Site|the Site class]] uses custom text."""
```

---

### Phase 3: Validation & Health Check (Week 3)

**Goal**: Catch and report broken API references with helpful suggestions

#### Tasks

**3.1 Create APILinkValidator**
- File: `bengal/health/validators/api_links.py` ⭐ NEW
- Check for broken `[[api:...]]` references
- Report ambiguous symbols with suggestions
- Use fuzzy matching for typos

```python
# bengal/health/validators/api_links.py
from typing import TYPE_CHECKING, override
from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult

if TYPE_CHECKING:
    from bengal.core.site import Site


class APILinkValidator(BaseValidator):
    """
    Validate API link references ([[api:...]]).

    Checks for:
    - Broken references (symbol not found)
    - Ambiguous references (multiple matches)
    - Suggestions for typos
    """

    name = "API Links"
    description = "Validates [[api:...]] references in documentation"
    enabled_by_default = True

    @override
    def validate(self, site: "Site") -> list[CheckResult]:
        """Validate API links in rendered pages."""
        results = []

        # Check if API index exists
        api_symbols = site.xref_index.get('api_symbols', {})
        if not api_symbols:
            results.append(
                CheckResult.info(
                    "No API symbols found",
                    recommendation="Run 'bengal autodoc' to generate API documentation"
                )
            )
            return results

        # Collect unresolved references from rendering
        broken_refs = []
        ambiguous_refs = []

        for page in site.pages:
            if not page.rendered_html:
                continue

            # Find broken API references
            import re
            broken_pattern = re.compile(
                r'<span class="broken-ref api-ref-broken"[^>]*data-symbol="([^"]+)"'
            )
            for match in broken_pattern.finditer(page.rendered_html):
                symbol = match.group(1)
                broken_refs.append((symbol, page.source_path))

            # Find ambiguous API references
            ambiguous_pattern = re.compile(
                r'<span class="broken-ref api-ref-ambiguous"[^>]*data-symbol="([^"]+)"'
            )
            for match in ambiguous_pattern.finditer(page.rendered_html):
                symbol = match.group(1)
                ambiguous_refs.append((symbol, page.source_path))

        # Report broken references
        if broken_refs:
            # Get suggestions using fuzzy matching
            unique_broken = list(set(ref[0] for ref in broken_refs))

            details = []
            for symbol in unique_broken[:5]:
                suggestions = self._find_similar_symbols(symbol, api_symbols)
                detail = f"  • {symbol}"
                if suggestions:
                    detail += f" (did you mean: {', '.join(suggestions[:3])}?)"
                details.append(detail)

            results.append(
                CheckResult.error(
                    f"{len(broken_refs)} broken API reference(s)",
                    recommendation=(
                        "Fix broken API references. Use qualified names if needed. "
                        "Run 'bengal build --verbose' to see all broken refs."
                    ),
                    details=details,
                )
            )

        # Report ambiguous references
        if ambiguous_refs:
            ambiguous_map = site.xref_index.get('api_ambiguous', {})

            details = []
            unique_ambiguous = list(set(ref[0] for ref in ambiguous_refs))
            for symbol in unique_ambiguous[:5]:
                matches = ambiguous_map.get(symbol, [])
                detail = f"  • {symbol} → {len(matches)} matches"
                if matches:
                    detail += f"\n    Use: [[api:{matches[0]}]]"
                details.append(detail)

            results.append(
                CheckResult.error(
                    f"{len(ambiguous_refs)} ambiguous API reference(s)",
                    recommendation=(
                        "Use fully qualified names for ambiguous symbols. "
                        "Example: [[api:bengal.core.site.Site.build]]"
                    ),
                    details=details,
                )
            )

        # Success case
        if not broken_refs and not ambiguous_refs:
            results.append(
                CheckResult.success(
                    f"All API links valid ({len(api_symbols)} symbols indexed)"
                )
            )

        return results

    def _find_similar_symbols(
        self,
        symbol: str,
        api_symbols: dict[str, dict]
    ) -> list[str]:
        """
        Find similar symbols using fuzzy matching.

        Args:
            symbol: The symbol to match
            api_symbols: Available API symbols

        Returns:
            List of similar symbol names
        """
        from difflib import get_close_matches

        # Get symbol names
        available = list(api_symbols.keys())

        # Fuzzy match (60% similarity threshold)
        matches = get_close_matches(symbol, available, n=3, cutoff=0.6)

        return matches
```

**3.2 Integrate with Health Check**
- File: `bengal/health/health_check.py` ⭐ MODIFY
- Add APILinkValidator to validator list

```python
# In HealthCheck._register_default_validators()
from bengal.health.validators.api_links import APILinkValidator

# Phase 2: Content validation
self.register(APILinkValidator())  # NEW
```

**3.3 CLI Output for Errors**
- Pretty-print broken links with context
- Show suggestions for typos

```bash
# Example output
❌ API Links

  5 broken API reference(s) found:
    • BuildOrchestrator (did you mean: BuildOrchestrator, BuildStats?)
    • Sight (did you mean: Site, Section?)

  2 ambiguous API reference(s) found:
    • build → 3 matches
      Use: [[api:Site.build]]

  Recommendation: Fix broken API references. Use qualified names if needed.
```

**Deliverables:**
- ✅ `bengal/health/validators/api_links.py`
- ✅ Integration with health check system
- ✅ Fuzzy matching for suggestions
- ✅ CLI output formatting
- ✅ Tests for validation logic

---

### Phase 4: Auto-Linking (Week 4) - OPTIONAL

**Goal**: Auto-detect and link code in backticks (opt-in for performance)

#### Tasks

**4.1 Create Code Auto-Linker**
- File: `bengal/rendering/plugins/auto_link_code.py` ⭐ NEW
- Post-process HTML to detect linkable code
- Make it opt-in via config
- Cache decisions for performance

```python
# bengal/rendering/plugins/auto_link_code.py
import re
from typing import Any
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


class CodeAutoLinker:
    """
    Auto-link backticked code to API docs.

    WARNING: This feature post-processes HTML and can add latency.
    Only enable if you need automatic linking of inline code.

    Performance: ~2-3ms per page (cached decisions help)

    Config:
        [autodoc]
        auto_link_code = true
    """

    # Match: <code>ClassName</code> or <code>ClassName.method()</code>
    # Only match if NOT already in <a> tag
    CODE_PATTERN = re.compile(
        r'<code>(?!<a)([A-Z][a-zA-Z0-9_]+(?:\.[a-z_][a-zA-Z0-9_]*)?(?:\(\))?)</code>'
    )

    def __init__(self, api_symbols: dict[str, dict[str, Any]]):
        """
        Initialize auto-linker.

        Args:
            api_symbols: API symbol index from xref_index
        """
        self.api_symbols = api_symbols
        self.linked_count = 0
        self.cache: dict[str, str | None] = {}  # symbol -> url or None

    def process(self, html: str, cache_key: str = '') -> str:
        """
        Auto-link code blocks to API docs.

        Args:
            html: Rendered HTML content
            cache_key: Cache key for this page (optional)

        Returns:
            HTML with auto-linked code
        """
        if '<code>' not in html:
            return html  # Fast path

        def replace_code(match: re.Match) -> str:
            code = match.group(1)
            symbol = code.rstrip('()')  # Remove trailing ()

            # Check cache first
            if symbol in self.cache:
                url = self.cache[symbol]
                if url:
                    self.linked_count += 1
                    return f'<a href="{url}" class="api-autolink"><code>{code}</code></a>'
                return match.group(0)  # Cache miss

            # O(1) lookup in API index
            if symbol in self.api_symbols:
                url = self.api_symbols[symbol]['url']
                self.cache[symbol] = url
                self.linked_count += 1
                return f'<a href="{url}" class="api-autolink"><code>{code}</code></a>'

            # Not found - cache the miss
            self.cache[symbol] = None
            return match.group(0)  # Leave as-is

        result = self.CODE_PATTERN.sub(replace_code, html)

        if self.linked_count > 0:
            logger.debug(
                "auto_linked_code",
                cache_key=cache_key,
                links_added=self.linked_count,
            )

        return result


def create_auto_linker(xref_index: dict[str, Any]) -> CodeAutoLinker:
    """Create auto-linker from xref index."""
    api_symbols = xref_index.get('api_symbols', {})
    return CodeAutoLinker(api_symbols)
```

**4.2 Integration in Rendering Pipeline**
- File: `bengal/rendering/pipeline.py` ⭐ MODIFY
- Apply after markdown parsing, before template rendering
- Only if `auto_link_code` enabled in config

```python
# In RenderingPipeline.process_page()
def process_page(self, page: Page) -> None:
    """Process a single page through the rendering pipeline."""
    # ... existing markdown parsing ...

    # NEW: Auto-link code if enabled
    if self.site.config.get('autodoc', {}).get('auto_link_code', False):
        from bengal.rendering.plugins.auto_link_code import create_auto_linker

        auto_linker = create_auto_linker(self.site.xref_index)
        html = auto_linker.process(
            html,
            cache_key=str(page.source_path)
        )

    # ... continue with template rendering ...
```

**4.3 Configuration Option**
- Add to `bengal.toml`
- Default: disabled (opt-in for performance)

```toml
[autodoc]
# Auto-link inline code to API documentation
auto_link_code = false  # Default: false (opt-in)

# Alternative: per-page opt-in via frontmatter
# ---
# auto_link_code: true
# ---
```

**4.4 Performance Testing**
- Measure overhead on 100+ page site
- Ensure < 3ms per page with caching

**Deliverables:**
- ✅ `bengal/rendering/plugins/auto_link_code.py`
- ✅ Configuration options
- ✅ Performance benchmarks
- ✅ Tests for auto-detection patterns

---

## Testing Strategy

### Unit Tests (Target: 95%+ coverage)

```
tests/unit/autodoc/
├── test_api_index.py                # Index building, symbol extraction
│   ├── test_build_index
│   ├── test_extract_symbols_from_page
│   ├── test_ambiguous_detection
│   ├── test_qualified_names
│   └── test_cache_integration

tests/unit/rendering/plugins/
├── test_cross_references.py         # Enhanced with API support
│   ├── test_api_simple_ref
│   ├── test_api_qualified_ref
│   ├── test_api_method_ref
│   ├── test_api_unresolved
│   ├── test_api_ambiguous
│   └── test_api_custom_text
│
└── test_auto_link_code.py           # Auto-linking (optional)
    ├── test_detect_class_names
    ├── test_detect_methods
    ├── test_no_false_positives
    └── test_cache_performance

tests/unit/health/validators/
└── test_api_links.py                # Validation
    ├── test_detect_broken_links
    ├── test_detect_ambiguous
    ├── test_fuzzy_suggestions
    └── test_report_format
```

### Integration Tests

```
tests/integration/
└── test_api_linking_workflow.py
    ├── test_full_autodoc_link_flow   # autodoc → index → render → validate
    ├── test_incremental_api_cache    # Index persists across builds
    ├── test_broken_link_detection    # Catches invalid refs
    └── test_cross_page_linking       # Docs → API, API → docs
```

### Performance Tests

```
tests/performance/
└── test_api_index_performance.py
    ├── test_index_build_speed        # < 50ms for 100 modules
    ├── test_lookup_speed             # < 0.1ms per lookup
    ├── test_render_overhead          # < 1% build time increase
    └── test_auto_link_overhead       # < 3ms per page (if enabled)
```

### Test Data

```
tests/fixtures/api_linking/
├── autodoc_pages/               # Sample autodoc output
│   ├── module_a.md
│   ├── module_b.md
│   └── class_with_methods.md
├── content_with_refs/           # Pages with [[api:...]] links
│   ├── valid_refs.md
│   ├── broken_refs.md
│   └── ambiguous_refs.md
└── expected_output/             # Expected HTML
    ├── valid_refs.html
    └── broken_refs_errors.txt
```

## Performance Targets

| Metric | Target | Measured How |
|--------|--------|--------------|
| **Index Build Time** | < 50ms for 100 modules | `pytest tests/performance/test_api_index_performance.py` |
| **Symbol Lookup** | < 0.1ms per lookup | Direct timing in test |
| **Render Overhead** | < 1% build time | Compare with/without API linking |
| **Cache Load** | < 1ms to load index | Time cache load operation |
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

[health_check.validators]
# Enable API link validation (default: true)
api_links = true
```

## Migration Path

### For Existing Bengal Sites

No breaking changes - this is purely additive:

1. **Opt-in**: Use `[[api:...]]` syntax where desired
2. **No change**: Existing sites continue to work
3. **Gradual adoption**: Add API links incrementally

### Example Migration

```markdown
<!-- Before -->
See the [Site class](/api/bengal/core/site/) for details.
Call the [build method](/api/bengal/core/site/#build) to build.

<!-- After -->
See the [[api:Site]] class for details.
Call the [[api:Site.build]] method to build.
```

## Timeline (Revised)

### Week 1: Core Index (Phase 1)
- ✅ API index builder (`api_index.py`)
- ✅ Build pipeline integration
- ✅ Cache integration
- ✅ Unit tests

### Week 2: Plugin Enhancement (Phase 2)
- ✅ Extend CrossReferencePlugin for `[[api:...]]`
- ✅ Parser integration
- ✅ Tests for syntax variants
- ✅ Documentation

### Week 3: Validation (Phase 3)
- ✅ API link validator
- ✅ Health check integration
- ✅ CLI error reporting
- ✅ Fuzzy suggestion matching
- ✅ Integration tests

### Week 4: Polish & Optional Features (Phase 4)
- ⚪ Auto-linking (optional)
- ✅ Performance testing
- ✅ User documentation
- ✅ Example content

**Total: 4 weeks** (3 core + 1 optional/polish)

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
| **Performance regression** | High | Benchmark continuously, use unified index |
| **Ambiguous symbol names** | Medium | Detect and warn, prefer qualified names |
| **Cache invalidation bugs** | Medium | Hash autodoc sources, validate on load |
| **Complex nested classes** | Low | Test edge cases, handle gracefully |
| **Memory usage on large sites** | Low | Use efficient dict structures, test at scale |
| **Plugin integration conflicts** | Low | Extend existing plugin vs new plugin |

## Future Enhancements (Post-v0.2.0)

1. **Multiple languages** - JavaScript, TypeScript via TSDoc
2. **External linking** - Link to other projects' docs (Intersphinx-style)
3. **Hover tooltips** - Show signatures on hover
4. **IDE integration** - Language server for autocomplete
5. **Link analytics** - Track which APIs are most referenced
6. **Symbol search** - Fast CLI/web search for symbols

## Documentation

### User-Facing Docs

Create/update these pages:

1. **docs/features/api-linking.md** - Overview and usage
2. **docs/reference/link-syntax.md** - Complete syntax reference
3. **docs/guides/documenting-code.md** - Best practices
4. **CHANGELOG.md** - Feature announcement

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

### Disambiguation

If you get an "ambiguous symbol" error, use a qualified name:

```markdown
<!-- Ambiguous -->
[[api:build]]  ❌

<!-- Unambiguous -->
[[api:Site.build]]  ✅
```

### Auto-Linking

Enable auto-linking to convert `ClassName` in backticks to links:

```toml
[autodoc]
auto_link_code = true
```

Then writing `Site` automatically links to the API docs.

**Note:** Auto-linking adds ~2-3ms per page. Only enable if needed.
```

## Questions / Open Issues

1. **Qualified name preference**: Should we prefer qualified names in suggestions?
   - **Decision**: Yes, show qualified names first to avoid ambiguity

2. **Performance threshold**: What's acceptable overhead?
   - **Decision**: < 1% build time, < 50ms index build (aligned with Bengal's speed goals)

3. **Auto-linking defaults**: Enable by default or opt-in?
   - **Decision**: Opt-in to avoid surprises and respect performance

4. **Anchor format**: `#method-name` vs `#method_name` vs `#method`?
   - **Decision**: Use `#method-name` (slugified) for consistency with existing heading anchors

5. **Cache storage**: Separate file or in BuildCache?
   - **Decision**: In BuildCache as part of xref_index (single source of truth)

## References

- [Sphinx Intersphinx](https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html)
- [MkDocs Autorefs](https://mkdocstrings.github.io/autorefs/)
- [Hugo Cross References](https://gohugo.io/content-management/cross-references/)
- Bengal Architecture: `/ARCHITECTURE.md`
- Bengal Autodoc: `/bengal/autodoc/`
- Bengal Cross-References: `/bengal/rendering/plugins/cross_references.py`

## Comparison: Original vs Refined Plan

| Aspect | Original Plan | Refined Plan | Why Changed |
|--------|---------------|--------------|-------------|
| **Plugin Architecture** | New APILinkPlugin | Extend CrossReferencePlugin | Reduce overhead, single system |
| **Index Storage** | Separate `site.api_index` | Merge into `site.xref_index` | Single source of truth |
| **Build Phase** | After content discovery | Phase 2.5 (after sections) | Ensure metadata stability |
| **Cache Structure** | Separate API cache | Part of xref_index | Simpler invalidation |
| **Auto-linking** | Phase 4 (Week 4) | Phase 4 (Week 4) optional | Same (good decision) |
| **Timeline** | 5 weeks | 4 weeks | Plugin extension is faster |
| **Performance Target** | < 1% overhead | < 1% overhead | Same (good target) |

---

**Next Steps:**
1. ✅ Review refined plan
2. Create feature branch: `feat/api-link-index`
3. Begin Phase 1 implementation
4. Set up performance benchmarks
5. Test on Bengal's own codebase (99 modules)

**Benefits of Refined Approach:**
- ✅ Simpler architecture (fewer moving parts)
- ✅ Better performance (unified index, single plugin)
- ✅ Easier maintenance (extend existing vs new system)
- ✅ Consistent UX (all `[[...]]` syntax works the same)
- ✅ Faster implementation (4 weeks vs 5 weeks)
