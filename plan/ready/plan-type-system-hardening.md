# Plan: Type System Hardening Implementation

**Source**: `plan/evaluated/rfc-type-system-hardening.md`  
**Status**: Ready  
**Created**: 2025-12-22  
**Estimated Time**: 11 hours (~1.5 days across 4 phases)

---

## Executive Summary

Eliminate `Any` leakage at Bengal's boundaries by introducing typed alternatives that preserve backward compatibility. The implementation uses forward references for cross-module types, a `Frontmatter` dataclass with dict compatibility, `ASTNode` TypedDict union for parsed content, and `DirectiveToken` TypedDict for validators.

**Key Deliverables**:
- `Page._site` typed as `Site | None` via `TYPE_CHECKING`
- `Frontmatter` dataclass with `.title`, `.tags` etc. + dict compatibility for templates
- `ASTNode` discriminated union for type-safe AST processing
- `DirectiveToken` TypedDict for typed directive validation

---

## Phase 1: Forward References (2 hours)

Zero-cost type safety improvements using `TYPE_CHECKING` pattern.

### 1.1 Add TYPE_CHECKING imports to page/__init__.py

**File**: `bengal/core/page/__init__.py`

**Changes** (around line 1-10):
```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.section import Section
```

**Evidence**:
- Current `_site: Any | None` at line 175
- RFC lines 209-228 specify forward reference pattern

**Commit**: `core(page): add TYPE_CHECKING imports for Site and Section forward refs`

---

### 1.2 Type _site field as Site | None

**File**: `bengal/core/page/__init__.py`

**Change** (line 175):
```python
# Before
_site: Any | None = field(default=None, repr=False)

# After
_site: Site | None = field(default=None, repr=False)
```

**Evidence**:
- RFC lines 67-73 show pattern
- Verified `_site: Any | None` exists at line 175

**Commit**: `core(page): type _site as Site | None using forward reference`

---

### 1.3 Fix _site: Any in mixins

**Files**:
- `bengal/core/page/navigation.py` (line 43)
- `bengal/core/page/metadata.py` (line 69)

**Pattern for each**:
```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site

# Change: _site: Any → _site: Site | None
```

**Evidence**:
- grep confirmed `_site: Any` at navigation.py:43 and metadata.py:69

**Commit**: `core(page): type _site in navigation and metadata mixins`

---

### 1.4 Run mypy and fix revealed issues

**Command**:
```bash
uv run mypy bengal/core/page/ --strict
```

Fix any type errors revealed by the forward references.

**Exit Criteria**: No `Any` for cross-module references in Page, mypy passes

**Commit**: `core(page): fix mypy errors from forward reference changes`

---

## Phase 2: Frontmatter Dataclass (4 hours)

Typed frontmatter with backward-compatible dict access for templates.

### 2.1 Create frontmatter.py module

**File**: `bengal/core/page/frontmatter.py` (NEW)

```python
"""Typed frontmatter with dict-style access for template compatibility."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator


@dataclass
class Frontmatter:
    """
    Typed frontmatter metadata with backward-compatible dict access.

    Standard fields have explicit types for IDE autocomplete and type checking.
    Unknown fields are stored in `extra` and accessible via dict syntax.

    Example:
        >>> fm = Frontmatter(title="My Post", tags=["python"])
        >>> fm.title           # Typed access: str
        'My Post'
        >>> fm["title"]        # Dict access (templates): Any
        'My Post'
        >>> fm.get("missing")  # Safe access with default
        None
    """
    # Core fields (from PageCore, single source of truth)
    title: str = ""
    date: datetime | None = None
    tags: list[str] = field(default_factory=list)
    slug: str | None = None
    weight: int | None = None

    # i18n
    lang: str | None = None

    # Content type
    type: str | None = None
    layout: str | None = None

    # SEO
    description: str | None = None

    # Behavior
    draft: bool = False
    aliases: list[str] = field(default_factory=list)

    # Extension point for custom fields
    extra: dict[str, Any] = field(default_factory=dict)

    # ---- Dict Compatibility (for templates) ----

    def __getitem__(self, key: str) -> Any:
        """Dict-style access: fm["title"]."""
        if key == "extra":
            return self.extra
        if hasattr(self, key) and key != "extra":
            value = getattr(self, key)
            if value is not None:
                return value
        if key in self.extra:
            return self.extra[key]
        raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        """Support `"title" in fm`."""
        if hasattr(self, key) and key != "extra":
            return getattr(self, key) is not None
        return key in self.extra

    def get(self, key: str, default: Any = None) -> Any:
        """Dict.get() compatibility."""
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self) -> Iterator[str]:
        """Iterate over available keys."""
        for f in self.__dataclass_fields__:
            if f != "extra" and getattr(self, f) is not None:
                yield f
        yield from self.extra.keys()

    def items(self) -> Iterator[tuple[str, Any]]:
        """Iterate over key-value pairs."""
        for key in self.keys():
            yield key, self[key]

    # ---- Factory ----

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Frontmatter:
        """
        Create Frontmatter from raw dict (e.g., parsed YAML).

        Known fields are extracted and typed; unknown fields go to extra.
        """
        known_fields = {f.name for f in cls.__dataclass_fields__.values() if f.name != "extra"}
        known = {}
        extra = {}

        for key, value in data.items():
            if key in known_fields:
                known[key] = value
            else:
                extra[key] = value

        return cls(**known, extra=extra)
```

