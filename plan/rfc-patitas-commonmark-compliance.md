# RFC: Patitas CommonMark Compliance & Test Coverage

**Status**: Draft  
**Author**: Bengal Team  
**Created**: 2026-01-01  
**Updated**: 2026-01-01  
**Target**: Patitas 1.0

## Executive Summary

Patitas must achieve near-complete CommonMark 0.31 compliance to be trusted as a production markdown parser. This RFC documents known compliance gaps, proposes a comprehensive test strategy, and outlines implementation priorities.

**Goal**: Make patitas the most reliable, fastest, and best-tested markdown parser in the Python ecosystem.

## Background

### Why CommonMark Compliance Matters

1. **User Trust**: Developers expect markdown to render consistently. Surprising behavior erodes trust.
2. **Migration Path**: Users migrating from mistune, markdown-it, or other parsers expect CommonMark semantics.
3. **Edge Cases in Production**: Real-world documentation hits edge cases. Spec compliance prevents subtle bugs.
4. **Competitive Positioning**: Patitas competes with battle-tested parsers. Compliance is table stakes.

### Current State

Patitas has 102 CommonMark-focused tests with a **91% pass rate** on existing tests. However, coverage breadth against the full 652-example CommonMark spec is incomplete.

**Test Suite Results** (as of 2026-01-01):
- ✅ **93 passed**
- ❌ **7 failed** (assertion style issues, not functionality)
- ⏭️ **2 skipped** (setext headings)
- ⚠️ **2 xfail** (known issues with failing tests)

| Category | Tests | Pass Rate | Notes |
|----------|-------|-----------|-------|
| ATX Headings | 11 | 55%* | *5 failures are assertion issues, not bugs |
| Setext Headings | 2 | 0% | Skipped - not implemented |
| Thematic Breaks | 13 | 100% | ✅ Complete |
| Fenced Code | 6 | 100% | ✅ Basic coverage complete |
| Block Quotes | 2 | 100% | ✅ Laziness works correctly |
| **Lists** | **30** | **93%** | 2 xfail for known issues |
| Paragraphs | 2 | 100% | ✅ Basic coverage |
| Blank Lines | 1 | 100% | ✅ Minimal |
| Code Spans | 3 | 100% | ✅ Basic coverage |
| Emphasis | 4 | 100% | ✅ Basic cases pass |
| Links | 3 | 100% | ✅ Inline links work |
| Images | 2 | 100% | ✅ Inline images work |
| Hard Breaks | 2 | 100% | ✅ Basic coverage |
| Backslash Escapes | 17 | 88% | 2 failures (quote chars) |
| **Total** | **102** | **91%** | Good foundation, gaps in breadth |

### Existing Infrastructure

The lexer already defines tokens for unimplemented features, reducing implementation complexity:

```python
# tokens.py - Infrastructure exists
SETEXT_HEADING_UNDERLINE = auto()  # === or --- (defined, not processed)
LINK_REFERENCE_DEF = auto()        # [label]: url "title" (defined, not processed)
```

This means implementation can focus on parser/renderer logic rather than lexer redesign.

## Known Compliance Issues

### Critical (Breaks Common Patterns)

#### Issue 1: Different List Markers Don't Create Separate Lists

**Status**: `xfail` in test suite (`test_commonmark.py:623`)  
**Spec Reference**: CommonMark 5.3

```markdown
- Item with dash

* Item with asterisk
```

**Expected**: Two separate `<ul>` elements  
**Actual**: Single merged `<ul>`  
**Impact**: High - common pattern in documentation

**Root Cause**: Parser doesn't track marker type when continuing lists.

**Fix Complexity**: Medium - requires parser state tracking

#### Issue 2: Deeply Nested Lists Trigger Code Block Detection

**Status**: `xfail` in test suite (`test_commonmark.py:475`)  
**Spec Reference**: CommonMark 5.2

```markdown
- Level 1
  - Level 2
    - Level 3  ← Treated as code block
```

**Expected**: Three nested `<ul>` elements  
**Actual**: Level 3 becomes `<pre><code>`  
**Impact**: High - nested documentation structures

**Root Cause**: Lexer detects 4+ spaces as indented code before considering list context.

**Fix Complexity**: High - requires context-aware lexer or two-pass approach

#### Issue 3: Ordered Lists Starting with 2+ May Incorrectly Interrupt Paragraphs

**Status**: Needs verification  
**Spec Reference**: CommonMark 5.3

```markdown
Some text
2. This should NOT be a list item
```

**Expected**: Single paragraph  
**Actual**: May render as paragraph + ordered list  
**Impact**: Medium - affects text with numbered references

