# Unified Autodoc Architecture: Python, OpenAPI, and CLI

**Status**: Design Exploration  
**Date**: October 4, 2025  
**Question**: Should Python autodoc, OpenAPI docs, and CLI docs share architecture?

---

## TL;DR

**Yes, they should share infrastructure.** 

The extraction layer differs, but everything downstream (templates, rendering, cross-references) is identical. Build a pluggable extractor system.

**Architecture**: `Extractor → Data Models → Templates → Markdown → Bengal Pipeline`

---

## The Insight

All three documentation types follow the same pattern:

```
Source (Code/Spec) 
    ↓
Extract Structure (different per type)
    ↓
Normalize to Data Models (same interface)
    ↓
Render with Templates (same system)
    ↓
Generate Markdown (same process)
    ↓
Bengal Pipeline (already exists)
```

**Only the first step differs. Everything else is reusable.**

---

## Comparative Analysis

### Python API Documentation

**Source**: Python source files  
**Extraction**: AST parsing  
**Structure**: Modules, classes, functions, methods  
**References**: `[[ClassName.method]]`  
**Templates**: `templates/autodoc/class.md`

**Example**:
```python
# bengal/core/site.py
class Site:
    """Represents the entire website."""
    
    def build(self) -> BuildStats:
        """Build the site."""
```

**Output**: `/api/bengal/core/site/#Site.build`

---

### OpenAPI Documentation

**Source**: OpenAPI spec (YAML/JSON) OR FastAPI/Flask decorators  
**Extraction**: Spec parsing OR decorator inspection  
**Structure**: Endpoints, schemas, parameters, responses  
**References**: `[[GET /api/users]]` or `[[UserSchema]]`  
**Templates**: `templates/autodoc/endpoint.md`

**Example**:
```python
# Using FastAPI
@app.get("/users/{user_id}")
async def get_user(user_id: int) -> User:
    """Get user by ID."""
    return db.get_user(user_id)
```

**Output**: `/api-docs/endpoints/users/#get-users-user_id`

---

### CLI Documentation

**Source**: Click/argparse/typer definitions  
**Extraction**: Introspect CLI framework  
**Structure**: Commands, options, arguments, subcommands  
**References**: `[[bengal build]]` or `[[--incremental]]`  
**Templates**: `templates/autodoc/command.md`

**Example**:
```python
# bengal/cli.py
@click.command()
@click.option('--incremental', help='Incremental build')
def build(incremental: bool):
    """Build the site."""
```

**Output**: `/cli/build/`

---

## Unified Architecture

### Core Abstraction

```python
# bengal/autodoc/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path

@dataclass
class DocElement:
    """
    Base class for all documented elements.
    Common interface for Python APIs, OpenAPI endpoints, CLI commands.
    """
    name: str                    # Element name
    qualified_name: str          # Full path (module.Class.method, GET /users, bengal build)
    description: str             # Main description
    element_type: str            # 'class', 'function', 'endpoint', 'command'
    source_file: Optional[Path]  # Source location
    line_number: Optional[int]   # Line number
    metadata: Dict[str, Any]     # Type-specific data
    children: List['DocElement'] # Nested elements (methods, subcommands, etc.)
    examples: List[str]          # Usage examples
    see_also: List[str]          # Cross-references
    deprecated: Optional[str]    # Deprecation notice


class Extractor(ABC):
    """
    Base extractor interface.
    Each documentation type implements this.
    """
    
    @abstractmethod
    def extract(self, source: Any) -> List[DocElement]:
        """
        Extract documentation elements from source.
        
        Args:
            source: Source to extract from (Path, dict, object, etc.)
            
        Returns:
            List of DocElement objects
        """
        pass
    
    @abstractmethod
    def get_template_dir(self) -> str:
        """Get template directory name (e.g., 'python', 'openapi', 'cli')."""
        pass
    
    @abstractmethod
    def get_output_path(self, element: DocElement) -> Path:
        """Determine output path for element."""
        pass


class DocumentationGenerator:
    """
    Unified documentation generator.
    Works with any Extractor implementation.
    """
    
    def __init__(self, extractor: Extractor, config: Dict[str, Any]):
        self.extractor = extractor
        self.config = config
        self.template_loader = TemplateLoader(extractor.get_template_dir())
    
    def generate(self, source: Any, output_dir: Path) -> List[Path]:
        """
        Generate documentation from source.
        
        Args:
            source: Source to document
            output_dir: Where to write markdown files
            
        Returns:
            List of generated file paths
        """
        # Extract elements
        elements = self.extractor.extract(source)
        
        # Build cross-reference index
        self.xref_index = self._build_xref_index(elements)
        
        # Generate markdown for each element
        generated = []
        for element in elements:
            # Get template
            template = self.template_loader.get_template(element.element_type)
            
            # Render
            content = template.render(
                element=element,
                config=self.config,
                xref=self.xref_index
            )
            
            # Write
            output_path = output_dir / self.extractor.get_output_path(element)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content)
            generated.append(output_path)
        
        return generated
```

