# RFC: Bengal Directive Migration to Patitas

| Field        | Value                                      |
|--------------|-------------------------------------------|
| **Status**   | In Progress (Phase B.1 Complete)           |
| **Author**   | Bengal Team                                |
| **Created**  | 2025-12-28                                 |
| **Updated**  | 2025-12-28                                 |
| **RFC**      | rfc-patitas-bengal-directive-migration     |
| **Depends**  | rfc-patitas-markdown-parser (Phase 2)      |
| **Blocks**   | rfc-patitas-roles-migration (glossary)     |

---

## Executive Summary

**Goal**: Migrate 55+ Bengal directives from mistune to Patitas for thread-safe Python 3.14t support.

| Metric | Current | Target |
|--------|---------|--------|
| **Phase A** | ✅ 17 directives done | 17/55 (31%) |
| **Phase A.1** | ✅ 43/43 parity tests | 100% HTML parity |
| **Phase B.1** | ✅ 3 cards directives done | 20/55 (36%) |
| **Remaining** | 35 directives | Weeks 5-9 |
| **Total LOC** | ~2,400 implemented | ~6,350 projected |
| **Risk Level** | Low | Verified by parity testing |

**Key Benefits**: Thread-safety, typed AST, no mistune dependency, identical HTML output.

**Next Action**: Implement Phase B.2 (code-tabs, tables, media) with same parity testing approach.

---

## Summary

Port all Bengal directives from mistune-based `BengalDirective` implementations to native Patitas `DirectiveHandler` implementations. This enables:

- **Thread-safe parsing** for Python 3.14t free-threading
- **Typed AST nodes** for better tooling and analysis
- **Removal of mistune dependency** for directive parsing
- **Identical HTML output** preserving all existing styling

---

## Current Status

### ✅ Phase A: Core Directives — COMPLETE

| Directive | LOC | Status | Notes |
|-----------|-----|--------|-------|
| Admonitions (10) | 216 | ✅ Done | Icons, Bengal HTML match |
| `dropdown` / `details` | 244 | ✅ Done | Full options, icons, colors |
| `tab-set` / `tab-item` | 465 | ✅ Done | Two render modes, sync, badges |
| `container` / `div` | 127 | ✅ Done | Generic wrapper |
| `steps` / `step` | 348 | ✅ Done | Contract validation, metadata |

**Total: 1,400 LOC implemented**

### ✅ Infrastructure — COMPLETE

| Component | LOC | Status | Notes |
|-----------|-----|--------|-------|
| `protocol.py` | 182 | ✅ Done | `DirectiveHandler` protocol |
| `options.py` | 253 | ✅ Done | Type coercion, 8 option classes |
| `contracts.py` | 285 | ✅ Done | 8 predefined contracts |
| `registry.py` | — | ✅ Done | Directive registration |
| `builtins/__init__.py` | 40 | ✅ Done | Exports all handlers |

### ✅ Phase A.1: Test Infrastructure — COMPLETE

| Component | Status | Notes |
|-----------|--------|-------|
| `conftest.py` | ✅ Done | HTML normalization, render fixtures, golden file support |
| `test_directive_parity.py` | ✅ Done | 43 parity tests, all passing |
| `test_directive_edge_cases.py` | ✅ Done | 79 edge cases, 74 passing |
| `golden_files/` | ✅ Done | Directory created, ready for golden file generation |

**Parity fixes applied**:
- Lexer: Block elements inside directives, code fence mode restoration
- Renderer: HTML quote escaping, trailing newlines, child render callback
- Handlers: Flag options, option key mapping, step numbering, tab selection

### ⚠️ Remaining Work

| Item | Status | Notes |
|------|--------|-------|
| Edge case fixes | ⚠️ 5 failures | Tables, task lists, nested lists |
| Phase B directives | ❌ Not started | cards, tables, gallery |
| Phase C directives | ❌ Not started | includes, embeds, navigation |
| Integration | ❌ Not started | Parser factory, deprecation |

---

## Motivation

Bengal currently has 55+ directive names (31 directive modules) built on mistune's `DirectivePlugin` base class. While Phase 2 of Patitas created the `DirectiveHandler` protocol and example implementations, Bengal's production directives remain on mistune.

**Why not use adapters/shims?**

1. **Technical debt**: Adapters add complexity without removing mistune dependency
2. **Performance**: Two parsing passes (patitas → adapter → mistune shim)
3. **Maintenance burden**: Must maintain compatibility with two systems
4. **Free-threading**: mistune isn't designed for 3.14t; adapters inherit those limitations

**Native migration benefits:**

1. **Clean architecture**: Single parsing path with typed AST
2. **Performance**: Direct patitas parsing, no translation layer
3. **Thread-safe by design**: Immutable AST nodes, no shared state
4. **Full control**: Optimize directive implementations for patitas's model

---

## Architecture Comparison

### Bengal Directive (mistune-based)

```python
class DropdownDirective(BengalDirective):
    NAMES: ClassVar[list[str]] = ["dropdown", "details"]
    TOKEN_TYPE: ClassVar[str] = "dropdown"
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = DropdownOptions
    CONTRACT: ClassVar[DirectiveContract | None] = None

    def parse_directive(
        self, title: str, options: DropdownOptions,
        content: str, children: list[dict], state: Any
    ) -> DirectiveToken:
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={"title": title, "open": options.open, ...},
            children=children,
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        title = attrs.get("title", "Details")
        return f'<details class="dropdown">...'
```

### Patitas Directive (implemented)

```python
class DropdownDirective:
    names: ClassVar[tuple[str, ...]] = ("dropdown", "details")
    token_type: ClassVar[str] = "dropdown"
    contract: ClassVar[DirectiveContract | None] = DROPDOWN_CONTRACT
    options_class: ClassVar[type[DropdownOptions]] = DropdownOptions

    def parse(
        self, name: str, title: str | None, options: DropdownOptions,
        content: str, children: Sequence[Block], location: SourceLocation
    ) -> Directive:
        return Directive(
            location=location,
            name=name,
            title=title or "Details",
            options=frozenset(opts_items),
            children=tuple(children),
        )

    def render(
        self, node: Directive, rendered_children: str, sb: StringBuilder
    ) -> None:
        sb.append(f'<details class="dropdown">...')
```

**Key differences:**

| Aspect | Bengal (mistune) | Patitas |
|--------|------------------|---------|
| State | Mutable `state` object | Immutable `SourceLocation` |
| Children | `list[dict]` tokens | `tuple[Block, ...]` AST nodes |
| Render output | Return `str` | Append to `StringBuilder` |
| Attributes | `dict[str, Any]` | `frozenset[tuple[str, str]]` |
| Class attrs | `NAMES` (list, SCREAMING_CASE) | `names` (tuple, snake_case) |
| Immutability | Mutable dataclasses | `frozen=True, slots=True` |

---

## Implementation Details (Completed)

### Icon Integration

All Phase A directives integrate with Bengal's icon system:

```python
# patitas/directives/builtins/admonition.py:98-113
def _render_admonition_icon(icon_name: str) -> str:
    try:
        from bengal.directives._icons import render_svg_icon
        return render_svg_icon(icon_name, size=20, css_class="admonition-icon")
    except ImportError:
        return ""  # Graceful fallback
```

**Icon-dependent directives implemented:**
- `admonition.py` — All 10 types with type-to-icon mapping
- `dropdown.py` — Optional title icons
- `tabs.py` — Tab label icons

### Options System

All options use frozen dataclasses with automatic type coercion:

```python
# patitas/directives/options.py
@dataclass(frozen=True, slots=True)
class StyledOptions(DirectiveOptions):
    class_: str | None = None
    name: str | None = None

@dataclass(frozen=True, slots=True)
class DropdownOptions(StyledOptions):
    open: bool = False
    icon: str | None = None
    badge: str | None = None
    color: str | None = None
    description: str | None = None
```

### Contract Validation

Predefined contracts enforce nesting rules:

