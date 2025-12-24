# RFC: Mistune Pattern Adoption for Bengal

**Status**: Draft  
**Created**: 2025-12-23  
**Updated**: 2025-12-23  
**Author**: AI Assistant + Lawrence Lane  
**Priority**: P2 (Medium)  
**Related**: `bengal/directives/`, `bengal/rendering/parsers/mistune/`, `tests/unit/rendering/`  
**Confidence**: 78% 🟢

---

## Executive Summary

After analyzing the mistune codebase (now in the workspace), several architectural patterns emerge that Bengal can adopt to improve testing ergonomics and extensibility. This RFC proposes two proven adoptions:

1. **Text-Based Test Fixtures** — Markdown→HTML fixture files with auto-generated test cases
2. **Pipeline Hook System** — Explicit before/after hooks aligned with mistune's design

Additionally, we propose investigating a **Speedup Plugin Pattern** pending benchmark validation.

**Key Insight**: Bengal already uses mistune as its markdown parser, making these patterns directly compatible. The adoption focuses on *infrastructure around* mistune, not replacing it.

**Note**: An earlier draft included "Global Parser Cache" as Proposal 4. This was removed after analysis showed Bengal's existing `ThreadLocalCache` in `bengal/rendering/pipeline/thread_local.py` already solves this problem — thread-local caching works for single-threaded CLI commands too (the main thread is still a thread).

---

## Current State Analysis

### What Bengal Does Well

| Area | Implementation | Quality |
|------|----------------|---------|
| **Mistune Integration** | `bengal/rendering/parsers/mistune/` | ✅ Excellent |
| **Directive System** | `bengal/directives/base.py` with contracts | ✅ Excellent |
| **Thread-Local Caching** | `bengal/rendering/pipeline/thread_local.py` | ✅ Excellent |
| **Lazy Registry** | `bengal/directives/registry.py` | ✅ Excellent |

### Gaps Identified

| Area | Current State | Opportunity |
|------|---------------|-------------|
| **Directive Testing** | Inline Python strings | Text fixtures would improve clarity |
| **Rendering Hooks** | Implicit via parser plugins | Explicit hook API would improve extensibility |
| **Common Case Optimization** | Standard mistune parsing | Speedup patterns for prose-heavy sites (needs validation) |

---

## Proposal 1: Text-Based Test Fixtures

### Problem

Current directive tests embed markdown and expected HTML as Python strings:

```python
# tests/unit/rendering/test_steps_directive.py:102-112
def test_steps_directive_basic(self, parser):
    content = """
::::{steps}
1. Step 1
2. Step 2
::::
"""
    result = parser.parse(content, {})
    assert '<div class="steps">' in result
    assert "<ol>" in result or "<li>" in result
```

Issues:
- Multi-line strings are hard to read in PRs
- Expected output scattered across assertions
- No documentation value outside tests
- Adding new test cases requires Python knowledge

### Mistune's Approach

Mistune uses text fixtures with clear input/output separation:

```text
# tests/fixtures/table.txt

## nptable

```````````````````````````````` example
First Header  | Second Header
------------- | -------------
Content Cell  | Content Cell
.
<table>
<thead>
<tr>
  <th>First Header</th>
  <th>Second Header</th>
</tr>
</thead>
...
</table>
````````````````````````````````
```

Tests auto-generated via `load_fixtures()`:

```python
# mistune/tests/__init__.py:10-23
@classmethod
def load_fixtures(cls, case_file: str) -> None:
    def attach_case(n: str, text: str, html: str) -> None:
        def method(self: "BaseTestCase") -> None:
            self.assert_case(n, text, html)
        name = "test_{}".format(n)
        setattr(cls, name, method)

    for n, text, html in fixtures.load_examples(case_file):
        attach_case(n, text, html)
```

### Proposed Implementation

#### Directory Structure

```
tests/
├── fixtures/
│   └── directives/
│       ├── admonitions.txt     # note, tip, warning, etc.
│       ├── tabs.txt            # tab-set, tab-item
│       ├── dropdown.txt        # dropdown, details
│       ├── cards.txt           # cards, card, child-cards
│       ├── steps.txt           # steps, step
│       ├── code_tabs.txt       # code-tabs
│       └── tables.txt          # list-table, data-table
└── _testing/
    └── fixtures.py             # Fixture loader
```

