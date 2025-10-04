---
title: "template_functions.content"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_functions/content.py"
---

# template_functions.content

Content transformation functions for templates.

Provides 6 functions for HTML/content manipulation and transformation.

**Source:** `../../bengal/rendering/template_functions/content.py`

---


## Functions

### register

```python
def register(env: 'Environment', site: 'Site') -> None
```

Register content transformation functions with Jinja2 environment.

**Parameters:**

- **env** (`'Environment'`)
- **site** (`'Site'`)

**Returns:** `None`





---
### safe_html

```python
def safe_html(text: str) -> str
```

Mark HTML as safe (prevents auto-escaping).

This is a marker function - Jinja2's 'safe' filter should be used instead.
Included for compatibility with other SSGs.

**Parameters:**

- **text** (`str`) - HTML text to mark as safe

**Returns:** `str` - Same text (use with Jinja2's |safe filter)


**Examples:**

{{ content | safe_html | safe }}




---
### html_escape

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

- **text** (`str`) - Text to escape

**Returns:** `str` - Escaped HTML text


**Examples:**

{{ user_input | html_escape }}




---
### html_unescape

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

- **text** (`str`) - HTML text with entities

**Returns:** `str` - Unescaped text


**Examples:**

{{ escaped_text | html_unescape }}




---
### nl2br

```python
def nl2br(text: str) -> str
```

Convert newlines to HTML <br> tags.
    
    Replaces 
 with <br>
 to preserve both HTML and text formatting.

**Parameters:**

- **text** (`str`) - Text with newlines

**Returns:** `str` - HTML with <br> tags


**Examples:**

{{ text | nl2br | safe }}




---
### smartquotes

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

- **text** (`str`) - Text with straight quotes

**Returns:** `str` - Text with smart quotes


**Examples:**

{{ text | smartquotes }}




---
### emojify

```python
def emojify(text: str) -> str
```

Convert emoji shortcodes to Unicode emoji.

Converts :emoji_name: to actual emoji characters.

**Parameters:**

- **text** (`str`) - Text with emoji shortcodes

**Returns:** `str` - Text with Unicode emoji


**Examples:**

{{ text | emojify }}




---
