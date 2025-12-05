
---
title: "strings"
type: "python-module"
source_file: "bengal/bengal/rendering/template_functions/strings.py"
line_number: 1
description: "String manipulation functions for templates. Provides 10 essential string functions for text processing in templates. Many of these functions are now thin wrappers around bengal.utils.text utilities t..."
---

# strings
**Type:** Module
**Source:** [View source](bengal/bengal/rendering/template_functions/strings.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[rendering](/api/bengal/rendering/) ›[template_functions](/api/bengal/rendering/template_functions/) ›strings

String manipulation functions for templates.

Provides 10 essential string functions for text processing in templates.

Many of these functions are now thin wrappers around bengal.utils.text utilities
to avoid code duplication and ensure consistency.

## Functions



### `register`


```python
def register(env: Environment, site: Site) -> None
```



Register string functions with Jinja2 environment.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `env` | `Environment` | - | *No description provided.* |
| `site` | `Site` | - | *No description provided.* |







**Returns**


`None`




### `dict_get`


```python
def dict_get(obj, key, default = None)
```



Safe get supporting dict-like objects for component preview contexts.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `obj` | - | - | *No description provided.* |
| `key` | - | - | *No description provided.* |
| `default` | - | - | *No description provided.* |









### `truncatewords`


```python
def truncatewords(text: str, count: int, suffix: str = '...') -> str
```



Truncate text to a specified number of words.

Uses bengal.utils.text.truncate_words internally.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | Text to truncate |
| `count` | `int` | - | Maximum number of words |
| `suffix` | `str` | `'...'` | Text to append when truncated (default: "...") |







**Returns**


`str` - Truncated text with suffix if needed
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ post.content | truncatewords(50) }}
    {{ post.content | truncatewords(30, " [Read more]") }}
```





### `truncatewords_html`


```python
def truncatewords_html(html: str, count: int, suffix: str = '...') -> str
```



Truncate HTML text to word count, preserving HTML tags.

This is more sophisticated than truncatewords - it preserves HTML structure
and properly closes tags.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `html` | `str` | - | HTML text to truncate |
| `count` | `int` | - | Maximum number of words |
| `suffix` | `str` | `'...'` | Text to append when truncated |







**Returns**


`str` - Truncated HTML with properly closed tags
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ post.html_content | truncatewords_html(50) }}
```





### `slugify`


```python
def slugify(text: str) -> str
```



Convert text to URL-safe slug.

Uses bengal.utils.text.slugify internally.
Converts to lowercase, removes special characters, replaces spaces with hyphens.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | Text to convert |







**Returns**


`str` - URL-safe slug
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ page.title | slugify }}  # "Hello World!" -> "hello-world"
```





### `markdownify`


```python
def markdownify(text: str) -> str
```



Render Markdown text to HTML.

Uses Python-Markdown with extensions for tables, code highlighting, etc.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | Markdown text |







**Returns**


`str` - Rendered HTML
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ markdown_text | markdownify | safe }}
```





### `strip_html`


```python
def strip_html(text: str) -> str
```



Remove all HTML tags from text.

Uses bengal.utils.text.strip_html internally.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | HTML text |







**Returns**


`str` - Text with HTML tags removed
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ post.html_content | strip_html }}
```





### `truncate_chars`


```python
def truncate_chars(text: str, length: int, suffix: str = '...') -> str
```



Truncate text to character length.

Uses bengal.utils.text.truncate_chars internally.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | Text to truncate |
| `length` | `int` | - | Maximum character length |
| `suffix` | `str` | `'...'` | Text to append when truncated |







**Returns**


`str` - Truncated text with suffix if needed
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ post.excerpt | truncate_chars(200) }}
```





### `replace_regex`


```python
def replace_regex(text: str, pattern: str, replacement: str) -> str
```



Replace text using regular expression.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | Text to search in |
| `pattern` | `str` | - | Regular expression pattern |
| `replacement` | `str` | - | Replacement text |







**Returns**


`str` - Text with replacements made
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ text | replace_regex('\d+', 'NUM') }}
```





### `pluralize`


```python
def pluralize(count: int, singular: str, plural: str | None = None) -> str
```



Return singular or plural form based on count.

Uses bengal.utils.text.pluralize internally.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `count` | `int` | - | Number to check |
| `singular` | `str` | - | Singular form |
| `plural` | `str \| None` | - | Plural form (default: singular + 's') |







**Returns**


`str` - Appropriate form based on count
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ posts | length }} {{ posts | length | pluralize('post', 'posts') }}
    {{ count | pluralize('item') }}  # auto-pluralizes to "items"
```





### `reading_time`


```python
def reading_time(text: str, wpm: int = 200) -> int
```



Calculate reading time in minutes.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | Text to analyze |
| `wpm` | `int` | `200` | Words per minute reading speed (default: 200) |







**Returns**


`int` - Reading time in minutes (minimum 1)
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ post.content | reading_time }} min read
    {{ post.content | reading_time(250) }} min read
```





### `excerpt`


```python
def excerpt(text: str, length: int = 200, respect_word_boundaries: bool = True) -> str
```



Extract excerpt from text, optionally respecting word boundaries.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | Text to excerpt from |
| `length` | `int` | `200` | Maximum length in characters |
| `respect_word_boundaries` | `bool` | `True` | Don't cut words in half (default: True) |







**Returns**


`str` - Excerpt with ellipsis if truncated
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ post.content | excerpt(200) }}
    {{ post.content | excerpt(150, false) }}  # Can cut words
```





### `strip_whitespace`


```python
def strip_whitespace(text: str) -> str
```



Remove extra whitespace (multiple spaces, newlines, tabs).

Uses bengal.utils.text.normalize_whitespace internally.
Replaces all whitespace sequences with a single space.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | Text to clean |







**Returns**


`str` - Text with normalized whitespace
:::{rubric} Examples
:class: rubric-examples
:::


```python
{{ messy_text | strip_whitespace }}
```



---
*Generated by Bengal autodoc from `bengal/bengal/rendering/template_functions/strings.py`*

