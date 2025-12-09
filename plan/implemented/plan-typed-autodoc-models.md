# Plan: Typed Autodoc Models

**Source RFC**: `plan/active/rfc-typed-autodoc-models.md`  
**Status**: Ready for Implementation  
**Created**: 2025-12-08  
**Estimated Effort**: 3-4 days

---

## Overview

Convert the RFC for typed autodoc models into implementation tasks. The approach is **Option A: Discriminated Union with Typed Metadata** with phased rollout to minimize risk.

### Goals

1. Create typed metadata dataclasses for Python, CLI, and OpenAPI domains
2. Add `typed_metadata` field to `DocElement`
3. Update extractors to populate typed metadata
4. Preserve backward compatibility with existing `metadata` dict

### Non-Goals (This Plan)

- Full migration to Option B (separate element classes)
- Removing the `metadata` dict (Phase 3 - future plan)
- Changing template rendering (separate plan)

---

## Phase 1: Create Typed Models Package

### Task 1.1: Create `models/` package structure

**Subsystem**: autodoc/models  
**Dependencies**: None  
**Risk**: Low

Create the new models package with common types.

**Files to create**:
- `bengal/autodoc/models/__init__.py`
- `bengal/autodoc/models/common.py`

**Implementation**:

```python
# bengal/autodoc/models/common.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Source code location for a documented element."""
    file: str  # String for cacheability
    line: int
    column: int | None = None
    
    def __post_init__(self) -> None:
        if self.line < 1:
            raise ValueError(f"Line must be >= 1, got {self.line}")
    
    @classmethod
    def from_path(cls, path: Path, line: int, column: int | None = None) -> SourceLocation:
        """Create from Path object."""
        return cls(file=str(path), line=line, column=column)

@dataclass(frozen=True, slots=True)
class QualifiedName:
    """Validated qualified name for a documented element."""
    parts: tuple[str, ...]
    
    def __post_init__(self) -> None:
        if not self.parts:
            raise ValueError("QualifiedName cannot be empty")
        for part in self.parts:
            if not part:
                raise ValueError(f"QualifiedName contains empty part: {self.parts}")
    
    @classmethod
    def from_string(cls, qualified_name: str, separator: str = ".") -> QualifiedName:
        """Create from dot-separated string, filtering empty parts."""
        parts = tuple(p for p in qualified_name.split(separator) if p)
        return cls(parts=parts)
    
    def __str__(self) -> str:
        return ".".join(self.parts)
    
    @property
    def name(self) -> str:
        """Last part of the qualified name."""
        return self.parts[-1]
    
    @property
    def parent(self) -> QualifiedName | None:
        """Parent qualified name, or None if top-level."""
        if len(self.parts) <= 1:
            return None
        return QualifiedName(parts=self.parts[:-1])
```

**Pre-drafted commit**:
```bash
git add -A && git commit -m "autodoc(models): add common types SourceLocation and QualifiedName with validation"
```

---

### Task 1.2: Create Python metadata models

**Subsystem**: autodoc/models  
**Dependencies**: Task 1.1  
**Risk**: Low

**Files to create**:
- `bengal/autodoc/models/python.py`

**Implementation** (key dataclasses):

```python
# bengal/autodoc/models/python.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

@dataclass(frozen=True, slots=True)
class ParameterInfo:
    """Single function parameter."""
    name: str
    type_hint: str | None = None
    default: str | None = None
    kind: Literal["positional", "keyword", "var_positional", "var_keyword", "positional_or_keyword"] = "positional_or_keyword"
    description: str | None = None

@dataclass(frozen=True, slots=True)
class ParsedDocstring:
    """Parsed docstring information."""
    summary: str = ""
    description: str = ""
    params: tuple[ParameterInfo, ...] = ()
    returns: str | None = None
    raises: tuple[tuple[str, str], ...] = ()  # (exception_type, description)
    examples: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class PythonModuleMetadata:
    """Metadata specific to Python modules."""
    file_path: str
    is_package: bool = False
    has_all: bool = False
    all_exports: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class PythonClassMetadata:
    """Metadata specific to Python classes."""
    bases: tuple[str, ...] = ()
    decorators: tuple[str, ...] = ()
    is_exception: bool = False
    is_dataclass: bool = False
    is_abstract: bool = False
    parsed_doc: ParsedDocstring | None = None

@dataclass(frozen=True, slots=True)
class PythonFunctionMetadata:
    """Metadata specific to Python functions/methods."""
    signature: str = ""
    parameters: tuple[ParameterInfo, ...] = ()
    return_type: str | None = None
    is_async: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    is_property: bool = False
    is_generator: bool = False
    decorators: tuple[str, ...] = ()
    parsed_doc: ParsedDocstring | None = None

@dataclass(frozen=True, slots=True)
class PythonAttributeMetadata:
    """Metadata specific to Python attributes/class variables."""
    annotation: str | None = None
    is_class_var: bool = False
    default_value: str | None = None

@dataclass(frozen=True, slots=True)
class PythonAliasMetadata:
    """Metadata for import aliases."""
    alias_of: str
    alias_kind: Literal["assignment", "import"] = "assignment"
```

