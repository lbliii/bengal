# Patitas Complexity Analysis

## Overview

All operations in Patitas are designed for **O(n)** document processing where n = document size.

---

## Architecture

Both the Lexer and Parser use a mixin-based design for modularity:

### Lexer Architecture

```
Lexer
├── Classifiers (pure logic, no state mutation)
│   ├── HeadingClassifierMixin       # ATX headings
│   ├── FenceClassifierMixin         # Fenced code blocks
│   ├── ThematicClassifierMixin      # Thematic breaks
│   ├── QuoteClassifierMixin         # Block quotes
│   ├── ListClassifierMixin          # List markers
│   ├── LinkRefClassifierMixin       # Link reference definitions
│   ├── FootnoteClassifierMixin      # Footnote definitions
│   ├── HtmlClassifierMixin          # HTML blocks (types 1-7)
│   └── DirectiveClassifierMixin     # MyST directives
└── Scanners (mode-specific scanning)
    ├── BlockScannerMixin            # Block mode dispatch
    ├── FenceScannerMixin            # Code fence mode
    ├── DirectiveScannerMixin        # Directive mode
    └── HtmlScannerMixin             # HTML block mode
```

### Parser Architecture

```
Parser
├── TokenNavigationMixin     # Token stream traversal
├── InlineParsingMixin       # Inline content parsing
│   ├── InlineParsingCoreMixin
│   ├── EmphasisMixin
│   ├── LinkParsingMixin
│   └── SpecialInlineMixin
└── BlockParsingMixin        # Block-level parsing
    ├── BlockParsingCoreMixin
    ├── ListParsingMixin
    ├── TableParsingMixin
    ├── DirectiveParsingMixin
    └── FootnoteParsingMixin
```

### Inline Token Architecture (RFC: Performance Modernization)

```
InlineToken (NamedTuple union type)
├── DelimiterToken    # Emphasis/strikethrough delimiters (*, _, ~~)
├── TextToken         # Plain text content
├── CodeSpanToken     # Inline code
├── NodeToken         # Pre-parsed AST nodes (links, images)
├── HardBreakToken    # Hard line breaks
└── SoftBreakToken    # Soft line breaks

MatchRegistry         # External delimiter match tracking
├── record_match()    # O(1) - Record opener/closer pair
├── is_active()       # O(1) - Check if delimiter active
├── deactivate()      # O(1) - Mark delimiter inactive
└── remaining_count() # O(1) - Get unconsumed delimiter count
```

**Key Design Decisions:**
- **Immutable tokens**: NamedTuples instead of dicts (~60% memory reduction)
- **External match tracking**: MatchRegistry decouples state from tokens
- **O(1) character sets**: Frozensets in `parsing/charsets.py`

---

## Lexer Complexity

| Operation | Complexity | Notes |
|-----------|------------|-------|
| `tokenize()` | **O(n)** | Single pass through source |
| Line detection | O(1) | Simple character checks |
| Token creation | O(1) | Dataclass instantiation |

**Total**: O(n) where n = source length

---

## Parser Complexity

| Operation | Complexity | Notes |
|-----------|------------|-------|
| `parse()` | **O(t)** | Where t = number of tokens |
| `_parse_block()` | O(1) | Match dispatch |
| `_parse_inline()` | O(i) | Where i = inline content length |
| `_process_emphasis()` | O(d²) worst | Where d = delimiter count (typically small) |
| `_parse_list()` | O(l) | Where l = list content tokens |

**Total**: O(t) where t = tokens ≈ O(n)

### Emphasis Algorithm

The CommonMark delimiter stack algorithm has worst-case O(d²) for pathological inputs with many unmatched delimiters. In practice, d is small (typically < 10 per paragraph), making it effectively O(1) per paragraph.

---

## Space Complexity

| Component | Space | Notes |
|-----------|-------|-------|
| Lexer | O(n) | Token list |
| Parser | O(1) | Only position tracking |
| AST | O(a) | Where a = AST nodes |

**Total**: O(n) space where n = source size

---

## File Organization

### Lexer Package

