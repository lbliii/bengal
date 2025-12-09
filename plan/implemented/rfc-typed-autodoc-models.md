# RFC: Typed Autodoc Models

**Status**: Draft (Audited)  
**Author**: AI Assistant  
**Created**: 2025-12-08  
**Audited**: 2025-12-08 — 88% confidence, 14/17 claims verified  
**Related**: Virtual page autodoc system, `bengal/autodoc/`

---

## Executive Summary

The current autodoc system uses a single generic `DocElement` dataclass with an untyped `metadata: dict[str, Any]` field. This causes bugs to surface at render time instead of extraction time, makes debugging difficult, and provides no IDE support when working with documentation elements.

**Recommendation**: Replace `DocElement` with typed, domain-specific dataclasses for Python, CLI, and OpenAPI documentation.

---

## Problem Statement

### Pain Points Discovered During Virtual Page Debugging

#### 1. Empty Section Names from Malformed Qualified Names

**Symptom**: Sidebar navigation showed "Section" instead of "API Reference"

**Root Cause** (Historical): The `qualified_name` field contained values like `...bengal.bengal.core` (with leading dots) because:
- Path resolution was inconsistent between `_source_root` (resolved) and file paths from `rglob` (unresolved)
- `qualified_name.split(".")` produced empty strings: `['', '', '', 'bengal', 'bengal', 'core']`
- Section creation code didn't validate parts before creating sections

**Current State**: The `_infer_module_name()` method in `PythonExtractor` (lines 598-651) now resolves paths consistently using `.resolve()`. However, no validation prevents malformed qualified names from being created.

**Type System Failure**: `qualified_name: str` accepts any string. A typed model would enforce:
```python
@dataclass
class ModulePath:
    parts: tuple[str, ...]  # Non-empty strings only

    def __post_init__(self):
        if not self.parts or any(not p for p in self.parts):
            raise ValueError(f"Invalid module path: {self.parts}")
```

#### 2. Virtual Environment Pollution

**Symptom**: 2270 pages generated instead of ~500; included PIL, site-packages, .venv

**Root Cause** (Historical): The `_should_skip()` method used naive substring matching that didn't catch hidden directories and site-packages paths.

**Current State**: This issue has been **partially addressed** in `PythonExtractor._should_skip()` (lines 160-205), which now includes:
- Hidden directory detection (`.venv`, `.env`, etc.)
- Common skip dirs (`site-packages`, `__pycache__`, `node_modules`, etc.)
- User-specified exclude patterns

**Remaining Gap**: The skip logic is still untyped and scattered. A typed model would make exclusion rules explicit and testable:
```python
@dataclass
class ExtractionConfig:
    source_roots: list[Path]  # Resolved, validated paths
    include_patterns: list[GlobPattern]
    exclude_patterns: list[GlobPattern]

    def should_extract(self, path: Path) -> bool:
        # Type-safe, testable, centralized logic
```

#### 3. Metadata Key Typos Are Silent

