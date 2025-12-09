# RFC: Directive System v2 — Container Syntax, Nesting Validation, and Cohesive Architecture

**Status**: Draft (Refreshed)  
**Author**: Bengal Team  
**Created**: 2025-12-08  
**Updated**: 2025-12-09  
**Target**: Bengal 1.x  
**Branch**: `refactor/directives`  

---

## Executive Summary

Redesign Bengal's directive system with three major improvements:

1. **Named Closure Syntax** — Optional `:::{/name}` closers to eliminate fence-depth counting
2. **Nested Directive Validation** — `DirectiveContract` system catches invalid nesting at parse time
3. **Cohesive Architecture** — `BengalDirective` base class with typed options and encapsulated rendering

The current system has 20+ directives that work but suffer from:
- **Fence-depth cascade** — Adding one admonition inside a tab requires updating 5+ fence depths
- **Silent nesting failures** — `step` outside `steps` produces broken HTML with no warning
- **Duplicated boilerplate** — Same patterns repeated across 24 files

**Key Proposals**:
- **Named Closers**: `:::{/tabs}` explicitly closes `:::{tabs}`, bypassing fence counting
- **Backward Compatible**: Standard `::::` counting still works for simple cases
- **Validation**: `DirectiveContract` validates parent-child relationships
- **Architecture**: `BengalDirective` base class standardizes development

**Primary Value**: 
- **Zero fence counting** — Nest arbitrarily deep using named closers when needed
- **Helpful warnings** — Invalid nesting caught at parse time, not in broken output

---

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Named closure syntax `:::{/name}` | ❌ Not started | Primary feature - parser changes needed |
| `DirectiveContract` nesting validation | ❌ Not started | `contracts.py` - new file |
| `BengalDirective` base class | ❌ Not started | `base.py` - new file |
| `DirectiveOptions` typed options | ❌ Not started | `options.py` - new file |
| `DirectiveToken` typed tokens | ❌ Not started | `tokens.py` - new file |
| Shared utilities module | ❌ Not started | `utils.py` - extract duplicates |
| Directive migration (24 files) | ❌ Not started | Phase 3-5 of migration |
| Test coverage | 🟡 Partial | Tests exist for directives, need contract tests |

**Current Branch**: `refactor/directives` (clean working tree)

---

## 1. Problem Statement

### 1.1 Current State Analysis

**Evidence Source**: `bengal/rendering/plugins/directives/`

**Verified**: 2025-12-09 - All claims verified against current codebase.

The directive system contains 27 files (24 directive implementations + 3 infrastructure) implementing ~35 directive names:

```
admonitions.py   (10 types)    dropdown.py      (2 types)
badge.py         (2 types)     glossary.py      (1 type)
button.py        (1 type)      icon.py          (2 types)
cards.py         (5 types)     include.py       (1 type)
checklist.py     (1 type)      list_table.py    (1 type)
code_tabs.py     (2 types)     literalinclude.py (1 type)
container.py     (2 types)     marimo.py        (1 type)
data_table.py    (1 type)      navigation.py    (4 types)
rubric.py        (1 type)      steps.py         (2 types)
tabs.py          (3 types)     term.py          (1 inline)
```

### 1.2 Issues Identified

#### Issue 1: Duplicated Boilerplate (HIGH)

Every directive duplicates the same patterns:

```python
# Repeated in ALL 24 files
from bengal.utils.logger import get_logger
logger = get_logger(__name__)

# Repeated in ALL 24 files  
def __call__(self, directive, md):
    directive.register("name", self.parse)
    if md.renderer and md.renderer.NAME == "html":
        md.renderer.register("token_type", render_function)
```

**Evidence** (verified 2025-12-09):
- Logger setup duplicated: `dropdown.py:19`, `steps.py:35`, `tabs.py`, `cards.py`, etc.
- `md.renderer.NAME == "html"` check: `dropdown.py:60`, `steps.py:88`, `steps.py:208`
- `_escape_html()` patterns duplicated across multiple files

#### Issue 2: Render Functions Orphaned from Classes (MEDIUM)

```python
# Current: render function separate from class
class DropdownDirective(DirectivePlugin):
    def parse(self, block, m, state): ...
    def __call__(self, ...): ...

def render_dropdown(renderer, text, **attrs):  # Orphaned!
    ...
```

This breaks encapsulation and makes testing harder.

#### Issue 3: Untyped Options (MEDIUM)

```python
# Current: options parsed to untyped dict
options = dict(self.parse_options(m))
columns = options.get("columns", "auto")  # No validation
```

Invalid options like `:columns: banana` silently become defaults. No IDE autocomplete, no documentation of valid values.

#### Issue 4: Ad-hoc Token Dicts (LOW)

```python
# Current: no type safety
return {
    "type": "dropdown",
    "attrs": {"title": title, **options},
    "children": children,
}
```

Easy to typo keys, no IDE support.

#### Issue 5: Inconsistent Type Hints (LOW)

Some files use `Any`, some use `Match[str]`, some have no hints:

```python
# admonitions.py - no type hints
def parse(self, block, m, state):

# steps.py - partial hints  
def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
```

#### Issue 6: Fence-Depth Cascade (HIGH) ⚠️ PRIMARY PAIN POINT

**This is the primary motivation for this refactor.**

Adding nested content to container directives requires updating ALL parent fence depths:

```markdown
<!-- BEFORE: Simple tabs -->
::::{tab-set}
:::{tab-item} Python
```python
print("hello")
```
:::
::::

<!-- AFTER: Want to add ONE admonition inside a tab -->
<!-- Must update: tab-set (4→5), ALL tab-items (3→4), container closer (4→5) -->
:::::{tab-set}
::::{tab-item} Python
:::{note}
Python is great!
:::
```python
print("hello")
```
::::
:::::
```

**The cascade**: Adding 1 admonition = updating 5+ lines of fence syntax.

**Real-world pain** from `site/content/cli/debug/sandbox.md`:

```markdown
<!-- This is BROKEN - inner code fence closes outer -->
```markdown
```{tabs}
```{tab} Tab 1
Content
```
```
```

The triple backticks inside conflict with the outer code block. No warning, just broken output.

#### Issue 7: No Nested Directive Validation (HIGH)

Nested directives fail silently or produce broken HTML when used incorrectly:

```markdown
<!-- ❌ PROBLEM: step outside of steps - renders incorrectly, NO WARNING -->
:::{step}
Orphaned step content - this renders as broken HTML
:::

<!-- ❌ PROBLEM: tab-item outside tab-set - broken navigation -->
:::{tab-item} Orphaned Tab
Content appears but tab navigation is broken
:::

<!-- ❌ PROBLEM: steps with no step children - empty container -->
:::{steps}
Just text here, no actual step directives
This renders as empty HTML with no warning
:::

<!-- ❌ PROBLEM: card outside cards grid - layout breaks -->
:::{card} Orphaned Card
No grid container means broken responsive layout
:::

<!-- ❌ PROBLEM: wrong fence nesting depth - silent parse failure -->
:::{steps}
::{step}    <!-- Wrong fence count (2 instead of 3) -->
Content silently disappears
::
:::
```

**Current Behavior**: All of the above fail silently. Users discover problems only when viewing rendered output.

**Desired Behavior**: Warnings at parse time:
```
⚠️ WARNING: directive_invalid_parent
  directive: step
  parent: (root)
  expected: ["steps"]
  location: content/guide.md:45

⚠️ WARNING: directive_missing_required_children
  directive: steps  
  required: ["step"]
  found: []
  location: content/guide.md:52
