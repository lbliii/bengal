
---
title: "orchestration.full_to_incremental"
type: python-module
source_file: "bengal/orchestration/full_to_incremental.py"
css_class: api-content
description: "Bridge helpers for transitioning from full builds to incremental runs.  ⚠️  TEST UTILITIES ONLY ======================== These utilities are primarily used in tests to simulate incremental passes w..."
---

# orchestration.full_to_incremental

Bridge helpers for transitioning from full builds to incremental runs.

⚠️  TEST UTILITIES ONLY
========================
These utilities are primarily used in tests to simulate incremental passes
without invoking the full BuildOrchestrator.

**Not for production use:**
- Writes placeholder output for test verification
- Skips full rendering pipeline
- Use BuildOrchestrator.run() for production incremental builds

**Primary consumers:**
- tests/integration/test_full_to_incremental_sequence.py
- Test scenarios validating incremental build flows

---


## Functions

### `run_incremental_bridge`
```python
def run_incremental_bridge(site, change_type: str, changed_paths: Iterable[str | Path]) -> None
```

Run a minimal incremental pass for the given site.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 3 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `site`
  - -
  - -
  - Site instance
* - `change_type`
  - `str`
  - -
  - One of "content", "template", or "config"
* - `changed_paths`
  - `Iterable[str | Path]`
  - -
  - Paths that changed (ignored for config)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
