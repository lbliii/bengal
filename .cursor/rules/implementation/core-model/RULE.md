---
description: Guide for safely modifying Bengal's core models (Page, Site, Section)
alwaysApply: false
globs: ["bengal/core/**/*.py"]
---

# Modify Core Model

Guide for safely modifying Bengal's core models. Core models have the **highest quality bar** because they're used everywhere.

**Shortcut**: `::modify-core`

**Works with**: `modules/types-as-contracts`, `modules/architecture-patterns`

---

## ⚠️ High-Risk Zone

Changes to `bengal/core/` affect:
- Every page build
- All templates
- Cache invalidation
- Test fixtures

**Quality gate**: 90% confidence required for core changes.

---

## Core Principles for Core Models

### 1. Models Are Passive

```python
# ✅ CORRECT - Data only
@dataclass
class Page:
    source_path: Path
    content: str

    @property
    def title(self) -> str:
        return self.metadata.get("title", "")

# ❌ WRONG - No I/O or logging
@dataclass
class Page:
    def save(self):
        self.path.write_text(self.content)  # NO!
```

### 2. Types Are Contracts

```python
# ✅ CORRECT - Frozen, typed, documented
@dataclass(frozen=True)
class PageCore:
    """Immutable page metadata - the contract."""
    source_path: str
    title: str
    date: datetime | None = None

# ❌ WRONG - Mutable, untyped
class PageCore:
    def __init__(self, data):
        self.data = data  # What's in data? Who knows!
```

### 3. Composition Over Modification

```python
# ✅ CORRECT - Add via mixin
class NewCapabilityMixin:
    """Adds new capability to Page."""
    @property
    def new_property(self) -> str:
        return compute_something(self.core)

@dataclass
class Page(ExistingMixins, NewCapabilityMixin):
    ...

# ❌ WRONG - Modify existing class directly
class Page:
    # Adding 50 new methods here...
```

---

## Procedure

### Step 1: Understand Current State

**Before any changes**, run:

```bash
# Understand the model
::research "How does Page work?"

# Check type coverage
::types bengal/core/

# Check architecture compliance
::arch bengal/core/
```

### Step 2: Define the Change as Types

**Write types before implementation**:

```python
# New field? Add to dataclass
@dataclass
class PageCore:
    # Existing fields...
    source_path: str
    title: str

    # New field with type
    new_field: NewType | None = None
```

```python
# New behavior? Add mixin
class NewBehaviorMixin:
    """Mixin providing [behavior]."""

    @property
    def new_property(self) -> ReturnType:
        """Returns [what it returns]."""
        ...
```

### Step 3: Check Cache Implications

**If modifying PageCore** (cacheable data):

1. **Cache must be invalidated** - Old caches have old schema
2. **Migration needed?** - Can old cache be upgraded?
3. **Version the cache** - Consider cache version bump

```python
# In bengal/cache/build_cache/
CACHE_VERSION = 3  # Bump when PageCore changes
```

### Step 4: Update Tests

**Tests to update/add**:

```
tests/unit/core/test_page.py          # Unit tests
tests/unit/core/test_page_core.py     # PageCore tests
tests/integration/test_build.py       # Build integration
tests/roots/test-basic/               # Test fixture if needed
```

```python
def test_new_field_default():
    """New field should have sensible default."""
    core = PageCore(source_path="test.md", title="Test")
    assert core.new_field is None


def test_new_field_serialization():
    """New field should serialize for cache."""
    core = PageCore(source_path="test.md", title="Test", new_field=value)
    data = core.to_dict()
    restored = PageCore.from_dict(data)
    assert restored.new_field == core.new_field
```

### Step 5: Update Dependent Code

**Search for usages**:

```bash
# Find all usages of the class
grep -rn "PageCore" bengal/ tests/

# Find all usages of specific attribute
grep -rn "\.source_path" bengal/
```

**Common dependents**:
- `bengal/core/page/__init__.py` - Page class
- `bengal/cache/` - Cache serialization
- `bengal/orchestration/` - Build operations
- Templates in `bengal/themes/`

### Step 6: Run Full Validation

```bash
# Type check
mypy bengal/core/

# Architecture check
::arch bengal/core/

# Run tests
pytest tests/unit/core/ tests/integration/ -v

# Full validation
::validate
```

---

## Checklist

Before modifying core:

- [ ] **Researched** current implementation (`::research`)
- [ ] **Types defined** before implementation
- [ ] **No I/O added** to models
- [ ] **No logging added** to models
- [ ] **Cache implications** considered
- [ ] **Mixin used** for new behavior (vs modifying existing)
- [ ] **Tests updated** in unit and integration
- [ ] **Dependents updated** (search for usages)
- [ ] **mypy passes** (`mypy bengal/core/`)
- [ ] **Architecture audit passes** (`::arch`)
- [ ] **Full test suite passes**
- [ ] **Confidence ≥ 90%** (`::validate`)

---

## Common Changes

### Adding a Field to PageCore

```python
# 1. Add to PageCore (bengal/core/page/page_core.py)
@dataclass(frozen=True)
class PageCore:
    # Existing...
    new_field: str | None = None  # Add with default

# 2. Update from_dict/to_dict
def to_dict(self) -> dict:
    return {
        **existing,
        "new_field": self.new_field,
    }

@classmethod
def from_dict(cls, data: dict) -> PageCore:
    return cls(
        **existing,
        new_field=data.get("new_field"),
    )

# 3. Bump cache version
CACHE_VERSION = 4
```

### Adding a Property to Page

```python
# 1. Add mixin (bengal/core/page/new_mixin.py)
class NewMixin:
    core: PageCore  # Type hint for mypy

    @property
    def new_property(self) -> str:
        return compute(self.core)

# 2. Add to Page (bengal/core/page/__init__.py)
@dataclass
class Page(ExistingMixins, NewMixin):
    ...
```

### Modifying Site

```python
# Site is simpler - just a container
@dataclass
class Site:
    # Add new collection
    new_collection: list[NewThing] = field(default_factory=list)

    # Add property (NOT method with I/O)
    @property
    def new_derived(self) -> DerivedType:
        return compute(self.pages)
```

---

## Anti-Patterns

### ❌ Adding I/O to Model

```python
class Site:
    def save_to_disk(self):
        # NO! Use orchestrator instead
```

### ❌ Logging in Model

```python
class Page:
    @property
    def url(self):
        logger.debug(f"Computing URL")  # NO!
```

### ❌ Growing God Object

```python
class Page:
    # 50 methods later...
    # NO! Use mixins instead
```

### ❌ Untyped Additions

```python
class PageCore:
    extra_stuff = None  # NO! Type it!
```

---

## Related

- `modules/types-as-contracts` - Type-first philosophy
- `modules/architecture-patterns` - Model/orchestrator split
- `validation/type-audit` - Type system audit
- `validation/architecture-audit` - Architecture audit
- `bengal/core/page/` - Page model package
- `bengal/core/site.py` - Site model
