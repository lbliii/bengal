
---
title: "assets.pipeline"
type: python-module
source_file: "bengal/assets/pipeline.py"
css_class: api-content
description: "Optional Node-based asset pipeline integration for Bengal SSG.  Provides SCSS → CSS, PostCSS transforms, and JS/TS bundling via esbuild.  Behavior: - Only runs when enabled via config (`[assets].pi..."
---

# assets.pipeline

Optional Node-based asset pipeline integration for Bengal SSG.

Provides SCSS → CSS, PostCSS transforms, and JS/TS bundling via esbuild.

Behavior:
- Only runs when enabled via config (`[assets].pipeline = true`).
- Detects required CLIs on PATH and produces clear, actionable errors.
- Compiles into a temporary pipeline output directory for subsequent
  Bengal fingerprinting and copying.

This module does not change the public API of asset processing; it returns
compiled output files to be treated as regular assets by AssetOrchestrator.

---

## Classes

### `PipelineConfig`


*No class description provided.*

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 9 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `root_path`
  - `Path`
  - -
* - `theme_name`
  - `str | None`
  - -
* - `enabled`
  - `bool`
  - -
* - `scss`
  - `bool`
  - -
* - `postcss`
  - `bool`
  - -
* - `postcss_config`
  - `str | None`
  - -
* - `bundle_js`
  - `bool`
  - -
* - `esbuild_target`
  - `str`
  - -
* - `sourcemaps`
  - `bool`
  - -
:::

::::



### `NodePipeline`


Thin wrapper over Node CLIs (sass, postcss, esbuild).




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, config: PipelineConfig) -> None
```

*No description provided.*



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `config`
  - `PipelineConfig`
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `build`
```python
def build(self) -> list[Path]
```

Run the pipeline and return a list of compiled output files.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`list[Path]`




---


## Functions

### `from_site`
```python
def from_site(site: Site) -> NodePipeline
```

Factory to create pipeline from site config.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `site`
  - `Site`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`NodePipeline`




---
