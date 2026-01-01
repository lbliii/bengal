# RFC: Patitas CommonMark Compliance & Test Coverage

**Status**: Draft  
**Author**: Bengal Team  
**Created**: 2026-01-01  
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

Patitas has ~100 CommonMark tests but significant gaps exist:

| Category | Tests | Coverage | Notes |
|----------|-------|----------|-------|
| ATX Headings | 11 | ~70% | Missing edge cases |
| Setext Headings | 0 | 0% | Not implemented |
| Thematic Breaks | 3 | ~60% | Basic coverage |
| Fenced Code | 6 | ~50% | Missing indentation rules |
| Block Quotes | 2 | ~30% | Missing nesting, laziness |
| **Lists** | **30** | **~60%** | Recently expanded, gaps remain |
| Paragraphs | 2 | ~40% | Missing interruption rules |
| Blank Lines | 1 | ~20% | Minimal |
| Code Spans | 3 | ~50% | Missing edge cases |
| Emphasis | 4 | ~40% | Missing complex delimiter rules |
| Links | 3 | ~30% | Missing reference links |
| Images | 2 | ~40% | Missing reference images |
| Hard Breaks | 1 | ~50% | Basic coverage |
| **Total** | ~68 | ~45% | Significant gaps |

## Known Compliance Issues

### Critical (Breaks Common Patterns)

#### Issue 1: Different List Markers Don't Create Separate Lists

**Status**: `xfail` in test suite  
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

**Status**: `xfail` in test suite  
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

#### Issue 3: Ordered Lists Starting with 2+ Cannot Interrupt Paragraphs

**Status**: `skip` in test suite  
**Spec Reference**: CommonMark 5.3

```markdown
Some text
2. This should NOT be a list item
```

**Expected**: Single paragraph  
**Actual**: Paragraph + ordered list  
**Impact**: Medium - affects text with numbered references

**Root Cause**: Parser doesn't distinguish list interruption from list continuation.

**Fix Complexity**: Medium - requires interruption context tracking

### High Priority (Spec Compliance)

#### Issue 4: Setext Headings Not Implemented

**Status**: Not implemented  
**Spec Reference**: CommonMark 4.3

```markdown
Heading
=======

Subheading
----------
```

**Expected**: `<h1>` and `<h2>`  
**Actual**: Paragraphs or thematic breaks  
**Impact**: Medium - some docs use this style

**Fix Complexity**: Medium - lexer needs to look ahead

#### Issue 5: Reference Links Not Implemented

**Status**: Not implemented  
**Spec Reference**: CommonMark 6.3

```markdown
[link text][ref]

[ref]: https://example.com
```

**Expected**: Rendered link  
**Actual**: Literal text  
**Impact**: High - common in large documentation

**Fix Complexity**: High - requires two-pass parsing or definition collection

#### Issue 6: Block Quote Laziness Not Implemented

**Status**: Not tested  
**Spec Reference**: CommonMark 5.1

```markdown
> Quote starts here
continues without >
still part of quote
```

**Expected**: All three lines in blockquote  
**Actual**: Only first line  
**Impact**: Medium - common lazy writing pattern

**Fix Complexity**: Medium - parser continuation logic

### Medium Priority (Edge Cases)

#### Issue 7: Link Titles with Parentheses

**Spec Reference**: CommonMark 6.3

```markdown
[link](url "title (with parens)")
```

**Fix Complexity**: Low - parser delimiter matching

#### Issue 8: Emphasis Delimiter Rules

**Spec Reference**: CommonMark 6.1-6.2

Complex cases like `**foo*bar**` have specific behavior.

**Fix Complexity**: Medium - delimiter stack algorithm refinement

#### Issue 9: Entity and Numeric Character References

**Spec Reference**: CommonMark 6.4

```markdown
&amp; &copy; &#65; &#x41;
```

**Fix Complexity**: Low - lexer token type + renderer mapping

## Proposed Test Strategy

### Phase 1: CommonMark Spec Tests (Official Suite)

The CommonMark project provides an official test suite with 652 examples.

**Action**: Import and run `spec.txt` tests

```python
# tests/rendering/parsers/patitas/test_commonmark_spec.py
import json
from pathlib import Path

SPEC_TESTS = json.loads(Path("commonmark-spec-0.31.json").read_text())

@pytest.mark.parametrize("example", SPEC_TESTS, ids=lambda x: f"example-{x['example']}")
def test_commonmark_spec(example):
    html = parse(example["markdown"])
    assert normalize_html(html) == normalize_html(example["html"])
```

**Expected Results**:
- Initial: ~400/652 passing (~61%)
- After Critical fixes: ~550/652 passing (~84%)
- Target: 630/652 passing (~97%)

### Phase 2: Targeted Compliance Tests

Expand existing test categories with spec-derived cases:

| Category | Current | Target | Priority |
|----------|---------|--------|----------|
| Lists | 30 | 60 | P0 |
| Emphasis | 4 | 25 | P1 |
| Links/Images | 5 | 30 | P1 |
| Block Quotes | 2 | 15 | P1 |
| Code Blocks | 9 | 20 | P2 |
| Headings | 11 | 20 | P2 |

### Phase 3: Regression Test Suite

Every bug fix must include:
1. Failing test demonstrating the bug
2. Fix implementation
3. Test passing

### Phase 4: Fuzz Testing

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=1000))
def test_no_crashes(markdown):
    """Parser never crashes on any input."""
    try:
        parse(markdown)
    except Exception as e:
        if not isinstance(e, MarkdownSyntaxError):
            raise