```python
# patitas/directives/contracts.py
STEPS_CONTRACT = DirectiveContract(
    requires_children=("step",),
    allows_children=("step",),
)

STEP_CONTRACT = DirectiveContract(
    requires_parent=("steps",),
)
```

### Tabs Rendering Modes

Two rendering modes implemented:

1. **Enhanced (default)**: JavaScript-based tabs with `data-tab-target`
2. **CSS State Machine**: URL-driven tabs using `:target` CSS selector

```python
# patitas/directives/builtins/tabs.py:266-269
if mode == "css_state_machine":
    self._render_css_state_machine(tab_id, sync_key, matches, sb)
else:
    self._render_enhanced(tab_id, sync_key, matches, sb)
```

---

## Complete Directive Inventory

### Admonitions (10 directive names, 1 module)

| Directive | Status | Notes |
|-----------|--------|-------|
| `note` | ✅ Done | Multi-name registration |
| `tip` | ✅ Done | |
| `warning` | ✅ Done | |
| `danger` | ✅ Done | |
| `error` | ✅ Done | |
| `info` | ✅ Done | |
| `example` | ✅ Done | |
| `success` | ✅ Done | |
| `caution` | ✅ Done | Maps to `warning` CSS |
| `seealso` | ✅ Done | |

### Layout & Structure (12 directive names)

| Directive | Aliases | Status | Notes |
|-----------|---------|--------|-------|
| `dropdown` | `details` | ✅ Done | Full options, icons, colors |
| `container` | `div` | ✅ Done | Generic wrapper |
| `tab-set` | `tabs` | ✅ Done | Two render modes |
| `tab-item` | `tab` | ✅ Done | Icons, badges, sync |
| `steps` | — | ✅ Done | Contract validation |
| `step` | — | ✅ Done | Metadata, anchors |
| `cards` | — | ✅ Done (B.1) | Grid layout |
| `card` | — | ✅ Done (B.1) | Contract: requires `cards` |
| `child-cards` | — | ✅ Done (B.1) | Auto-generates cards |

### Content & Tables (6 directive names)

| Directive | Aliases | Status | Notes |
|-----------|---------|--------|-------|
| `code-tabs` | `code_tabs` | ⏳ Phase B | Language sync |
| `list-table` | — | ⏳ Phase B | Table from list |
| `data-table` | — | ⏳ Phase B | Table from YAML/JSON |
| `checklist` | — | ⏳ Phase B | Interactive checkboxes |
| `gallery` | — | ⏳ Phase B | Image grid |
| `figure` | — | ⏳ Phase B | Image with caption |

### Embeds - Video (5 directive names)

| Directive | Status | Notes |
|-----------|--------|-------|
| `youtube` | ⏳ Phase C | Embed iframe |
| `vimeo` | ⏳ Phase C | Embed iframe |
| `video` | ⏳ Phase C | HTML5 `<video>` |
| `tiktok` | ⏳ Phase C | Embed iframe |
| `audio` | ⏳ Phase C | HTML5 `<audio>` |

### Embeds - Developer Tools (6 directive names)

| Directive | Status | Notes |
|-----------|--------|-------|
| `gist` | ⏳ Phase C | GitHub Gist |
| `codepen` | ⏳ Phase C | CodePen embed |
| `codesandbox` | ⏳ Phase C | CodeSandbox embed |
| `stackblitz` | ⏳ Phase C | StackBlitz embed |
| `spotify` | ⏳ Phase C | Spotify embed |
| `soundcloud` | ⏳ Phase C | SoundCloud embed |

### File Inclusion (3 directive names)

| Directive | Status | Notes |
|-----------|--------|-------|
| `include` | ⏳ Phase C | File system, caching |
| `literalinclude` | ⏳ Phase C | Code file inclusion |
| `marimo` | ⏳ Phase C | Notebook integration |

### Navigation (4 directive names)

| Directive | Status | Notes |
|-----------|--------|-------|
| `breadcrumbs` | ⏳ Phase C | Site navigation |
| `siblings` | ⏳ Phase C | Adjacent pages |
| `prev-next` | ⏳ Phase C | Sequential navigation |
| `related` | ⏳ Phase C | Related content |

### Versioning (6 directive names)

| Directive | Aliases | Status | Notes |
|-----------|---------|--------|-------|
| `since` | `versionadded` | ⏳ Phase C | Version badge |
| `deprecated` | `versionremoved` | ⏳ Phase C | Deprecation notice |
| `changed` | `versionchanged` | ⏳ Phase C | Change notice |

### Miscellaneous (9 directive names)

| Directive | Aliases | Status | Notes |
|-----------|---------|--------|-------|
| `badge` | `bdg` | ⏳ Phase C | Inline badge |
| `button` | — | ⏳ Phase C | Styled button |
| `icon` | `svg-icon` | ⏳ Phase C | Inline SVG |
| `rubric` | — | ⏳ Phase C | Section heading |
| `target` | `anchor` | ⏳ Phase C | Link target |
| `example-label` | — | ⏳ Phase C | Example annotation |
| `glossary` | — | ⏳ Phase C | ⚠️ Requires roles |
| `build` | — | ⏳ Phase C | Build-time directive |
| `asciinema` | — | ⏳ Phase C | Terminal recording |

**Summary: 20 done, 35 remaining**

---

## Phase Plan (Updated)

### ~~Phase 0: Pre-work~~ — SUPERSEDED

> Original plan was to validate builtins. Colleague implemented full-featured
> directives with Bengal HTML matching from the start.

### ~~Phase A: Core Directives~~ — ✅ COMPLETE

All 5 core directive modules implemented (1,400+ LOC):

| File | Directives | LOC |
|------|------------|-----|
| `admonition.py` | 10 types | 216 |
| `dropdown.py` | dropdown, details | 244 |
| `tabs.py` | tab-set, tab-item | 465 |
| `container.py` | container, div | 127 |
| `steps.py` | steps, step | 348 |

### Phase A.1: Test Infrastructure — COMPLETE ✅

**Status**: Complete (2025-12-28)

**Goal**: Prove HTML output equivalence between Bengal/mistune and Patitas implementations.

**Results**:
- **43/43 parity tests passing** (100% HTML match)
- **74/79 edge case tests passing** (94%)
- **5 remaining edge cases**: tables, task lists, nested lists, bold-italic, indented content

**Bugs Fixed During Implementation**:

| Component | Issue | Fix |
|-----------|-------|-----|
| `lexer.py` | Lists not parsed inside directives | Added block element classification |
| `lexer.py` | Code fence returns to wrong mode | Check directive stack, return to DIRECTIVE mode |
| `html.py` | Quote escaping mismatch | Changed `_escape_html` to escape quotes |
| `html.py` | Missing trailing newline in code | Added newline after code content |
| `html.py` | Container directives can't render children | Added `render_child_directive` callback |
| `dropdown.py` | `:open:` flag not recognized | Handle empty value as True |
| `tabs.py` | `:selected:` flag not recognized | Handle empty value as True |
| `admonition.py` | `:class:` option not applied | Check `class` key (not `class_`) |
| `container.py` | Title not used as CSS class | Parse title as class names |
| `steps.py` | Step numbers always 1 | Render children directly with injected numbers |

#### Test Framework Design

```python
# tests/migration/conftest.py

import pytest
from pathlib import Path
from bengal.rendering import create_parser
from bengal.rendering.parsers.patitas import parse as patitas_parse

GOLDEN_DIR = Path(__file__).parent / "golden_files"


def render_with_bengal_mistune(source: str) -> str:
    """Render using the existing Bengal/mistune pipeline."""
    parser = create_parser(backend="mistune")
    return parser.render(source)


def render_with_patitas(source: str) -> str:
    """Render using the new Patitas pipeline."""
    return patitas_parse(source)


def normalize_html(html: str) -> str:
    """Normalize HTML for comparison.

    - Strip leading/trailing whitespace per line
    - Normalize attribute order (alphabetical)
    - Collapse multiple spaces
    - Remove blank lines
    """
    import re
    from html.parser import HTMLParser

    # Simple normalization - production should use proper HTML parser
    lines = [line.strip() for line in html.split("\n") if line.strip()]
    normalized = "\n".join(lines)
    return re.sub(r"\s+", " ", normalized).strip()


@pytest.fixture
def golden_file_path(request):
    """Return path for golden file based on test name."""
    test_name = request.node.name
    return GOLDEN_DIR / f"{test_name}.html"
```

