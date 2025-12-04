
---
title: "progress"
type: "python-module"
source_file: "bengal/bengal/utils/progress.py"
line_number: 1
description: "Progress reporting system for build progress tracking. Provides protocol-based progress reporting with multiple implementations (CLI, server, noop for tests). Enables consistent progress reporting acr..."
---

# progress
**Type:** Module
**Source:** [View source](bengal/bengal/utils/progress.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[utils](/api/bengal/utils/) ›progress

Progress reporting system for build progress tracking.

Provides protocol-based progress reporting with multiple implementations
(CLI, server, noop for tests). Enables consistent progress reporting across
different execution contexts.

Key Concepts:
    - Progress protocol: Protocol-based interface for progress reporting
    - Phase tracking: Build phase tracking with progress updates
    - Multiple implementations: CLI, server, noop, rich reporters
    - Adapter pattern: LiveProgressManager adapter for compatibility

Related Modules:
    - bengal.utils.live_progress: Live progress manager implementation
    - bengal.orchestration.build: Build orchestration using progress reporting
    - bengal.cli.commands.build: CLI build command using progress reporting

See Also:
    - bengal/utils/progress.py:ProgressReporter for progress protocol
    - bengal/utils/progress.py:NoopReporter for test-friendly implementation

## Classes




### `ProgressReporter`


**Inherits from:**`Protocol`Protocol for reporting build progress and user-facing messages.

Defines interface for progress reporting implementations. Used throughout
the build system for consistent progress reporting across CLI, server, and
test contexts.

Creation:
    Protocol - not instantiated directly. Implementations include:
    - NoopReporter: No-op implementation for tests
    - LiveProgressReporterAdapter: Adapter for LiveProgressManager
    - CLI implementations: Rich progress bars for CLI

Relationships:
    - Implemented by: NoopReporter, LiveProgressReporterAdapter, CLI reporters
    - Used by: BuildOrchestrator for build progress reporting
    - Used by: All orchestrators for phase progress updates









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


No-op progress reporter implementation.

Provides safe default implementation that does nothing, suitable for tests
and quiet modes. All methods are no-ops that return immediately.

Creation:
    Direct instantiation: NoopReporter()
        - Created as default reporter when no progress reporting needed
        - Safe for tests and quiet build modes

Relationships:
    - Implements: ProgressReporter protocol
    - Used by: BuildOrchestrator as default reporter
    - Used in: Tests and quiet build modes









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


Adapter to bridge LiveProgressManager to ProgressReporter protocol.

Provides adapter pattern implementation that bridges LiveProgressManager
to the ProgressReporter protocol. Delegates phase methods directly and
prints simple lines for log() messages.

Creation:
    Direct instantiation: LiveProgressReporterAdapter(live_progress_manager)
        - Created by BuildOrchestrator when using LiveProgressManager
        - Requires LiveProgressManager instance



**Attributes:**

| Name | Type | Description |
|:-----|:-----|:------------|
| `_pm` | - | LiveProgressManager instance being adapted |
| `Relationships` | - | - Implements: ProgressReporter protocol - Uses: LiveProgressManager for actual progress reporting - Used by: BuildOrchestrator for progress reporting |







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
