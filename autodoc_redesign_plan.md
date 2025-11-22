# Bengal Autodoc Template Redesign Plan

## Overview

Redesign Bengal's autodoc template system to be safer, more maintainable, and less prone to silent failures by combining Hugo-style safety patterns with template decomposition across Python API, CLI, and OpenAPI documentation.

## Current Problems

### Template Complexity ✅ **RESOLVED**
- **Python**: `python/module.md.jinja2` decomposed into focused partials
- **CLI**: `cli/command.md.jinja2` and `cli/command_group.md.jinja2` with safe rendering
- **OpenAPI**: `openapi/endpoint.md.jinja2` and `openapi/schema.md.jinja2` with error boundaries
- **All**: Repetitive patterns across different doc types

### Safety Issues
- **Silent failures**: Template errors often produce empty/broken output
- **Whitespace sensitivity**: Easy to break with spacing issues
- **Hard to debug**: When something breaks, hard to isolate the problem
- **No error boundaries**: One template failure can break entire page

### Maintainability Issues
- **Monolithic templates**: Single large files doing too much
- **Code duplication**: Same patterns repeated across templates
- **No reusable components**: Each template reinvents parameter tables, etc.
- **No inheritance**: Common layouts duplicated

## Design Goals

1. **Safety First**: Templates should fail gracefully with clear error messages
2. **Maintainability**: Small, focused templates that are easy to edit
3. **Reusability**: Shared components across Python/CLI/OpenAPI docs
4. **Debuggability**: Clear error isolation and helpful debugging info
5. **Consistency**: Unified patterns across all documentation types

## Architecture Overview

```
bengal/autodoc/templates/
├── base/                          # Shared base templates
│   ├── base.md.jinja2            # Common layout inheritance
│   ├── error_fallback.md.jinja2  # Error boundary fallbacks
│   └── metadata.md.jinja2        # Common frontmatter
├── macros/                        # Reusable components
│   ├── safe_macros.md.jinja2     # Error boundaries, safe rendering
│   ├── parameter_table.md.jinja2 # Shared parameter rendering
│   ├── code_blocks.md.jinja2     # Code formatting utilities
│   └── navigation.md.jinja2      # Cross-references, links
├── python/                        # Python API templates ✅ IMPLEMENTED
│   ├── module.md.jinja2          # Main module template (simplified)
│   ├── class.md.jinja2           # Standalone class template
│   ├── function.md.jinja2        # Standalone function template
│   └── partials/                 # Module sub-components
│       ├── module_description.md.jinja2
│       ├── module_classes.md.jinja2
│       ├── module_functions.md.jinja2
│       ├── class_methods.md.jinja2
│       ├── class_properties.md.jinja2
│       └── function_signature.md.jinja2
├── cli/                          # CLI documentation templates
│   ├── command_group.md.jinja2   # Main command group template
│   ├── command.md.jinja2         # Individual command template
│   └── partials/                 # CLI sub-components
│       ├── command_description.md.jinja2
│       ├── command_options.md.jinja2
│       ├── command_arguments.md.jinja2
│       ├── command_examples.md.jinja2
│       └── subcommands_list.md.jinja2
└── openapi/                      # OpenAPI/REST templates
    ├── api_overview.md.jinja2    # Main API documentation
    ├── endpoint.md.jinja2        # Individual endpoint template
    ├── schema.md.jinja2          # Data schema template
    └── partials/                 # OpenAPI sub-components
        ├── endpoint_description.md.jinja2
        ├── request_body.md.jinja2
        ├── response_schemas.md.jinja2
        ├── parameters_table.md.jinja2
        └── examples_section.md.jinja2
```

## Implementation Plan

### Phase 1: Foundation (Week 1-2)

#### 1.1 Create Safe Template Infrastructure
- **File**: `bengal/autodoc/template_safety.py`
- **Purpose**: Hugo-style error handling and safe rendering
- **Features**:
  - Error boundary decorators
  - Safe context creation
  - Fallback content generation
  - Template validation utilities

#### 1.2 Build Shared Macro Library
- **Files**: `bengal/autodoc/templates/macros/*.md.jinja2`
- **Components**:
  - `safe_macros.md.jinja2` - Error boundaries, safe rendering
  - `parameter_table.md.jinja2` - Unified parameter/argument tables
  - `code_blocks.md.jinja2` - Code formatting with syntax highlighting
  - `navigation.md.jinja2` - Cross-references and internal links