#### Fixture Format

```text
# tests/fixtures/directives/dropdown.txt

# Dropdown Directive

Test cases for the dropdown/details directive.

## basic_dropdown

```````````````````````````````` example
:::{dropdown} Click to expand
This is the hidden content.
:::
.
<details class="dropdown">
<summary class="dropdown__header">
<span class="dropdown__title">Click to expand</span>
</summary>
<div class="dropdown__content">
<p>This is the hidden content.</p>
</div>
</details>
````````````````````````````````

## dropdown_open

```````````````````````````````` example
:::{dropdown} Already visible
:open:

This content is visible by default.
:::
.
<details class="dropdown" open>
<summary class="dropdown__header">
<span class="dropdown__title">Already visible</span>
</summary>
<div class="dropdown__content">
<p>This content is visible by default.</p>
</div>
</details>
````````````````````````````````

## dropdown_with_icon

```````````````````````````````` example
:::{dropdown} Settings
:icon: gear

Configuration options.
:::
.
<details class="dropdown dropdown--with-icon">
<summary class="dropdown__header">
<span class="dropdown__icon"><!-- icon: gear --></span>
<span class="dropdown__title">Settings</span>
</summary>
<div class="dropdown__content">
<p>Configuration options.</p>
</div>
</details>
````````````````````````````````
```

#### Fixture Loader

```python
# tests/_testing/fixtures.py

"""
Text-based test fixture loader for directive testing.

Inspired by mistune's fixture format. Supports:
- Markdown input → HTML output pairs
- Section headers for organization
- Comments for documentation
- Dynamic content placeholders (IDs, timestamps)

Format:
    ## section_name

    ```````````````````````````````` example
    markdown input here
    .
    expected HTML output here
    ````````````````````````````````

Dynamic Content:
    Use placeholders for content that varies between runs:
    - {{ID}} matches any id="..." attribute value
    - {{TIMESTAMP}} matches ISO timestamps
    - {{UUID}} matches UUID patterns
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).parent.parent / "fixtures"

EXAMPLE_PATTERN = re.compile(
    r"^`{32} example\n([\s\S]*?)"
    r"^\.\n([\s\S]*?)"
    r"^`{32}$|^#{1,6} *(.*)$",
    flags=re.M,
)

# Patterns for dynamic content normalization
DYNAMIC_PATTERNS = {
    "{{ID}}": r'id="[^"]*"',
    "{{TIMESTAMP}}": r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
    "{{UUID}}": r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
}


def load_directive_fixtures(filename: str) -> Iterable[tuple[str, str, str]]:
    """
    Load test fixtures from a directive fixture file.

    Args:
        filename: Fixture filename (e.g., "dropdown.txt")

    Yields:
        Tuples of (test_name, markdown_input, expected_html)
    """
    filepath = ROOT / "directives" / filename
    if not filepath.exists():
        return

    content = filepath.read_text(encoding="utf-8")
    yield from parse_examples(content)


def parse_examples(text: str) -> Iterable[tuple[str, str, str]]:
    """
    Parse examples from fixture text.

    Each example has:
    - Section title (becomes test name)
    - Markdown input (before the ".")
    - Expected HTML output (after the ".")
    """
    data = EXAMPLE_PATTERN.findall(text)

    section = None
    count = 0
    for md, html, title in data:
        if title:
            count = 0
            section = title.lower().replace(" ", "_").replace("-", "_")

        if md and html:
            count += 1
            name = f"{section}_{count:03d}" if section else f"example_{count:03d}"
            # Normalize whitespace
            md = md.strip()
            html = html.strip()
            yield name, md, html


