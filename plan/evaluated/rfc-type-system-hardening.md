# RFC: Type System Hardening - Eliminating `Any` at Boundaries

**Status**: Evaluated
**Created**: 2025-12-22
**Author**: AI-assisted
**Confidence**: 97% 🟢
**Category**: Architecture / Type Safety

---

## Executive Summary

Bengal's type system is strong at the architectural level (PageCore contract, DirectiveContract, Strategy Pattern) but has `Any` leakage at boundaries: metadata dicts, AST nodes, cross-module references, and directive tokens. This RFC proposes typed alternatives that preserve Bengal's "types as contracts" philosophy while maintaining backward compatibility.

**Principle**: Type signatures should be more important than implementations. Where Bengal currently uses `Any`, the implementation becomes the only source of truth—violating this principle.

---

## Problem Statement

### Current State

Bengal already excels at type-driven architecture:

✅ **PageCore** - Single source of truth for cacheable metadata, enforced across Page/PageProxy/PageMetadata  
✅ **DirectiveContract** - Frozen dataclass where type signature IS the validation spec  
✅ **Mixin architecture** - Type signatures show Page capabilities at a glance  
✅ **Strict mypy** - `disallow_untyped_defs`, `disallow_any_generics`

However, several boundaries leak `Any`:

### Evidence: `Any` Usage in Core Modules

| Location | Type | Impact |
|----------|------|--------|
| `Page.metadata` | `dict[str, Any]` | No IDE support for frontmatter fields |
| `Page._site` | `Any \| None` | Circular import workaround, loses type safety |
| `Page.parsed_ast` | `Any \| None` | External library (mistune) untyped |
| `PageCore.props` | `dict[str, Any]` | Custom frontmatter escape hatch |
| `ContractValidator.validate_children` | `list[dict[str, Any]]` | Token structure untyped |
| `Page._ast_cache` | `list[dict[str, Any]] \| None` | AST nodes untyped |

### Impact

1. **No IDE autocomplete** for known frontmatter fields (title, date, tags accessed via `metadata["title"]`)
2. **Runtime key errors** possible when accessing metadata
3. **Type checker blind spots** - bugs in AST processing not caught statically
4. **Documentation gap** - types don't document expected structures

### Evidence: Frontmatter Access Pattern

```python
# Current: Untyped access, IDE blind
title = page.metadata.get("title", "")
date = page.metadata.get("date")  # type: Any

# Ideal: Typed access, IDE knows the type
title = page.frontmatter.title  # type: str
date = page.frontmatter.date    # type: datetime | None
```

### Evidence: Circular Import Pattern

```python
# bengal/core/page/__init__.py:175
_site: Any | None = field(default=None, repr=False)

# This loses type safety. Should be:
if TYPE_CHECKING:
    from bengal.core.site import Site
_site: Site | None = field(default=None, repr=False)
```

---

## Goals & Non-Goals

### Goals

1. **Eliminate `Any` from public interfaces** where structure is known
2. **Preserve backward compatibility** - existing templates/code must work
3. **Improve IDE experience** - autocomplete for frontmatter, AST nodes
4. **Catch bugs statically** - type checker finds AST/token access errors
5. **Document contracts via types** - signatures explain expected structures

### Non-Goals

- Runtime validation of all types (performance cost)
- Breaking existing template syntax (`item["key"]` must still work)
- Typing arbitrary user frontmatter (genuinely dynamic)
- Adding external dependencies (no pydantic requirement)

---

## Design Options

### Option A: TypedDict for Known Structures

Use TypedDict for structures with known keys.

**Frontmatter**:
```python
class KnownFrontmatter(TypedDict, total=False):
    """Standard frontmatter fields with types."""
    title: str
    date: str | datetime
    tags: list[str]
    slug: str
    weight: int
    type: str
    layout: str
    description: str
    draft: bool
    aliases: list[str]

class PageMetadataDict(TypedDict):
    """Full metadata structure."""
    known: KnownFrontmatter
    extra: dict[str, Any]  # Escape hatch
```

