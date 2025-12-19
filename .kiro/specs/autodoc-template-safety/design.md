# Design: Autodoc Template Safety and Maintainability

## Overview

This design implements a comprehensive redesign of Bengal's autodoc template system using Hugo-inspired safety patterns and template decomposition to eliminate silent failures and improve maintainability across Python API, CLI, and OpenAPI documentation.

## Architecture

### Template Organization Structure

```
bengal/autodoc/templates/
├── base/                          # Shared foundation templates
│   ├── base.md.jinja2            # Common layout inheritance
│   ├── error_fallback.md.jinja2  # Error boundary fallbacks
│   └── metadata.md.jinja2        # Shared frontmatter generation
├── macros/                        # Reusable template components
│   ├── safe_macros.md.jinja2     # Error boundaries and safe rendering
│   ├── parameter_table.md.jinja2 # Unified parameter/argument tables
│   ├── code_blocks.md.jinja2     # Code formatting with syntax highlighting
│   └── navigation.md.jinja2      # Cross-references and internal links
├── python/                        # Python API documentation templates
│   ├── module.md.jinja2          # Main module template (simplified)
│   ├── class.md.jinja2           # Standalone class template
│   ├── function.md.jinja2        # Standalone function template
│   └── partials/                 # Decomposed module components
│       ├── module_description.md.jinja2
│       ├── module_classes.md.jinja2
│       ├── module_functions.md.jinja2
│       ├── class_methods.md.jinja2
│       ├── class_properties.md.jinja2
│       └── function_signature.md.jinja2
├── cli/                          # CLI documentation templates
│   ├── command_group.md.jinja2   # Main command group template
│   ├── command.md.jinja2         # Individual command template
│   └── partials/                 # CLI component templates
│       ├── command_description.md.jinja2
│       ├── command_options.md.jinja2
│       ├── command_arguments.md.jinja2
│       ├── command_examples.md.jinja2
│       └── subcommands_list.md.jinja2
└── openapi/                      # OpenAPI/REST documentation templates
    ├── api_overview.md.jinja2    # Main API documentation page
    ├── endpoint.md.jinja2        # Individual endpoint template
    ├── schema.md.jinja2          # Data schema template
    └── partials/                 # OpenAPI component templates
        ├── endpoint_description.md.jinja2
        ├── request_body.md.jinja2
        ├── response_schemas.md.jinja2
        ├── parameters_table.md.jinja2
        └── examples_section.md.jinja2
```

### Safe Template Rendering System

#### Error Boundary Implementation

```python
# bengal/autodoc/template_safety.py

class SafeTemplateRenderer:
    """Hugo-style safe template rendering with error boundaries."""

    def __init__(self, environment: Environment):
        self.env = environment
        self.error_count = 0
        self.logger = get_logger(__name__)

    def render_with_boundaries(self, template_name: str, context: dict) -> str:
        """Render template with error boundaries and fallbacks."""
        try:
            template = self.env.get_template(template_name)
            return template.render(context)
        except TemplateError as e:
            self.error_count += 1
            self.logger.error(f"Template {template_name} failed: {e}")
            return self._render_fallback(template_name, context, e)
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Unexpected error in {template_name}: {e}")
            return self._render_emergency_fallback(context)

    def _render_fallback(self, template_name: str, context: dict, error: Exception) -> str:
        """Generate structured fallback content when template fails."""
        element = context.get('element')
        if not element:
            return self._render_emergency_fallback(context)

        return f"""# {element.name}

```{{error}}
Template Error: {template_name} failed to render
Error: {str(error)}
```

## Basic Information

**Type:** {element.element_type}
**Source:** {element.source_file if hasattr(element, 'source_file') else 'Unknown'}

{element.description if hasattr(element, 'description') and element.description else '*No description available.*'}

*Note: Full documentation template failed. This is fallback content.*
"""

    def _render_emergency_fallback(self, context: dict) -> str:
        """Last resort fallback when everything fails."""
        return """# Documentation Error

```{error}
Critical template rendering failure. Please check template syntax and context data.
```

*This is emergency fallback content. Please report this issue.*
"""
```

#### Safe Macro System

```jinja2
{# macros/safe_macros.md.jinja2 #}

{#- Hugo-style error boundary macro -#}
{% macro safe_section(section_name) %}
{% if caller %}
<!-- BEGIN {{ section_name }} section -->
{% try %}
{{ caller() }}
{% except Exception as e %}
```{warning}
Section "{{ section_name }}" could not be rendered: {{ e }}
```
{% endtry %}
<!-- END {{ section_name }} section -->
{% endif %}
{% endmacro %}

{#- Safe rendering with item-level fallbacks -#}
{% macro safe_render(item_type, item) %}
{% if caller and item %}
{% try %}
{% with current_item = item %}
{{ caller() }}
{% endwith %}
{% except Exception as e %}
**`{{ item.name if item.name else 'Unknown' }}`** *({{ item_type }} documentation unavailable: {{ e }})*
{% endtry %}
{% endif %}
{% endmacro %}

{#- Safe variable access with defaults -#}
{% macro safe_var(obj, attr, default="-") %}
{% try %}
{{ obj[attr] if obj and attr in obj else default }}
{% except %}
{{ default }}
{% endtry %}
{% endmacro %}
```

