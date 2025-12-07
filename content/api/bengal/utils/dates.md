
---
title: "dates"
type: "python-module"
source_file: "bengal/utils/dates.py"
line_number: 1
description: "Date and time utilities for Bengal SSG. Provides centralized date parsing, formatting, and manipulation functions to eliminate duplicate logic across templates and core code."
---

# dates
**Type:** Module
**Source:** [View source](bengal/utils/dates.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[utils](/api/bengal/utils/) ›dates

Date and time utilities for Bengal SSG.

Provides centralized date parsing, formatting, and manipulation functions
to eliminate duplicate logic across templates and core code.

## Functions



### `parse_date`


```python
def parse_date(value: DateLike, formats: list[str] | None = None, on_error: str = 'return_none') -> datetime | None
```



Parse various date formats into datetime.

Handles:
- datetime objects (pass through)
- date objects (convert to datetime at midnight)
- ISO 8601 strings (with or without timezone)
- Custom format strings


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `value` | `DateLike` | - | Date value in various formats |
| `formats` | `list[str] \| None` | - | Optional list of strptime format strings to try |
| `on_error` | `str` | `'return_none'` | How to handle parse errors: - 'return_none': Return None (default) - 'raise': Raise ValueError - 'return_original': Return original value as-is |







**Returns**


`datetime | None` - datetime object or None if parsing fails
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> parse_date("2025-10-09")
    datetime(2025, 10, 9, 0, 0)
    >>> parse_date("2025-10-09T14:30:00Z")
    datetime(2025, 10, 9, 14, 30, tzinfo=...)
    >>> parse_date(datetime.now())
    datetime(...)
```





### `format_date_iso`


```python
def format_date_iso(date: DateLike) -> str
```



Format date as ISO 8601 string.

Uses parse_date internally for flexible input handling.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `date` | `DateLike` | - | Date value in various formats |







**Returns**


`str` - ISO 8601 formatted string (YYYY-MM-DDTHH:MM:SS)
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> format_date_iso(datetime(2025, 10, 9, 14, 30))
    '2025-10-09T14:30:00'
    >>> format_date_iso("2025-10-09")
    '2025-10-09T00:00:00'
```





### `format_date_rfc822`


```python
def format_date_rfc822(date: DateLike) -> str
```



Format date as RFC 822 string (for RSS feeds).

Uses parse_date internally for flexible input handling.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `date` | `DateLike` | - | Date value in various formats |







**Returns**


`str` - RFC 822 formatted string (e.g., "Fri, 03 Oct 2025 14:30:00 +0000")
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> format_date_rfc822(datetime(2025, 10, 9, 14, 30))
    'Thu, 09 Oct 2025 14:30:00 '
```





### `format_date_human`


```python
def format_date_human(date: DateLike, format: str = '%B %d, %Y') -> str
```



Format date in human-readable format.

Uses parse_date internally for flexible input handling.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `date` | `DateLike` | - | Date value in various formats |
| `format` | `str` | `'%B %d, %Y'` | strftime format string (default: "October 09, 2025") |







**Returns**


`str` - Formatted date string
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> format_date_human(datetime(2025, 10, 9))
    'October 09, 2025'
    >>> format_date_human("2025-10-09", format='%Y-%m-%d')
    '2025-10-09'
```





### `time_ago`


```python
def time_ago(date: DateLike, now: datetime | None = None) -> str
```



Convert date to human-readable "time ago" format.

Uses parse_date internally for flexible input handling.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `date` | `DateLike` | - | Date to convert |
| `now` | `datetime \| None` | - | Current time (defaults to datetime.now()) |







**Returns**


`str` - Human-readable time ago string
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> time_ago(datetime.now() - timedelta(minutes=5))
    '5 minutes ago'
    >>> time_ago(datetime.now() - timedelta(days=2))
    '2 days ago'
    >>> time_ago("2025-10-01")
    '8 days ago'
```





### `get_current_year`


```python
def get_current_year() -> int
```



Get current year as integer.

Useful for copyright notices and templates.



**Returns**


`int` - Current year
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> get_current_year()
    2025
```





### `is_recent`


```python
def is_recent(date: DateLike, days: int = 7, now: datetime | None = None) -> bool
```



Check if date is recent (within specified days).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `date` | `DateLike` | - | Date to check |
| `days` | `int` | `7` | Number of days to consider "recent" (default: 7) |
| `now` | `datetime \| None` | - | Current time (defaults to datetime.now()) |







**Returns**


`bool` - True if date is within the last N days
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> is_recent(datetime.now() - timedelta(days=3))
    True
    >>> is_recent("2025-01-01", days=7)
    False
```





### `date_range_overlap`


```python
def date_range_overlap(start1: DateLike, end1: DateLike, start2: DateLike, end2: DateLike) -> bool
```



Check if two date ranges overlap.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `start1` | `DateLike` | - | Start of first range |
| `end1` | `DateLike` | - | End of first range |
| `start2` | `DateLike` | - | Start of second range |
| `end2` | `DateLike` | - | End of second range |







**Returns**


`bool` - True if ranges overlap
:::{rubric} Examples
:class: rubric-examples
:::


```python
>>> date_range_overlap("2025-01-01", "2025-01-10", "2025-01-05", "2025-01-15")
    True
    >>> date_range_overlap("2025-01-01", "2025-01-10", "2025-01-15", "2025-01-20")
    False
```





### `utc_now`


```python
def utc_now() -> datetime
```



Get current UTC datetime (low-level primitive).



**Returns**


`datetime`




### `iso_timestamp`


```python
def iso_timestamp(dt: datetime | None = None) -> str
```



Get ISO 8601 timestamp from datetime (UTC).


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `dt` | `datetime \| None` | - | *No description provided.* |







**Returns**


`str`



---
*Generated by Bengal autodoc from `bengal/utils/dates.py`*

