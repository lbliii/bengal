# Bengal Autodoc: Technical Implementation Plan

**Status**: Design Specification  
**Target**: v0.3.0  
**Effort**: 3-4 weeks  
**Priority**: P0 - CRITICAL

---

## Executive Summary

Build AST-based Python API documentation system that's faster, more reliable, and more flexible than Sphinx autodoc. No imports, no mock gymnastics, beautiful templates, full customization.

**Key Innovation**: Parse Python source via AST instead of importing. Eliminates 90% of Sphinx's pain points.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [AST Extraction Engine](#ast-extraction-engine)
3. [Template System & Customization](#template-system--customization)
4. [Cross-Reference System](#cross-reference-system)
5. [Configuration & CLI](#configuration--cli)
6. [Migration from Sphinx](#migration-from-sphinx)
7. [Implementation Roadmap](#implementation-roadmap)

---

## Architecture Overview

### High-Level Flow

```
Python Source Files
    ↓
AST Parser (bengal/autodoc/parser.py)
    ↓
Data Models (Module, Class, Function, etc.)
    ↓
Markdown Generator (bengal/autodoc/generator.py)
    ↓
Markdown Files in content/api/
    ↓
Standard Bengal Pipeline (rendering, templates)
    ↓
Beautiful API Documentation
```

### Key Design Principles

1. **AST-First**: Never import user code during extraction
2. **Markdown Output**: Generate .md files, let Bengal's pipeline handle rendering
3. **Template-Driven**: Full Jinja2 customization for all output
4. **Progressive Enhancement**: Start simple, add features incrementally
5. **Sphinx-Compatible**: Understand Sphinx docstring formats

---

## AST Extraction Engine

### Core Architecture

```python
# bengal/autodoc/parser.py

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any
import ast
import inspect

@dataclass
class FunctionDoc:
    """Represents a documented function."""
    name: str
    qualname: str  # Fully qualified name (module.Class.method)
    signature: str  # def foo(arg: int) -> str
    docstring: Optional[str]
    args: List['ArgumentDoc']
    returns: Optional['TypeAnnotation']
    raises: List[str]  # Exception types
    decorators: List[str]
    is_async: bool
    is_classmethod: bool
    is_staticmethod: bool
    is_property: bool
    source_file: Path
    line_number: int
    examples: List[str]  # Extracted from docstring
    see_also: List[str]  # Cross-references
    deprecated: Optional[str]
    added_version: Optional[str]

@dataclass
class ClassDoc:
    """Represents a documented class."""
    name: str
    qualname: str
    docstring: Optional[str]
    bases: List[str]  # Parent classes
    methods: List[FunctionDoc]
    attributes: List['AttributeDoc']
    properties: List[FunctionDoc]
    class_variables: List['AttributeDoc']
    decorators: List[str]
    source_file: Path
    line_number: int
    is_abstract: bool
    is_dataclass: bool

@dataclass
class ModuleDoc:
    """Represents a documented module."""
    name: str
    docstring: Optional[str]
    functions: List[FunctionDoc]
    classes: List[ClassDoc]
    attributes: List['AttributeDoc']
    imports: List[str]
    source_file: Path
    submodules: List['ModuleDoc']
    all_exports: Optional[List[str]]  # From __all__

@dataclass
class ArgumentDoc:
    """Represents a function argument."""
    name: str
    annotation: Optional[str]
    default: Optional[str]
    kind: str  # 'positional', 'keyword', 'var_positional', 'var_keyword'
    docstring: Optional[str]  # From parsed docstring

@dataclass
class AttributeDoc:
    """Represents a class/module attribute."""
    name: str
    annotation: Optional[str]
    default: Optional[str]
    docstring: Optional[str]
    line_number: int


class PythonAPIExtractor:
    """
    Extract API documentation from Python source via AST parsing.
    No imports, no execution, pure static analysis.
    """
    
    def __init__(self, source_dirs: List[Path], exclude_patterns: List[str] = None):
        """
        Initialize extractor.
        
        Args:
            source_dirs: Directories containing Python source
            exclude_patterns: Glob patterns to exclude (e.g., "*/tests/*")
        """
        self.source_dirs = source_dirs
        self.exclude_patterns = exclude_patterns or []
        self.modules: Dict[str, ModuleDoc] = {}
    
    def extract_all(self) -> Dict[str, ModuleDoc]:
        """
        Extract documentation from all Python files.
        
        Returns:
            Dict mapping module names to ModuleDoc objects
        """
        for source_dir in self.source_dirs:
            for py_file in source_dir.rglob("*.py"):
                if self._should_exclude(py_file):
                    continue
                module_name = self._get_module_name(py_file, source_dir)
                self.modules[module_name] = self.extract_module(py_file)
        
        return self.modules
    
    def extract_module(self, path: Path) -> ModuleDoc:
        """
        Extract documentation from a single Python file.
        
        Args:
            path: Path to Python source file
            
        Returns:
            ModuleDoc with all extracted information
        """
        source = path.read_text(encoding='utf-8')
        tree = ast.parse(source, filename=str(path))
        
        module_doc = ModuleDoc(
            name=self._infer_module_name(path),
            docstring=ast.get_docstring(tree),
            functions=[],
            classes=[],
            attributes=[],
            imports=[],
            source_file=path,
            submodules=[],
            all_exports=self._extract_all_exports(tree)
        )
        
        # Walk AST and extract elements
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Only top-level functions (not methods)
                if self._is_top_level(node, tree):
                    module_doc.functions.append(self._extract_function(node, path))
            
            elif isinstance(node, ast.ClassDef):
                if self._is_top_level(node, tree):
                    module_doc.classes.append(self._extract_class(node, path))
            
            elif isinstance(node, ast.AnnAssign):
                # Type-annotated module-level variables
                if self._is_top_level(node, tree):
                    module_doc.attributes.append(self._extract_attribute(node))
        
        return module_doc
    
    def _extract_function(self, node: ast.FunctionDef, source_file: Path) -> FunctionDoc:
        """Extract function/method documentation."""
        # Parse docstring (Google/NumPy/Sphinx style)
        docstring = ast.get_docstring(node)
        parsed_doc = self._parse_docstring(docstring) if docstring else {}
        
        # Extract signature
        signature = self._build_signature(node)
        
        # Extract arguments with docstrings
        args = []
        for arg in node.args.args:
            arg_doc = ArgumentDoc(
                name=arg.arg,
                annotation=self._annotation_to_string(arg.annotation),
                default=None,  # Handled separately
                kind='positional',
                docstring=parsed_doc.get('args', {}).get(arg.arg)
            )
            args.append(arg_doc)
        
        # Check decorators
        decorators = [self._decorator_to_string(d) for d in node.decorator_list]
        is_classmethod = 'classmethod' in decorators
        is_staticmethod = 'staticmethod' in decorators
        is_property = 'property' in decorators
        
        return FunctionDoc(
            name=node.name,
            qualname=node.name,  # Update with class name if method
            signature=signature,
            docstring=docstring,
            args=args,
            returns=self._annotation_to_string(node.returns),
            raises=parsed_doc.get('raises', []),
            decorators=decorators,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_classmethod=is_classmethod,
            is_staticmethod=is_staticmethod,
            is_property=is_property,
            source_file=source_file,
            line_number=node.lineno,
            examples=parsed_doc.get('examples', []),
            see_also=parsed_doc.get('see_also', []),
            deprecated=parsed_doc.get('deprecated'),
            added_version=parsed_doc.get('version_added')
        )
    
    def _extract_class(self, node: ast.ClassDef, source_file: Path) -> ClassDoc:
        """Extract class documentation."""
        methods = []
        properties = []
        attributes = []
        class_variables = []
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                func_doc = self._extract_function(item, source_file)
                func_doc.qualname = f"{node.name}.{func_doc.name}"
                
                if func_doc.is_property:
                    properties.append(func_doc)
                else:
                    methods.append(func_doc)
            
            elif isinstance(item, ast.AnnAssign):
                attr = self._extract_attribute(item)
                attributes.append(attr)
            
            elif isinstance(item, ast.Assign):
                # Class variables (no annotation)
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_variables.append(AttributeDoc(
                            name=target.id,
                            annotation=None,
                            default=self._expr_to_string(item.value),
                            docstring=None,
                            line_number=item.lineno
                        ))
        
        # Extract base classes
        bases = [self._expr_to_string(base) for base in node.bases]
        
        # Check for special decorators
        decorators = [self._decorator_to_string(d) for d in node.decorator_list]
        is_dataclass = 'dataclass' in decorators
        is_abstract = any('ABC' in base or 'abc.ABC' in base for base in bases)
        
        return ClassDoc(
            name=node.name,
            qualname=node.name,
            docstring=ast.get_docstring(node),
            bases=bases,
            methods=methods,
            attributes=attributes,
            properties=properties,
            class_variables=class_variables,
            decorators=decorators,
            source_file=source_file,
            line_number=node.lineno,
            is_abstract=is_abstract,
            is_dataclass=is_dataclass
        )
    
    def _parse_docstring(self, docstring: str) -> Dict[str, Any]:
        """
        Parse structured docstring (Google, NumPy, or Sphinx style).
        
        Returns dict with:
            - args: Dict[str, str] - argument descriptions
            - returns: str - return value description
            - raises: List[str] - exception types
            - examples: List[str] - code examples
            - see_also: List[str] - cross-references
            - deprecated: Optional[str] - deprecation notice
            - version_added: Optional[str] - version info
        """
        # Detect style
        if "Args:" in docstring or "Returns:" in docstring:
            return self._parse_google_docstring(docstring)
        elif "Parameters\n" in docstring or "--------" in docstring:
            return self._parse_numpy_docstring(docstring)
        else:
            return self._parse_sphinx_docstring(docstring)
    
    def _build_signature(self, node: ast.FunctionDef) -> str:
        """Build function signature string."""
        # Extract args, defaults, annotations
        args_parts = []
        
        # Regular args
        for arg in node.args.args:
            part = arg.arg
            if arg.annotation:
                part += f": {self._annotation_to_string(arg.annotation)}"
            args_parts.append(part)
        
        # Add defaults
        defaults = node.args.defaults
        if defaults:
            for i, default in enumerate(defaults):
                idx = len(args_parts) - len(defaults) + i
                args_parts[idx] += f" = {self._expr_to_string(default)}"
        
        # *args
        if node.args.vararg:
            part = f"*{node.args.vararg.arg}"
            if node.args.vararg.annotation:
                part += f": {self._annotation_to_string(node.args.vararg.annotation)}"
            args_parts.append(part)
        
        # **kwargs
        if node.args.kwarg:
            part = f"**{node.args.kwarg.arg}"
            if node.args.kwarg.annotation:
                part += f": {self._annotation_to_string(node.args.kwarg.annotation)}"
            args_parts.append(part)
        
        signature = f"def {node.name}({', '.join(args_parts)})"
        
        # Return annotation
        if node.returns:
            signature += f" -> {self._annotation_to_string(node.returns)}"
        
        return signature
    
    def _annotation_to_string(self, annotation: Optional[ast.expr]) -> Optional[str]:
        """Convert AST annotation to string."""
        if annotation is None:
            return None
        return ast.unparse(annotation)
    
    def _expr_to_string(self, expr: ast.expr) -> str:
        """Convert AST expression to string."""
        return ast.unparse(expr)
```

### Docstring Parsers

```python
# bengal/autodoc/docstring_parser.py

import re
from typing import Dict, List, Any, Optional

class GoogleDocstringParser:
    """
    Parse Google-style docstrings.
    
    Example:
        Args:
            name (str): The name to greet
            loud (bool): Whether to shout
            
        Returns:
            str: The greeting message
            
        Raises:
            ValueError: If name is empty
            
        Example:
            >>> greet("World", loud=True)
            'HELLO, WORLD!'
    """
    
    def parse(self, docstring: str) -> Dict[str, Any]:
        """Parse Google-style docstring."""
        sections = self._split_sections(docstring)
        
        return {
            'summary': sections.get('summary', ''),
            'description': sections.get('description', ''),
            'args': self._parse_args(sections.get('Args', '')),
            'returns': sections.get('Returns', ''),
            'raises': self._parse_raises(sections.get('Raises', '')),
            'examples': self._parse_examples(sections.get('Example', '')),
            'see_also': self._parse_see_also(sections.get('See Also', '')),
            'deprecated': sections.get('Deprecated'),
            'version_added': self._parse_version(sections.get('Version', ''))
        }
    
    def _split_sections(self, docstring: str) -> Dict[str, str]:
        """Split docstring into sections."""
        sections = {}
        current_section = 'summary'
        lines = docstring.split('\n')
        
        section_markers = ['Args:', 'Returns:', 'Raises:', 'Example:', 'Examples:', 
                          'See Also:', 'Note:', 'Warning:', 'Deprecated:']
        
        buffer = []
        for line in lines:
            stripped = line.strip()
            if any(stripped.startswith(marker) for marker in section_markers):
                # Save previous section
                if buffer:
                    sections[current_section] = '\n'.join(buffer).strip()
                    buffer = []
                current_section = stripped.rstrip(':')
            else:
                buffer.append(line)
        
        if buffer:
            sections[current_section] = '\n'.join(buffer).strip()
        
        return sections
    
    def _parse_args(self, args_section: str) -> Dict[str, str]:
        """Parse Args section into dict."""
        args = {}
        # Pattern: name (type): description
        pattern = r'(\w+)\s*(?:\(([^)]+)\))?\s*:\s*(.+)'
        
        for line in args_section.split('\n'):
            match = re.match(pattern, line.strip())
            if match:
                name, type_hint, description = match.groups()
                args[name] = description.strip()
        
        return args
    
    def _parse_raises(self, raises_section: str) -> List[str]:
        """Parse Raises section into list."""
        raises = []
        for line in raises_section.split('\n'):
            if ':' in line:
                exc_type = line.split(':')[0].strip()
                raises.append(exc_type)
        return raises
    
    def _parse_examples(self, example_section: str) -> List[str]:
        """Extract code examples."""
        # Look for >>> or code blocks
        examples = []
        in_example = False
        current_example = []
        
        for line in example_section.split('\n'):
            if '>>>' in line or line.strip().startswith('```'):
                in_example = True
            
            if in_example:
                current_example.append(line)
                
                if line.strip().endswith('```') and len(current_example) > 1:
                    examples.append('\n'.join(current_example))
                    current_example = []
                    in_example = False
        
        if current_example:
            examples.append('\n'.join(current_example))
        
        return examples


class NumpyDocstringParser:
    """Parse NumPy-style docstrings."""
    
    def parse(self, docstring: str) -> Dict[str, Any]:
        """Parse NumPy-style docstring."""
        # Similar to Google but different markers
        # Parameters, Returns, Raises, Examples, See Also, Notes
        # Uses -------- underlines
        pass


class SphinxDocstringParser:
    """
    Parse Sphinx-style docstrings.
    
    Example:
        :param name: The name to greet
        :type name: str
        :param loud: Whether to shout
        :type loud: bool
        :returns: The greeting message
        :rtype: str
        :raises ValueError: If name is empty
    """
    
    def parse(self, docstring: str) -> Dict[str, Any]:
        """Parse Sphinx-style docstring."""
        args = {}
        returns = None
        raises = []
        
        for line in docstring.split('\n'):
            line = line.strip()
            
            # :param name: description
            if line.startswith(':param'):
                match = re.match(r':param\s+(\w+):\s*(.+)', line)
                if match:
                    name, desc = match.groups()
                    args[name] = desc
            
            # :returns: description
            elif line.startswith(':returns:') or line.startswith(':return:'):
                returns = line.split(':', 2)[2].strip()
            
            # :raises Exception: description
            elif line.startswith(':raises'):
                match = re.match(r':raises\s+(\w+):', line)
                if match:
                    raises.append(match.group(1))
        
        return {
            'args': args,
            'returns': returns,
            'raises': raises,
            'examples': [],
            'see_also': []
        }
```

---

## Template System & Customization

### Default Template Hierarchy

Bengal will look for templates in this order:

1. `templates/autodoc/module.md` - Custom module template
2. `templates/autodoc/class.md` - Custom class template
3. `templates/autodoc/function.md` - Custom function template
4. `templates/api/module.md` - Alternative location
5. `templates/sdk/module.md` - Alternative location (for SDK docs)
6. Built-in defaults

### Template Context

Each template receives rich context:

```python
# Context for module.md template
{
    'module': ModuleDoc(
        name='bengal.core.site',
        docstring='Site object - orchestrates builds',
        functions=[...],
        classes=[...],
        attributes=[...],
        source_file=Path('bengal/core/site.py'),
        submodules=[...]
    ),
    'config': site.config,  # Site configuration
    'autodoc_config': {...},  # Autodoc-specific config
    'site': site  # Full site object for cross-references
}
```

### Default Templates

```markdown
<!-- templates/autodoc/module.md -->
---
title: "{{ module.name }}"
layout: autodoc-module
generated: true
module_path: "{{ module.name }}"
---

# {{ module.name }}

{{ module.docstring | default("No module description.") }}

**Source:** `{{ module.source_file.relative_to(source_dir) }}`

{% if module.all_exports %}
## Public API

Exported members (from `__all__`):
{% for name in module.all_exports %}
- `{{ name }}`
{% endfor %}
{% endif %}

{% if module.functions %}
## Functions

{% for func in module.functions %}
### {{ func.name }}

```python
{{ func.signature }}
```

{{ func.docstring | default("No description.") }}

{% if func.args %}
**Parameters:**

{% for arg in func.args %}
- **{{ arg.name }}**{% if arg.annotation %} (`{{ arg.annotation }}`){% endif %}{% if arg.default %} = `{{ arg.default }}`{% endif %}
  {% if arg.docstring %}{{ arg.docstring }}{% endif %}
{% endfor %}
{% endif %}

{% if func.returns %}
**Returns:** {{ func.returns }}
{% endif %}

{% if func.raises %}
**Raises:**

{% for exc in func.raises %}
- `{{ exc }}`
{% endfor %}
{% endif %}

{% if func.examples %}
**Examples:**

{% for example in func.examples %}
{{ example }}
{% endfor %}
{% endif %}

{% if func.see_also %}
**See Also:** {% for ref in func.see_also %}[[{{ ref }}]]{% if not loop.last %}, {% endif %}{% endfor %}
{% endif %}

{% if func.deprecated %}
!!! warning "Deprecated"
    {{ func.deprecated }}
{% endif %}

---
{% endfor %}
{% endif %}

{% if module.classes %}
## Classes

{% for cls in module.classes %}
### {{ cls.name }}

```python
class {{ cls.name }}{% if cls.bases %}({{ cls.bases | join(', ') }}){% endif %}
```

{{ cls.docstring | default("No description.") }}

{% if cls.attributes %}
**Attributes:**

{% for attr in cls.attributes %}
- **{{ attr.name }}**{% if attr.annotation %} (`{{ attr.annotation }}`){% endif %}{% if attr.default %} = `{{ attr.default }}`{% endif %}
  {% if attr.docstring %}{{ attr.docstring }}{% endif %}
{% endfor %}
{% endif %}

{% if cls.properties %}
**Properties:**

{% for prop in cls.properties %}
#### {{ prop.name }}

```python
@property
{{ prop.signature }}
```

{{ prop.docstring | default("No description.") }}
{% endfor %}
{% endif %}

{% if cls.methods %}
**Methods:**

{% for method in cls.methods %}
#### {{ method.name }}

```python
{{ method.signature }}
```

{{ method.docstring | default("No description.") }}

{% if method.args %}
**Parameters:**

{% for arg in method.args %}
- **{{ arg.name }}**{% if arg.annotation %} (`{{ arg.annotation }}`){% endif %}
  {% if arg.docstring %}{{ arg.docstring }}{% endif %}
{% endfor %}
{% endif %}

{% if method.returns %}
**Returns:** {{ method.returns }}
{% endif %}

---
{% endfor %}
{% endif %}

{% endfor %}
{% endif %}
```

### Customization Examples

#### Example 1: Minimal API Reference

```markdown
<!-- templates/api/function.md -->
---
title: "{{ func.qualname }}"
---

# {{ func.name }}

```python
{{ func.signature }}
```

{{ func.docstring }}
```

#### Example 2: SDK Documentation Style

```markdown
<!-- templates/sdk/class.md -->
---
title: "{{ cls.name }} - {{ site.config.site.title }}"
description: "{{ cls.docstring | truncate(150) }}"
---

<div class="sdk-header">
  <h1>{{ cls.name }}</h1>
  <span class="badge">{{ cls.source_file.stem }}</span>
</div>

## Overview

{{ cls.docstring }}

## Quick Start

{% if cls.methods | selectattr('name', 'equalto', '__init__') | first %}
{{ cls.methods | selectattr('name', 'equalto', '__init__') | first | extract_example }}
{% endif %}

## Methods

<div class="method-grid">
{% for method in cls.methods if not method.name.startswith('_') %}
  <div class="method-card">
    <h3>{{ method.name }}</h3>
    <code>{{ method.signature | truncate(60) }}</code>
    <p>{{ method.docstring | truncate(100) }}</p>
    <a href="#{{ method.name }}">Details →</a>
  </div>
{% endfor %}
</div>

## Detailed Reference

{% for method in cls.methods %}
### {{ method.name }}
<!-- ... full details ... -->
{% endfor %}
```

#### Example 3: ReadTheDocs Style

```markdown
<!-- templates/autodoc/module.md -->
---
title: "{{ module.name }}"
nav_section: "API Reference"
---

.. module:: {{ module.name }}

{{ module.name }}
{{ '=' * module.name | length }}

{{ module.docstring }}

{% if module.functions %}
Functions
---------

{% for func in module.functions %}
.. function:: {{ func.signature }}

   {{ func.docstring | indent(3) }}
   
{% endfor %}
{% endif %}
```

### Template Customization API

Users can also customize programmatically:

```python
# bengal/autodoc/templates.py

class TemplateCustomizer:
    """Allow programmatic template customization."""
    
    def register_filter(self, name: str, func: callable):
        """Register custom Jinja2 filter."""
        
    def register_function(self, name: str, func: callable):
        """Register custom Jinja2 function."""
        
    def set_template_dir(self, path: Path):
        """Override template directory."""

# In site config or hook:
autodoc.templates.register_filter('format_signature', my_formatter)
autodoc.templates.register_function('extract_example', my_example_extractor)
```

---

## Cross-Reference System

### Cross-Reference Syntax

Bengal will support multiple cross-reference syntaxes:

```markdown
<!-- Sphinx-compatible -->
:func:`function_name`
:class:`ClassName`
:meth:`ClassName.method_name`
:mod:`module.name`

<!-- Bengal shorthand (preferred) -->
[[function_name]]
[[ClassName]]
[[ClassName.method_name]]
[[module.name]]

<!-- Markdown reference -->
[function_name][bengal.core.site.build]
```

### Cross-Reference Resolution

```python
# bengal/autodoc/cross_refs.py

class CrossReferenceResolver:
    """
    Resolve cross-references to Python API elements.
    
    Features:
    - Resolve partial names (smart search)
    - Handle imports (resolve 'Site' to 'bengal.core.site.Site')
    - Generate links to API docs
    - Warning on broken references
    """
    
    def __init__(self, api_index: Dict[str, Any]):
        """
        Initialize resolver.
        
        Args:
            api_index: Index of all API elements (from extraction)
        """
        self.api_index = api_index
        self._build_index()
    
    def _build_index(self):
        """Build searchable index of all API elements."""
        self.index = {
            'functions': {},  # name -> full path
            'classes': {},
            'methods': {},
            'modules': {},
            'attributes': {}
        }
        
        # Populate from extracted docs
        for module_path, module_doc in self.api_index.items():
            self.index['modules'][module_doc.name] = module_path
            
            for func in module_doc.functions:
                self.index['functions'][func.name] = f"{module_path}.{func.name}"
                self.index['functions'][func.qualname] = f"{module_path}.{func.qualname}"
            
            for cls in module_doc.classes:
                self.index['classes'][cls.name] = f"{module_path}.{cls.name}"
                
                for method in cls.methods:
                    full_name = f"{cls.name}.{method.name}"
                    self.index['methods'][full_name] = f"{module_path}.{full_name}"
    
    def resolve(self, ref: str, context: Optional[str] = None) -> Optional[str]:
        """
        Resolve reference to URL.
        
        Args:
            ref: Reference string (e.g., 'Site.build' or 'build')
            context: Current module context for relative resolution
            
        Returns:
            URL to API doc, or None if not found
            
        Example:
            >>> resolver.resolve('Site.build')
            '/api/bengal/core/site/#Site.build'
            
            >>> resolver.resolve('build', context='bengal.core.site')
            '/api/bengal/core/site/#Site.build'
        """
        # Try exact match first
        for element_type, index in self.index.items():
            if ref in index:
                return self._generate_url(index[ref], element_type)
        
        # Try partial match
        candidates = []
        for element_type, index in self.index.items():
            for name, full_path in index.items():
                if name.endswith(ref):
                    candidates.append((full_path, element_type))
        
        if len(candidates) == 1:
            return self._generate_url(candidates[0][0], candidates[0][1])
        elif len(candidates) > 1:
            # Ambiguous reference - use context to resolve
            if context:
                # Prefer references in same module
                for full_path, element_type in candidates:
                    if full_path.startswith(context):
                        return self._generate_url(full_path, element_type)
            
            # Still ambiguous - log warning
            logger.warning(f"Ambiguous reference '{ref}': {[c[0] for c in candidates]}")
            return self._generate_url(candidates[0][0], candidates[0][1])
        
        # Not found
        logger.warning(f"Could not resolve reference: {ref}")
        return None
    
    def _generate_url(self, full_path: str, element_type: str) -> str:
        """Generate URL for API element."""
        # e.g., 'bengal.core.site.Site.build' -> '/api/bengal/core/site/#Site.build'
        parts = full_path.split('.')
        module_path = '.'.join(parts[:-1])  # bengal.core.site
        element_name = parts[-1]  # build
        
        return f"/api/{module_path.replace('.', '/')}#{element_name}"


# Integration with Bengal's rendering pipeline
class CrossReferencePlugin:
    """Mistune plugin to resolve cross-references during rendering."""
    
    def __init__(self, resolver: CrossReferenceResolver):
        self.resolver = resolver
    
    def parse(self, inline, m, state):
        """Parse [[ref]] syntax."""
        ref = m.group(1)
        url = self.resolver.resolve(ref, context=state.get('current_module'))
        
        if url:
            return 'link', url, ref
        else:
            # Broken reference - render as code
            return 'codespan', ref
```

### Cross-Reference Validation

```python
# Run as health check after build
class CrossReferenceValidator:
    """Validate all cross-references in API docs."""
    
    def validate(self, site: Site) -> List[CheckResult]:
        """Check all cross-references resolve."""
        broken_refs = []
        
        for page in site.pages:
            if page.metadata.get('generated') and page.metadata.get('module_path'):
                refs = self._extract_refs(page.content)
                for ref in refs:
                    if not self.resolver.resolve(ref):
                        broken_refs.append((page.source_path, ref))
        
        if broken_refs:
            return [CheckResult(
                status=CheckStatus.ERROR,
                message=f"Found {len(broken_refs)} broken cross-references",
                details=broken_refs
            )]
        
        return [CheckResult(
            status=CheckStatus.SUCCESS,
            message="All cross-references valid"
        )]
```

---

## Configuration & CLI

### Configuration File

```toml
# bengal.toml

[autodoc]
# Enable autodoc
enabled = true

# Source directories to document
source_dirs = ["src/bengal"]

# Output directory (relative to content/)
output_dir = "api"

# Exclude patterns
exclude = [
    "*/tests/*",
    "*/test_*.py",
    "*/__pycache__/*",
    "*/migrations/*"
]

# Docstring style (auto-detect, google, numpy, sphinx)
docstring_style = "auto"

# Template directory (optional)
template_dir = "templates/autodoc"

# Generate index pages
generate_index = true

# Cross-reference configuration
[autodoc.cross_refs]
enabled = true
resolve_imports = true  # Try to resolve imported names
warn_broken = true      # Warn on broken references

# Member visibility
[autodoc.members]
private = false          # Include _private methods
special = false          # Include __special__ methods
inherited = true         # Include inherited members
undocumented = true      # Include members without docstrings

# Sorting
[autodoc.sorting]
classes = "alphabetical"    # alphabetical, source, custom
functions = "alphabetical"
members = "source"          # Keep source order for class members

# Output format
[autodoc.output]
format = "markdown"           # Output format
one_file_per = "module"       # module, class, function
include_source_links = true   # Link to source code
include_edit_links = true     # "Edit this page" links

# Advanced: Import fallback (use sparingly!)
[autodoc.import_fallback]
enabled = false              # Enable import-based extraction for dynamic code
mock_imports = ["torch", "tensorflow"]  # Mock these imports
```

### CLI Commands

```bash
# Extract API documentation
$ bengal autodoc [OPTIONS]

Options:
  --source-dir PATH        Source directory (can be repeated)
  --output-dir PATH        Output directory
  --config FILE            Config file (default: bengal.toml)
  --clean                  Clean output directory first
  --watch                  Watch for changes and regenerate
  --verbose                Show detailed output
  
Examples:
  # Basic usage
  $ bengal autodoc
  
  # Multiple source directories
  $ bengal autodoc --source-dir src/core --source-dir src/plugins
  
  # Watch mode (auto-regenerate on changes)
  $ bengal autodoc --watch
  
  # Generate and build
  $ bengal autodoc && bengal build


# Validate cross-references
$ bengal autodoc --validate

Checking cross-references...
  ✓ 127 references resolved
  ✗ 3 broken references:
    - api/core/site.md:42: [[Page.render]] -> not found
    - api/utils/helpers.md:18: [[unknown_function]] -> not found


# Show API coverage
$ bengal autodoc --coverage

API Documentation Coverage:
  Modules:     23/25 (92%)
  Classes:     45/48 (94%)
  Functions:   120/135 (89%)
  Methods:     234/256 (91%)
  
  Missing documentation:
    - bengal.utils.internal.helper (no docstring)
    - bengal.core.Asset.optimize (no docstring)
    ...
```

### Integration with Build

```python
# bengal/orchestration/autodoc.py

class AutodocOrchestrator:
    """
    Orchestrate API documentation generation.
    Integrates with Bengal's build pipeline.
    """
    
    def __init__(self, site: Site):
        self.site = site
        self.config = site.config.get('autodoc', {})
        self.extractor = None
        self.resolver = None
    
    def run(self, watch: bool = False) -> bool:
        """
        Generate API documentation.
        
        Args:
            watch: Continue watching for changes
            
        Returns:
            True if successful
        """
        if not self.config.get('enabled', False):
            return True
        
        print("\n📚 Generating API Documentation...")
        
        # Extract from source
        source_dirs = [Path(d) for d in self.config['source_dirs']]
        self.extractor = PythonAPIExtractor(
            source_dirs=source_dirs,
            exclude_patterns=self.config.get('exclude', [])
        )
        
        modules = self.extractor.extract_all()
        print(f"   Extracted {len(modules)} modules")
        
        # Build cross-reference index
        self.resolver = CrossReferenceResolver(modules)
        
        # Generate markdown files
        generator = MarkdownGenerator(
            template_dir=self.config.get('template_dir'),
            config=self.config
        )
        
        output_dir = self.site.root_path / 'content' / self.config['output_dir']
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generated_count = 0
        for module_name, module_doc in modules.items():
            output_path = self._get_output_path(module_name, output_dir)
            content = generator.generate_module(module_doc)
            
            # Write markdown file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding='utf-8')
            generated_count += 1
        
        print(f"   Generated {generated_count} API documentation pages")
        
        # Generate index
        if self.config.get('generate_index', True):
            index_content = generator.generate_index(modules)
            index_path = output_dir / 'index.md'
            index_path.write_text(index_content, encoding='utf-8')
            print(f"   Generated API index")
        
        # Watch mode
        if watch:
            self._watch_for_changes(source_dirs)
        
        return True
    
    def _watch_for_changes(self, source_dirs: List[Path]):
        """Watch source directories and regenerate on changes."""
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
        
        class SourceChangeHandler(FileSystemEventHandler):
            def __init__(self, orchestrator):
                self.orchestrator = orchestrator
            
            def on_modified(self, event):
                if event.src_path.endswith('.py'):
                    print(f"\n📝 {Path(event.src_path).name} changed, regenerating...")
                    self.orchestrator.run(watch=False)
        
        observer = Observer()
        handler = SourceChangeHandler(self)
        
        for source_dir in source_dirs:
            observer.schedule(handler, str(source_dir), recursive=True)
        
        observer.start()
        print("\n👀 Watching for changes (Ctrl+C to stop)...")
        
        try:
            observer.join()
        except KeyboardInterrupt:
            observer.stop()
            observer.join()
```

---

## Migration from Sphinx

### Sphinx Autodoc Directive Converter

```python
# bengal/autodoc/sphinx_migration.py

class SphinxAutodocConverter:
    """
    Convert Sphinx autodoc directives to Bengal autodoc.
    
    Handles:
    - .. automodule::
    - .. autoclass::
    - .. autofunction::
    - .. automethod::
    """
    
    def convert_rst_file(self, rst_path: Path) -> str:
        """
        Convert RST file with autodoc directives to Markdown.
        
        Returns:
            Converted Markdown content
        """
        content = rst_path.read_text()
        
        # Replace automodule directives
        content = re.sub(
            r'\.\. automodule:: ([^\n]+)\n((?:   :[^\n]+\n)*)',
            self._convert_automodule,
            content
        )
        
        # Replace autoclass directives
        content = re.sub(
            r'\.\. autoclass:: ([^\n]+)\n((?:   :[^\n]+\n)*)',
            self._convert_autoclass,
            content
        )
        
        # Convert RST to Markdown
        content = self._rst_to_markdown(content)
        
        return content
    
    def _convert_automodule(self, match) -> str:
        """Convert automodule directive."""
        module_name = match.group(1).strip()
        options = self._parse_options(match.group(2))
        
        # In Bengal, this is just a reference
        return f"[[{module_name}]]"
    
    def _convert_autoclass(self, match) -> str:
        """Convert autoclass directive."""
        class_name = match.group(1).strip()
        options = self._parse_options(match.group(2))
        
        # Include members?
        if 'members' in options:
            return f"[[{class_name}]]  <!-- Full class documentation -->"
        else:
            return f"[[{class_name}]]  <!-- Summary only -->"
    
    def generate_bengal_config(self, conf_py: Path) -> Dict[str, Any]:
        """
        Extract autodoc configuration from conf.py.
        
        Returns:
            Bengal autodoc configuration dict
        """
        # Parse conf.py (safely, without executing)
        config = {}
        
        conf_content = conf_py.read_text()
        
        # Extract autodoc settings
        if match := re.search(r"autodoc_default_options\s*=\s*(\{[^}]+\})", conf_content):
            # Parse options dict
            pass
        
        if match := re.search(r"autodoc_mock_imports\s*=\s*\[([^\]]+)\]", conf_content):
            imports = [i.strip().strip('"\'') for i in match.group(1).split(',')]
            config['mock_imports'] = imports
        
        return config


# CLI integration
def migrate_from_sphinx(sphinx_dir: Path, output_dir: Path):
    """
    Migrate Sphinx project to Bengal.
    
    Steps:
    1. Convert conf.py -> bengal.toml
    2. Convert .rst files -> .md files
    3. Setup autodoc configuration
    4. Generate initial API docs
    """
    print("🔄 Migrating from Sphinx...")
    
    # Find conf.py
    conf_py = sphinx_dir / 'source' / 'conf.py'
    if not conf_py.exists():
        conf_py = sphinx_dir / 'conf.py'
    
    if conf_py.exists():
        print(f"   ✓ Found {conf_py}")
        converter = SphinxAutodocConverter()
        autodoc_config = converter.generate_bengal_config(conf_py)
        # Write to bengal.toml
    
    # Convert RST files
    rst_files = list(sphinx_dir.rglob("*.rst"))
    print(f"   Found {len(rst_files)} RST files")
    
    for rst_file in rst_files:
        md_file = output_dir / rst_file.relative_to(sphinx_dir).with_suffix('.md')
        md_file.parent.mkdir(parents=True, exist_ok=True)
        
        converted = converter.convert_rst_file(rst_file)
        md_file.write_text(converted)
    
    print(f"   ✓ Converted {len(rst_files)} files")
    print("\n✅ Migration complete!")
    print("\nNext steps:")
    print("  1. Review bengal.toml")
    print("  2. Run: bengal autodoc")
    print("  3. Run: bengal build")
```

---

## Implementation Roadmap

### Week 1: Core Extraction (5 days)

**Day 1-2: AST Parser**
- [x] Create `PythonAPIExtractor` class
- [x] Extract functions (name, signature, docstring)
- [x] Extract classes (name, methods, attributes)
- [x] Extract modules (structure, exports)
- [x] Handle type annotations
- [x] Tests for extraction

**Day 3: Docstring Parsers**
- [x] GoogleDocstringParser
- [x] NumpyDocstringParser  
- [x] SphinxDocstringParser
- [x] Auto-detection
- [x] Tests for all styles

**Day 4-5: Markdown Generation**
- [x] MarkdownGenerator class
- [x] Default templates (module, class, function)
- [x] Template loading system
- [x] Generate API docs from extracted data
- [x] Integration tests

**Deliverable**: Can extract and generate basic API docs

---

### Week 2: Templates & Customization (5 days)

**Day 1-2: Template System**
- [x] Template hierarchy (autodoc/, api/, sdk/)
- [x] Custom template loading
- [x] Template context building
- [x] Custom filters/functions
- [x] Examples of different styles

**Day 3: Configuration**
- [x] bengal.toml [autodoc] section
- [x] Member filtering (private, special, etc.)
- [x] Sorting options
- [x] Output options
- [x] Validation

**Day 4-5: CLI Integration**
- [x] `bengal autodoc` command
- [x] Watch mode
- [x] Integration with `bengal build`
- [x] Progress output
- [x] Error handling

**Deliverable**: Fully customizable API doc generation

---

### Week 3: Cross-References & Polish (5 days)

**Day 1-2: Cross-Reference System**
- [x] CrossReferenceResolver
- [x] Build API index
- [x] Resolve [[ref]] syntax
- [x] Sphinx :func: compatibility
- [x] Smart partial matching
- [x] Tests

**Day 3: Integration**
- [x] Mistune plugin for cross-refs
- [x] Resolve during rendering
- [x] Generate proper links
- [x] Broken reference warnings
- [x] Health check validator

**Day 4: Advanced Features**
- [x] Source code links
- [x] "Edit this page" links
- [x] Inheritance documentation
- [x] Coverage reporting
- [x] API index generation

**Day 5: Documentation**
- [x] Write user guide
- [x] Write customization guide
- [x] Create examples
- [x] Video tutorial (optional)

**Deliverable**: Production-ready autodoc system

---

### Week 4: Migration & Launch (5 days)

**Day 1-2: Sphinx Migration**
- [x] SphinxAutodocConverter
- [x] conf.py parser
- [x] RST converter
- [x] `bengal migrate` command
- [x] Migration guide

**Day 3: Theme**
- [x] API documentation theme preset
- [x] Three-column layout
- [x] Syntax highlighting
- [x] Search-ready structure

**Day 4: Testing & Polish**
- [x] Test on real projects
- [x] Performance optimization
- [x] Bug fixes
- [x] Error message improvements

**Day 5: Launch**
- [x] Ship v0.3.0
- [x] Write announcement
- [x] Update documentation
- [x] Create comparison demos

**Deliverable**: v0.3.0 "API Documentation Release"

---

## Success Metrics

### Functional Metrics
- ✅ Extract 95%+ of Python API elements (functions, classes, methods)
- ✅ Support all 3 docstring styles (Google, NumPy, Sphinx)
- ✅ Resolve 90%+ of cross-references
- ✅ Generate docs in < 5 seconds for typical library (50 modules)
- ✅ Zero import errors during extraction

### Quality Metrics
- ✅ Beautiful default output (comparable to Sphinx/MkDocs)
- ✅ Fully customizable templates
- ✅ Helpful error messages
- ✅ Health checks catch issues

### Adoption Metrics  
- ✅ Migrate 3-5 real projects from Sphinx
- ✅ Get feedback from early adopters
- ✅ Document pain points for iteration

---

## Technical Risks & Mitigation

### Risk 1: AST Can't Handle Dynamic Code

**Example**: Runtime-generated methods, metaclasses, decorators that add members

**Mitigation**:
1. **80/20 Rule**: AST handles 80%+ of real-world code
2. **Fallback Mode**: Optional import-based extraction for edge cases
3. **Manual Override**: Let users document dynamic code manually
4. **Clear Documentation**: Explain what works and what doesn't

**Acceptance**: Some dynamic code won't be auto-documented. That's OK. Sphinx has the same issue.

---

### Risk 2: Docstring Parsing Edge Cases

**Example**: Custom formats, malformed docstrings, mixed styles

**Mitigation**:
1. **Graceful Degradation**: If parsing fails, show raw docstring
2. **Best Effort**: Extract what we can, skip what we can't
3. **User Control**: Let users override with manual docs
4. **Iterative**: Add parsers for common custom formats over time

---

### Risk 3: Cross-Reference Ambiguity

**Example**: Multiple `build()` methods across codebase

**Mitigation**:
1. **Context-Aware**: Use current module for disambiguation
2. **Full Paths**: Support `module.Class.method` for precision
3. **Warnings**: Alert on ambiguous references
4. **Override**: Let users specify full path when needed

---

## Future Enhancements (Post-v0.3.0)

### Phase 2 (v0.4.0)
- **Type Checking Integration**: Use mypy/pyright for better type info
- **Stub File Support**: Generate and use `.pyi` stubs
- **Inherited Members**: Show inherited methods with source links
- **Search Integration**: Generate search index for API docs

### Phase 3 (v0.5.0)
- **Multi-Language**: Support TypeScript/JavaScript (via AST)
- **Examples from Tests**: Extract examples from test files
- **Changelog Integration**: Link API changes to changelog entries
- **Coverage Dashboard**: Visual API documentation coverage

---

## Conclusion

This autodoc system will give Bengal a **technical advantage** over Sphinx:

1. **More Reliable**: AST parsing > import-based
2. **Faster**: No code execution
3. **More Flexible**: Full template customization
4. **Better DX**: Clear errors, health checks, watch mode

**Timeline**: 3-4 weeks to v0.3.0  
**Outcome**: Competitive with Sphinx, superior experience

Ship this, and Bengal becomes the obvious choice for Python documentation.

---

*Next: Create VERSIONED_DOCS_IMPLEMENTATION_PLAN.md*

