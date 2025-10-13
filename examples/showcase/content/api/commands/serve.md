
---
title: "commands.serve"
type: python-module
source_file: "bengal/cli/commands/serve.py"
css_class: api-content
description: "Development server command."
---

# commands.serve

Development server command.

---


## Functions

### `serve`
```python
def serve(host: str, port: int, watch: bool, auto_port: bool, open_browser: bool, verbose: bool, debug: bool, config: str, source: str) -> None
```

🚀 Start development server with hot reload.

Watches for changes in content, assets, and templates,
automatically rebuilding the site when files are modified.



:::{rubric} Parameters
:class: rubric-parameters
:::
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `host` | `str` | - | - |
| `port` | `int` | - | - |
| `watch` | `bool` | - | - |
| `auto_port` | `bool` | - | - |
| `open_browser` | `bool` | - | - |
| `verbose` | `bool` | - | - |
| `debug` | `bool` | - | - |
| `config` | `str` | - | - |
| `source` | `str` | - | - |

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
