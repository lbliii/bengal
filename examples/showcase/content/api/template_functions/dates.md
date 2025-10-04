---
title: "template_functions.dates"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/template_functions/dates.py"
---

# template_functions.dates

Date and time functions for templates.

Provides 3 functions for date formatting and display.

**Source:** `../../bengal/rendering/template_functions/dates.py`

---


## Functions

### register

```python
def register(env: 'Environment', site: 'Site') -> None
```

Register date functions with Jinja2 environment.

**Parameters:**

- **env** (`'Environment'`)
- **site** (`'Site'`)

**Returns:** `None`





---
### time_ago

```python
def time_ago(date: Union[datetime, str, None]) -> str
```

Convert date to human-readable "time ago" format.

**Parameters:**

- **date** (`Union[datetime, str, None]`) - Date to convert (datetime object or ISO string)

**Returns:** `str` - Human-readable time ago string


**Examples:**

{{ post.date | time_ago }}  # "2 days ago", "5 hours ago", etc.




---
### date_iso

```python
def date_iso(date: Union[datetime, str, None]) -> str
```

Format date as ISO 8601 string.

**Parameters:**

- **date** (`Union[datetime, str, None]`) - Date to format

**Returns:** `str` - ISO 8601 formatted date string


**Examples:**

<time datetime="{{ post.date | date_iso }}">




---
### date_rfc822

```python
def date_rfc822(date: Union[datetime, str, None]) -> str
```

Format date as RFC 822 string (for RSS feeds).

**Parameters:**

- **date** (`Union[datetime, str, None]`) - Date to format

**Returns:** `str` - RFC 822 formatted date string


**Examples:**

<pubDate>{{ post.date | date_rfc822 }}</pubDate>




---