---

## Implementation: Python API Extractor

```python
# bengal/autodoc/extractors/python.py

class PythonExtractor(Extractor):
    """Extract Python API documentation via AST."""
    
    def extract(self, source: Path) -> List[DocElement]:
        """Extract from Python source files."""
        elements = []
        
        for py_file in source.rglob("*.py"):
            tree = ast.parse(py_file.read_text())
            module_elements = self._extract_module(tree, py_file)
            elements.extend(module_elements)
        
        return elements
    
    def _extract_module(self, tree: ast.Module, file: Path) -> List[DocElement]:
        """Extract module and its contents."""
        elements = []
        
        # Module itself
        module_doc = DocElement(
            name=self._infer_module_name(file),
            qualified_name=self._infer_module_name(file),
            description=ast.get_docstring(tree) or "",
            element_type='module',
            source_file=file,
            line_number=1,
            metadata={'exports': self._get_all_exports(tree)},
            children=[],
            examples=[],
            see_also=[]
        )
        
        # Extract classes and functions
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_doc = self._extract_class(node, file)
                module_doc.children.append(class_doc)
            
            elif isinstance(node, ast.FunctionDef):
                if self._is_top_level(node, tree):
                    func_doc = self._extract_function(node, file)
                    module_doc.children.append(func_doc)
        
        elements.append(module_doc)
        return elements
    
    def _extract_class(self, node: ast.ClassDef, file: Path) -> DocElement:
        """Extract class documentation."""
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_doc = self._extract_function(item, file)
                methods.append(method_doc)
        
        return DocElement(
            name=node.name,
            qualified_name=f"{self._infer_module_name(file)}.{node.name}",
            description=ast.get_docstring(node) or "",
            element_type='class',
            source_file=file,
            line_number=node.lineno,
            metadata={
                'bases': [self._expr_to_string(b) for b in node.bases],
                'decorators': [self._decorator_to_string(d) for d in node.decorator_list]
            },
            children=methods,
            examples=[],
            see_also=[]
        )
    
    def _extract_function(self, node: ast.FunctionDef, file: Path) -> DocElement:
        """Extract function/method documentation."""
        signature = self._build_signature(node)
        
        # Parse docstring
        parsed = self._parse_docstring(ast.get_docstring(node) or "")
        
        return DocElement(
            name=node.name,
            qualified_name=node.name,  # Updated later with class context
            description=parsed.get('summary', ''),
            element_type='function',
            source_file=file,
            line_number=node.lineno,
            metadata={
                'signature': signature,
                'args': parsed.get('args', {}),
                'returns': parsed.get('returns'),
                'raises': parsed.get('raises', [])
            },
            children=[],
            examples=parsed.get('examples', []),
            see_also=parsed.get('see_also', [])
        )
    
    def get_template_dir(self) -> str:
        return "python"
    
    def get_output_path(self, element: DocElement) -> Path:
        """Generate output path for Python element."""
        if element.element_type == 'module':
            # bengal.core.site -> bengal/core/site.md
            return Path(element.qualified_name.replace('.', '/') + '.md')
        else:
            # Part of module page
            return Path(element.qualified_name.rsplit('.', 1)[0].replace('.', '/') + '.md')
```

---

## Implementation: OpenAPI Extractor

