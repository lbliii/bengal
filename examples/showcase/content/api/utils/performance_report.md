
---
title: "utils.performance_report"
type: python-module
source_file: "bengal/utils/performance_report.py"
css_class: api-content
description: "Performance metrics reporting and analysis.  Reads collected metrics from .bengal-metrics/ and provides analysis, visualization, and trend detection."
---

# utils.performance_report

Performance metrics reporting and analysis.

Reads collected metrics from .bengal-metrics/ and provides analysis,
visualization, and trend detection.

---

## Classes

### `BuildMetric`


Single build metric record.

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::
- **`timestamp`** (`str`)- **`total_pages`** (`int`)- **`build_time_ms`** (`float`)- **`memory_rss_mb`** (`float`)- **`memory_heap_mb`** (`float`)- **`memory_peak_mb`** (`float`)- **`parallel`** (`bool`)- **`incremental`** (`bool`)- **`skipped`** (`bool`)- **`discovery_time_ms`** (`float`)- **`taxonomy_time_ms`** (`float`)- **`rendering_time_ms`** (`float`)- **`assets_time_ms`** (`float`)- **`postprocess_time_ms`** (`float`)

:::{rubric} Properties
:class: rubric-properties
:::
#### `build_time_s` @property

```python
@property
def build_time_s(self) -> float
```

Build time in seconds.
#### `pages_per_second` @property

```python
@property
def pages_per_second(self) -> float
```

Throughput in pages/second.
#### `memory_per_page_mb` @property

```python
@property
def memory_per_page_mb(self) -> float
```

Memory per page in MB.
#### `datetime` @property

```python
@property
def datetime(self) -> datetime
```

Parse timestamp to datetime.

:::{rubric} Methods
:class: rubric-methods
:::
#### `build_time_s`
```python
def build_time_s(self) -> float
```

Build time in seconds.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`float`




---
#### `pages_per_second`
```python
def pages_per_second(self) -> float
```

Throughput in pages/second.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`float`




---
#### `memory_per_page_mb`
```python
def memory_per_page_mb(self) -> float
```

Memory per page in MB.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`float`




---
#### `datetime`
```python
def datetime(self) -> datetime
```

Parse timestamp to datetime.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`datetime`




---
#### `from_dict` @classmethod
```python
def from_dict(cls, data: dict[str, Any]) -> 'BuildMetric'
```

Create from dictionary.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`cls`**
- **`data`** (`dict[str, Any]`)

:::{rubric} Returns
:class: rubric-returns
:::
`'BuildMetric'`




---

### `PerformanceReport`


Generates performance reports from collected metrics.

Usage:
    report = PerformanceReport()
    report.show(last=10, format='table')




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, metrics_dir: Path | None = None)
```

Initialize report generator.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`metrics_dir`** (`Path | None`) = `None` - Directory containing metrics (default: .bengal-metrics)





---
#### `load_metrics`
```python
def load_metrics(self, last: int | None = None) -> list[BuildMetric]
```

Load metrics from history file.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`last`** (`int | None`) = `None` - Number of recent builds to load (None = all)

:::{rubric} Returns
:class: rubric-returns
:::
`list[BuildMetric]` - List of BuildMetric objects, most recent first




---
#### `show`
```python
def show(self, last: int = 10, format: str = 'table')
```

Show performance report.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`last`** (`int`) = `10` - Number of recent builds to show
- **`format`** (`str`) = `'table'` - Output format ('table', 'json', 'summary')





---
#### `compare`
```python
def compare(self, build1_idx: int = 0, build2_idx: int = 1)
```

Compare two builds.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`build1_idx`** (`int`) = `0` - Index of first build (0 = latest)
- **`build2_idx`** (`int`) = `1` - Index of second build





---
