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

# Optional: Enable strict mode for CI/CD
strict: false  # Set to true to fail builds on autodoc errors
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

### Build Lifecycle (Deferred Rendering)

Autodoc follows the same pattern as regular pages - data during discovery, HTML during rendering:

```
1. Discovery Phase (Phase 5)
   ├─ Extract DocElements from source (Python, CLI, OpenAPI)
   ├─ Create virtual Page objects with element metadata
   └─ Store DocElement on page (NO HTML rendering yet)

2. Menu Building Phase (Phase 9)
   └─ site.menu populated with navigation

3. Rendering Phase (Phase 14)
   ├─ RenderingPipeline detects autodoc pages (is_autodoc=True)
   ├─ Calls _render_autodoc_page() with FULL template context
   ├─ Templates now have access to menus, active states, etc.
   └─ HTML written to output
```

This architecture ensures autodoc pages have the same navigation (header, sidebar) as regular pages.

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

### Incremental Build Support

Autodoc integrates with Bengal's incremental build system for fast dev server rebuilds:

**File Watching**: The dev server automatically watches autodoc source directories:
- Python `source_dirs` configured in `autodoc.python.source_dirs`
- OpenAPI spec files configured in `autodoc.openapi.spec_file`

**Selective Rebuilds**: When a Python/OpenAPI source file changes:
- Only the autodoc pages generated from that file are rebuilt
- Unaffected autodoc pages are skipped (not all 200+ autodoc pages)
- Content changes to `.md` files don't trigger unnecessary autodoc rebuilds

**Performance Impact**:
| Scenario | Before | After |
|----------|--------|-------|
| Edit content, 200 autodoc pages | Rebuild 200 | Rebuild 0 |
| Edit 1 Python file, 200 autodoc pages | Rebuild 0* | Rebuild 1 |

*Previously Python changes weren't detected at all

**Source File Deletion**: When source files are deleted, their corresponding autodoc output pages are automatically cleaned up.

## Resilience and Error Handling

### Best-Effort Mode (Default)

By default, autodoc operates in **best-effort mode**: extraction or rendering failures are logged as warnings but don't block the build. Partial successes are preserved.

```yaml
autodoc:
  strict: false  # Default: failures logged but don't block build
```

**Behavior**:
- Extraction failures: Logged with warning, empty result returned
- Template failures: Fallback template used, page tagged with `_autodoc_fallback_template: true`
- Summary logged: Counts of successes, failures, and warnings

### Strict Mode

Enable strict mode for CI/CD to fail builds when autodoc content is expected:

```yaml
autodoc:
  strict: true  # Fail build on any extraction or rendering failure
```

**Behavior**:
- Extraction failures: `RuntimeError` raised immediately
- Template failures: `RuntimeError` raised when fallback is used
- Partial results: Failures recorded before raising (for context)

### Run Summary

Autodoc generation returns a summary with counts and failure details:

```python
from bengal.autodoc import VirtualAutodocOrchestrator, AutodocRunResult

orchestrator = VirtualAutodocOrchestrator(site)
pages, sections, result = orchestrator.generate()

# Check summary
assert isinstance(result, AutodocRunResult)
print(f"Extracted: {result.extracted}, Rendered: {result.rendered}")
print(f"Failures: {result.failed_extract} extraction, {result.failed_render} rendering")

if result.has_failures():
    print(f"Failed extractions: {result.failed_extract_identifiers}")
    print(f"Failed renders: {result.failed_render_identifiers}")
    print(f"Fallback pages: {result.fallback_pages}")
```

### Fallback Template Tagging

Pages rendered via fallback template are tagged in metadata:

```python
if page.metadata.get("_autodoc_fallback_template"):
    # This page used fallback template
    reason = page.metadata.get("_autodoc_fallback_reason", "Unknown")
    print(f"Fallback used: {reason}")
```

Use this to detect pages that need custom templates or to assert zero fallbacks in CI.

## Programmatic Usage

```python
from bengal.autodoc import VirtualAutodocOrchestrator, AutodocRunResult
from bengal.core.site import Site

site = Site.from_config(Path("site"))
orchestrator = VirtualAutodocOrchestrator(site)

if orchestrator.is_enabled():
    pages, sections, result = orchestrator.generate()
    # pages and sections are virtual - integrate with site
    # result contains summary of extraction/rendering
```

## License

Same as Bengal - see LICENSE file.