```python
# bengal/autodoc/extractors/openapi.py

import yaml
from typing import Union

class OpenAPIExtractor(Extractor):
    """Extract API documentation from OpenAPI spec or FastAPI/Flask."""
    
    def __init__(self, source_type: str = 'spec'):
        """
        Initialize extractor.
        
        Args:
            source_type: 'spec' (OpenAPI YAML/JSON) or 'fastapi' (live app)
        """
        self.source_type = source_type
    
    def extract(self, source: Union[Path, Any]) -> List[DocElement]:
        """Extract from OpenAPI spec or framework."""
        if self.source_type == 'spec':
            return self._extract_from_spec(source)
        elif self.source_type == 'fastapi':
            return self._extract_from_fastapi(source)
        else:
            raise ValueError(f"Unknown source type: {self.source_type}")
    
    def _extract_from_spec(self, spec_path: Path) -> List[DocElement]:
        """Extract from OpenAPI YAML/JSON file."""
        # Load spec
        spec = yaml.safe_load(spec_path.read_text())
        
        elements = []
        
        # Extract endpoints
        for path, path_item in spec.get('paths', {}).items():
            for method, operation in path_item.items():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    endpoint_doc = self._extract_endpoint(method, path, operation)
                    elements.append(endpoint_doc)
        
        # Extract schemas
        for schema_name, schema_def in spec.get('components', {}).get('schemas', {}).items():
            schema_doc = self._extract_schema(schema_name, schema_def)
            elements.append(schema_doc)
        
        return elements
    
    def _extract_endpoint(self, method: str, path: str, operation: dict) -> DocElement:
        """Extract API endpoint documentation."""
        return DocElement(
            name=f"{method.upper()} {path}",
            qualified_name=f"{method}:{path}",
            description=operation.get('description', operation.get('summary', '')),
            element_type='endpoint',
            source_file=None,
            line_number=None,
            metadata={
                'method': method.upper(),
                'path': path,
                'parameters': operation.get('parameters', []),
                'request_body': operation.get('requestBody'),
                'responses': operation.get('responses', {}),
                'tags': operation.get('tags', []),
                'security': operation.get('security', [])
            },
            children=[],
            examples=self._extract_examples(operation),
            see_also=[]
        )
    
    def _extract_schema(self, name: str, schema: dict) -> DocElement:
        """Extract schema/model documentation."""
        properties = []
        for prop_name, prop_def in schema.get('properties', {}).items():
            prop_doc = DocElement(
                name=prop_name,
                qualified_name=f"{name}.{prop_name}",
                description=prop_def.get('description', ''),
                element_type='property',
                source_file=None,
                line_number=None,
                metadata={
                    'type': prop_def.get('type'),
                    'format': prop_def.get('format'),
                    'required': prop_name in schema.get('required', [])
                },
                children=[],
                examples=[],
                see_also=[]
            )
            properties.append(prop_doc)
        
        return DocElement(
            name=name,
            qualified_name=name,
            description=schema.get('description', ''),
            element_type='schema',
            source_file=None,
            line_number=None,
            metadata={
                'type': schema.get('type'),
                'required': schema.get('required', [])
            },
            children=properties,
            examples=[],
            see_also=[]
        )
    
    def _extract_from_fastapi(self, app: Any) -> List[DocElement]:
        """Extract from live FastAPI app."""
        # FastAPI provides OpenAPI spec via app.openapi()
        spec = app.openapi()
        
        # Convert to our format
        return self._extract_from_spec_dict(spec)
    
    def get_template_dir(self) -> str:
        return "openapi"
    
    def get_output_path(self, element: DocElement) -> Path:
        """Generate output path for API element."""
        if element.element_type == 'endpoint':
            # GET /users/{id} -> endpoints/users/get-users-id.md
            method, path = element.name.split(' ', 1)
            safe_path = path.strip('/').replace('/', '-').replace('{', '').replace('}', '')
            return Path(f"endpoints/{method.lower()}-{safe_path}.md")
        
        elif element.element_type == 'schema':
            # UserSchema -> schemas/user-schema.md
            return Path(f"schemas/{element.name.lower()}.md")
        
        return Path(f"{element.name}.md")
```

---

## Implementation: CLI Extractor

