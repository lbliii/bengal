
---
title: "template_functions.dates"
type: python-module
source_file: "bengal/rendering/template_functions/dates.py"
css_class: api-content
description: "Date and time functions for templates.  Provides 3 functions for date formatting and display."
---

# template_functions.dates

Date and time functions for templates.

Provides 3 functions for date formatting and display.

---


## Functions

### `register`
```python
def register(env: 'Environment', site: 'Site') -> None
```

Register date functions with Jinja2 environment.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 2 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `env`
  - `'Environment'`
  - -
  - -
* - `site`
  - `'Site'`
  - -
  - -
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
### `time_ago`
```python
def time_ago(date: datetime | str | None) -> str
```

Convert date to human-readable "time ago" format.

Uses bengal.utils.dates.time_ago internally for robust date handling.



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
* - `date`
  - `datetime | str | None`
  - -
  - Date to convert (datetime object or ISO string)
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - Human-readable time ago string




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ post.date | time_ago }}  # "2 days ago", "5 hours ago", etc.
```


---
### `date_iso`
```python
def date_iso(date: datetime | str | None) -> str
```

Format date as ISO 8601 string.

Uses bengal.utils.dates.format_date_iso internally for robust date handling.



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
* - `date`
  - `datetime | str | None`
  - -
  - Date to format
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - ISO 8601 formatted date string




:::{rubric} Examples
:class: rubric-examples
:::
```python
<time datetime="{{ post.date | date_iso }}">
```


---
### `date_rfc822`
```python
def date_rfc822(date: datetime | str | None) -> str
```

Format date as RFC 822 string (for RSS feeds).

Uses bengal.utils.dates.format_date_rfc822 internally for robust date handling.



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
* - `date`
  - `datetime | str | None`
  - -
  - Date to format
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - RFC 822 formatted date string




:::{rubric} Examples
:class: rubric-examples
:::
```python
<pubDate>{{ post.date | date_rfc822 }}</pubDate>
```


---