```

**Evidence of Problem** (verified 2025-12-09):
- `steps.py:38-90`: `StepDirective.parse()` has no parent validation - allows orphaned steps
- `tabs.py:160-200`: `TabItemDirective` has no validation that it's inside `TabSetDirective`
- `cards.py:200-300`: `CardDirective` has no validation that it's inside `CardsDirective`
- `steps.py:109`: Documents fence-depth workaround: "Parent container uses 4 colons, nested steps use 3 colons"

**Directives with Parent-Child Relationships** (must be validated):

| Parent | Required Children | Currently Validated? |
|--------|-------------------|---------------------|
| `steps` | `step` (1+) | ❌ NO |
| `tabs` / `tab-set` | `tab-item` (1+) | ❌ NO |
| `cards` | `card` (0+) | ❌ NO |
| `code-tabs` | code blocks | ❌ NO |

| Child | Required Parent | Currently Validated? |
|-------|-----------------|---------------------|
| `step` | `steps` | ❌ NO |
| `tab-item` | `tabs` or `tab-set` | ❌ NO |
| `card` | `cards` or `grid` | ❌ NO |

### 1.3 Impact

| Issue | Files Affected | Maintenance Cost | Bug Risk |
|-------|---------------|------------------|----------|
| **Fence-depth cascade** | **All content** | **HIGH** | **HIGH** ⚠️ |
| **No nesting validation** | **8** | **HIGH** | **HIGH** ⚠️ |
| Duplicated boilerplate | 24 | HIGH | LOW |
| Orphaned render | 24 | MEDIUM | LOW |
| Untyped options | 24 | MEDIUM | MEDIUM |
| Ad-hoc tokens | 24 | LOW | LOW |
| Inconsistent types | 24 | LOW | LOW |

---

## 2. Goals and Non-Goals

### 2.1 Goals

**Primary Goals** (address main pain points):
1. **🎯 Named closure syntax** — `:::{/name}` syntax to escape fence-depth hell
2. **🎯 Nested directive validation** — Invalid nesting produces helpful warnings, not silent failures

**Secondary Goals** (improve DX and maintainability):
3. **Reduce boilerplate** — Common patterns should be automatic
4. **Type safety** — Options and tokens should be typed
5. **Encapsulation** — Render logic belongs with directive class
6. **Option validation** — Invalid options should produce helpful errors
7. **Testability** — Directives should be easy to unit test
8. **Documentation** — Options and nesting rules should be self-documenting
9. **Backward compatibility** — Existing directives should continue working during migration

### 2.2 Non-Goals

1. **Breaking mistune compatibility** — Must work with FencedDirective
2. **Removing existing syntax** — `:::` and `::::` syntax continues to work
3. **Forcing migration** — Old-style directives should still work
4. **Adding new directives** — Focus is architecture, not features
5. **Compile-time errors** — Warnings are sufficient; don't break builds

---

## 3. Proposed Design

### 3.0 Named Closure Syntax: `:::{/name}` ⭐ KEY FEATURE

#### 3.0.1 The Problem

Current MyST-style fence counting works well for shallow nesting but becomes "Fence-Depth Hell" for complex content:

```markdown
<!-- Current: Must count and increment fence depths -->
:::::{tab-set}          ← 5 colons (container)
::::{tab-item} Python   ← 4 colons (item)
:::{note}               ← 3 colons (nested content)
Important info
:::
::::
:::::

<!-- Adding ONE more level requires updating EVERYTHING above -->
```

#### 3.0.2 The Solution: Optional Named Closers

We introduce **Named Closers** (`:::{/name}`) as an **optional** alternative to fence counting.

You can mix and match: use standard fence counting for simple cases, and named closers when things get deep.

**Standard (Simple):**
```markdown
::: note
Simple content
:::
```

**Named Closure (Complex):**
```markdown
:::{tab-set}

:::{tab} Python
:::{note}
No need to count colons! The /tab explicitly closes the tab.
:::
:::{/tab}

:::{tab} JS
Content
:::{/tab}

:::{/tab-set}
```

**Benefits:**
- **Zero fence counting** — Use `:::{/name}` to close exactly what you want
- **Symmetry** — `:::{name}` opens, `:::{/name}` closes (perfect match)
- **Cognitive ease** — Matches HTML mental model (`<tag>` ... `</tag>`)
- **Tooling friendly** — Uses standard `:::` markers, preserving syntax highlighting
- **Backward compatible** — Existing fence-counting syntax continues to work perfectly

#### 3.0.3 Syntax Rules

| Style | Opener | Closer | Use Case |
|-------|--------|--------|----------|
| **Standard** | `:::{name}` | `:::` (matching length) | Simple, shallow content |
| **Named** | `:::{name}` | `:::{/name}` | Deep nesting, complex structures |

**Note on Syntax**: While `::: /name` (space) is also supported for flexibility, the recommended style is `:::{/name}` (curly braces) to strictly match the MyST opening style.

#### 3.0.4 Full Examples

**Example 1: Tabs with Named Closers**

```markdown
:::{tab-set}

:::{tab} macOS

:::{note}
Requires Homebrew
:::

```bash
brew install bengal
```

:::{/tab}

:::{tab} Linux

```bash
pip install bengal
```

:::{tip}
Use a virtual environment!
:::

:::{/tab}

:::{/tab-set}
```

**Example 2: Mixing Styles**

```markdown
<!-- Outer container uses named closers -->
:::{steps}

:::{step} Install Dependencies
<!-- Inner content uses standard simple fences -->
:::{note}
Standard 3-colon fence works fine here
:::
:::{/step}

:::{step} Configure
Content
:::{/step}

:::{/steps}
```

**Example 3: Documentation**

Documenting directives is easier because you don't need to escalate fence depths endlessly:

````markdown
## How to Use Tabs

```markdown
:::{tab-set}
:::{tab} Tab 1
Content
:::{/tab}
:::{/tab-set}
```
````

Only **3 backticks** needed for the code block if you use 3 colons inside!

#### 3.0.5 Options Syntax

Unchanged. Options immediately follow the opener.

```markdown
:::{cards}
:columns: 3

:::{card} Title
:icon: star

Content
:::{/card}
:::{/cards}
```


    Content here.
    :::{/card}
    :::{/cards}
    ```

#### 3.0.6 Parser Implementation

```python
# bengal/rendering/plugins/directives/hybrid_parser.py
import re
from typing import Any

# Standard fence pattern: :::{name}
# Matches 3+ colons, optional space, directive name (in {} or bare), optional title
FENCE_OPEN_PATTERN = re.compile(
    r'^:{3,}\s*(?:\{([a-zA-Z0-9_-]+)\}|([a-zA-Z0-9_-]+))\s*(.*)$',
    re.MULTILINE
)

# Named closer pattern: :::{/name} OR ::: /name
# Matches 3+ colons, optional space, /name (in {} or bare)
NAMED_CLOSE_PATTERN = re.compile(
    r'^:{3,}\s*(?:\{/([a-zA-Z0-9_-]+)\}|/([a-zA-Z0-9_-]+))\s*$',
    re.MULTILINE
)

# Standard closer pattern: :::
# Matches 3+ colons only
STANDARD_CLOSE_PATTERN = re.compile(
    r'^:{3,}\s*$',
    re.MULTILINE
)

def parse_directive(content: str) -> dict[str, Any]:
    """
    Parse directive with support for both standard and named closers.
    """
    # ... (simplified logic logic) ...
    
    # Algorithm:
    # 1. Scan for next fence
    # 2. If named closer (:::{/name}):
    #    - Check if it matches current directive name
    #    - If yes, close current directive (ignore nesting depth)
    # 3. If opener (:::{name}):
    #    - Increment nesting depth
    # 4. If standard closer (:::):
    #    - Decrement nesting depth
    # 5. If nesting depth == 0:
    #    - Close directive
    
    pass
```

