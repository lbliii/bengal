---
title: "template_functions.collections"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_functions/collections.py"
---

# template_functions.collections

Collection manipulation functions for templates.

Provides 8 functions for filtering, sorting, and transforming lists and dicts.

**Source:** `../../bengal/rendering/template_functions/collections.py`

---


## Functions

### register

```python
def register(env: 'Environment', site: 'Site') -> None
```

Register collection functions with Jinja2 environment.

**Parameters:**

- **env** (`'Environment'`)
- **site** (`'Site'`)

**Returns:** `None`





---
### where

```python
def where(items: List[Dict[str, Any]], key: str, value: Any) -> List[Dict[str, Any]]
```

Filter items where key equals value.

**Parameters:**

- **items** (`List[Dict[str, Any]]`) - List of dictionaries to filter
- **key** (`str`) - Dictionary key to check
- **value** (`Any`) - Value to match

**Returns:** `List[Dict[str, Any]]` - Filtered list


**Examples:**

{% set tutorials = site.pages | where('category', 'tutorial') %}




---
### where_not

```python
def where_not(items: List[Dict[str, Any]], key: str, value: Any) -> List[Dict[str, Any]]
```

Filter items where key does not equal value.

**Parameters:**

- **items** (`List[Dict[str, Any]]`) - List of dictionaries to filter
- **key** (`str`) - Dictionary key to check
- **value** (`Any`) - Value to exclude

**Returns:** `List[Dict[str, Any]]` - Filtered list


**Examples:**

{% set active = users | where_not('status', 'archived') %}




---
### group_by

```python
def group_by(items: List[Dict[str, Any]], key: str) -> Dict[Any, List[Dict[str, Any]]]
```

Group items by key value.

**Parameters:**

- **items** (`List[Dict[str, Any]]`) - List of dictionaries to group
- **key** (`str`) - Dictionary key to group by

**Returns:** `Dict[Any, List[Dict[str, Any]]]` - Dictionary mapping key values to lists of items


**Examples:**

{% set by_category = posts | group_by('category') %}




---
### sort_by

```python
def sort_by(items: List[Any], key: str, reverse: bool = False) -> List[Any]
```

Sort items by key.

**Parameters:**

- **items** (`List[Any]`) - List to sort
- **key** (`str`) - Dictionary key or object attribute to sort by
- **reverse** (`bool`) = `False` - Sort in descending order (default: False)

**Returns:** `List[Any]` - Sorted list


**Examples:**

{% set recent = posts | sort_by('date', reverse=true) %}




---
### limit

```python
def limit(items: List[Any], count: int) -> List[Any]
```

Limit items to specified count.

**Parameters:**

- **items** (`List[Any]`) - List to limit
- **count** (`int`) - Maximum number of items

**Returns:** `List[Any]` - First N items


**Examples:**

{% set recent_5 = posts | sort_by('date', reverse=true) | limit(5) %}




---
### offset

```python
def offset(items: List[Any], count: int) -> List[Any]
```

Skip first N items.

**Parameters:**

- **items** (`List[Any]`) - List to skip from
- **count** (`int`) - Number of items to skip

**Returns:** `List[Any]` - Items after offset


**Examples:**

{% set page_2 = posts | offset(10) | limit(10) %}




---
### uniq

```python
def uniq(items: List[Any]) -> List[Any]
```

Remove duplicate items while preserving order.

**Parameters:**

- **items** (`List[Any]`) - List with potential duplicates

**Returns:** `List[Any]` - List with duplicates removed


**Examples:**

{% set unique_tags = all_tags | uniq %}




---
### flatten

```python
def flatten(items: List[List[Any]]) -> List[Any]
```

Flatten nested lists into single list.

Only flattens one level deep.

**Parameters:**

- **items** (`List[List[Any]]`) - List of lists

**Returns:** `List[Any]` - Flattened list


**Examples:**

{% set all_tags = posts | map(attribute='tags') | flatten %}




---