**AST Nodes**:
```python
class TextNode(TypedDict):
    type: Literal["text"]
    raw: str

class HeadingNode(TypedDict):
    type: Literal["heading"]
    level: int
    children: list[ASTNode]

ASTNode = TextNode | HeadingNode | ParagraphNode | ...
```

**Pros**: Full type safety, discriminated unions work with `match`  
**Cons**: Verbose, requires defining all node types

### Option B: Dataclasses with Dict Compatibility

Use dataclasses that support both `.field` and `["field"]` access.

```python
@dataclass
class Frontmatter:
    """Typed frontmatter with backward-compatible dict access."""
    title: str = ""
    date: datetime | None = None
    tags: list[str] = field(default_factory=list)
    slug: str | None = None
    # ... other known fields ...

    # Extension point
    extra: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        """Dict-style access for template compatibility."""
        if hasattr(self, key):
            return getattr(self, key)
        return self.extra.get(key)

    def get(self, key: str, default: Any = None) -> Any:
        """Dict.get() compatibility."""
        try:
            return self[key]
        except KeyError:
            return default
```

**Pros**: IDE autocomplete, templates still work with `["key"]`  
**Cons**: Slight runtime overhead for `__getitem__`

### Option C: TYPE_CHECKING Forward References Only

Minimal change: fix circular imports with `TYPE_CHECKING`, leave metadata as-is.

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site

@dataclass
class Page:
    _site: Site | None = field(default=None, repr=False)
```

**Pros**: Zero runtime cost, fixes type checker errors  
**Cons**: Doesn't improve IDE experience for frontmatter

### Recommended: Option B (Dataclasses) + Option C (Forward Refs)

Combine approaches for comprehensive improvement:

1. **Forward references** for cross-module types (zero cost)
2. **Frontmatter dataclass** with dict compatibility (IDE + templates)
3. **ASTNode TypedDict union** for parsed content (type safety)
4. **DirectiveToken TypedDict** for validator (type safety)

---

## Detailed Design

### Phase 1: Forward References (Zero Cost)

Fix circular imports with `TYPE_CHECKING`:

```python
# bengal/core/page/__init__.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.core.section import Section

@dataclass
class Page:
    # Before: _site: Any | None
    _site: Site | None = field(default=None, repr=False)

    # Before: _section implicit Any
    # After: typed via property return
    @property
    def _section(self) -> Section | None:
        ...
```

**Files Changed**:
- `bengal/core/page/__init__.py`
- `bengal/core/page/relationships.py`
- `bengal/core/page/navigation.py`

### Phase 2: Frontmatter Dataclass

Create typed frontmatter with backward compatibility:

```python
# bengal/core/page/frontmatter.py
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

**Integration with Page**:

```python
# bengal/core/page/__init__.py

@dataclass
class Page:
    source_path: Path
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)  # Raw dict (unchanged)

    # Typed frontmatter (lazy-created from metadata)
    _frontmatter: Frontmatter | None = field(default=None, init=False, repr=False)

    @property
    def frontmatter(self) -> Frontmatter:
        """Typed access to frontmatter fields."""
        if self._frontmatter is None:
            self._frontmatter = Frontmatter.from_dict(self.metadata)
        return self._frontmatter

    # Convenience properties delegate to frontmatter
    @property
    def title(self) -> str:
        return self.frontmatter.title or self.core.title
```

**Backward Compatibility**:
- `page.metadata["title"]` still works (raw dict)
- `page.frontmatter.title` is new typed access
- `page.frontmatter["title"]` works for templates
- Existing code unchanged

### Phase 3: AST Node Types

Define typed AST nodes for parsed content:

```python
# bengal/rendering/ast_types.py
"""Type definitions for markdown AST nodes (mistune-compatible)."""

from __future__ import annotations

from typing import Literal, TypedDict, Union


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
    attrs: dict[str, str]


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
    # Add more as needed
]


def is_heading(node: ASTNode) -> bool:
    """Type guard for heading nodes."""
    return node.get("type") == "heading"


def get_heading_level(node: ASTNode) -> int | None:
    """Get heading level if node is a heading."""
    if node.get("type") == "heading":
        return node.get("level")  # type: ignore
    return None
```

