
---
title: "progress"
type: "python-module"
source_file: "bengal/bengal/utils/progress.py"
line_number: 1
description: "progress package"
---

# progress
**Type:** Module
**Source:** [View source](bengal/bengal/utils/progress.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[utils](/api/bengal/utils/) ›progress

*No module description provided.*

## Classes




### `ProgressReporter`


**Inherits from:**`Protocol`Contract for reporting build progress and user-facing messages.

Implementations: CLI, server, noop (tests), rich, etc.









## Methods



#### `add_phase`
```python
def add_phase(self, phase_id: str, label: str, total: int | None = None) -> None
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `phase_id` | `str` | - | *No description provided.* |
| `label` | `str` | - | *No description provided.* |
| `total` | `int \| None` | - | *No description provided.* |







**Returns**


`None`



#### `start_phase`
```python
def start_phase(self, phase_id: str) -> None
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `phase_id` | `str` | - | *No description provided.* |







**Returns**


`None`



#### `update_phase`
```python
def update_phase(self, phase_id: str, current: int | None = None, current_item: str | None = None) -> None
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `phase_id` | `str` | - | *No description provided.* |
| `current` | `int \| None` | - | *No description provided.* |
| `current_item` | `str \| None` | - | *No description provided.* |







**Returns**


`None`



#### `complete_phase`
```python
def complete_phase(self, phase_id: str, elapsed_ms: float | None = None) -> None
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `phase_id` | `str` | - | *No description provided.* |
| `elapsed_ms` | `float \| None` | - | *No description provided.* |







**Returns**


`None`



#### `log`
```python
def log(self, message: str) -> None
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `message` | `str` | - | *No description provided.* |







**Returns**


`None`




### `NoopReporter`


Default reporter that does nothing (safe for tests and quiet modes).









## Methods



#### `add_phase`
```python
def add_phase(self, phase_id: str, label: str, total: int | None = None) -> None
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `phase_id` | `str` | - | *No description provided.* |
| `label` | `str` | - | *No description provided.* |
| `total` | `int \| None` | - | *No description provided.* |







**Returns**


`None`



#### `start_phase`
```python
def start_phase(self, phase_id: str) -> None
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `phase_id` | `str` | - | *No description provided.* |







**Returns**


`None`



#### `update_phase`
```python
def update_phase(self, phase_id: str, current: int | None = None, current_item: str | None = None) -> None
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `phase_id` | `str` | - | *No description provided.* |
| `current` | `int \| None` | - | *No description provided.* |
| `current_item` | `str \| None` | - | *No description provided.* |







**Returns**


`None`



#### `complete_phase`
```python
def complete_phase(self, phase_id: str, elapsed_ms: float | None = None) -> None
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `phase_id` | `str` | - | *No description provided.* |
| `elapsed_ms` | `float \| None` | - | *No description provided.* |







**Returns**


`None`



#### `log`
```python
def log(self, message: str) -> None
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `message` | `str` | - | *No description provided.* |







**Returns**


`None`




### `LiveProgressReporterAdapter`


Adapter to bridge LiveProgressManager to ProgressReporter.

Delegates phase methods directly and prints simple lines for log().









## Methods



#### `__init__`
```python
def __init__(self, live_progress_manager: Any)
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `live_progress_manager` | `Any` | - | *No description provided.* |








#### `add_phase`
```python
def add_phase(self, phase_id: str, label: str, total: int | None = None) -> None
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `phase_id` | `str` | - | *No description provided.* |
| `label` | `str` | - | *No description provided.* |
| `total` | `int \| None` | - | *No description provided.* |







**Returns**


`None`



#### `start_phase`
```python
def start_phase(self, phase_id: str) -> None
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `phase_id` | `str` | - | *No description provided.* |







**Returns**


`None`



#### `update_phase`
```python
def update_phase(self, phase_id: str, current: int | None = None, current_item: str | None = None) -> None
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `phase_id` | `str` | - | *No description provided.* |
| `current` | `int \| None` | - | *No description provided.* |
| `current_item` | `str \| None` | - | *No description provided.* |







**Returns**


`None`



#### `complete_phase`
```python
def complete_phase(self, phase_id: str, elapsed_ms: float | None = None) -> None
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `phase_id` | `str` | - | *No description provided.* |
| `elapsed_ms` | `float \| None` | - | *No description provided.* |







**Returns**


`None`



#### `log`
```python
def log(self, message: str) -> None
```


*No description provided.*


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `message` | `str` | - | *No description provided.* |







**Returns**


`None`



---
*Generated by Bengal autodoc from `bengal/bengal/utils/progress.py`*
