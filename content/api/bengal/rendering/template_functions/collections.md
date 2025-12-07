
---
title: "collections"
type: "python-module"
source_file: "bengal/rendering/template_functions/collections.py"
line_number: 1
description: "Collection manipulation functions for templates. Provides 15+ functions for filtering, sorting, and transforming lists and dicts. Includes advanced page querying and manipulation functions."
---

# collections
**Type:** Module
**Source:** [View source](bengal/rendering/template_functions/collections.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[rendering](/api/bengal/rendering/) ›[template_functions](/api/bengal/rendering/template_functions/) ›collections

Collection manipulation functions for templates.

Provides 15+ functions for filtering, sorting, and transforming lists and dicts.
Includes advanced page querying and manipulation functions.

## Functions



### `register`


```python
def register(env: Environment, site: Site) -> None
```



Register collection functions with Jinja2 environment.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `env` | `Environment` | - | *No description provided.* |
| `site` | `Site` | - | *No description provided.* |







**Returns**


`None`




### `where`


```python
def where(items: list[dict[str, Any]], key: str, value: Any = None, operator: str = 'eq') -> list[dict[str, Any]]
```



Filter items where key matches value using specified operator.

Supports nested attribute access (e.g., 'metadata.track_id') and comparison operators.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `items` | `list[dict[str, Any]]` | - | List of dictionaries or objects to filter |
| `key` | `str` | - | Dictionary key or attribute path to check (supports dot notation like 'metadata.track_id') |
| `value` | `Any` | - | Value to compare against (required for all operators) |
| `operator` | `str` | `'eq'` | Comparison operator: 'eq' (default), 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'not in' |







**Returns**


`list[dict[str, Any]]` - Filtered list
:::{rubric} Examples
:class: rubric-examples
:::


```python
{# Basic equality (backward compatible) #}
    {% set tutorials = site.pages | where('category', 'tutorial') %}
    {% set track_pages = site.pages | where('metadata.track_id', 'getting-started') %}

    {# With operators #}
    {% set recent = site.pages | where('date', one_year_ago, 'gt') %}
    {% set python = site.pages | where('tags', ['python', 'web'], 'in') %}
    {% set published = site.pages | where('status', 'draft', 'ne') %}
```





### `where_not`


```python
def where_not(items: list[dict[str, Any]], key: str, value: Any) -> list[dict[str, Any]]
```



Filter items where key does not equal value.

Supports nested attribute access (e.g., 'metadata.track_id').


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `items` | `list[dict[str, Any]]` | - | List of dictionaries or objects to filter |
| `key` | `str` | - | Dictionary key or attribute path to check (supports dot notation like 'metadata.track_id') |
| `value` | `Any` | - | Value to exclude |







**Returns**


`list[dict[str, Any]]` - Filtered list
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set active = users | where_not('status', 'archived') %}
    {% set non_tracks = site.pages | where_not('metadata.track_id', 'getting-started') %}
```





### `group_by`


```python
def group_by(items: list[dict[str, Any]], key: str) -> dict[Any, list[dict[str, Any]]]
```



Group items by key value.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `items` | `list[dict[str, Any]]` | - | List of dictionaries to group |
| `key` | `str` | - | Dictionary key to group by |







**Returns**


`dict[Any, list[dict[str, Any]]]` - Dictionary mapping key values to lists of items
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set by_category = posts | group_by('category') %}
    {% for category, posts in by_category.items() %}
        <h2>{{ category }}</h2>
        ...
    {% endfor %}
```





### `sort_by`


```python
def sort_by(items: list[Any], key: str, reverse: bool = False) -> list[Any]
```



Sort items by key.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `items` | `list[Any]` | - | List to sort |
| `key` | `str` | - | Dictionary key or object attribute to sort by |
| `reverse` | `bool` | `False` | Sort in descending order (default: False) |







**Returns**


`list[Any]` - Sorted list
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set recent = posts | sort_by('date', reverse=true) %}
    {% set alphabetical = pages | sort_by('title') %}
```





### `limit`


```python
def limit(items: list[Any], count: int) -> list[Any]
```



Limit items to specified count.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `items` | `list[Any]` | - | List to limit |
| `count` | `int` | - | Maximum number of items |







**Returns**


`list[Any]` - First N items
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set recent_5 = posts | sort_by('date', reverse=true) | limit(5) %}
```





### `offset`