```python
# bengal/autodoc/extractors/cli.py

import click
import inspect

class CLIExtractor(Extractor):
    """Extract CLI documentation from Click/argparse/typer."""
    
    def __init__(self, framework: str = 'click'):
        """
        Initialize extractor.
        
        Args:
            framework: 'click', 'argparse', or 'typer'
        """
        self.framework = framework
    
    def extract(self, source: Any) -> List[DocElement]:
        """
        Extract from CLI application.
        
        Args:
            source: Click command group, argparse parser, or typer app
        """
        if self.framework == 'click':
            return self._extract_from_click(source)
        elif self.framework == 'argparse':
            return self._extract_from_argparse(source)
        elif self.framework == 'typer':
            return self._extract_from_typer(source)
        else:
            raise ValueError(f"Unknown framework: {self.framework}")
    
    def _extract_from_click(self, cli: click.Group) -> List[DocElement]:
        """Extract from Click command group."""
        elements = []
        
        # Main command group
        main_doc = DocElement(
            name=cli.name or 'cli',
            qualified_name=cli.name or 'cli',
            description=cli.help or '',
            element_type='command-group',
            source_file=None,
            line_number=None,
            metadata={
                'callback': cli.callback.__name__ if cli.callback else None
            },
            children=[],
            examples=[],
            see_also=[]
        )
        
        # Extract commands
        for cmd_name, cmd in cli.commands.items():
            cmd_doc = self._extract_click_command(cmd, parent=cli.name)
            main_doc.children.append(cmd_doc)
        
        elements.append(main_doc)
        return elements
    
    def _extract_click_command(self, cmd: click.Command, parent: str = None) -> DocElement:
        """Extract Click command documentation."""
        options = []
        
        # Extract options/arguments
        for param in cmd.params:
            option_doc = DocElement(
                name=param.name,
                qualified_name=f"{parent}.{cmd.name}.{param.name}" if parent else f"{cmd.name}.{param.name}",
                description=param.help or '',
                element_type='option',
                source_file=None,
                line_number=None,
                metadata={
                    'param_type': param.__class__.__name__,
                    'required': param.required,
                    'default': param.default,
                    'type': param.type.name if hasattr(param.type, 'name') else str(param.type),
                    'opts': getattr(param, 'opts', []),
                    'multiple': getattr(param, 'multiple', False)
                },
                children=[],
                examples=[],
                see_also=[]
            )
            options.append(option_doc)
        
        # Get callback source for examples
        examples = []
        if cmd.callback:
            docstring = inspect.getdoc(cmd.callback)
            if docstring and 'Example:' in docstring:
                # Extract examples from docstring
                examples = self._extract_examples_from_docstring(docstring)
        
        return DocElement(
            name=cmd.name,
            qualified_name=f"{parent}.{cmd.name}" if parent else cmd.name,
            description=cmd.help or '',
            element_type='command',
            source_file=None,
            line_number=None,
            metadata={
                'callback': cmd.callback.__name__ if cmd.callback else None
            },
            children=options,
            examples=examples,
            see_also=[]
        )
    
    def get_template_dir(self) -> str:
        return "cli"
    
    def get_output_path(self, element: DocElement) -> Path:
        """Generate output path for CLI element."""
        if element.element_type == 'command-group':
            return Path("index.md")
        elif element.element_type == 'command':
            # bengal build -> commands/build.md
            return Path(f"commands/{element.name}.md")
        return Path(f"{element.name}.md")
```

---

## Unified Configuration

```toml
# bengal.toml

[autodoc.python]
enabled = true
source_dirs = ["src/bengal"]
output_dir = "api"
exclude = ["*/tests/*"]
docstring_style = "google"

[autodoc.openapi]
enabled = true
source_type = "spec"  # or "fastapi"
spec_file = "openapi.yaml"  # or app module
output_dir = "api-docs"

[autodoc.cli]
enabled = true
framework = "click"
module = "bengal.cli"  # Import this module to get CLI
command = "main"       # Click group/command name
output_dir = "cli-reference"

# Shared settings
[autodoc.templates]
# Custom templates apply to all types
custom_dir = "templates/autodoc"

[autodoc.cross_refs]
# Cross-references work across all doc types
enabled = true
link_style = "bengal"  # [[ref]] syntax

[autodoc.output]
one_file_per = "module"  # or "class", "function", "endpoint", "command"
include_source_links = true
```

---

## Unified CLI

```bash
# Generate all documentation types
$ bengal autodoc

📚 Generating Documentation...
   🐍 Python API:    127 elements extracted
   🌐 OpenAPI:       45 endpoints, 23 schemas
   ⌨️  CLI:          12 commands, 47 options

✅ Generated 207 documentation pages in 2.3s


# Generate specific type
$ bengal autodoc --type python
$ bengal autodoc --type openapi
$ bengal autodoc --type cli

# Watch mode (all types)
$ bengal autodoc --watch

👀 Watching for changes...
   - src/ (Python)
   - openapi.yaml (OpenAPI)
   - bengal/cli.py (CLI)
```

---

## Unified Templates