#### Test Cases

```python
# tests/migration/test_directive_parity.py

import pytest
from tests.migration.conftest import (
    render_with_bengal_mistune,
    render_with_patitas,
    normalize_html,
)

# Comprehensive test cases covering all Phase A directives
DIRECTIVE_TEST_CASES = [
    # Admonitions - basic
    ("note_basic", ":::{note}\nContent\n:::"),
    ("note_titled", ":::{note} Custom Title\nContent\n:::"),
    ("warning_basic", ":::{warning}\nDanger ahead!\n:::"),
    ("tip_basic", ":::{tip}\nHelpful tip here.\n:::"),
    ("danger_basic", ":::{danger}\nCritical warning!\n:::"),
    ("error_basic", ":::{error}\nError message.\n:::"),
    ("info_basic", ":::{info}\nInformational note.\n:::"),
    ("example_basic", ":::{example}\nExample content.\n:::"),
    ("success_basic", ":::{success}\nSuccess message.\n:::"),
    ("caution_basic", ":::{caution}\nProceed carefully.\n:::"),
    ("seealso_basic", ":::{seealso}\nRelated topics.\n:::"),

    # Admonitions - with options
    ("note_with_class", ":::{note}\n:class: custom-note\nContent\n:::"),
    ("note_collapsible", ":::{note}\n:collapsible:\nCollapsible content\n:::"),

    # Dropdown - all option combinations
    ("dropdown_basic", ":::{dropdown} Title\nContent\n:::"),
    ("dropdown_open", ":::{dropdown} Title\n:open:\nContent\n:::"),
    ("dropdown_icon", ":::{dropdown} Title\n:icon: info\nContent\n:::"),
    ("dropdown_badge", ":::{dropdown} Title\n:badge: New\nContent\n:::"),
    ("dropdown_color_success", ":::{dropdown} Title\n:color: success\nContent\n:::"),
    ("dropdown_color_warning", ":::{dropdown} Title\n:color: warning\nContent\n:::"),
    ("dropdown_color_danger", ":::{dropdown} Title\n:color: danger\nContent\n:::"),
    ("dropdown_color_info", ":::{dropdown} Title\n:color: info\nContent\n:::"),
    ("dropdown_description", ":::{dropdown} Title\n:description: More context\nContent\n:::"),
    ("dropdown_full", ":::{dropdown} Title\n:open:\n:icon: info\n:badge: New\n:color: info\n:description: Details\nContent\n:::"),
    ("details_alias", ":::{details} Title\nContent\n:::"),

    # Tabs - basic and advanced
    ("tabs_basic", "::::{tab-set}\n:::{tab-item} Tab 1\nContent 1\n:::\n:::{tab-item} Tab 2\nContent 2\n:::\n::::"),
    ("tabs_sync", "::::{tab-set}\n:sync: language\n:::{tab-item} Python\n:sync: python\ncode\n:::\n::::"),
    ("tabs_selected", "::::{tab-set}\n:::{tab-item} Tab 1\nContent 1\n:::\n:::{tab-item} Tab 2\n:selected:\nContent 2\n:::\n::::"),
    ("tabs_with_badges", "::::{tab-set}\n:::{tab-item} Tab 1\n:badge: New\nContent\n:::\n::::"),
    ("tabs_alias", "::::{tabs}\n:::{tab} Tab 1\nContent 1\n:::\n::::"),

    # Steps - basic and advanced
    ("steps_basic", "::::{steps}\n:::{step} Step 1\nDo this\n:::\n::::"),
    ("steps_start_number", "::::{steps}\n:start: 2\n:::{step} Step 2\nContent\n:::\n::::"),
    ("step_description", "::::{steps}\n:::{step} Step 1\n:description: Lead-in text\nContent\n:::\n::::"),
    ("step_duration", "::::{steps}\n:::{step} Step 1\n:duration: 5 min\nContent\n:::\n::::"),
    ("steps_full", "::::{steps}\n:start: 1\n:::{step} Step 1\n:description: First step\n:duration: 5 min\nDo this\n:::\n:::{step} Step 2\n:description: Second step\n:duration: 10 min\nDo that\n:::\n::::"),

    # Container
    ("container_basic", ":::{container} my-class\nContent\n:::"),
    ("container_multiple_classes", ":::{container} class-a class-b\nContent\n:::"),
    ("div_alias", ":::{div} wrapper\nContent\n:::"),

    # Nested directives
    ("nested_note_in_dropdown", "::::{dropdown} Title\n:::{note}\nNested note\n:::\n::::"),
    ("nested_tabs_in_dropdown", ":::::{dropdown} Title\n::::{tab-set}\n:::{tab-item} Tab\nContent\n:::\n::::\n:::::"),
]


@pytest.mark.parametrize("name,source", DIRECTIVE_TEST_CASES)
def test_html_parity(name: str, source: str):
    """Verify Patitas produces identical HTML to Bengal/mistune."""
    bengal_html = render_with_bengal_mistune(source)
    patitas_html = render_with_patitas(source)
    assert normalize_html(patitas_html) == normalize_html(bengal_html), (
        f"HTML mismatch in {name}\n"
        f"Expected (Bengal):\n{bengal_html}\n\n"
        f"Got (Patitas):\n{patitas_html}"
    )


@pytest.mark.parametrize("name,source", DIRECTIVE_TEST_CASES)
def test_golden_file(name: str, source: str, golden_file_path, update_golden_files):
    """Compare against golden files (update with --update-golden-files)."""
    patitas_html = render_with_patitas(source)

    if update_golden_files:
        golden_file_path.parent.mkdir(parents=True, exist_ok=True)
        golden_file_path.write_text(patitas_html)
        pytest.skip("Golden file updated")

    if not golden_file_path.exists():
        pytest.skip(f"Golden file not found: {golden_file_path}")

    expected = golden_file_path.read_text()
    assert normalize_html(patitas_html) == normalize_html(expected)
```

#### Edge Cases and Error Handling

```python
# tests/migration/test_directive_edge_cases.py

import pytest

EDGE_CASES = [
    # Empty content
    ("empty_note", ":::{note}\n:::"),
    ("empty_dropdown", ":::{dropdown} Title\n:::"),

    # Special characters in titles
    ("special_chars_title", ":::{note} Title with <script> & \"quotes\"\nContent\n:::"),

    # Markdown in content
    ("markdown_in_content", ":::{note}\n**Bold** and *italic* and `code`\n:::"),

    # Code blocks inside directives
    ("code_block_in_directive", ":::{note}\n```python\nprint('hello')\n```\n:::"),

    # Unicode content
    ("unicode_content", ":::{note}\n日本語とEmoji 🎉\n:::"),

    # Very long content
    ("long_content", ":::{note}\n" + "Content. " * 500 + "\n:::"),

    # Missing closing fence
    ("unclosed_directive", ":::{note}\nThis is never closed"),

    # Invalid option values
    ("invalid_color", ":::{dropdown} Title\n:color: invalid\nContent\n:::"),
]

@pytest.mark.parametrize("name,source", EDGE_CASES)
def test_edge_case_parity(name: str, source: str):
    """Edge cases produce identical results or both fail gracefully."""
    # Implementation here
    pass
```

#### Test Infrastructure Tasks