def normalize_for_comparison(expected: str, actual: str) -> tuple[str, str]:
    """
    Normalize expected and actual HTML for comparison.

    Handles dynamic content placeholders in expected HTML by converting
    them to regex patterns and replacing matches in actual HTML.

    Args:
        expected: Expected HTML (may contain {{PLACEHOLDER}} markers)
        actual: Actual rendered HTML

    Returns:
        Tuple of (normalized_expected, normalized_actual) for comparison
    """
    normalized_expected = expected
    normalized_actual = actual

    for placeholder, pattern in DYNAMIC_PATTERNS.items():
        if placeholder in expected:
            # Replace placeholder with a stable marker in expected
            normalized_expected = normalized_expected.replace(placeholder, f"__DYNAMIC_{placeholder}__")
            # Replace all matches in actual with the same stable marker
            normalized_actual = re.sub(pattern, f"__DYNAMIC_{placeholder}__", normalized_actual)

    return normalized_expected, normalized_actual
```

#### Base Test Class

```python
# tests/_testing/directive_test_base.py

"""
Base class for directive fixture tests.

Usage:
    class TestDropdownDirective(DirectiveTestCase):
        @staticmethod
        def parse(text: str) -> str:
            parser = MistuneParser()
            return parser.parse(text, {})

    TestDropdownDirective.load_fixtures("dropdown.txt")
"""

from __future__ import annotations

from abc import abstractmethod
from typing import ClassVar
from unittest import TestCase

from tests._testing.fixtures import load_directive_fixtures


class DirectiveTestCase(TestCase):
    """Base class for directive tests with fixture loading."""

    # Subclasses can override to skip specific tests
    SKIP_CASES: ClassVar[set[str]] = set()

    @classmethod
    def load_fixtures(cls, fixture_file: str) -> None:
        """Load fixtures and attach as test methods."""
        def attach_case(name: str, markdown: str, expected: str) -> None:
            def method(self: "DirectiveTestCase") -> None:
                self.assert_case(name, markdown, expected)

            method_name = f"test_{name}"
            method.__name__ = method_name
            method.__doc__ = f"Fixture test: {fixture_file} - {name}"
            setattr(cls, method_name, method)

        for name, markdown, expected in load_directive_fixtures(fixture_file):
            if name in cls.SKIP_CASES:
                continue
            attach_case(name, markdown, expected)

    @staticmethod
    @abstractmethod
    def parse(text: str) -> str:
        """Parse markdown text to HTML. Override in subclass."""
        ...

    def assert_case(self, name: str, markdown: str, expected: str) -> None:
        """Assert that parsed markdown matches expected HTML."""
        result = self.parse(markdown)

        # Normalize for comparison (handle dynamic content + whitespace)
        from tests._testing.fixtures import normalize_for_comparison
        expected_norm, result_norm = normalize_for_comparison(expected, result)

        result_normalized = self._normalize_html(result_norm)
        expected_normalized = self._normalize_html(expected_norm)

        self.assertEqual(
            result_normalized,
            expected_normalized,
            f"Fixture '{name}' failed:\n"
            f"Input:\n{markdown}\n\n"
            f"Expected:\n{expected}\n\n"
            f"Got:\n{result}"
        )

    @staticmethod
    def _normalize_html(html: str) -> str:
        """Normalize HTML for comparison."""
        import re
        # Collapse whitespace between tags only (preserve text whitespace)
        html = re.sub(r">\s+<", "><", html)
        # Normalize multiple spaces to single space
        html = re.sub(r" +", " ", html)
        return html.strip()
```

#### Example Test File

```python
# tests/unit/rendering/test_dropdown_fixtures.py

"""
Fixture-based tests for dropdown directive.

Test cases defined in: tests/fixtures/directives/dropdown.txt
"""

from bengal.rendering.parsers import MistuneParser
from tests._testing.directive_test_base import DirectiveTestCase


class TestDropdownDirective(DirectiveTestCase):
    """Dropdown directive tests from fixtures."""

    @staticmethod
    def parse(text: str) -> str:
        parser = MistuneParser()
        return parser.parse(text, {})