```

### Phase 5: Performance Regression Tests

```python
@pytest.mark.benchmark
def test_list_performance(benchmark):
    """List parsing stays O(n)."""
    md = "- item\n" * 1000
    result = benchmark(parse, md)
    assert result  # Sanity check
```

## Implementation Roadmap

### Sprint 1: Foundation (2 weeks)

**Goal**: Import CommonMark spec suite, establish baseline

- [ ] Download CommonMark 0.31 spec.txt and convert to JSON
- [ ] Create test infrastructure for spec tests
- [ ] Run full suite, document baseline pass rate
- [ ] Triage failures into Critical/High/Medium/Low

**Exit Criteria**: Baseline metrics established, issues categorized

### Sprint 2: List Compliance (2 weeks)

**Goal**: Fix all list-related compliance issues

- [ ] Fix: Different markers create separate lists
- [ ] Fix: Deeply nested lists (context-aware indentation)
- [ ] Fix: Ordered list interruption rules
- [ ] Add: List item with multiple blocks
- [ ] Add: List continuation after blank lines

**Exit Criteria**: All list spec tests passing

### Sprint 3: Links & References (2 weeks)

**Goal**: Implement reference links and images

- [ ] Implement: Link reference definitions
- [ ] Implement: Full reference links `[text][ref]`
- [ ] Implement: Collapsed reference links `[ref][]`
- [ ] Implement: Shortcut reference links `[ref]`
- [ ] Implement: Reference images

**Exit Criteria**: All link/image spec tests passing

### Sprint 4: Block Elements (2 weeks)

**Goal**: Fix block-level compliance issues

- [ ] Implement: Setext headings
- [ ] Fix: Block quote laziness
- [ ] Fix: Block quote nesting
- [ ] Fix: Indented code in list context
- [ ] Add: HTML block types 1-7

**Exit Criteria**: All block spec tests passing

### Sprint 5: Inline Elements (2 weeks)

**Goal**: Fix inline-level compliance issues

- [ ] Fix: Complex emphasis delimiter cases
- [ ] Fix: Link title parsing edge cases
- [ ] Implement: Entity references
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
| CommonMark Spec Pass Rate | ~45% | 97% | spec.txt tests |
| List Tests | 30 | 60 | test_commonmark.py |
| Fuzz Test Coverage | 0 | 1000 cases | hypothesis tests |
| Regression Tests | N/A | 100% of bugs | PR requirement |
| Performance Regression | N/A | <5% variance | benchmark suite |

## Competitive Analysis

| Parser | CommonMark Compliance | Performance | Thread-Safe |
|--------|----------------------|-------------|-------------|
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
5. Integrated directive system

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Reference links require two-pass | Performance regression | Lazy definition collection |
| Setext headings need lookahead | Complexity increase | Limited lookahead buffer |
| Context-aware lexer for lists | Architecture change | Lexer mode stack |
| Breaking changes during fixes | User disruption | Deprecation warnings, changelog |

## Appendix A: CommonMark Spec Sections

| Section | Title | Tests | Priority |
|---------|-------|-------|----------|
| 2.1 | Characters and lines | 0 | P2 |
| 2.2 | Tabs | 11 | P2 |
| 2.3 | Insecure characters | 1 | P3 |
| 3 | Blocks and inlines | 0 | N/A |
| 4.1 | Thematic breaks | 19 | P1 |
| 4.2 | ATX headings | 18 | P1 |
| 4.3 | Setext headings | 27 | P1 |
| 4.4 | Indented code blocks | 12 | P1 |
| 4.5 | Fenced code blocks | 29 | P1 |
| 4.6 | HTML blocks | 44 | P2 |
| 4.7 | Link reference definitions | 27 | P0 |
| 4.8 | Paragraphs | 8 | P1 |
| 4.9 | Blank lines | 1 | P2 |
| 5.1 | Block quotes | 25 | P1 |
| 5.2 | List items | 48 | P0 |
| 5.3 | Lists | 26 | P0 |
| 6.1 | Backslash escapes | 13 | P1 |
| 6.2 | Entity references | 12 | P2 |
| 6.3 | Code spans | 22 | P1 |
| 6.4 | Emphasis | 131 | P1 |
| 6.5 | Links | 89 | P0 |
| 6.6 | Images | 22 | P1 |
| 6.7 | Autolinks | 19 | P2 |
| 6.8 | Raw HTML | 21 | P2 |
| 6.9 | Hard line breaks | 15 | P1 |
| 6.10 | Soft line breaks | 2 | P2 |
| 6.11 | Textual content | 3 | P2 |

**Total**: 652 spec examples

## Appendix B: Test File Structure

```
tests/rendering/parsers/patitas/
├── test_commonmark_spec.py      # Official spec suite (652 tests)
├── test_commonmark.py           # Categorized compliance tests
├── test_blocks.py               # Block-level edge cases
├── test_inline.py               # Inline-level edge cases
├── test_lexer.py                # Lexer unit tests
├── test_parser.py               # Parser unit tests
├── test_renderer.py             # Renderer unit tests
├── test_edge_cases.py           # Regression tests
├── test_performance.py          # Benchmark tests
├── test_fuzz.py                 # Hypothesis fuzz tests
└── conftest.py                  # Shared fixtures
```

## References

- [CommonMark Spec 0.31](https://spec.commonmark.org/0.31.2/)
- [CommonMark Test Suite](https://github.com/commonmark/commonmark-spec)
- [GFM Spec](https://github.github.com/gfm/)
- [Patitas RFC](plan/drafted/rfc-patitas-markdown-parser.md)
