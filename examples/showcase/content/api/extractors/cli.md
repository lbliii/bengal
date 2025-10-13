
---
title: "extractors.cli"
type: python-module
source_file: "bengal/autodoc/extractors/cli.py"
css_class: api-content
description: "CLI documentation extractor for autodoc system.  Extracts documentation from command-line applications built with Click, argparse, or Typer."
---

# extractors.cli

CLI documentation extractor for autodoc system.

Extracts documentation from command-line applications built with Click, argparse, or Typer.

---

## Classes

### `CLIExtractor`

**Inherits from:** `Extractor`
Extract CLI documentation from Click/argparse/typer applications.

This extractor introspects CLI frameworks to build comprehensive documentation
for commands, options, arguments, and their relationships.

Currently supported frameworks:
- Click (full support)
- argparse (planned)
- Typer (planned)




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, framework: str = 'click', include_hidden: bool = False)
```

Initialize CLI extractor.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`framework`** (`str`) = `'click'` - CLI framework to extract from ('click', 'argparse', 'typer')
- **`include_hidden`** (`bool`) = `False` - Include hidden commands (default: False)





---
#### `extract`
```python
def extract(self, source: Any) -> list[DocElement]
```

Extract documentation from CLI application.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`source`** (`Any`) - CLI application object - For Click: click.Group or click.Command - For argparse: ArgumentParser instance - For Typer: Typer app instance

:::{rubric} Returns
:class: rubric-returns
:::
`list[DocElement]` - List of DocElements representing the CLI structure

:::{rubric} Raises
:class: rubric-raises
:::
- **`ValueError`**: If source type doesn't match framework



---
#### `get_template_dir`
```python
def get_template_dir(self) -> str
```

Get template directory name for CLI documentation.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`str` - 'cli'




---
#### `get_output_path`
```python
def get_output_path(self, element: DocElement) -> Path
```

Determine output path for CLI element.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`element`** (`DocElement`) - CLI DocElement

:::{rubric} Returns
:class: rubric-returns
:::
`Path` - Relative path for the generated markdown file




:::{rubric} Examples
:class: rubric-examples
:::
```python
command-group (main) → _index.md (section index)
```


---
