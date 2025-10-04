# Autodoc: CLI Design & Template System

**Date**: October 4, 2025  
**Status**: Design Refinement  
**Purpose**: Define developer ergonomics and template architecture

---

## CLI Design Philosophy

**Goal**: Intuitive, discoverable, powerful, follows Bengal conventions.

### Core Command Structure

```bash
# Main autodoc command (generates all enabled types)
bengal autodoc

# Type-specific generation
bengal autodoc python
bengal autodoc api        # OpenAPI
bengal autodoc cli

# Short aliases
bengal gen python
bengal gen api
bengal gen cli
bengal gen all            # Same as 'bengal autodoc'
```

---

## Complete CLI Reference

### Basic Usage

```bash
# Generate all documentation (based on config)
$ bengal autodoc

📚 Generating Documentation...
   🐍 Python API (src/bengal) → content/api/
      ✓ Extracted 23 modules, 127 classes, 456 functions
      ✓ Generated 150 pages in 1.2s
   
   ⌨️  CLI (bengal.cli) → content/cli/
      ✓ Extracted 12 commands, 47 options
      ✓ Generated 12 pages in 0.3s

✅ Generated 162 documentation pages in 1.5s


# Generate specific type
$ bengal autodoc python
$ bengal autodoc api
$ bengal autodoc cli

# Short form
$ bengal gen python
$ bengal gen api
$ bengal gen cli
```

---

### Advanced Usage

```bash
# Specify source and output
$ bengal autodoc python \
    --source src/mylib \
    --output content/sdk

# Multiple sources
$ bengal autodoc python \
    --source src/core \
    --source src/plugins \
    --output content/api

# Watch mode (auto-regenerate on changes)
$ bengal autodoc python --watch

👀 Watching src/bengal for changes...
   📝 bengal/core/site.py changed
   ✓ Regenerated api/bengal/core/site.md

# Clean output directory first
$ bengal autodoc python --clean

# Validate without generating
$ bengal autodoc python --validate

🔍 Validating Python API...
   ✓ All 456 functions have docstrings (100%)
   ✓ All 127 classes documented
   ⚠ 12 functions missing type hints
   ✗ 3 broken cross-references:
      - [[UnknownClass]] in site.py:42
      - [[missing_func]] in page.py:18

# Show coverage stats
$ bengal autodoc python --coverage

📊 API Documentation Coverage:
   Modules:     23/23   (100%) ✓
   Classes:     127/127 (100%) ✓
   Functions:   456/456 (100%) ✓
   Type Hints:  444/456 (97%)  ⚠
   Docstrings:  456/456 (100%) ✓
   Examples:    89/456  (19%)  ⚠
   
   Overall: 98% documented

# Dry run (show what would be generated)
$ bengal autodoc python --dry-run

Would generate:
   content/api/bengal/core/site.md
   content/api/bengal/core/page.md
   content/api/bengal/core/section.md
   ... (150 files total)

# Output format options
$ bengal autodoc python --format markdown   # Default
$ bengal autodoc python --format json       # JSON schema
$ bengal autodoc python --format rst        # reStructuredText (for migration)

# Template debugging
$ bengal autodoc python --show-template class

Showing template: templates/autodoc/python/class.md
Source: /Users/you/project/templates/autodoc/python/class.md
Fallback: bengal/autodoc/templates/python/class.md

Template variables available:
  - element (ClassDoc)
  - config (dict)
  - site (Site)
  - xref (CrossReferenceResolver)
```

---

### OpenAPI-Specific Options

```bash
# From OpenAPI spec file
$ bengal autodoc api --spec openapi.yaml

# From FastAPI app
$ bengal autodoc api --app myapp.main:app

# From Flask app with flask-restx
$ bengal autodoc api --app myapp:app --framework flask-restx

# Multiple specs (microservices)
$ bengal autodoc api \
    --spec services/users/openapi.yaml \
    --spec services/orders/openapi.yaml \
    --output content/api
```

---

### CLI-Specific Options

```bash
# From Click app
$ bengal autodoc cli --app bengal.cli:main

# From argparse
$ bengal autodoc cli --parser myscript:create_parser

# From Typer
$ bengal autodoc cli --app myapp.cli:app --framework typer

# Generate man pages too
$ bengal autodoc cli --man-pages
```