#### 3.0.7 Migration Path

1. **Phase 1**: Update parser to recognize `:::{/name}` pattern
2. **Phase 2**: Update documentation to feature named closers for complex examples
3. **Phase 3**: No deprecation needed (both syntaxes valid)

#### 3.0.8 Visual Metaphor

Named closers bring the **HTML tag metaphor** to Markdown:

```
:::{tabs}           ← <tabs>
  :::{tab}          ← <tab>
  :::{/tab}         ← </tab>
:::{/tabs}          ← </tabs>
```

---

### 3.1 Architecture Overview

```
bengal/rendering/plugins/directives/
├── __init__.py              # Public API, registry
├── base.py                  # BengalDirective base class
├── contracts.py             # DirectiveContract nesting validation ⭐ NEW
├── options.py               # DirectiveOptions typed options
├── tokens.py                # DirectiveToken typed tokens
├── utils.py                 # Shared utilities (escape_html, etc.)
├── registry.py              # Directive registration helpers
│
├── # Individual directives (migrated)
├── admonitions.py
├── dropdown.py
├── cards/                   # Complex directives become packages
│   ├── __init__.py
│   ├── options.py
│   ├── cards_grid.py
│   ├── card.py
│   └── child_cards.py
└── ...
```

**Key New Component**: `contracts.py` defines `DirectiveContract` which specifies valid parent-child relationships. The base class validates these contracts at parse time and emits warnings for violations.

### 3.2 Core Components

#### 3.2.1 DirectiveToken — Typed Token Structure

```python
# bengal/rendering/plugins/directives/tokens.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DirectiveToken:
    """
    Typed AST token for directives.

    Replaces ad-hoc dicts like:
        {"type": "dropdown", "attrs": {...}, "children": [...]}

    Benefits:
        - Type checking catches typos
        - IDE autocomplete for fields
        - Consistent structure across all directives

    Example:
        token = DirectiveToken(
            type="dropdown",
            attrs={"title": "Details", "open": True},
            children=parsed_children,
        )
        return token.to_dict()  # For mistune compatibility
    """
    type: str
    attrs: dict[str, Any] = field(default_factory=dict)
    children: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for mistune AST compatibility."""
        return {
            "type": self.type,
            "attrs": self.attrs,
            "children": self.children,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DirectiveToken:
        """Create from dict (for testing)."""
        return cls(
            type=data["type"],
            attrs=data.get("attrs", {}),
            children=data.get("children", []),
        )
```

#### 3.2.2 DirectiveOptions — Typed Option Parsing

```python
# bengal/rendering/plugins/directives/options.py
from __future__ import annotations

from dataclasses import dataclass, fields, field
from typing import Any, ClassVar, get_type_hints, get_origin, get_args

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DirectiveOptions:
    """
    Base class for typed directive options.

    Subclass with typed fields to get automatic:
    - Parsing from :option: syntax
    - Type coercion (str -> bool, str -> int, str -> list)
    - Validation (via __post_init__)
    - Default values
    - Self-documentation

    Example:
        @dataclass
        class DropdownOptions(DirectiveOptions):
            open: bool = False
            css_class: str = ""

            _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}

        # Usage:
        opts = DropdownOptions.from_raw({"open": "true", "class": "my-class"})
        # opts.open = True
        # opts.css_class = "my-class"
    """

    # Override in subclass to map :option-name: to field_name
    # e.g., {"class": "css_class"} maps :class: to self.css_class
    _field_aliases: ClassVar[dict[str, str]] = {}

    # Override to specify allowed values for string fields
    # e.g., {"gap": ["small", "medium", "large"]}
    _allowed_values: ClassVar[dict[str, list[str]]] = {}

    @classmethod
    def from_raw(cls, raw_options: dict[str, str]) -> DirectiveOptions:
        """
        Parse raw string options into typed instance.

        Handles:
        - Field aliases (:class: -> css_class)
        - Type coercion (str -> bool, int, list)
        - Validation via _allowed_values and __post_init__
        - Unknown options are logged and ignored

        Args:
            raw_options: Dict from mistune's parse_options()

        Returns:
            Typed options instance with defaults applied
        """
        kwargs: dict[str, Any] = {}
        hints = get_type_hints(cls)
        known_fields = {f.name for f in fields(cls) if not f.name.startswith("_")}

        for raw_name, raw_value in raw_options.items():
            # Resolve alias
            field_name = cls._field_aliases.get(raw_name, raw_name.replace("-", "_"))

            if field_name not in known_fields:
                logger.debug(
                    "directive_unknown_option",
                    option=raw_name,
                    directive=cls.__name__,
                )
                continue

            # Get target type
            target_type = hints.get(field_name, str)

            # Coerce value
            try:
                coerced = cls._coerce_value(raw_value, target_type)

                # Validate allowed values
                if field_name in cls._allowed_values:
                    allowed = cls._allowed_values[field_name]
                    if coerced not in allowed:
                        logger.warning(
                            "directive_invalid_option_value",
                            option=raw_name,
                            value=raw_value,
                            allowed=allowed,
                            directive=cls.__name__,
                        )
                        continue  # Skip invalid, use default

                kwargs[field_name] = coerced

            except (ValueError, TypeError) as e:
                logger.warning(
                    "directive_option_coerce_failed",
                    option=raw_name,
                    value=raw_value,
                    target_type=str(target_type),
                    error=str(e),
                )

        return cls(**kwargs)

    @classmethod
    def _coerce_value(cls, value: str, target_type: type) -> Any:
        """
        Coerce string value to target type.

        Supports:
        - bool: "true", "1", "yes", "" -> True; others -> False
        - int: numeric strings
        - list[str]: comma-separated values
        - str: pass-through
        """
        # Handle Optional types
        origin = get_origin(target_type)
        if origin is type(None) or (origin and type(None) in get_args(target_type)):
            # Optional type - extract inner type
            args = get_args(target_type)
            target_type = next((a for a in args if a is not type(None)), str)

        if target_type == bool:
            return value.lower() in ("true", "1", "yes", "")

        if target_type == int:
            return int(value) if value.lstrip("-").isdigit() else 0

        if target_type == float:
            try:
                return float(value)
            except ValueError:
                return 0.0

        if origin == list or target_type == list:
            return [v.strip() for v in value.split(",") if v.strip()]

        return value


# Pre-built option classes for common patterns

@dataclass
class StyledOptions(DirectiveOptions):
    """Common options for styled directives."""
    css_class: str = ""

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


@dataclass  
class ContainerOptions(StyledOptions):
    """Options for container-style directives (cards, tabs, etc.)."""
    columns: str = "auto"
    gap: str = "medium"
    style: str = "default"

    _allowed_values: ClassVar[dict[str, list[str]]] = {
        "gap": ["small", "medium", "large"],
        "style": ["default", "minimal", "bordered"],
    }
```

#### 3.2.3 BengalDirective — Base Class

