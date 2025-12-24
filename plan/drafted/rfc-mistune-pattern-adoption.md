# RFC: Mistune Pattern Adoption for Bengal

**Status**: Draft  
**Created**: 2025-12-23  
**Updated**: 2025-12-23  
**Author**: AI Assistant + Lawrence Lane  
**Priority**: P2 (Medium)  
**Related**: `bengal/directives/`, `bengal/rendering/parsers/mistune/`, `tests/unit/rendering/`  
**Confidence**: 82% 🟢

---

## Executive Summary

After analyzing the mistune codebase (now in the workspace), several architectural patterns emerge that Bengal can adopt to improve testing ergonomics, performance, and extensibility. This RFC proposes three key adoptions:

1. **Text-Based Test Fixtures** — Markdown→HTML fixture files with auto-generated test cases
2. **Pipeline Hook System** — Explicit before/after hooks for extensibility without subclassing  
3. **Speedup Plugin Pattern** — Optimized fast-paths for common content patterns

**Key Insight**: Bengal already uses mistune as its markdown parser, making these patterns directly compatible. The adoption focuses on *infrastructure around* mistune, not replacing it.

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
| **Common Case Optimization** | Standard mistune parsing | Speedup patterns for prose-heavy sites |
| **Parser Caching** | Per-thread only | Global config-keyed cache for CLI commands |

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

Format:
    ## section_name

    ```````````````````````````````` example
    markdown input here
    .
    expected HTML output here
    ````````````````````````````````
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

        # Normalize for comparison (ignore whitespace differences)
        result_normalized = self._normalize_html(result)
        expected_normalized = self._normalize_html(expected)

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
        # Collapse whitespace
        html = re.sub(r">\s+<", "><", html)
        html = re.sub(r"\s+", " ", html)
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

- Fixture loader: 1 day
- Base test class: 1 day  
- Migrate 5 directives: 3 days
- Total: **5 days**

---

## Proposal 2: Pipeline Hook System

### Problem

Bengal's rendering pipeline has implicit extension points through parser plugins, but no explicit hooks for:
- Pre-processing raw content before parsing
- Post-processing AST before rendering
- Post-processing HTML after rendering
- Injecting context before template rendering

Users wanting to customize must subclass or patch, which is fragile.

### Mistune's Approach

Mistune provides three simple hook lists:

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

Add explicit hooks to `RenderingPipeline`:

```python
# bengal/rendering/pipeline/core.py (additions)

from typing import Callable, Protocol

class ContentHook(Protocol):
    """Hook called with raw content before parsing."""
    def __call__(self, content: str, page: Page, context: dict) -> str: ...

class ASTHook(Protocol):
    """Hook called with AST tokens after parsing."""
    def __call__(self, ast: list[dict], page: Page, context: dict) -> list[dict]: ...

class HTMLHook(Protocol):
    """Hook called with HTML after rendering."""
    def __call__(self, html: str, page: Page, context: dict) -> str: ...


class RenderingPipeline:
    """Coordinates the entire rendering process."""

    def __init__(self, site, ...):
        # ... existing init ...

        # Hook lists for extensibility
        self.before_parse_hooks: list[ContentHook] = []
        self.after_parse_hooks: list[ASTHook] = []
        self.after_render_hooks: list[HTMLHook] = []

        # Register default hooks
        self._register_default_hooks()

    def _register_default_hooks(self) -> None:
        """Register built-in hooks."""
        # Example: Variable substitution as a hook
        # self.before_parse_hooks.append(self._substitute_variables)
        pass

    def add_before_parse_hook(self, hook: ContentHook) -> None:
        """Add a hook to run before markdown parsing."""
        self.before_parse_hooks.append(hook)

    def add_after_parse_hook(self, hook: ASTHook) -> None:
        """Add a hook to run after AST generation."""
        self.after_parse_hooks.append(hook)

    def add_after_render_hook(self, hook: HTMLHook) -> None:
        """Add a hook to run after HTML generation."""
        self.after_render_hooks.append(hook)

    def _parse_content(self, page: Page) -> None:
        """Parse page content through markdown parser."""
        content = page.content or ""
        context = self._build_context(page)

        # HOOK: Before parse
        for hook in self.before_parse_hooks:
            content = hook(content, page, context)

        # Parse markdown
        if hasattr(self.parser, "parse_with_toc_and_context"):
            html, toc = self.parser.parse_with_toc_and_context(content, page.metadata, context)
        else:
            html = self.parser.parse(content, page.metadata)
            toc = ""

        # HOOK: After render (HTML post-processing)
        for hook in self.after_render_hooks:
            html = hook(html, page, context)

        page.parsed_ast = html
        page.toc = toc
```

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

## Proposal 3: Speedup Plugin Pattern

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

### Proposed Implementation

```python
# bengal/rendering/plugins/speedup.py

"""
Speedup plugin for prose-heavy documentation sites.

Optimizes parsing for pages with mostly plain text and few directives.
Provides measurable speedup for large documentation sites.

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
from typing import TYPE_CHECKING, Match

if TYPE_CHECKING:
    from mistune.block_parser import BlockParser
    from mistune.core import BlockState, InlineState
    from mistune.inline_parser import InlineParser
    from mistune.markdown import Markdown

# Pattern for paragraphs that definitely don't contain directives
# Starts with letter/number, doesn't contain directive markers
PLAIN_PARAGRAPH = (
    r"(?:^(?![:\s]*{|```|~~~)[^\s#\-*>+\d][^\n]*\n)+"
)