| Task | Status | Notes |
|------|--------|-------|
| Create `tests/migration/` directory | ⏳ Pending | |
| Implement `conftest.py` fixtures | ⏳ Pending | normalize_html, golden file support |
| Create `DIRECTIVE_TEST_CASES` | ⏳ Pending | 40+ test cases |
| Implement parity comparison | ⏳ Pending | Side-by-side comparison |
| Generate initial golden files | ⏳ Pending | From Bengal/mistune output |
| Add `--update-golden-files` pytest option | ⏳ Pending | For regeneration |
| CI integration | ⏳ Pending | Run parity tests on PRs |

**Exit Criteria**:
- All 40+ Phase A directive test cases pass
- Zero HTML diff between mistune and Patitas rendering
- Golden files committed to version control

### Phase B: Content Directives — IN PROGRESS

**Goal**: Migrate content-focused directives that are widely used in documentation.

**Phase B.1**: ✅ COMPLETE (2025-12-28)

| Directive | Complexity | Dependencies | Status |
|-----------|------------|--------------|--------|
| `cards` / `card` / `child-cards` | High | Contracts exist | ✅ Done |
| `code-tabs` | Medium | Rosettes | ⏳ Next |
| `list-table` | Medium | — | ⏳ Pending |
| `data-table` | Medium | — | ⏳ Pending |
| `figure` / `gallery` / `audio` | Medium | — | ⏳ Pending |
| `checklist` | Low | — | ⏳ Pending |

#### B.1: Cards System (High Priority) — ✅ COMPLETE

**Files created**:
- `patitas/directives/builtins/cards.py` (~500 LOC)

**Implementation Notes**:
- `CardsDirective`: Grid container with columns, gap, style, variant options
- `CardDirective`: Individual card with link, icon, badge, color, description
- `ChildCardsDirective`: Auto-generates cards from child pages (placeholder for build-time)
- All parity tests passing (17/17 card-related tests)

**Source analysis** from `bengal/directives/cards/`:

```python
# cards_grid.py: CardsDirective
# - Options: columns, gap, style, variant, layout
# - Contract: CARDS_CONTRACT (allows card children)
# - Renders: <div class="card-grid" data-columns="..." ...>

# card.py: CardDirective  
# - Options: link, target, icon, description, columns, rows
# - Contract: CARD_CONTRACT (requires cards parent)
# - Renders: <a class="card" ...> or <div class="card" ...>

# child_cards.py: ChildCardsDirective
# - Auto-generates cards from child pages
# - Complex: requires site context
```

**Implementation pattern**:

```python
@dataclass(frozen=True, slots=True)
class CardsOptions(StyledOptions):
    columns: str = "auto"
    gap: str = "medium"
    style: str = "default"
    variant: str = "navigation"
    layout: str = "default"


class CardsDirective:
    names: ClassVar[tuple[str, ...]] = ("cards",)
    token_type: ClassVar[str] = "cards_grid"
    contract: ClassVar[DirectiveContract] = CARDS_CONTRACT
    options_class: ClassVar[type[CardsOptions]] = CardsOptions

    def render(self, node: Directive, rendered_children: str, sb: StringBuilder) -> None:
        opts = dict(node.options)
        sb.append(f'<div class="card-grid" data-columns="{opts.get("columns", "auto")}" ...>')
        sb.append(rendered_children)
        sb.append('</div>\n')
```

**Estimated LOC**: 400 (cards_grid + card + child_cards combined)

#### B.2: Code Tabs (Medium Priority)

**Dependency**: Rosettes syntax highlighting integration

**Source**: `bengal/directives/code_tabs.py`

```python
# CodeTabsDirective
# - Similar to tab-set but specifically for code blocks
# - Language sync: clicking Python shows Python in all synced code-tabs
# - Options: sync_group, show_copy_button

@dataclass(frozen=True, slots=True)
class CodeTabsOptions(StyledOptions):
    sync_group: str | None = None
    show_copy_button: bool = True


class CodeTabsDirective:
    names: ClassVar[tuple[str, ...]] = ("code-tabs", "code_tabs")
    token_type: ClassVar[str] = "code_tabs"
    contract: ClassVar[DirectiveContract] = CODE_TABS_CONTRACT
    options_class: ClassVar[type[CodeTabsOptions]] = CodeTabsOptions
```

**Estimated LOC**: 200

#### B.3: Tables (Medium Priority)

**Source**: `bengal/directives/list_table.py`, `data_table.py`

```python
# list-table: Convert bullet lists to tables
# - Options: header_rows, stub_columns, widths, align

# data-table: Table from YAML/JSON data
# - Options: source, columns, sortable, filterable
```

**Estimated LOC**: 300 (both combined)

#### B.4: Media Directives (Medium Priority)

**Source**: `bengal/directives/figure.py`, `gallery.py`

```python
# figure: Image with caption
# - Options: width, height, alt, align, target

# gallery: Grid of images
# - Options: columns, gap, lightbox, captions

# audio: HTML5 audio player
# - Options: src, controls, autoplay, loop
```

**Estimated LOC**: 250

#### B.5: Checklist (Low Priority)

**Source**: `bengal/directives/checklist.py`

```python
# checklist: Interactive checkboxes
# - Options: interactive, persist

class ChecklistDirective:
    names: ClassVar[tuple[str, ...]] = ("checklist",)
    token_type: ClassVar[str] = "checklist"
```

**Estimated LOC**: 100

#### Phase B Implementation Order

1. **Week 4**: Cards system (high usage, complex contracts)
2. **Week 5**: Code-tabs + tables (developer docs staple)
3. **Week 5**: Media + checklist (lower complexity)

**Estimated Total**: 1,250 LOC, 2 weeks

### Phase C: Specialized Directives — NOT STARTED

**Goal**: Complete migration of remaining directives by category.

| Category | Directives | Complexity |
|----------|------------|------------|
| File I/O | include, literalinclude | High |
| Video embeds | youtube, vimeo, video, tiktok | Low |
| Developer embeds | gist, codepen, codesandbox, stackblitz, spotify, soundcloud | Low |
| Navigation | breadcrumbs, siblings, prev-next, related | Medium |
| Versioning | since, deprecated, changed | Low |
| Miscellaneous | badge, button, icon, rubric, target, example-label, build, asciinema | Low |
| Cross-refs | glossary | Medium (⚠️ needs roles) |

#### C.1: File I/O Directives (High Priority, High Complexity)

**Source**: `bengal/directives/include.py`, `literalinclude.py`

**Key challenges**:
- File system access (security: path traversal protection)
- Caching strategy for repeated includes
- Parse-time vs render-time resolution
- Circular include detection

```python
@dataclass(frozen=True, slots=True)
class IncludeOptions(DirectiveOptions):
    literal: bool = False  # Include as literal (no parsing)
    start_line: int | None = None
    end_line: int | None = None
    start_after: str | None = None
    end_before: str | None = None
    encoding: str = "utf-8"


class IncludeDirective:
    names: ClassVar[tuple[str, ...]] = ("include",)
    token_type: ClassVar[str] = "include"

    def parse(self, ..., context: ParseContext) -> Directive:
        # Resolve path relative to current file
        # Check file exists
        # Load content with caching
        # Recursively parse if not literal
        pass


class LiteralIncludeDirective:
    names: ClassVar[tuple[str, ...]] = ("literalinclude",)
    token_type: ClassVar[str] = "literalinclude"

    # Options: language, linenos, emphasize_lines, caption, dedent
    # Integrates with Rosettes for syntax highlighting
```

**File**: `patitas/directives/builtins/include.py` (~300 LOC)

**Special consideration**: Include directives require `ParseContext` to:
- Resolve relative paths
- Access file system (sandboxed)
- Track include stack for circular detection

#### C.2: Video Embeds (Low Complexity)

**Source**: `bengal/directives/video.py`

