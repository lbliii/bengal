---
title: "template_functions.strings"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_functions/strings.py"
---

# template_functions.strings

String manipulation functions for templates.

Provides 10 essential string functions for text processing in templates.

**Source:** `../../bengal/rendering/template_functions/strings.py`

---


## Functions

### register

```python
def register(env: 'Environment', site: 'Site') -> None
```

Register string functions with Jinja2 environment.

**Parameters:**

- **env** (`'Environment'`)
- **site** (`'Site'`)

**Returns:** `None`





---
### truncatewords

```python
def truncatewords(text: str, count: int, suffix: str = '...') -> str
```

Truncate text to a specified number of words.

**Parameters:**

- **text** (`str`) - Text to truncate
- **count** (`int`) - Maximum number of words
- **suffix** (`str`) = `'...'` - Text to append when truncated (default: "...")

**Returns:** `str` - Truncated text with suffix if needed


**Examples:**

{{ post.content | truncatewords(50) }}




---
### truncatewords_html

```python
def truncatewords_html(html: str, count: int, suffix: str = '...') -> str
```

Truncate HTML text to word count, preserving HTML tags.

This is more sophisticated than truncatewords - it preserves HTML structure
and properly closes tags.

**Parameters:**

- **html** (`str`) - HTML text to truncate
- **count** (`int`) - Maximum number of words
- **suffix** (`str`) = `'...'` - Text to append when truncated

**Returns:** `str` - Truncated HTML with properly closed tags


**Examples:**

{{ post.html_content | truncatewords_html(50) }}




---
### slugify

```python
def slugify(text: str) -> str
```

Convert text to URL-safe slug.

Converts to lowercase, removes special characters, replaces spaces with hyphens.

**Parameters:**

- **text** (`str`) - Text to convert

**Returns:** `str` - URL-safe slug


**Examples:**

{{ page.title | slugify }}  # "Hello World!" -> "hello-world"




---
### markdownify

```python
def markdownify(text: str) -> str
```

Render Markdown text to HTML.

Uses Python-Markdown with extensions for tables, code highlighting, etc.

**Parameters:**

- **text** (`str`) - Markdown text

**Returns:** `str` - Rendered HTML


**Examples:**

{{ markdown_text | markdownify | safe }}




---
### strip_html

```python
def strip_html(text: str) -> str
```

Remove all HTML tags from text.

**Parameters:**

- **text** (`str`) - HTML text

**Returns:** `str` - Text with HTML tags removed


**Examples:**

{{ post.html_content | strip_html }}




---
### truncate_chars

```python
def truncate_chars(text: str, length: int, suffix: str = '...') -> str
```

Truncate text to character length.

**Parameters:**

- **text** (`str`) - Text to truncate
- **length** (`int`) - Maximum character length
- **suffix** (`str`) = `'...'` - Text to append when truncated

**Returns:** `str` - Truncated text with suffix if needed


**Examples:**

{{ post.excerpt | truncate_chars(200) }}




---
### replace_regex

```python
def replace_regex(text: str, pattern: str, replacement: str) -> str
```

Replace text using regular expression.

**Parameters:**

- **text** (`str`) - Text to search in
- **pattern** (`str`) - Regular expression pattern
- **replacement** (`str`) - Replacement text

**Returns:** `str` - Text with replacements made


**Examples:**

{{ text | replace_regex('\d+', 'NUM') }}




---
### pluralize

```python
def pluralize(count: int, singular: str, plural: Optional[str] = None) -> str
```

Return singular or plural form based on count.

**Parameters:**

- **count** (`int`) - Number to check
- **singular** (`str`) - Singular form
- **plural** (`Optional[str]`) = `None` - Plural form (default: singular + 's')

**Returns:** `str` - Appropriate form based on count


**Examples:**

{{ posts | length }} {{ posts | length | pluralize('post', 'posts') }}




---
### reading_time

```python
def reading_time(text: str, wpm: int = 200) -> int
```

Calculate reading time in minutes.

**Parameters:**

- **text** (`str`) - Text to analyze
- **wpm** (`int`) = `200` - Words per minute reading speed (default: 200)

**Returns:** `int` - Reading time in minutes (minimum 1)


**Examples:**

{{ post.content | reading_time }} min read




---
### excerpt

```python
def excerpt(text: str, length: int = 200, respect_word_boundaries: bool = True) -> str
```

Extract excerpt from text, optionally respecting word boundaries.

**Parameters:**

- **text** (`str`) - Text to excerpt from
- **length** (`int`) = `200` - Maximum length in characters
- **respect_word_boundaries** (`bool`) = `True` - Don't cut words in half (default: True)

**Returns:** `str` - Excerpt with ellipsis if truncated


**Examples:**

{{ post.content | excerpt(200) }}




---
### strip_whitespace

```python
def strip_whitespace(text: str) -> str
```

Remove extra whitespace (multiple spaces, newlines, tabs).

Replaces all whitespace sequences with a single space.

**Parameters:**

- **text** (`str`) - Text to clean

**Returns:** `str` - Text with normalized whitespace


**Examples:**

{{ messy_text | strip_whitespace }}




---
