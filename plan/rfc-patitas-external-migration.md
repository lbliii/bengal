# RFC: Patitas External Package Migration

**Status**: Complete  
**Created**: 2026-01-13  
**Author**: Bengal Contributors

## Executive Summary

Bengal has migrated from an embedded patitas parser to the external `patitas>=0.1.0` PyPI package. This removes 12,135 lines of duplicated code while keeping Bengal-specific extensions (directives, roles, page context).

**Result**: Bengal now depends on `patitas` as a first-class external dependency, enabling independent versioning, testing, and optimization of the Markdown parser.

## Problem Statement

### Before Migration

Bengal contained a full copy of the patitas Markdown parser embedded at:

```
bengal/rendering/parsers/patitas/
├── lexer/          # ~2,500 lines
├── parsing/        # ~5,000 lines
├── plugins/        # ~500 lines
├── parser.py       # ~330 lines
├── nodes.py        # ~550 lines
├── tokens.py       # ~160 lines
├── location.py     # ~90 lines
├── stringbuilder.py # ~110 lines
├── directives/     # Bengal-specific
├── roles/          # Bengal-specific
└── renderers/      # Bengal-specific extensions
```

**Problems**:

1. **Code duplication**: Parser improvements had to be made in two places
2. **Testing burden**: CommonMark compliance tests duplicated in Bengal
3. **Version drift**: Bengal's embedded version could diverge from canonical patitas
4. **Dependency confusion**: Other projects wanting patitas had to copy from Bengal

### After Migration

```
bengal/rendering/parsers/patitas/
├── directives/     # ✅ KEPT (40+ Bengal-specific directives)
├── roles/          # ✅ KEPT (Bengal-specific roles)
├── renderers/      # ✅ KEPT (extended renderer with page_context)
├── wrapper.py      # ✅ KEPT (PatitasParser adapter)
├── config.py       # ✅ KEPT (Bengal's config API)
└── ... (Bengal-specific extensions only)
```

**External dependency**: `patitas>=0.1.0` (published to PyPI)

## Design Decisions

### 1. What Moves to External Package

**Core parser components** (generic Markdown parsing):

| Component | Rationale |
|-----------|-----------|
| `lexer/` | State-machine tokenizer - no Bengal dependencies |
| `parsing/` | Recursive descent parser - no Bengal dependencies |
| `plugins/` | GFM extensions (tables, strikethrough, etc.) |
| `nodes.py` | AST node definitions - pure data structures |
| `tokens.py` | Token types - enumeration only |
| `location.py` | Source location tracking |
| `stringbuilder.py` | O(n) string building utility |

### 2. What Stays in Bengal

**Bengal-specific extensions** (require Bengal infrastructure):

| Component | Rationale |
|-----------|-----------|
| `directives/` | 40+ Bengal-specific directives (admonition, cards, tabs, etc.) |
| `roles/` | Bengal-specific roles (icons, formatting) |
| `renderers/html.py` | Extended with `page_context`, `directive_cache` |
| `wrapper.py` | `PatitasParser` adapter for `BaseMarkdownParser` |
| `config.py` | Token-based reset API (different from external patitas) |
| `render_config.py` | Bengal-specific render configuration |
| `accumulator.py` | Metadata accumulator (RFC: contextvar-downstream-patterns) |
| `request_context.py` | Request-scoped context |
| `pool.py` | Parser/renderer pooling (disabled, see below) |

### 3. Parser Pooling Disabled

Bengal's `ParserPool` relied on a `_reinit()` method to reuse parser instances:

```python
# Old approach (embedded parser)
parser = pool.pop()
parser._reinit(source, source_file)  # Reset state without allocation
```

External patitas `Parser` doesn't expose `_reinit()`. Options considered:

1. **Add `_reinit()` to patitas**: Rejected - YAGNI, Parser creation is cheap
2. **Skip pooling**: ✅ Selected - Always create new Parser instances
3. **Fork patitas**: Rejected - Defeats purpose of extraction

**Decision**: Parser pooling disabled. Benchmarks show negligible impact for typical workloads.

### 4. Directive API Compatibility

Bengal's directives expect different option handling than external patitas:

```python
# Bengal's expectation
node.options.columns  # Direct attribute access

# External patitas
node.options.get("columns")  # Dict-like access
```

**Current state**: Some directive tests fail. Follow-up work needed to align APIs.

## Migration Steps Completed

### Step 1: Publish patitas to PyPI ✅

```bash
cd patitas
uv build
uv publish  # patitas 0.1.0 on PyPI
```

### Step 2: Add Dependency ✅

```toml
# bengal/pyproject.toml
dependencies = [
    "patitas>=0.1.0",
    # ...
]
```

### Step 3: Update Imports ✅

Global search-replace across Bengal:

```python
# Before
from bengal.rendering.parsers.patitas.nodes import Heading
from bengal.rendering.parsers.patitas.parser import Parser

# After
from patitas.nodes import Heading
from patitas.parser import Parser
```

### Step 4: Delete Embedded Code ✅

```bash
rm -rf bengal/rendering/parsers/patitas/{lexer,parsing,plugins}
rm bengal/rendering/parsers/patitas/{parser,nodes,tokens,location,stringbuilder}.py
```

**Lines deleted**: 12,135

### Step 5: Rename Test Directory ✅

```bash
mv tests/rendering/parsers/patitas tests/rendering/parsers/test_patitas
```