### Template Decomposition Strategy

#### Python Module Template Breakdown

**Current State:** 361-line monolithic `module.md.jinja2`

**New Structure:**
```jinja2
{# python/module.md.jinja2 - Main orchestrator (30-40 lines) #}
{% extends "base/base.md.jinja2" %}

{% block content %}
{% call safe_section("description") %}
  {% include 'python/partials/module_description.md.jinja2' %}
{% endcall %}

{% call safe_section("aliases") %}
  {% include 'python/partials/module_aliases.md.jinja2' %}
{% endcall %}

{% call safe_section("classes") %}
  {% include 'python/partials/module_classes.md.jinja2' %}
{% endcall %}

{% call safe_section("functions") %}
  {% include 'python/partials/module_functions.md.jinja2' %}
{% endcall %}

{% call safe_section("constants") %}
  {% include 'python/partials/module_constants.md.jinja2' %}
{% endcall %}
{% endblock %}
```

**Component Templates (10-50 lines each):**
- `module_description.md.jinja2` - Module docstring and metadata
- `module_classes.md.jinja2` - Class listing with error boundaries
- `module_functions.md.jinja2` - Function listing with safe rendering
- `class_methods.md.jinja2` - Method documentation with parameter tables
- `function_signature.md.jinja2` - Function signatures with type safety

### Shared Component System

#### Unified Parameter Table

```jinja2
{# macros/parameter_table.md.jinja2 #}
{% macro parameter_table(parameters, title="Parameters", show_types=true, show_defaults=true) %}
{% if parameters %}
**{{ title }}:**

| Name | {% if show_types %}Type | {% endif %}{% if show_defaults %}Default | {% endif %}Description |
|------|{% if show_types %}------|{% endif %}{% if show_defaults %}---------|{% endif %}-------------|
{% for param in parameters %}
{% call safe_render("parameter", param) %}
| `{{ param.name }}` | {% if show_types %}{{ param.type | safe_type }}{% endif %} | {% if show_defaults %}{{ param.default | safe_default }}{% endif %} | {{ param.description | safe_text }} |
{% endcall %}
{% endfor %}

{% endif %}
{% endmacro %}

{#- Use safe filters for parameter rendering -#}
{#- These filters are now built into the safe template environment -#}
```

#### Code Block Formatting

```jinja2
{# macros/code_blocks.md.jinja2 #}
{% macro code_block(code, language="python", title=None) %}
{% if code %}
{% if title %}**{{ title }}:**{% endif %}

```{{ language }}
{{ code.strip() }}
```
{% endif %}
{% endmacro %}

{% macro signature_block(signature, element_type="function") %}
{% if signature %}
```python
{{ signature }}
```
{% else %}
```{warning}
{{ element_type | title }} signature unavailable
```
{% endif %}
{% endmacro %}
```

### Template Inheritance System

#### Base Template

```jinja2
{# base/base.md.jinja2 #}
---
title: "{% block title %}{{ element.name }}{% endblock %}"
type: "{% block doc_type %}doc{% endblock %}"
source_file: "{% block source_file %}{{ element.source_file | project_relative }}{% endblock %}"
description: "{% block description %}{{ element.description | safe_description }}{% endblock %}"
{% block extra_frontmatter %}{% endblock %}
---

{% block header %}
# {% block page_title %}{{ element.name }}{% endblock %}
{% endblock %}

{% block badges %}
{#- Override in child templates for type-specific badges -#}
{% endblock %}

{% block content %}
{#- Child templates implement this -#}
{% endblock %}

{% block see_also %}
{#- Cross-references and related links -#}
{% endblock %}

{% block footer %}
---
{% block footer_content %}
*Generated by Bengal autodoc from `{{ element.source_file | project_relative }}`*
{% endblock %}
{% endblock %}
```

### CLI Template System

#### Command Group Template

```jinja2
{# cli/command_group.md.jinja2 #}
{% extends "base/base.md.jinja2" %}

{% block doc_type %}autodoc/cli{% endblock %}

{% block badges %}
```{badge} Command Group
:class: badge-cli-group
```
{% endblock %}

{% block content %}
{% call safe_section("description") %}
  {% include 'cli/partials/command_description.md.jinja2' %}
{% endcall %}

{% call safe_section("usage") %}
  {% include 'cli/partials/command_usage.md.jinja2' %}
{% endcall %}

{% call safe_section("subcommands") %}
  {% include 'cli/partials/subcommands_list.md.jinja2' %}
{% endcall %}

{% call safe_section("global_options") %}
  {% include 'cli/partials/command_options.md.jinja2' %}
{% endcall %}
{% endblock %}
```