```python
# bengal/rendering/plugins/directives/base.py
from __future__ import annotations

from abc import abstractmethod
from re import Match
from typing import Any, ClassVar

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

from .options import DirectiveOptions
from .tokens import DirectiveToken


class BengalDirective(DirectivePlugin):
    """
    Base class for Bengal directives.

    Provides:
    - Automatic directive and renderer registration
    - Typed option parsing via OPTIONS_CLASS
    - Shared utility methods (escape_html, build_class_string)
    - Consistent type hints
    - Logger setup

    Subclass Requirements:
    - NAMES: list of directive names to register
    - TOKEN_TYPE: token type string for AST
    - OPTIONS_CLASS: (optional) typed options dataclass
    - parse_directive(): build token from parsed components
    - render(): render token to HTML

    Example:
        class DropdownDirective(BengalDirective):
            NAMES = ["dropdown", "details"]
            TOKEN_TYPE = "dropdown"
            OPTIONS_CLASS = DropdownOptions

            def parse_directive(self, title, options, content, children, state):
                return DirectiveToken(
                    type=self.TOKEN_TYPE,
                    attrs={"title": title or "Details", "open": options.open},
                    children=children,
                )

            def render(self, renderer, text, **attrs):
                title = attrs.get("title", "Details")
                is_open = attrs.get("open", False)
                return f'<details{" open" if is_open else ""}><summary>{title}</summary>{text}</details>'
    """

    # -------------------------------------------------------------------------
    # Class Attributes (override in subclass)
    # -------------------------------------------------------------------------

    # Directive names to register (e.g., ["dropdown", "details"])
    NAMES: ClassVar[list[str]]

    # Token type for AST (e.g., "dropdown")
    TOKEN_TYPE: ClassVar[str]

    # Typed options class (defaults to base DirectiveOptions)
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = DirectiveOptions

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self) -> None:
        super().__init__()
        self.logger = get_logger(self.__class__.__module__)

    # -------------------------------------------------------------------------
    # Parse Flow (template method pattern)
    # -------------------------------------------------------------------------

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
        """
        Standard parse flow - delegates to parse_directive().

        Override parse_directive() instead of this method for most cases.
        Override this method only if you need custom pre/post processing.
        """
        # Extract components using mistune helpers
        title = self.parse_title(m)
        raw_options = dict(self.parse_options(m))
        content = self.parse_content(m)
        children = self.parse_tokens(block, content, state)

        # Parse options into typed instance
        options = self.OPTIONS_CLASS.from_raw(raw_options)

        # Delegate to subclass
        token = self.parse_directive(title, options, content, children, state)

        # Return dict for mistune compatibility
        if isinstance(token, DirectiveToken):
            return token.to_dict()
        return token  # Allow returning raw dict for flexibility

    @abstractmethod
    def parse_directive(
        self,
        title: str,
        options: DirectiveOptions,
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken | dict[str, Any]:
        """
        Build the token from parsed components.

        Override this method to implement directive-specific logic.

        Args:
            title: Directive title (text after directive name)
            options: Parsed and typed options
            content: Raw content string (rarely needed, use children)
            children: Parsed nested content tokens
            state: Parser state (for accessing heading levels, etc.)

        Returns:
            DirectiveToken or dict for AST
        """
        ...

    # -------------------------------------------------------------------------
    # Render (override in subclass)
    # -------------------------------------------------------------------------

    @abstractmethod
    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """
        Render token to HTML.

        Args:
            renderer: Mistune renderer instance
            text: Pre-rendered children HTML
            **attrs: Token attributes

        Returns:
            HTML string
        """
        ...

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    def __call__(self, directive: Any, md: Any) -> None:
        """
        Register directive names and renderer.

        Override only if you need custom registration logic
        (e.g., multiple token types like AdmonitionDirective).
        """
        for name in self.NAMES:
            directive.register(name, self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register(self.TOKEN_TYPE, self.render)

    # -------------------------------------------------------------------------
    # Shared Utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def escape_html(text: str) -> str:
        """
        Escape HTML special characters for use in attributes.

        Escapes: & < > " '
        """
        if not text:
            return ""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

    @staticmethod
    def build_class_string(*classes: str) -> str:
        """
        Build CSS class string from multiple class sources.

        Filters out empty strings and joins with space.

        Example:
            build_class_string("dropdown", "", "my-class")
            # Returns: "dropdown my-class"
        """
        return " ".join(c.strip() for c in classes if c and c.strip())

    @staticmethod
    def bool_attr(name: str, value: bool) -> str:
        """
        Return HTML boolean attribute string.

        Example:
            bool_attr("open", True)   # Returns: " open"
            bool_attr("open", False)  # Returns: ""
        """
        return f" {name}" if value else ""
```

#### 3.2.4 Shared Utilities

```python
# bengal/rendering/plugins/directives/utils.py
from __future__ import annotations

from typing import Any

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def build_class_string(*classes: str) -> str:
    """Build CSS class string from multiple sources."""
    return " ".join(c.strip() for c in classes if c and c.strip())


def bool_attr(name: str, value: bool) -> str:
    """Return HTML boolean attribute string."""
    return f" {name}" if value else ""


def data_attrs(**attrs: Any) -> str:
    """
    Build data-* attribute string.

    Example:
        data_attrs(columns="auto", gap="medium")
        # Returns: 'data-columns="auto" data-gap="medium"'
    """
    parts = []
    for key, value in attrs.items():
        if value is not None and value != "":
            key_str = key.replace("_", "-")
            parts.append(f'data-{key_str}="{escape_html(str(value))}"')
    return " ".join(parts)
```

#### 3.2.5 DirectiveContract — Nested Directive Validation ⭐ KEY FEATURE

