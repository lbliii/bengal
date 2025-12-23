---
description: Type-first development guide - define contracts before implementation
alwaysApply: false
globs: ["bengal/**/*.py"]
---

# Type-First Development

Guide for developing features in Bengal using the type-first philosophy: **define types and contracts before writing implementation**.

**Shortcut**: Part of `::implement` for new features

**Works with**: `modules/types-as-contracts`, `modules/architecture-patterns`

---

## Philosophy

> **Type signatures should be more important than implementations.**

When you define types first:
1. You think about the contract before the code
2. IDE gives you autocomplete immediately
3. Tests can be written against the types
4. Implementation becomes filling in the blanks

---

## Procedure

### Step 1: Define the Contract (Types)

**Start with a frozen dataclass** for data:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class NewFeatureData:
    """
    Immutable data for [feature].

    This is the contract - type signature defines expected structure.

    Attributes:
        id: Unique identifier
        name: Display name
        created: Creation timestamp
        tags: Associated tags (immutable tuple)
    """
    id: str
    name: str
    created: datetime
    tags: tuple[str, ...] = ()
```

**Define method signatures** with types:

```python
class FeatureProcessor:
    """Processes [feature] data."""

    def process(self, data: NewFeatureData) -> ProcessedResult:
        """
        Process the feature data.

        Args:
            data: Input data conforming to NewFeatureData contract

        Returns:
            Processed result with derived fields

        Raises:
            ValidationError: If data fails validation
        """
        ...  # Implementation comes later
```

### Step 2: Write Tests Against Types

**Tests can run before implementation exists**:

```python
def test_feature_data_is_immutable():
    """NewFeatureData should be immutable (frozen)."""
    data = NewFeatureData(id="1", name="test", created=datetime.now())

    with pytest.raises(FrozenInstanceError):
        data.name = "changed"


def test_feature_processor_signature():
    """FeatureProcessor.process accepts NewFeatureData and returns ProcessedResult."""
    processor = FeatureProcessor()
    data = NewFeatureData(id="1", name="test", created=datetime.now())

    result = processor.process(data)

    assert isinstance(result, ProcessedResult)
```

### Step 3: Implement to Satisfy Types

**Now fill in the implementation**:

```python
def process(self, data: NewFeatureData) -> ProcessedResult:
    """Implementation that satisfies the type contract."""
    # mypy ensures we return ProcessedResult
    return ProcessedResult(
        data_id=data.id,
        processed_name=data.name.upper(),
        tag_count=len(data.tags),
    )
```

---

## Type Patterns to Use

### Pattern 1: Frozen Dataclasses for Contracts

```python
@dataclass(frozen=True)
class PageCore:
    """Immutable, hashable, cacheable."""
    source_path: str
    title: str
    date: datetime | None = None
```

**Use when**: Data should not change after creation (cache keys, config)

### Pattern 2: TypedDict for Known Structures

```python
class KnownFrontmatter(TypedDict, total=False):
    title: str
    date: datetime | None
    tags: list[str]
    draft: bool
```

**Use when**: Working with dicts that have known keys (parsed YAML, JSON)

### Pattern 3: Protocol for Duck Typing

```python
from typing import Protocol

class Renderable(Protocol):
    """Any object that can be rendered."""
    def render(self, context: RenderContext) -> str: ...

def render_item(item: Renderable) -> str:
    """Works with any object implementing render()."""
    return item.render(context)
```

**Use when**: Multiple types share behavior without inheritance

### Pattern 4: Discriminated Unions

```python
class TextNode(TypedDict):
    type: Literal["text"]
    content: str

class HeadingNode(TypedDict):
    type: Literal["heading"]
    level: int
    children: list[ASTNode]

ASTNode = TextNode | HeadingNode | ...

def process_node(node: ASTNode) -> str:
    match node["type"]:
        case "text":
            return node["content"]  # Type narrowed!
        case "heading":
            return f"<h{node['level']}>"  # Type narrowed!
```

**Use when**: Multiple related types distinguished by a field

### Pattern 5: Forward References

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.site import Site

@dataclass
class Page:
    _site: Site | None = field(default=None)
```

**Use when**: Circular imports would occur

---

## Anti-Patterns to Avoid

### ❌ Implementation-First

```python
# BAD - Figuring out types as you go
def process_data(data):
    result = {}
    result["name"] = data.get("name", "")
    result["count"] = len(data.get("items", []))
    return result
```

### ✅ Types-First

```python
# GOOD - Contract is clear before implementation
@dataclass
class InputData:
    name: str
    items: list[Item]

@dataclass
class ProcessedData:
    name: str
    count: int

def process_data(data: InputData) -> ProcessedData:
    return ProcessedData(name=data.name, count=len(data.items))
```

### ❌ Any Everywhere

```python
# BAD - No type safety
def get_config() -> Any:
    return load_yaml("config.yaml")
```

### ✅ Typed Return

```python
# GOOD - Contract is explicit
def get_config() -> BengalConfig:
    data = load_yaml("config.yaml")
    return BengalConfig.from_dict(data)
```

---

## Checklist

Before implementing a new feature:

- [ ] **Define data types** as frozen dataclasses
- [ ] **Write method signatures** with full type hints
- [ ] **Add docstrings** explaining the contract
- [ ] **Write tests** against the types (can fail initially)
- [ ] **Run mypy** to verify types are correct
- [ ] **Implement** to satisfy the types
- [ ] **Tests pass** with implementation

---

## Example: Adding a New Index

### Step 1: Define Types

```python
# bengal/cache/indexes/new_index.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page


@dataclass(frozen=True)
class IndexEntry:
    """Single entry in the index."""
    page_path: str
    value: str
    weight: int = 0


@dataclass
class NewIndex:
    """Index for [purpose]."""

    entries: dict[str, list[IndexEntry]] = field(default_factory=dict)

    def add(self, key: str, entry: IndexEntry) -> None:
        """Add an entry to the index."""
        ...

    def query(self, key: str) -> list[IndexEntry]:
        """Query entries by key."""
        ...

    @classmethod
    def from_pages(cls, pages: list[Page]) -> NewIndex:
        """Build index from pages."""
        ...
```

### Step 2: Write Tests

```python
# tests/unit/cache/indexes/test_new_index.py

def test_index_entry_is_immutable():
    entry = IndexEntry(page_path="test.md", value="test")
    with pytest.raises(FrozenInstanceError):
        entry.value = "changed"


def test_index_add_and_query():
    index = NewIndex()
    entry = IndexEntry(page_path="page.md", value="test")

    index.add("key", entry)

    results = index.query("key")
    assert entry in results
```

### Step 3: Implement

```python
def add(self, key: str, entry: IndexEntry) -> None:
    if key not in self.entries:
        self.entries[key] = []
    self.entries[key].append(entry)

def query(self, key: str) -> list[IndexEntry]:
    return self.entries.get(key, [])
```

---

## Related

- `modules/types-as-contracts` - Philosophy
- [RFC: Type System Hardening](plan/ready/rfc-type-system-hardening.md)
- [TYPE_CHECKING_GUIDE.md](TYPE_CHECKING_GUIDE.md)
- `validation/type-audit` - Audit type compliance
