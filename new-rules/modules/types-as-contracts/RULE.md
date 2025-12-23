---
description: Bengal's core philosophy - type signatures are contracts that define behavior
alwaysApply: false
globs: ["bengal/**/*.py", "tests/**/*.py"]
---

# Types as Contracts

Bengal treats **type signatures as contracts** that are more important than implementations. Where types exist, they define the expected behavior. Where `Any` appears, it represents a deliberate escape hatch.

**Works with**: `modules/evidence-handling`, `modules/architecture-patterns`

---

## Core Principle

> **Type signatures should be more important than implementations.**
>
> Where Bengal currently uses `Any`, the implementation becomes the only source of truth—violating this principle.

This means:

1. **Types document intent** - Reading a type signature should tell you what a function does
2. **Types enable tooling** - IDE autocomplete, mypy catches bugs before runtime
3. **Types are testable** - Type contracts can be verified statically
4. **Types survive refactoring** - Implementations change, contracts remain stable

---

## Type-First Development

When implementing features in Bengal:

### Step 1: Define Types First

```python
# ✅ CORRECT - Define the contract before implementation
@dataclass(frozen=True)
class PageCore:
    """Immutable, cacheable page metadata - the contract."""
    source_path: str
    title: str
    date: datetime | None = None
    tags: tuple[str, ...] = ()

# Implementation follows the contract
class Page:
    core: PageCore  # Type defines the relationship
```

### Step 2: Use Precise Types (Avoid `Any`)

```python
# ✅ CORRECT - Precise types
def get_pages_by_tag(tag: str) -> list[Page]:
    ...

# ❌ WRONG - Loses type safety
def get_pages_by_tag(tag: str) -> list[Any]:
    ...
```

### Step 3: Use TypedDict for Known Structures

```python
# ✅ CORRECT - Known structure typed
class KnownFrontmatter(TypedDict, total=False):
    title: str
    date: datetime | None
    tags: list[str]
    draft: bool

# ❌ WRONG - Untyped dict
metadata: dict[str, Any]  # No IDE support
```

### Step 4: Use `TYPE_CHECKING` for Circular Imports

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site

@dataclass
class Page:
    _site: Site | None = field(default=None, repr=False)
```

---

## When `Any` is Acceptable

`Any` is a deliberate escape hatch for genuinely dynamic data:

| Location | Type | Justification |
|----------|------|---------------|
| `Frontmatter.extra` | `dict[str, Any]` | User-defined fields are genuinely unknown |
| Plugin return values | `Any` | Third-party plugins may return arbitrary types |
| External library interop | `Any` | Some libraries lack type stubs |

**The rule**: Use `Any` at boundaries, convert to typed structures immediately inside Bengal's code.

---

## Type Patterns in Bengal

### Pattern 1: Frozen Dataclasses as Contracts

```python
@dataclass(frozen=True)
class DirectiveContract:
    """Type IS the validation spec - frozen for immutability."""
    name: str
    allowed_children: frozenset[str] = frozenset()
    required_args: tuple[str, ...] = ()
    optional_args: frozenset[str] = frozenset()
```

**Evidence**: `bengal/directives/contracts.py`

### Pattern 2: Composition via Core Objects

```python
@dataclass
class Page:
    core: PageCore          # Typed contract
    content: str
    rendered_html: str | None = None

    @property
    def title(self) -> str:
        return self.core.title  # Delegates to typed core
```

**Evidence**: `bengal/core/page/__init__.py`

### Pattern 3: Protocol Classes for Duck Typing

```python
from typing import Protocol

class Cacheable(Protocol):
    """Protocol for objects that can be cached."""
    def cache_key(self) -> str: ...
    def to_dict(self) -> dict[str, Any]: ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self: ...
```

**Evidence**: `bengal/cache/cacheable.py`

### Pattern 4: Discriminated Unions

```python
from typing import Literal, TypedDict

class TextNode(TypedDict):
    type: Literal["text"]
    raw: str

class HeadingNode(TypedDict):
    type: Literal["heading"]
    level: int
    children: list[ASTNode]

ASTNode = TextNode | HeadingNode | ParagraphNode | ...

# Usage with match statement
match node["type"]:
    case "heading":
        level = node["level"]  # Type narrowed!
```

---

## Validation Checklist

When reviewing code, verify:

- [ ] **No untyped public functions** - All public methods have return types
- [ ] **No `Any` in signatures** - Except documented escape hatches
- [ ] **Forward references for circular imports** - Use `TYPE_CHECKING`
- [ ] **TypedDict for known structures** - Dict literals with known keys
- [ ] **Frozen dataclasses for contracts** - Immutable, hashable, cacheable
- [ ] **Protocols for duck typing** - Interface contracts without inheritance

---

## Anti-Patterns

### ❌ Dictionary Soup

```python
# BAD - No type safety
def process_page(data: dict) -> dict:
    return {"title": data["title"], "content": data["content"]}
```

### ✅ Typed Structures

```python
# GOOD - Types define the contract
def process_page(page: Page) -> RenderedPage:
    return RenderedPage(title=page.title, html=render(page.content))
```

### ❌ Implicit `Any` via Missing Hints

```python
# BAD - No return type = implicit Any
def get_config():
    return load_yaml("config.yaml")
```

### ✅ Explicit Return Types

```python
# GOOD - Contract is explicit
def get_config() -> BengalConfig:
    return BengalConfig.from_yaml("config.yaml")
```

---

## Quick Reference

| Principle | Application |
|-----------|-------------|
| Types first | Define types before implementation |
| Avoid `Any` | Use precise types, TypedDict, Protocols |
| Frozen contracts | Use `frozen=True` for immutable data |
| Forward refs | Use `TYPE_CHECKING` for circular imports |
| Discriminated unions | Use `Literal` for type narrowing |

---

## Related

- [RFC: Type System Hardening](plan/ready/rfc-type-system-hardening.md)
- [TYPE_CHECKING_GUIDE.md](TYPE_CHECKING_GUIDE.md)
- `pyproject.toml` - mypy strict settings