#### 1.3 Create Base Template System
- **Files**: `bengal/autodoc/templates/base/*.md.jinja2`
- **Features**:
  - Template inheritance for common layouts
  - Shared frontmatter generation
  - Error fallback templates
  - Consistent styling hooks

### Phase 2: Python API Templates (Week 3-4)

#### 2.1 Decompose Python Module Template ✅ **COMPLETED**
**Previous**: 361-line `module.md.jinja2`
**New Structure**:
```
python/
├── module.md.jinja2           # 30-40 lines - orchestrates partials
└── partials/
    ├── module_description.md.jinja2    # 10-15 lines
    ├── module_aliases.md.jinja2        # 15-20 lines
    ├── module_classes.md.jinja2        # 20-25 lines
    ├── module_functions.md.jinja2      # 20-25 lines
    ├── module_constants.md.jinja2      # 15-20 lines
    ├── class_detail.md.jinja2          # 40-50 lines
    ├── method_detail.md.jinja2         # 30-40 lines
    └── function_detail.md.jinja2       # 25-35 lines
```

#### 2.2 Add Python-Specific Safety Features
- Type annotation safe rendering
- Docstring parsing error handling
- Import path validation
- Signature formatting safety

#### 2.3 Create Standalone Templates ✅ **COMPLETED**
- ✅ `python/class.md.jinja2` - For individual class pages
- ✅ `python/function.md.jinja2` - For individual function pages
- ✅ Enable flexible documentation organization with unified directory structure

### Phase 3: CLI Templates (Week 5)

#### 3.1 Redesign CLI Command Templates
**Current Issues**: Complex nested command/option logic
**New Structure**:
```
cli/
├── command_group.md.jinja2    # Main command group (like 'bengal site')
├── command.md.jinja2          # Individual command (like 'bengal site build')
└── partials/
    ├── command_description.md.jinja2   # Command help text
    ├── command_usage.md.jinja2         # Usage syntax
    ├── command_options.md.jinja2       # Options table
    ├── command_arguments.md.jinja2     # Arguments table
    ├── command_examples.md.jinja2      # Usage examples
    └── subcommands_list.md.jinja2      # Nested commands
```

#### 3.2 CLI-Specific Safety Features
- Click framework error handling
- Option/argument validation
- Command hierarchy navigation
- Example code validation

### Phase 4: OpenAPI Templates (Week 6)

#### 4.1 Create OpenAPI Template System
**New Structure**:
```
openapi/
├── api_overview.md.jinja2     # Main API documentation page
├── endpoint.md.jinja2         # Individual REST endpoint
├── schema.md.jinja2           # Data model/schema
└── partials/
    ├── endpoint_description.md.jinja2  # Endpoint summary
    ├── http_methods.md.jinja2          # GET/POST/PUT/DELETE
    ├── request_body.md.jinja2          # Request schema/examples
    ├── response_schemas.md.jinja2      # Response formats
    ├── parameters_table.md.jinja2      # Query/path parameters
    ├── authentication.md.jinja2        # Auth requirements
    └── examples_section.md.jinja2      # Request/response examples
```

#### 4.2 OpenAPI-Specific Features
- JSON Schema validation
- HTTP status code handling
- Authentication method rendering
- Request/response example formatting

### Phase 5: Integration & Testing (Week 7)

#### 5.1 Update Template Engine
- **File**: `bengal/autodoc/generator.py`
- **Changes**:
  - Add safe rendering methods
  - Integrate error boundaries
  - Add template validation
  - Support new template structure

#### 5.2 Create Template Testing Framework
- **File**: `tests/unit/autodoc/test_template_safety.py`
- **Features**:
  - Test all templates with sample data
  - Validate error handling
  - Check for unrendered variables
  - Performance regression tests

#### 5.3 Migration Tools
- **File**: `bengal/utils/template_migrator.py`
- **Purpose**: Help users migrate custom templates
- **Features**:
  - Analyze existing templates
  - Suggest decomposition strategies
  - Validate new template structure

### Phase 6: Documentation & Polish (Week 8)

#### 6.1 Template Development Guide
- How to create safe templates
- Best practices for error handling
- Template debugging techniques
- Custom template creation guide

#### 6.2 Performance Optimization
- Template caching improvements
- Lazy loading for large documentation sets
- Memory usage optimization
- Build time benchmarking

## Technical Specifications

### Safe Template Rendering