**Evidence**: RFC lines 239-350 specify exact implementation

**Commit**: `core(page): add Frontmatter dataclass with dict compatibility`

---

### 2.2 Add page.frontmatter property

**File**: `bengal/core/page/__init__.py`

**Changes**:

1. Add import:
```python
from bengal.core.page.frontmatter import Frontmatter
```

2. Add field (after `metadata` field):
```python
_frontmatter: Frontmatter | None = field(default=None, init=False, repr=False)
```

3. Add property:
```python
@property
def frontmatter(self) -> Frontmatter:
    """
    Typed access to frontmatter fields.

    Lazily created from metadata dict on first access.

    Example:
        >>> page.frontmatter.title  # Typed: str
        'My Post'
        >>> page.frontmatter["title"]  # Dict syntax for templates
        'My Post'
    """
    if self._frontmatter is None:
        self._frontmatter = Frontmatter.from_dict(self.metadata)
    return self._frontmatter
```

**Evidence**: RFC lines 355-377 specify integration

**Commit**: `core(page): add frontmatter property for typed metadata access`

---

### 2.3 Export Frontmatter from page package

**File**: `bengal/core/page/__init__.py`

Update `__all__` to include:
```python
from bengal.core.page.frontmatter import Frontmatter

__all__ = [
    # ... existing exports
    "Frontmatter",
]
```

**Commit**: `core(page): export Frontmatter from page package`

---

### 2.4 Add unit tests for Frontmatter

**File**: `tests/unit/core/page/test_frontmatter.py` (NEW)

```python
"""Tests for Frontmatter dataclass."""

from __future__ import annotations

from datetime import datetime

import pytest

from bengal.core.page.frontmatter import Frontmatter


class TestFrontmatterFromDict:
    """Test Frontmatter.from_dict factory."""

    def test_separates_known_and_extra_fields(self) -> None:
        """Frontmatter.from_dict separates known and extra fields."""
        data = {
            "title": "My Post",
            "tags": ["python", "testing"],
            "custom_field": "value",
            "another_custom": 42,
        }
        fm = Frontmatter.from_dict(data)

        assert fm.title == "My Post"
        assert fm.tags == ["python", "testing"]
        assert fm.extra["custom_field"] == "value"
        assert fm.extra["another_custom"] == 42

    def test_handles_empty_dict(self) -> None:
        """Empty dict creates default Frontmatter."""
        fm = Frontmatter.from_dict({})

        assert fm.title == ""
        assert fm.tags == []
        assert fm.extra == {}

    def test_preserves_date_type(self) -> None:
        """Date field is preserved from input."""
        now = datetime.now()
        fm = Frontmatter.from_dict({"date": now})

        assert fm.date == now


class TestFrontmatterDictAccess:
    """Test dict-style access for template compatibility."""

    def test_getitem_known_field(self) -> None:
        """Dict access works for known fields."""
        fm = Frontmatter(title="Test")

        assert fm["title"] == "Test"

    def test_getitem_extra_field(self) -> None:
        """Dict access works for extra fields."""
        fm = Frontmatter(extra={"custom": "value"})

        assert fm["custom"] == "value"

    def test_getitem_missing_raises_keyerror(self) -> None:
        """Dict access raises KeyError for missing keys."""
        fm = Frontmatter()

        with pytest.raises(KeyError):
            _ = fm["nonexistent"]

    def test_get_with_default(self) -> None:
        """get() returns default for missing keys."""
        fm = Frontmatter()

        assert fm.get("missing") is None
        assert fm.get("missing", "default") == "default"

    def test_contains_known_field(self) -> None:
        """'in' operator works for known fields."""
        fm = Frontmatter(title="Test")

        assert "title" in fm
        assert "slug" not in fm  # None value

    def test_contains_extra_field(self) -> None:
        """'in' operator works for extra fields."""
        fm = Frontmatter(extra={"custom": "value"})

        assert "custom" in fm
        assert "missing" not in fm


class TestFrontmatterIteration:
    """Test iteration methods for templates."""

    def test_keys_yields_set_fields(self) -> None:
        """keys() yields fields with non-None values."""
        fm = Frontmatter(title="Test", tags=["a", "b"])

        keys = list(fm.keys())

        assert "title" in keys
        assert "tags" in keys
        assert "slug" not in keys  # None

    def test_keys_includes_extra(self) -> None:
        """keys() includes extra field keys."""
        fm = Frontmatter(title="Test", extra={"custom": "value"})

        keys = list(fm.keys())

        assert "custom" in keys

    def test_items_yields_key_value_pairs(self) -> None:
        """items() yields (key, value) tuples."""
        fm = Frontmatter(title="Test", tags=["a"])

        items = dict(fm.items())

        assert items["title"] == "Test"
        assert items["tags"] == ["a"]
```

