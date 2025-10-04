---
title: "template_functions.advanced_collections"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_functions/advanced_collections.py"
---

# template_functions.advanced_collections

Advanced collection manipulation functions for templates.

Provides 3 advanced functions for working with lists.

**Source:** `../../bengal/rendering/template_functions/advanced_collections.py`

---


## Functions

### register

```python
def register(env: 'Environment', site: 'Site') -> None
```

Register advanced collection functions with Jinja2 environment.

**Parameters:**

- **env** (`'Environment'`)
- **site** (`'Site'`)

**Returns:** `None`





---
### sample

```python
def sample(items: List[Any], count: int = 1, seed: int = None) -> List[Any]
```

Get random sample of items.

**Parameters:**

- **items** (`List[Any]`) - List to sample from
- **count** (`int`) = `1` - Number of items to sample (default: 1)
- **seed** (`int`) = `None` - Random seed for reproducibility (optional)

**Returns:** `List[Any]` - Random sample of items


**Examples:**

{% set featured = posts | sample(3) %}




---
### shuffle

```python
def shuffle(items: List[Any], seed: int = None) -> List[Any]
```

Shuffle items randomly.

**Parameters:**

- **items** (`List[Any]`) - List to shuffle
- **seed** (`int`) = `None` - Random seed for reproducibility (optional)

**Returns:** `List[Any]` - Shuffled copy of list


**Examples:**

{% set random_posts = posts | shuffle %}




---
### chunk

```python
def chunk(items: List[Any], size: int) -> List[List[Any]]
```

Split list into chunks of specified size.

**Parameters:**

- **items** (`List[Any]`) - List to chunk
- **size** (`int`) - Chunk size

**Returns:** `List[List[Any]]` - List of chunks


**Examples:**

{% for row in items | chunk(3) %}




---