```python
# All share common pattern: embed iframe with provider-specific URL

@dataclass(frozen=True, slots=True)
class EmbedOptions(StyledOptions):
    width: str = "100%"
    height: str = "315"
    title: str | None = None
    privacy_enhanced: bool = True  # YouTube: use youtube-nocookie.com


class YouTubeDirective:
    names: ClassVar[tuple[str, ...]] = ("youtube",)

    def render(self, node: Directive, ..., sb: StringBuilder) -> None:
        video_id = node.title  # e.g., "dQw4w9WgXcQ"
        sb.append(f'<iframe src="https://www.youtube-nocookie.com/embed/{video_id}" ...></iframe>')


class VimeoDirective:
    names: ClassVar[tuple[str, ...]] = ("vimeo",)
    # Similar pattern


class TikTokDirective:
    names: ClassVar[tuple[str, ...]] = ("tiktok",)
    # Uses TikTok embed script


class VideoDirective:
    names: ClassVar[tuple[str, ...]] = ("video",)
    # HTML5 <video> element
    # Options: src, poster, controls, autoplay, loop, muted
```

**File**: `patitas/directives/builtins/video.py` (~200 LOC)

#### C.3: Developer Embeds (Low Complexity)

**Source**: `bengal/directives/embed.py`

```python
# Common embed pattern for developer tools

class GistDirective:
    # Options: file (specific file from gist)
    # Renders: <script src="https://gist.github.com/{user}/{id}.js"></script>

class CodePenDirective:
    # Options: height, theme, default_tab, editable
    # Renders: <iframe src="https://codepen.io/..."></iframe>

class CodeSandboxDirective:
    # Options: height, view (editor/preview/split)

class StackBlitzDirective:
    # Options: height, embed_options
```

**File**: `patitas/directives/builtins/embed.py` (~250 LOC)

#### C.4: Navigation Directives (Medium Complexity)

**Source**: `bengal/directives/navigation.py`

**Key challenge**: Requires site context (page tree, siblings, etc.)

```python
class BreadcrumbsDirective:
    # Renders page hierarchy: Home > Section > Page
    # Requires: current page path, site structure

    def render(self, node: Directive, context: RenderContext, sb: StringBuilder) -> None:
        page = context.current_page
        ancestors = context.site.get_ancestors(page)
        # Render breadcrumb trail


class SiblingsDirective:
    # Shows adjacent pages at same level

class PrevNextDirective:
    # Sequential navigation links
    # Options: show_title, show_icon

class RelatedDirective:
    # Manual related links from frontmatter
```

**File**: `patitas/directives/builtins/navigation.py` (~200 LOC)

#### C.5: Versioning Directives (Low Complexity)

**Source**: `bengal/directives/versioning.py`

```python
@dataclass(frozen=True, slots=True)
class VersioningOptions(StyledOptions):
    version: str | None = None  # Can also use title


class SinceDirective:
    names: ClassVar[tuple[str, ...]] = ("since", "versionadded")
    # Renders: <div class="version-badge added"><span>New in v{version}</span>...</div>


class DeprecatedDirective:
    names: ClassVar[tuple[str, ...]] = ("deprecated", "versionremoved")
    # Renders: <div class="version-badge deprecated">...</div>


class ChangedDirective:
    names: ClassVar[tuple[str, ...]] = ("changed", "versionchanged")
    # Renders: <div class="version-badge changed">...</div>
```

**File**: `patitas/directives/builtins/versioning.py` (~150 LOC)

#### C.6: Miscellaneous Directives (Low Complexity)

**Source**: Various files

```python
# badge.py: Inline badge
class BadgeDirective:
    names: ClassVar[tuple[str, ...]] = ("badge", "bdg")
    # Options: color, link
    # Renders: <span class="badge badge-{color}">{title}</span>

# button.py: Styled button/link
class ButtonDirective:
    names: ClassVar[tuple[str, ...]] = ("button",)
    # Options: link, color, size, outline

# icon.py: Inline SVG icon
class IconDirective:
    names: ClassVar[tuple[str, ...]] = ("icon", "svg-icon")
    # Uses Bengal icon system

# rubric.py: Section heading (no TOC entry)
class RubricDirective:
    names: ClassVar[tuple[str, ...]] = ("rubric",)
    # Renders: <p class="rubric">{title}</p>

# target.py: Link target/anchor
class TargetDirective:
    names: ClassVar[tuple[str, ...]] = ("target", "anchor")
    # Renders: <span id="{name}"></span>

# example_label.py: Example annotation
class ExampleLabelDirective:
    names: ClassVar[tuple[str, ...]] = ("example-label",)

# terminal.py: Asciinema recordings
class AsciinemaDirective:
    names: ClassVar[tuple[str, ...]] = ("asciinema",)
    # Embeds asciinema player

# build.py: Build-time conditional content
class BuildDirective:
    names: ClassVar[tuple[str, ...]] = ("build",)
    # Options: env, format
    # Conditional rendering based on build config
```

**Files**:
- `patitas/directives/builtins/inline.py` (~150 LOC) - badge, icon, target
- `patitas/directives/builtins/button.py` (~80 LOC)
- `patitas/directives/builtins/misc.py` (~120 LOC) - rubric, example-label, build

#### C.7: Cross-Reference Directives (Blocked)

**Source**: `bengal/directives/glossary.py`

```python
# ⚠️ BLOCKED: Requires role system migration

class GlossaryDirective:
    # Creates glossary from definition list
    # Referenced via {term}`word` role

    # Defer to separate RFC: rfc-patitas-roles-migration
```

**Recommendation**: Create `rfc-patitas-roles-migration.md` RFC to handle:
- `{term}` role for glossary references
- `{ref}` role for cross-references
- `{doc}` role for document links
- Custom role support

#### Phase C Implementation Order

1. **Week 6**: Video + developer embeds (quick wins)
2. **Week 6**: Versioning + miscellaneous (quick wins)
3. **Week 7**: Navigation (requires site context)
4. **Week 7**: File I/O (complex, security-sensitive)

**Estimated Total**: 1,450 LOC, 2 weeks

### Phase D: Integration & Deprecation — NOT STARTED

**Goal**: Seamlessly switch Bengal from mistune to Patitas backend with zero breaking changes.

#### D.1: Parser Factory Update

**Source**: `bengal/rendering/factory.py`

```python
# Current API
parser = create_parser(backend="mistune")  # Default

# New API (backward compatible)
parser = create_parser(backend="patitas")  # New default
parser = create_parser(backend="mistune")  # Legacy, deprecated
```

**Implementation**:

```python
# bengal/rendering/factory.py

import warnings
from typing import Literal

Backend = Literal["patitas", "mistune"]


def create_parser(
    backend: Backend = "patitas",
    *,
    directives: DirectiveRegistry | None = None,
    strict: bool = False,
) -> MarkdownParser:
    """Create a markdown parser with the specified backend.

    Args:
        backend: Parser backend ("patitas" or "mistune")
        directives: Custom directive registry (default: all built-ins)
        strict: Enable strict parsing (errors instead of warnings)

    Returns:
        Configured MarkdownParser instance

    .. deprecated:: 2.0
        The "mistune" backend is deprecated and will be removed in 3.0.
        Use "patitas" (default) for thread-safe parsing.
    """
    if backend == "mistune":
        warnings.warn(
            "The 'mistune' backend is deprecated and will be removed in Bengal 3.0. "
            "Use 'patitas' (default) for thread-safe, typed parsing.",
            DeprecationWarning,
            stacklevel=2,
        )
        return _create_mistune_parser(directives)

    return _create_patitas_parser(directives, strict)
```

#### D.2: Directive Registry Bridge

**Goal**: Allow using existing Bengal directives with Patitas during transition.

```python
# bengal/rendering/parsers/patitas/directives/compat.py

class BengalDirectiveAdapter:
    """Adapter to use Bengal BengalDirective with Patitas parser.

    This is a temporary bridge for directives not yet migrated.
    Performance: ~20% slower than native Patitas directives.

    Usage:
        adapter = BengalDirectiveAdapter(SomeBengalDirective())
        registry.register(adapter)
    """

    def __init__(self, bengal_directive: BengalDirective):
        self._wrapped = bengal_directive
        self.names = tuple(bengal_directive.NAMES)
        self.token_type = bengal_directive.TOKEN_TYPE
        self.options_class = self._convert_options_class(bengal_directive.OPTIONS_CLASS)
        self.contract = self._convert_contract(bengal_directive.CONTRACT)

    def parse(self, name, title, options, content, children, location) -> Directive:
        # Convert Patitas args to Bengal format
        # Call Bengal directive's parse_directive
        # Convert result back to Patitas Directive
        pass

    def render(self, node: Directive, rendered_children: str, sb: StringBuilder) -> None:
        # Convert to Bengal format
        # Call Bengal directive's render
        # Append result to StringBuilder
        pass
```