```python
# bengal/rendering/plugins/directives/contracts.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DirectiveContract:
    """
    Defines valid nesting relationships for a directive.

    This is the KEY FEATURE that solves the nested directive validation problem.
    Contracts are checked at parse time to catch invalid nesting early.

    Attributes:
        requires_parent: This directive MUST be inside one of these parent types.
                        Empty list means can appear anywhere (root-level OK).

        requires_children: This directive MUST contain at least one of these types.
                          Empty list means no required children.

        allowed_children: Only these child types are allowed (whitelist).
                         Empty list means any children allowed.

        disallowed_children: These child types are NOT allowed (blacklist).
                            Takes precedence over allowed_children.

        min_children: Minimum count of required_children types.

        max_children: Maximum children (0 = unlimited).

    Example - StepDirective (must be inside steps):
        CONTRACT = DirectiveContract(
            requires_parent=["steps"],
        )

    Example - StepsDirective (must contain steps):
        CONTRACT = DirectiveContract(
            requires_children=["step"],
            min_children=1,
            allowed_children=["step"],
        )

    Example - TabSetDirective (tabs with items):
        CONTRACT = DirectiveContract(
            requires_children=["tab_item"],
            min_children=1,
        )
    """

    # Parent requirements
    requires_parent: tuple[str, ...] = ()

    # Child requirements
    requires_children: tuple[str, ...] = ()
    min_children: int = 0
    max_children: int = 0  # 0 = unlimited

    # Child filtering
    allowed_children: tuple[str, ...] = ()  # Empty = allow all
    disallowed_children: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Convert any lists to tuples for hashability."""
        # Handled by frozen=True, but validate min_children
        if self.min_children < 0:
            raise ValueError("min_children must be >= 0")
        if self.max_children < 0:
            raise ValueError("max_children must be >= 0")

    @property
    def has_parent_requirement(self) -> bool:
        """True if this directive requires a specific parent."""
        return len(self.requires_parent) > 0

    @property
    def has_child_requirement(self) -> bool:
        """True if this directive requires specific children."""
        return len(self.requires_children) > 0 or self.min_children > 0


@dataclass
class ContractViolation:
    """
    Represents a contract violation found during parsing.

    Collected violations can be:
    - Logged as warnings (default)
    - Raised as errors (strict mode)
    - Reported in health checks
    """
    directive: str
    violation_type: str  # "invalid_parent", "missing_children", "invalid_children", etc.
    message: str
    expected: list[str] | int | None = None
    found: list[str] | str | int | None = None
    location: str | None = None  # e.g., "content/guide.md:45"

    def to_log_dict(self) -> dict[str, Any]:
        """Convert to structured log format."""
        result = {
            "directive": self.directive,
            "violation": self.violation_type,
            "message": self.message,
        }
        if self.expected is not None:
            result["expected"] = self.expected
        if self.found is not None:
            result["found"] = self.found
        if self.location:
            result["location"] = self.location
        return result


class ContractValidator:
    """
    Validates directive nesting against contracts.

    Used by BengalDirective.parse() to check:
    1. Parent context is valid (if requires_parent specified)
    2. Children meet requirements (if requires_children specified)
    3. Children types are allowed (if allowed_children specified)

    Example usage in BengalDirective:
        def parse(self, block, m, state):
            # ... parse content ...

            # Validate parent
            if self.CONTRACT:
                parent_type = self._get_parent_type(state)
                violations = ContractValidator.validate_parent(
                    self.CONTRACT, self.TOKEN_TYPE, parent_type
                )
                for v in violations:
                    self.logger.warning(v.violation_type, **v.to_log_dict())

            # ... parse children ...

            # Validate children
            if self.CONTRACT:
                violations = ContractValidator.validate_children(
                    self.CONTRACT, self.TOKEN_TYPE, children
                )
                for v in violations:
                    self.logger.warning(v.violation_type, **v.to_log_dict())
    """

    @staticmethod
    def validate_parent(
        contract: DirectiveContract,
        directive_type: str,
        parent_type: str | None,
        location: str | None = None,
    ) -> list[ContractViolation]:
        """
        Validate that the directive is inside a valid parent.

        Args:
            contract: The directive's contract
            directive_type: The directive being validated (e.g., "step")
            parent_type: The parent directive type (None if at root)
            location: Source location for error messages

        Returns:
            List of violations (empty if valid)
        """
        violations = []

        if contract.requires_parent:
            if parent_type not in contract.requires_parent:
                violations.append(ContractViolation(
                    directive=directive_type,
                    violation_type="directive_invalid_parent",
                    message=f"{directive_type} must be inside {contract.requires_parent}, found: {parent_type or '(root)'}",
                    expected=list(contract.requires_parent),
                    found=parent_type or "(root)",
                    location=location,
                ))

        return violations

    @staticmethod
    def validate_children(
        contract: DirectiveContract,
        directive_type: str,
        children: list[dict[str, Any]],
        location: str | None = None,
    ) -> list[ContractViolation]:
        """
        Validate that children meet contract requirements.

        Args:
            contract: The directive's contract
            directive_type: The directive being validated (e.g., "steps")
            children: Parsed child tokens
            location: Source location for error messages

        Returns:
            List of violations (empty if valid)
        """
        violations = []

        # Extract child types
        child_types = [
            c.get("type") for c in children
            if isinstance(c, dict) and c.get("type")
        ]

        # Check required children exist
        if contract.requires_children:
            required_found = [t for t in child_types if t in contract.requires_children]

            if not required_found:
                violations.append(ContractViolation(
                    directive=directive_type,
                    violation_type="directive_missing_required_children",
                    message=f"{directive_type} requires at least one of {contract.requires_children}",
                    expected=list(contract.requires_children),
                    found=child_types,
                    location=location,
                ))
            elif len(required_found) < contract.min_children:
                violations.append(ContractViolation(
                    directive=directive_type,
                    violation_type="directive_insufficient_children",
                    message=f"{directive_type} requires at least {contract.min_children} {contract.requires_children}, found {len(required_found)}",
                    expected=contract.min_children,
                    found=len(required_found),
                    location=location,
                ))

        # Check max children
        if contract.max_children > 0 and len(child_types) > contract.max_children:
            violations.append(ContractViolation(
                directive=directive_type,
                violation_type="directive_too_many_children",
                message=f"{directive_type} allows max {contract.max_children} children, found {len(child_types)}",
                expected=contract.max_children,
                found=len(child_types),
                location=location,
            ))

        # Check allowed children (whitelist)
        if contract.allowed_children:
            invalid = [t for t in child_types if t and t not in contract.allowed_children]
            if invalid:
                violations.append(ContractViolation(
                    directive=directive_type,
                    violation_type="directive_invalid_child_types",
                    message=f"{directive_type} does not allow children of type {invalid}",
                    expected=list(contract.allowed_children),
                    found=invalid,
                    location=location,
                ))

        # Check disallowed children (blacklist)
        if contract.disallowed_children:
            invalid = [t for t in child_types if t in contract.disallowed_children]
            if invalid:
                violations.append(ContractViolation(
                    directive=directive_type,
                    violation_type="directive_disallowed_child_types",
                    message=f"{directive_type} does not allow children of type {invalid}",
                    expected=f"not {list(contract.disallowed_children)}",
                    found=invalid,
                    location=location,
                ))

        return violations


# =============================================================================
# Pre-defined Contracts for Bengal Directives
# =============================================================================

# Steps directives
STEPS_CONTRACT = DirectiveContract(
    requires_children=("step",),
    min_children=1,
    allowed_children=("step",),
)

STEP_CONTRACT = DirectiveContract(
    requires_parent=("steps",),
)

# Tabs directives  
TAB_SET_CONTRACT = DirectiveContract(
    requires_children=("tab_item",),
    min_children=1,
)

TAB_ITEM_CONTRACT = DirectiveContract(
    requires_parent=("tab_set", "legacy_tabs"),
)

# Cards directives
CARDS_CONTRACT = DirectiveContract(
    # Cards can have card children, but they're optional (child-cards auto-generates)
    allowed_children=("card",),
)

CARD_CONTRACT = DirectiveContract(
    requires_parent=("cards_grid",),
)

# Code tabs
CODE_TABS_CONTRACT = DirectiveContract(
    # Requires code block children
    min_children=1,
)
```

#### 3.2.6 Updated BengalDirective with Contract Validation

The base class now validates contracts automatically:

```python
# bengal/rendering/plugins/directives/base.py (updated with contracts)
from __future__ import annotations

from abc import abstractmethod
from re import Match
from typing import Any, ClassVar

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

from .contracts import DirectiveContract, ContractValidator
from .options import DirectiveOptions
from .tokens import DirectiveToken


class BengalDirective(DirectivePlugin):
    """
    Base class for Bengal directives with nesting validation.

    NEW: Supports DirectiveContract for validating parent-child relationships.

    Subclass Requirements:
    - NAMES: list of directive names to register
    - TOKEN_TYPE: token type string for AST
    - OPTIONS_CLASS: (optional) typed options dataclass
    - CONTRACT: (optional) nesting validation contract ⭐ NEW
    - parse_directive(): build token from parsed components
    - render(): render token to HTML

    Example with contract:
        class StepDirective(BengalDirective):
            NAMES = ["step"]
            TOKEN_TYPE = "step"
            CONTRACT = DirectiveContract(requires_parent=["steps"])

            def parse_directive(self, ...): ...
            def render(self, ...): ...
    """

    # -------------------------------------------------------------------------
    # Class Attributes (override in subclass)
    # -------------------------------------------------------------------------

    NAMES: ClassVar[list[str]]
    TOKEN_TYPE: ClassVar[str]
    OPTIONS_CLASS: ClassVar[type[DirectiveOptions]] = DirectiveOptions

    # NEW: Contract for nesting validation (optional)
    CONTRACT: ClassVar[DirectiveContract | None] = None

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __init__(self) -> None:
        super().__init__()
        self.logger = get_logger(self.__class__.__module__)

    # -------------------------------------------------------------------------
    # Parse Flow with Contract Validation
    # -------------------------------------------------------------------------

    def parse(self, block: Any, m: Match[str], state: Any) -> dict[str, Any]:
        """
        Standard parse flow with contract validation.

        Validation steps:
        1. Validate parent context (if CONTRACT.requires_parent)
        2. Parse content and children
        3. Validate children (if CONTRACT.requires_children)
        """
        # Get source location for error messages
        location = self._get_source_location(state)

        # STEP 1: Validate parent context BEFORE parsing
        if self.CONTRACT and self.CONTRACT.has_parent_requirement:
            parent_type = self._get_parent_directive_type(state)
            violations = ContractValidator.validate_parent(
                self.CONTRACT, self.TOKEN_TYPE, parent_type, location
            )
            for v in violations:
                self.logger.warning(v.violation_type, **v.to_log_dict())

        # STEP 2: Parse content
        title = self.parse_title(m)
        raw_options = dict(self.parse_options(m))
        content = self.parse_content(m)
        children = self.parse_tokens(block, content, state)

        # Parse options into typed instance
        options = self.OPTIONS_CLASS.from_raw(raw_options)

        # STEP 3: Validate children AFTER parsing
        if self.CONTRACT and self.CONTRACT.has_child_requirement:
            # Convert children to list of dicts for validation
            child_dicts = [
                c if isinstance(c, dict) else {"type": "unknown"}
                for c in children
            ]
            violations = ContractValidator.validate_children(
                self.CONTRACT, self.TOKEN_TYPE, child_dicts, location
            )
            for v in violations:
                self.logger.warning(v.violation_type, **v.to_log_dict())

        # Build token via subclass
        token = self.parse_directive(title, options, content, children, state)

        # Return dict for mistune compatibility
        if isinstance(token, DirectiveToken):
            return token.to_dict()
        return token

    def _get_parent_directive_type(self, state: Any) -> str | None:
        """
        Extract parent directive type from parser state.

        Mistune tracks directive nesting in state. This method extracts
        the immediate parent directive type for contract validation.

        Returns:
            Parent directive type (e.g., "steps") or None if at root
        """
        # Check for Bengal's directive stack in state
        directive_stack = getattr(state, "_directive_stack", None)
        if directive_stack and len(directive_stack) > 0:
            return directive_stack[-1]

        # Fallback: check state.env for parent tracking
        env = getattr(state, "env", {})
        if isinstance(env, dict):
            stack = env.get("directive_stack", [])
            if stack:
                return stack[-1]

        return None

    def _get_source_location(self, state: Any) -> str | None:
        """
        Extract source file location from parser state.

        Returns:
            Location string like "content/guide.md:45" or None
        """
        env = getattr(state, "env", {})
        if isinstance(env, dict):
            source_file = env.get("source_file", "")
            # Line number tracking would require mistune modifications
            if source_file:
                return source_file
        return None

    @abstractmethod
    def parse_directive(
        self,
        title: str,
        options: DirectiveOptions,
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken | dict[str, Any]:
        """Build the token from parsed components."""
        ...

    @abstractmethod
    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        """Render token to HTML."""
        ...

    def __call__(self, directive: Any, md: Any) -> None:
        """Register directive names and renderer."""
        for name in self.NAMES:
            directive.register(name, self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register(self.TOKEN_TYPE, self.render)

    # -------------------------------------------------------------------------
    # Shared Utilities (unchanged)
    # -------------------------------------------------------------------------

    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML special characters for use in attributes."""
        if not text:
            return ""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

    @staticmethod
    def build_class_string(*classes: str) -> str:
        """Build CSS class string from multiple class sources."""
        return " ".join(c.strip() for c in classes if c and c.strip())

    @staticmethod
    def bool_attr(name: str, value: bool) -> str:
        """Return HTML boolean attribute string."""
        return f" {name}" if value else ""
```

### 3.3 Example Migration: DropdownDirective

#### Before (Current Implementation)

```python
# bengal/rendering/plugins/directives/dropdown.py (current)
from __future__ import annotations

from mistune.directives import DirectivePlugin

from bengal.utils.logger import get_logger

__all__ = ["DropdownDirective", "render_dropdown"]

logger = get_logger(__name__)


class DropdownDirective(DirectivePlugin):
    DIRECTIVE_NAMES = ["dropdown", "details"]

    def parse(self, block, m, state):
        title = self.parse_title(m)
        if not title:
            title = "Details"
        options = dict(self.parse_options(m))
        content = self.parse_content(m)
        children = self.parse_tokens(block, content, state)
        return {"type": "dropdown", "attrs": {"title": title, **options}, "children": children}

    def __call__(self, directive, md):
        directive.register("dropdown", self.parse)
        directive.register("details", self.parse)
        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("dropdown", render_dropdown)


def render_dropdown(renderer, text, **attrs):
    title = attrs.get("title", "Details")
    is_open = attrs.get("open", "").lower() in ("true", "1", "yes")
    open_attr = " open" if is_open else ""
    html = (
        f'<details class="dropdown"{open_attr}>\n'
        f"  <summary>{title}</summary>\n"
        f'  <div class="dropdown-content">\n'
        f"{text}"
        f"  </div>\n"
        f"</details>\n"
    )
    return html
```

#### After (Migrated)

```python
# bengal/rendering/plugins/directives/dropdown.py (migrated)
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from .base import BengalDirective
from .options import DirectiveOptions
from .tokens import DirectiveToken

__all__ = ["DropdownDirective", "DropdownOptions"]


@dataclass
class DropdownOptions(DirectiveOptions):
    """
    Options for dropdown directive.

    Attributes:
        open: Whether dropdown is initially open
        css_class: Additional CSS classes

    Example:
        :::{dropdown} My Title
        :open: true
        :class: my-custom-class
        Content here
        :::
    """
    open: bool = False
    css_class: str = ""

    _field_aliases: ClassVar[dict[str, str]] = {"class": "css_class"}


class DropdownDirective(BengalDirective):
    """
    Collapsible dropdown directive with markdown support.

    Syntax:
        :::{dropdown} Title
        :open: true
        :class: custom-class

        Content with **markdown**, code blocks, etc.
        :::

    Aliases:
        - dropdown
        - details (HTML5 semantic alias)
    """

    NAMES = ["dropdown", "details"]
    TOKEN_TYPE = "dropdown"
    OPTIONS_CLASS = DropdownOptions

    def parse_directive(
        self,
        title: str,
        options: DropdownOptions,
        content: str,
        children: list[Any],
        state: Any,
    ) -> DirectiveToken:
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "title": title or "Details",
                "open": options.open,
                "css_class": options.css_class,
            },
            children=children,
        )

    def render(self, renderer: Any, text: str, **attrs: Any) -> str:
        title = attrs.get("title", "Details")
        is_open = attrs.get("open", False)
        css_class = self.build_class_string("dropdown", attrs.get("css_class", ""))

        return (
            f'<details class="{css_class}"{self.bool_attr("open", is_open)}>\n'
            f"  <summary>{self.escape_html(title)}</summary>\n"
            f'  <div class="dropdown-content">\n'
            f"{text}"
            f"  </div>\n"
            f"</details>\n"
        )
```