**Pre-drafted commit**:
```bash
git add -A && git commit -m "autodoc(models): add Python metadata dataclasses for module, class, function, attribute, alias"
```

---

### Task 1.3: Create CLI metadata models

**Subsystem**: autodoc/models  
**Dependencies**: Task 1.1  
**Risk**: Low

**Files to create**:
- `bengal/autodoc/models/cli.py`

**Implementation**:

```python
# bengal/autodoc/models/cli.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Any

@dataclass(frozen=True, slots=True)
class CLIOptionMetadata:
    """Metadata for CLI option."""
    name: str
    param_type: Literal["option", "argument"]
    type_name: str = "STRING"
    required: bool = False
    default: Any = None
    multiple: bool = False
    is_flag: bool = False
    count: bool = False
    opts: tuple[str, ...] = ()  # e.g., ("-v", "--verbose")
    envvar: str | None = None
    help_text: str = ""

@dataclass(frozen=True, slots=True)
class CLICommandMetadata:
    """Metadata specific to CLI commands."""
    callback: str | None = None
    option_count: int = 0
    argument_count: int = 0
    is_group: bool = False
    is_hidden: bool = False

@dataclass(frozen=True, slots=True)
class CLIGroupMetadata:
    """Metadata specific to CLI command groups."""
    callback: str | None = None
    command_count: int = 0
```

**Pre-drafted commit**:
```bash
git add -A && git commit -m "autodoc(models): add CLI metadata dataclasses for command, group, and option"
```

---

### Task 1.4: Create OpenAPI metadata models

**Subsystem**: autodoc/models  
**Dependencies**: Task 1.1  
**Risk**: Low

**Files to create**:
- `bengal/autodoc/models/openapi.py`

**Implementation**:

```python
# bengal/autodoc/models/openapi.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Any

type HTTPMethod = Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

@dataclass(frozen=True, slots=True)
class OpenAPIParameterMetadata:
    """Metadata for OpenAPI parameter."""
    name: str
    location: Literal["path", "query", "header", "cookie"]
    required: bool = False
    schema_type: str = "string"
    description: str = ""

@dataclass(frozen=True, slots=True)
class OpenAPIRequestBodyMetadata:
    """Metadata for OpenAPI request body."""
    content_type: str = "application/json"
    schema_ref: str | None = None
    required: bool = False
    description: str = ""

@dataclass(frozen=True, slots=True)
class OpenAPIResponseMetadata:
    """Metadata for OpenAPI response."""
    status_code: int | str  # "200" or "default"
    description: str = ""
    content_type: str | None = None
    schema_ref: str | None = None

@dataclass(frozen=True, slots=True)
class OpenAPIEndpointMetadata:
    """Metadata specific to OpenAPI endpoints."""
    method: HTTPMethod
    path: str
    operation_id: str | None = None
    summary: str | None = None
    tags: tuple[str, ...] = ()
    parameters: tuple[OpenAPIParameterMetadata, ...] = ()
    request_body: OpenAPIRequestBodyMetadata | None = None
    responses: tuple[OpenAPIResponseMetadata, ...] = ()
    security: tuple[str, ...] = ()
    deprecated: bool = False

@dataclass(frozen=True, slots=True)
class OpenAPIOverviewMetadata:
    """Metadata for OpenAPI spec overview."""
    version: str | None = None
    servers: tuple[str, ...] = ()
    security_schemes: dict[str, Any] = field(default_factory=dict)
    tags: tuple[dict[str, Any], ...] = ()

@dataclass(frozen=True, slots=True)
class OpenAPISchemaMetadata:
    """Metadata for OpenAPI schema/model."""
    schema_type: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    required: tuple[str, ...] = ()
    enum: tuple[Any, ...] | None = None
    example: Any = None
```

