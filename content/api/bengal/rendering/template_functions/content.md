
---
title: "content"
type: "python-module"
source_file: "bengal/rendering/template_functions/content.py"
line_number: 1
description: "Content transformation functions for templates. Provides 6 functions for HTML/content manipulation and transformation."
---

# content
**Type:** Module
**Source:** [View source](bengal/rendering/template_functions/content.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[rendering](/api/bengal/rendering/) ›[template_functions](/api/bengal/rendering/template_functions/) ›content

Content transformation functions for templates.

Provides 6 functions for HTML/content manipulation and transformation.

## Functions



### `register`


```python
def register(env: Environment, site: Site) -> None
```



Register content transformation functions with Jinja2 environment.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `env` | `Environment` | - | *No description provided.* |
| `site` | `Site` | - | *No description provided.* |







**Returns**


`None`




### `safe_html`


```python
def safe_html(text: str) -> str
```



Mark HTML as safe (prevents auto-escaping).

This is a marker function - Jinja2's 'safe' filter should be used instead.
Included for compatibility with other SSGs.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | HTML text to mark as safe |







**Returns**


`str` - Same text (use with Jinja2's |safe filter)
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ content | safe_html | safe }}
```





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


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | Text to escape |







**Returns**


`str` - Escaped HTML text
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ user_input | html_escape }}
    # "<script>" becomes "&lt;script&gt;"
```





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


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | HTML text with entities |







**Returns**


`str` - Unescaped text
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ escaped_text | html_unescape }}
    # "&lt;Hello&gt;" becomes "<Hello>"
```





### `nl2br`


```python
def nl2br(text: str) -> str
```



Convert newlines to HTML <br> tags.

    Replaces 
 with <br>
 to preserve both HTML and text formatting.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | Text with newlines |







**Returns**


`str` - HTML with <br> tags
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ text | nl2br | safe }}
        # "Line 1
Line 2" becomes "Line 1<br>
Line 2"
```





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


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | Text with straight quotes |







**Returns**


`str` - Text with smart quotes
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ text | smartquotes }}
    # "Hello" becomes "Hello"
```





### `emojify`


```python
def emojify(text: str) -> str
```



Convert emoji shortcodes to Unicode emoji.

Converts :emoji_name: to actual emoji characters.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | Text with emoji shortcodes |







**Returns**


`str` - Text with Unicode emoji
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ text | emojify }}
    # "Hello :smile:" becomes "Hello 😊"
    # "I :heart: Python" becomes "I ❤️ Python"
```





### `extract_content`


```python
def extract_content(html: str) -> str
```



Extract content portion from full rendered HTML page.

Removes the page wrapper (html, head, body, navigation, footer) and
extracts just the main content area. This is useful for embedding
page content within other pages (e.g., track pages).

Tries multiple strategies to find content:
1. Look for <article class="prose"> or <div class="docs-content">
2. Look for <main> content (excluding nav/footer)
3. Fall back to empty string if no content area found


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `html` | `str` | - | Full rendered HTML page |







**Returns**


`str` - Extracted content HTML (or empty string if extraction fails)
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ page.rendered_html | extract_content | safe }}
```



---
*Generated by Bengal autodoc from `bengal/rendering/template_functions/content.py`*