```python
def offset(items: list[Any], count: int) -> list[Any]
```



Skip first N items.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `items` | `list[Any]` | - | List to skip from |
| `count` | `int` | - | Number of items to skip |







**Returns**


`list[Any]` - Items after offset
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set page_2 = posts | offset(10) | limit(10) %}
```





### `uniq`


```python
def uniq(items: list[Any]) -> list[Any]
```



Remove duplicate items while preserving order.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `items` | `list[Any]` | - | List with potential duplicates |







**Returns**


`list[Any]` - List with duplicates removed
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set unique_tags = all_tags | uniq %}
```





### `flatten`


```python
def flatten(items: list[list[Any]]) -> list[Any]
```



Flatten nested lists into single list.

Only flattens one level deep.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `items` | `list[list[Any]]` | - | List of lists |







**Returns**


`list[Any]` - Flattened list
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set all_tags = posts | map(attribute='tags') | flatten %}
```





### `first`


```python
def first(items: list[Any]) -> Any
```



Get first item from list.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `items` | `list[Any]` | - | List to get first item from |







**Returns**


`Any` - First item or None if list is empty
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set featured = site.pages | where('metadata.featured', true) | first %}
    {% if featured %}
        <h2>{{ featured.title }}</h2>
    {% endif %}
```





### `last`


```python
def last(items: list[Any]) -> Any
```



Get last item from list.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `items` | `list[Any]` | - | List to get last item from |







**Returns**


`Any` - Last item or None if list is empty
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set latest = posts | sort_by('date', reverse=true) | first %}
    {% set oldest = posts | sort_by('date') | last %}
```





### `reverse`


```python
def reverse(items: list[Any]) -> list[Any]
```



Reverse a list.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `items` | `list[Any]` | - | List to reverse |







**Returns**


`list[Any]` - Reversed copy of list
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set reversed = posts | reverse %}
    {% set chronological = posts | sort_by('date') | reverse %}
```





### `union`


```python
def union(items1: list[Any], items2: list[Any]) -> list[Any]
```



Combine two lists, removing duplicates (set union).

Preserves order from first list, then adds items from second list that aren't already present.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `items1` | `list[Any]` | - | First list |
| `items2` | `list[Any]` | - | Second list |







**Returns**


`list[Any]` - Combined list with duplicates removed
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set all = posts | union(pages) %}
    {% set combined = site.pages | where('type', 'post') | union(site.pages | where('type', 'page')) %}
```





### `intersect`


```python
def intersect(items1: list[Any], items2: list[Any]) -> list[Any]
```



Get items that appear in both lists (set intersection).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `items1` | `list[Any]` | - | First list |
| `items2` | `list[Any]` | - | Second list |







**Returns**


`list[Any]` - List of items present in both lists
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set common = posts | intersect(featured_pages) %}
    {% set python_and_web = site.pages | where('tags', 'python', 'in') | intersect(site.pages | where('tags', 'web', 'in')) %}
```





### `complement`


```python
def complement(items1: list[Any], items2: list[Any]) -> list[Any]
```



Get items in first list that are not in second list (set difference).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `items1` | `list[Any]` | - | First list (items to keep) |
| `items2` | `list[Any]` | - | Second list (items to exclude) |







**Returns**


`list[Any]` - List of items in first list but not in second list
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set only_posts = posts | complement(pages) %}
    {% set non_featured = site.pages | complement(site.pages | where('metadata.featured', true)) %}
```





### `resolve_pages`


```python
def resolve_pages(page_paths: list[str], site: Site) -> list
```



Resolve page paths to Page objects.

Used with query indexes to convert O(1) path lookups into Page objects:
    {% set blog_paths = site.indexes.section.get('blog') %}
    {% set blog_pages = blog_paths | resolve_pages %}


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `page_paths` | `list[str]` | - | List of page source paths (strings) |
| `site` | `Site` | - | Site instance with pages |







**Returns**


`list` - List of Page objects
:::{rubric} Examples
:class: rubric-examples
:::


```python
{% set author_paths = site.indexes.author.get('Jane Smith') %}
    {% set author_posts = author_paths | resolve_pages %}
    {% for post in author_posts | sort(attribute='date', reverse=true) %}
        <h2>{{ post.title }}</h2>
    {% endfor %}
```



---
*Generated by Bengal autodoc from `bengal/rendering/template_functions/collections.py`*

