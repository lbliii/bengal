# RFC: Directive Package Test Maturity

**Status**: Draft  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/directives/`  
**Confidence**: 95% 🟢 (metrics verified via find/grep)  
**Priority**: P1 (High) — Core rendering feature with 11% test coverage  
**Estimated Effort**: 3-4 days (single dev) | 2 days (2 devs, parallelized)

---

## Executive Summary

The `bengal/directives/` package is the **most immature part of the Bengal codebase**. With 47 source files and only 4-5 test files (~11% test ratio), it represents a significant quality risk. Major directives like `admonitions`, `cards`, `literalinclude`, `gallery`, `glossary`, `steps`, `dropdown`, `embed`, `video`, and `navigation` have **zero dedicated unit tests**.

Additionally, the package has:
- **2 explicit TODO comments** in production code (`marimo.py`)
- **34 `# type: ignore` comments** across directive files
- **~60 `: Any` type annotations** indicating weak typing
- **1 missing import** (`MistuneBlockState` in `marimo.py:76`)

**Recommendation**: Add 25-30 test files covering all directives, fix incomplete implementations, and improve type safety.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Current State Evidence](#current-state-evidence)
3. [Gap Analysis by Directive](#gap-analysis-by-directive)
4. [Incomplete Implementations](#incomplete-implementations)
5. [Type Safety Issues](#type-safety-issues)
6. [Proposed Test Plan](#proposed-test-plan)
7. [Implementation Phases](#implementation-phases)
8. [Success Criteria](#success-criteria)
9. [Risks and Mitigations](#risks-and-mitigations)

---

## Problem Statement

### Why This Matters

Directives are a **core user-facing feature** of Bengal. Users write content like:

```markdown
:::{admonition} Warning
:class: warning
This is critical user content that must render correctly.
:::

:::{literalinclude} /path/to/code.py
:language: python
:lines: 1-20
:::

:::{cards}
:columns: 3
Card content...
:::
```

If directives fail, user content breaks silently or renders incorrectly. Without tests:
- **Regressions go undetected** during refactoring
- **Edge cases** are undiscovered
- **Breaking changes** in upstream Mistune are not caught
- **Documentation claims** cannot be verified

### Severity Assessment

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Source files | 47 | 47 | — |
| Test files | 4-5 | 30+ | **25+ missing** |
| Test ratio | 11% | 70%+ | **59% gap** |
| `: Any` usages | ~60 | <10 | **50+ to refine** |
| `# type: ignore` | 34 | <5 | **29 to fix** |
| TODO comments | 2 | 0 | **2 incomplete** |

---

## Current State Evidence

### Test Coverage Analysis

**Existing test files** (verified via `ls tests/unit/directives/`):

| Test File | What It Tests | LOC |
|-----------|---------------|-----|
| `test_code_tabs.py` | Code tabs directive | ~100 |
| `test_tabs_native.py` | Native tabs rendering | ~80 |
| `test_tokens.py` | Token processing | ~120 |
| `test_priority.py` | Directive priority ordering | ~60 |

**Total existing coverage**: 4 test files covering ~4 of 47 source files.

### Source Files Without Tests

**Evidence**: `find bengal/directives -name "*.py" | wc -l` → 47 files

| Category | Files | Impact | Tested |
|----------|-------|--------|--------|
| **Admonitions** | `admonitions.py` | 🔴 High — most common directive | ❌ |
| **Cards** | `cards/*.py` (4 files) | 🔴 High — complex grid layouts | ❌ |
| **Code Display** | `literalinclude.py`, `fenced.py` | 🔴 High — code blocks | ❌ |
| **Navigation** | `navigation.py` | 🔴 High — site navigation | ❌ |
| **Interactive** | `dropdown.py`, `tabs.py`, `steps.py` | 🟡 Medium | Partial |
| **Media** | `video.py`, `figure.py`, `gallery.py` | 🟡 Medium | ❌ |
| **Metadata** | `badge.py`, `versioning.py`, `glossary.py` | 🟡 Medium | ❌ |
| **Embed** | `embed.py` | 🟡 Medium — iframes | ❌ |
| **Experimental** | `marimo.py` | 🟢 Low — opt-in | Partial |
| **Infrastructure** | `base.py`, `registry.py`, `factory.py` | 🔴 High | ❌ |

---

## Gap Analysis by Directive

### Tier 1: Critical (Most Used, Zero Tests)

#### `admonitions.py` — UNTESTED ❌

**Usage**: Most common directive in documentation.

```markdown
:::{note}
This is a note.
:::

:::{warning}
This is critical.
:::
```

**Source**: `bengal/directives/admonitions.py` (~150 lines)

**What needs testing**:
- All admonition types (note, warning, danger, tip, etc.)
- Custom titles
- Nested content
- Class attribute handling
- Icon rendering

#### `cards/*.py` — UNTESTED ❌

**Usage**: Landing pages, feature grids, documentation cards.

```markdown
:::{cards}
:columns: 3

:::{card} Title
:link: /path
Content here
:::

:::
```

**Source**: `bengal/directives/cards/` (4 files, ~400 lines total)

**What needs testing**:
- `card.py`: Single card rendering
- `cards_grid.py`: Grid layout
- `child_cards.py`: Nested cards
- `utils.py`: Card utilities
- Link handling, icons, responsive columns

#### `literalinclude.py` — UNTESTED ❌

**Usage**: Including external code files.

```markdown
:::{literalinclude} /src/example.py
:language: python
:lines: 10-20
:emphasize-lines: 3,5
:::
```

**Source**: `bengal/directives/literalinclude.py` (~250 lines)

**What needs testing**:
- File resolution
- Line range extraction (`:lines:`)
- Line emphasis (`:emphasize-lines:`)
- Start/end markers (`:start-after:`, `:end-before:`)
- Language detection
- Error handling for missing files

#### `base.py` — UNTESTED ❌

**Usage**: Foundation for all directives.

**Source**: `bengal/directives/base.py` (568 lines)

**What needs testing**:
- Option parsing
- Argument validation
- Content extraction
- Error context creation
- Plugin registration

### Tier 2: High Impact (Complex Logic, Zero Tests)

| Directive | Lines | Key Features to Test |
|-----------|-------|---------------------|
| `dropdown.py` | ~120 | Expand/collapse, nested content |
| `steps.py` | ~150 | Step numbering, continuation |
| `gallery.py` | ~180 | Image grid, lightbox integration |
| `glossary.py` | ~200 | Term definitions, cross-references |
| `video.py` | ~150 | YouTube/Vimeo embeds, lazy loading |
| `embed.py` | ~180 | Generic iframes, security |
| `figure.py` | ~130 | Captions, alignment |
| `navigation.py` | ~160 | TOC generation |

### Tier 3: Infrastructure (Affects All Directives)

| File | Lines | Impact |
|------|-------|--------|
| `registry.py` | ~100 | Directive registration |
| `factory.py` | ~80 | Directive instantiation |
| `validator.py` | ~120 | Option validation |
| `options.py` | ~150 | Option parsing |
| `types.py` | ~80 | Type definitions |
| `contracts.py` | ~60 | Interface contracts |

---

## Incomplete Implementations

### `marimo.py` — Caching TODO

**Location**: `bengal/directives/marimo.py:140-144, 167-169`

```python
# TODO: Implement caching
# if use_cache and label:
#     cached = self._get_from_cache(label, code)
#     if cached:
#         return cached
```

**Impact**: Performance — without caching, Marimo cells re-execute on every build.

**Resolution**: Implement cache using `bengal.cache` infrastructure or remove caching option from public API until implemented.

### `marimo.py` — Missing Import

**Location**: `bengal/directives/marimo.py:76`

```python
def parse(self, block: Any, m: Any, state: MistuneBlockState) -> dict[str, Any]:
```

**Issue**: `MistuneBlockState` is not imported in this file.

**Resolution**: Add import or change to `Any` with a type comment explaining why.

---

## Type Safety Issues

### `# type: ignore` Distribution

**Evidence**: `grep -r "type: ignore" bengal/directives --include="*.py" | wc -l` → 34

| File | Count | Reason |
|------|-------|--------|
| `mistune/__init__.py` | 9 | Mistune API typing |
| `embed.py` | 6 | HTML sanitization |
| `video.py` | 4 | URL parsing |
| `navigation.py` | 4 | AST manipulation |
| `versioning.py` | 3 | Version comparison |
| Others | 8 | Various |

### `: Any` Distribution

**Evidence**: `grep -r ": Any" bengal/directives --include="*.py" | wc -l` → ~60

**Hotspots**:
- `base.py`: 2 (acceptable — Mistune API)
- `glossary.py`: 6 (needs TypedDict for term structure)
- `steps.py`: 3 (needs step item TypedDict)
- `marimo.py`: 3 (needs generator typing)
- `cards/*.py`: 13 (needs card option TypedDict)

---

## Proposed Test Plan

### Test Architecture

```
tests/unit/directives/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_base.py             # Base directive tests
├── test_registry.py         # Registration tests
├── test_factory.py          # Factory tests
├── test_options.py          # Option parsing tests
├── test_validator.py        # Validation tests
│
├── content/                 # Content directives
│   ├── test_admonitions.py
│   ├── test_dropdown.py
│   ├── test_steps.py
│   ├── test_checklist.py
│   └── test_container.py
│
├── cards/                   # Card directives
│   ├── test_card.py
│   ├── test_cards_grid.py
│   └── test_child_cards.py
│
├── code/                    # Code directives
│   ├── test_literalinclude.py
│   ├── test_fenced.py
│   └── test_terminal.py
│
├── media/                   # Media directives
│   ├── test_figure.py
│   ├── test_gallery.py
│   ├── test_video.py
│   └── test_embed.py
│
├── navigation/              # Navigation directives
│   ├── test_navigation.py
│   └── test_target.py
│
├── metadata/                # Metadata directives
│   ├── test_badge.py
│   ├── test_versioning.py
│   ├── test_glossary.py
│   └── test_term.py
│
└── experimental/            # Experimental directives
    └── test_marimo.py       # Expand existing
```

### Test Patterns

#### Pattern 1: Parse-and-Render Test

```python
"""Tests for admonitions directive."""
import pytest
from bengal.directives.admonitions import AdmonitionsDirective
from tests._testing.rendering import render_directive

class TestAdmonitions:
    """Test admonition rendering."""

    @pytest.mark.parametrize("admon_type", [
        "note", "warning", "danger", "tip", "important", "caution"
    ])
    def test_all_types_render(self, admon_type: str) -> None:
        """All admonition types render without error."""
        content = f"""
        :::{{admonition}} Test
        :class: {admon_type}
        Content here.
        :::
        """
        html = render_directive(content)
        assert f'class="admonition {admon_type}"' in html
        assert "Content here." in html

    def test_custom_title(self) -> None:
        """Custom title is rendered."""
        content = """
        :::{note} Custom Title
        Content.
        :::
        """
        html = render_directive(content)
        assert "Custom Title" in html

    def test_nested_content(self) -> None:
        """Nested markdown is processed."""
        content = """
        :::{warning}
        This has **bold** and `code`.
        :::
        """
        html = render_directive(content)
        assert "<strong>bold</strong>" in html
        assert "<code>code</code>" in html
```

#### Pattern 2: Option Validation Test

```python
"""Tests for literalinclude directive."""
import pytest
from pathlib import Path
from bengal.directives.literalinclude import LiteralincludeDirective

class TestLiteralincludeOptions:
    """Test option parsing and validation."""

    def test_lines_option_parses_range(self) -> None:
        """`:lines: 5-10` extracts correct range."""
        directive = LiteralincludeDirective()
        lines = directive._parse_lines_option("5-10")
        assert lines == (5, 10)

    def test_lines_option_single_line(self) -> None:
        """`:lines: 5` extracts single line."""
        directive = LiteralincludeDirective()
        lines = directive._parse_lines_option("5")
        assert lines == (5, 5)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Missing file raises descriptive error."""
        with pytest.raises(FileNotFoundError) as exc:
            render_literalinclude("/nonexistent.py")
        assert "nonexistent.py" in str(exc.value)
```

#### Pattern 3: Integration Test

```python
"""Integration tests for cards directive."""
import pytest
from bengal.core import Site
from tests._testing.sites import create_test_site

class TestCardsIntegration:
    """Test cards with full rendering pipeline."""

    def test_cards_grid_layout(self, tmp_site: Site) -> None:
        """Cards render in grid layout."""
        page = tmp_site.create_page("test.md", content="""
        :::{cards}
        :columns: 3

        :::{card} Card 1
        Content 1
        :::

        :::{card} Card 2
        Content 2
        :::

        :::
        """)
        html = tmp_site.render_page(page)

        assert 'class="cards-grid"' in html
        assert 'style="--columns: 3"' in html or 'columns-3' in html
        assert "Card 1" in html
        assert "Card 2" in html
```

---

## Implementation Phases

### Phase 1: Infrastructure (Day 1)

**Goal**: Test the directive foundation.

| Test File | Source File | Priority |
|-----------|-------------|----------|
| `test_base.py` | `base.py` | 🔴 Critical |
| `test_registry.py` | `registry.py` | 🔴 Critical |
| `test_factory.py` | `factory.py` | 🔴 Critical |
| `test_options.py` | `options.py` | 🔴 Critical |
| `test_validator.py` | `validator.py` | 🔴 Critical |

**Expected tests**: ~80-100  
**Expected coverage**: Foundation layer 80%+

### Phase 2: Tier 1 Directives (Day 2)

**Goal**: Test the most critical, most-used directives.

| Test File | Source File | Priority |
|-----------|-------------|----------|
| `test_admonitions.py` | `admonitions.py` | 🔴 Critical |
| `test_card.py` | `cards/card.py` | 🔴 Critical |
| `test_cards_grid.py` | `cards/cards_grid.py` | 🔴 Critical |
| `test_literalinclude.py` | `literalinclude.py` | 🔴 Critical |
| `test_fenced.py` | `fenced.py` | 🔴 Critical |

**Expected tests**: ~150-200  
**Expected coverage**: Core directives 70%+

### Phase 3: Tier 2 Directives (Day 3)

**Goal**: Test complex interactive directives.

| Test File | Source File | Priority |
|-----------|-------------|----------|
| `test_dropdown.py` | `dropdown.py` | 🟡 High |
| `test_steps.py` | `steps.py` | 🟡 High |
| `test_gallery.py` | `gallery.py` | 🟡 High |
| `test_glossary.py` | `glossary.py` | 🟡 High |
| `test_video.py` | `video.py` | 🟡 High |
| `test_embed.py` | `embed.py` | 🟡 High |
| `test_figure.py` | `figure.py` | 🟡 High |
| `test_navigation.py` | `navigation.py` | 🟡 High |

**Expected tests**: ~200-250  
**Expected coverage**: All major directives 60%+

### Phase 4: Cleanup & Type Fixes (Day 4)

**Goal**: Fix incomplete implementations and type issues.

| Task | Files | Effort |
|------|-------|--------|
| Implement marimo caching | `marimo.py` | 2h |
| Fix marimo import | `marimo.py` | 15min |
| Add TypedDict for card options | `cards/*.py` | 1h |
| Add TypedDict for step structure | `steps.py` | 30min |
| Add TypedDict for glossary terms | `glossary.py` | 30min |
| Reduce `# type: ignore` by 50% | Various | 2h |

**Expected outcome**:
- TODO count: 0
- `# type: ignore`: <15
- `: Any`: <30

---

## Success Criteria

### Phase 1 Complete When:

- [ ] 5 infrastructure test files created
- [ ] 80+ tests pass
- [ ] `base.py` coverage >80%
- [ ] `registry.py` coverage >90%

### Phase 2 Complete When:

- [ ] 5 Tier 1 directive test files created
- [ ] 230+ total tests pass
- [ ] `admonitions.py` coverage >70%
- [ ] `literalinclude.py` coverage >70%
- [ ] All card directives covered

### Phase 3 Complete When:

- [ ] 8 Tier 2 directive test files created
- [ ] 430+ total tests pass
- [ ] All user-facing directives have tests
- [ ] No directive has 0% coverage

### Phase 4 Complete When:

- [ ] Marimo caching implemented or option removed
- [ ] All type errors fixed (0 `# type: ignore` for directive logic)
- [ ] `: Any` count reduced by 50%
- [ ] All existing tests still pass

### Final State:

| Metric | Before | After |
|--------|--------|-------|
| Test files | 4-5 | 30+ |
| Test ratio | 11% | 70%+ |
| `: Any` usages | ~60 | <30 |
| `# type: ignore` | 34 | <15 |
| TODO comments | 2 | 0 |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tests reveal bugs | High | Low | Fix bugs — that's the point |
| Mistune API changes | Medium | Medium | Pin Mistune version, add API tests |
| Slow test suite | Low | Low | Use fixtures, avoid full renders |
| Type fixes break code | Low | Medium | Run full test suite after each change |

---

## Dependencies

### On Other RFCs

- **rfc-type-refinement-sweep.md**: Type improvements in directives should align with the broader type refinement effort.
- **rfc-test-coverage-gaps.md**: This RFC is a focused subset addressing the most critical gap.

### On External Packages

- **Mistune**: Directive parsing relies on Mistune's plugin API.
- **pytest**: Test infrastructure.
- **hypothesis**: Property-based tests for option parsing.

---

## References

- `bengal/directives/` — Source directory
- `tests/unit/directives/` — Existing test directory
- `tests/unit/rendering/test_marimo_directive.py` — Existing Marimo tests
- `plan/drafted/rfc-test-coverage-gaps.md` — Related coverage RFC
- `plan/drafted/rfc-type-refinement-sweep.md` — Related type RFC