#### Command Options Component

```jinja2
{# cli/partials/command_options.md.jinja2 #}
{% set options = element.children | selectattr('element_type', 'equalto', 'option') | list %}
{% if options %}
## Options

{% for option in options %}
{% call safe_render("option", option) %}
### `{{ option.name }}`

{% if option.metadata.short_name %}
**Short form:** `-{{ option.metadata.short_name }}`
{% endif %}

{% if option.description %}
{{ option.description }}
{% else %}
*No description provided.*
{% endif %}

{% if option.metadata.type %}
**Type:** `{{ option.metadata.type }}`
{% endif %}

{% if option.metadata.default %}
**Default:** `{{ option.metadata.default }}`
{% endif %}

{% if option.metadata.required %}
```{note}
This option is required.
```
{% endif %}

{% endcall %}
{% endfor %}
{% endif %}
```

### OpenAPI Template System

#### Endpoint Template

```jinja2
{# openapi/endpoint.md.jinja2 #}
{% extends "base/base.md.jinja2" %}

{% block doc_type %}api-endpoint{% endblock %}

{% block badges %}
```{badge} {{ element.metadata.method | upper }}
:class: badge-http-{{ element.metadata.method | lower }}
```

{% if element.metadata.deprecated %}
```{badge} Deprecated
:class: badge-deprecated
```
{% endif %}
{% endblock %}

{% block content %}
{% call safe_section("description") %}
  {% include 'openapi/partials/endpoint_description.md.jinja2' %}
{% endcall %}

{% call safe_section("request") %}
  {% include 'openapi/partials/request_body.md.jinja2' %}
{% endcall %}

{% call safe_section("parameters") %}
  {% include 'openapi/partials/parameters_table.md.jinja2' %}
{% endcall %}

{% call safe_section("responses") %}
  {% include 'openapi/partials/response_schemas.md.jinja2' %}
{% endcall %}

{% call safe_section("examples") %}
  {% include 'openapi/partials/examples_section.md.jinja2' %}
{% endcall %}
{% endblock %}
```

## Error Handling Strategy

### Three-Tier Error Handling

1. **Template Level**: Entire template fails → Structured fallback page
2. **Section Level**: Template section fails → Error message + continue other sections  
3. **Component Level**: Individual item fails → Item-specific fallback + continue list

### Error Reporting

```python
# bengal/autodoc/error_reporter.py

class TemplateErrorReporter:
    """Collect and report template rendering errors."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def report_error(self, template_name: str, error: Exception, context: dict):
        """Record a template error with context."""
        self.errors.append({
            'template': template_name,
            'error': str(error),
            'error_type': type(error).__name__,
            'element_name': context.get('element', {}).get('name', 'Unknown'),
            'timestamp': datetime.now().isoformat()
        })

    def generate_report(self) -> str:
        """Generate human-readable error report."""
        if not self.errors and not self.warnings:
            return "✅ All templates rendered successfully"

        report = []
        if self.errors:
            report.append(f"❌ {len(self.errors)} template errors:")
            for error in self.errors:
                report.append(f"  - {error['template']}: {error['error']}")

        if self.warnings:
            report.append(f"⚠️ {len(self.warnings)} template warnings:")
            for warning in self.warnings:
                report.append(f"  - {warning['template']}: {warning['message']}")

        return "\n".join(report)
```

## Implementation Strategy

## Implementation Status

### ✅ Task 1: Safe Template Rendering Infrastructure (COMPLETED)

The foundation of the template safety system has been implemented in `bengal/autodoc/template_safety.py`:

#### SafeTemplateRenderer
- **Error boundary support**: Catches and handles TemplateNotFound, UndefinedError, TemplateError, and unexpected exceptions
- **Structured fallback content**: Generates meaningful fallback pages when templates fail
- **Error categorization**: Classifies errors by type (template_not_found, undefined_variable, template_syntax_error, unexpected_error)
- **Comprehensive logging**: Records detailed error information with context for debugging
- **Error reporting**: Provides human-readable error summaries and statistics

#### TemplateValidator
- **Syntax validation**: Checks template syntax before rendering
- **Structure analysis**: Validates balanced blocks and proper Jinja2 structure
- **Variable analysis**: Detects potentially undefined variables
- **Whitespace checking**: Identifies common formatting issues