---

### Integration Commands

```bash
# Generate and build in one command
$ bengal autodoc && bengal build

# Or use the combined flag
$ bengal build --with-autodoc

# Build with versioning + autodoc
$ bengal build --versioned --with-autodoc

# Watch mode for development
$ bengal serve --with-autodoc
```

---

### Configuration Commands

```bash
# Initialize autodoc configuration
$ bengal autodoc init

What would you like to document?
  [x] Python API
  [ ] OpenAPI endpoints
  [ ] CLI commands

Python source directory: src/bengal
Output directory: content/api
Docstring style: google

Created bengal.toml with autodoc configuration!
Run: bengal autodoc


# Show current configuration
$ bengal autodoc config

Autodoc Configuration:
  Python:
    enabled: true
    sources: ['src/bengal']
    output: content/api
    style: google
  
  OpenAPI:
    enabled: false
  
  CLI:
    enabled: false


# Update configuration interactively
$ bengal autodoc config --edit
```

---

## Template System Architecture

### Two-Layer Template System

You're right to ask about this! There are actually **two template layers**:

```
Layer 1: Markdown Generation Templates (.md.jinja2)
    ↓
Generate .md files in content/api/
    ↓
Layer 2: HTML Rendering Templates (.html)
    ↓
Final HTML output
```

---

### Layer 1: Markdown Generation Templates (.md.jinja2)

**Purpose**: Generate the markdown content for API docs

**Location**: `templates/autodoc/python/class.md.jinja2`

**Example**:
```jinja2
{# templates/autodoc/python/class.md.jinja2 #}
---
title: "{{ element.name }}"
layout: api-reference
type: python-class
source_file: "{{ element.source_file }}"
---

# {{ element.name }}

{{ element.description }}

{% if element.metadata.bases %}
**Inherits from:** {% for base in element.metadata.bases %}`{{ base }}`{% if not loop.last %}, {% endif %}{% endfor %}
{% endif %}

## Attributes

{% for attr in element.children | selectattr('element_type', 'equalto', 'attribute') %}
### {{ attr.name }}

{% if attr.metadata.annotation %}**Type:** `{{ attr.metadata.annotation }}`{% endif %}

{{ attr.description }}
{% endfor %}

## Methods

{% for method in element.children | selectattr('element_type', 'equalto', 'function') %}
### {{ method.name }}

```python
{{ method.metadata.signature }}
```

{{ method.description }}

{% if method.examples %}
**Examples:**

{% for example in method.examples %}
{{ example }}
{% endfor %}
{% endif %}
{% endfor %}
```

**Output**: `content/api/bengal/core/site.md` (markdown file)

---

### Layer 2: HTML Rendering Templates (.html)

**Purpose**: Render the generated markdown to final HTML

**Location**: `templates/api-reference.html` or `templates/layouts/api-reference.html`

**This uses Bengal's existing template system!**

```html
{# templates/layouts/api-reference.html #}
<!DOCTYPE html>
<html>
<head>
    <title>{{ page.title }} - {{ site.config.site.title }}</title>
    <link rel="stylesheet" href="{{ url_for('assets/css/api-docs.css') }}">
</head>
<body>
    <div class="api-layout">
        {# Left sidebar: API navigation #}
        <aside class="api-sidebar">
            <div class="api-nav">
                <h3>API Reference</h3>
                {% include "partials/api-nav.html" %}
            </div>
        </aside>
        
        {# Main content #}
        <main class="api-content">
            {# Breadcrumbs #}
            <nav class="breadcrumbs">
                <a href="/api/">API</a>
                {% for ancestor in page.ancestors %}
                / <a href="{{ url_for(ancestor) }}">{{ ancestor.title }}</a>
                {% endfor %}
            </nav>
            
            {# The markdown content (rendered by Bengal) #}
            <article class="api-doc">
                {{ content }}
            </article>
            
            {# Right sidebar: Table of contents #}
            <aside class="toc">
                <h4>On This Page</h4>
                {{ page.toc }}
            </aside>
        </main>
    </div>
    
    {# Syntax highlighting #}
    <script src="{{ url_for('assets/js/highlight.js') }}"></script>
    
    {# API-specific features #}
    <script>
        // Copy code blocks
        // Expand/collapse sections
        // Search within page
    </script>
</body>
</html>
```

