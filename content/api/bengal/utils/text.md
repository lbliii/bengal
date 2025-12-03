
---
title: "text"
type: "python-module"
source_file: "bengal/bengal/utils/text.py"
line_number: 1
description: "Text processing utilities. Provides canonical implementations for common text operations like slugification, HTML stripping, truncation, and excerpt generation. These utilities consolidate duplicate i..."
---

# text
**Type:** Module
**Source:** [View source](bengal/bengal/utils/text.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[utils](/api/bengal/utils/) ›text

Text processing utilities.

Provides canonical implementations for common text operations like slugification,
HTML stripping, truncation, and excerpt generation. These utilities consolidate
duplicate implementations found throughout the codebase.

Example:
    from bengal.utils.text import slugify, strip_html, truncate_words

    slug = slugify("Hello World!")  # "hello-world"
    text = strip_html("<p>Hello</p>")  # "Hello"
    excerpt = truncate_words("Long text here...", 10)

## Functions



### `slugify`


```python
def slugify(text: str, unescape_html: bool = True, max_length: int | None = None, separator: str = '-') -> str
```



Convert text to URL-safe slug with Unicode support.

Preserves Unicode word characters (letters, digits, underscore) to support
international content. Modern web browsers and servers handle Unicode URLs.

Consolidates implementations from:
- bengal/rendering/parser.py:629 (_slugify)
- bengal/rendering/template_functions/strings.py:92 (slugify)
- bengal/rendering/template_functions/taxonomies.py:184 (tag_url pattern)


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | Text to slugify |
| `unescape_html` | `bool` | `True` | Whether to decode HTML entities first (e.g., &amp; -> &) |
| `max_length` | `int \| None` | - | Maximum slug length (None = unlimited) |
| `separator` | `str` | `'-'` | Character to use between words (default: '-') |







**Returns**


`str` - URL-safe slug (lowercase, with Unicode word chars and separators)
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> slugify("Hello World!")
    'hello-world'
    >>> slugify("Test & Code")
    'test-code'
    >>> slugify("Test &amp; Code", unescape_html=True)
    'test-code'
    >>> slugify("Very Long Title Here", max_length=10)
    'very-long'
    >>> slugify("hello_world", separator='_')
    'hello_world'
    >>> slugify("你好世界")
    '你好世界'
    >>> slugify("Café")
    'café'
```

:::{note}Uses Python's \w regex pattern which includes Unicode letters and digits. This is intentional to support international content in URLs.:::





### `strip_html`


```python
def strip_html(text: str, decode_entities: bool = True) -> str
```



Remove all HTML tags from text.

Consolidates implementation from:
- bengal/rendering/template_functions/strings.py:157 (strip_html)


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | HTML text to clean |
| `decode_entities` | `bool` | `True` | Whether to decode HTML entities (e.g., &lt; -> <) |







**Returns**


`str` - Plain text with HTML tags removed
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> strip_html("<p>Hello <strong>World</strong></p>")
    'Hello World'
    >>> strip_html("&lt;script&gt;", decode_entities=True)
    '<script>'
    >>> strip_html("&lt;script&gt;", decode_entities=False)
    '&lt;script&gt;'
```





### `truncate_words`


```python
def truncate_words(text: str, word_count: int, suffix: str = '...') -> str
```



Truncate text to specified word count.

Consolidates pattern from:
- bengal/rendering/template_functions/strings.py (truncatewords)


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | Text to truncate |
| `word_count` | `int` | - | Maximum number of words |
| `suffix` | `str` | `'...'` | Suffix to append if truncated |







**Returns**


`str` - Truncated text with suffix if shortened
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> truncate_words("The quick brown fox jumps", 3)
    'The quick brown...'
    >>> truncate_words("Short text", 10)
    'Short text'
    >>> truncate_words("One two three four", 3, suffix="…")
    'One two three…'
```





### `truncate_chars`


```python
def truncate_chars(text: str, length: int, suffix: str = '...') -> str
```



Truncate text to specified character length (including suffix).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | Text to truncate |
| `length` | `int` | - | Maximum total length (including suffix if truncated) |
| `suffix` | `str` | `'...'` | Suffix to append if truncated |







**Returns**


`str` - Truncated text with suffix if shortened, never exceeding length
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> truncate_chars("Hello World", 8)
    'Hello...'
    >>> truncate_chars("Short", 10)
    'Short'
    >>> truncate_chars("0123456789", 10)
    '0123456...'
```





### `truncate_middle`


```python
def truncate_middle(text: str, max_length: int, separator: str = '...') -> str
```



Truncate text in the middle (useful for file paths).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | Text to truncate |
| `max_length` | `int` | - | Maximum total length |
| `separator` | `str` | `'...'` | Separator to use in middle |







**Returns**


`str` - Truncated text with separator in middle
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> truncate_middle('/very/long/path/to/file.txt', 20)
    '/very/.../file.txt'
    >>> truncate_middle('short.txt', 20)
    'short.txt'
```





### `generate_excerpt`


```python
def generate_excerpt(html: str, word_count: int = 50, suffix: str = '...') -> str
```



Generate plain text excerpt from HTML content.

Combines strip_html and truncate_words for common use case.
Consolidates pattern from:
- bengal/postprocess/output_formats.py:674
- Various template functions


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `html` | `str` | - | HTML content |
| `word_count` | `int` | `50` | Maximum number of words |
| `suffix` | `str` | `'...'` | Suffix to append if truncated |







**Returns**


`str` - Plain text excerpt
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> generate_excerpt("<p>Hello <strong>World</strong> from Bengal</p>", 2)
    'Hello World...'
```





### `normalize_whitespace`


```python
def normalize_whitespace(text: str, collapse: bool = True) -> str
```



Normalize whitespace in text.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `text` | `str` | - | Text to normalize |
| `collapse` | `bool` | `True` | Whether to collapse multiple spaces to single space |







**Returns**


`str` - Text with normalized whitespace
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> normalize_whitespace("  hello   world  ")
    'hello world'
    >>> normalize_whitespace("line1\n\n\nline2", collapse=True)
    'line1 line2'
```





### `escape_html`


```python
def escape_html(text: str) -> str
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


`str` - HTML-escaped text
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> escape_html("<script>alert('xss')</script>")
    "&lt;script&gt;alert('xss')&lt;/script&gt;"
```





### `unescape_html`


```python
def unescape_html(text: str) -> str
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
>>> unescape_html("&lt;Hello&gt;")
    '<Hello>'
```





### `pluralize`


```python
def pluralize(count: int, singular: str, plural: str | None = None) -> str
```



Return singular or plural form based on count.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `count` | `int` | - | Count value |
| `singular` | `str` | - | Singular form |
| `plural` | `str \| None` | - | Plural form (default: singular + 's') |







**Returns**


`str` - Appropriate form for the count
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> pluralize(1, 'page')
    'page'
    >>> pluralize(2, 'page')
    'pages'
    >>> pluralize(2, 'box', 'boxes')
    'boxes'
    >>> pluralize(0, 'item')
    'items'
```





### `humanize_bytes`


```python
def humanize_bytes(size_bytes: int) -> str
```



Format bytes as human-readable string.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `size_bytes` | `int` | - | Size in bytes |







**Returns**


`str` - Human-readable string (e.g., "1.5 KB", "2.3 MB")
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> humanize_bytes(1024)
    '1.0 KB'
    >>> humanize_bytes(1536)
    '1.5 KB'
    >>> humanize_bytes(1048576)
    '1.0 MB'
```





### `humanize_number`


```python
def humanize_number(num: int) -> str
```



Format number with thousand separators.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `num` | `int` | - | Number to format |







**Returns**


`str` - Formatted string with commas
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> humanize_number(1234567)
    '1,234,567'
    >>> humanize_number(1000)
    '1,000'
```



---
*Generated by Bengal autodoc from `bengal/bengal/utils/text.py`*