**Root Cause**: Parser doesn't distinguish list interruption from list continuation.

**Fix Complexity**: Medium - requires interruption context tracking

### High Priority (Spec Compliance)

#### Issue 4: Setext Headings Not Implemented

**Status**: Skipped in test suite, token infrastructure exists  
**Spec Reference**: CommonMark 4.3

```markdown
Heading
=======

Subheading
----------
```

**Expected**: `<h1>` and `<h2>`  
**Actual**: Rendered as paragraphs  
**Impact**: Medium - some docs use this style

**Implementation Notes**:
- `SETEXT_HEADING_UNDERLINE` token already defined in `tokens.py`
- `nodes.py` already supports `style: Literal["atx", "setext"]`
- Requires lexer lookahead to detect underline pattern

**Fix Complexity**: Medium - leverage existing token, add lexer lookahead

#### Issue 5: Reference Links Not Implemented

**Status**: Token infrastructure exists, parser doesn't process  
**Spec Reference**: CommonMark 4.7, 6.5

```markdown
[link text][ref]

[ref]: https://example.com
```

**Expected**: Rendered link  
**Actual**: Literal text `[link text][ref]`  
**Impact**: High - common in large documentation

**Implementation Notes**:
- `LINK_REFERENCE_DEF` token already defined in `tokens.py`
- Requires definition collection pass before inline parsing
- Must support full, collapsed, and shortcut reference styles

**Fix Complexity**: High - requires two-pass parsing or lazy definition collection

### Medium Priority (Edge Cases)

#### Issue 6: Link Titles with Parentheses

**Spec Reference**: CommonMark 6.5

```markdown
[link](url "title (with parens)")
```

**Fix Complexity**: Low - parser delimiter matching

#### Issue 7: Emphasis Delimiter Rules

**Spec Reference**: CommonMark 6.4

Complex cases like `**foo*bar**` have specific behavior per spec.

**Fix Complexity**: Medium - delimiter stack algorithm refinement

#### Issue 8: Entity and Numeric Character References

**Spec Reference**: CommonMark 6.2

```markdown
&amp; &copy; &#65; &#x41;
```

**Fix Complexity**: Low - lexer token type + renderer mapping

#### Issue 9: Backslash Escape Edge Cases

**Status**: 2 failing tests for quote characters  
**Spec Reference**: CommonMark 6.1

```markdown
\"  ← Should render as literal "
\'  ← Should render as literal '
```

**Current**: Renders as HTML entities (`&quot;`, `&#x27;`)  
**Fix Complexity**: Low - renderer output adjustment

## Proposed Test Strategy

### Phase 1: CommonMark Spec Tests (Official Suite)

The CommonMark project provides an official test suite with 652 examples.

**Action**: Import and run `spec.txt` tests

```python
# tests/rendering/parsers/patitas/test_commonmark_spec.py
import json
from pathlib import Path

import pytest

from bengal.rendering.parsers.patitas import parse

SPEC_TESTS = json.loads(Path("commonmark-spec-0.31.json").read_text())

def normalize_html(html: str) -> str:
    """Normalize HTML for comparison (whitespace, attribute order)."""
    # Implementation details...
    return html.strip()

@pytest.mark.parametrize("example", SPEC_TESTS, ids=lambda x: f"example-{x['example']}")
def test_commonmark_spec(example):
    html = parse(example["markdown"])
    assert normalize_html(html) == normalize_html(example["html"])
```

**Expected Results**:
- Initial baseline: TBD after importing spec suite
- After Critical fixes: ~550/652 passing (~84%)
- Target: 630/652 passing (~97%)

### Phase 2: Targeted Compliance Tests

Expand existing test categories with spec-derived cases:

| Category | Current | Target | Priority |
|----------|---------|--------|----------|
| Lists | 30 | 60 | P0 |
| Links/Images | 5 | 30 | P0 |
| Emphasis | 4 | 25 | P1 |
| Block Quotes | 2 | 15 | P1 |
| Code Blocks | 9 | 20 | P2 |
| Headings | 13 | 25 | P2 |

### Phase 3: Regression Test Suite

Every bug fix must include:
1. Failing test demonstrating the bug
2. Fix implementation
3. Test passing

### Phase 4: Fuzz Testing

```python
from hypothesis import given, strategies as st

from bengal.rendering.parsers.patitas import parse

@given(st.text(min_size=1, max_size=1000))
def test_no_crashes(markdown):
    """Parser never crashes on any input."""
    try:
        parse(markdown)
    except Exception as e:
        # Only syntax errors are acceptable
        if not isinstance(e, (ValueError, SyntaxError)):
            raise
```

