---
title: Autodoc
description: Automatic documentation generation
weight: 10
draft: false
lang: en
tags: [autodoc, api-docs, generation]
keywords: [autodoc, api-docs, python, cli, openapi]
category: guide
---

# Autodoc

Generate documentation automatically from source code.

## Overview

Bengal's autodoc system extracts documentation from:

- **Python** — Docstrings, type hints, module structure
- **CLI** — Command definitions, help text, arguments
- **OpenAPI** — API specifications

## Quick Start

```bash
# Generate Python API docs
bengal autodoc python --source ./mypackage --output content/api/

# Generate CLI docs
bengal autodoc cli --source ./mypackage --output content/cli/
```

## Python Autodoc

Extracts from Python modules:

- Module docstrings
- Class and method documentation
- Type hints and signatures
- Examples from docstrings

```toml
# bengal.toml
[autodoc.python]
source = "mypackage"
output = "content/api"
include_private = false
include_dunder = false
```

## CLI Autodoc

Extracts from Click/Typer commands:

- Command descriptions
- Argument documentation
- Option flags and defaults
- Subcommand hierarchy

## In This Section

- **[Python](/docs/extending/autodoc/python/)** — Python API documentation
- **[CLI](/docs/extending/autodoc/cli/)** — CLI reference documentation
- **[OpenAPI](/docs/extending/autodoc/openapi/)** — API specification docs