# Load all fixtures and generate test methods
TestDropdownDirective.load_fixtures("dropdown.txt")
```

### Benefits

1. **Clarity** — Input and output visible side-by-side
2. **Documentation** — Fixtures serve as directive examples
3. **Easy to Add** — New tests are just text, no Python needed
4. **PR Readability** — Changes to expected output are obvious
5. **Regression Detection** — Output changes are explicit in diffs

### Estimated Effort

- Fixture loader with dynamic content support: 1 day
- Base test class: 1 day  
- Pilot migration (steps directive): 1 day
- Wave 1-3 migrations: 4 days (can be done incrementally)
- Total: **7 days** (spread across 4 weeks for incremental rollout)

---

## Proposal 2: Pipeline Hook System

### Problem

Bengal's rendering pipeline has implicit extension points through parser plugins, but no explicit hooks for:
- Pre-processing raw content before parsing
- Post-processing HTML after rendering
- Injecting context before template rendering

Users wanting to customize must subclass or patch, which is fragile. The existing transforms in `bengal/rendering/pipeline/transforms.py` are called directly in the pipeline — there's no way to add custom transforms without modifying Bengal's code.

### Mistune's Approach

Mistune provides three simple hook lists with a consistent signature pattern:

```python
# mistune/markdown.py:40-44
self.before_parse_hooks: List[Callable[[Markdown, BlockState], None]] = []
self.before_render_hooks: List[Callable[[Markdown, BlockState], Any]] = []
self.after_render_hooks: List[
    Callable[[Markdown, Union[str, List[...]], BlockState], Union[str, List[...]]]
] = []
```

Used like:

```python
# mistune/toc.py:39-56
def toc_hook(md: "Markdown", state: "BlockState") -> None:
    headings = [tok for tok in state.tokens if tok["type"] == "heading"]
    state.env["toc_items"] = [normalize_toc_item(md, tok) for tok in headings]

md.before_render_hooks.append(toc_hook)
```

### Proposed Implementation

Add explicit hooks to `RenderingPipeline`, aligned with mistune's signature pattern:

```python
# bengal/rendering/pipeline/hooks.py