**Pre-drafted commit**:
```bash
git add -A && git commit -m "autodoc(models): add OpenAPI metadata dataclasses for endpoint, schema, overview"
```

---

### Task 1.5: Create union type and export models

**Subsystem**: autodoc/models  
**Dependencies**: Tasks 1.2-1.4  
**Risk**: Low

**Files to update**:
- `bengal/autodoc/models/__init__.py`

**Implementation**:

```python
# bengal/autodoc/models/__init__.py
"""
Typed metadata models for autodoc system.

This package provides type-safe metadata dataclasses that replace
the untyped `metadata: dict[str, Any]` field on DocElement.

Usage:
    from bengal.autodoc.models import PythonClassMetadata, DocMetadata
    
    if isinstance(element.typed_metadata, PythonClassMetadata):
        bases = element.typed_metadata.bases  # Type-safe!
"""
from __future__ import annotations

from bengal.autodoc.models.common import QualifiedName, SourceLocation
from bengal.autodoc.models.python import (
    ParameterInfo,
    ParsedDocstring,
    PythonAliasMetadata,
    PythonAttributeMetadata,
    PythonClassMetadata,
    PythonFunctionMetadata,
    PythonModuleMetadata,
)
from bengal.autodoc.models.cli import (
    CLICommandMetadata,
    CLIGroupMetadata,
    CLIOptionMetadata,
)
from bengal.autodoc.models.openapi import (
    HTTPMethod,
    OpenAPIEndpointMetadata,
    OpenAPIOverviewMetadata,
    OpenAPIParameterMetadata,
    OpenAPIRequestBodyMetadata,
    OpenAPIResponseMetadata,
    OpenAPISchemaMetadata,
)

# Union type for all metadata
type DocMetadata = (
    PythonModuleMetadata
    | PythonClassMetadata
    | PythonFunctionMetadata
    | PythonAttributeMetadata
    | PythonAliasMetadata
    | CLICommandMetadata
    | CLIGroupMetadata
    | CLIOptionMetadata
    | OpenAPIEndpointMetadata
    | OpenAPIOverviewMetadata
    | OpenAPISchemaMetadata
)

__all__ = [
    # Common
    "QualifiedName",
    "SourceLocation",
    # Python
    "ParameterInfo",
    "ParsedDocstring",
    "PythonAliasMetadata",
    "PythonAttributeMetadata",
    "PythonClassMetadata",
    "PythonFunctionMetadata",
    "PythonModuleMetadata",
    # CLI
    "CLICommandMetadata",
    "CLIGroupMetadata",
    "CLIOptionMetadata",
    # OpenAPI
    "HTTPMethod",
    "OpenAPIEndpointMetadata",
    "OpenAPIOverviewMetadata",
    "OpenAPIParameterMetadata",
    "OpenAPIRequestBodyMetadata",
    "OpenAPIResponseMetadata",
    "OpenAPISchemaMetadata",
    # Union
    "DocMetadata",
]
```

**Pre-drafted commit**:
```bash
git add -A && git commit -m "autodoc(models): export all metadata types and create DocMetadata union type"
```

---

## Phase 2: Integrate with DocElement

### Task 2.1: Add `typed_metadata` field to DocElement

**Subsystem**: autodoc/base  
**Dependencies**: Phase 1 complete  
**Risk**: Low (additive change)

**Files to update**:
- `bengal/autodoc/base.py`

**Changes**:

```python
# In base.py, update DocElement:
from bengal.autodoc.models import DocMetadata

@dataclass
class DocElement:
    # ... existing fields ...
    metadata: dict[str, Any] = field(default_factory=dict)
    typed_metadata: DocMetadata | None = None  # NEW FIELD
    # ... rest of existing fields ...
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for caching/serialization."""
        result = {
            # ... existing fields ...
            "metadata": self.metadata,
            "typed_metadata": None,  # Handled separately for complex types
            # ...
        }
        # Serialize typed_metadata if present
        if self.typed_metadata is not None:
            from dataclasses import asdict
            result["typed_metadata"] = {
                "type": type(self.typed_metadata).__name__,
                "data": asdict(self.typed_metadata),
            }
        return result
```

**Pre-drafted commit**:
```bash
git add -A && git commit -m "autodoc(base): add typed_metadata field to DocElement; preserve backward compat with metadata dict"
```

---

### Task 2.2: Add deserialization for typed_metadata

