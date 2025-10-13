
---
title: "commands.autodoc"
type: python-module
source_file: "bengal/cli/commands/autodoc.py"
css_class: api-content
description: "Autodoc commands for generating API and CLI documentation."
---

# commands.autodoc

Autodoc commands for generating API and CLI documentation.

---


## Functions

### `autodoc`
```python
def autodoc(source: tuple, output: str, clean: bool, parallel: bool, verbose: bool, stats: bool, config: str, python_only: bool, cli_only: bool) -> None
```

📚 Generate comprehensive API documentation (Python + CLI).

Automatically generates both Python API docs and CLI docs based on
your bengal.toml configuration. Use --python-only or --cli-only to
generate specific types.



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `source` | `tuple` | - | - |
| `output` | `str` | - | - |
| `clean` | `bool` | - | - |
| `parallel` | `bool` | - | - |
| `verbose` | `bool` | - | - |
| `stats` | `bool` | - | - |
| `config` | `str` | - | - |
| `python_only` | `bool` | - | - |
| `cli_only` | `bool` | - | - |

:::{rubric} Returns
:class: rubric-returns
:::
`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
bengal autodoc                    # Generate all configured docs
```


---
### `autodoc_cli`
```python
def autodoc_cli(app: str, framework: str, output: str, include_hidden: bool, clean: bool, verbose: bool, config: str) -> None
```

⌨️  Generate CLI documentation from Click/argparse/typer apps.

Extracts documentation from command-line interfaces to create
comprehensive command reference documentation.



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `app` | `str` | - | - |
| `framework` | `str` | - | - |
| `output` | `str` | - | - |
| `include_hidden` | `bool` | - | - |
| `clean` | `bool` | - | - |
| `verbose` | `bool` | - | - |
| `config` | `str` | - | - |

:::{rubric} Returns
:class: rubric-returns
:::
`None`




:::{rubric} Examples
:class: rubric-examples
:::
```python
bengal autodoc-cli --app bengal.cli:main --output content/cli
```


---