"""
Hook system for rendering pipeline extensibility.

Aligns with mistune's hook pattern for consistency. Hooks receive
the pipeline instance for access to parser, site, and config.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Protocol

if TYPE_CHECKING:
    from bengal.core.page import Page
    from bengal.rendering.pipeline.core import RenderingPipeline


class BeforeParseHook(Protocol):
    """
    Hook called before markdown parsing.

    Receives raw content and can modify it before parsing.
    Similar to mistune's before_parse_hooks.
    """
    def __call__(
        self,
        pipeline: "RenderingPipeline",
        content: str,
        page: "Page",
    ) -> str:
        """Return modified content."""
        ...


class AfterRenderHook(Protocol):
    """
    Hook called after HTML rendering.

    Receives rendered HTML and can modify it before template rendering.
    Similar to mistune's after_render_hooks.
    """
    def __call__(
        self,
        pipeline: "RenderingPipeline",
        html: str,
        page: "Page",
    ) -> str:
        """Return modified HTML."""
        ...
```

```python
# bengal/rendering/pipeline/core.py (additions)

from bengal.rendering.pipeline.hooks import AfterRenderHook, BeforeParseHook


class RenderingPipeline:
    """Coordinates the entire rendering process."""

    def __init__(self, site, ...):
        # ... existing init ...

        # Hook lists for extensibility (aligned with mistune pattern)
        self.before_parse_hooks: list[BeforeParseHook] = []
        self.after_render_hooks: list[AfterRenderHook] = []

        # Register built-in transforms as hooks
        self._register_default_hooks()

    def _register_default_hooks(self) -> None:
        """Register built-in transforms as hooks."""
        # Migrate existing transforms to hook pattern
        from bengal.rendering.pipeline.transforms import (
            escape_jinja_blocks,
            escape_template_syntax_in_html,
        )

        # Wrap existing transforms as hooks
        self.after_render_hooks.append(
            lambda pipeline, html, page: escape_template_syntax_in_html(html)
        )
        self.after_render_hooks.append(
            lambda pipeline, html, page: escape_jinja_blocks(html)
        )

    def add_before_parse_hook(self, hook: BeforeParseHook) -> None:
        """Add a hook to run before markdown parsing."""
        self.before_parse_hooks.append(hook)

    def add_after_render_hook(self, hook: AfterRenderHook) -> None:
        """Add a hook to run after HTML generation."""
        self.after_render_hooks.append(hook)

    def _parse_content(self, page: Page) -> None:
        """Parse page content through markdown parser."""
        content = page.content or ""

        # HOOK: Before parse (content preprocessing)
        for hook in self.before_parse_hooks:
            content = hook(self, content, page)

        # Parse markdown
        if hasattr(self.parser, "parse_with_toc_and_context"):
            html, toc = self.parser.parse_with_toc_and_context(content, page.metadata, {})
        else:
            html = self.parser.parse(content, page.metadata)
            toc = ""

        # HOOK: After render (HTML post-processing)
        for hook in self.after_render_hooks:
            html = hook(self, html, page)

        page.parsed_ast = html
        page.toc = toc
```

**Design Note**: We intentionally omit `after_parse_hooks` (AST manipulation) because Bengal's current architecture doesn't expose the raw AST — mistune renders directly to HTML. Adding AST hooks would require significant architectural changes that are out of scope for this RFC.

### Usage Example

```python
# User code or plugin

def add_reading_time(html: str, page: Page, context: dict) -> str:
    """Add reading time estimate to page."""
    words = len(page.plain_text.split())
    minutes = max(1, words // 200)
    page.metadata["reading_time"] = f"{minutes} min read"
    return html

# In config or setup
pipeline.add_after_render_hook(add_reading_time)
```

### Benefits

1. **Extensibility** — Easy customization without subclassing
2. **Composability** — Multiple hooks can be chained
3. **Clarity** — Hook points are explicit and documented
4. **Testing** — Hooks can be tested in isolation

### Estimated Effort

- Hook infrastructure: 2 days
- Migrate existing transforms to hooks: 2 days
- Documentation: 1 day
- Total: **5 days**

---

## Proposal 3: Speedup Plugin Pattern (Conditional)

> ⚠️ **This proposal requires benchmark validation before implementation.**
> The value of this optimization depends on proving that parsing is a bottleneck.

### Problem

Bengal uses standard mistune parsing for all content, but many documentation sites are prose-heavy with few directives. Parsing every paragraph through the full directive scanner is unnecessary overhead.

### Mistune's Approach

Mistune provides a `speedup` plugin that optimizes common cases:

```python
# mistune/plugins/speedup.py:35-50
def speedup(md: "Markdown") -> None:
    """Increase the speed of parsing paragraph and inline text."""
    # Optimized paragraph pattern - starts with non-punctuation
    md.block.register("paragraph", PARAGRAPH, parse_paragraph)

    # Optimized text pattern - stops at special chars
    punc = r"\\><!\[_*`~\^\$="
    text_pattern = r"[\s\S]+?(?=[" + punc + r"]|"
    # ... build pattern ...
    md.inline.register("text", text_pattern, parse_text)
```

This lets plain text bypass the full regex scanner.

### Prerequisite: Benchmark Validation

**Before implementing this proposal**, run benchmarks to validate:

1. **Is parsing a bottleneck?** Profile a 500+ page Bengal site to identify where time is spent.
2. **What's the directive density?** Bengal sites often have high directive usage (cards, steps, tabs). The speedup may be minimal.
3. **Baseline metrics**: Establish current parsing time per page.

```bash
# Run existing benchmark suite
cd benchmarks
uv run pytest test_build.py -v --benchmark-only

# Profile a real site
uv run python -m cProfile -s cumulative -m bengal build site/
```

### Proposed Implementation

```python
# bengal/rendering/plugins/speedup.py

"""
Speedup plugin for prose-heavy documentation sites.

Optimizes parsing for pages with mostly plain text and few directives.
Provides measurable speedup for large documentation sites.

IMPORTANT: Bengal uses MyST-style ::: directive syntax, not {} syntax.
The patterns below are calibrated for Bengal's directive format.

Usage:
    # In config
    [markdown]
    speedup = true

    # Or per-page in frontmatter
    ---
    markdown:
      speedup: true
    ---
