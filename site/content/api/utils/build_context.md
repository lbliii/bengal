
---
title: "utils.build_context"
type: python-module
source_file: "bengal/utils/build_context.py"
css_class: api-content
description: "Python module documentation"
---

# utils.build_context

*No module description provided.*

---

## Classes

### `BuildContext`


Shared build context passed across orchestrators.

Introduced to reduce implicit global state usage and make dependencies explicit.
Fields are optional to maintain backward compatibility while we thread this through.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::

::::{dropdown} 8 attributes (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 25 25 50

* - Name
  - Type
  - Description
* - `site`
  - `Site | None`
  - -
* - `pages`
  - `list[Page] | None`
  - -
* - `assets`
  - `list[Asset] | None`
  - -
* - `tracker`
  - `DependencyTracker | None`
  - -
* - `stats`
  - `BuildStats | None`
  - -
* - `profile`
  - `BuildProfile | None`
  - -
* - `progress_manager`
  - `LiveProgressManager | None`
  - -
* - `reporter`
  - `ProgressReporter | None`
  - -
:::

::::