**Illustrative Example** (this specific typo doesn't exist in code, but the risk is real):
```python
# In extractor
element.metadata["decoraters"] = decorators  # Typo: "decoraters"

# In template  
decorators = element.metadata.get("decorators", [])  # Always empty!
```

**Evidence of Risk**: There are 18+ `.metadata.get()` patterns in `bengal/autodoc/` that could silently fail on typos. Examples from actual code:
- `element.metadata.get("method", "").lower()` — `virtual_orchestrator.py:877`
- `element.metadata.get("tags", [])` — `virtual_orchestrator.py:622`
- `method.metadata.get("decorators", [])` — `extractors/python.py:347`

**Type System Failure**: `dict[str, Any]` accepts any key. No compile-time or runtime error.

#### 4. Different Doc Types Have Incompatible Structures

**Python Elements** (from `extractors/python.py`):
- Classes: `bases`, `decorators`, `is_dataclass`, `is_abstract`, `parsed_doc`
- Functions: `signature`, `args`, `returns`, `decorators`, `is_async`, `is_property`, `is_classmethod`, `is_staticmethod`, `parsed_doc`
- Modules: `file_path`, `has_all`
- Attributes: `annotation`

**CLI Elements** (from `extractors/cli.py`):
- Commands: `callback`, `option_count`, `argument_count`
- Parameters: `param_type`, `type`, `required`, `default`, `multiple`, `is_flag`, `count`, `opts`, `envvar`

**OpenAPI Elements** (from `extractors/openapi.py`):
- Overview: `version`, `servers`, `security_schemes`, `tags`
- Endpoints: `method`, `path`, `summary`, `operation_id`, `tags`, `parameters`, `request_body`, `responses`, `security`, `deprecated`
- Schemas: `type`, `properties`, `required`, `enum`, `example`, `raw_schema`

**Current Approach**: Everything stuffed into `metadata: dict[str, Any]`

**Result**: Template code is defensive and fragile:
```python
# Have to handle missing keys everywhere (from virtual_orchestrator.py)
method = element.metadata.get("method", "").lower()  # line 877
bases = element.metadata.get("bases", [])             # python.py:697
tags = element.metadata.get("tags", []) if element.metadata else []  # line 921
```

#### 5. Section Hierarchy for Virtual Sections

**Symptom**: `page._section.root` returned wrong section or None

**Root Cause**: Virtual sections weren't being properly linked in parent-child hierarchy:
- `Section.create_virtual()` creates a section but doesn't set `parent`
- `add_subsection()` sets parent, but orchestrator code was inconsistent
- URL registry lookup succeeded but returned sections with broken hierarchy

**Type System Failure**: No type enforcement that virtual sections must have their hierarchy established before registration.

---

## Current Architecture

**Verified against codebase** — All structures below confirmed via audit.

```
DocElement (single class for everything)           # base.py:15-83
├── name: str
├── qualified_name: str  
├── description: str
├── element_type: str  # "module", "class", "function", "endpoint", "command"
├── metadata: dict[str, Any]  # 👈 TYPE SAFETY ENDS HERE (line 43)
├── children: list[DocElement]
├── source_file: Path | None
├── line_number: int | None
├── examples: list[str]
├── see_also: list[str]
└── deprecated: str | None

Extractors:
├── PythonExtractor.extract() -> list[DocElement]  # extractors/python.py:102
├── CLIExtractor.extract() -> list[DocElement]     # extractors/cli.py:106
└── OpenAPIExtractor.extract() -> list[DocElement] # extractors/openapi.py:28

VirtualAutodocOrchestrator:                        # virtual_orchestrator.py:75
├── _extract_python() -> list[DocElement]          # line 1188
├── _extract_cli() -> list[DocElement]             # line 1214
├── _extract_openapi() -> list[DocElement]         # line 1244
├── _create_python_sections(elements)              # line 436
├── _create_pages(elements, sections)              # line 665
└── generate() -> tuple[list[Page], list[Section]] # line 350
```

### What Does NOT Exist Yet

The following are **proposed** and do not currently exist in the codebase:

- ❌ `bengal/autodoc/models/` package
- ❌ `typed_metadata` field on `DocElement`
- ❌ `QualifiedName` type with validation
- ❌ `SourceLocation` dataclass
- ❌ `PythonModuleMetadata`, `PythonClassMetadata`, `PythonFunctionMetadata`
- ❌ `CLICommandMetadata`, `CLIOptionMetadata`
- ❌ `OpenAPIEndpointMetadata`

---

## Proposed Architecture

### Option A: Discriminated Union with Typed Metadata

Keep `DocElement` but add typed metadata classes:

```python
from dataclasses import dataclass
from typing import Literal

# Typed metadata for each domain
@dataclass(frozen=True)
class PythonModuleMetadata:
    """Metadata specific to Python modules."""
    is_package: bool = False
    all_exports: list[str] = field(default_factory=list)

@dataclass(frozen=True)
class PythonClassMetadata:
    """Metadata specific to Python classes."""
    bases: tuple[str, ...] = ()
    decorators: tuple[str, ...] = ()
    is_exception: bool = False
    is_dataclass: bool = False
    is_abstract: bool = False

@dataclass(frozen=True)
class PythonFunctionMetadata:
    """Metadata specific to Python functions/methods."""
    signature: str = ""
    parameters: tuple[ParameterInfo, ...] = ()
    return_type: str | None = None
    is_async: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False
    is_property: bool = False
    decorators: tuple[str, ...] = ()

@dataclass(frozen=True)
class ParameterInfo:
    """Single function parameter."""
    name: str
    type_hint: str | None = None
    default: str | None = None
    kind: Literal["positional", "keyword", "var_positional", "var_keyword"] = "positional"

# Similar for CLI and OpenAPI...
@dataclass(frozen=True)
class CLICommandMetadata:
    options: tuple[CLIOption, ...] = ()
    arguments: tuple[CLIArgument, ...] = ()
    is_hidden: bool = False

@dataclass(frozen=True)
class OpenAPIEndpointMetadata:
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    path: str
    tags: tuple[str, ...] = ()
    request_body: RequestBodyInfo | None = None
    responses: dict[str, ResponseInfo] = field(default_factory=dict)
```

Then `DocElement` becomes:

```python
type DocMetadata = (
    PythonModuleMetadata
    | PythonClassMetadata
    | PythonFunctionMetadata
    | CLICommandMetadata
    | OpenAPIEndpointMetadata
)

@dataclass
class DocElement:
    name: str
    qualified_name: QualifiedName  # Typed, validated
    description: str
    element_type: str
    typed_metadata: DocMetadata  # 👈 TYPED!
    children: list[DocElement] = field(default_factory=list)
    source_location: SourceLocation | None = None
```

**Pros**:
- Backward compatible (can keep `metadata` dict for migration)
- Gradual adoption possible
- Single element type simplifies orchestrator

**Cons**:
- Still one class doing many things
- Type narrowing required in templates

### Option B: Separate Element Classes Per Domain

```python
# Base for all doc elements
@dataclass
class BaseDocElement(ABC):
    name: str
    description: str
    source_location: SourceLocation | None = None

    @abstractmethod
    def to_page_metadata(self) -> dict[str, Any]:
        """Convert to Page metadata for virtual page creation."""

# Python-specific elements
@dataclass
class PythonModule(BaseDocElement):
    qualified_name: ModulePath
    is_package: bool = False
    classes: list[PythonClass] = field(default_factory=list)
    functions: list[PythonFunction] = field(default_factory=list)
    all_exports: list[str] = field(default_factory=list)

@dataclass
class PythonClass(BaseDocElement):
    qualified_name: ModulePath
    bases: tuple[str, ...] = ()
    decorators: tuple[str, ...] = ()
    methods: list[PythonFunction] = field(default_factory=list)
    attributes: list[PythonAttribute] = field(default_factory=list)
    is_exception: bool = False
    is_dataclass: bool = False

@dataclass  
class PythonFunction(BaseDocElement):
    qualified_name: ModulePath
    signature: Signature
    is_async: bool = False
    is_method: bool = False
    decorators: tuple[str, ...] = ()

@dataclass(frozen=True)
class Signature:
    """Typed function signature."""
    parameters: tuple[Parameter, ...] = ()
    return_type: str | None = None

    def __str__(self) -> str:
        params = ", ".join(str(p) for p in self.parameters)
        ret = f" -> {self.return_type}" if self.return_type else ""
        return f"({params}){ret}"

# CLI-specific elements
@dataclass
class CLICommand(BaseDocElement):
    name: str
    help_text: str
    options: list[CLIOption] = field(default_factory=list)
    arguments: list[CLIArgument] = field(default_factory=list)
    subcommands: list[CLICommand] = field(default_factory=list)
    is_hidden: bool = False

# OpenAPI-specific elements
@dataclass
class OpenAPIEndpoint(BaseDocElement):
    method: HTTPMethod
    path: str
    operation_id: str | None = None
    tags: tuple[str, ...] = ()
    parameters: list[OpenAPIParameter] = field(default_factory=list)
    request_body: OpenAPIRequestBody | None = None
    responses: dict[int, OpenAPIResponse] = field(default_factory=dict)
```

**Pros**:
- Full type safety throughout
- IDE autocomplete works perfectly
- Impossible to have wrong metadata keys
- Each element type is self-documenting

**Cons**:
- More classes to maintain
- Extractors return different types
- Orchestrator needs to handle multiple types

### Option C: Hybrid - Typed Extractors, Generic Orchestrator

Keep `DocElement` as the "interchange format" but have extractors produce typed intermediates:

```python
# Extractors produce typed results
class PythonExtractor:
    def extract(self, source: Path) -> PythonPackage:
        """Returns fully typed Python documentation tree."""
        ...

    def to_doc_elements(self, package: PythonPackage) -> list[DocElement]:
        """Convert to generic DocElements for orchestrator."""
        # Validation happens HERE, during conversion
        ...

# Orchestrator works with DocElement
class VirtualAutodocOrchestrator:
    def generate(self) -> tuple[list[Page], list[Section]]:
        elements: list[DocElement] = []

        if self.python_enabled:
            extractor = PythonExtractor(self.python_config)
            typed_result = extractor.extract(source)  # Typed!
            elements.extend(extractor.to_doc_elements(typed_result))

        # ... rest uses DocElement
```

**Pros**:
- Type safety where it matters most (extraction)
- Orchestrator stays simple
- Errors caught at extraction time

**Cons**:
- Two representations to maintain
- Conversion step adds complexity

---

## Recommendation

**Option A (Discriminated Union)** for Phase 1:
- Add typed metadata classes alongside existing `metadata: dict`
- Migrate extractors to populate `typed_metadata`
- Update templates to use typed access
- Deprecate untyped `metadata` access

**Option B (Separate Classes)** for Phase 2:
- Once typed metadata is working, consider full separation
- Evaluate based on template complexity

---

## Implementation Plan

### Phase 1: Add Typed Metadata (Low Risk)

1. Create `bengal/autodoc/models/` package:
   - `python.py` - PythonModuleMetadata, PythonClassMetadata, etc.
   - `cli.py` - CLICommandMetadata, CLIOptionMetadata, etc.
   - `openapi.py` - OpenAPIEndpointMetadata, etc.
   - `common.py` - SourceLocation, ModulePath, Signature

2. Add `typed_metadata` field to `DocElement`:
   ```python
   @dataclass
   class DocElement:
       # ... existing fields ...
       typed_metadata: DocMetadata | None = None  # New field
   ```

3. Update `PythonExtractor` to populate typed metadata:
   ```python
   def _extract_class(self, node: ast.ClassDef) -> DocElement:
       typed = PythonClassMetadata(
           bases=tuple(self._get_bases(node)),
           decorators=tuple(self._get_decorators(node)),
           is_exception=self._is_exception(node),
       )
       return DocElement(
           name=node.name,
           # ...
           typed_metadata=typed,
       )
   ```

4. Update templates to use typed access:
   ```python
   # Before (fragile)
   bases = element.metadata.get("bases", [])

   # After (type-safe)
   if isinstance(element.typed_metadata, PythonClassMetadata):
       bases = element.typed_metadata.bases
   ```

### Phase 2: Add Validation

1. Add `QualifiedName` type with validation:
   ```python
   @dataclass(frozen=True)
   class QualifiedName:
       parts: tuple[str, ...]

       def __post_init__(self):
           if not self.parts:
               raise ValueError("QualifiedName cannot be empty")
           for part in self.parts:
               if not part or not part.isidentifier():
                   raise ValueError(f"Invalid identifier: {part!r}")
   ```

2. Add `SourceLocation` type:
   ```python
   @dataclass(frozen=True)
   class SourceLocation:
       file: Path
       line: int
       column: int | None = None

       def __post_init__(self):
           if self.line < 1:
               raise ValueError(f"Line must be >= 1, got {self.line}")
   ```

### Phase 3: Deprecate Untyped Access

1. Add deprecation warning to `metadata` access
2. Update all templates to use `typed_metadata`
3. Remove `metadata` field in next major version

---

## Testing Strategy

1. **Unit tests for typed models**:
   ```python
   def test_qualified_name_rejects_empty_parts():
       with pytest.raises(ValueError, match="Invalid identifier"):
           QualifiedName(parts=("bengal", "", "core"))

   def test_python_class_metadata_frozen():
       meta = PythonClassMetadata(bases=("BaseClass",))
       with pytest.raises(FrozenInstanceError):
           meta.bases = ("OtherClass",)
   ```

2. **Integration tests for extractor output**:
   ```python
   def test_python_extractor_produces_typed_metadata():
       extractor = PythonExtractor()
       elements = extractor.extract(Path("bengal/core/site.py"))

       for elem in elements:
           assert elem.typed_metadata is not None
           if elem.element_type == "class":
               assert isinstance(elem.typed_metadata, PythonClassMetadata)
   ```

3. **Template tests with typed access**:
   ```python
   def test_template_uses_typed_metadata():
       # Ensure templates don't fall back to untyped metadata
       element = DocElement(
           name="Test",
           typed_metadata=PythonClassMetadata(bases=("Base",)),
           metadata={},  # Empty - should not be used
       )
       html = render_template("python/class.html", element=element)
       assert "Base" in html
   ```

---

## Migration Path

### For Existing Code

1. **No breaking changes initially** - `metadata` dict still works
2. **Gradual migration** - Update one extractor at a time
3. **Deprecation warnings** - Help find untyped access
4. **Codemods available** - Automated migration scripts

### For Template Authors

```python
# Old way (still works during migration)
{% set bases = element.metadata.get("bases", []) %}

# New way (type-safe)
{% if element.typed_metadata and element.typed_metadata.__class__.__name__ == "PythonClassMetadata" %}
  {% set bases = element.typed_metadata.bases %}
{% endif %}

# Or with a helper
{% set bases = get_typed_field(element, "bases", []) %}
```

---

## Success Metrics

1. **Zero typo-related bugs** in metadata access
2. **IDE autocomplete works** for all element fields
3. **Extraction errors caught early** (not at render time)
4. **Reduced debugging time** for virtual page issues
5. **Self-documenting code** - types explain what's expected

---

## Appendix: Current Pain Points Summary

| Issue | Current Status | Root Cause | Type System Fix |
|-------|----------------|-----------|-----------------|
| Empty section names | ⚠️ Partially fixed | Unvalidated `qualified_name` | `QualifiedName` with validation |
| Venv pollution | ✅ Mostly fixed | Naive path filtering | `ExtractionConfig` with typed patterns |
| Silent key typos | ❌ Still present | `dict[str, Any]` | Typed metadata dataclasses |
| Incompatible structures | ❌ Still present | One class for all | Domain-specific models |
| Broken section hierarchy | ⚠️ Partially fixed | No hierarchy validation | `VirtualSection` with required parent |
| Template defensiveness | ❌ Still present | Missing key handling | Type narrowing with guarantees |

**Legend**: ✅ Fixed, ⚠️ Partially fixed, ❌ Still present

---

## References

### Core Files (Verified)

| File | Key Lines | Description |
|------|-----------|-------------|
| `bengal/autodoc/base.py` | 15-83 | `DocElement` dataclass with `metadata: dict[str, Any]` (line 43) |
| `bengal/autodoc/extractors/python.py` | 22-921 | `PythonExtractor` with `extract()` method (line 102) |
| `bengal/autodoc/extractors/cli.py` | 70-633 | `CLIExtractor` with Click/Typer support |
| `bengal/autodoc/extractors/openapi.py` | 21-197 | `OpenAPIExtractor` for OpenAPI specs |
| `bengal/autodoc/virtual_orchestrator.py` | 75-1264 | Orchestrator with `_extract_python()`, `_create_pages()` |
| `bengal/core/section.py` | 51-769 | `Section` with `create_virtual()` (line 116) |

### Defensive Pattern Locations

Evidence of untyped `.metadata.get()` patterns requiring defensive coding:

```
bengal/autodoc/virtual_orchestrator.py:622  — tags = element.metadata.get("tags", [])
bengal/autodoc/virtual_orchestrator.py:877  — method = element.metadata.get("method", "").lower()
bengal/autodoc/virtual_orchestrator.py:921  — tags=element.metadata.get("tags", []) if element.metadata else []
bengal/autodoc/extractors/python.py:347    — method.metadata.get("decorators", [])
bengal/autodoc/extractors/python.py:697    — bases = class_elem.metadata.get("bases", [])
bengal/autodoc/extractors/openapi.py:84    — element.metadata.get("tags")
```
