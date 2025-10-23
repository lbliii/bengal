# Bengal Autodoc

Unified documentation generation system for Bengal static sites.

## Features

- **Python API Documentation**: AST-based extraction (no imports required)
- **Alias Detection**: Automatically detects and documents assignment aliases
- **Inherited Members**: Optionally show inherited methods from base classes
- **OpenAPI/REST Documentation**: Generate docs from OpenAPI specs
- **CLI Documentation**: Document Click/argparse/typer commands
- **Cross-References**: Automatic linking between elements
- **Incremental Builds**: Fast regeneration on changes

## Quick Start

### Configuration

Add to your `bengal.toml`:

```toml
[autodoc.python]
enabled = true
source_dirs = ["src"]
output_dir = "content/api"
docstring_style = "auto"  # auto, google, numpy, sphinx
include_private = false   # Include _private members
include_special = false   # Include __special__ methods

# New: Alias and inherited member features
include_inherited = false              # Global toggle for inherited members
alias_strategy = "canonical"           # How to render aliases: canonical, duplicate, list-only

[autodoc.python.include_inherited_by_type]
class = false      # Show inherited methods on classes
exception = false  # Show inherited methods on exceptions
```

### Generate Documentation

```bash
# Generate API docs
bengal autodoc

# Or programmatically
from bengal.autodoc import PythonExtractor, DocumentationGenerator
from bengal.autodoc.config import load_autodoc_config

config = load_autodoc_config()
extractor = PythonExtractor(config=config["python"])
elements = extractor.extract(Path("src"))

generator = DocumentationGenerator(extractor, config)
generator.generate(elements, output_dir=Path("content/api"))
```

## Alias Detection

Bengal Autodoc automatically detects simple assignment aliases and documents them with proper provenance.

### Supported Patterns

```python
# Simple name alias
def original_function():
    '''The original function.'''
    pass

public_api = original_function  # ✅ Detected as alias

# Class alias
class InternalClass:
    '''Internal implementation.'''
    pass

PublicClass = InternalClass  # ✅ Detected as alias

# Qualified attribute alias
import os
path_join = os.path.join  # ✅ Detected as alias
```

### Alias Strategies

Configure how aliases are rendered with `alias_strategy`:

#### `"canonical"` (default)

- Alias gets a short entry linking to the canonical element
- Canonical element lists all its aliases in an "Also known as" box
- Avoids duplication while preserving discoverability

```markdown
## Functions

### `original_function`
The original function.

> **Also known as**: `public_api`

### `public_api` 🔗
> **Alias**: This is an alias of [`original_function`](#original_function)
```

#### `"list-only"`

- Aliases are only listed on the canonical element
- No separate documentation entries for aliases
- Most compact option

#### `"duplicate"`

- Alias gets full documentation (duplicated)
- Useful if you want aliases to be completely standalone
- Risk of content divergence if docs are updated

### Metadata

Alias elements include metadata:

```python
{
    "alias_of": "module.name.original",
    "alias_kind": "assignment"
}
```

Canonical elements track their aliases:

```python
{
    "aliases": ["alias1", "alias2"]
}
```

## Inherited Members

Show methods inherited from base classes in generated documentation.

### Configuration

```toml
[autodoc.python]
# Global toggle - applies to all types
include_inherited = true

# Or enable per-type
[autodoc.python.include_inherited_by_type]
class = true       # Show inherited members on classes
exception = false  # Don't show for exceptions
```

### Behavior

When enabled:

```python
class Base:
    def base_method(self):
        '''A base method.'''
        pass

class Derived(Base):
    def derived_method(self):
        '''A derived method.'''
        pass
```

Generated docs for `Derived` will show:

```markdown
### Methods

#### `derived_method`
A derived method.

### Inherited Members

**From `Base`:**
- **`base_method`** - Inherited from `Base`
```

### Features

- **No Duplication**: Overridden methods only show the derived version
- **Private Filtering**: Respects `include_private` setting for inherited members
- **Collapsible UI**: Inherited members in a dropdown to avoid cluttering the page
- **Synthetic Metadata**: Inherited members marked with `synthetic: true` and `inherited_from: "Base"`

### Limitations

- Only synthesizes members from base classes present in the documented source
- Standard library/third-party bases are silently skipped (extensible in future)
- No full MRO resolution across external packages

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
- **Aliases**: Assignment aliases (new)

### Type Hints

Type hints are preserved from source:

```python
def process(items: List[str], count: Optional[int] = None) -> Dict[str, int]:
    '''Process items.'''
    ...
```

Generates:

```markdown
#### `process`

```python
process(items: List[str], count: Optional[int] = None) -> Dict[str, int]
```
```

### Docstring Formats

Auto-detected support for:

- **Google style** (recommended)
- **NumPy style**
- **Sphinx/reStructuredText**
- **Plain text**

```python
def example(x: int) -> int:
    '''
    Short description.

    Args:
        x: Parameter description

    Returns:
        Return value description

    Raises:
        ValueError: When x is negative

    Example:
        >>> example(42)
        42
    '''
    return x
```

All sections are parsed and rendered appropriately in templates.

## Templates

Templates are located in `bengal/autodoc/templates/{type}/` where `{type}` is:

- `python/` - Python API docs
- `openapi/` - REST API docs
- `cli/` - CLI command docs

### Customization

Create custom templates in your project:

```
my_site/
  templates/
    autodoc/
      python/
        module.md.jinja2  # Overrides built-in template
```

### Template Variables

Python templates receive:

```python
{
    "element": DocElement(
        name="MyClass",
        qualified_name="mymodule.MyClass",
        description="...",
        element_type="class",  # module, class, function, method, alias
        metadata={
            "bases": [...],
            "aliases": [...],          # For canonical elements
            "alias_of": "...",         # For alias elements
            "inherited_from": "...",   # For inherited members
            "synthetic": True/False    # True for inherited members
        },
        children=[...]
    )
}
```