```markdown
<!-- templates/autodoc/python/class.md -->
---
title: "{{ element.name }}"
type: python-class
---

# {{ element.name }}

{{ element.description }}

{% for method in element.children %}
## {{ method.name }}
...
{% endfor %}
```

```markdown
<!-- templates/autodoc/openapi/endpoint.md -->
---
title: "{{ element.metadata.method }} {{ element.metadata.path }}"
type: api-endpoint
---

# {{ element.name }}

{{ element.description }}

**Method:** `{{ element.metadata.method }}`  
**Path:** `{{ element.metadata.path }}`

## Parameters

{% for param in element.metadata.parameters %}
...
{% endfor %}

## Request Body

{{ element.metadata.request_body }}

## Responses

{% for status, response in element.metadata.responses.items() %}
...
{% endfor %}

## Examples

{% for example in element.examples %}
{{ example }}
{% endfor %}
```

```markdown
<!-- templates/autodoc/cli/command.md -->
---
title: "{{ element.qualified_name }}"
type: cli-command
---

# {{ element.name }}

{{ element.description }}

## Usage

```bash
{{ element.qualified_name }} [OPTIONS]
```

## Options

{% for option in element.children %}
### {{ option.name }}

{{ option.description }}

**Type:** `{{ option.metadata.type }}`  
**Required:** {{ 'Yes' if option.metadata.required else 'No' }}  
{% if option.metadata.default %}**Default:** `{{ option.metadata.default }}`{% endif %}

{% endfor %}

## Examples

{% for example in element.examples %}
{{ example }}
{% endfor %}
```

---

## Cross-Type References

The unified system allows cross-references across documentation types:

```markdown
<!-- In Python API docs -->
See also the CLI command [[bengal build]] and the API endpoint [[POST /sites/build]].

<!-- In CLI docs -->
This command uses [[Site.build()]] internally and triggers [[POST /build/status]].

<!-- In OpenAPI docs -->
This endpoint is exposed by [[FastAPIBuilder]] and can be triggered via [[bengal serve --api]].
```

The cross-reference resolver knows about all three types:

```python
# bengal/autodoc/cross_refs.py

class UnifiedCrossReferenceResolver:
    """Resolve references across all documentation types."""
    
    def __init__(self, python_index, openapi_index, cli_index):
        self.indices = {
            'python': python_index,
            'openapi': openapi_index,
            'cli': cli_index
        }
    
    def resolve(self, ref: str) -> Optional[str]:
        """
        Resolve reference to any documentation type.
        
        Examples:
            'Site.build' -> Python API
            'GET /users' -> OpenAPI endpoint
            'bengal build' -> CLI command
        """
        # Try Python first
        if '.' in ref or ref[0].isupper():
            if url := self._resolve_python(ref):
                return url
        
        # Try OpenAPI
        if any(method in ref.upper() for method in ['GET', 'POST', 'PUT', 'DELETE']):
            if url := self._resolve_openapi(ref):
                return url
        
        # Try CLI
        if ' ' in ref or '--' in ref:
            if url := self._resolve_cli(ref):
                return url
        
        # Try all indices
        for doc_type, index in self.indices.items():
            if url := index.resolve(ref):
                return url
        
        return None
```

---

## Benefits of Unified Architecture

### 1. **Consistency**
- Same template system across all doc types
- Same cross-reference syntax
- Same configuration style
- Same CLI interface

### 2. **Reusability**
- Write template functions once, use everywhere
- Share cross-reference resolver
- Share markdown generator
- Share validation logic

### 3. **Extensibility**
- Easy to add new extractors (GraphQL, gRPC, etc.)
- Each extractor is ~200 lines
- Pluggable architecture

### 4. **Integration**
- Cross-type references work seamlessly
- Single build command for all docs
- Unified search index

### 5. **Maintenance**
- One codebase to maintain
- Shared tests and infrastructure
- Improvements benefit all types

---

## Use Cases

### Use Case 1: Python Library (bengal-ssg)

```toml
[autodoc.python]
enabled = true
source_dirs = ["bengal"]
output_dir = "api"

[autodoc.cli]
enabled = true
module = "bengal.cli"
output_dir = "cli"
```

**Result**: Python API docs + CLI reference

---

### Use Case 2: FastAPI Application

```toml
[autodoc.openapi]
enabled = true
source_type = "fastapi"
app_module = "myapp.main:app"
output_dir = "api"

[autodoc.python]
enabled = true
source_dirs = ["myapp/models", "myapp/services"]
output_dir = "sdk"
```

