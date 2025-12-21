---
title: Autodoc System
nav_title: Autodoc
description: AST-based Python documentation generator
weight: 10
category: subsystems
tags:
- subsystems
- autodoc
- documentation
- ast
- python
- code-generation
- cli
keywords:
- autodoc
- documentation generation
- AST
- Python
- code generation
- CLI docs
---

# Autodoc System

Bengal includes an **automatic documentation generation system** that extracts API documentation from Python source code using AST-based static analysis.

:::{note}
**Zero-Import Extraction**: Unlike Sphinx, Bengal's autodoc **does not import your code**. This means it never crashes due to missing dependencies or side effects.
:::

## Architecture

The system follows a clean Extractor → Generator → Template pipeline:

```mermaid
flowchart LR
    Input[Python Source] --> Parser[AST Parser]
    Parser --> Extractor[PythonExtractor]
    Extractor --> Model[DocElement Model]

    Model --> Generator[Doc Generator]
    Generator --> Templates[Jinja2 Templates]
    Templates --> Output[Markdown Files]

    Output --> Build[Bengal Build]
    Build --> HTML[Final HTML]
```

## Components

::::{tab-set}
:::{tab-item} Extractors
**Source Analysis** (`extractors/`)

Parses source code into `DocElement` objects.

- **Python** (`extractors/python/`): Package with modular components:
  - `extractor.py`: Main `PythonExtractor` class using AST for classes, functions, and type hints
  - `signature.py`: Function signature and argument extraction
  - `module_info.py`: Module name inference and path resolution
  - `inheritance.py`: Inherited member synthesis
  - `skip_logic.py`: Exclusion pattern matching
  - `aliases.py`: Module alias detection
- **CLI** (`extractors/cli.py`): Extracts commands and options from Click apps.
- **OpenAPI** (`extractors/openapi.py`): Extracts endpoints from OpenAPI specs.
:::

:::{tab-item} Model
**Unified Data Model** (`base.py`)

`DocElement` is the universal representation of any documented item.

- **Structure**: Name, description, metadata, children
- **Language Agnostic**: Used for Python, CLI, and HTTP APIs
- **Serializable**: Can be cached to disk
:::

:::{tab-item} Orchestration
**Virtual Page Generation** (`orchestration/`)

Generates API documentation as virtual Page objects.

- **VirtualAutodocOrchestrator**: Main coordinator for autodoc generation
- **Page Builders**: Creates virtual pages from DocElements
- **Template Integration**: Renders directly via theme templates
- **No Intermediate Files**: Docs generate as virtual pages, not markdown files
:::
::::


## Template Safety

Autodoc templates are designed to never fail the build, even with malformed docstrings.

::::{cards}
:columns: 2
:gap: medium
:variant: explanation

:::{card} Error Boundaries
:icon: check-circle
If a template section fails, only that section shows an error. The rest of the page renders normally.
:::

:::{card} Safe Filters
:icon: funnel
Custom filters like `safe_description` handles escaping and fallback for missing data.
:::
::::

## Configuration

Configure autodoc in `bengal.toml`:

```toml
[autodoc.python]
enabled = true
source_dirs = ["src/mylib"]
output_dir = "content/api"
docstring_style = "google"  # google, numpy, sphinx
```

## CLI Support

We currently support **Click** applications via configuration.

```toml
# bengal.toml
[autodoc.cli]
enabled = true
app = "myapp.cli:main"
output_dir = "content/autodoc/cli"
```

This generates command references including arguments, options, and hierarchy.