| File | Lines | Purpose |
|------|-------|---------|
| `lexer/__init__.py` | ~40 | Re-exports Lexer, LexerMode |
| `lexer/core.py` | ~280 | Lexer class + navigation helpers |
| `lexer/modes.py` | ~90 | LexerMode enum, HTML tag constants |
| `lexer/classifiers/heading.py` | ~60 | ATX heading classification |
| `lexer/classifiers/fence.py` | ~110 | Fenced code classification |
| `lexer/classifiers/thematic.py` | ~55 | Thematic break classification |
| `lexer/classifiers/quote.py` | ~50 | Block quote classification |
| `lexer/classifiers/list.py` | ~130 | List marker classification |
| `lexer/classifiers/link_ref.py` | ~75 | Link reference definition |
| `lexer/classifiers/footnote.py` | ~55 | Footnote definition |
| `lexer/classifiers/html.py` | ~210 | HTML blocks (types 1-7) |
| `lexer/classifiers/directive.py` | ~220 | MyST directive classification |
| `lexer/scanners/block.py` | ~160 | Block mode scanner |
| `lexer/scanners/fence.py` | ~85 | Code fence mode scanner |
| `lexer/scanners/directive.py` | ~140 | Directive mode scanner |
| `lexer/scanners/html.py` | ~100 | HTML block mode scanner |

**Lexer Total**: ~1860 lines across 16 files (max ~280 lines/file)

### Parser Package

| File | Lines | Purpose |
|------|-------|---------|
| `parser.py` | ~150 | Main parser class |
| `parsing/charsets.py` | ~60 | O(1) character classification frozensets |
| `parsing/token_nav.py` | ~50 | Token navigation |
| `parsing/inline/core.py` | ~350 | Core inline parsing with typed tokens |
| `parsing/inline/emphasis.py` | ~170 | CommonMark emphasis with MatchRegistry |
| `parsing/inline/tokens.py` | ~150 | Typed NamedTuple inline tokens |
| `parsing/inline/match_registry.py` | ~100 | External delimiter match tracking |
| `parsing/inline/links.py` | ~150 | Link/image parsing |
| `parsing/inline/special.py` | ~100 | HTML/role/math |
| `parsing/blocks/core.py` | ~290 | Block dispatch + basics |
| `parsing/blocks/list.py` | ~310 | List parsing |
| `parsing/blocks/table.py` | ~150 | GFM tables |
| `parsing/blocks/directive.py` | ~180 | Directive parsing |
| `parsing/blocks/footnote.py` | ~80 | Footnote definitions |

**Parser Total**: ~2300 lines across 14 files

---

## Optimization Checklist

### Lexer
- [x] Single-pass tokenization
- [x] Zero-copy source references (FencedCode)
- [x] Efficient regex patterns
- [x] Frozenset character classification (O(1) lookup)

### Parser
- [x] Match dispatch for block types (O(1))
- [x] Frozenset for inline special chars (O(1) lookup)
- [x] Immutable AST nodes (thread-safe)
- [x] Local variable caching in hot loops

### Inline Parsing (RFC: Performance Modernization)
- [x] NamedTuple tokens (~60% memory vs dicts)
- [x] External MatchRegistry for delimiter tracking
- [x] Pattern matching for type-safe dispatch
- [x] Centralized charsets.py for O(1) classification

### Memory
- [x] Generator-based lexer option
- [x] Zero-copy code block content via source offsets
- [x] Immutable tuples for AST children
- [x] Immutable NamedTuple inline tokens

---

## Threading Characteristics

| Aspect | Patitas |
|--------|---------|
| Parse | Single-threaded (instance state) |
| AST | **Immutable** (frozen dataclasses) |
| Share AST | **Thread-safe** |

---

## Comparison

### Lexer Modularization

| Metric | Before (1 file) | After (16 files) |
|--------|-----------------|------------------|
| Max file size | 1482 lines | ~280 lines |
| Avg file size | 1482 lines | ~115 lines |
| Testability | Hard (monolithic) | Easy (per-classifier) |
| Maintainability | Poor | Good |
| Navigation | Hard | Easy (by concern) |

### Parser Modularization

| Metric | Before (1 file) | After (14 files) |
|--------|-----------------|------------------|
| Max file size | 1950 lines | 310 lines |
| Avg file size | 1950 lines | ~175 lines |
| Testability | Hard (monolithic) | Easy (per-mixin) |
| Maintainability | Poor | Good |
| Navigation | Hard | Easy (by concern) |
