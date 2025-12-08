# RFC: Typed Metadata Access (Phase 6)

**Status**: Draft  
**Author**: AI Assistant  
**Created**: 2025-12-08  
**Depends On**: RFC Typed Autodoc Models (implemented)

---

## Executive Summary

Phase 1 added `typed_metadata` dataclasses to `DocElement` with dual-write in extractors. Phase 6 migrates consumers (orchestrator, template helpers) to use type-safe access patterns, providing IDE autocomplete and compile-time error detection.

**Goal**: Replace 23+ `.metadata.get()` calls with type-safe `typed_metadata` access while maintaining backward compatibility.

---

## Current State

### Evidence: `.metadata.get()` Usage Patterns

**bengal/autodoc/virtual_orchestrator.py** (12 usages):
```python
# Line 622 - OpenAPI tags for grouping
tags = element.metadata.get("tags", [])

# Line 791 - OpenAPI endpoint tags for section lookup
tags = element.metadata.get("tags", [])

# Line 876-877 - OpenAPI method/path for template selection
method = element.metadata.get("method", "").lower()
path = element.metadata.get("path", "").strip("/")

# Line 921 - Tags for page context
tags=element.metadata.get("tags", []) if element.metadata else []

# Lines 1028, 1058, 1067, 1124, 1141-1143, 1173 - Section metadata
section.metadata.get("type", "api-reference")
section.metadata.get("description", "")
p.metadata.get("element_type", "")
```

**bengal/autodoc/extractors/python.py** (5 usages):
```python
# Line 310-311 - Alias tracking
child.metadata["aliases"] = []
child.metadata["aliases"].append(alias_name)

# Line 377 - Property detection
method.metadata.get("decorators", [])

# Line 847 - Inheritance base classes
bases = class_elem.metadata.get("bases", [])

# Line 891-892 - Inherited member detection
member.metadata.get("is_property")
```

**bengal/autodoc/extractors/openapi.py** (6 usages):
```python
# Lines 94-104 - Output path determination
element.metadata.get("tags")
element.metadata["tags"][0]
element.metadata.get("operation_id")
element.metadata.get("method", "op")
element.metadata.get("path", "path")
```

---

## Proposed Solution

### Option A: Helper Functions with Fallback (Recommended)

Create type-safe helper functions that use `typed_metadata` when available with fallback to untyped `metadata`:

```python
# bengal/autodoc/utils.py (add to existing)

from bengal.autodoc.models import (
    PythonClassMetadata,
    PythonFunctionMetadata,
    OpenAPIEndpointMetadata,
    CLICommandMetadata,
)

def get_python_class_bases(element: DocElement) -> tuple[str, ...]:
    """Get class bases with type-safe access."""
    if isinstance(element.typed_metadata, PythonClassMetadata):
        return element.typed_metadata.bases
    return tuple(element.metadata.get("bases", []))

def get_python_function_decorators(element: DocElement) -> tuple[str, ...]:
    """Get function decorators with type-safe access."""
    if isinstance(element.typed_metadata, PythonFunctionMetadata):
        return element.typed_metadata.decorators
    return tuple(element.metadata.get("decorators", []))

def get_openapi_tags(element: DocElement) -> tuple[str, ...]:
    """Get OpenAPI endpoint tags with type-safe access."""
    if isinstance(element.typed_metadata, OpenAPIEndpointMetadata):
        return element.typed_metadata.tags
    return tuple(element.metadata.get("tags", []))

def get_openapi_method(element: DocElement) -> str:
    """Get OpenAPI HTTP method with type-safe access."""
    if isinstance(element.typed_metadata, OpenAPIEndpointMetadata):
        return element.typed_metadata.method
    return element.metadata.get("method", "").upper()

def get_openapi_path(element: DocElement) -> str:
    """Get OpenAPI endpoint path with type-safe access."""
    if isinstance(element.typed_metadata, OpenAPIEndpointMetadata):
        return element.typed_metadata.path
    return element.metadata.get("path", "")
```

**Pros**:
- Gradual migration
- Single point of change
- Backward compatible
- Clear fallback semantics

**Cons**:
- Many small helper functions
- Indirection layer

### Option B: Generic Accessor with Type Narrowing