**Subsystem**: autodoc/base  
**Dependencies**: Task 2.1  
**Risk**: Medium (affects cache loading)

**Files to update**:
- `bengal/autodoc/base.py`

**Implementation**:

```python
# Add to DocElement.from_dict():
@classmethod
def from_dict(cls, data: dict[str, Any]) -> DocElement:
    """Create from dictionary (for cache loading)."""
    children = [cls.from_dict(child) for child in data.get("children", [])]
    source_file = Path(data["source_file"]) if data.get("source_file") else None
    
    # Deserialize typed_metadata
    typed_metadata = None
    if data.get("typed_metadata"):
        typed_metadata = cls._deserialize_typed_metadata(data["typed_metadata"])
    
    return cls(
        # ... existing fields ...
        typed_metadata=typed_metadata,
    )

@staticmethod
def _deserialize_typed_metadata(data: dict[str, Any]) -> DocMetadata | None:
    """Deserialize typed_metadata from dict."""
    from bengal.autodoc.models import (
        PythonModuleMetadata,
        PythonClassMetadata,
        PythonFunctionMetadata,
        # ... all types ...
    )
    
    type_map = {
        "PythonModuleMetadata": PythonModuleMetadata,
        "PythonClassMetadata": PythonClassMetadata,
        "PythonFunctionMetadata": PythonFunctionMetadata,
        # ... all types ...
    }
    
    type_name = data.get("type")
    type_data = data.get("data", {})
    
    if type_name in type_map:
        return type_map[type_name](**type_data)
    return None
```

**Pre-drafted commit**:
```bash
git add -A && git commit -m "autodoc(base): add typed_metadata serialization/deserialization in DocElement"
```

---

## Phase 3: Update Python Extractor

### Task 3.1: Update module extraction to use typed metadata

**Subsystem**: autodoc/extractors  
**Dependencies**: Phase 2 complete  
**Risk**: Medium

**Files to update**:
- `bengal/autodoc/extractors/python.py`

**Changes** (for `_extract_module_elements`):

```python
from bengal.autodoc.models import PythonModuleMetadata

# In _extract_module_elements(), update return:
return DocElement(
    name=module_name,
    qualified_name=module_qualified_name,
    description=module_doc,
    element_type="module",
    source_file=file_path,
    line_number=1,
    metadata={  # Keep for backward compat
        "file_path": str(file_path),
        "has_all": self._extract_all_exports(tree),
    },
    typed_metadata=PythonModuleMetadata(  # NEW
        file_path=str(file_path),
        has_all=self._extract_all_exports(tree),
    ),
    children=children,
)
```

**Pre-drafted commit**:
```bash
git add -A && git commit -m "autodoc(python): add typed_metadata for module extraction; dual-write to metadata dict"
```

---

### Task 3.2: Update class extraction to use typed metadata

**Subsystem**: autodoc/extractors  
**Dependencies**: Task 3.1  
**Risk**: Medium

**Files to update**:
- `bengal/autodoc/extractors/python.py`

**Changes** (for `_extract_class`):

```python
from bengal.autodoc.models import PythonClassMetadata, ParsedDocstring

# In _extract_class(), update return:
typed = PythonClassMetadata(
    bases=tuple(bases),
    decorators=tuple(decorators),
    is_exception=any(b in ("Exception", "BaseException") for b in bases),
    is_dataclass="dataclass" in decorators,
    is_abstract=any("ABC" in base for base in bases),
    parsed_doc=self._to_parsed_docstring(parsed_doc) if parsed_doc else None,
)

return DocElement(
    # ... existing fields ...
    metadata={...},  # Keep for backward compat
    typed_metadata=typed,
)
```

**Pre-drafted commit**:
```bash
git add -A && git commit -m "autodoc(python): add typed_metadata for class extraction with ParsedDocstring"
```

---

### Task 3.3: Update function extraction to use typed metadata

**Subsystem**: autodoc/extractors  
**Dependencies**: Task 3.2  
**Risk**: Medium

**Files to update**:
- `bengal/autodoc/extractors/python.py`

**Changes** (for `_extract_function`):