### Phase 5: Performance Regression Tests

```python
import pytest

from bengal.rendering.parsers.patitas import parse

@pytest.mark.benchmark
def test_list_performance(benchmark):
    """List parsing stays O(n)."""
    md = "- item\n" * 1000
    result = benchmark(parse, md)
    assert result  # Sanity check
```

## Implementation Roadmap

### Sprint 1: Foundation (2 weeks)

**Goal**: Import CommonMark spec suite, establish accurate baseline

- [ ] Download CommonMark 0.31.2 spec.json
- [ ] Create test infrastructure with HTML normalization
- [ ] Run full 652-example suite, document baseline pass rate
- [ ] Triage failures into Critical/High/Medium/Low
- [ ] Fix 7 assertion-style test failures in existing tests

**Exit Criteria**: Accurate baseline metrics, issues categorized by spec section

### Sprint 2: List Compliance (2 weeks)

**Goal**: Fix all list-related compliance issues

- [ ] Fix: Different markers create separate lists (Issue 1)
- [ ] Fix: Deeply nested lists context-aware indentation (Issue 2)
- [ ] Verify/Fix: Ordered list interruption rules (Issue 3)
- [ ] Add: List item with multiple blocks
- [ ] Add: List continuation after blank lines

**Exit Criteria**: All list spec tests passing (74 tests in sections 5.2, 5.3)

### Sprint 3: Links & References (2 weeks)

**Goal**: Implement reference links and images

- [ ] Implement: Link reference definitions (leverage existing token)
- [ ] Implement: Full reference links `[text][ref]`
- [ ] Implement: Collapsed reference links `[ref][]`
- [ ] Implement: Shortcut reference links `[ref]`
- [ ] Implement: Reference images
- [ ] Fix: Link title edge cases (Issue 6)

**Exit Criteria**: All link/image spec tests passing (138 tests in sections 4.7, 6.5, 6.6)

### Sprint 4: Block Elements (2 weeks)

**Goal**: Implement remaining block-level features

- [ ] Implement: Setext headings (leverage existing token)
- [ ] Fix: Block quote nesting edge cases
- [ ] Fix: Indented code in list context
- [ ] Add: HTML block types 1-7

**Exit Criteria**: All block spec tests passing

### Sprint 5: Inline Elements (2 weeks)

**Goal**: Fix inline-level compliance issues

- [ ] Fix: Complex emphasis delimiter cases (Issue 7)
- [ ] Fix: Backslash escape edge cases (Issue 9)
- [ ] Implement: Entity references (Issue 8)
- [ ] Implement: Autolinks (email, URL)
- [ ] Fix: Hard line break edge cases

**Exit Criteria**: All inline spec tests passing

### Sprint 6: Polish & Fuzz (1 week)

**Goal**: Harden parser, achieve target compliance

- [ ] Run fuzz tests, fix any crashes
- [ ] Performance regression tests
- [ ] Documentation of remaining intentional deviations
- [ ] Final compliance report

**Exit Criteria**: 97%+ spec compliance, no crashes on fuzz tests

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Existing Test Pass Rate | 91% | 100% | test_commonmark.py |
| CommonMark Spec Pass Rate | TBD | 97% | spec.json (652 examples) |
| List Spec Tests | ~60% est. | 100% | sections 5.2, 5.3 (74 tests) |
| Link Spec Tests | ~30% est. | 100% | sections 4.7, 6.5 (116 tests) |
| Fuzz Test Coverage | 0 | 1000+ cases | hypothesis tests |
| Regression Tests | N/A | 100% of bugs | PR requirement |
| Performance Regression | N/A | <5% variance | benchmark suite |

## Competitive Analysis

| Parser | CommonMark Compliance | Performance | Thread-Safe |
|--------|----------------------|-------------|-------------|
| **Patitas (current)** | ~70% est. | O(n) guaranteed | ✅ |
| **Patitas (target)** | 97% | O(n) guaranteed | ✅ |
| mistune 3.x | ~95% | O(n) typical | ❌ |
| markdown-it-py | ~99% | O(n) typical | ❌ |
| commonmark.py | 100% | O(n²) worst | ❌ |
| cmark (C) | 100% | O(n) guaranteed | ✅ |