#### Safe Template Environment
- **Safe filters**: Comprehensive set of filters for safe variable rendering:
  - `safe_description` - Format description text for YAML frontmatter with quote escaping
  - `code_or_dash` - Wrap values in code backticks or return "-" for empty values
  - `safe_anchor` - Generate safe anchor links by cleaning special characters
  - `project_relative` - Convert absolute paths to project-relative paths
  - `safe_type` - Format type annotations with cleanup of typing module prefixes
  - `safe_default` - Format default values with proper quoting
  - `safe_text` - Format text content with fallback for empty values
  - `truncate_text` - Truncate text to specified length with customizable suffix
  - `format_list` - Format lists with separators and truncation for long lists
- **Markdown-optimized**: Configured for Markdown generation with proper block handling
- **Error-safe configuration**: Environment settings that minimize rendering failures

#### Comprehensive Test Coverage
- **25 test cases** covering all error scenarios and safety features
- **Error boundary testing**: Validates fallback content generation for all error types
- **Filter testing**: Comprehensive tests for all 9 safe filters with edge cases
- **Integration testing**: Tests complete safe environment creation and configuration
- **Template validation**: Tests syntax checking and structure validation

### Direct Replacement

Since there are no external users, we can directly replace the existing template system:

```python
# bengal/autodoc/generator.py

class DocumentationGenerator:
    def __init__(self, extractor: Extractor, config: dict):
        self.config = config
        self.renderer = SafeTemplateRenderer(self._create_safe_environment())
        self.error_reporter = TemplateErrorReporter()

    def render_element(self, element: DocElement) -> str:
        """Render element using safe template system."""
        return self.renderer.render_with_boundaries(
            self._get_template_name(element),
            {'element': element, 'config': self.config}
        )
```

### Simplified Configuration

```yaml
# bengal.toml - Clean configuration without feature flags
[autodoc.template_safety]
error_boundaries = true    # Enable error boundary protection (default: true)
fallback_content = true    # Generate fallback content on errors (default: true)
validate_templates = true  # Validate templates before rendering (default: true)
debug_mode = false         # Show detailed error info in output (default: false)
```

## Testing Strategy

### Template Testing Framework

```python
# tests/unit/autodoc/test_template_safety.py

class TestTemplateSafety:
    """Test template safety and error handling."""

    def test_template_error_boundaries(self):
        """Test that template errors are contained and don't break entire pages."""
        # Create element with invalid data that will cause template error
        element = create_invalid_element()

        renderer = SafeTemplateRenderer(create_test_environment())
        result = renderer.render_with_boundaries('python/module.md.jinja2', {'element': element})

        # Should contain error message but still render page structure
        assert 'Template Error' in result
        assert element.name in result  # Basic info should still appear
        assert '# ' in result  # Should have header structure

    def test_all_templates_render_with_sample_data(self):
        """Test that all templates can render with sample data."""
        templates = discover_all_templates()

        for template_path in templates:
            sample_data = generate_sample_data_for_template(template_path)

            try:
                result = render_template(template_path, sample_data)
                assert len(result) > 0
                assert '{{' not in result  # No unrendered variables
                assert '{%' not in result  # No unrendered logic
            except Exception as e:
                pytest.fail(f"Template {template_path} failed with sample data: {e}")
```

## Performance Considerations

### Template Caching

```python
# bengal/autodoc/template_cache.py

class TemplateCache:
    """Cache compiled templates and rendered content."""

    def __init__(self, max_size: int = 1000):
        self.template_cache = {}
        self.content_cache = LRUCache(max_size)

    def get_template(self, template_name: str, environment: Environment):
        """Get cached compiled template."""
        if template_name not in self.template_cache:
            self.template_cache[template_name] = environment.get_template(template_name)
        return self.template_cache[template_name]

    def get_rendered_content(self, cache_key: str, render_func: callable):
        """Get cached rendered content or render and cache."""
        if cache_key in self.content_cache:
            return self.content_cache[cache_key]

        content = render_func()
        self.content_cache[cache_key] = content
        return content
```

### Memory Optimization

- **Lazy template loading**: Load templates only when needed
- **Content streaming**: Process large documentation sets in batches
- **Memory profiling**: Monitor memory usage during template rendering
- **Cache eviction**: Intelligent cache management for long-running processes

## Success Metrics

### Safety Metrics
- **Zero silent failures**: All template errors produce visible output
- **Error recovery rate**: 95%+ of template errors have useful fallbacks
- **Debug time reduction**: 50%+ faster to identify and fix template issues

### Maintainability Metrics  
- **Template size reduction**: Average template size < 50 lines (vs 361-line current)
- **Component reuse**: 80%+ of common patterns use shared macros
- **Edit confidence**: Developers can modify templates without fear of breaking system

### Performance Metrics
- **Build time parity**: No regression in documentation generation speed
- **Memory efficiency**: Optimized template loading and caching
- **Cache effectiveness**: High cache hit rates for repeated template rendering
