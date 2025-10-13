
---
title: "template_functions.advanced_collections"
type: python-module
source_file: "bengal/rendering/template_functions/advanced_collections.py"
css_class: api-content
description: "Advanced collection manipulation functions for templates.  Provides 3 advanced functions for working with lists."
---

# template_functions.advanced_collections

Advanced collection manipulation functions for templates.

Provides 3 advanced functions for working with lists.

---


## Functions

### `register`
```python
def register(env: 'Environment', site: 'Site') -> None
```

Register advanced collection functions with Jinja2 environment.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`env`** (`'Environment'`)
- **`site`** (`'Site'`)

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `sample`
```python
def sample(items: list[Any], count: int = 1, seed: int | None = None) -> list[Any]
```

Get random sample of items.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`items`** (`list[Any]`) - List to sample from
- **`count`** (`int`) = `1` - Number of items to sample (default: 1)
- **`seed`** (`int | None`) = `None` - Random seed for reproducibility (optional)

:::{rubric} Returns
:class: rubric-returns
:::
`list[Any]` - Random sample of items




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set featured = posts | sample(3) %}
```


---
### `shuffle`
```python
def shuffle(items: list[Any], seed: int | None = None) -> list[Any]
```

Shuffle items randomly.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`items`** (`list[Any]`) - List to shuffle
- **`seed`** (`int | None`) = `None` - Random seed for reproducibility (optional)

:::{rubric} Returns
:class: rubric-returns
:::
`list[Any]` - Shuffled copy of list




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% set random_posts = posts | shuffle %}
```


---
### `chunk`
```python
def chunk(items: list[Any], size: int) -> list[list[Any]]
```

Split list into chunks of specified size.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`items`** (`list[Any]`) - List to chunk
- **`size`** (`int`) - Chunk size

:::{rubric} Returns
:class: rubric-returns
:::
`list[list[Any]]` - List of chunks




:::{rubric} Examples
:class: rubric-examples
:::
```python
{% for row in items | chunk(3) %}
```


---
