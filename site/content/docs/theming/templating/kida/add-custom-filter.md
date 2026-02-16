---
title: Add a Custom Filter
nav_title: Custom Filter
description: Extend Kida with your own template filters
weight: 20
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

Learn how to create and register custom filters for Kida templates in Bengal.

## Goal

Create a custom filter that formats currency values and use it in templates.

:::{note}
**Filters vs Functions:** This guide covers **filters** (transform values with `|`). For **functions** (standalone operations), see Add Custom Functions (coming soon).

**Quick distinction:**
- **Filter**: `{{ value | my_filter }}` → transforms `value`
- **Function**: `{{ my_function() }}` → performs operation
:::

## Prerequisites

- Bengal site initialized
- Kida enabled in `bengal.toml`
- Python knowledge

:::{steps}
:::{step} Create Filter Function

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

:::{/step}
:::{step} Register Filter

Create a registration function to add your filter to the template environment:

```bash
mkdir -p python
touch python/filter_registration.py
```

Register the filter:

```python
# python/filter_registration.py
from bengal.core import Site
from .filters import currency

def register_filters(site: Site) -> None:
    """Register custom Kida filters.

    Note: This uses internal APIs that may change in future versions.
    A stable plugin API is planned for v0.4.0.
    """
    # Access the template engine environment
    # The template engine is created during the build process
    if hasattr(site, '_template_engine') and site._template_engine:
        env = site._template_engine._env
        env.add_filter("currency", currency)
```

:::{/step}
:::{step} Call Registration Function

You need to call this function during the build process. Currently, this requires accessing internal APIs. Two approaches:

**Option A: Programmatic Build (Recommended)**

Create a custom build script that calls your registration function:

```python
# build.py
from pathlib import Path
from bengal.core import Site
from bengal.orchestration.build import BuildOptions
from python.filter_registration import register_filters

# Load site
site = Site.from_config(Path("."))

# Register filters before building
register_filters(site)

# Build site
options = BuildOptions()
site.build(options)
```

**Option B: Internal API Access (Advanced)**

:::{caution}
This approach uses internal APIs (`site._template_engine`) that may change. Use with caution and test after Bengal updates.
:::

If you need to register filters during the build process, you can access the template engine after it's created. The template engine is typically available during the rendering phase of the build.

:::{/step}
:::{step} Use Filter in Template

Use your custom filter in templates:

```kida
{{ 1234.56 | currency }}
{# Output: $1,234.56 #}

{{ 1234.56 | currency("€") }}
{# Output: €1,234.56 #}

{{ product.price | currency }}
{# Output: $29.99 #}
```

:::{/step}
:::{/steps}

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
# python/filter_registration.py
from bengal.core import Site
from .filters import truncate_words

def register_filters(site: Site) -> None:
    """Register custom Kida filters."""
    if hasattr(site, '_template_engine') and site._template_engine:
        env = site._template_engine._env
        env.add_filter("truncate_words", truncate_words)
```

```kida
{{ page.content | truncate_words(20, "...") }}
```

### Filter with Context Access

Filters can access template context if needed:

```python
# python/filters.py
def relative_date(value, context=None):
    """Format date relative to current date.

    Args:
        value: Date to format
        context: Template context (optional, if provided by template engine)

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
# python/filter_registration.py
from bengal.core import Site
from .filters import relative_date

def register_filters(site: Site) -> None:
    """Register custom Kida filters."""
    if hasattr(site, '_template_engine') and site._template_engine:
        env = site._template_engine._env
        # Note: Context passing depends on filter implementation
        # Kida passes context when filters accept it as a parameter
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
# python/filter_registration.py
from bengal.core import Site
from .filters import where_contains

def register_filters(site: Site) -> None:
    """Register custom Kida filters."""
    if hasattr(site, '_template_engine') and site._template_engine:
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
# python/filter_registration.py
from bengal.core import Site

def register_filters(site: Site) -> None:
    """Register all custom filters."""
    if hasattr(site, '_template_engine') and site._template_engine:
        env = site._template_engine._env

        @env.filter()
        def currency(value: float, symbol: str = "$") -> str:
            """Format a number as currency."""
            return f"{symbol}{value:,.2f}"

        @env.filter()
        def truncate_words(value: str, length: int = 50) -> str:
            """Truncate text to a specific word count."""
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
6. **API access**: Use `env.add_filter()` method (preferred) over `env.filters['name'] = func`

## Troubleshooting

### Filter Not Found

If your filter isn't available in templates:

:::{dropdown} Check registration timing
:icon: clock

Ensure `register_filters()` is called before templates are rendered.
:::

:::{dropdown} Verify template engine
:icon: gear

Confirm `site._template_engine` exists and has `_env` attribute.
:::

:::{dropdown} Check filter name
:icon: tag

Filter names are case-sensitive and must match exactly.
:::

### Template Engine Not Available

If `site._template_engine` is `None`:

- The template engine is created during the rendering phase
- Ensure you're calling `register_filters()` after the engine is initialized
- Consider using a custom build script that registers filters before building

### Context Not Passed to Filters

Kida doesn't automatically inject context into filters. If you need template context:

:::{dropdown} Accept context parameter
:icon: plug

Accept `context=None` as a parameter in your filter function.
:::

:::{dropdown} Access context variables
:icon: database

Access context variables through the context parameter when provided.
:::

:::{dropdown} Note context behavior
:icon: info

Context passing behavior may vary depending on how the filter is called.
:::

:::{caution}
**Internal API Usage**: Accessing `site._template_engine._env` uses internal APIs that may change in future versions. A stable plugin API for filter registration is planned for v0.4.0. Test your filter registration after Bengal updates.
:::

## Complete Example

```python
# python/filters.py
"""Custom Kida template filters."""

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
# python/filter_registration.py
"""Filter registration for custom Kida filters."""
from bengal.core import Site
from .filters import currency, truncate_words, relative_date

def register_filters(site: Site) -> None:
    """Register custom Kida filters.

    Call this function before building your site to register all custom filters.
    """
    if hasattr(site, '_template_engine') and site._template_engine:
        env = site._template_engine._env
        env.add_filter("currency", currency)
        env.add_filter("truncate_words", truncate_words)
        env.add_filter("relative_date", relative_date)
```

**Using in a build script:**

```python
# build.py
from pathlib import Path
from bengal.core import Site
from bengal.orchestration.build import BuildOptions
from python.filter_registration import register_filters

site = Site.from_config(Path("."))
register_filters(site)
site.build(BuildOptions())
```

## Next Steps

- [Use Pipeline Operator](/docs/theming/templating/kida/syntax/operators/#pipeline-operator) — Chain filters together
- [Create Custom Template](/docs/theming/templating/kida/create-custom-template/) — Build templates with your filters
- [Kida Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation

:::{seealso}
- [Template Functions Reference](/docs/reference/template-functions/) — Built-in filters
- [Build Hooks](/docs/extending/build-hooks/) — More customization options
:::
