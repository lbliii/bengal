
---
title: "template_functions.content"
type: python-module
source_file: "bengal/rendering/template_functions/content.py"
css_class: api-content
description: "Content transformation functions for templates.  Provides 6 functions for HTML/content manipulation and transformation."
---

# template_functions.content

Content transformation functions for templates.

Provides 6 functions for HTML/content manipulation and transformation.

---


## Functions

### `register`
```python
def register(env: 'Environment', site: 'Site') -> None
```

Register content transformation functions with Jinja2 environment.



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
### `safe_html`
```python
def safe_html(text: str) -> str
```

Mark HTML as safe (prevents auto-escaping).

This is a marker function - Jinja2's 'safe' filter should be used instead.
Included for compatibility with other SSGs.



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
* - `text`
  - `str`
  - -
  - HTML text to mark as safe
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - Same text (use with Jinja2's |safe filter)




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ content | safe_html | safe }}
```


---
### `html_escape`
```python
def html_escape(text: str) -> str
```

Escape HTML entities.

Converts special characters to HTML entities:
- < becomes &lt;
- > becomes &gt;
- & becomes &amp;
- " becomes &quot;
- ' becomes &#x27;



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
* - `text`
  - `str`
  - -
  - Text to escape
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - Escaped HTML text




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ user_input | html_escape }}
```


---
### `html_unescape`
```python
def html_unescape(text: str) -> str
```

Unescape HTML entities.

Converts HTML entities back to characters:
- &lt; becomes <
- &gt; becomes >
- &amp; becomes &
- &quot; becomes "



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
* - `text`
  - `str`
  - -
  - HTML text with entities
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - Unescaped text




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ escaped_text | html_unescape }}
```


---
### `nl2br`
```python
def nl2br(text: str) -> str
```

Convert newlines to HTML <br> tags.

    Replaces 
 with <br>
 to preserve both HTML and text formatting.



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
* - `text`
  - `str`
  - -
  - Text with newlines
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - HTML with <br> tags




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ text | nl2br | safe }}
```


---
### `smartquotes`
```python
def smartquotes(text: str) -> str
```

Convert straight quotes to smart (curly) quotes.

Converts:
- " to " and "
- ' to ' and '
- -- to –
- --- to —



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
* - `text`
  - `str`
  - -
  - Text with straight quotes
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - Text with smart quotes




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ text | smartquotes }}
```


---
### `emojify`
```python
def emojify(text: str) -> str
```

Convert emoji shortcodes to Unicode emoji.

Converts :emoji_name: to actual emoji characters.



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
* - `text`
  - `str`
  - -
  - Text with emoji shortcodes
:::

::::
:::{rubric} Returns
:class: rubric-returns
:::
`str` - Text with Unicode emoji




:::{rubric} Examples
:class: rubric-examples
:::
```python
{{ text | emojify }}
```


---
