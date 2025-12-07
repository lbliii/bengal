
---
title: "strategies"
type: "python-module"
source_file: "bengal/content_types/strategies.py"
line_number: 1
description: "Concrete content type strategies. Implements specific strategies for different content types like blog, docs, etc."
---

# strategies
**Type:** Module
**Source:** [View source](bengal/content_types/strategies.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[content_types](/api/bengal/content_types/) ›strategies

Concrete content type strategies.

Implements specific strategies for different content types like blog, docs, etc.

## Classes




### `BlogStrategy`


**Inherits from:**`ContentTypeStrategy`Strategy for blog/news content with chronological ordering.









## Methods



#### `sort_pages`

:::{div} api-badge-group
:::

```python
def sort_pages(self, pages: list[Page]) -> list[Page]
```


Sort by date (newest first).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `pages` | `list[Page]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`list[Page]`



#### `detect_from_section`

:::{div} api-badge-group
:::

```python
def detect_from_section(self, section: Section) -> bool
```


Detect blog sections by name or date-heavy content.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `section` | `Section` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`bool`



#### `get_template`

:::{div} api-badge-group
:::

```python
def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str
```


Blog-specific template selection.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Page \| None` | - | *No description provided.* |
| `template_engine` | `Any \| None` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`str`




### `ArchiveStrategy`


**Inherits from:**`BlogStrategy`Strategy for archive/chronological content.

Similar to blog but uses simpler archive template.












### `DocsStrategy`


**Inherits from:**`ContentTypeStrategy`Strategy for documentation with weight-based ordering.









## Methods



#### `sort_pages`

:::{div} api-badge-group
:::

```python
def sort_pages(self, pages: list[Page]) -> list[Page]
```


Sort by weight, then title (keeps manual ordering).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `pages` | `list[Page]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`list[Page]`



#### `detect_from_section`

:::{div} api-badge-group
:::

```python
def detect_from_section(self, section: Section) -> bool
```


Detect docs sections by name.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `section` | `Section` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`bool`



#### `get_template`

:::{div} api-badge-group
:::

```python
def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str
```


Docs-specific template selection.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Page \| None` | - | *No description provided.* |
| `template_engine` | `Any \| None` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`str`




### `ApiReferenceStrategy`


**Inherits from:**`ContentTypeStrategy`Strategy for API reference documentation.









## Methods



#### `sort_pages`

:::{div} api-badge-group
:::

```python
def sort_pages(self, pages: list[Page]) -> list[Page]
```


Keep original discovery order (alphabetical).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `pages` | `list[Page]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`list[Page]`



#### `detect_from_section`

:::{div} api-badge-group
:::

```python
def detect_from_section(self, section: Section) -> bool
```


Detect API sections by name or content.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `section` | `Section` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`bool`



#### `get_template`

:::{div} api-badge-group
:::

```python
def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str
```


API reference-specific template selection.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Page \| None` | - | *No description provided.* |
| `template_engine` | `Any \| None` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`str`




### `CliReferenceStrategy`


**Inherits from:**`ContentTypeStrategy`Strategy for CLI reference documentation.









## Methods



#### `sort_pages`

:::{div} api-badge-group
:::

```python
def sort_pages(self, pages: list[Page]) -> list[Page]
```


Keep original discovery order (alphabetical).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `pages` | `list[Page]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`list[Page]`



#### `detect_from_section`

:::{div} api-badge-group
:::

```python
def detect_from_section(self, section: Section) -> bool
```


Detect CLI sections by name or content.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `section` | `Section` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`bool`



#### `get_template`

:::{div} api-badge-group
:::

```python
def get_template(self, page: Page | None = None, template_engine: Any | None = None) -> str
```


CLI reference-specific template selection.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page` | `Page \| None` | - | *No description provided.* |
| `template_engine` | `Any \| None` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`str`




### `TutorialStrategy`


**Inherits from:**`ContentTypeStrategy`Strategy for tutorial content.









## Methods



#### `sort_pages`

:::{div} api-badge-group
:::

```python
def sort_pages(self, pages: list[Page]) -> list[Page]
```


Sort by weight (for sequential tutorials).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `pages` | `list[Page]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`list[Page]`



#### `detect_from_section`

:::{div} api-badge-group
:::

```python
def detect_from_section(self, section: Section) -> bool
```


Detect tutorial sections by name.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `section` | `Section` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`bool`




### `ChangelogStrategy`


**Inherits from:**`ContentTypeStrategy`Strategy for changelog/release notes with chronological timeline.









## Methods



#### `sort_pages`

:::{div} api-badge-group
:::

```python
def sort_pages(self, pages: list[Page]) -> list[Page]
```


Sort by date (newest first) or by version number.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `pages` | `list[Page]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`list[Page]`



#### `detect_from_section`

:::{div} api-badge-group
:::

```python
def detect_from_section(self, section: Section) -> bool
```


Detect changelog sections by name.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `section` | `Section` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`bool`




### `PageStrategy`


**Inherits from:**`ContentTypeStrategy`Default strategy for generic pages.









## Methods



#### `sort_pages`

:::{div} api-badge-group
:::

```python
def sort_pages(self, pages: list[Page]) -> list[Page]
```


Sort by weight, then title.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `pages` | `list[Page]` | - | *No description provided.* |







:::{rubric} Returns
:class: rubric-returns
:::


`list[Page]`



---
*Generated by Bengal autodoc from `bengal/content_types/strategies.py`*