Avoids namespace collision with external `patitas` package.

### Step 6: Delete Internal Tests ✅

Tests that belong in patitas repo (not Bengal):

- `test_lexer.py` - Tests Lexer internals
- `test_parser.py` - Tests Parser AST construction

## Test Results

### CommonMark Compliance

```
655 passed (100%)
```

All CommonMark spec examples pass with external patitas.

### Bengal Integration Tests

```
1043 passed
23 failed
```

Failing tests are due to:

1. **Directive API differences** (11 tests): Bengal directives expect `options.attribute`, patitas uses dict-like access
2. **GFM extension differences** (6 tests): Table wrapper, strikethrough rendering differences
3. **FencedCode API change** (3 tests): Now uses zero-copy `get_code(source)` instead of `code` attribute
4. **Autolink edge cases** (3 tests): Minor parsing differences

## Follow-Up Work

### Priority 1: Directive API Alignment

Update Bengal's directives to work with external patitas's `DirectiveOptions`:

```python
# Current Bengal directive
class ChildCardsDirective:
    def render(self, node, sb):
        columns = node.options.columns  # ❌ Fails

# Updated for external patitas
class ChildCardsDirective:
    options_class = ChildCardsOptions  # Define typed options
    
    def render(self, node, sb):
        columns = node.options.columns  # ✅ Works with typed options
```

### Priority 2: Test Expectations Update

Update tests that check implementation details:

```python
# Old (tests internal representation)
assert code.code == "hello"

# New (tests via method)
assert code.get_code(source) == "hello"
```

### Priority 3: Evaluate Pooling Need

If benchmarks show parser creation is a bottleneck:

1. Add `_reinit()` method to external patitas
2. Re-enable Bengal's `ParserPool`

Current evidence suggests this is unnecessary.

## Appendix A: File Inventory

### Deleted from Bengal (12,135 lines)

```
lexer/__init__.py                    44
lexer/classifiers/__init__.py        48
lexer/classifiers/directive.py      299
lexer/classifiers/fence.py          131
lexer/classifiers/footnote.py        61
lexer/classifiers/heading.py         75
lexer/classifiers/html.py           428
lexer/classifiers/link_ref.py       323
lexer/classifiers/list.py           158
lexer/classifiers/quote.py          132
lexer/classifiers/thematic.py        66
lexer/core.py                       367
lexer/modes.py                       99
lexer/scanners/__init__.py           21
lexer/scanners/block.py             214
lexer/scanners/directive.py         187
lexer/scanners/fence.py             102
lexer/scanners/html.py              129
location.py                          89
nodes.py                            549
parser.py                           327
parsing/__init__.py                  39
parsing/blocks/__init__.py           73
parsing/blocks/core.py              813
parsing/blocks/directive.py         211
parsing/blocks/footnote.py           87
parsing/blocks/list/__init__.py      27
parsing/blocks/list/blank_line.py   200
parsing/blocks/list/indent.py       119
parsing/blocks/list/item_blocks.py  281
parsing/blocks/list/marker.py       180
parsing/blocks/list/mixin.py        929
parsing/blocks/list/nested.py       349
parsing/blocks/list/trace.py        110
parsing/blocks/list/types.py        120
parsing/blocks/table.py             188
parsing/charsets.py                  95
parsing/containers.py               299
parsing/inline/__init__.py           81
parsing/inline/core.py              695
parsing/inline/emphasis.py          199
parsing/inline/links.py             687
parsing/inline/match_registry.py    136
parsing/inline/special.py           432
parsing/inline/tokens.py            163
parsing/token_nav.py                 82
plugins/__init__.py                 197
plugins/autolinks.py                 74
plugins/footnotes.py                 76
plugins/math.py                      72
plugins/strikethrough.py             62
plugins/table.py                     73
plugins/task_lists.py                71
stringbuilder.py                    109
tokens.py                           159
```

### Kept in Bengal

```
__init__.py              # Re-exports, Bengal's Markdown class
accumulator.py           # Metadata accumulator
config.py                # Bengal's config (token-based reset)
directives/              # 40+ Bengal-specific directives
pool.py                  # Parser/renderer pooling
protocols.py             # Bengal protocols
render_config.py         # Bengal render config
renderers/html.py        # Extended renderer
request_context.py       # Request context
roles/                   # Bengal-specific roles
wrapper.py               # PatitasParser adapter
```

## Appendix B: Import Mapping

| Before (Bengal embedded) | After (External patitas) |
|--------------------------|--------------------------|
| `bengal.rendering.parsers.patitas.nodes` | `patitas.nodes` |
| `bengal.rendering.parsers.patitas.tokens` | `patitas.tokens` |
| `bengal.rendering.parsers.patitas.parser` | `patitas.parser` |
| `bengal.rendering.parsers.patitas.lexer` | `patitas.lexer` |
| `bengal.rendering.parsers.patitas.location` | `patitas.location` |
| `bengal.rendering.parsers.patitas.stringbuilder` | `patitas.stringbuilder` |

## References

- [patitas on PyPI](https://pypi.org/project/patitas/)
- [RFC: patitas-markdown-parser](plan/drafted/rfc-patitas-markdown-parser.md)
- [RFC: contextvar-config-implementation](plan/rfc-contextvar-config-implementation.md)
- [RFC: patitas-performance-optimization](../patitas/plan/rfc-performance-optimization.md)