**Usage in Page**:

```python
# bengal/core/page/__init__.py
from bengal.rendering.ast_types import ASTNode

@dataclass
class Page:
    # Before: parsed_ast: Any | None = None
    parsed_ast: list[ASTNode] | None = None

    # Before: _ast_cache: list[dict[str, Any]] | None
    _ast_cache: list[ASTNode] | None = field(default=None, repr=False)
```

### Phase 4: Directive Token Types

Type the directive validation tokens:

```python
# bengal/directives/tokens.py
"""Type definitions for directive tokens."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class DirectiveToken(TypedDict):
    """Token representing a parsed directive."""
    type: str  # Directive type (e.g., "step", "tab_item")
    children: NotRequired[list[DirectiveToken]]
    attrs: NotRequired[dict[str, str]]
    raw: NotRequired[str]
    body: NotRequired[str]


# Update ContractValidator signature
def validate_children(
    contract: DirectiveContract,
    directive_type: str,
    children: list[DirectiveToken],  # Now typed!
    location: str | None = None,
) -> list[ContractViolation]:
    """Validate children meet contract requirements."""
    # No more c.get("type") - just c["type"]
    child_types = [c["type"] for c in children]
    ...
```

---

## Architecture Impact

| Subsystem | Impact | Changes |
|-----------|--------|---------|
| Core | **Medium** | Frontmatter dataclass, AST types on Page |
| Directives | **Low** | DirectiveToken type, validator signatures |
| Rendering | **Low** | ast_types.py module, parser return types |
| Cache | **None** | PageCore unchanged (already typed) |
| Templates | **None** | Dict compatibility preserved |
| CLI | **None** | No changes |

**Files Changed**:

```
bengal/core/page/__init__.py          # Forward refs, frontmatter property
bengal/core/page/frontmatter.py       # NEW - Frontmatter dataclass
bengal/rendering/ast_types.py         # NEW - ASTNode types
bengal/directives/tokens.py           # NEW - DirectiveToken type
bengal/directives/contracts.py        # Type signature update
bengal/directives/validator.py        # Type signature update
```

**Breaking Changes**: None. All changes are additive or internal signature improvements.

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/core/test_frontmatter.py

def test_frontmatter_from_dict():
    """Frontmatter.from_dict separates known and extra fields."""
    data = {
        "title": "My Post",
        "tags": ["python"],
        "custom_field": "value",
    }
    fm = Frontmatter.from_dict(data)

    assert fm.title == "My Post"
    assert fm.tags == ["python"]
    assert fm.extra["custom_field"] == "value"


def test_frontmatter_dict_access():
    """Frontmatter supports dict-style access for templates."""
    fm = Frontmatter(title="Test", extra={"custom": "value"})

    assert fm["title"] == "Test"
    assert fm["custom"] == "value"
    assert fm.get("missing") is None


def test_frontmatter_iteration():
    """Frontmatter.keys() and .items() work for templates."""
    fm = Frontmatter(title="Test", tags=["a", "b"])

    keys = list(fm.keys())
    assert "title" in keys
    assert "tags" in keys


# tests/unit/rendering/test_ast_types.py

def test_ast_node_type_narrowing():
    """Type narrowing works with match statement."""
    node: ASTNode = {"type": "heading", "level": 2, "children": [], "attrs": {}}

    match node["type"]:
        case "heading":
            assert node["level"] == 2  # Type narrowed
        case _:
            pytest.fail("Should match heading")
```

### Integration Tests

```python
# tests/integration/test_type_safety.py

def test_page_frontmatter_integration(site_with_content):
    """Page.frontmatter provides typed access to metadata."""
    site_with_content.discover_content()
    page = site_with_content.pages[0]

    # Typed access
    assert isinstance(page.frontmatter.title, str)
    assert isinstance(page.frontmatter.tags, list)

    # Dict access still works
    assert page.frontmatter["title"] == page.frontmatter.title


def test_template_dict_syntax_preserved(build_site):
    """Templates using dict syntax still work."""
    # Template: {{ page.frontmatter["title"] }}
    output = build_site()
    assert "My Post Title" in output