```python
from bengal.autodoc.models import PythonFunctionMetadata, ParameterInfo

# In _extract_function(), update return:
typed = PythonFunctionMetadata(
    signature=signature,
    parameters=tuple(self._to_parameter_info(arg) for arg in merged_args),
    return_type=returns,
    is_async=is_async,
    is_classmethod="classmethod" in decorators,
    is_staticmethod="staticmethod" in decorators,
    is_property="property" in decorators,
    is_generator=is_generator,
    decorators=tuple(decorators),
    parsed_doc=self._to_parsed_docstring(parsed_doc) if parsed_doc else None,
)

return DocElement(
    # ... existing fields ...
    metadata={...},  # Keep for backward compat
    typed_metadata=typed,
)
```

**Pre-drafted commit**:
```bash
git add -A && git commit -m "autodoc(python): add typed_metadata for function extraction with ParameterInfo"
```

---

### Task 3.4: Add helper methods for conversion

**Subsystem**: autodoc/extractors  
**Dependencies**: Task 3.1  
**Risk**: Low

**Files to update**:
- `bengal/autodoc/extractors/python.py`

**Add helper methods**:

```python
def _to_parsed_docstring(self, parsed: ParsedDoc | None) -> ParsedDocstring | None:
    """Convert ParsedDoc to frozen ParsedDocstring."""
    if not parsed:
        return None
    return ParsedDocstring(
        summary=parsed.summary or "",
        description=parsed.description or "",
        params=tuple(
            ParameterInfo(
                name=p.name,
                type_hint=p.type_hint,
                description=p.description,
            )
            for p in (parsed.params or [])
        ),
        returns=parsed.returns,
        raises=tuple(
            (r.type_name, r.description)
            for r in (parsed.raises or [])
        ),
        examples=tuple(parsed.examples or []),
    )

def _to_parameter_info(self, arg: dict[str, Any]) -> ParameterInfo:
    """Convert arg dict to ParameterInfo."""
    return ParameterInfo(
        name=arg.get("name", ""),
        type_hint=arg.get("type"),
        default=arg.get("default"),
        description=arg.get("description"),
    )
```

**Pre-drafted commit**:
```bash
git add -A && git commit -m "autodoc(python): add helper methods for ParsedDocstring and ParameterInfo conversion"
```

---

## Phase 4: Update CLI and OpenAPI Extractors

### Task 4.1: Update CLI extractor

**Subsystem**: autodoc/extractors  
**Dependencies**: Phase 3 complete  
**Risk**: Medium

**Files to update**:
- `bengal/autodoc/extractors/cli.py`

**Pre-drafted commit**:
```bash
git add -A && git commit -m "autodoc(cli): add typed_metadata for command and group extraction"
```

---

### Task 4.2: Update OpenAPI extractor

**Subsystem**: autodoc/extractors  
**Dependencies**: Phase 3 complete  
**Risk**: Medium

**Files to update**:
- `bengal/autodoc/extractors/openapi.py`

**Pre-drafted commit**:
```bash
git add -A && git commit -m "autodoc(openapi): add typed_metadata for endpoint, schema, overview extraction"
```

---

## Phase 5: Testing

### Task 5.1: Unit tests for common models

**Subsystem**: tests  
**Dependencies**: Task 1.1  
**Risk**: Low

**Files to create**:
- `tests/unit/autodoc/test_models_common.py`

**Test cases**:
- `test_qualified_name_rejects_empty_parts`
- `test_qualified_name_from_string_filters_empty`
- `test_qualified_name_parent_property`
- `test_source_location_rejects_negative_line`
- `test_source_location_from_path`

**Pre-drafted commit**:
```bash
git add -A && git commit -m "tests(autodoc): add unit tests for QualifiedName and SourceLocation"
```

---

### Task 5.2: Unit tests for Python models

**Subsystem**: tests  
**Dependencies**: Task 1.2  
**Risk**: Low

**Files to create**:
- `tests/unit/autodoc/test_models_python.py`

**Test cases**:
- `test_python_module_metadata_frozen`
- `test_python_class_metadata_default_values`
- `test_python_function_metadata_signature`
- `test_parameter_info_kinds`
- `test_parsed_docstring_immutable`

**Pre-drafted commit**:
```bash
git add -A && git commit -m "tests(autodoc): add unit tests for Python metadata dataclasses"
```

---

### Task 5.3: Integration tests for extractor output

**Subsystem**: tests  
**Dependencies**: Phase 3 complete  
**Risk**: Medium

**Files to create**:
- `tests/unit/autodoc/test_python_extractor_typed.py`

**Test cases**:
- `test_python_extractor_produces_typed_metadata`
- `test_typed_metadata_matches_untyped_dict`
- `test_class_extraction_has_correct_metadata_type`
- `test_function_extraction_has_parameters`