---

### Complete Template Hierarchy

```
User's Project:
templates/
├── autodoc/                          # Layer 1: Markdown generation
│   ├── python/
│   │   ├── module.md.jinja2         # Generate module markdown
│   │   ├── class.md.jinja2          # Generate class markdown
│   │   └── function.md.jinja2       # Generate function markdown
│   ├── api/
│   │   ├── endpoint.md.jinja2       # Generate API endpoint markdown
│   │   └── schema.md.jinja2         # Generate schema markdown
│   └── cli/
│       └── command.md.jinja2        # Generate CLI command markdown
│
├── layouts/                          # Layer 2: HTML rendering
│   ├── api-reference.html           # Layout for API docs
│   ├── api-endpoint.html            # Layout for API endpoints
│   └── cli-reference.html           # Layout for CLI docs
│
├── partials/
│   ├── api-nav.html                 # API navigation sidebar
│   ├── method-signature.html        # Reusable method display
│   └── parameter-list.html          # Reusable parameter table
│
└── page.html                        # Default page layout
```

---

### File Extension Convention

```
.md.jinja2    → Markdown generation template (Layer 1)
.html         → HTML rendering template (Layer 2)
.jinja2.html  → Alternative if you prefer
```

We'll support all three for flexibility.

---

### Customization Examples

#### Example 1: Minimal API Reference

**Markdown template** (`templates/autodoc/python/class.md.jinja2`):
```jinja2
---
title: "{{ element.name }}"
layout: minimal-api
---

# {{ element.name }}

{{ element.description }}

{% for method in element.children %}
## {{ method.name }}
`{{ method.metadata.signature }}`

{{ method.description }}
{% endfor %}
```

**HTML template** (`templates/layouts/minimal-api.html`):
```html
<!DOCTYPE html>
<html>
<head>
    <title>{{ page.title }}</title>
    <style>
        body { font-family: system-ui; max-width: 800px; margin: 0 auto; padding: 2rem; }
        code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }
    </style>
</head>
<body>
    {{ content }}
</body>
</html>
```

---

#### Example 2: SDK Documentation Style

**Markdown template** (`templates/autodoc/python/class.md.jinja2`):
```jinja2
---
title: "{{ element.name }}"
layout: sdk-reference
category: "{{ element.qualified_name.split('.')[1] }}"
---

::: class-header
# {{ element.name }}
{{ element.description | truncate(200) }}
:::

::: quick-example
## Quick Start

```python
from {{ element.qualified_name.rsplit('.', 1)[0] }} import {{ element.name }}

# Create instance
obj = {{ element.name }}()

# Use it
obj.main_method()
```
:::

## Constructor

{% for method in element.children if method.name == '__init__' %}
```python
{{ method.metadata.signature }}
```

{{ method.description }}
{% endfor %}

## Methods

<div class="method-grid">
{% for method in element.children if not method.name.startswith('_') %}
::: method-card
### {{ method.name }}
{{ method.description | truncate(100) }}
[Learn more →](#{{ method.name }})
:::
{% endfor %}
</div>

## Detailed Reference

{% for method in element.children if not method.name.startswith('_') %}
---

### {{ method.name }} {#{{ method.name }}}

```python
{{ method.metadata.signature }}
```

{{ method.description }}

{% if method.metadata.args %}
**Parameters:**

| Name | Type | Description |
|------|------|-------------|
{% for arg_name, arg_desc in method.metadata.args.items() %}
| `{{ arg_name }}` | `{{ method.get_arg_type(arg_name) }}` | {{ arg_desc }} |
{% endfor %}
{% endif %}

{% if method.metadata.returns %}
**Returns:** {{ method.metadata.returns }}
{% endif %}

{% if method.examples %}
**Example:**
{% for example in method.examples %}
{{ example }}
{% endfor %}
{% endif %}
{% endfor %}
```

