
---
title: "server.request_logger"
type: python-module
source_file: "bengal/server/request_logger.py"
css_class: api-content
description: "Request logging utilities for the dev server.  Provides beautiful, minimal logging for HTTP requests with color-coded output."
---

# server.request_logger

Request logging utilities for the dev server.

Provides beautiful, minimal logging for HTTP requests with color-coded output.

---

## Classes

### `RequestLogger`


Mixin class providing beautiful, minimal logging for HTTP requests.

This class is designed to be mixed into an HTTP request handler.




:::{rubric} Methods
:class: rubric-methods
:::
#### `log_message`
```python
def log_message(self, format: str, *args: Any) -> None
```

Log an HTTP request with beautiful formatting.



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
* - `self`
  - -
  - -
  - -
* - `format`
  - `str`
  - -
  - Format string *args: Format arguments
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `log_error`
```python
def log_error(self, format: str, *args: Any) -> None
```

Suppress error logging - we handle everything in log_message.



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
* - `self`
  - -
  - -
  - -
* - `format`
  - `str`
  - -
  - Format string *args: Format arguments
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
