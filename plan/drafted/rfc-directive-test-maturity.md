# RFC: Directive Package Test Maturity

**Status**: Draft  
**Created**: 2025-12-24  
**Author**: AI Assistant  
**Subsystem**: `bengal/directives/`  
**Confidence**: 92% 🟢 (metrics verified via find/grep/wc)  
**Priority**: P2 (Medium) — Core rendering feature with partial test coverage  
**Estimated Effort**: 2-3 days (single dev) | 1.5 days (2 devs, parallelized)

---

## Executive Summary

The `bengal/directives/` package has **47 source files** and **mixed test coverage**. While many directives have dedicated tests in `tests/unit/rendering/`, the infrastructure layer (`base.py`, `registry.py`, `factory.py`, `options.py`, `validator.py`) lacks focused unit tests.

**Current state**:
- **15 directive test files** in `tests/unit/rendering/` (~5,968 LOC)
- **4 infrastructure test files** in `tests/unit/directives/` (~1,116 LOC)
- **2 TODO comments** in production code (`marimo.py`)
- **43 `# type: ignore` comments** (40 are intentional override suppressions)
- **~98 `: Any` type annotations** indicating opportunities for type refinement

**Key gaps**:
- Admonitions directive (most common) — no dedicated test file
- Dropdown, embed, video, figure, gallery directives — no dedicated tests
- Infrastructure layer (base, registry, factory, options, validator) — minimal testing