**HTML template** (`templates/layouts/sdk-reference.html`):
```html
<!DOCTYPE html>
<html>
<head>
    <title>{{ page.title }} - SDK Documentation</title>
    <link rel="stylesheet" href="{{ url_for('assets/css/sdk.css') }}">
</head>
<body>
    <div class="sdk-layout">
        <aside class="sdk-sidebar">
            {# Category-based navigation #}
            <nav class="sdk-nav">
                <h3>{{ page.metadata.category | title }}</h3>
                {% include "partials/sdk-nav.html" %}
            </nav>
        </aside>
        
        <main class="sdk-content">
            {# Hero section for class #}
            <div class="class-hero">
                <span class="category-badge">{{ page.metadata.category }}</span>
                <h1>{{ page.title }}</h1>
                <p class="class-description">{{ page.description }}</p>
                
                {# Quick links #}
                <div class="quick-links">
                    <a href="{{ page.metadata.source_file }}">View Source</a>
                    <a href="#examples">Examples</a>
                    <a href="#methods">Methods</a>
                </div>
            </div>
            
            {# Rendered markdown content #}
            <article class="sdk-article">
                {{ content }}
            </article>
        </main>
        
        {# TOC sidebar #}
        <aside class="toc-sidebar">
            <div class="toc-sticky">
                <h4>On This Page</h4>
                {{ page.toc }}
            </div>
        </aside>
    </div>
    
    <script src="{{ url_for('assets/js/sdk.js') }}"></script>
</body>
</html>
```

---

#### Example 3: ReadTheDocs Style

**Markdown template** (`templates/autodoc/python/module.md.jinja2`):
```jinja2
---
title: "{{ element.name }}"
layout: rtd-reference
---

::: module-header
{{ element.name }}
{{ '=' * element.name | length }}
:::

{{ element.description }}

{% if element.children | selectattr('element_type', 'equalto', 'class') | list %}
## Classes

{% for cls in element.children | selectattr('element_type', 'equalto', 'class') %}
### class {{ cls.name }}

```python
class {{ cls.name }}{% if cls.metadata.bases %}({{ cls.metadata.bases | join(', ') }}){% endif %}
```

{{ cls.description }}

{% for method in cls.children | selectattr('element_type', 'equalto', 'function') | list[:3] %}
#### {{ method.name }}()

{{ method.description | truncate(100) }}
{% endfor %}

[Full {{ cls.name }} reference →]({{ cls.qualified_name.replace('.', '/') }})

{% endfor %}
{% endif %}
```

---

### Configuration for Templates

```toml
# bengal.toml

[autodoc.templates]
# Markdown generation templates (Layer 1)
markdown_dir = "templates/autodoc"

# HTML rendering templates (Layer 2)
layout_dir = "templates/layouts"

# Default layouts per type
[autodoc.templates.layouts]
python = "api-reference.html"      # or "sdk-reference.html", "minimal-api.html"
openapi = "api-endpoint.html"
cli = "cli-reference.html"

# Custom template context
[autodoc.templates.context]
# Add custom variables to all templates
company_name = "Acme Corp"
api_version = "2.0"
support_email = "support@example.com"
```

---

### Template Context API

Both layers receive rich context:

**Layer 1 (Markdown generation)**:
```python
{
    'element': DocElement,        # The documented element
    'config': dict,               # Site config
    'autodoc_config': dict,       # Autodoc config
    'site': Site,                 # Full site object
    'xref': CrossRefResolver,     # Cross-reference resolver
    
    # Custom context from config
    'company_name': 'Acme Corp',
    'api_version': '2.0'
}
```

**Layer 2 (HTML rendering)** - existing Bengal template context:
```python
{
    'page': Page,                 # Current page
    'content': str,               # Rendered markdown content
    'site': Site,                 # Site object
    'config': dict,               # Site config
    
    # All existing Bengal template functions
    'url_for': ...,
    'truncate': ...,
    # ... 75+ template functions
}
```

---

### Custom Template Functions

Register custom functions for markdown generation:

```python
# In a build hook or plugin
from bengal.autodoc.templates import TemplateRegistry

@TemplateRegistry.register_filter('format_signature')
def format_signature(signature: str) -> str:
    """Custom signature formatting."""
    # Add syntax highlighting, break long lines, etc.
    return formatted

@TemplateRegistry.register_function('related_classes')
def related_classes(element: DocElement) -> List[DocElement]:
    """Find related classes based on usage."""
    # Your custom logic
    return related
```

Use in templates:
```jinja2
{{ method.metadata.signature | format_signature }}

## Related Classes
{% for cls in related_classes(element) %}
- [[{{ cls.qualified_name }}]]
{% endfor %}
```

---

## Developer Workflow Examples

### Example 1: Python Library Author

```bash
# Initial setup
$ bengal new site --preset api-docs
$ cd myproject
$ bengal autodoc init

# Configure autodoc (or edit bengal.toml)
Python source: src/mylib
Output: content/api
Docstring style: google

# Generate API docs
$ bengal autodoc python

# Customize templates (optional)
$ mkdir -p templates/autodoc/python
$ cp $(bengal info template-path)/autodoc/python/class.md.jinja2 \
     templates/autodoc/python/class.md.jinja2
$ vim templates/autodoc/python/class.md.jinja2

# Regenerate with custom templates
$ bengal autodoc python

# Serve with live reload
$ bengal serve --with-autodoc

# Deploy
$ bengal build --with-autodoc
$ netlify deploy --dir=public
```

---

### Example 2: FastAPI Developer

```bash
# Setup
$ bengal autodoc init

What would you like to document?
  [x] Python API (SDK)
  [x] OpenAPI endpoints
  [ ] CLI commands

# Configure
Python source: myapp/models/
OpenAPI: FastAPI app at myapp.main:app

# Generate everything
$ bengal autodoc

📚 Generating Documentation...
   🐍 Python API (myapp/models/) → content/sdk/
      ✓ Generated 23 model classes
   
   🌐 OpenAPI (myapp.main:app) → content/api/
      ✓ Generated 45 endpoints
      ✓ Generated 23 schemas

# Cross-references work!
# In endpoint docs: "Returns [[User]] model"
# In model docs: "Used by [[GET /users]] endpoint"

$ bengal build
```

---

### Example 3: CLI Tool Maintainer

```bash
# Self-document Bengal's CLI!
$ bengal autodoc cli --app bengal.cli:main --output content/cli

⌨️  CLI Documentation (bengal.cli) → content/cli/
   ✓ Extracted 12 commands
   ✓ Extracted 47 options
   ✓ Generated 12 pages

# Generated pages:
content/cli/
├── index.md              # CLI overview
├── build.md              # bengal build
├── serve.md              # bengal serve
├── autodoc.md            # bengal autodoc
└── ...

# Each includes:
# - Usage examples
# - All options/flags
# - Related commands
```

---

## IDE Integration (Future)

```bash
# Generate IDE stubs for autocomplete
$ bengal autodoc python --generate-stubs

Generated .pyi stub files in typings/

# Generate JSON schema for tools
$ bengal autodoc python --format json-schema
```

---

## Summary

### CLI Design
```bash
# Simple and intuitive
bengal autodoc                # Generate all
bengal autodoc python         # Generate Python docs
bengal autodoc api            # Generate OpenAPI docs
bengal autodoc cli            # Generate CLI docs

# Short form
bengal gen {python,api,cli}

# Powerful options
--watch                       # Auto-regenerate
--coverage                    # Show coverage stats
--validate                    # Validate without generating
--clean                       # Clean before generating
```

### Template System

**Two layers**:

1. **Markdown generation** (`.md.jinja2`)
   - Generates API docs as markdown
   - Location: `templates/autodoc/python/class.md.jinja2`
   - Output: `content/api/bengal/core/site.md`

2. **HTML rendering** (`.html`)
   - Renders markdown to HTML
   - Location: `templates/layouts/api-reference.html`
   - Output: `public/api/bengal/core/site/index.html`

**Both are fully customizable!**

---

This gives you maximum flexibility:
- Customize markdown generation (content structure)
- Customize HTML rendering (presentation)
- Or use beautiful defaults for both

---

*Ready to implement? This is the complete CLI and template design.*