"""

from __future__ import annotations

import re
import string
from typing import TYPE_CHECKING, Match

if TYPE_CHECKING:
    from mistune.block_parser import BlockParser
    from mistune.core import BlockState, InlineState
    from mistune.inline_parser import InlineParser
    from mistune.markdown import Markdown

HARD_LINEBREAK_RE = re.compile(r" *\n\s*")

# Pattern for paragraphs that definitely don't contain directives
# Bengal uses ::: for directives (MyST syntax), NOT {} like Sphinx
# Excludes lines starting with:
#   - ::: (directive open/close)
#   - ``` or ~~~ (code fences, may contain directives in MyST)
#   - # (headings)
#   - >, -, *, + (blockquotes, lists)
#   - digits (ordered lists)
#   - whitespace (indented content)
PLAIN_PARAGRAPH = (
    r"(?:^(?!:{3,}|```|~~~)[^\s#\->*+\d][^\n]*\n)+"
)

# Pattern for text runs without special inline markers
# Includes : for inline roles like {role}`text`
PLAIN_TEXT_PUNCTUATION = r"\\><!\[_*`~\^\$:{}"


def parse_plain_paragraph(
    block: "BlockParser", m: Match[str], state: "BlockState"
) -> int:
    """Fast-path parser for plain paragraphs."""
    text = m.group(0)
    state.add_paragraph(text)
    return m.end()


def parse_plain_text(
    inline: "InlineParser", m: Match[str], state: "InlineState"
) -> int:
    """Fast-path parser for plain text runs."""
    text = m.group(0)
    # Handle hard wraps
    text = HARD_LINEBREAK_RE.sub("\n", text)
    inline.process_text(text, state)
    return m.end()


def speedup(md: "Markdown") -> None:
    """
    Enable speedup optimizations for prose-heavy content.

    Registers optimized parsers for:
    - Plain paragraphs (no directive markers)
    - Plain text runs (no inline markers)

    Performance (requires validation):
        Target speedup: 10-20% for prose-heavy pages
        Expected impact on directive-heavy pages: minimal

    Note:
        This plugin is disabled by default. Enable only after
        benchmarking confirms parsing is a bottleneck for your site.
    """
    # Register optimized paragraph parser (runs before directive check)
    md.block.register(
        "plain_paragraph",
        PLAIN_PARAGRAPH,
        parse_plain_paragraph,
        before="paragraph",  # Try before general paragraph
    )

    # Build text pattern dynamically based on parser configuration
    text_pattern = r"[\s\S]+?(?=[" + PLAIN_TEXT_PUNCTUATION + r"]|"

    if "url_link" in md.inline.rules:
        text_pattern += "https?:|"

    if md.inline.hard_wrap:
        text_pattern += r" *\n|"
    else:
        text_pattern += r" {2,}\n|"

    text_pattern += r"$)"

    # Register optimized text parser
    md.inline.register(
        "plain_text",
        text_pattern,
        parse_plain_text,
        before="text",  # Try before general text
    )


def create_speedup_plugin() -> callable:
    """Factory function for the speedup plugin."""
    return speedup
```

#### Integration

```python
# bengal/rendering/parsers/mistune/__init__.py

class MistuneParser:
    def __init__(self, enable_highlighting: bool = True, enable_speedup: bool = False):
        # ... existing init ...

        if enable_speedup:
            from bengal.rendering.plugins.speedup import speedup
            plugins.append(speedup)
```

#### Configuration

```toml
# bengal.toml

[markdown]
parser = "mistune"
speedup = true  # Enable speedup optimizations
```

### Benefits

1. **Performance** — 10-20% faster parsing for prose-heavy pages
2. **Transparent** — No behavior changes for valid content
3. **Optional** — Disabled by default, enable when needed
4. **Composable** — Works with existing plugins

### Estimated Effort

- Plugin implementation: 2 days
- Integration and config: 1 day
- Benchmarking: 1 day
- Total: **4 days**

---

## Implementation Plan

### Phase 0: Benchmark Baseline (Day 1)

Before implementing optimizations, establish baseline metrics:

- [ ] Run `benchmarks/test_build.py` on small_site and large_site scenarios
- [ ] Profile Bengal documentation site build (`site/`)
- [ ] Identify actual bottlenecks (parsing vs. template rendering vs. I/O)
- [ ] Document baseline metrics in `benchmarks/BASELINE.md`

### Phase 1: Text Fixtures (Week 1)

- [ ] Create `tests/fixtures/directives/` directory
- [ ] Implement `tests/_testing/fixtures.py` loader with dynamic content support
- [ ] Implement `tests/_testing/directive_test_base.py`
- [ ] **Pilot Migration**: Convert `test_steps_directive.py` to fixtures
- [ ] Validate pytest discovers fixture-generated tests correctly
- [ ] Migrate remaining directives incrementally (see Migration Strategy below)
- [ ] Update `CONTRIBUTING.md` with fixture format documentation

### Phase 2: Pipeline Hooks (Week 2)

- [ ] Add `bengal/rendering/pipeline/hooks.py` with Protocol definitions
- [ ] Add hook lists to `RenderingPipeline.__init__`
- [ ] Add `add_before_parse_hook()` and `add_after_render_hook()` methods
- [ ] Integrate hooks into `_parse_content()`
- [ ] Wrap existing transforms (`escape_jinja_blocks`, `escape_template_syntax_in_html`) as hooks
- [ ] Keep `normalize_markdown_links` and `transform_internal_links` as direct calls (they need config)
- [ ] Add hook documentation to docstrings
- [ ] Add example custom hook in docs

### Phase 3: Speedup Plugin (Week 3 — Conditional)

**Only proceed if Phase 0 benchmarks show parsing is ≥20% of build time.**

- [ ] Create `bengal/rendering/plugins/speedup.py`
- [ ] Add `enable_speedup` parameter to `MistuneParser`
- [ ] Add `speedup` config option to `[markdown]` section
- [ ] Run benchmarks with speedup enabled
- [ ] Verify no regressions on directive-heavy content
- [ ] Document configuration and expected gains

---

## Migration Strategy

### Fixture Migration Approach

Migrate directive tests **incrementally** rather than all at once:

1. **Pilot** (Week 1): `test_steps_directive.py` — complex directive with nesting
2. **Wave 1** (Week 2): Simple directives — `dropdown`, `admonitions`
3. **Wave 2** (Week 3): Complex directives — `cards`, `tabs`, `code_tabs`
4. **Wave 3** (Week 4): Remaining — `navigation`, `data_table`, etc.

### Coexistence Strategy

During migration, both test styles can coexist:

```python
# tests/unit/rendering/test_steps_directive.py

# Original tests (keep for edge cases that need Python logic)
class TestStepsEdgeCases:
    def test_step_with_dynamic_id(self, parser):
        """Test that requires programmatic ID verification."""
        ...

# Fixture-based tests (new)
class TestStepsDirective(DirectiveTestCase):
    @staticmethod
    def parse(text: str) -> str:
        return MistuneParser().parse(text, {})

TestStepsDirective.load_fixtures("steps.txt")
```

### Test Discovery Verification

Pytest should discover fixture-generated tests automatically. Verify with:

```bash
# Should show test_steps_basic_001, test_steps_nested_002, etc.
uv run pytest tests/unit/rendering/test_steps_fixtures.py --collect-only
```

### CI Considerations

- Fixture tests will show individual test names in CI output
- Failures will show the fixture name, input, expected, and actual output
- Consider adding `pytest-sugar` for better diff visualization

---

## Testing Strategy

### Fixture Tests

```python
# Automatically generated from fixture files
def test_dropdown_basic_001(self): ...
def test_dropdown_open_001(self): ...
def test_dropdown_with_icon_001(self): ...
```

### Hook Tests

```python
def test_before_parse_hook_modifies_content():
    """Hook can modify content before parsing."""

def test_after_render_hook_modifies_html():
    """Hook can modify HTML after rendering."""

def test_hooks_execute_in_order():
    """Multiple hooks execute in registration order."""
```

### Performance Tests

```python
def test_speedup_improves_prose_performance():
    """Speedup plugin improves performance for prose-heavy content."""

def test_speedup_no_behavior_change():
    """Speedup plugin produces identical output."""
```

---

## Risk Assessment

### Risk 1: Fixture Format Complexity

**Problem**: Complex directive output may be hard to represent in fixtures.

**Mitigation**:
- Dynamic content placeholders (`{{ID}}`, `{{TIMESTAMP}}`, `{{UUID}}`) for volatile content
- Whitespace normalization for formatting differences
- Keep complex programmatic tests alongside fixtures for edge cases

**Residual Risk**: Low — fixtures can coexist with traditional tests.

### Risk 2: Hook Performance Overhead

**Problem**: Hook calls add function call overhead.

**Mitigation**:
- Hooks are simple list iteration (negligible overhead)
- Empty hook lists are O(0) — just a length check
- Profile before/after to validate no measurable impact

**Residual Risk**: Very Low — function call overhead is nanoseconds.

### Risk 3: Speedup Regex Edge Cases

**Problem**: Optimized patterns may misparse edge cases with Bengal's `:::` syntax.

**Mitigation**:
- Conservative patterns that fall through to standard parser on any uncertainty
- Extensive fixture testing for edge cases (admonitions, nested directives)
- Disabled by default — opt-in only after validation
- **Prerequisite benchmarking** ensures we only implement if there's proven value

**Residual Risk**: Medium — regex fast-paths are inherently tricky. The conservative design (fall through on doubt) limits blast radius.

### Risk 4: Test Discovery Issues

**Problem**: Dynamically generated tests via `load_fixtures()` may not be discovered by pytest.

**Mitigation**:
- Call `load_fixtures()` at module import time (after class definition)
- Verify with `pytest --collect-only` before merging
- Document the pattern clearly in CONTRIBUTING.md

**Residual Risk**: Low — pattern is proven in mistune.

---

## Success Metrics

| Metric | Target | Validation |
|--------|--------|------------|
| Directive test count | +50 fixture-based tests | `pytest --collect-only \| grep fixture` |
| Test file readability | Fixtures are primary documentation | Code review feedback |
| Hook adoption | 2+ built-in transforms migrated to hooks | Code inspection |
| Speedup performance | 10%+ improvement (if implemented) | Benchmark comparison to baseline |
| Zero regressions | All existing tests pass | CI green |

---

## References

- **Mistune codebase**: `/Users/llane/Documents/github/python/mistune/`
- **Mistune test fixtures**: `/Users/llane/Documents/github/python/mistune/tests/fixtures/`
- **Mistune fixture loader**: `/Users/llane/Documents/github/python/mistune/tests/fixtures/__init__.py`
- **Mistune hook implementation**: `/Users/llane/Documents/github/python/mistune/src/mistune/markdown.py` (lines 40-44)
- **Mistune speedup plugin**: `/Users/llane/Documents/github/python/mistune/src/mistune/plugins/speedup.py`
- **Bengal directives**: `/Users/llane/Documents/github/python/bengal/bengal/directives/`
- **Bengal directive tests**: `/Users/llane/Documents/github/python/bengal/tests/unit/rendering/`
- **Bengal transforms**: `/Users/llane/Documents/github/python/bengal/bengal/rendering/pipeline/transforms.py`
- **Bengal parser caching**: `/Users/llane/Documents/github/python/bengal/bengal/rendering/pipeline/thread_local.py`
- **Bengal benchmarks**: `/Users/llane/Documents/github/python/bengal/benchmarks/`

---

## Changelog

- 2025-12-23: Revision 2
  - **Removed Proposal 4** (Global Parser Cache) — Bengal's ThreadLocalCache already solves this
  - **Revised Proposal 2** (Pipeline Hooks) — aligned signatures with mistune, removed AST hooks
  - **Revised Proposal 3** (Speedup) — added benchmark prerequisite, fixed regex for ::: syntax
  - Added dynamic content handling to fixture loader ({{ID}}, {{TIMESTAMP}})
  - Added Migration Strategy section with incremental approach
  - Added Phase 0 (benchmark baseline) to implementation plan
  - Updated success metrics with validation methods

- 2025-12-23: Initial draft
  - Analyzed mistune codebase patterns
  - Proposed text fixture system
  - Proposed pipeline hook system  
  - Proposed speedup plugin pattern
  - Added implementation plan and testing strategy
