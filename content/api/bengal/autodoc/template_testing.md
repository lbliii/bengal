
---
title: "template_testing"
type: "python-module"
source_file: "bengal/autodoc/template_testing.py"
line_number: 1
description: "Template testing framework for automated template validation and regression testing. Provides comprehensive testing capabilities for template safety, rendering accuracy, and performance regression det..."
---

# template_testing
**Type:** Module
**Source:** [View source](bengal/autodoc/template_testing.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[autodoc](/api/bengal/autodoc/) ›template_testing

Template testing framework for automated template validation and regression testing.

Provides comprehensive testing capabilities for template safety, rendering accuracy,
and performance regression detection.

## Classes




### `TemplateTestCase`


Test case for template rendering.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`name`
: 

`template_name`
: 

`element_data`
: 

`config_data`
: 

`expected_content`
: 

`expected_errors`
: 

`should_fail`
: 

`performance_threshold_ms`
: 

:::







## Methods



#### `to_dict`

:::{div} api-badge-group
:::

```python
def to_dict(self) -> dict[str, Any]
```


Convert to dictionary for serialization.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]`



#### `from_dict`

:::{div} api-badge-group
<span class="api-badge api-badge-classmethod">classmethod</span>:::

```python
def from_dict(cls, data: dict[str, Any]) -> TemplateTestCase
```


Create from dictionary.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `data` | `dict[str, Any]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`TemplateTestCase`




### `TemplateTestResult`


Result of template test execution.


:::{info}
This is a dataclass.
:::



**Attributes:**

:::{div} api-attributes
`test_case_name`
: 

`template_name`
: 

`passed`
: 

`render_time_ms`
: 

`content_length`
: 

`errors`
: 

`warnings`
: 

`failure_reason`
: 

`content_preview`
: 

:::







## Methods



#### `to_dict`

:::{div} api-badge-group
:::

```python
def to_dict(self) -> dict[str, Any]
```


Convert to dictionary for serialization.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]`




### `TemplateTestSuite`


Test suite for template validation and regression testing.









## Methods



#### `__init__`

:::{div} api-badge-group
:::

```python
def __init__(self, renderer: SafeTemplateRenderer, validator: TemplateValidator, sample_generator: SampleDataGenerator | None = None)
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `renderer` | `SafeTemplateRenderer` | - | *No description provided.* |
| `validator` | `TemplateValidator` | - | *No description provided.* |
| `sample_generator` | `SampleDataGenerator \| None` | - | *No description provided.* |








#### `add_test_case`

:::{div} api-badge-group
:::

```python
def add_test_case(self, test_case: TemplateTestCase) -> None
```


Add a test case to the suite.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `test_case` | `TemplateTestCase` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `generate_standard_test_cases`

:::{div} api-badge-group
:::

```python
def generate_standard_test_cases(self) -> None
```


Generate standard test cases for all template types.



:::{rubric} Returns
:class: rubric-returns
:::


`None`




#### `run_test_case`

:::{div} api-badge-group
:::

```python
def run_test_case(self, test_case: TemplateTestCase) -> TemplateTestResult
```


Run a single test case.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `test_case` | `TemplateTestCase` | - | Test case to execute |







:::{rubric} Returns
:class: rubric-returns
:::


`TemplateTestResult` - Test result




#### `run_all_tests`

:::{div} api-badge-group
:::

```python
def run_all_tests(self) -> dict[str, Any]
```


Run all test cases in the suite.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]` - Test suite results summary



#### `get_test_summary`

:::{div} api-badge-group
:::

```python
def get_test_summary(self) -> dict[str, Any]
```


Get summary of test results.



:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]`



#### `export_results`

:::{div} api-badge-group
:::

```python
def export_results(self, output_path: Path) -> None
```


Export test results to JSON file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `output_path` | `Path` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `load_test_cases`

:::{div} api-badge-group
:::

```python
def load_test_cases(self, input_path: Path) -> None
```


Load test cases from JSON file.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `input_path` | `Path` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`




### `RegressionTester`


Detect performance and output regressions in templates.









## Methods



#### `__init__`

:::{div} api-badge-group
:::

```python
def __init__(self, baseline_path: Path | None = None)
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `baseline_path` | `Path \| None` | - | *No description provided.* |








#### `load_baseline`

:::{div} api-badge-group
:::

```python
def load_baseline(self) -> None
```


Load baseline test results.



:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `save_baseline`

:::{div} api-badge-group
:::

```python
def save_baseline(self, test_results: dict[str, Any]) -> None
```


Save current results as new baseline.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `test_results` | `dict[str, Any]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`None`



#### `detect_regressions`

:::{div} api-badge-group
:::

```python
def detect_regressions(self, current_results: dict[str, Any]) -> dict[str, Any]
```


Detect regressions compared to baseline.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `current_results` | `dict[str, Any]` | - | Current test results |







:::{rubric} Returns
:class: rubric-returns
:::


`dict[str, Any]` - Regression analysis report

## Functions



### `create_template_test_suite`


```python
def create_template_test_suite(renderer: SafeTemplateRenderer, validator: TemplateValidator, include_standard_tests: bool = True) -> TemplateTestSuite
```



Create a comprehensive template test suite.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `renderer` | `SafeTemplateRenderer` | - | Safe template renderer |
| `validator` | `TemplateValidator` | - | Template validator |
| `include_standard_tests` | `bool` | `True` | Whether to include standard test cases |







**Returns**


`TemplateTestSuite` - Configured test suite



---
*Generated by Bengal autodoc from `bengal/autodoc/template_testing.py`*