**Patitas differentiators**:
1. Pure Python with free-threading support (3.14t)
2. Zero regex in hot path (ReDoS-immune)
3. Typed AST with frozen dataclasses
4. StringBuilder O(n) rendering
5. Integrated directive system (MyST-compatible)
6. Designed for documentation sites (Bengal integration)

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Reference links require two-pass | Performance regression | High | Lazy definition collection, benchmark before/after |
| Setext headings need lookahead | Complexity increase | Medium | Limited lookahead buffer (2 lines max) |
| Context-aware lexer for lists | Architecture change | Medium | Lexer mode stack (already have `LexerMode` enum) |
| Breaking changes during fixes | User disruption | Medium | Deprecation warnings, changelog, migration guide |
| Spec suite reveals more issues | Timeline slip | Medium | Buffer in Sprint 6, prioritize by impact |

## Appendix A: CommonMark Spec Sections

| Section | Title | Tests | Priority | Notes |
|---------|-------|-------|----------|-------|
| 2.1 | Characters and lines | 0 | P2 | |
| 2.2 | Tabs | 11 | P2 | |
| 2.3 | Insecure characters | 1 | P3 | |
| 3 | Blocks and inlines | 0 | N/A | Overview |
| 4.1 | Thematic breaks | 19 | P1 | ✅ Mostly working |
| 4.2 | ATX headings | 18 | P1 | ✅ Mostly working |
| 4.3 | Setext headings | 27 | P1 | ❌ Not implemented |
| 4.4 | Indented code blocks | 12 | P1 | ⚠️ Context issues |
| 4.5 | Fenced code blocks | 29 | P1 | ✅ Working |
| 4.6 | HTML blocks | 44 | P2 | |
| 4.7 | Link reference definitions | 27 | P0 | ❌ Not implemented |
| 4.8 | Paragraphs | 8 | P1 | ✅ Working |
| 4.9 | Blank lines | 1 | P2 | ✅ Working |
| 5.1 | Block quotes | 25 | P1 | ✅ Laziness works |
| 5.2 | List items | 48 | P0 | ⚠️ Nesting issues |
| 5.3 | Lists | 26 | P0 | ⚠️ Marker issues |
| 6.1 | Backslash escapes | 13 | P1 | ⚠️ Quote chars |
| 6.2 | Entity references | 12 | P2 | ❌ Not implemented |
| 6.3 | Code spans | 22 | P1 | ✅ Working |
| 6.4 | Emphasis | 131 | P1 | ⚠️ Edge cases |
| 6.5 | Links | 89 | P0 | ⚠️ No references |
| 6.6 | Images | 22 | P1 | ⚠️ No references |
| 6.7 | Autolinks | 19 | P2 | Plugin exists |
| 6.8 | Raw HTML | 21 | P2 | |
| 6.9 | Hard line breaks | 15 | P1 | ✅ Working |
| 6.10 | Soft line breaks | 2 | P2 | ✅ Working |
| 6.11 | Textual content | 3 | P2 | ✅ Working |

**Total**: 652 spec examples

## Appendix B: Test File Structure

```
tests/rendering/parsers/patitas/
├── test_commonmark_spec.py      # Official spec suite (652 tests) [NEW]
├── test_commonmark.py           # Categorized compliance tests (102 tests)
├── test_blocks.py               # Block-level edge cases
├── test_inline.py               # Inline-level edge cases
├── test_lexer.py                # Lexer unit tests
├── test_parser.py               # Parser unit tests
├── test_renderer.py             # Renderer unit tests
├── test_edge_cases.py           # Regression tests
├── test_performance.py          # Benchmark tests [NEW]
├── test_fuzz.py                 # Hypothesis fuzz tests [NEW]
└── conftest.py                  # Shared fixtures
```

## Appendix C: Known Working Features

Features verified as working correctly (2026-01-01):

- ✅ ATX headings (`# H1` through `###### H6`)
- ✅ Thematic breaks (`---`, `***`, `___`)
- ✅ Fenced code blocks (backtick and tilde)
- ✅ Block quotes (including lazy continuation)
- ✅ Bullet lists (-, *, +)
- ✅ Ordered lists (1. and 1) styles)
- ✅ List starting numbers (`start` attribute)
- ✅ Tight vs loose list detection
- ✅ Inline code spans
- ✅ Emphasis and strong (`*`, `_`, `**`, `__`)
- ✅ Inline links and images
- ✅ Hard line breaks (backslash)
- ✅ Soft line breaks
- ✅ Most backslash escapes

## References

- [CommonMark Spec 0.31.2](https://spec.commonmark.org/0.31.2/)
- [CommonMark Test Suite](https://github.com/commonmark/commonmark-spec)
- [GFM Spec](https://github.github.com/gfm/)
- [Patitas RFC](plan/drafted/rfc-patitas-markdown-parser.md)