```

### Type Checking Tests

```bash
# Verify mypy catches errors in typed code
# tests/typecheck/test_frontmatter_types.py.txt (not run, just checked)

from bengal.core.page.frontmatter import Frontmatter

fm = Frontmatter()
title: str = fm.title  # OK
tags: list[str] = fm.tags  # OK
# wrong: int = fm.title  # mypy error: Incompatible types
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Template breakage | Low | High | Dict compatibility layer, comprehensive tests |
| Performance regression | Low | Medium | Lazy frontmatter creation, benchmark |
| Incomplete AST types | Medium | Low | Start with common nodes, extend as needed |
| mypy errors in user code | Low | Low | Types are internal, user code unchanged |
| Circular import issues | Low | Medium | TYPE_CHECKING pattern well-established |

---

## Implementation Plan

### Sprint 1: Forward References (2 hours)

- [ ] Add `TYPE_CHECKING` imports to `page/__init__.py`
- [ ] Type `_site` as `Site | None`
- [ ] Type `_section` property return
- [ ] Run mypy, fix any revealed issues

**Exit Criteria**: No `Any` for cross-module references, mypy passes

### Sprint 2: Frontmatter Dataclass (4 hours)

- [ ] Create `bengal/core/page/frontmatter.py`
- [ ] Add `Frontmatter` dataclass with dict compatibility
- [ ] Add `page.frontmatter` property
- [ ] Add unit tests for dict access, iteration
- [ ] Verify templates still work

**Exit Criteria**: `page.frontmatter.title` works, templates unchanged

### Sprint 3: AST Types (3 hours)

- [ ] Create `bengal/rendering/ast_types.py`
- [ ] Define `ASTNode` union with common types
- [ ] Update `Page.parsed_ast` type
- [ ] Add type guards for common patterns
- [ ] Run mypy on rendering module

**Exit Criteria**: `parsed_ast` typed, mypy passes on rendering/

### Sprint 4: Directive Tokens (2 hours)

- [ ] Create `bengal/directives/tokens.py`
- [ ] Define `DirectiveToken` TypedDict
- [ ] Update `ContractValidator` signatures
- [ ] Update directive base class
- [ ] Run mypy on directives/

**Exit Criteria**: Directive validation fully typed

**Total Estimate**: 11 hours (~1.5 days)

---

## Success Criteria

### Quantitative

- [ ] Zero `Any` in public method signatures of Page, PageCore, DirectiveContract
- [ ] 100% mypy pass rate (current baseline maintained)
- [ ] No template test failures
- [ ] < 1% performance regression in build benchmarks

### Qualitative

- [ ] IDE autocomplete works for `page.frontmatter.title`
- [ ] Type checker catches invalid AST access
- [ ] New developers understand expected structures from types
- [ ] "Types as documentation" principle strengthened

---

## Open Questions

- [ ] Should `Frontmatter` support `**kwargs` for unknown fields in constructor?
- [ ] Should we add runtime validation (pydantic-style) or stay pure types?
- [ ] Which AST node types are essential vs. nice-to-have?
- [ ] Should `DirectiveToken` use `Literal` for known directive types?

---

## References

- **Evidence**: `bengal/core/page/__init__.py:153-199` - Current `Any` usage
- **Pattern**: `bengal/core/page/page_core.py` - PageCore as typed contract
- **Pattern**: `bengal/directives/contracts.py` - DirectiveContract frozen dataclass
- **Rule**: `bengal/.cursor/rules/python-style.mdc` - Type hint requirements
- **Guide**: `TYPE_CHECKING_GUIDE.md` - Forward reference patterns
- **Config**: `pyproject.toml` - mypy strict settings

---

## Appendix: Fundamental Limitations

Some `Any` usage is **intentional and correct**:

1. **User-defined frontmatter** - `extra: dict[str, Any]` is the right type for genuinely dynamic data
2. **Plugin return values** - Third-party plugins may return arbitrary types
3. **External library interop** - Some libraries lack type stubs

The goal is not to eliminate all `Any`, but to **use it deliberately at boundaries** and convert to typed structures immediately inside Bengal's code.
