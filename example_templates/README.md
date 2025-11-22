# Example Templates

This directory contains example templates and utilities for Bengal static site generator.

## Directory Structure

```
example_templates/
├── filters/           # Custom Jinja2 filters
├── macros/           # Reusable template macros  
├── partials/         # Template partials/includes
└── module_main.md.jinja2  # Main module template example
```

## Custom Filters (`filters/`)

### Safe Filters (`safe_filters.py`)

Custom Jinja2 filters for safer template rendering, particularly useful for autodoc templates:

- **`safe_description`** - Safely formats description text for YAML frontmatter by removing problematic characters, truncating to 200 chars, and escaping quotes
- **`code_or_dash`** - Wraps values in code backticks unless they're empty or dash
- **`safe_anchor`** - Generates safe anchor links by converting to lowercase and replacing spaces/dots with dashes

#### Usage Example

```python
# In your template engine setup
from example_templates.filters.safe_filters import SAFE_FILTERS

# Register filters with Jinja2 environment
for name, filter_func in SAFE_FILTERS.items():
    jinja_env.filters[name] = filter_func
```

```jinja2
{# In your templates #}
description: "{{ element.description | safe_description }}"
type: {{ element.type | code_or_dash }}
anchor: {{ element.name | safe_anchor }}
```

## Template Examples

These examples demonstrate best practices for:

- Safe handling of dynamic content in YAML frontmatter
- Consistent formatting across documentation templates
- Reusable template components and macros
- Custom filter implementation patterns

## Integration with Bengal

These examples can be used as starting points for:

- Custom autodoc templates
- Theme development
- Template function extensions
- Safe content processing patterns

For more information about Bengal's template system, see the [rendering architecture documentation](../architecture/rendering.md).