**Evidence**: RFC lines 607-640 provide test templates

**Commit**: `tests(page): add unit tests for Frontmatter dataclass`

---

### 2.5 Add integration test for page.frontmatter

**File**: `tests/integration/core/test_page_frontmatter.py` (NEW)

```python
"""Integration tests for Page.frontmatter property."""

from __future__ import annotations

from pathlib import Path

import pytest

from bengal.core.page import Page
from bengal.core.page.frontmatter import Frontmatter


def test_page_frontmatter_typed_access(tmp_path: Path) -> None:
    """Page.frontmatter provides typed access to metadata."""
    page = Page(
        source_path=tmp_path / "test.md",
        content="# Test",
        metadata={"title": "My Post", "tags": ["python"], "custom": "value"},
    )

    # Typed access
    assert isinstance(page.frontmatter, Frontmatter)
    assert page.frontmatter.title == "My Post"
    assert page.frontmatter.tags == ["python"]

    # Extra fields
    assert page.frontmatter.extra["custom"] == "value"


def test_frontmatter_dict_syntax_works(tmp_path: Path) -> None:
    """Templates using dict syntax still work."""
    page = Page(
        source_path=tmp_path / "test.md",
        content="# Test",
        metadata={"title": "My Post"},
    )

    # Dict access (what templates use)
    assert page.frontmatter["title"] == "My Post"
    assert page.frontmatter.get("missing") is None


def test_frontmatter_cached(tmp_path: Path) -> None:
    """Frontmatter is cached after first access."""
    page = Page(
        source_path=tmp_path / "test.md",
        content="# Test",
        metadata={"title": "Test"},
    )

    fm1 = page.frontmatter
    fm2 = page.frontmatter

    assert fm1 is fm2  # Same instance
```

**Commit**: `tests(integration): add tests for Page.frontmatter property`

---

**Exit Criteria Phase 2**: `page.frontmatter.title` works, templates unchanged, all tests pass

---

## Phase 3: AST Node Types (3 hours)

Type definitions for parsed markdown AST nodes.

### 3.1 Create ast_types.py module

**File**: `bengal/rendering/ast_types.py` (NEW)