# Pattern for text runs without special inline markers
PLAIN_TEXT = r"[\s\S]+?(?=[\\<>!\[_*`~\^\$:{}]|https?:|$)"


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
    text = re.sub(r" *\n\s*", "\n", text)
    inline.process_text(text, state)
    return m.end()


def speedup(md: "Markdown") -> None:
    """
    Enable speedup optimizations for prose-heavy content.

    Registers optimized parsers for:
    - Plain paragraphs (no directive markers)
    - Plain text runs (no inline markers)

    Performance:
        Typical speedup: 10-20% for prose-heavy pages
        Minimal impact on directive-heavy pages
    """
    # Register optimized paragraph parser (runs before directive check)
    md.block.register(
        "plain_paragraph",
        PLAIN_PARAGRAPH,
        parse_plain_paragraph,
        before="paragraph",  # Try before general paragraph
    )

    # Register optimized text parser
    md.inline.register(
        "plain_text",
        PLAIN_TEXT,
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

## Proposal 4: Global Parser Cache (Bonus)

### Problem

Bengal's parser cache is per-thread, but CLI commands like `bengal validate` that don't use threading still recreate parsers repeatedly.

### Mistune's Approach

```python
# mistune/__init__.py:61-80
__cached_parsers: Dict[Tuple[...], Markdown] = {}

def markdown(text: str, ...):
    key = (escape, renderer, plugins)
    if key in __cached_parsers:
        return __cached_parsers[key](text)

    md = create_markdown(...)
    __cached_parsers[key] = md
    return md(text)
```

### Proposed Implementation

```python
# bengal/rendering/parsers/__init__.py

import threading
from functools import lru_cache

_parser_lock = threading.Lock()
_parser_cache: dict[tuple, BaseMarkdownParser] = {}

@lru_cache(maxsize=4)
def get_cached_parser(
    engine: str = "mistune",
    enable_highlighting: bool = True,
    enable_speedup: bool = False,
) -> BaseMarkdownParser:
    """
    Get a cached parser by configuration.

    Unlike thread-local caching, this provides a global cache keyed by
    configuration. Useful for CLI commands that don't use threading.

    Thread-safe via LRU cache's internal locking.
    """
    return create_markdown_parser(
        engine=engine,
        enable_highlighting=enable_highlighting,
        enable_speedup=enable_speedup,
    )
```

### Benefits

1. **CLI Performance** — Single-threaded commands don't recreate parsers
2. **Config-Aware** — Different configs get different cached instances
3. **Memory Bounded** — LRU cache limits memory usage

### Estimated Effort

- Implementation: 1 day
- Testing: 1 day
- Total: **2 days**

---

## Implementation Plan

### Phase 1: Text Fixtures (Week 1)

- [ ] Create `tests/fixtures/directives/` directory
- [ ] Implement `tests/_testing/fixtures.py` loader
- [ ] Implement `tests/_testing/directive_test_base.py`
- [ ] Migrate `dropdown` directive tests to fixtures
- [ ] Migrate `tabs` directive tests to fixtures
- [ ] Migrate `admonitions` directive tests to fixtures
- [ ] Update test documentation

### Phase 2: Pipeline Hooks (Week 2)

- [ ] Add hook type protocols to `bengal/rendering/pipeline/hooks.py`
- [ ] Add hook lists to `RenderingPipeline.__init__`
- [ ] Add `add_*_hook()` methods
- [ ] Integrate hooks into `_parse_content()`
- [ ] Migrate `escape_jinja_blocks` to hook
- [ ] Migrate `normalize_markdown_links` to hook
- [ ] Add hook documentation

### Phase 3: Speedup Plugin (Week 3)

- [ ] Create `bengal/rendering/plugins/speedup.py`
- [ ] Add `enable_speedup` to `MistuneParser`
- [ ] Add `speedup` config option
- [ ] Benchmark on 500+ page site
- [ ] Document configuration

### Phase 4: Global Cache (Week 3)

- [ ] Add `get_cached_parser()` function
- [ ] Update CLI commands to use global cache
- [ ] Verify thread safety
- [ ] Document usage patterns

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
- Support fuzzy matching for dynamic content (IDs, etc.)
- Allow `<!-- ignore: ... -->` markers for volatile sections

### Risk 2: Hook Performance Overhead

**Problem**: Hook calls add function call overhead.

**Mitigation**:
- Hooks are simple list iteration (negligible overhead)
- Empty hook lists short-circuit immediately

### Risk 3: Speedup Regex Edge Cases

**Problem**: Optimized patterns may misparse edge cases.

**Mitigation**:
- Conservative patterns that fall through to standard parser
- Extensive fixture testing for edge cases
- Disabled by default

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Directive test count | +50 fixture-based tests |
| Test file readability | Fixtures are primary documentation |
| Hook adoption | 3+ built-in transforms migrated to hooks |
| Speedup performance | 10%+ improvement on prose-heavy sites |
| Parser cache hits | 90%+ for CLI commands |

---

## References

- **Mistune codebase**: `/Users/llane/Documents/github/python/mistune/`
- **Mistune test fixtures**: `/Users/llane/Documents/github/python/mistune/tests/fixtures/`
- **Bengal directives**: `/Users/llane/Documents/github/python/bengal/bengal/directives/`
- **Bengal tests**: `/Users/llane/Documents/github/python/bengal/tests/unit/rendering/`
- **Thread-local caching**: `/Users/llane/Documents/github/python/bengal/bengal/rendering/pipeline/thread_local.py`

---

## Changelog

- 2025-12-23: Initial draft
  - Analyzed mistune codebase patterns
  - Proposed text fixture system
  - Proposed pipeline hook system  
  - Proposed speedup plugin pattern
  - Added implementation plan and testing strategy
