# RFC: Type System Hardening - Strict Boundaries & Zero Shims

**Status**: Draft
**Created**: 2025-12-22
**Author**: AI-assisted
**Confidence**: 92% 🟢
**Category**: Architecture / Type Safety

---

## Executive Summary

Bengal's type system is strong at the architectural level but leaks `Any` at boundaries (metadata, AST, directive tokens). This RFC proposes a **strict, zero-shim** hardening of the type system.

**Decision**: Backward compatibility for template dict-style access (`page.metadata["key"]`) is intentionally sacrificed to achieve a clean, purely typed object model with no legacy holdovers.

**Principle**: Type signatures are the source of truth. Interfaces must be strictly typed to enable maximum IDE support, static verification, and architectural clarity.

---

## Problem Statement

### Current State
Several boundaries in Bengal use `Any`, creating "blind spots" for both the type checker and developers:

1. **`Page.metadata`**: Currently `dict[str, Any]`. Templates and core logic rely on string-key access which lacks autocomplete and static verification.
2. **`Page.parsed_ast`**: Currently `Any | None`. AST processing is a common source of bugs that are currently only caught at runtime.
3. **Circular Imports**: `Page._site` uses `Any` to avoid circularity, losing the `Site` contract.
4. **Directive Tokens**: `validate_children` receives `list[dict[str, Any]]`, making validator logic fragile.

### Impact
- **Maintenance Burden**: Refactoring frontmatter fields requires manual grep instead of IDE refactoring tools.
- **Runtime Fragility**: Typo in a metadata key or AST property name fails at runtime.
- **Cognitive Load**: Developers must remember field names instead of relying on types.

---

## Goals & Non-Goals

### Goals
1. **Zero `Any` at Boundaries**: All public interfaces must use concrete types or strictly defined unions.
2. **Clean Code Only**: No shims, no `__getitem__` overrides for backward compatibility, no `dict` fallbacks.
3. **Strict Page Model**: `Page.metadata` becomes a typed `Frontmatter` object.
4. **IDE First**: Enable 100% autocomplete for all known metadata and AST structures.

### Non-Goals
- **Backward Compatibility**: We do NOT care about preserving `page.metadata["title"]` if it hinders type safety.
- **Runtime Validation**: This remains a static type effort (mypy); no Pydantic runtime overhead.
- **Hybrid Support**: We will not provide "legacy shims" during transition.

---

## Design: Strict Typing

### 1. The `Frontmatter` Dataclass (Strict)
Replace the raw metadata dict with a pure dataclass.

```python
# bengal/core/page/frontmatter.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass(frozen=True, slots=True)
class Frontmatter:
    """
    Pure typed frontmatter. No dict shims.
    """
    title: str = ""
    date: datetime | None = None
    tags: list[str] = field(default_factory=list)
    slug: str | None = None
    weight: int | None = None
    lang: str | None = None
    type: str | None = None
    layout: str | None = None
    description: str | None = None
    draft: bool = False
    aliases: list[str] = field(default_factory=list)

    # Strictly for unmapped user data
    extra: dict[str, Any] = field(default_factory=dict)
```

### 2. Refactored `Page` Model
The `Page` model adopts the `Frontmatter` class as its primary metadata storage.

```python
# bengal/core/page/__init__.py
@dataclass
class Page:
    source_path: Path
    content: str = ""
    metadata: Frontmatter = field(default_factory=Frontmatter) # No more dict[str, Any]

    # ...
```

### 3. Strict AST Node Unions
Define a comprehensive union for AST nodes using `TypedDict` for performance and `Literal` for narrowing.

```python
# bengal/rendering/ast_types.py
from typing import Literal, TypedDict, Union

class TextNode(TypedDict):
    type: Literal["text"]
    raw: str

class HeadingNode(TypedDict):
    type: Literal["heading"]
    level: int
    children: list[ASTNode]
    attrs: dict[str, str]

# ... other nodes ...

ASTNode = Union[TextNode, HeadingNode, ParagraphNode, ...]
```

### 4. Strict Directive Tokens
Formalize the token structure passed to validators.

```python
# bengal/directives/tokens.py
class DirectiveToken(TypedDict):
    type: str
    children: list[DirectiveToken]
    attrs: dict[str, str]
    raw: str
    body: str | None
```

---

## Architecture Impact

| Subsystem | Change | Impact |
|-----------|--------|--------|
| **Core** | `Page.metadata` changed to `Frontmatter` | **High**. Requires update to all metadata consumers. |
| **Templates** | Access changes from `metadata["title"]` to `metadata.title` | **High**. Breaks legacy templates. |
| **Rendering** | `parsed_ast` fully typed | **Medium**. Improves parser reliability. |
| **Directives** | Token validation fully typed | **Low**. Simplifies validator logic. |

---

## Testing Strategy

### 1. Static Verification
- **mypy**: 100% pass on all core modules with zero `--allow-any` flags.
- **refactor-test**: Verify IDE can rename `Frontmatter.title` and update all usages automatically.

### 2. Unit Tests
- `test_frontmatter_parsing`: Verify YAML maps correctly to `Frontmatter` fields.
- `test_ast_narrowing`: Verify `match node["type"]` correctly narrows to specific node types.

---

## Implementation Plan

### Sprint 1: Strict Core Hardening
1. Introduce `Frontmatter` dataclass.
2. Update `Page` definition and fix all internal references (properties).
3. Update `PageCore` to match `Frontmatter` fields exactly.

### Sprint 2: AST & Rendering
1. Introduce `ast_types.py`.
2. Update `MarkdownParser` to return `list[ASTNode]`.
3. Update all shortcode/rendering logic to use `match` on typed nodes.

### Sprint 3: Directives & Cleanup
1. Introduce `DirectiveToken` TypedDict.
2. Update `ContractValidator.validate_children` signature.
3. Final `grep` for `Any` and `dict[str, Any]` at module boundaries.

---

## Success Criteria
- [ ] No `dict[str, Any]` used for internal metadata propagation.
- [ ] No `__getitem__` or `get()` methods in `Frontmatter`.
- [ ] 100% autocomplete in VS Code/Cursor for all Page attributes.
- [ ] Zero shims in the codebase for legacy support.