**Note**: Adapter is for transition only. Native Patitas implementations are preferred.

#### D.3: Test Suite Transition

**Test Matrix**:

| Test Category | Backend | Status |
|---------------|---------|--------|
| Unit tests | Both | Run all tests against both backends |
| Integration tests | Both | Compare outputs |
| Golden file tests | Both | Must match exactly |
| Performance tests | Both | Patitas must be ≤5% slower |
| Thread-safety tests | Patitas only | TSan verification |

```python
# conftest.py

@pytest.fixture(params=["patitas", "mistune"])
def parser_backend(request):
    """Run tests against both backends."""
    return request.param


def test_directive_output(parser_backend):
    parser = create_parser(backend=parser_backend)
    result = parser.render(":::{note}\nContent\n:::")
    assert "admonition" in result
```

#### D.4: Deprecation Timeline

| Version | Action |
|---------|--------|
| 2.0 | Patitas becomes default, mistune deprecated with warning |
| 2.1 | Deprecation warnings become errors (configurable) |
| 3.0 | Mistune backend removed |

**Deprecation messages**:

```python
# Using mistune backend
warnings.warn(
    "The 'mistune' backend is deprecated. "
    "Use 'patitas' for thread-safe parsing. "
    "See migration guide: https://bengal.dev/migration/patitas",
    DeprecationWarning,
)

# Importing mistune directives directly
warnings.warn(
    "Importing from 'bengal.directives' is deprecated. "
    "Use 'bengal.rendering.parsers.patitas.directives' instead.",
    DeprecationWarning,
)
```

#### D.5: Documentation Updates

| Document | Changes |
|----------|---------|
| Migration Guide | New: `docs/migration/patitas.md` |
| API Reference | Update parser factory docs |
| Directive Reference | Note Patitas equivalents |
| Changelog | Document breaking changes |
| README | Update quick start examples |

#### D.6: Rollout Strategy

**Phase D.1: Internal testing (Week 8)**
- Enable Patitas on CI
- Run full test suite with both backends
- Fix any parity issues

**Phase D.2: Opt-in (Week 8)**
- Release as minor version (2.x)
- Patitas available via `backend="patitas"`
- Default remains mistune
- Collect feedback

**Phase D.3: Default switch (Week 9)**
- Patitas becomes default
- Mistune requires explicit opt-in
- Deprecation warnings active

**Phase D.4: Cleanup (Future 3.0)**
- Remove mistune backend
- Remove adapter layer
- Remove deprecated imports

**Estimated**: 2 weeks

#### D.7: Integration Checklist

- [ ] Parser factory updated with backend parameter
- [ ] Deprecation warnings implemented
- [ ] Adapter layer for unmigrated directives
- [ ] Test suite runs against both backends
- [ ] Golden file tests pass for all directives
- [ ] Performance benchmarks show ≤5% regression
- [ ] TSan verification passes (Python 3.14t)
- [ ] Migration guide written
- [ ] Changelog updated
- [ ] README updated

---

## File Structure

### Current (Phase B.1 Complete)

```
bengal/rendering/parsers/patitas/directives/
├── __init__.py
├── protocol.py          # ✅ DirectiveHandler protocol (182 LOC)
├── options.py           # ✅ 8 option classes (253 LOC)
├── contracts.py         # ✅ 10 contracts (320 LOC)
├── registry.py          # ✅ Directive registration
│
└── builtins/            # ✅ Phase A + B.1 complete
    ├── __init__.py      # ✅ Exports all handlers (50 LOC)
    ├── admonition.py    # ✅ 10 types (216 LOC)
    ├── cards.py         # ✅ cards, card, child-cards (500 LOC)
    ├── container.py     # ✅ container, div (127 LOC)
    ├── dropdown.py      # ✅ dropdown, details (244 LOC)
    ├── steps.py         # ✅ steps, step (348 LOC)
    └── tabs.py          # ✅ tab-set, tab-item (465 LOC)
```

### Planned (Phases B.2-D)

```
bengal/rendering/parsers/patitas/directives/
├── ...existing files...
├── compat.py            # ⏳ Phase D: BengalDirectiveAdapter (150 LOC)
│
└── builtins/
    ├── ...existing files...
    │
    │ # Phase B.2: Remaining Content Directives
    ├── code_tabs.py     # ⏳ code-tabs (200 LOC)
    ├── tables.py        # ⏳ list-table, data-table (300 LOC)
    ├── media.py         # ⏳ figure, gallery, audio (250 LOC)
    ├── checklist.py     # ⏳ checklist (100 LOC)
    │
    │ # Phase C: Specialized Directives
    ├── include.py       # ⏳ include, literalinclude (300 LOC)
    ├── video.py         # ⏳ youtube, vimeo, video, tiktok (200 LOC)
    ├── embed.py         # ⏳ gist, codepen, codesandbox, etc. (250 LOC)
    ├── navigation.py    # ⏳ breadcrumbs, siblings, prev-next (200 LOC)
    ├── versioning.py    # ⏳ since, deprecated, changed (150 LOC)
    ├── inline.py        # ⏳ badge, icon, target (150 LOC)
    ├── button.py        # ⏳ button (80 LOC)
    └── misc.py          # ⏳ rubric, example-label, build (120 LOC)

tests/migration/
├── conftest.py          # ✅ Phase A.1: Test fixtures, HTML normalization
├── test_directive_parity.py     # ✅ Phase A.1: 43 parity tests (100% passing)
├── test_directive_edge_cases.py # ✅ Phase A.1: 79 edge cases (74 passing)
├── golden_files/        # ✅ Phase A.1: Directory ready for golden files
│   └── .gitkeep
└── README.md            # ✅ Phase A.1: Test documentation

tests/performance/
├── test_directive_performance.py    # ⏳ Phase D: Benchmarks
└── test_concurrent_parsing.py       # ⏳ Phase D: Thread-safety
```

### LOC Summary

| Phase | Directive LOC | Test LOC | Total |
|-------|---------------|----------|-------|
| A (done) | 1,400 | — | 1,400 |
| A.1 (done) | — | 500 | 500 |
| B.1 (done) | 500 | 200 | 700 |
| B.2 | 750 | 200 | 950 |
| C | 1,450 | 400 | 1,850 |
| D | 150 | 300 | 450 |
| **Total** | **4,250** | **1,600** | **5,850** |

---

## Decision Log

| Date | Decision | Rationale | Alternatives Considered |
|------|----------|-----------|------------------------|
| 2025-12-15 | Native migration over adapters | Adapters add complexity without removing mistune dependency | Shim layer, gradual adapter deprecation |
| 2025-12-18 | Implement full Phase A before testing | Enables comprehensive parity testing | Test-first development |
| 2025-12-20 | Use `StringBuilder` for rendering | Efficient string building without allocations | Return `str` (GC pressure), list join |
| 2025-12-22 | Immutable AST nodes (`frozen=True`) | Thread-safety, hashability | Mutable nodes with locking |
| 2025-12-25 | Icon system graceful fallback | Allows Patitas to work standalone | Hard dependency on Bengal icons |
| 2025-12-28 | Defer `glossary` to roles RFC | Requires role system not yet designed | Stub implementation |

---

## Performance Benchmarks

### Baseline Metrics (mistune)

Collect before migration:

```python
# scripts/benchmark_directives.py

import timeit
from bengal.rendering import create_parser

BENCHMARK_SOURCES = {
    "simple_note": ":::{note}\nContent\n:::",
    "nested_tabs": "::::{tab-set}\n:::{tab-item} Tab 1\nContent\n:::\n::::".repeat(10),
    "complex_page": open("docs/examples/complex_page.md").read(),
}

def benchmark_parser(backend: str, source: str, iterations: int = 1000) -> float:
    parser = create_parser(backend=backend)
    return timeit.timeit(lambda: parser.render(source), number=iterations)
```

### Target Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| Parse time | ≤5% regression | User-noticeable threshold |
| Memory per page | ≤10% increase | Acceptable for immutability |
| Memory per directive | ≤5% increase | Frozen dataclasses are efficient |
| GC pressure | ≤20% increase | Immutable nodes create more objects |

### Benchmark Suite

```python
# tests/performance/test_directive_performance.py

import pytest
from bengal.rendering import create_parser

@pytest.mark.benchmark
def test_simple_directive_parse(benchmark):
    parser = create_parser(backend="patitas")
    result = benchmark(parser.render, ":::{note}\nContent\n:::")
    assert "admonition" in result


@pytest.mark.benchmark
def test_nested_directives_parse(benchmark):
    source = "::::{tab-set}\n" + ":::{tab-item} Tab\nContent\n:::\n" * 20 + "::::"
    parser = create_parser(backend="patitas")
    result = benchmark(parser.render, source)
    assert result


@pytest.mark.benchmark  
def test_complex_page_parse(benchmark):
    source = open("tests/fixtures/complex_page.md").read()
    parser = create_parser(backend="patitas")
    result = benchmark(parser.render, source)
    assert result
```

### Thread-Safety Verification

```bash
# Run with ThreadSanitizer (Python 3.14t)
python3.14t -X tsansupported tests/performance/test_concurrent_parsing.py
```

```python
# tests/performance/test_concurrent_parsing.py

import concurrent.futures
from bengal.rendering import create_parser

def test_concurrent_parsing():
    """Verify no data races under concurrent parsing."""
    parser = create_parser(backend="patitas")
    sources = [f":::{note}\nContent {i}\n:::" for i in range(100)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(parser.render, sources))

    assert len(results) == 100
    assert all("admonition" in r for r in results)
```

---

## Rollback Plan

### Immediate Rollback (Minutes)

If critical issues discovered post-release:

```python
# User config: bengal.toml
[rendering]
backend = "mistune"  # Force legacy backend
```

```bash
# Environment variable override
export BENGAL_PARSER_BACKEND=mistune
```

### Version Rollback (Hours)

```bash
# Revert to previous version
pip install bengal==1.x.x  # Last mistune-default version
```

### Code Rollback (Days)

```bash
# Git revert
git revert <patitas-integration-commit>
git push
# Release patch version
```

### Rollback Criteria

| Severity | Threshold | Action |
|----------|-----------|--------|
| Critical | Any data loss, security issue | Immediate rollback |
| High | >1% of pages render differently | Rollback within 24h |
| Medium | Performance >10% regression | Investigate, optional rollback |
| Low | Edge case rendering differences | Fix forward |

### Rollback Checklist

- [ ] Issue reported and triaged
- [ ] Severity assessed
- [ ] Rollback decision made
- [ ] Config/env override documented
- [ ] Hotfix released (if applicable)
- [ ] Post-mortem scheduled

---

## Risks & Mitigations

| Risk | Status | Mitigation |
|------|--------|------------|
| HTML output differences | ✅ Resolved | Phase A.1: 43/43 parity tests passing |
| Missing edge cases | ⚠️ 5 failures | Tables, task lists, nested lists need work |
| Icon system coupling | ✅ Resolved | Graceful fallback implemented |
| Performance regression | ⚠️ Untested | Benchmark before Phase D |
| Free-threading issues | ⚠️ Untested | TSan in CI (Phase D) |
| Role system dependency | Deferred | `glossary` gated until roles RFC |

---

## Success Criteria

1. **Parity**: 100% of Bengal's directive test cases pass with Patitas
2. **Golden files**: Zero HTML diff between mistune and Patitas rendering
3. **Performance**: ≤5% regression on directive-heavy pages
4. **Thread-safe**: Zero TSan errors under concurrent parsing
5. **Clean break**: No runtime dependency on mistune for directive parsing
6. **Test coverage**: All migrated directives have parity tests

---

## Timeline (Updated)

| Week | Phase | Status | Deliverables |
|------|-------|--------|--------------|
| 1-2 | Phase A | ✅ COMPLETE | Core directives (1,400 LOC) |
| 3 | Phase A.1 | ✅ COMPLETE | Parity tests (500 LOC), 43/43 passing |
| 4 | Phase B.1 | ✅ COMPLETE | Cards system (500 LOC), 17/17 passing |
| 5 | Phase B.2 | ⏳ NEXT | Code-tabs, tables, media, checklist (850 LOC) |
| 6 | Phase C.1-2 | Pending | Video embeds, developer embeds, versioning (600 LOC) |
| 7 | Phase C.3-4 | Pending | Navigation, file I/O, miscellaneous (850 LOC) |
| 8-9 | Phase D | Pending | Integration, deprecation, documentation |

### Milestone Tracking

```
Week 1-2   [████████████████████] Phase A: Core Directives ✅
Week 3     [████████████████████] Phase A.1: Test Infrastructure ✅
Week 4     [████████████████████] Phase B.1: Cards System ✅
Week 5     [░░░░░░░░░░░░░░░░░░░░] Phase B.2: Remaining Content
Week 6-7   [░░░░░░░░░░░░░░░░░░░░] Phase C: Specialized Directives
Week 8-9   [░░░░░░░░░░░░░░░░░░░░] Phase D: Integration
```

**Original estimate**: 9 weeks  
**Current progress**: Phase A complete (2 weeks)  
**Remaining work**: 6-7 weeks  
**Projected completion**: Mid-February 2026

---

## Open Questions

### ✅ Resolved

1. **Role migration**: Create separate RFC for roles?
   - `glossary` directive blocked without `{term}` role
   - Cross-references (`{ref}`, `{doc}`) used by multiple directives
   - **Decision**: Separate RFC (`rfc-patitas-roles-migration`), gate `glossary` until complete

2. **Rosettes integration**: Required for `code-tabs` in Phase B
   - Syntax highlighting integration
   - **Decision**: Include as Phase B dependency, Rosettes already Patitas-compatible

3. **Adapter layer**: Support unmigrated directives during transition?
   - **Decision**: Yes, implement `BengalDirectiveAdapter` for gradual migration

4. **Deprecation timeline**: How long to support mistune backend?
   - **Decision**: 2.x series with deprecation warnings, removed in 3.0

### ⏳ Open

5. **ParseContext threading**: How to handle `include` directive file access?
   - Include requires file system access
   - File system access must be sandboxed
   - Options: Pass reader function, use context protocol
   - **Status**: Design decision needed in Phase C

6. **Site context for navigation**: How to provide site structure to directives?
   - `breadcrumbs`, `siblings`, `prev-next` need site tree
   - Options: Inject via RenderContext, lazy site accessor
   - **Status**: Design decision needed in Phase C

---

## Related Documents

### RFCs

| RFC | Relationship | Status |
|-----|--------------|--------|
| [rfc-patitas-markdown-parser](rfc-patitas-markdown-parser.md) | **Prerequisite** - Core parser design | Phase 2 complete |
| rfc-patitas-roles-migration | **Blocked by this** - Role system | Not started |
| [rfc-rosettes-test-gauntlet](rfc-rosettes-test-gauntlet.md) | Related - Syntax highlighting | In progress |

### Source Code References

| File | Description |
|------|-------------|
| `bengal/directives/base.py` | Current `BengalDirective` base class |
| `bengal/directives/registry.py` | Current directive registry |
| `bengal/rendering/parsers/patitas/directives/protocol.py` | New `DirectiveHandler` protocol |
| `bengal/rendering/parsers/patitas/directives/builtins/` | Patitas directive implementations |

### External References