```python
"""Type definitions for markdown AST nodes (mistune-compatible)."""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict, Union


class BaseNode(TypedDict, total=False):
    """Common fields for all AST nodes."""
    children: list[ASTNode]
    attrs: dict[str, str]


class TextNode(TypedDict):
    """Plain text content."""
    type: Literal["text"]
    raw: str


class CodeSpanNode(TypedDict):
    """Inline code."""
    type: Literal["codespan"]
    raw: str


class HeadingNode(TypedDict):
    """Heading (h1-h6)."""
    type: Literal["heading"]
    level: int
    children: list[ASTNode]
    attrs: NotRequired[dict[str, str]]


class ParagraphNode(TypedDict):
    """Paragraph block."""
    type: Literal["paragraph"]
    children: list[ASTNode]


class CodeBlockNode(TypedDict):
    """Fenced code block."""
    type: Literal["block_code"]
    raw: str
    info: str | None  # Language hint


class ListNode(TypedDict):
    """Ordered or unordered list."""
    type: Literal["list"]
    ordered: bool
    children: list[ListItemNode]


class ListItemNode(TypedDict):
    """List item."""
    type: Literal["list_item"]
    children: list[ASTNode]


class BlockquoteNode(TypedDict):
    """Blockquote."""
    type: Literal["block_quote"]
    children: list[ASTNode]


class LinkNode(TypedDict):
    """Hyperlink."""
    type: Literal["link"]
    url: str
    title: str | None
    children: list[ASTNode]


class ImageNode(TypedDict):
    """Image."""
    type: Literal["image"]
    src: str
    alt: str
    title: str | None


class EmphasisNode(TypedDict):
    """Emphasis (italic)."""
    type: Literal["emphasis"]
    children: list[ASTNode]


class StrongNode(TypedDict):
    """Strong (bold)."""
    type: Literal["strong"]
    children: list[ASTNode]


class ThematicBreakNode(TypedDict):
    """Horizontal rule / thematic break."""
    type: Literal["thematic_break"]


class SoftBreakNode(TypedDict):
    """Soft line break."""
    type: Literal["softbreak"]


class HardBreakNode(TypedDict):
    """Hard line break."""
    type: Literal["linebreak"]


# Discriminated union of all node types
ASTNode = Union[
    TextNode,
    CodeSpanNode,
    HeadingNode,
    ParagraphNode,
    CodeBlockNode,
    ListNode,
    ListItemNode,
    BlockquoteNode,
    LinkNode,
    ImageNode,
    EmphasisNode,
    StrongNode,
    ThematicBreakNode,
    SoftBreakNode,
    HardBreakNode,
]


# Type guards for common patterns
def is_heading(node: ASTNode) -> bool:
    """Type guard for heading nodes."""
    return node.get("type") == "heading"


def is_text(node: ASTNode) -> bool:
    """Type guard for text nodes."""
    return node.get("type") == "text"


def is_code_block(node: ASTNode) -> bool:
    """Type guard for code block nodes."""
    return node.get("type") == "block_code"


def get_heading_level(node: ASTNode) -> int | None:
    """Get heading level if node is a heading."""
    if is_heading(node):
        return node.get("level")  # type: ignore[return-value]
    return None


def get_node_text(node: ASTNode) -> str:
    """Extract text content from a node."""
    if "raw" in node:
        return node["raw"]  # type: ignore[typeddict-item]
    return ""
```

**Evidence**: RFC lines 401-514 specify AST types

**Commit**: `rendering: add ASTNode TypedDict union for typed AST processing`

---

### 3.2 Update Page.parsed_ast type

**File**: `bengal/core/page/__init__.py`

**Changes**:

1. Add import:
```python
from bengal.rendering.ast_types import ASTNode
```

2. Update field type (line 154):
```python
# Before
parsed_ast: Any | None = None

# After
parsed_ast: list[ASTNode] | None = None
```

**Evidence**: RFC lines 519-529

**Commit**: `core(page): type parsed_ast as list[ASTNode]`

---

### 3.3 Update Page content mixin

**File**: `bengal/core/page/content.py`

**Changes** (line 51):
```python
# Before
parsed_ast: Any  # Contains HTML (not AST)

# After
from bengal.rendering.ast_types import ASTNode

parsed_ast: list[ASTNode] | None
```

**Commit**: `core(page): type parsed_ast in content mixin`

---

### 3.4 Add unit tests for AST types

**File**: `tests/unit/rendering/test_ast_types.py` (NEW)

