# Bengal Autodoc

Virtual page documentation generation system for Bengal static sites.

## Features

- **Python API Documentation**: AST-based extraction (no imports required)
- **OpenAPI/REST Documentation**: Generate docs from OpenAPI specs
- **CLI Documentation**: Document Click/argparse/typer commands
- **Virtual Pages**: Documentation rendered directly via theme templates
- **Cross-References**: Automatic linking between elements
- **Incremental Builds**: Fast regeneration on changes

## Quick Start

### Configuration

Add to your site's `config/_default/autodoc.yaml`:

```yaml
python:
  enabled: true
  source_dirs:
    - bengal  # Relative to site root
  exclude:
    - "*/tests/*"
    - "*/__pycache__/*"
  docstring_style: auto  # auto, google, numpy, sphinx
  include_private: false
  include_special: false
  display_name: API Reference  # Title in nav

cli:
  enabled: true
  app_module: bengal.cli:main
  framework: click
  include_hidden: false
  display_name: CLI Reference
```

### Build with Autodoc

Autodoc runs automatically during `bengal build` when enabled:

```bash
# Build site with autodoc
bengal build

# Serve with live reload (autodoc regenerates on changes)
bengal serve
```

## Architecture

### Virtual Pages Approach

Bengal Autodoc uses **virtual pages** - documentation is rendered directly
via theme templates without intermediate markdown files. This provides:

- **Faster builds**: No markdown-to-HTML conversion step
- **Better integration**: Uses site theme directly
- **Simpler architecture**: No manifest files or intermediate state

### Core Components

- **Extractors** (`bengal/autodoc/extractors/`): Parse source and extract `DocElement` objects
- **VirtualAutodocOrchestrator** (`bengal/autodoc/virtual_orchestrator.py`): Create virtual pages/sections
- **Config** (`bengal/autodoc/config.py`): Load and merge configuration
- **Fallback Templates** (`bengal/autodoc/fallback/`): Minimal templates when theme doesn't provide them

### DocElement Structure

```python
@dataclass
class DocElement:
    name: str                           # Simple name
    qualified_name: str                 # Fully qualified name
    description: str                    # Main docstring text
    element_type: str                   # module, class, function, method
    source_file: Path                   # Source file path
    line_number: int                    # Line number in source
    metadata: dict[str, Any]            # Type-specific metadata (legacy)
    typed_metadata: DocMetadata | None  # Typed metadata (preferred)
    children: list[DocElement]          # Nested elements (methods, etc.)
    examples: list[str]                 # Example code blocks
    see_also: list[str]                 # Cross-references
    deprecated: str | None              # Deprecation notice
```

### Typed Metadata (Recommended)

Extractors populate `typed_metadata` with domain-specific dataclasses for
type-safe access with IDE autocomplete:

```python
from bengal.autodoc.utils import (
    get_python_class_bases,
    get_python_function_is_property,
    get_openapi_tags,
    get_openapi_method,
)

# Type-safe access with fallback to metadata dict
bases = get_python_class_bases(class_element)  # tuple[str, ...]
is_prop = get_python_function_is_property(method)  # bool
tags = get_openapi_tags(endpoint)  # tuple[str, ...]
method = get_openapi_method(endpoint)  # str (e.g., "GET")
```

**Available Metadata Types**:

- **Python**: `PythonModuleMetadata`, `PythonClassMetadata`, `PythonFunctionMetadata`
- **CLI**: `CLICommandMetadata`, `CLIGroupMetadata`, `CLIOptionMetadata`
- **OpenAPI**: `OpenAPIEndpointMetadata`, `OpenAPIOverviewMetadata`, `OpenAPISchemaMetadata`

See `bengal/autodoc/models/` for full type definitions.

## Python Extractor

### AST-Only Extraction

Bengal uses AST parsing instead of runtime imports for several benefits:

- **Fast**: No module loading overhead
- **Safe**: No side effects from imports
- **Reliable**: Works with any Python version syntax
- **Clean**: No pollution of Python path

### Supported Elements

- **Modules**: Top-level module docstrings
- **Classes**: Including bases, decorators, dataclasses
- **Methods**: Instance, class, static methods
- **Functions**: Regular and async functions
- **Properties**: `@property` decorated methods
- **Attributes**: Class and instance attributes with type hints

### Type Hints

Type hints are preserved from source:

```python
def process(items: List[str], count: Optional[int] = None) -> Dict[str, int]:
    '''Process items.'''
    ...
```

### Docstring Formats

Auto-detected support for:

- **Google style** (recommended)
- **NumPy style**
- **Sphinx/reStructuredText**
- **Plain text**

## Theme Integration

### Required Templates

Your theme should provide these templates in `templates/api-reference/`:

- `module.html` - Module documentation page
- `section-index.html` - Section index page

### Fallback Templates

If your theme doesn't provide API templates, Bengal uses minimal fallbacks
from `bengal/autodoc/fallback/`. These are intentionally basic - customize
for a better experience.

### Template Variables

API templates receive:

```python
{
    "element": DocElement(...),  # The documented element
    "page": Page(...),           # Virtual page object
    "site": Site(...),           # Site object
    # Plus standard template context
}
```

## Performance

- **AST parsing**: ~0.1-0.5s per file
- **Virtual page creation**: Very fast (no I/O)
- **Incremental builds**: Only regenerates on source changes

## Programmatic Usage

```python
from bengal.autodoc import VirtualAutodocOrchestrator
from bengal.core.site import Site

site = Site.from_config(Path("site"))
orchestrator = VirtualAutodocOrchestrator(site)

if orchestrator.is_enabled():
    pages, sections = orchestrator.generate()
    # pages and sections are virtual - integrate with site
```

## License

Same as Bengal - see LICENSE file.