### 3.4 Complex Example: CardsDirective

For complex directives with multiple classes, organize as a package:

```
bengal/rendering/plugins/directives/cards/
├── __init__.py          # Public API
├── options.py           # CardsOptions, CardOptions, etc.
├── cards_grid.py        # CardsDirective
├── card.py              # CardDirective
├── child_cards.py       # ChildCardsDirective
├── grid_compat.py       # GridDirective, GridItemCardDirective
└── utils.py             # Card-specific helpers
```

---

## 4. Migration Strategy

### 4.1 Phased Approach

```
Phase 1: Foundation (Week 1)
├── Add base.py, options.py, tokens.py, utils.py, contracts.py
├── Add container_parser.py for [[ ]] syntax
├── Write comprehensive tests for base classes
└── No changes to existing directives

Phase 2: Container Syntax (Week 1-2) ⭐ HIGH PRIORITY
├── Implement [[ ]] parser for container directives
├── Add support for: tabs/tab-set, steps, cards, grid
├── Test nested container scenarios
├── Both syntaxes work side-by-side

Phase 3: Simple Directives (Week 2)
├── Migrate: dropdown, container, rubric, button, badge
├── These have simple options and rendering
└── Validate backward compatibility

Phase 4: Medium Directives (Week 2-3)
├── Migrate: admonitions, checklist, glossary, icon
├── AdmonitionDirective needs custom __call__ (multiple token types)
└── Validate nested directive support

Phase 5: Complex Directives (Week 3-4)
├── Migrate: cards, tabs, steps, navigation
├── Add DirectiveContract validation
├── Consider package structure for cards
├── Validate all edge cases

Phase 6: Cleanup (Week 4)
├── Remove duplicated utilities
├── Update __init__.py exports
├── Update documentation (prefer [[ ]] for containers)
└── Archive old implementations
```

### 4.2 Backward Compatibility

During migration:

1. **Old-style directives continue working** — `DirectivePlugin` subclasses unchanged
2. **New base class is optional** — Migration can be gradual
3. **Token format unchanged** — Output dicts identical to before
4. **No syntax changes** — User markdown unchanged

### 4.3 Testing Strategy

```python
# tests/unit/rendering/directives/test_base.py

def test_directive_token_to_dict():
    """DirectiveToken produces correct dict format."""
    token = DirectiveToken(
        type="dropdown",
        attrs={"title": "Test", "open": True},
        children=[{"type": "paragraph", "children": [...]}],
    )
    assert token.to_dict() == {
        "type": "dropdown",
        "attrs": {"title": "Test", "open": True},
        "children": [{"type": "paragraph", "children": [...]}],
    }


def test_options_type_coercion():
    """Options correctly coerce string values."""
    @dataclass
    class TestOptions(DirectiveOptions):
        flag: bool = False
        count: int = 0
        items: list[str] = field(default_factory=list)

    opts = TestOptions.from_raw({
        "flag": "true",
        "count": "42",
        "items": "a, b, c",
    })

    assert opts.flag is True
    assert opts.count == 42
    assert opts.items == ["a", "b", "c"]


def test_options_validation():
    """Options validate allowed values."""
    @dataclass
    class TestOptions(DirectiveOptions):
        size: str = "medium"
        _allowed_values: ClassVar[dict[str, list[str]]] = {
            "size": ["small", "medium", "large"],
        }

    # Valid value
    opts = TestOptions.from_raw({"size": "small"})
    assert opts.size == "small"

    # Invalid value uses default
    opts = TestOptions.from_raw({"size": "invalid"})
    assert opts.size == "medium"
```

---

## 5. Design Alternatives Considered

### 5.1 Alternative A: Utilities Only (No Base Class)

**Approach**: Extract only shared utilities, keep directive classes as-is.

```python
# utils.py
def escape_html(text): ...
def register_directive(directive, md, names, parse_fn, token_type, render_fn): ...
```

**Pros**:
- Minimal change
- No new abstraction

**Cons**:
- Doesn't solve orphaned render functions
- Doesn't provide type safety
- Still requires boilerplate in each directive

**Verdict**: Insufficient for goals.

### 5.2 Alternative B: Decorator-Based

**Approach**: Use decorators instead of base class.

```python
@directive(names=["dropdown", "details"], token_type="dropdown")
class DropdownDirective:
    @options
    class Options:
        open: bool = False

    def parse(self, ...): ...
    def render(self, ...): ...
```

**Pros**:
- Very declarative
- No inheritance

**Cons**:
- Magic behavior
- Harder to understand
- More complex implementation

**Verdict**: Over-engineered for this use case.

### 5.3 Alternative C: Protocol-Based

**Approach**: Define Protocol instead of base class.

```python
class DirectiveProtocol(Protocol):
    NAMES: ClassVar[list[str]]
    TOKEN_TYPE: ClassVar[str]

    def parse(self, ...): ...
    def render(self, ...): ...
```

**Pros**:
- Structural typing
- No forced inheritance

**Cons**:
- No shared implementation
- Still need boilerplate

**Verdict**: Could complement base class, not replace it.

---

## 6. Architecture Impact

### 6.1 Affected Modules

| Module | Change Type | Impact |
|--------|-------------|--------|
| `rendering/plugins/directives/container_parser.py` | **NEW** | HIGH |
| `rendering/plugins/directives/base.py` | **NEW** | HIGH |
| `rendering/plugins/directives/contracts.py` | **NEW** | HIGH |
| `rendering/plugins/directives/*.py` | Refactor | HIGH |
| `rendering/plugins/directives/__init__.py` | Update exports | LOW |
| `tests/unit/rendering/directives/` | Add tests | MEDIUM |
| `health/validators/rendering.py` | Update checks | LOW |

### 6.2 Dependencies

```
BengalDirective
├── DirectivePlugin (mistune) - external, unchanged
├── DirectiveOptions - new, internal
├── DirectiveToken - new, internal
└── bengal.utils.logger - existing

DirectiveOptions
└── dataclasses - stdlib

DirectiveToken  
└── dataclasses - stdlib
```

### 6.3 API Surface

**New Public API**:
- `:::{/name}` - named closure syntax
- `BengalDirective` - base class
- `DirectiveContract` - nesting validation
- `DirectiveOptions` - options base
- `DirectiveToken` - token structure
- `StyledOptions` - common option pattern
- `ContainerOptions` - container option pattern
- `parse_container_directive()` - container parser
- Utility functions: `escape_html`, `build_class_string`, `bool_attr`, `data_attrs`

**Unchanged**:
- `:::{name}` ... `:::` - leaf directive syntax (user-facing, still supported)
- `::::{name}` ... `::::` - old container syntax (deprecated but still works)
- All directive classes (just different base)
- Token format (dicts for mistune)

---

## 7. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Named closer collision with existing content | LOW | LOW | Unlikely to have `:::{/name}` in normal text |
| Parser complexity for hybrid mode | MEDIUM | MEDIUM | Prioritize named closer matching over depth counting |
| Regression in standard directive parsing | MEDIUM | HIGH | Extensive regression tests for standard syntax |
| User confusion with two styles | LOW | LOW | Styles are complementary; one for simple, one for complex |

---

## 8. Success Criteria

### 8.1 Quantitative

