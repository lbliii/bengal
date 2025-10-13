
---
title: "template_functions.collections"
type: python-module
source_file: "bengal/rendering/template_functions/collections.py"
css_class: api-content
description: "Collection manipulation functions for templates.  Provides 8 functions for filtering, sorting, and transforming lists and dicts."
---

# template_functions.collections

Collection manipulation functions for templates.

Provides 8 functions for filtering, sorting, and transforming lists and dicts.

---


## Functions

### `register`
```python
def register(env: Environment, site: Site) -> None
```

Register collection functions with Jinja2 environment.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`env`** (`Environment`)
- **`site`** (`Site`)

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `where`
```python
def where(items: list[dict[str, Any]], key: str, value: Any) -> list[dict[str, Any]]
```

Filter items where key equals value.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`items`** (`list[dict[str, Any]]`) - List of dictionaries to filter
- **`key`** (`str`) - Dictionary key to check
- **`value`** (`Any`) - Value to match

:::{rubric} Returns
:class: rubric-returns
:::
`list[dict[str, Any]]` - Filtered list




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set tutorials = site.pages | where('category', 'tutorial') %}
```


---
### `where_not`
```python
def where_not(items: list[dict[str, Any]], key: str, value: Any) -> list[dict[str, Any]]
```

Filter items where key does not equal value.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`items`** (`list[dict[str, Any]]`) - List of dictionaries to filter
- **`key`** (`str`) - Dictionary key to check
- **`value`** (`Any`) - Value to exclude

:::{rubric} Returns
:class: rubric-returns
:::
`list[dict[str, Any]]` - Filtered list




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set active = users | where_not('status', 'archived') %}
```


---
### `group_by`
```python
def group_by(items: list[dict[str, Any]], key: str) -> dict[Any, list[dict[str, Any]]]
```

Group items by key value.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`items`** (`list[dict[str, Any]]`) - List of dictionaries to group
- **`key`** (`str`) - Dictionary key to group by

:::{rubric} Returns
:class: rubric-returns
:::
`dict[Any, list[dict[str, Any]]]` - Dictionary mapping key values to lists of items




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set by_category = posts | group_by('category') %}
```


---
### `sort_by`
```python
def sort_by(items: list[Any], key: str, reverse: bool = False) -> list[Any]
```

Sort items by key.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`items`** (`list[Any]`) - List to sort
- **`key`** (`str`) - Dictionary key or object attribute to sort by
- **`reverse`** (`bool`) = `False` - Sort in descending order (default: False)

:::{rubric} Returns
:class: rubric-returns
:::
`list[Any]` - Sorted list




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set recent = posts | sort_by('date', reverse=true) %}
```


---
### `limit`
```python
def limit(items: list[Any], count: int) -> list[Any]
```

Limit items to specified count.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`items`** (`list[Any]`) - List to limit
- **`count`** (`int`) - Maximum number of items

:::{rubric} Returns
:class: rubric-returns
:::
`list[Any]` - First N items




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set recent_5 = posts | sort_by('date', reverse=true) | limit(5) %}
```


---
### `offset`
```python
def offset(items: list[Any], count: int) -> list[Any]
```

Skip first N items.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`items`** (`list[Any]`) - List to skip from
- **`count`** (`int`) - Number of items to skip

:::{rubric} Returns
:class: rubric-returns
:::
`list[Any]` - Items after offset




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set page_2 = posts | offset(10) | limit(10) %}
```


---
### `uniq`
```python
def uniq(items: list[Any]) -> list[Any]
```

Remove duplicate items while preserving order.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`items`** (`list[Any]`) - List with potential duplicates

:::{rubric} Returns
:class: rubric-returns
:::
`list[Any]` - List with duplicates removed




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set unique_tags = all_tags | uniq %}
```


---
### `flatten`
```python
def flatten(items: list[list[Any]]) -> list[Any]
```

Flatten nested lists into single list.

Only flattens one level deep.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`items`** (`list[list[Any]]`) - List of lists

:::{rubric} Returns
:class: rubric-returns
:::
`list[Any]` - Flattened list




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set all_tags = posts | map(attribute='tags') | flatten %}
```


---
