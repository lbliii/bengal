# RFC: Rosettes Test Gauntlet

| Field | Value |
|-------|-------|
| **RFC ID** | RFC-0006 |
| **Title** | Rosettes Comprehensive Test Gauntlet |
| **Status** | Draft |
| **Created** | 2025-12-27 |
| **Author** | Bengal Core Team |
| **Depends On** | RFC-0002 (Rosettes Syntax Highlighter) |

---

## Executive Summary

| Aspect | Details |
|--------|---------|
| **What** | Build a comprehensive test suite ("Gauntlet") for Rosettes syntax highlighter |
| **Why** | Current coverage is ~5% — only 1 test file with 158 lines for 54 lexers + formatter + themes |
| **Effort** | 2-3 weeks |
| **Risk** | Low — additive testing, no production changes |
| **Priority** | High — critical for reliability before 1.0 release |
| **Lexer Count** | 54 lexers (including Kida, Bengal's native template engine) |
| **Target Coverage** | 80%+ for `bengal.rendering.rosettes` with CI enforcement |

**Coverage Gap Analysis:**

| Component | Current | Target | Gap |
|-----------|---------|--------|-----|
| 54 Language Lexers | 0 tests | 540+ tests | ❌ Critical |
| Token Accuracy | 0 tests | 200+ tests | ❌ Critical |
| Edge Cases | 0 tests | 300+ tests | ❌ High |
| ReDoS Prevention | 0 tests | 50+ tests | ❌ High |
| Thread Safety | 0 tests | 20+ tests | ❌ High |
| HTML Formatter | ~10 tests | 50+ tests | ⚠️ Medium |
| Themes/Palettes | 0 tests | 30+ tests | ⚠️ Medium |
| Registry/Aliases | ~5 tests | 30+ tests | ⚠️ Medium |
| Parallel API | 0 tests | 15+ tests | ⚠️ Medium |

---

## Motivation

### Current State: Dangerously Undertested

The entire Rosettes test suite consists of:

```
tests/unit/rendering/highlighting/test_rosettes_backend.py  (158 lines)
```

This file tests:
- ✅ Backend name property
- ✅ 5 languages are "supported" (boolean check only)
- ✅ Unknown languages return `False`
- ✅ `highlight()` returns HTML with CSS classes
- ✅ HTML escaping (basic check)
- ✅ Line highlighting (3 tests)
- ✅ Empty/whitespace handling

**What's NOT tested:**
- ❌ All 50 individual lexers produce correct tokens
- ❌ Token types are semantically correct for each language construct
- ❌ Edge cases (nested comments, unterminated strings, unicode, escape sequences)
- ❌ ReDoS/pathological input timing
- ❌ Thread safety under concurrent access
- ❌ Formatter output correctness
- ❌ Theme loading and CSS generation
- ❌ Language alias resolution
- ❌ Parallel API (`highlight_many`, `tokenize_many`)
- ❌ Performance regression detection

### Why This Matters

1. **Correctness**: Users rely on accurate syntax highlighting for documentation
2. **Security**: ReDoS vulnerabilities can cause DoS (see Pygments CVEs)
3. **Free-Threading**: Python 3.14t requires thread-safe components
4. **Maintainability**: Changes to lexers have no regression detection
5. **Confidence**: Cannot safely refactor or optimize without tests

### Relationship to Existing Tests

The existing test file `tests/unit/rendering/highlighting/test_rosettes_backend.py` tests only the **backend wrapper** (`RosettesBackend` class), not the lexers themselves:

| Current Test | What It Tests | What's Missing |
|--------------|--------------|----------------|
| `test_name_property` | Backend name is "rosettes" | N/A |
| `test_supports_language_known` | 5 languages return `True` | Token accuracy |
| `test_highlight_produces_html` | HTML output exists | Correct token types |
| `test_hl_lines_*` | Line highlighting wrapper | Lexer internals |

**Migration Plan:**
- **Keep** `test_rosettes_backend.py` for backend integration tests
- **Create** new `tests/unit/rendering/rosettes/` for lexer-specific tests
- **No duplication**: Backend tests remain high-level; new tests target lexer accuracy

---

## Test Categories

### Category 1: Lexer Accuracy Tests (Priority: Critical)

**Scope**: Verify each of 54 lexers produces correct tokens for language constructs.

**Approach**: Fixture-based testing with golden outputs.

#### Fixture Generation Strategy

To reduce maintenance burden and ensure accuracy:

1. **Canonical Reference Sources**:
   - Use tree-sitter grammars as ground truth for token boundaries
   - Use Pygments output as comparison baseline (when available)
   - Manual curation for Kida (Bengal-specific, no external reference)

2. **Fixture Update Process**:
   ```bash
   # Regenerate fixtures after lexer changes
   python scripts/regenerate_fixtures.py --lexer python --diff

   # Review diffs, approve intentional changes
   python scripts/regenerate_fixtures.py --lexer python --approve
   ```

3. **Fuzzy Matching for Edge Cases**:
   - Allow token boundary tolerance (±1 char) for ambiguous constructs
   - Strict matching for keywords, operators, and strings

```
tests/unit/rendering/rosettes/
├── lexers/
│   ├── test_python_sm.py      # Python-specific constructs
│   ├── test_javascript_sm.py  # JavaScript-specific constructs
│   ├── test_rust_sm.py        # Rust-specific constructs
│   └── ...                    # 47 more lexer tests
├── fixtures/
│   ├── python/
│   │   ├── keywords.py        # Input file
│   │   ├── keywords.tokens    # Expected tokens (JSON)
│   │   ├── strings.py
│   │   ├── strings.tokens
│   │   └── ...
│   ├── javascript/
│   │   └── ...
│   └── ...
```

**Per-Language Test Matrix:**

| Construct | Python | JS | Rust | Go | ... |
|-----------|--------|-----|------|-----|-----|
| Keywords | ✓ | ✓ | ✓ | ✓ | ... |
| Strings (single) | ✓ | ✓ | ✓ | ✓ | ... |
| Strings (double) | ✓ | ✓ | ✓ | ✓ | ... |
| Strings (multi-line) | ✓ | ✓ | ✓ | ✓ | ... |
| Numbers (int) | ✓ | ✓ | ✓ | ✓ | ... |
| Numbers (float) | ✓ | ✓ | ✓ | ✓ | ... |
| Numbers (hex/bin/oct) | ✓ | ✓ | ✓ | ✓ | ... |
| Comments (line) | ✓ | ✓ | ✓ | ✓ | ... |
| Comments (block) | ✓ | ✓ | ✓ | ✓ | ... |
| Operators | ✓ | ✓ | ✓ | ✓ | ... |
| Punctuation | ✓ | ✓ | ✓ | ✓ | ... |
| Decorators | ✓ | ✗ | ✓ | ✗ | ... |
| Type annotations | ✓ | ✓ | ✓ | ✓ | ... |
| Escape sequences | ✓ | ✓ | ✓ | ✓ | ... |

**Estimated Tests**: 54 languages × 10 constructs avg = **540+ tests**

---

### Category 2: Edge Case Tests (Priority: High)

**Scope**: Stress-test lexers with edge cases that often cause bugs.

**Test Cases per Category:**

#### 2.1 Unterminated Constructs
```python
# Test: Unterminated string at EOF
code = '"hello'
# Lexer should NOT hang or crash; should emit STRING or ERROR token

# Test: Unterminated block comment
code = '/* hello'
# Lexer should handle gracefully
```

#### 2.2 Nested Constructs
```python
# Test: Nested strings (template literals, f-strings)
code = 'f"outer {f"inner"} outer"'

# Test: Nested comments (Rust, D, etc.)
code = '/* outer /* inner */ still outer */'

# Test: Comments inside strings (should NOT tokenize as comment)
code = '"not a # comment"'
```

#### 2.3 Unicode
```python
# Test: Unicode identifiers
code = 'привет = 42'
code = '变量 = "值"'

# Test: Unicode in strings
code = '"emoji: 🎉"'
code = '"cjk: 日本語"'

# Test: Unicode escape sequences
code = '"\\u0041"'  # Should be STRING_ESCAPE
```

#### 2.4 Escape Sequences
```python
# Test: All standard escapes
code = '"\\n\\t\\r\\\\\\"\\'"'

# Test: Invalid escapes
code = '"\\z"'  # Language-dependent handling

# Test: Raw strings
code = 'r"\\n is literal"'
```

#### 2.5 Boundary Conditions
```python
# Test: Empty input
code = ''

# Test: Single character
code = 'x'

# Test: Only whitespace
code = '   \n\t  '

# Test: Very long line (100K chars)
code = 'x' * 100_000

# Test: Many tokens
code = 'x ' * 50_000  # 100K tokens
```

**Estimated Tests**: 54 languages × 6 edge cases avg = **325+ tests**

---

### Category 3: ReDoS Prevention Tests (Priority: High)

**Scope**: Verify O(n) time guarantee with pathological inputs.

**Approach**: Timing-based tests with strict timeout.

```python
import time

def test_no_exponential_backtracking():
    """Pathological input should complete in O(n) time."""
    # Classic ReDoS pattern: repeated escapes
    pathological = 'f"' + '\\"' * 50 + 'x'

    start = time.perf_counter()
    tokens = list(lexer.tokenize(pathological))
    elapsed = time.perf_counter() - start

    # O(n) means ~linear scaling
    # For 100 chars, should complete in < 10ms
    assert elapsed < 0.1, f"Took {elapsed:.3f}s — possible ReDoS"
```

**Pathological Input Patterns:**

| Pattern | Description | Risk |
|---------|-------------|------|
| `"\"\"\"\"\"\"...x` | Repeated escapes | High |
| `(((((...)))))` | Deep nesting | Medium |
| `a+a+a+a+...` | Repeated operators | Medium |
| `/* /* /* ... */` | Nested comments | High |
| `'''...'''...'''` | Alternating quotes | Medium |

**Test Strategy:**

1. **Timing Tests**: Assert completion within O(n) bounds
2. **Scaling Tests**: Double input size, time should ~double (not explode)
3. **Stress Tests**: Large inputs (1MB) should complete in <1s

**Estimated Tests**: 54 languages × 1 ReDoS test = **54+ tests**

---

### Category 4: Thread Safety Tests (Priority: High)

**Scope**: Verify concurrent tokenization is safe.

```python
import concurrent.futures

def test_concurrent_tokenization():
    """Multiple threads tokenizing simultaneously should not interfere."""
    lexer = get_lexer("python")

    codes = [f"x{i} = {i}" for i in range(100)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(
            lambda c: list(lexer.tokenize(c)), codes
        ))

    # Verify each result is correct
    for i, tokens in enumerate(results):
        assert tokens[0].value == f"x{i}"

def test_parallel_api_correctness():
    """highlight_many() should return correct results in order."""
    items = [
        ("def foo(): pass", "python"),
        ("const x = 1;", "javascript"),
        ("fn main() {}", "rust"),
    ]

    results = highlight_many(items)

    assert len(results) == 3
    assert "foo" in results[0]
    assert "const" in results[1]
    assert "fn" in results[2]
```

**Test Cases:**

1. **Concurrent Tokenization**: Same lexer, multiple threads
2. **Concurrent Different Lexers**: Different languages in parallel
3. **Parallel API**: `highlight_many()`, `tokenize_many()` correctness
4. **Race Condition Detection**: Use `threading.Barrier` to maximize contention
5. **Registry Thread Safety**: Concurrent `get_lexer()` calls

**Estimated Tests**: **20+ tests**

---

### Category 5: Formatter Tests (Priority: Medium)

**Scope**: Verify HTML output correctness.

```python
def test_semantic_class_output():
    """Semantic mode should use .syntax-* classes."""
    formatter = HtmlFormatter(css_class_style="semantic")
    tokens = [Token(TokenType.KEYWORD, "def", 0, 0)]

    html = formatter.format_string(iter(tokens), FormatConfig())

    assert 'class="syntax-' in html

def test_pygments_class_output():
    """Pygments mode should use short classes like .k, .nf."""
    formatter = HtmlFormatter(css_class_style="pygments")
    tokens = [Token(TokenType.KEYWORD, "def", 0, 0)]

    html = formatter.format_string(iter(tokens), FormatConfig())

    assert 'class="k"' in html

def test_html_escaping():
    """HTML special chars must be escaped."""
    code = "<script>alert('xss')</script>"
    html = highlight(code, "html")

    assert "&lt;script&gt;" in html
    assert "<script>" not in html

def test_xss_prevention_comprehensive():
    """All XSS vectors must be neutralized in output."""
    xss_vectors = [
        ("<script>alert('xss')</script>", "html"),
        ("<img src=x onerror=alert(1)>", "html"),
        ("javascript:alert(1)", "javascript"),
        ("{{ __import__('os').system('rm -rf') }}", "jinja"),
        ("{% import os %}{{ os.system('ls') }}", "kida"),
        ("<svg onload=alert(1)>", "html"),
        ("'><script>alert(1)</script>", "html"),
    ]

    for code, lang in xss_vectors:
        html = highlight(code, lang)
        # No unescaped angle brackets except our own wrapper
        assert "<script>" not in html.replace("<pre", "").replace("<code", "")
        assert "onerror=" not in html
        assert "onload=" not in html

def test_line_highlighting():
    """hl_lines should add .hll class to specified lines."""
    code = "line1\nline2\nline3"
    html = highlight(code, "python", hl_lines={2})

    assert 'class="hll"' in html
    # Only line 2 should be highlighted
    assert html.count('class="hll"') == 1
```

**Test Cases:**

1. **CSS Class Modes**: semantic vs pygments
2. **HTML Escaping**: `<`, `>`, `&`, `"`, `'`
3. **Line Highlighting**: Single, multiple, out-of-range
4. **Line Numbers**: `show_linenos=True`
5. **Empty/Whitespace Handling**
6. **Wrapper Classes**: `rosettes` vs `highlight`
7. **Data Attributes**: `data-language`

**Estimated Tests**: **50+ tests**

---

### Category 6: Theme/Palette Tests (Priority: Medium)

**Scope**: Verify theme loading and CSS generation.

```python
def test_palette_loading():
    """Built-in palettes should load correctly."""
    palettes = ["bengal-tiger", "monokai", "dracula", "github"]

    for name in palettes:
        palette = get_palette(name)
        assert palette is not None
        assert hasattr(palette, "foreground")
        assert hasattr(palette, "background")

def test_role_mapping():
    """Token types should map to semantic roles."""
    for tt in TokenType:
        role = get_role(tt)
        assert isinstance(role, SyntaxRole)

def test_css_generation():
    """CSS should be generated for all roles."""
    palette = get_palette("bengal-tiger")
    css = palette.generate_css()

    assert ".syntax-keyword" in css or ".k" in css
    assert ".syntax-string" in css or ".s" in css
```

**Estimated Tests**: **30+ tests**

---

### Category 7: Registry Tests (Priority: Medium)

**Scope**: Verify language detection and alias handling.

```python
def test_language_aliases():
    """Common aliases should resolve correctly."""
    aliases = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "rb": "ruby",
        "yml": "yaml",
        "rs": "rust",
    }

    for alias, expected in aliases.items():
        lexer = get_lexer(alias)
        assert lexer.name == expected

def test_list_languages():
    """list_languages() should return all supported languages."""
    languages = list_languages()

    assert len(languages) >= 50
    assert "python" in languages
    assert "javascript" in languages

def test_unknown_language_error():
    """Unknown language should raise LookupError."""
    with pytest.raises(LookupError):
        get_lexer("nonexistent-language-xyz")
```

**Estimated Tests**: **30+ tests**

---

### Category 8: Performance Regression Tests (Priority: Medium)

**Scope**: Detect performance regressions in CI.

```python
import pytest

@pytest.mark.benchmark
def test_python_lexer_performance(benchmark):
    """Python lexer should tokenize ~1MB/s on standard hardware."""
    lexer = get_lexer("python")
    code = load_fixture("large_python_file.py")  # ~100KB

    result = benchmark(lambda: list(lexer.tokenize(code)))

    # Assert reasonable performance (adjust for CI hardware)
    assert benchmark.stats.mean < 0.5  # <500ms for 100KB
```

**Benchmarks:**

| Lexer | Input Size | Target Time |
|-------|-----------|-------------|
| Python | 100KB | <500ms |
| JavaScript | 100KB | <500ms |
| Rust | 100KB | <500ms |
| Synthetic | 1MB | <5s |

**Estimated Tests**: **20+ tests**

---

## Test Directory Structure

```
tests/unit/rendering/rosettes/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── test_types.py                  # Token, TokenType tests
├── test_registry.py               # get_lexer, list_languages, aliases
├── test_parallel.py               # highlight_many, tokenize_many
├── test_thread_safety.py          # Concurrent access tests
│
├── lexers/
│   ├── __init__.py
│   ├── conftest.py                # Lexer test helpers
│   ├── test_base_state_machine.py # StateMachineLexer base class
│   ├── test_python_sm.py          # Python lexer
│   ├── test_javascript_sm.py      # JavaScript lexer
│   ├── test_rust_sm.py            # Rust lexer
│   ├── test_go_sm.py              # Go lexer
│   ├── test_kida_sm.py            # Kida lexer (Bengal template engine)
│   └── ...                        # 45 more lexer tests
│
├── formatters/
│   ├── __init__.py
│   ├── test_html_formatter.py     # HTML output tests
│   └── test_escaping.py           # Security tests
│
├── themes/
│   ├── __init__.py
│   ├── test_palettes.py           # Palette loading
│   ├── test_roles.py              # Role mapping
│   └── test_css_generation.py     # CSS output
│
├── edge_cases/
│   ├── __init__.py
│   ├── test_unterminated.py       # Unterminated constructs
│   ├── test_unicode.py            # Unicode handling
│   ├── test_escapes.py            # Escape sequences
│   ├── test_nested.py             # Nested constructs
│   └── test_boundaries.py         # Boundary conditions
│
├── security/
│   ├── __init__.py
│   ├── test_redos.py              # ReDoS prevention (timing-based)
│   ├── test_xss.py                # XSS prevention in output
│   └── test_injection.py          # Template injection vectors (Kida, Jinja)
│
├── fixtures/
│   ├── python/
│   │   ├── keywords.py
│   │   ├── keywords.tokens
│   │   ├── strings.py
│   │   ├── strings.tokens
│   │   └── ...
│   ├── kida/
│   │   ├── expressions.kida
│   │   ├── expressions.tokens
│   │   ├── statements.kida
│   │   ├── statements.tokens
│   │   ├── pipeline.kida          # Kida-specific |>
│   │   └── ...
│   ├── javascript/
│   │   └── ...
│   └── ...
│
└── conftest.py                    # Shared pytest fixtures

# Supporting scripts (not in tests/)
scripts/
├── regenerate_fixtures.py         # Fixture regeneration with diff review
└── benchmark_lexers.py            # Performance baseline generator
```

---

## Implementation Plan

### Phase 1: Foundation (Week 1)

| Task | Effort | Output |
|------|--------|--------|
| Establish performance baselines | 2h | Current timing data for all 54 lexers |
| Create directory structure | 1h | Test skeleton |
| Build test fixtures framework | 4h | Fixture loader, token comparator, fixture regeneration script |
| Write Python lexer tests | 8h | Full coverage for Python |
| Write JavaScript lexer tests | 6h | Full coverage for JS |
| Write Rust lexer tests | 4h | Full coverage for Rust |
| Write Kida lexer tests | 4h | Full coverage for Bengal's template engine |

**Baseline Benchmark Command:**
```bash
# Run before any optimizations to establish targets
python -c "
from bengal.rendering.rosettes import list_languages, get_lexer
import time

for lang in sorted(list_languages()):
    lexer = get_lexer(lang)
    code = 'x = 1\n' * 10000  # 10K lines
    start = time.perf_counter()
    list(lexer.tokenize(code))
    elapsed = time.perf_counter() - start
    print(f'{lang}: {elapsed:.3f}s')
" | tee benchmarks/rosettes-baseline.txt
```

**Deliverables:**
- Performance baseline for all 54 lexers
- 4 fully-tested lexers (Python, JavaScript, Rust, Kida)
- Fixture framework for remaining lexers
- ~200 new tests

### Phase 2: Lexer Expansion (Week 2)

| Task | Effort | Output |
|------|--------|--------|
| Generate fixture templates | 4h | Starter fixtures for 50 languages |
| Write tests for 11 high-priority languages | 16h | Go, TypeScript, C, C++, Java, YAML, JSON, HTML, CSS, SQL, Bash |
| Write tests for 15 medium-priority languages | 12h | Ruby, PHP, Swift, Kotlin, Scala, etc. |
| Write tests for 24 low-priority languages | 8h | Basic coverage |

**Deliverables:**
- All 54 lexers have basic test coverage
- High-priority languages have comprehensive tests
- ~400 new tests

### Phase 3: Security & Edge Cases (Week 3)

| Task | Effort | Output |
|------|--------|--------|
| ReDoS prevention tests | 8h | Timing tests for all lexers |
| Edge case tests | 8h | Unicode, escapes, boundaries |
| Thread safety tests | 6h | Concurrent access tests |
| XSS prevention tests | 4h | HTML escaping validation |
| Performance regression tests | 6h | Benchmark suite |

**Deliverables:**
- Security test suite
- Edge case coverage
- Performance baselines
- ~150 new tests

### Phase 4: Formatter & Themes (Week 3)

| Task | Effort | Output |
|------|--------|--------|
| Formatter tests | 8h | HTML output validation |
| Theme tests | 4h | Palette loading, CSS generation |
| Registry tests | 4h | Alias resolution, error handling |

**Deliverables:**
- Complete formatter coverage
- Theme/palette tests
- Registry tests
- ~80 new tests

---

## Test Count Summary

| Category | Tests |
|----------|-------|
| Lexer Accuracy (54 languages) | 540+ |
| Edge Cases | 325+ |
| ReDoS Prevention | 54+ |
| Thread Safety | 20+ |
| Formatter | 50+ |
| XSS Prevention | 15+ |
| Themes/Palettes | 30+ |
| Registry | 30+ |
| Performance | 20+ |
| **Total** | **1084+** |

---

## Success Criteria

### Minimum Viable Gauntlet (MVP)

- [ ] All 54 lexers have at least 5 tests each
- [ ] ReDoS timing tests for all lexers
- [ ] Thread safety tests pass on 3.14t
- [ ] Formatter tests for both CSS modes
- [ ] XSS prevention tests for all injection vectors
- [ ] No test failures in CI

### Full Gauntlet

- [ ] 80%+ line coverage for `bengal.rendering.rosettes`
- [ ] All edge case categories covered
- [ ] Performance regression detection active
- [ ] Fuzz testing infrastructure (bonus)

### Regression Prevention (CI Gates)

To prevent coverage regression after initial implementation:

```toml
# Add to pyproject.toml [tool.pytest.ini_options]
[tool.coverage.run]
source = ["bengal/rendering/rosettes"]

[tool.coverage.report]
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
]
```

**CI Enforcement:**
```yaml
# .github/workflows/test.yml
- name: Test Rosettes with coverage
  run: |
    pytest tests/unit/rendering/rosettes/ \
      --cov=bengal.rendering.rosettes \
      --cov-fail-under=80 \
      --cov-report=term-missing
```

**PR Gate (required for lexer changes):**
- PRs modifying `bengal/rendering/rosettes/lexers/*.py` must include corresponding test updates
- Coverage for modified files must not decrease

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Fixture maintenance burden | Medium | Generate fixtures from canonical parsers; diff-based updates; regeneration script |
| False positive ReDoS tests | Low | Use generous timeouts (1s), track CI hardware, add `@pytest.mark.slow` |
| Flaky thread safety tests | Medium | Use barriers and deterministic ordering; run with `--forked` if needed |
| Large test count slows CI | Low | Parallelize with pytest-xdist; split lexer tests into separate jobs |
| Kida has no external reference | Medium | Manual curation; treat as ground truth; prioritize human review |
| Coverage regression after merge | High | Add `--cov-fail-under=80` gate; require test updates with lexer PRs |

---

## Appendix A: High-Priority Languages

Based on Bengal usage analytics and documentation importance:

| Priority | Language | Rationale |
|----------|----------|-----------|
| 1 | **Kida** | Bengal's native template engine — no external reference, critical |
| 2 | Python | Primary audience, most used in docs |
| 3 | JavaScript | Web ecosystem, high usage |
| 4 | TypeScript | Web ecosystem, growing usage |
| 5 | Rust | Performance-focused audience |
| 6 | Go | Cloud/DevOps documentation |
| 7 | YAML | Configuration files |
| 8 | JSON | Configuration, API responses |
| 9 | Bash | Scripts, CLI examples |
| 10 | HTML | Web documentation |
| 11 | CSS | Styling examples |
| 12 | SQL | Database documentation |
| 13 | Markdown | Meta (documenting docs) |
| 14 | Java | Enterprise documentation |
| 15 | C/C++ | Systems programming |
| 16 | Jinja | Template comparison (similar to Kida) |

---

## Appendix B: Fixture Format

```json
{
  "input": "def hello(): pass",
  "language": "python",
  "expected_tokens": [
    {"type": "kd", "value": "def"},
    {"type": "w", "value": " "},
    {"type": "nf", "value": "hello"},
    {"type": "p", "value": "("},
    {"type": "p", "value": ")"},
    {"type": "p", "value": ":"},
    {"type": "w", "value": " "},
    {"type": "k", "value": "pass"}
  ]
}
```

---

## Appendix C: ReDoS Test Template

```python
import time
import pytest
from bengal.rendering.rosettes import list_languages, get_lexer

@pytest.mark.slow
@pytest.mark.parametrize("language", list_languages())
def test_lexer_no_redos(language: str):
    """Lexer should complete in O(n) time for pathological input.

    All 54 lexers must pass this test to prevent ReDoS vulnerabilities.
    Uses 1s timeout to account for CI hardware variance.
    """
    lexer = get_lexer(language)

    # Pathological patterns (language-agnostic)
    patterns = [
        '"' + '\\"' * 100 + 'x',           # Repeated escapes
        '(' * 50 + 'x' + ')' * 50,         # Deep nesting
        '/* ' + '/* ' * 20 + 'x',          # Nested comments
        'a' + '+a' * 100,                   # Repeated operators
    ]

    for pattern in patterns:
        start = time.perf_counter()
        try:
            list(lexer.tokenize(pattern))
        except Exception:
            pass  # Error is OK, hang is not
        elapsed = time.perf_counter() - start

        # O(n) means linear time; generous 1s timeout for CI variance
        assert elapsed < 1.0, f"{language}: {pattern[:50]}... took {elapsed:.3f}s"


def test_lexer_linear_scaling():
    """Verify doubling input size approximately doubles time (not exponential)."""
    lexer = get_lexer("python")

    small = "x = 1\n" * 1000   # 1K lines
    large = "x = 1\n" * 2000   # 2K lines

    start = time.perf_counter()
    list(lexer.tokenize(small))
    small_time = time.perf_counter() - start

    start = time.perf_counter()
    list(lexer.tokenize(large))
    large_time = time.perf_counter() - start

    # Large should be ~2x small (with tolerance), not exponential
    ratio = large_time / small_time if small_time > 0 else float('inf')
    assert ratio < 4.0, f"Scaling ratio {ratio:.2f}x suggests non-linear time"
```

---

## Appendix D: Kida Lexer Test Strategy

Kida is Bengal's native template engine with no external reference parser. This requires special handling:

**Kida-Specific Constructs to Test:**

| Construct | Example | Token Types |
|-----------|---------|-------------|
| Comments | `{# comment #}` | `COMMENT_MULTILINE` |
| Expressions | `{{ variable }}` | `PUNCTUATION_MARKER`, `NAME_VARIABLE` |
| Statements | `{% if cond %}` | `PUNCTUATION_MARKER`, `KEYWORD` |
| Pipeline | `{{ x \|> filter }}` | `OPERATOR` (`\|>`), `NAME_FUNCTION` |
| Null-coalesce | `{{ x ?? default }}` | `OPERATOR` (`??`) |
| Unified endings | `{% end %}` | `KEYWORD` (not `endif`, `endfor`) |
| Let bindings | `{% let x = 1 %}` | `KEYWORD`, `NAME_VARIABLE` |
| Pattern matching | `{% match x %}{% case 1 %}` | `KEYWORD` pairs |
| Built-in filters | `{{ x \| slugify }}` | `NAME_FUNCTION` |
| Built-in tests | `{% if x is defined %}` | `NAME_BUILTIN` |

**Ground Truth Approach:**

Since Kida has no canonical external parser:
1. **Human-curated fixtures**: Manually verify token output for each construct
2. **Dual-review process**: Two developers must approve Kida fixture changes
3. **Documentation alignment**: Fixtures must match Kida syntax documentation
4. **Jinja2 compatibility tests**: Verify Jinja2 constructs tokenize correctly

```python
# tests/unit/rendering/rosettes/lexers/test_kida_sm.py

class TestKidaLexer:
    """Kida lexer tests — Bengal's native template engine."""

    def test_pipeline_operator(self):
        """Kida-specific |> pipeline operator."""
        code = "{{ value |> upper |> trim }}"
        tokens = list(get_lexer("kida").tokenize(code))

        operators = [t for t in tokens if t.value == "|>"]
        assert len(operators) == 2
        assert all(t.type == TokenType.OPERATOR for t in operators)

    def test_unified_end_keyword(self):
        """Kida uses 'end' instead of 'endif', 'endfor', etc."""
        code = "{% if x %}content{% end %}"
        tokens = list(get_lexer("kida").tokenize(code))

        keywords = [t for t in tokens if t.type == TokenType.KEYWORD]
        assert "if" in [t.value for t in keywords]
        assert "end" in [t.value for t in keywords]

    def test_null_coalescing(self):
        """Kida-specific ?? operator."""
        code = "{{ value ?? 'default' }}"
        tokens = list(get_lexer("kida").tokenize(code))

        null_coalesce = [t for t in tokens if t.value == "??"]
        assert len(null_coalesce) == 1
        assert null_coalesce[0].type == TokenType.OPERATOR
```

---

## References

- [RFC-0002: Rosettes Syntax Highlighter](rfc-rosettes-syntax-highlighter.md)
- [RFC-0004: ReDoS Prevention](rfc-rosettes-redos-prevention.md)
- [Pygments CVE History](https://cve.mitre.org/cgi-bin/cvekey.cgi?keyword=pygments)
- [Python 3.14t Free-Threading PEP 703](https://peps.python.org/pep-0703/)