| Resource | Description |
|----------|-------------|
| [MyST Markdown](https://myst-parser.readthedocs.io/) | Directive syntax specification |
| [Python 3.14 Free-threading](https://docs.python.org/3.14/whatsnew/3.14.html) | Thread-safety motivation |
| [mistune Directives](https://mistune.lepture.com/en/latest/directives.html) | Current implementation basis |

---

## Testing Strategy

### Test Pyramid

```
                    ┌───────────────────┐
                    │   E2E Tests       │  Phase D: Full build tests
                    │   (10%)           │  with real documentation
                    └───────────────────┘
              ┌─────────────────────────────┐
              │   Integration Tests         │  Phase A.1: 43/43 parity tests ✅
              │   (30%)                     │  74/79 edge cases passing
              └─────────────────────────────┘
        ┌─────────────────────────────────────────┐
        │   Unit Tests (60%)                      │  Each phase: Handler tests
        │   - Options parsing                     │  - Parse tests
        │   - Contract validation                 │  - Render tests
        │   - Individual directive tests          │  - Edge cases
        └─────────────────────────────────────────┘
```

### Test Categories

| Category | Purpose | Location |
|----------|---------|----------|
| **Unit Tests** | Individual directive behavior | `tests/unit/rendering/parsers/patitas/` |
| **Parity Tests** | Bengal vs Patitas HTML output | `tests/migration/` |
| **Golden Files** | Stable reference output | `tests/migration/golden_files/` |
| **Contract Tests** | Nesting validation | `tests/unit/.../test_contracts.py` |
| **Performance Tests** | Benchmark regression | `tests/performance/` |
| **Thread-Safety Tests** | TSan verification | `tests/performance/test_concurrent.py` |

### Test Coverage Requirements

| Directive Type | Coverage Target | Notes |
|----------------|-----------------|-------|
| Core (Phase A) | 95% | Critical path |
| Content (Phase B) | 90% | High usage |
| Specialized (Phase C) | 85% | Lower usage |
| Adapters (Phase D) | 80% | Temporary code |

### CI Integration

```yaml
# .github/workflows/patitas-migration.yml
name: Patitas Migration Tests

on: [push, pull_request]

jobs:
  parity-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run parity tests
        run: pytest tests/migration/ -v

      - name: Run golden file tests
        run: pytest tests/migration/ -k golden -v

  performance-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run benchmarks
        run: pytest tests/performance/ --benchmark-json=results.json

      - name: Check regression
        run: python scripts/check_benchmark_regression.py results.json

  thread-safety:
    runs-on: ubuntu-latest
    steps:
      - name: Install Python 3.14t
        run: |
          # Install free-threaded Python

      - name: Run with TSan
        run: python3.14t -X tsansupported tests/performance/test_concurrent.py
```

---

## Implementation Notes

### Pattern: Directive Handler

All Patitas directives follow this pattern:

```python
from dataclasses import dataclass
from typing import ClassVar
from collections.abc import Sequence

from bengal.rendering.parsers.patitas.directives.contracts import DirectiveContract
from bengal.rendering.parsers.patitas.directives.options import StyledOptions
from bengal.rendering.parsers.patitas.nodes import Directive, Block
from bengal.rendering.parsers.patitas.location import SourceLocation
from bengal.rendering.parsers.patitas.stringbuilder import StringBuilder


@dataclass(frozen=True, slots=True)
class MyDirectiveOptions(StyledOptions):
    """Immutable options for the directive."""
    option_a: str | None = None
    option_b: bool = False


class MyDirective:
    """Handler for {mydirective} directive."""

    # Class attributes (protocol requirements)
    names: ClassVar[tuple[str, ...]] = ("mydirective", "alias")
    token_type: ClassVar[str] = "mydirective"
    contract: ClassVar[DirectiveContract | None] = None  # Or specific contract
    options_class: ClassVar[type[MyDirectiveOptions]] = MyDirectiveOptions

    def parse(
        self,
        name: str,                    # Which alias was used
        title: str | None,            # Text after directive name
        options: MyDirectiveOptions,  # Typed options
        content: str,                 # Raw content (rarely needed)
        children: Sequence[Block],    # Parsed children
        location: SourceLocation,     # Source file:line
    ) -> Directive:
        """Build immutable AST node."""
        return Directive(
            location=location,
            name=name,
            title=title,
            options=frozenset(self._options_to_pairs(options)),
            children=tuple(children),
        )

    def render(
        self,
        node: Directive,
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render to HTML using StringBuilder."""
        opts = dict(node.options)
        sb.append('<div class="mydirective">')
        sb.append(rendered_children)
        sb.append('</div>\n')

    def _options_to_pairs(self, options: MyDirectiveOptions) -> list[tuple[str, str]]:
        """Convert options to storable pairs."""
        pairs = []
        if options.option_a:
            pairs.append(("option_a", options.option_a))
        if options.option_b:
            pairs.append(("option_b", "true"))
        return pairs
```

### Key Differences from Bengal

| Aspect | Bengal (mistune) | Patitas |
|--------|------------------|---------|
| Attribute naming | `SCREAMING_CASE` | `snake_case` |
| Collections | `list[str]` | `tuple[str, ...]` |
| Mutability | Mutable | Frozen dataclasses |
| Options storage | `dict[str, Any]` | `frozenset[tuple[str, str]]` |
| Render output | `return str` | `sb.append(str)` |
| State | Mutable `state` | Immutable `SourceLocation` |

### Common Pitfalls

1. **Mutable defaults**: Use `None` instead of `[]` or `{}`
2. **String conversion**: Options stored as strings, convert in render
3. **HTML escaping**: Always escape user content with `html.escape()`
4. **Icon fallback**: Always handle missing icons gracefully

---

## Appendix A: Directive Migration Checklist

For each directive migration:

- [x] Create Patitas `DirectiveHandler` implementation
- [x] Port `Options` dataclass (add `frozen=True, slots=True`)
- [x] Port `Contract` if applicable
- [x] Port `render()` logic to use `StringBuilder`
- [x] Add to `DirectiveRegistry`
- [ ] Port unit tests
- [ ] Add golden file test cases
- [ ] Verify HTML output matches exactly
- [ ] Update imports in Bengal
- [ ] Mark old implementation as deprecated

---

## Appendix B: Implemented Contracts

```python
# patitas/directives/contracts.py

STEPS_CONTRACT = DirectiveContract(
    requires_children=("step",),
    allows_children=("step",),
)

STEP_CONTRACT = DirectiveContract(
    requires_parent=("steps",),
)

TAB_SET_CONTRACT = DirectiveContract(
    requires_children=("tab-item",),
    allows_children=("tab-item",),
)

TAB_ITEM_CONTRACT = DirectiveContract(
    requires_parent=("tab-set",),
)

DROPDOWN_CONTRACT = DirectiveContract()

GRID_CONTRACT = DirectiveContract(
    requires_children=("grid-item", "card"),
)

GRID_ITEM_CONTRACT = DirectiveContract(
    requires_parent=("grid",),
)

DEFINITION_LIST_CONTRACT = DirectiveContract(
    requires_children=("definition",),
    allows_children=("definition",),
)

DEFINITION_CONTRACT = DirectiveContract(
    requires_parent=("definition-list",),
)
```

---

## Appendix C: Options Classes Implemented

| Class | Extends | Fields |
|-------|---------|--------|
| `DirectiveOptions` | — | `_aliases` |
| `StyledOptions` | DirectiveOptions | `class_`, `name` |
| `AdmonitionOptions` | StyledOptions | `collapsible`, `open` |
| `CodeBlockOptions` | DirectiveOptions | `language`, `linenos`, `lineno_start`, `emphasize_lines`, `caption` |
| `ImageOptions` | StyledOptions | `width`, `height`, `alt`, `align` |
| `FigureOptions` | ImageOptions | `figwidth`, `figclass` |
| `TabSetOptions` | StyledOptions | `sync_group` |
| `TabItemOptions` | StyledOptions | `selected`, `sync` |