```python
"""Tests for AST type definitions."""

from __future__ import annotations

import pytest

from bengal.rendering.ast_types import (
    ASTNode,
    CodeBlockNode,
    HeadingNode,
    TextNode,
    get_heading_level,
    get_node_text,
    is_code_block,
    is_heading,
    is_text,
)


class TestASTNodeTypes:
    """Test AST node type definitions."""

    def test_heading_node_structure(self) -> None:
        """HeadingNode has required fields."""
        node: HeadingNode = {
            "type": "heading",
            "level": 2,
            "children": [],
        }

        assert node["type"] == "heading"
        assert node["level"] == 2

    def test_text_node_structure(self) -> None:
        """TextNode has required fields."""
        node: TextNode = {
            "type": "text",
            "raw": "Hello world",
        }

        assert node["type"] == "text"
        assert node["raw"] == "Hello world"

    def test_code_block_structure(self) -> None:
        """CodeBlockNode has required fields."""
        node: CodeBlockNode = {
            "type": "block_code",
            "raw": "print('hello')",
            "info": "python",
        }

        assert node["type"] == "block_code"
        assert node["info"] == "python"


class TestTypeGuards:
    """Test type guard functions."""

    def test_is_heading(self) -> None:
        """is_heading identifies heading nodes."""
        heading: ASTNode = {"type": "heading", "level": 1, "children": []}
        text: ASTNode = {"type": "text", "raw": "hello"}

        assert is_heading(heading) is True
        assert is_heading(text) is False

    def test_is_text(self) -> None:
        """is_text identifies text nodes."""
        text: ASTNode = {"type": "text", "raw": "hello"}
        heading: ASTNode = {"type": "heading", "level": 1, "children": []}

        assert is_text(text) is True
        assert is_text(heading) is False

    def test_is_code_block(self) -> None:
        """is_code_block identifies code block nodes."""
        code: ASTNode = {"type": "block_code", "raw": "code", "info": None}
        text: ASTNode = {"type": "text", "raw": "hello"}

        assert is_code_block(code) is True
        assert is_code_block(text) is False


class TestHelpers:
    """Test helper functions."""

    def test_get_heading_level(self) -> None:
        """get_heading_level extracts level from heading."""
        heading: ASTNode = {"type": "heading", "level": 3, "children": []}
        text: ASTNode = {"type": "text", "raw": "hello"}

        assert get_heading_level(heading) == 3
        assert get_heading_level(text) is None

    def test_get_node_text(self) -> None:
        """get_node_text extracts raw text."""
        text: ASTNode = {"type": "text", "raw": "hello"}
        code: ASTNode = {"type": "block_code", "raw": "print()", "info": None}
        heading: ASTNode = {"type": "heading", "level": 1, "children": []}

        assert get_node_text(text) == "hello"
        assert get_node_text(code) == "print()"
        assert get_node_text(heading) == ""


class TestTypeNarrowing:
    """Test type narrowing with match statement."""

    def test_match_statement_works(self) -> None:
        """Type narrowing works with match statement."""
        node: ASTNode = {"type": "heading", "level": 2, "children": []}

        match node["type"]:
            case "heading":
                assert node["level"] == 2  # Type narrowed
            case _:
                pytest.fail("Should match heading")
```

**Evidence**: RFC lines 642-653 provide test template

**Commit**: `tests(rendering): add unit tests for ASTNode types`

---

### 3.5 Run mypy on rendering module

**Command**:
```bash
uv run mypy bengal/rendering/ast_types.py --strict
uv run mypy bengal/rendering/ --strict
```

**Exit Criteria Phase 3**: `parsed_ast` typed, mypy passes on rendering/

**Commit**: `rendering: fix mypy errors from AST type changes`

---

## Phase 4: Directive Token Types (2 hours)

Type definitions for directive validation tokens.

### 4.1 Create tokens.py module

**File**: `bengal/directives/tokens.py` (NEW)

```python
"""Type definitions for directive tokens."""

from __future__ import annotations

from enum import Enum
from typing import NotRequired, TypedDict


class DirectiveType(Enum):
    """Known directive types for type-safe validation."""
    # Container directives
    STEP = "step"
    STEPS = "steps"
    TAB_ITEM = "tab_item"
    TABS = "tabs"

    # Admonition directives
    NOTE = "note"
    WARNING = "warning"
    TIP = "tip"
    IMPORTANT = "important"
    CAUTION = "caution"

    # Code directives
    CODE_INCLUDE = "code_include"

    # Other directives
    FIGURE = "figure"
    GLOSSARY = "glossary"
    TOC = "toc"


class DirectiveToken(TypedDict):
    """
    Token representing a parsed directive.

    This is the structure passed to ContractValidator for validation.
    """
    type: str  # Directive type (e.g., "step", "tab_item")
    children: NotRequired[list[DirectiveToken]]
    attrs: NotRequired[dict[str, str]]
    raw: NotRequired[str]
    body: NotRequired[str]


class DirectiveContext(TypedDict, total=False):
    """Context for directive rendering."""
    page_path: str
    site_config: dict[str, str]
    section_path: str
```

**Evidence**: RFC lines 539-572 specify token types

