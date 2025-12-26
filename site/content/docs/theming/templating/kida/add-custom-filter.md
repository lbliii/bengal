---
title: Add a Custom Filter
nav_title: Custom Filter
description: Extend KIDA with your own template filters
weight: 20
type: doc
draft: false
lang: en
tags:
- how-to
- templates
- kida
- filters
keywords:
- custom filter
- kida filter
- template filter
category: guide
---

# Add a Custom Filter

Learn how to create and register custom filters for KIDA templates in Bengal.

## Goal

Create a custom filter that formats currency values and use it in templates.

## Prerequisites

- Bengal site initialized
- KIDA enabled in `bengal.yaml`
- Python knowledge

## Steps

### Step 1: Create Filter Function

Create a Python file for your filters:

```bash
mkdir -p python
touch python/filters.py
```

Define your filter function:

```python
# python/filters.py
def currency(value: float, symbol: str = "$") -> str:
    """Format a number as currency.
    
    Args:
        value: Numeric value to format
        symbol: Currency symbol (default: "$")
    
    Returns:
        Formatted string like "$1,234.56"
    """
    if value is None:
        return f"{symbol}0.00"
    return f"{symbol}{value:,.2f}"
```

### Step 2: Register Filter in Build Hook

Create a build hook to register your filter:

```bash
mkdir -p python
touch python/build_hooks.py
```

Register the filter:

```python
# python/build_hooks.py
from bengal.core import Site
from .filters import currency

def register_filters(site: Site) -> None:
    """Register custom KIDA filters."""
    # Get the KIDA environment from the template engine
    if hasattr(site, '_template_engine') and site._template_engine:
        env = site._template_engine._env
        env.add_filter("currency", currency)
```

### Step 3: Configure Build Hook

Add the build hook to `bengal.yaml`:

```yaml
build_hooks:
  - python.build_hooks.register_filters
```

### Step 4: Use Filter in Template

Use your custom filter in templates:

```kida
{{ 1234.56 | currency }}
{# Output: $1,234.56 #}

{{ 1234.56 | currency("€") }}
{# Output: €1,234.56 #}

{{ product.price | currency }}
{# Output: $29.99 #}
```

## Advanced Examples

### Filter with Multiple Arguments

```python
# python/filters.py
def truncate_words(value: str, length: int = 50, suffix: str = "...") -> str:
    """Truncate text to a specific word count.
    
    Args:
        value: Text to truncate
        length: Maximum word count
        suffix: Text to append if truncated
    
    Returns:
        Truncated text
    """
    if not value:
        return ""
    
    words = value.split()
    if len(words) <= length:
        return value
    
    return " ".join(words[:length]) + suffix
```

Register and use:

```python
# python/build_hooks.py
from .filters import truncate_words

def register_filters(site: Site) -> None:
    env = site._template_engine._env
    env.add_filter("truncate_words", truncate_words)
```

```kida
{{ page.content | truncate_words(20, "...") }}
```

### Filter with Context Access

Access template context in filters:

```python
# python/filters.py
def relative_date(value, context=None):
    """Format date relative to current date.
    
    Args:
        value: Date to format
        context: Template context (auto-injected)
    
    Returns:
        Relative date string like "2 days ago"
    """
    from datetime import datetime
    
    if not value:
        return ""
    
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    
    now = datetime.now()
    delta = now - value
    
    if delta.days == 0:
        return "Today"
    elif delta.days == 1:
        return "Yesterday"
    elif delta.days < 7:
        return f"{delta.days} days ago"
    elif delta.days < 30:
        weeks = delta.days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    else:
        months = delta.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
```

```python
# python/build_hooks.py
from .filters import relative_date

def register_filters(site: Site) -> None:
    env = site._template_engine._env
    # KIDA automatically passes context to filters
    env.add_filter("relative_date", relative_date)
```

```kida
{{ post.date | relative_date }}
{# Output: "2 days ago" #}
```