- [ ] **Named closer parser implemented** and tested
- [ ] **100% of directives support** named closers
- [ ] **100% of directives migrated** to new pattern
- [ ] **0 duplicated escape_html** implementations
- [ ] **100% type coverage** on new base classes
- [ ] **All existing tests pass** unchanged

### 8.2 Qualitative

- [ ] **Zero fence counting** — Authors never need to count colons for nested containers
- [ ] **Clear error messages** — Invalid nesting produces actionable warnings
- [ ] **New directives are faster to write** (~50% less boilerplate)
- [ ] **Invalid options produce helpful warnings** (not silent defaults)
- [ ] **IDE autocomplete works** for options
- [ ] **Documentation auto-generates** from options classes

---

## 9. Open Questions

1. **Should AdmonitionDirective use multiple OPTIONS_CLASS?**  
   It registers 10 directive names but all use the same options.

2. **Should we support option inheritance?**  
   e.g., `CardOptions(StyledOptions)` to share common fields.

3. **Should token validation be in DirectiveToken?**  
   e.g., required attrs, type checking.

4. **Should we add option groups for complex directives?**  
   e.g., Cards has layout options, content options, behavior options.

---

## 10. References

- **Evidence**: `bengal/rendering/plugins/directives/*.py`
- **Pain Point Example**: `site/content/cli/debug/sandbox.md:74-87`
- **Mistune Directives**: [mistune docs](https://mistune.lepture.com/en/latest/directives.html)
- **Bengal Architecture**: `bengal/.cursor/rules/architecture-patterns.mdc`
- **Dataclass Conventions**: `bengal/.cursor/rules/dataclass-conventions.mdc`

---

## Appendix A: Full Directive Inventory

| File | Directives | Token Types | Complexity |
|------|------------|-------------|------------|
| admonitions.py | note, tip, warning, danger, error, info, example, success, caution, seealso | admonition | MEDIUM |
| badge.py | badge, bdg | badge | LOW |
| button.py | button | button | LOW |
| cards.py | cards, card, child-cards, grid, grid-item-card | cards_grid, card, child_cards | HIGH |
| checklist.py | checklist | checklist | LOW |
| code_tabs.py | code-tabs, code_tabs | code_tabs | MEDIUM |
| container.py | container, div | container | LOW |
| data_table.py | data-table | data_table | MEDIUM |
| dropdown.py | dropdown, details | dropdown | LOW |
| glossary.py | glossary | glossary | MEDIUM |
| icon.py | icon, svg-icon | icon | LOW |
| include.py | include | include | MEDIUM |
| list_table.py | list-table | list_table | MEDIUM |
| literalinclude.py | literalinclude | literalinclude | MEDIUM |
| marimo.py | marimo | marimo | MEDIUM |
| navigation.py | breadcrumbs, siblings, prev-next, related | breadcrumbs, siblings, prev_next, related | MEDIUM |
| rubric.py | rubric | rubric | LOW |
| steps.py | steps, step | steps, step | MEDIUM |
| tabs.py | tabs, tab-set, tab-item | legacy_tabs, tab_set, tab_item | HIGH |
| term.py | term | term | LOW (inline) |

---

## Appendix B: Options Field Reference

Common option patterns across directives:

| Option | Type | Used By | Description |
|--------|------|---------|-------------|
| :class: | str | 15+ | Additional CSS classes |
| :open: | bool | dropdown | Initially expanded |
| :columns: | str | cards, grid | Column count/responsive |
| :gap: | str | cards | Spacing (small/medium/large) |
| :style: | str | cards, container | Visual style variant |
| :link: | str | card, button | Destination URL |
| :icon: | str | card, admonitions | Icon name |
| :selected: | bool | tab-item | Initially selected tab |
| :sync: | str | tab-set | Tab sync key |

---

---

## Appendix C: Container vs Leaf Directive Classification

### Container Directives (use Named Closers when nested)

These directives MUST contain specific child directives:

| Directive | Required Children | Use Case |
|-----------|------------------|----------|
| `tab-set` / `tabs` | `tab-item` / `tab` | Tabbed content |
| `steps` | `step` | Step-by-step guides |
| `cards` | `card` | Card grids |
| `grid` | `grid-item-card` | Flexible grids |

### Leaf Directives

These directives contain arbitrary content, not specific child directives:

| Directive | Content Type | Use Case |
|-----------|-------------|----------|
| `note`, `tip`, `warning`, etc. | Markdown | Admonitions/callouts |
| `dropdown` / `details` | Markdown | Collapsible sections |
| `badge` | Text | Status badges |
| `button` | Text | CTA buttons |
| `glossary` | Auto-generated | Term definitions |
| `include` | File reference | Content reuse |
| `literalinclude` | File reference | Code inclusion |
| `checklist` | List items | Task lists |
| `rubric` | Text | Pseudo-headings |
| `container` / `div` | Markdown | Generic wrapper |
| `code-tabs` | Code blocks | Multi-language code |

### Hybrid Directives

These can appear as children OR standalone:

| Directive | Parent Context | Standalone |
|-----------|---------------|------------|
| `tab-item` / `tab` | Inside `tab-set` | ❌ Invalid |
| `step` | Inside `steps` | ❌ Invalid |
| `card` | Inside `cards`/`grid` | ⚠️ Works but no grid |

---

## Appendix D: Syntax Quick Reference

```markdown
# Standard syntax (simple)
:::{tabs}
  :::{tab} Title
  content
  :::
:::

# Named closure syntax (complex/nested)
:::{tabs}
  :::{tab} Title
  content
  :::{/tab}
:::{/tabs}

# Mixed syntax
:::{steps}
  :::{step} First
  :::{note}
  Simple nested content
  :::
  :::{/step}
:::{/steps}
```

---

## Appendix E: Recommended Next Steps

### Immediate Actions (Priority Order)

1. **Create Foundation Files** (Day 1)
   - `bengal/rendering/plugins/directives/tokens.py` - DirectiveToken dataclass
   - `bengal/rendering/plugins/directives/options.py` - DirectiveOptions base + StyledOptions
   - `bengal/rendering/plugins/directives/utils.py` - Extract shared utilities
   - `bengal/rendering/plugins/directives/contracts.py` - DirectiveContract + ContractValidator

2. **Create Base Class** (Day 1-2)
   - `bengal/rendering/plugins/directives/base.py` - BengalDirective with contract validation
   - Write comprehensive unit tests

3. **Pilot Migration** (Day 2-3)
   - Migrate `DropdownDirective` as proof-of-concept (simplest directive)
   - Validate backward compatibility
   - Update tests

4. **Named Closer Parser** (Day 3-4)
   - Extend `FencedDirective` to recognize `:::{/name}` pattern
   - Add comprehensive parsing tests
   - Validate existing content still works

### Command to Begin

```bash
# Create foundation structure
mkdir -p bengal/rendering/plugins/directives/_new
touch bengal/rendering/plugins/directives/_new/__init__.py
touch bengal/rendering/plugins/directives/_new/tokens.py
touch bengal/rendering/plugins/directives/_new/options.py
touch bengal/rendering/plugins/directives/_new/contracts.py
touch bengal/rendering/plugins/directives/_new/base.py
touch bengal/rendering/plugins/directives/_new/utils.py
```

### Test Commands

```bash
# Run directive tests
pytest tests/unit/rendering/test_steps_directive.py -v
pytest tests/unit/rendering/test_myst_tabs.py -v
pytest tests/unit/health/test_directive_validator.py -v

# All directive-related tests
pytest tests/unit/rendering/ -k directive -v
```

---

**End of RFC**