```python
def get_typed_field[T](
    element: DocElement,
    metadata_type: type[T],
    field: str,
    default: Any = None,
) -> Any:
    """
    Get field from typed_metadata with fallback to metadata dict.

    Usage:
        bases = get_typed_field(elem, PythonClassMetadata, "bases", ())
    """
    if isinstance(element.typed_metadata, metadata_type):
        return getattr(element.typed_metadata, field, default)
    return element.metadata.get(field, default)
```

**Pros**:
- Single function
- Flexible

**Cons**:
- No IDE autocomplete for field names
- Runtime field lookup
- Less type safety

### Option C: Protocol-Based Access

```python
class HasBases(Protocol):
    bases: tuple[str, ...]

def get_bases(element: DocElement) -> tuple[str, ...]:
    if isinstance(element.typed_metadata, HasBases):
        return element.typed_metadata.bases
    return tuple(element.metadata.get("bases", []))
```

**Pros**:
- Protocol-based typing
- Works across metadata types

**Cons**:
- Protocols add complexity
- Multiple protocol definitions needed

---

## Recommendation

**Option A (Helper Functions)** - Most practical approach:
- Clear, explicit helpers for each access pattern
- Full IDE support
- Easy to understand and maintain
- Can add new helpers as needed

---

## Implementation Plan

### Phase 6.1: Create Helper Module

Add typed access helpers to `bengal/autodoc/utils.py`:

```python
# Python metadata accessors
def get_python_class_bases(element: DocElement) -> tuple[str, ...]
def get_python_class_decorators(element: DocElement) -> tuple[str, ...]
def get_python_function_decorators(element: DocElement) -> tuple[str, ...]
def get_python_function_is_property(element: DocElement) -> bool

# CLI metadata accessors
def get_cli_command_callback(element: DocElement) -> str | None
def get_cli_option_type(element: DocElement) -> str

# OpenAPI metadata accessors
def get_openapi_tags(element: DocElement) -> tuple[str, ...]
def get_openapi_method(element: DocElement) -> str
def get_openapi_path(element: DocElement) -> str
def get_openapi_operation_id(element: DocElement) -> str | None
```

### Phase 6.2: Update Virtual Orchestrator

Replace `.metadata.get()` calls with typed helpers:

```python
# Before
tags = element.metadata.get("tags", [])

# After
from bengal.autodoc.utils import get_openapi_tags
tags = get_openapi_tags(element)
```

### Phase 6.3: Update Extractors

Replace internal `.metadata.get()` calls in extractors:

```python
# Before (python.py:847)
bases = class_elem.metadata.get("bases", [])

# After
bases = get_python_class_bases(class_elem)
```

### Phase 6.4: Add Tests

Test helper functions with both typed and untyped metadata:

```python
def test_get_python_class_bases_from_typed():
    meta = PythonClassMetadata(bases=("Base1", "Base2"))
    elem = DocElement(..., typed_metadata=meta)
    assert get_python_class_bases(elem) == ("Base1", "Base2")

def test_get_python_class_bases_fallback_to_untyped():
    elem = DocElement(..., metadata={"bases": ["Base1"]})
    assert get_python_class_bases(elem) == ("Base1",)
```

### Phase 6.5: Update Documentation

Update `bengal/autodoc/README.md` to document:
- `typed_metadata` field
- Helper functions
- Migration guide for theme authors

---

## Migration Strategy

1. **Non-breaking**: Helpers work with both typed and untyped metadata
2. **Incremental**: Can migrate one file at a time
3. **Testable**: Each migration is independently testable
4. **Reversible**: Can always fall back to `.metadata.get()`

---

## Success Criteria

- [ ] All 23 `.metadata.get()` calls migrated to typed helpers
- [ ] IDE autocomplete works for helper function return types
- [ ] All existing tests pass
- [ ] New tests for helper functions (both typed and untyped paths)
- [ ] Documentation updated

---

## Future Work (Phase 7)

Once Phase 6 is complete and stable:
- Add deprecation warnings to `metadata` dict access
- Warn when `typed_metadata` is None but could be set
- Track migration progress

---

## References

- Implemented RFC: `plan/implemented/rfc-typed-autodoc-models.md`
- Implemented Plan: `plan/implemented/plan-typed-autodoc-models.md`
- Evidence locations: See grep results above