**Commit**: `directives: add DirectiveToken TypedDict and DirectiveType enum`

---

### 4.2 Update ContractValidator.validate_children signature

**File**: `bengal/directives/contracts.py`

**Changes** (around line 259-264):

1. Add import:
```python
from bengal.directives.tokens import DirectiveToken
```

2. Update signature:
```python
# Before
def validate_children(
    contract: DirectiveContract,
    directive_type: str,
    children: list[dict[str, Any]],
    location: str | None = None,
) -> list[ContractViolation]:

# After
def validate_children(
    contract: DirectiveContract,
    directive_type: str,
    children: list[DirectiveToken],
    location: str | None = None,
) -> list[ContractViolation]:
```

3. Update child_types extraction (line 281):
```python
# Before
child_types = [c.get("type") for c in children if isinstance(c, dict) and c.get("type")]

# After (cleaner with typed tokens)
child_types = [c["type"] for c in children if "type" in c]
```

**Evidence**: RFC lines 562-572

**Commit**: `directives(contracts): type validate_children with DirectiveToken`

---

### 4.3 Update base directive validate call

**File**: `bengal/directives/base.py`

**Changes** (around line 232):

1. Add import:
```python
from bengal.directives.tokens import DirectiveToken
```

2. Ensure children passed to `validate_children` are cast appropriately:
```python
# Type annotation for clarity
children: list[DirectiveToken] = [...]
violations = ContractValidator.validate_children(
    self.contract,
    self.directive_type,
    children,
    location,
)
```

**Commit**: `directives(base): use DirectiveToken type in validation`

---

### 4.4 Export tokens from directives package

**File**: `bengal/directives/__init__.py`

Add export:
```python
from bengal.directives.tokens import DirectiveToken, DirectiveType

__all__ = [
    # ... existing exports
    "DirectiveToken",
    "DirectiveType",
]
```

**Commit**: `directives: export DirectiveToken and DirectiveType`

---

### 4.5 Add unit tests for directive tokens

**File**: `tests/unit/directives/test_tokens.py` (NEW)

```python
"""Tests for directive token types."""

from __future__ import annotations

from bengal.directives.tokens import DirectiveToken, DirectiveType


class TestDirectiveType:
    """Test DirectiveType enum."""

    def test_known_types_exist(self) -> None:
        """Known directive types are defined."""
        assert DirectiveType.STEP.value == "step"
        assert DirectiveType.NOTE.value == "note"
        assert DirectiveType.TABS.value == "tabs"

    def test_enum_iteration(self) -> None:
        """Can iterate over directive types."""
        types = list(DirectiveType)

        assert len(types) > 0
        assert DirectiveType.STEP in types


class TestDirectiveToken:
    """Test DirectiveToken TypedDict structure."""

    def test_minimal_token(self) -> None:
        """Minimal token has required type field."""
        token: DirectiveToken = {"type": "note"}

        assert token["type"] == "note"

    def test_full_token(self) -> None:
        """Full token has all optional fields."""
        token: DirectiveToken = {
            "type": "step",
            "children": [{"type": "paragraph"}],
            "attrs": {"id": "step-1"},
            "raw": "Step content",
            "body": "Processed body",
        }

        assert token["type"] == "step"
        assert len(token["children"]) == 1
        assert token["attrs"]["id"] == "step-1"

    def test_nested_tokens(self) -> None:
        """Tokens can be nested."""
        token: DirectiveToken = {
            "type": "steps",
            "children": [
                {"type": "step", "body": "First"},
                {"type": "step", "body": "Second"},
            ],
        }

        assert len(token["children"]) == 2
        assert token["children"][0]["type"] == "step"
```

**Commit**: `tests(directives): add unit tests for DirectiveToken types`

---

### 4.6 Run mypy on directives module

**Command**:
```bash
uv run mypy bengal/directives/ --strict
```

**Exit Criteria Phase 4**: Directive validation fully typed, mypy passes

**Commit**: `directives: fix mypy errors from token type changes`

---

## Verification & Cleanup

### Run full test suite

```bash
# Unit tests for new modules
uv run pytest tests/unit/core/page/test_frontmatter.py -v
uv run pytest tests/unit/rendering/test_ast_types.py -v
uv run pytest tests/unit/directives/test_tokens.py -v

# Integration tests
uv run pytest tests/integration/core/test_page_frontmatter.py -v

# Full test suite to ensure no regressions
uv run pytest tests/ -v --tb=short

# Linter
uv run ruff check bengal/core/page/ bengal/rendering/ bengal/directives/

# Type check
uv run mypy bengal/core/page/ bengal/rendering/ bengal/directives/ --strict
```