**Recommendation**: Add 10-12 targeted test files focusing on untested directives and infrastructure, then improve type safety.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Current State Evidence](#current-state-evidence)
3. [Coverage Analysis](#coverage-analysis)
4. [Gap Analysis by Directive](#gap-analysis-by-directive)
5. [Incomplete Implementations](#incomplete-implementations)
6. [Type Safety Analysis](#type-safety-analysis)
7. [Proposed Test Plan](#proposed-test-plan)
8. [Implementation Phases](#implementation-phases)
9. [Success Criteria](#success-criteria)
10. [Risks and Mitigations](#risks-and-mitigations)

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

If directives fail, user content breaks silently or renders incorrectly. Without comprehensive tests:
- **Regressions go undetected** during refactoring
- **Edge cases** are undiscovered
- **Breaking changes** in upstream Mistune are not caught
- **Documentation claims** cannot be verified

### Current Coverage Summary

| Location | Test Files | LOC | Focus |
|----------|------------|-----|-------|
| `tests/unit/rendering/test_*directive*.py` | 15 | ~5,968 | Directive behavior |
| `tests/unit/directives/` | 4 | ~1,116 | Infrastructure |
| **Total** | **19** | **~7,084** | — |

This is **better than initially assessed**, but significant gaps remain in specific directives and the infrastructure layer.

---

## Current State Evidence

### Existing Test Files

**`tests/unit/rendering/` — Directive Behavior Tests** (15 files, ~5,968 LOC):

| Test File | Directive(s) Covered | LOC |
|-----------|----------------------|-----|
| `test_cards_directive.py` | cards, card | ~913 |
| `test_literalinclude_directive.py` | literalinclude | ~527 |
| `test_navigation_directives.py` | breadcrumbs, prev-next, siblings | ~400+ |
| `test_steps_directive.py` | steps, step | ~300+ |
| `test_glossary_directive.py` | glossary, term | ~250+ |
| `test_marimo_directive.py` | marimo | ~200+ |
| `test_include_directive.py` | include | ~200+ |
| `test_checklist_directive.py` | checklist | ~150+ |
| `test_data_table_directive.py` | data-table | ~150+ |
| `test_button_directive.py` | button | ~150+ |
| `test_icon_directive.py` | icon | ~150+ |
| `test_target_directive.py` | target | ~100+ |
| `test_directive_registration.py` | registration system | ~200+ |
| `test_directive_registry.py` | registry | ~150+ |
| `test_directive_optimizations.py` | performance | ~100+ |

**`tests/unit/directives/` — Infrastructure Tests** (4 files, ~1,116 LOC):

| Test File | What It Tests | LOC |
|-----------|---------------|-----|
| `test_code_tabs.py` | Code tabs directive | ~400 |
| `test_tabs_native.py` | Native tabs rendering | ~300 |
| `test_tokens.py` | Token processing | ~250 |
| `test_priority.py` | Directive priority ordering | ~166 |

### Source Files (47 total)

**Evidence**: `find bengal/directives -name "*.py" | wc -l` → 47

**Breakdown by category**:

| Category | Files | Has Tests |
|----------|-------|-----------|
| **Infrastructure** | `base.py`, `registry.py`, `factory.py`, `options.py`, `validator.py`, `contracts.py`, `types.py`, `tokens.py`, `errors.py`, `cache.py`, `utils.py` | Partial |
| **Admonitions** | `admonitions.py` | ❌ |
| **Cards** | `cards/card.py`, `cards_grid.py`, `child_cards.py`, `utils.py` | ✅ |
| **Code** | `literalinclude.py`, `fenced.py`, `code_tabs.py`, `terminal.py` | ✅ Partial |
| **Navigation** | `navigation.py`, `target.py` | ✅ |
| **Interactive** | `dropdown.py`, `tabs.py`, `steps.py`, `checklist.py` | ✅ Partial |
| **Media** | `video.py`, `figure.py`, `gallery.py`, `embed.py` | ❌ |
| **Metadata** | `badge.py`, `versioning.py`, `glossary.py`, `term.py` | ✅ Partial |
| **Other** | `button.py`, `icon.py`, `include.py`, `container.py`, `rubric.py`, `list_table.py`, `data_table.py`, `example_label.py`, `build.py`, `marimo.py` | ✅ Partial |

---

## Coverage Analysis

### Directives WITH Dedicated Tests

| Directive | Test File | Coverage Level |
|-----------|-----------|----------------|
| cards/card | `test_cards_directive.py` | 🟢 Good (913 LOC) |
| literalinclude | `test_literalinclude_directive.py` | 🟢 Good (527 LOC) |
| navigation | `test_navigation_directives.py` | 🟢 Good |
| steps | `test_steps_directive.py` | 🟢 Good |
| glossary/term | `test_glossary_directive.py` | 🟢 Good |
| marimo | `test_marimo_directive.py` | 🟡 Moderate |
| include | `test_include_directive.py` | 🟡 Moderate |
| checklist | `test_checklist_directive.py` | 🟡 Moderate |
| data-table | `test_data_table_directive.py` | 🟡 Moderate |
| button | `test_button_directive.py` | 🟡 Moderate |
| icon | `test_icon_directive.py` | 🟡 Moderate |
| target | `test_target_directive.py` | 🟡 Moderate |
| code_tabs | `test_code_tabs.py` | 🟢 Good |
| tabs | `test_tabs_native.py` | 🟢 Good |

### Directives WITHOUT Dedicated Tests

| Directive | Source File | Lines | Impact | Priority |
|-----------|-------------|-------|--------|----------|
| **admonitions** | `admonitions.py` | ~200 | 🔴 High — most common directive | P1 |
| **dropdown** | `dropdown.py` | ~200 | 🟡 Medium — interactive content | P2 |
| **embed** | `embed.py` | ~1,100 | 🟡 Medium — 6 embed types | P2 |
| **video** | `video.py` | ~900 | 🟡 Medium — 4 video platforms | P2 |
| **gallery** | `gallery.py` | ~200 | 🟡 Medium — image grids | P2 |
| **figure** | `figure.py` | ~450 | 🟡 Medium — captions, alignment | P2 |
| **versioning** | `versioning.py` | ~400 | 🟢 Low — since/deprecated/changed | P3 |
| **badge** | `badge.py` | ~150 | 🟢 Low — decorative | P3 |
| **container** | `container.py` | ~150 | 🟢 Low — generic wrapper | P3 |
| **rubric** | `rubric.py` | ~100 | 🟢 Low — headings | P3 |
| **list_table** | `list_table.py` | ~200 | 🟢 Low — table variant | P3 |
| **terminal** | `terminal.py` | ~200 | 🟢 Low — asciinema | P3 |
| **example_label** | `example_label.py` | ~150 | 🟢 Low — cross-refs | P3 |
| **build** | `build.py` | ~150 | 🟢 Low — build-only content | P3 |

### Infrastructure WITHOUT Dedicated Tests

| File | Lines | Impact | Priority |
|------|-------|--------|----------|
| `base.py` | 568 | 🔴 High — foundation | P1 |
| `factory.py` | ~100 | 🔴 High — instantiation | P1 |
| `options.py` | ~200 | 🔴 High — option parsing | P1 |
| `validator.py` | ~200 | 🟡 Medium — validation | P2 |

**Note**: `registry.py` has partial coverage via `test_directive_registry.py`.

---

## Gap Analysis by Directive

### Tier 1: Critical (High Usage, Zero Tests)

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

**Source**: `bengal/directives/admonitions.py` (~200 lines)

**What needs testing**:
- All admonition types (note, warning, danger, tip, important, caution, attention, error, hint, seealso)
- Custom titles
- Nested content (bold, code, links)
- Class attribute handling
- Icon rendering
- Collapsible admonitions (if supported)

#### `base.py` — UNTESTED ❌

**Usage**: Foundation for all directives.

**Source**: `bengal/directives/base.py` (568 lines)

**What needs testing**:
- Option parsing
- Argument validation
- Content extraction
- Error context creation
- Plugin registration hooks
- Default value handling

### Tier 2: High Impact (Complex, Zero Tests)

| Directive | Lines | Key Features to Test |
|-----------|-------|---------------------|
| `dropdown.py` | ~200 | Expand/collapse, nested content, open-by-default |
| `embed.py` | ~1,100 | Gist, CodePen, CodeSandbox, StackBlitz, Spotify, SoundCloud |
| `video.py` | ~900 | YouTube, Vimeo, self-hosted, TikTok |
| `gallery.py` | ~200 | Image grid, lightbox integration |
| `figure.py` | ~450 | Captions, alignment, sizing |

### Tier 3: Lower Priority (Less Used)

| Directive | Lines | Key Features to Test |
|-----------|-------|---------------------|
| `versioning.py` | ~400 | Since, deprecated, changed annotations |
| `badge.py` | ~150 | Badge styles, links |
| `container.py` | ~150 | Generic div wrapper |
| `terminal.py` | ~200 | Asciinema player |
| `list_table.py` | ~200 | Alternative table syntax |

---

## Incomplete Implementations

### `marimo.py` — Caching TODO

**Location**: `bengal/directives/marimo.py:142, 169`

```python
# TODO: Implement caching
# if use_cache and label:
#     cached = self._get_from_cache(label, code)
#     if cached:
#         return cached

# TODO: Store in cache
```

**Impact**: Performance — without caching, Marimo cells re-execute on every build.

**Resolution Options**:
1. Implement cache using `bengal.cache` infrastructure
2. Remove caching option from public API until implemented
3. Document as "planned feature"

---

## Type Safety Analysis

### `# type: ignore` Distribution (43 total)

**Evidence**: `grep -r "type: ignore" bengal/directives --include="*.py" | wc -l` → 43

**Breakdown by type**:

| Type | Count | Reason | Action |
|------|-------|--------|--------|
| `# type: ignore[override]` | 40 | Method signature narrowing (intentional) | Keep — valid pattern |
| `# type: ignore[attr-defined]` | 3 | State attribute access in `include.py` | Fix — add proper typing |

**The `# type: ignore[override]` Pattern**:

This pattern appears in every directive subclass:

```python
def render(
    self,
    options: CardOptions,  # type: ignore[override]
) -> str:
```

This is **intentional**: Python's type system doesn't support covariant parameter types, so subclasses narrowing `BaseOptions` to `CardOptions` require the suppression. This is a known limitation, not a code smell.

**Action items**:
- Keep the 40 `[override]` suppressions
- Fix the 3 `[attr-defined]` in `include.py` by adding type stubs or proper state typing

### `: Any` Distribution (~98 total)

**Evidence**: `grep -r ": Any" bengal/directives --include="*.py"` → 98 matches across 36 files

**Hotspots**:

| File | Count | Recommendation |
|------|-------|----------------|
| `cards/utils.py` | 6 | Add `CardData` TypedDict |
| `glossary.py` | 6 | Add `GlossaryTerm` TypedDict |
| `steps.py` | 6 | Add `StepItem` TypedDict |
| `versioning.py` | 6 | Add `VersionInfo` TypedDict |
| `data_table.py` | 5 | Add `TableRow` TypedDict |
| `build.py` | 4 | Add `BuildContext` TypedDict |
| `code_tabs.py` | 4 | Add `TabInfo` TypedDict |
| `tabs.py` | 4 | Already uses options; review |
| `figure.py` | 4 | Add `FigureData` TypedDict |

**Target**: Reduce from ~98 to <50 by adding TypedDicts for common structures.

---

## Proposed Test Plan

### Test Architecture

```
tests/unit/directives/
├── __init__.py
├── conftest.py                  # Shared fixtures (existing)
├── test_code_tabs.py            # ✅ Existing
├── test_priority.py             # ✅ Existing
├── test_tabs_native.py          # ✅ Existing
├── test_tokens.py               # ✅ Existing
│
├── infrastructure/              # NEW
│   ├── test_base.py             # Base directive class
│   ├── test_factory.py          # Directive instantiation
│   └── test_options.py          # Option parsing
│
└── content/                     # NEW
    └── test_admonitions.py      # Admonition rendering

tests/unit/rendering/
├── test_dropdown_directive.py   # NEW
├── test_embed_directive.py      # NEW
├── test_video_directive.py      # NEW
├── test_gallery_directive.py    # NEW
├── test_figure_directive.py     # NEW
├── ... (existing files)         # ✅ Keep
```

### Test Patterns

#### Pattern 1: Parse-and-Render Test

```python
"""Tests for admonitions directive."""
import pytest
from tests._testing.rendering import render_directive

class TestAdmonitions:
    """Test admonition rendering."""

    @pytest.mark.parametrize("admon_type", [
        "note", "warning", "danger", "tip", "important",
        "caution", "attention", "error", "hint", "seealso"
    ])
    def test_all_types_render(self, parser, admon_type: str) -> None:
        """All admonition types render without error."""
        content = f"""
        :::{{admonition}} Test
        :class: {admon_type}
        Content here.
        :::
        """
        html = parser.parse(content, {})
        assert f'class="admonition {admon_type}"' in html or admon_type in html
        assert "Content here." in html

    def test_custom_title(self, parser) -> None:
        """Custom title is rendered."""
        content = """
        :::{note} Custom Title
        Content.
        :::
        """
        html = parser.parse(content, {})
        assert "Custom Title" in html

    def test_nested_markdown(self, parser) -> None:
        """Nested markdown is processed."""
        content = """
        :::{warning}
        This has **bold** and `code`.
        :::
        """
        html = parser.parse(content, {})
        assert "<strong>bold</strong>" in html or "<b>bold</b>" in html
        assert "<code>code</code>" in html
```

#### Pattern 2: Option Validation Test

```python
"""Tests for base directive option handling."""
import pytest
from bengal.directives.base import BaseDirective

class TestBaseDirectiveOptions:
    """Test option parsing and validation."""

    def test_boolean_option_true(self) -> None:
        """Boolean options parse 'true' correctly."""
        result = BaseDirective._parse_boolean_option("true")
        assert result is True

    def test_boolean_option_false(self) -> None:
        """Boolean options parse 'false' correctly."""
        result = BaseDirective._parse_boolean_option("false")
        assert result is False

    def test_missing_required_option_raises(self) -> None:
        """Missing required option raises descriptive error."""
        with pytest.raises(ValueError) as exc:
            BaseDirective._validate_required_options({}, ["required_key"])
        assert "required_key" in str(exc.value)
```

---

## Implementation Phases

### Phase 1: Infrastructure (Day 1)

**Goal**: Test the directive foundation.

| Test File | Source File | Priority | Est. Tests |
|-----------|-------------|----------|------------|
| `test_base.py` | `base.py` | 🔴 Critical | ~30 |
| `test_factory.py` | `factory.py` | 🔴 Critical | ~15 |
| `test_options.py` | `options.py` | 🔴 Critical | ~25 |

**Expected outcome**: Infrastructure layer 80%+ coverage

### Phase 2: Critical Directives (Day 1-2)

**Goal**: Test the highest-impact untested directives.

| Test File | Source File | Priority | Est. Tests |
|-----------|-------------|----------|------------|
| `test_admonitions.py` | `admonitions.py` | 🔴 Critical | ~40 |
| `test_dropdown_directive.py` | `dropdown.py` | 🟡 High | ~20 |

**Expected outcome**: Core user-facing directives covered

### Phase 3: Media & Embed (Day 2-3)

**Goal**: Test media and embed directives.

| Test File | Source File | Priority | Est. Tests |
|-----------|-------------|----------|------------|
| `test_embed_directive.py` | `embed.py` | 🟡 High | ~50 |
| `test_video_directive.py` | `video.py` | 🟡 High | ~40 |
| `test_figure_directive.py` | `figure.py` | 🟡 High | ~25 |
| `test_gallery_directive.py` | `gallery.py` | 🟡 Medium | ~20 |

**Expected outcome**: All media directives covered

### Phase 4: Type Fixes (Day 3)

**Goal**: Improve type safety.

| Task | Files | Effort |
|------|-------|--------|
| Fix `include.py` type ignores | `include.py` | 30min |
| Add `CardData` TypedDict | `cards/utils.py` | 30min |
| Add `GlossaryTerm` TypedDict | `glossary.py` | 30min |
| Add `StepItem` TypedDict | `steps.py` | 30min |
| Implement marimo caching OR remove option | `marimo.py` | 2h |

**Expected outcome**:
- TODO count: 0 (or documented as planned feature)
- `# type: ignore`: 40 (all intentional overrides)
- `: Any`: <70

---

## Success Criteria

### Phase 1-2 Complete When:

- [ ] 3 infrastructure test files created
- [ ] `test_admonitions.py` created with 30+ tests
- [ ] `base.py` coverage >70%
- [ ] All admonition types verified

### Phase 3 Complete When:

- [ ] 4 media/embed test files created
- [ ] 150+ new tests pass
- [ ] All embed types (Gist, CodePen, etc.) have at least 1 test
- [ ] All video types (YouTube, Vimeo, etc.) have at least 1 test

### Phase 4 Complete When:

- [ ] Marimo caching implemented or option documented as planned
- [ ] `include.py` type ignores fixed
- [ ] At least 3 TypedDicts added
- [ ] All existing tests still pass

### Final State:

| Metric | Before | After |
|--------|--------|-------|
| Directive test files | 19 | 27+ |
| Test LOC | ~7,084 | ~9,000+ |
| `: Any` usages | ~98 | <70 |
| `# type: ignore[attr-defined]` | 3 | 0 |
| TODO comments | 2 | 0 |
| Untested critical directives | 1 (admonitions) | 0 |

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tests reveal bugs | High | Low | Fix bugs — that's the point |
| Mistune API changes | Medium | Medium | Pin Mistune version, add API tests |
| Slow test suite | Low | Low | Use fixtures, avoid full renders when possible |
| Type fixes break code | Low | Medium | Run full test suite after each change |

---

## Dependencies

### On Other RFCs

- **rfc-type-refinement-sweep.md**: Type improvements should align with the broader type refinement effort.
- **rfc-test-coverage-gaps.md**: This RFC addresses a specific subset of the overall coverage gap.

### On External Packages

- **Mistune**: Directive parsing relies on Mistune's plugin API.
- **pytest**: Test infrastructure.
- **hypothesis**: Optional — property-based tests for option parsing.

---

## References

- `bengal/directives/` — Source directory (47 files)
- `tests/unit/directives/` — Infrastructure tests (4 files, ~1,116 LOC)
- `tests/unit/rendering/test_*directive*.py` — Behavior tests (15 files, ~5,968 LOC)
- `plan/drafted/rfc-test-coverage-gaps.md` — Related coverage RFC
- `plan/drafted/rfc-type-refinement-sweep.md` — Related type RFC