**Pre-drafted commit**:
```bash
git add -A && git commit -m "tests(autodoc): add integration tests verifying typed_metadata matches metadata dict"
```

---

### Task 5.4: Serialization round-trip tests

**Subsystem**: tests  
**Dependencies**: Task 2.2  
**Risk**: Medium

**Files to create**:
- `tests/unit/autodoc/test_doc_element_serialization.py`

**Test cases**:
- `test_doc_element_to_dict_includes_typed_metadata`
- `test_doc_element_from_dict_restores_typed_metadata`
- `test_serialization_round_trip_preserves_data`

**Pre-drafted commit**:
```bash
git add -A && git commit -m "tests(autodoc): add serialization round-trip tests for typed_metadata"
```

---

## Task Summary

| Phase | Task | Subsystem | Risk | Dependencies |
|-------|------|-----------|------|--------------|
| 1 | 1.1 Create models package | autodoc/models | Low | None |
| 1 | 1.2 Python metadata | autodoc/models | Low | 1.1 |
| 1 | 1.3 CLI metadata | autodoc/models | Low | 1.1 |
| 1 | 1.4 OpenAPI metadata | autodoc/models | Low | 1.1 |
| 1 | 1.5 Export and union | autodoc/models | Low | 1.2-1.4 |
| 2 | 2.1 Add typed_metadata field | autodoc/base | Low | Phase 1 |
| 2 | 2.2 Deserialization | autodoc/base | Medium | 2.1 |
| 3 | 3.1 Module extraction | autodoc/extractors | Medium | Phase 2 |
| 3 | 3.2 Class extraction | autodoc/extractors | Medium | 3.1 |
| 3 | 3.3 Function extraction | autodoc/extractors | Medium | 3.2 |
| 3 | 3.4 Helper methods | autodoc/extractors | Low | 3.1 |
| 4 | 4.1 CLI extractor | autodoc/extractors | Medium | Phase 3 |
| 4 | 4.2 OpenAPI extractor | autodoc/extractors | Medium | Phase 3 |
| 5 | 5.1 Common model tests | tests | Low | 1.1 |
| 5 | 5.2 Python model tests | tests | Low | 1.2 |
| 5 | 5.3 Extractor integration | tests | Medium | Phase 3 |
| 5 | 5.4 Serialization tests | tests | Medium | 2.2 |

---

## Implementation Order

**Recommended sequence**:

1. **Day 1**: Phase 1 (Tasks 1.1-1.5) + Task 5.1-5.2
   - Create all model files
   - Run tests to verify models work

2. **Day 2**: Phase 2 (Tasks 2.1-2.2) + Task 5.4
   - Integrate with DocElement
   - Verify serialization

3. **Day 3**: Phase 3 (Tasks 3.1-3.4) + Task 5.3
   - Update Python extractor
   - Verify dual-write works

4. **Day 4**: Phase 4 (Tasks 4.1-4.2)
   - Update CLI extractor
   - Update OpenAPI extractor

---

## Rollback Plan

If issues are discovered:

1. **Phase 1-2**: No rollback needed - additive changes only
2. **Phase 3-4**: Set `typed_metadata = None` in extractors to disable
3. **Emergency**: Revert commits using git

The `metadata` dict is preserved throughout, so existing code continues to work.

---

## Success Criteria

- [ ] All typed metadata models compile and pass type checking
- [ ] `QualifiedName` rejects malformed input (empty parts)
- [ ] `SourceLocation` rejects invalid line numbers
- [ ] `DocElement.typed_metadata` populated by all extractors
- [ ] `DocElement.to_dict()` / `from_dict()` round-trips preserve typed data
- [ ] Existing `metadata` dict still populated (backward compat)
- [ ] All tests pass (new and existing)
- [ ] No regressions in autodoc generation

---

## Future Work (Not in This Plan)

- **Phase 6**: Update templates to use `typed_metadata`
- **Phase 7**: Add deprecation warnings on `metadata` access
- **Phase 8**: Remove `metadata` dict (breaking change)
- **Phase 9**: Consider Option B (separate element classes)

---

## References

- RFC: `plan/active/rfc-typed-autodoc-models.md`
- Current base: `bengal/autodoc/base.py:15-83`
- Python extractor: `bengal/autodoc/extractors/python.py`
- CLI extractor: `bengal/autodoc/extractors/cli.py`
- OpenAPI extractor: `bengal/autodoc/extractors/openapi.py`