---

## Success Criteria

### Quantitative

- [ ] Zero `Any` in public method signatures of Page, PageCore, DirectiveContract
- [ ] 100% mypy pass rate (current baseline maintained)
- [ ] No template test failures
- [ ] All new unit tests pass

### Qualitative

- [ ] IDE autocomplete works for `page.frontmatter.title`
- [ ] Type checker catches invalid AST access
- [ ] `page.frontmatter["title"]` works for templates (backward compatible)

---

## File Change Summary

| File | Change Type | Lines |
|------|-------------|-------|
| `bengal/core/page/__init__.py` | Modify | ~25 |
| `bengal/core/page/frontmatter.py` | **New** | ~100 |
| `bengal/core/page/navigation.py` | Modify | ~10 |
| `bengal/core/page/metadata.py` | Modify | ~10 |
| `bengal/core/page/content.py` | Modify | ~5 |
| `bengal/rendering/ast_types.py` | **New** | ~150 |
| `bengal/directives/tokens.py` | **New** | ~50 |
| `bengal/directives/contracts.py` | Modify | ~15 |
| `bengal/directives/base.py` | Modify | ~10 |
| `bengal/directives/__init__.py` | Modify | ~5 |
| `tests/unit/core/page/test_frontmatter.py` | **New** | ~100 |
| `tests/unit/rendering/test_ast_types.py` | **New** | ~80 |
| `tests/unit/directives/test_tokens.py` | **New** | ~60 |
| `tests/integration/core/test_page_frontmatter.py` | **New** | ~50 |

**Total**: ~670 lines added/modified

---

## Commit Sequence

### Phase 1: Forward References
1. `core(page): add TYPE_CHECKING imports for Site and Section forward refs`
2. `core(page): type _site as Site | None using forward reference`
3. `core(page): type _site in navigation and metadata mixins`
4. `core(page): fix mypy errors from forward reference changes`

### Phase 2: Frontmatter Dataclass
5. `core(page): add Frontmatter dataclass with dict compatibility`
6. `core(page): add frontmatter property for typed metadata access`
7. `core(page): export Frontmatter from page package`
8. `tests(page): add unit tests for Frontmatter dataclass`
9. `tests(integration): add tests for Page.frontmatter property`

### Phase 3: AST Types
10. `rendering: add ASTNode TypedDict union for typed AST processing`
11. `core(page): type parsed_ast as list[ASTNode]`
12. `core(page): type parsed_ast in content mixin`
13. `tests(rendering): add unit tests for ASTNode types`
14. `rendering: fix mypy errors from AST type changes`

### Phase 4: Directive Tokens
15. `directives: add DirectiveToken TypedDict and DirectiveType enum`
16. `directives(contracts): type validate_children with DirectiveToken`
17. `directives(base): use DirectiveToken type in validation`
18. `directives: export DirectiveToken and DirectiveType`
19. `tests(directives): add unit tests for DirectiveToken types`
20. `directives: fix mypy errors from token type changes`

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Template breakage | Low | Dict compatibility layer tested extensively |
| Circular imports | Low | TYPE_CHECKING pattern established |
| Incomplete AST types | Medium | Start with common nodes, extend as needed |
| Performance regression | Low | Lazy frontmatter creation |

---

## Open Questions from RFC

- [ ] Should `Frontmatter` support `**kwargs` for unknown fields in constructor?
  - **Recommendation**: No, use `from_dict()` factory instead
- [ ] Which AST node types are essential vs. nice-to-have?
  - **Implemented**: Common mistune nodes (heading, paragraph, code, list, link, image)
- [x] Should `DirectiveToken` use `Literal` for known directive types?
  - **Implemented**: Added `DirectiveType` enum for known types

---

## References

- RFC: `plan/evaluated/rfc-type-system-hardening.md`
- Current `_site: Any`: `bengal/core/page/__init__.py:175`
- Current `parsed_ast: Any`: `bengal/core/page/__init__.py:154`
- Current `validate_children`: `bengal/directives/contracts.py:259-264`
- Bengal dataclass conventions: `bengal/.cursor/rules/dataclass-conventions.mdc`
- TYPE_CHECKING guide: `TYPE_CHECKING_GUIDE.md`
