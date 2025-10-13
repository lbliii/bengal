
---
title: "commands.build"
type: python-module
source_file: "bengal/cli/commands/build.py"
css_class: api-content
description: "Build command for generating the static site."
---

# commands.build

Build command for generating the static site.

---


## Functions

### `build`
```python
def build(parallel: bool, incremental: bool, memory_optimized: bool, profile: str, perf_profile: str, use_theme_dev: bool, use_dev: bool, verbose: bool, strict: bool, debug: bool, validate: bool, assets_pipeline: bool, autodoc: bool, config: str, quiet: bool, full_output: bool, log_file: str, source: str) -> None
```

🔨 Build the static site.

Generates HTML files from your content, applies templates,
processes assets, and outputs a production-ready site.



:::{rubric} Parameters
:class: rubric-parameters
:::
````{dropdown} 18 parameters (click to expand)
:open: false

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `parallel` | `bool` | - | - |
| `incremental` | `bool` | - | - |
| `memory_optimized` | `bool` | - | - |
| `profile` | `str` | - | - |
| `perf_profile` | `str` | - | - |
| `use_theme_dev` | `bool` | - | - |
| `use_dev` | `bool` | - | - |
| `verbose` | `bool` | - | - |
| `strict` | `bool` | - | - |
| `debug` | `bool` | - | - |
| `validate` | `bool` | - | - |
| `assets_pipeline` | `bool` | - | - |
| `autodoc` | `bool` | - | - |
| `config` | `str` | - | - |
| `quiet` | `bool` | - | - |
| `full_output` | `bool` | - | - |
| `log_file` | `str` | - | - |
| `source` | `str` | - | - |

````

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