### Collection Filter

Create a filter that works on collections:

```python
# python/filters.py
def where_contains(items, key, value):
    """Filter items where key contains value.
    
    Args:
        items: List of dictionaries
        key: Key to check
        value: Value to search for
    
    Returns:
        Filtered list
    """
    if not items:
        return []
    
    return [
        item for item in items
        if value.lower() in str(item.get(key, "")).lower()
    ]
```

```python
# python/build_hooks.py
from .filters import where_contains

def register_filters(site: Site) -> None:
    env = site._template_engine._env
    env.add_filter("where_contains", where_contains)
```

```kida
{% let matching_posts = site.pages
  |> where('type', 'blog')
  |> where_contains('title', 'python') %}
```

## Using Decorator Syntax

You can also use decorator syntax for cleaner registration:

```python
# python/filters.py
from bengal.core import Site

def register_filters(site: Site) -> None:
    """Register all custom filters."""
    env = site._template_engine._env
    
    @env.filter()
    def currency(value: float, symbol: str = "$") -> str:
        return f"{symbol}{value:,.2f}"
    
    @env.filter()
    def truncate_words(value: str, length: int = 50) -> str:
        words = value.split()
        if len(words) <= length:
            return value
        return " ".join(words[:length]) + "..."
```

## Testing Filters

Test your filters:

```python
# python/test_filters.py
from .filters import currency, truncate_words

def test_currency():
    assert currency(1234.56) == "$1,234.56"
    assert currency(1234.56, "€") == "€1,234.56"
    assert currency(None) == "$0.00"

def test_truncate_words():
    text = "This is a very long text that needs to be truncated"
    result = truncate_words(text, 5)
    assert result == "This is a very long text..."
```

## Best Practices

1. **Type hints**: Always include type hints for clarity
2. **Docstrings**: Document parameters and return values
3. **None handling**: Handle None values gracefully
4. **Error handling**: Provide sensible defaults
5. **Naming**: Use descriptive, lowercase names with underscores

## Complete Example

```python
# python/filters.py
"""Custom KIDA template filters."""

def currency(value: float | None, symbol: str = "$") -> str:
    """Format a number as currency."""
    if value is None:
        return f"{symbol}0.00"
    return f"{symbol}{value:,.2f}"

def truncate_words(value: str | None, length: int = 50, suffix: str = "...") -> str:
    """Truncate text to a specific word count."""
    if not value:
        return ""
    
    words = value.split()
    if len(words) <= length:
        return value
    
    return " ".join(words[:length]) + suffix

def relative_date(value, context=None) -> str:
    """Format date relative to current date."""
    from datetime import datetime
    
    if not value:
        return ""
    
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    
    now = datetime.now()
    delta = now - value
    
    if delta.days == 0:
        return "Today"
    elif delta.days == 1:
        return "Yesterday"
    elif delta.days < 7:
        return f"{delta.days} days ago"
    else:
        weeks = delta.days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
```

```python
# python/build_hooks.py
"""Build hooks for custom filters."""
from bengal.core import Site
from .filters import currency, truncate_words, relative_date

def register_filters(site: Site) -> None:
    """Register custom KIDA filters."""
    if hasattr(site, '_template_engine') and site._template_engine:
        env = site._template_engine._env
        env.add_filter("currency", currency)
        env.add_filter("truncate_words", truncate_words)
        env.add_filter("relative_date", relative_date)
```

```yaml
# bengal.yaml
build_hooks:
  - python.build_hooks.register_filters
```

## Next Steps

- [Use Pipeline Operator](/docs/theming/templating/kida/use-pipeline-operator/) — Chain filters together
- [Create Custom Template](/docs/theming/templating/kida/create-custom-template/) — Build templates with your filters
- [KIDA Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation

:::{seealso}
- [Template Functions Reference](/docs/reference/template-functions/) — Built-in filters
- [Build Hooks](/docs/extending/build-hooks/) — More customization options
:::

