
---
title: "analysis.performance_advisor"
type: python-module
source_file: "bengal/analysis/performance_advisor.py"
css_class: api-content
description: "Performance analysis and intelligent suggestions for Bengal builds.  Analyzes build statistics and provides context-aware recommendations for improving build speed, resource usage, and developer ex..."
---

# analysis.performance_advisor

Performance analysis and intelligent suggestions for Bengal builds.

Analyzes build statistics and provides context-aware recommendations
for improving build speed, resource usage, and developer experience.

---

## Classes

### `SuggestionType`

**Inherits from:** `Enum`
Types of performance suggestions.





### `SuggestionPriority`

**Inherits from:** `Enum`
Priority levels for suggestions.





### `PerformanceSuggestion`


A single performance improvement suggestion.

Represents an actionable recommendation to improve build performance,
with estimated impact and configuration examples.

Attributes:
    type: Category of suggestion (BUILD, CONTENT, CONFIG, etc.)
    priority: Priority level (HIGH, MEDIUM, LOW)
    title: Short title of the suggestion
    description: Detailed explanation of the issue
    impact: Estimated performance impact (e.g., "Could save ~2.5s")
    action: What the user should do to implement this suggestion
    config_example: Optional example configuration change

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::
- **`type`** (`SuggestionType`)- **`priority`** (`SuggestionPriority`)- **`title`** (`str`)- **`description`** (`str`)- **`impact`** (`str`)- **`action`** (`str`)- **`config_example`** (`str | None`)


:::{rubric} Methods
:class: rubric-methods
:::
#### `__str__`
```python
def __str__(self) -> str
```

Format suggestion for display.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`str`




---

### `PerformanceGrade`


Overall performance assessment for a build.

Provides a letter grade (A-F) and category assessment based on
build performance metrics and best practices compliance.

Attributes:
    grade: Letter grade (A, B, C, D, or F)
    score: Numeric score (0-100)
    category: Performance category ("Excellent", "Good", "Fair", "Poor", "Critical")
    summary: One-line summary of performance assessment

```{info}
This is a dataclass.
```

:::{rubric} Attributes
:class: rubric-attributes
:::
- **`grade`** (`str`)- **`score`** (`int`)- **`category`** (`str`)- **`summary`** (`str`)


:::{rubric} Methods
:class: rubric-methods
:::
#### `calculate` @classmethod
```python
def calculate(cls, stats: BuildStats) -> PerformanceGrade
```

Calculate performance grade based on build statistics.

Scoring factors:
- Build speed (pages/second)
- Time distribution (balanced vs bottlenecked)
- Cache effectiveness (if incremental)
- Resource usage



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`cls`**
- **`stats`** (`BuildStats`)

:::{rubric} Returns
:class: rubric-returns
:::
`PerformanceGrade`




---

### `PerformanceAdvisor`


Analyzes build performance and provides intelligent suggestions.

Uses build statistics to identify bottlenecks and recommend
optimizations tailored to the specific project.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, stats: BuildStats, environment: dict[str, Any] | None = None)
```

Initialize performance advisor.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`stats`** (`BuildStats`) - Build statistics to analyze
- **`environment`** (`dict[str, Any] | None`) = `None` - Environment info from rich_console.detect_environment()





---
#### `analyze`
```python
def analyze(self) -> list[PerformanceSuggestion]
```

Analyze build and generate suggestions.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`list[PerformanceSuggestion]` - List of suggestions, ordered by priority




---
#### `get_grade`
```python
def get_grade(self) -> PerformanceGrade
```

Get overall performance grade.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`PerformanceGrade` - PerformanceGrade with score and category




---
#### `get_bottleneck`
```python
def get_bottleneck(self) -> str | None
```

Identify the primary bottleneck phase.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`str | None` - Name of slowest phase, or None if well-balanced




---
#### `get_top_suggestions`
```python
def get_top_suggestions(self, limit: int = 3) -> list[PerformanceSuggestion]
```

Get top N suggestions.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`limit`** (`int`) = `3` - Maximum number of suggestions to return

:::{rubric} Returns
:class: rubric-returns
:::
`list[PerformanceSuggestion]` - Up to `limit` highest-priority suggestions




---
#### `format_summary`
```python
def format_summary(self) -> str
```

Format a text summary of analysis.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Multi-line string with analysis summary




---


## Functions

### `analyze_build`
```python
def analyze_build(stats: BuildStats, environment: dict[str, Any] | None = None) -> PerformanceAdvisor
```

Quick analysis of build statistics.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`stats`** (`BuildStats`) - Build statistics
- **`environment`** (`dict[str, Any] | None`) = `None` - Optional environment info

:::{rubric} Returns
:class: rubric-returns
:::
`PerformanceAdvisor` - PerformanceAdvisor with analysis complete




---
