
---
title: "commands.perf"
type: python-module
source_file: "bengal/cli/commands/perf.py"
css_class: api-content
description: "Performance metrics and analysis commands."
---

# commands.perf

Performance metrics and analysis commands.

---


## Functions

### `perf`
```python
def perf(last, format, compare)
```

Show performance metrics and trends.

Displays build performance metrics collected from previous builds.
Metrics are automatically saved to .bengal-metrics/ directory.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`last`**
- **`format`**
- **`compare`**





:::{rubric} Examples
:class: rubric-examples
:::
```python
bengal perf              # Show last 10 builds as table
```


---
