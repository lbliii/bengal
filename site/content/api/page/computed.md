
---
title: "page.computed"
type: python-module
source_file: "bengal/core/page/computed.py"
css_class: api-content
description: "Page Computed Properties Mixin - Cached expensive computations."
---

# page.computed

Page Computed Properties Mixin - Cached expensive computations.

---

## Classes

### `PageComputedMixin`


Mixin providing cached computed properties for pages.

This mixin handles expensive operations that are cached after first access:
- meta_description - SEO-friendly description
- reading_time - Estimated reading time
- excerpt - Content excerpt



:::{rubric} Properties
:class: rubric-properties
:::
#### `meta_description` @property

```python
@property
def meta_description(self) -> str
```

Generate SEO-friendly meta description (computed once, cached).

Creates description by:
- Using explicit 'description' from metadata if available
- Otherwise generating from content by stripping HTML and truncating
- Attempting to end at sentence boundary for better readability

The result is cached after first access, so multiple template uses
(meta tag, og:description, twitter:description) only compute once.
#### `reading_time` @property

```python
@property
def reading_time(self) -> int
```

Calculate reading time in minutes (computed once, cached).

Estimates reading time based on word count at 200 words per minute.
Strips HTML before counting to ensure accurate word count.

The result is cached after first access for efficient repeated use.
#### `excerpt` @property

```python
@property
def excerpt(self) -> str
```

Extract content excerpt (computed once, cached).

Creates a 200-character excerpt from content by:
- Stripping HTML tags
- Truncating to length
- Respecting word boundaries (doesn't cut words in half)
- Adding ellipsis if truncated

The result is cached after first access for efficient repeated use.

:::{rubric} Methods
:class: rubric-methods
:::
#### `meta_description`
```python
def meta_description(self) -> str
```

Generate SEO-friendly meta description (computed once, cached).

Creates description by:
- Using explicit 'description' from metadata if available
- Otherwise generating from content by stripping HTML and truncating
- Attempting to end at sentence boundary for better readability

The result is cached after first access, so multiple template uses
(meta tag, og:description, twitter:description) only compute once.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str` - Meta description text (max 160 chars)




:::{rubric} Examples
:class: rubric-examples
:::
```python
<meta name="description" content="{{ page.meta_description }}">
```


---
#### `reading_time`
```python
def reading_time(self) -> int
```

Calculate reading time in minutes (computed once, cached).

Estimates reading time based on word count at 200 words per minute.
Strips HTML before counting to ensure accurate word count.

The result is cached after first access for efficient repeated use.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`int` - Reading time in minutes (minimum 1)




:::{rubric} Examples
:class: rubric-examples
:::
```python
<span class="reading-time">{{ page.reading_time }} min read</span>
```


---
#### `excerpt`
```python
def excerpt(self) -> str
```

Extract content excerpt (computed once, cached).

Creates a 200-character excerpt from content by:
- Stripping HTML tags
- Truncating to length
- Respecting word boundaries (doesn't cut words in half)
- Adding ellipsis if truncated

The result is cached after first access for efficient repeated use.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`str` - Excerpt text with ellipsis if truncated




:::{rubric} Examples
:class: rubric-examples
:::
```python
<p class="excerpt">{{ page.excerpt }}</p>
```


---