**Result**: REST API docs + Python SDK docs

---

### Use Case 3: CLI Tool with SDK

```toml
[autodoc.cli]
enabled = true
module = "mytool.cli"
output_dir = "commands"

[autodoc.python]
enabled = true
source_dirs = ["mytool/sdk"]
output_dir = "sdk"
```

**Result**: CLI reference + Python SDK docs

---

### Use Case 4: Full Stack (Like Bengal)

```toml
[autodoc.python]
enabled = true
source_dirs = ["bengal"]
output_dir = "api"

[autodoc.cli]
enabled = true
module = "bengal.cli"
output_dir = "cli"

[autodoc.openapi]
enabled = true
source_type = "spec"
spec_file = "api/openapi.yaml"
output_dir = "rest-api"
```

**Result**: Complete documentation suite

---

## Implementation Strategy

### Phase 1: Core Infrastructure (Week 1)
- ✅ Base `Extractor` interface
- ✅ Unified `DocElement` model
- ✅ `DocumentationGenerator`
- ✅ Template system
- ✅ Cross-reference resolver

### Phase 2: Python Extractor (Week 2)
- ✅ Implement `PythonExtractor`
- ✅ Python-specific templates
- ✅ Tests

### Phase 3: CLI Extractor (Week 3)
- ✅ Implement `CLIExtractor` (Click support)
- ✅ CLI-specific templates
- ✅ Self-document Bengal's CLI
- ✅ Tests

### Phase 4: OpenAPI Extractor (Week 4)
- ✅ Implement `OpenAPIExtractor`
- ✅ OpenAPI-specific templates
- ✅ FastAPI integration
- ✅ Tests

---

## File Structure

```
bengal/autodoc/
├── __init__.py
├── base.py                    # Base classes (Extractor, DocElement)
├── generator.py               # DocumentationGenerator
├── cross_refs.py              # UnifiedCrossReferenceResolver
├── templates.py               # Template loading/rendering
│
├── extractors/
│   ├── __init__.py
│   ├── python.py              # PythonExtractor
│   ├── openapi.py             # OpenAPIExtractor
│   └── cli.py                 # CLIExtractor
│
├── docstring_parsers/
│   ├── __init__.py
│   ├── google.py
│   ├── numpy.py
│   └── sphinx.py
│
└── templates/
    ├── python/
    │   ├── module.md
    │   ├── class.md
    │   └── function.md
    ├── openapi/
    │   ├── endpoint.md
    │   └── schema.md
    └── cli/
        ├── command-group.md
        ├── command.md
        └── option.md
```

---

## Answer to Your Question

### Should they share architecture?

**Yes.** The unified architecture is:
1. **More maintainable**: One codebase, shared infrastructure
2. **More powerful**: Cross-type references, unified search
3. **More extensible**: Easy to add new extractors
4. **More consistent**: Same UX across all doc types

### Do we need separate projects?

**No.** They should all be part of `bengal.autodoc` with different extractors.

### Benefits of designing together?

**Massive benefits:**
- Shared template system saves weeks of work
- Cross-references work across all types (huge UX win)
- Single `bengal autodoc` command (simple UX)
- Each extractor leverages the others (Python SDK → OpenAPI → CLI)

---

## Competitive Advantage

**No other tool does this.**

- Sphinx: Only Python
- MkDocs: Plugins for each, no integration
- Docusaurus: Separate systems for each
- ReadTheDocs: No autodoc at all

**Bengal would be the first unified documentation system.**

Generate Python API docs, REST API docs, and CLI docs from a single command, with cross-references that work across all three.

That's a **killer feature**.

---

## Recommendation

**Ship Python autodoc first (v0.3.0), but architect for extensibility.**

1. **v0.3.0**: Python autodoc with pluggable architecture
2. **v0.4.0**: Add CLI extractor (self-document Bengal)
3. **v0.5.0**: Add OpenAPI extractor (for FastAPI users)

Each release adds value without breaking prior functionality.

---

## Next Steps

1. Implement base classes (`Extractor`, `DocElement`, `DocumentationGenerator`)
2. Implement `PythonExtractor` using the base
3. Ship v0.3.0 with Python support
4. Add CLI extractor in v0.4.0
5. Add OpenAPI extractor in v0.5.0

**Timeline**: Same 4 weeks for Python, +1 week each for CLI and OpenAPI.

---

*This unified architecture positions Bengal as the first truly comprehensive documentation system for modern Python projects.*