```python
# bengal/autodoc/template_safety.py

class SafeTemplateRenderer:
    """Hugo-style safe template rendering with error boundaries."""

    def render_with_boundaries(self, template_name: str, context: dict) -> str:
        """Render template with error boundaries and fallbacks."""
        try:
            return self._render_template(template_name, context)
        except TemplateError as e:
            return self._render_fallback(template_name, context, e)

    def _render_fallback(self, template_name: str, context: dict, error: Exception) -> str:
        """Generate fallback content when template fails."""
        element = context.get('element')
        return f"""# {element.name if element else 'Documentation'}

**Template Error**: {template_name} failed to render.

**Error**: {str(error)}

**Fallback Content**: Basic information is shown below.

{self._generate_basic_content(element)}
"""
```

### Shared Macro System

```jinja2
{# macros/parameter_table.md.jinja2 #}
{% macro parameter_table(parameters, title="Parameters", show_types=true) %}
{% if parameters %}
**{{ title }}:**

| Name | {% if show_types %}Type | {% endif %}Default | Description |
|------|{% if show_types %}------|{% endif %}---------|-------------|
{% for param in parameters %}
{% call safe_render_param(param) %}
| `{{ param.name }}` | {% if show_types %}{{ param.type | safe_type }}{% endif %} | {{ param.default | safe_default }} | {{ param.description | safe_description }} |
{% endcall %}
{% endfor %}

{% endif %}
{% endmacro %}

{% macro safe_render_param(param) %}
{% try %}
{{ caller() }}
{% except %}
| `{{ param.name }}` | - | - | *(parameter info unavailable)* |
{% endtry %}
{% endmacro %}
```

### Template Inheritance

```jinja2
{# base/base.md.jinja2 #}
---
title: "{% block title %}{{ element.name }}{% endblock %}"
type: "{% block doc_type %}doc{% endblock %}"
source_file: "{{ element.source_file | project_relative }}"
description: "{% block description %}{{ element.description | safe_description }}{% endblock %}"
---

{% block header %}
# {% block page_title %}{{ element.name }}{% endblock %}
{% endblock %}

{% block content %}
{# Child templates override this #}
{% endblock %}

{% block footer %}
---
*Generated by Bengal autodoc*
{% endblock %}
```

## Benefits

### Safety Improvements
- **Error isolation**: Template failures don't break entire pages
- **Graceful degradation**: Fallback content when rendering fails
- **Clear error messages**: Developers know exactly what broke
- **Validation**: Templates validated before use

### Maintainability Improvements
- **Small files**: Each template < 50 lines, focused on one thing
- **Reusable components**: Shared macros across all doc types
- **Template inheritance**: Common layouts defined once
- **Clear structure**: Easy to find and edit specific functionality

### Developer Experience
- **Easier debugging**: Stack traces point to specific small files
- **Faster iteration**: Edit small focused templates
- **Better testing**: Each component can be tested independently
- **Documentation**: Clear guides for template development

## Migration Strategy

### Backward Compatibility
1. **Phase 1-2**: New templates alongside old ones
2. **Phase 3-4**: Feature flag to switch between systems
3. **Phase 5-6**: Migration tools and documentation
4. **Phase 7**: Deprecate old templates (next major version)

### User Impact
- **Minimal disruption**: Existing sites continue working
- **Opt-in migration**: Users can migrate when ready
- **Migration assistance**: Tools to help convert custom templates
- **Clear upgrade path**: Step-by-step migration guide

## Success Metrics

### Template Safety
- **Zero silent failures**: All template errors produce visible output
- **Error recovery rate**: 95%+ of template errors have useful fallbacks
- **Debug time reduction**: 50%+ faster to identify template issues

### Maintainability
- **Template size reduction**: Average template size < 50 lines
- **Code reuse**: 80%+ of common patterns use shared macros
- **Edit frequency**: Developers can make changes confidently

### Performance
- **Build time**: No regression in documentation generation speed
- **Memory usage**: Efficient template loading and caching
- **Cache hit rate**: Improved template caching effectiveness

## Timeline Summary

- **Week 1-2**: Foundation (safe rendering, macros, base templates)
- **Week 3-4**: Python API templates (decompose 361-line monster)
- **Week 5**: CLI templates (command/option safety)
- **Week 6**: OpenAPI templates (REST endpoint documentation)
- **Week 7**: Integration & testing (template engine updates)
- **Week 8**: Documentation & polish (guides, optimization)

**Total**: 8 weeks for complete redesign with full backward compatibility and migration support.