### Alias Template Example

```jinja2
{% if element.element_type == 'alias' %}
### `{{ element.name }}` 🔗

```{info} Alias
This is an alias of [`{{ element.metadata.alias_of }}`](#{{ element.metadata.alias_of.split('.')[-1] | lower }})
```
{% endif %}
```

### Inherited Members Template Example

```jinja2
{% set inherited_methods = cls.children | selectattr('metadata.synthetic', 'equalto', true) | list %}

{% if inherited_methods %}
:::{rubric} Inherited Members
:::

::::{dropdown} {{ inherited_methods | length }} inherited members
:open: false

{% for base_class, methods in inherited_methods | groupby('metadata.inherited_from') %}
**From `{{ base_class }}`:**
{% for method in methods %}
- **`{{ method.name }}`** - {{ method.description }}
{% endfor %}
{% endfor %}

::::
{% endif %}
```

## CLI Usage

```bash
# Generate all enabled autodoc types
bengal autodoc

# Generate only Python API docs
bengal autodoc --python

# Specify custom config
bengal autodoc --config path/to/bengal.toml

# Watch mode (regenerate on changes)
bengal autodoc --watch
```

## Performance

- **AST parsing**: ~0.1-0.5s per file
- **Alias detection**: <5% overhead
- **Inherited synthesis**: <5% overhead when enabled, 0% when disabled
- **Parallel generation**: Uses all CPU cores
- **Incremental builds**: Only regenerates changed files

## Examples

### Basic Function

```python
def add(a: int, b: int) -> int:
    '''
    Add two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        The sum of a and b
    '''
    return a + b
```

### Class with Inheritance

```python
class Animal:
    '''Base animal class.'''

    def speak(self) -> str:
        '''Make a sound.'''
        return "..."

class Dog(Animal):
    '''A dog.'''

    def speak(self) -> str:
        '''Bark!'''
        return "Woof!"

    def fetch(self) -> None:
        '''Fetch a ball.'''
        pass

# With include_inherited = true, Dog docs show inherited members
```

### Aliases for Public API

```python
# Internal implementation
def _internal_calculate(x: float) -> float:
    '''Internal calculation logic.'''
    return x * 2.5

# Public API alias
calculate = _internal_calculate

# In docs:
# - _internal_calculate: documented (if include_private=true)
# - calculate: shows as alias of _internal_calculate
```

## Migration Guide

### From Sphinx

Bengal Autodoc is compatible with many Sphinx docstring conventions:

- Google-style docstrings work out of the box
- No need for `autodoc` directives - extraction is automatic
- Type hints are preserved (no need for `:type:` fields)

### Configuration Comparison

| Sphinx | Bengal Autodoc |
|--------|----------------|
| `autodoc_member_order = 'bysource'` | Default behavior |
| `autodoc_typehints = 'signature'` | Default behavior |
| `autodoc_inherit_docstrings = True` | `include_inherited = true` |
| `autoclass_content = 'both'` | Always includes both |

## Troubleshooting

### Aliases Not Detected

**Issue**: Aliases not showing up in docs

**Solutions**:
- Ensure the alias is a simple assignment: `alias = original`
- Check that the original is defined in the same documented corpus
- Verify the alias is at module level (not inside functions/classes)

### Inherited Members Not Showing

**Issue**: Inherited methods missing even with `include_inherited = true`

**Solutions**:
- Check that base class is in the same documented source tree
- If base is from stdlib/third-party, it won't be included (limitation)
- Verify the class actually inherits: `class Derived(Base):`

### Private Members Appearing

**Issue**: Don't want to see `_private` methods

**Solutions**:
```toml
[autodoc.python]
include_private = false  # This filters both own and inherited private members
```

## Architecture

### Core Components

- **Extractors** (`bengal/autodoc/extractors/`): Parse source and extract `DocElement` objects
- **Generator** (`bengal/autodoc/generator.py`): Render templates with `DocElement` data
- **Config** (`bengal/autodoc/config.py`): Load and merge configuration
- **Templates** (`bengal/autodoc/templates/`): Jinja2 templates for rendering

### DocElement Structure

```python
@dataclass
class DocElement:
    name: str                           # Simple name
    qualified_name: str                 # Fully qualified name
    description: str                    # Main docstring text
    element_type: str                   # module, class, function, method, alias
    source_file: Path                   # Source file path
    line_number: int                    # Line number in source
    metadata: dict[str, Any]            # Type-specific metadata
    children: list[DocElement]          # Nested elements (methods, etc.)
    examples: list[str]                 # Example code blocks
    see_also: list[str]                 # Cross-references
    deprecated: str | None              # Deprecation notice
```

## Contributing

### Adding a New Extractor

1. Subclass `Extractor` in `bengal/autodoc/extractors/`
2. Implement `extract()`, `get_template_dir()`, `get_output_path()`
3. Create templates in `bengal/autodoc/templates/{your_type}/`
4. Add default config in `bengal/autodoc/config.py`
5. Add tests

### Testing

```bash
# Run autodoc tests
pytest tests/unit/autodoc/ -v

# Run specific test file
pytest tests/unit/autodoc/test_python_extractor.py -v

# Run with coverage
pytest tests/unit/autodoc/ --cov=bengal.autodoc
```

## Future Enhancements

- [ ] MRO resolution for external base classes via stubs
- [ ] Redirect stubs for aliases (optional)
- [ ] Cross-module alias tracking
- [ ] Dynamic alias analysis (beyond simple assignments)
- [ ] Interactive API browser
- [ ] Diff generation for API changes

## License

Same as Bengal - see LICENSE file.
