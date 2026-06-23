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
aliases:
  - /docs/theming/templating/kida/add-custom-filter/
aliases:
  - /docs/build-sites/customize/templating/kida/add-custom-filter/
  - /docs/theming/templating/kida/add-custom-filter/
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
:::{step} Register the Filter in a Plugin

Register filters through the supported [plugin API](/docs/build-sites/extend/plugins/).
A plugin implements the `Plugin` protocol and calls
`registry.add_template_filter()` in its `register()` method:

```python
# my_bengal_plugin/__init__.py
from bengal.plugins.protocol import Plugin
from bengal.plugins.registry import PluginRegistry

from .filters import currency


class MyFiltersPlugin(Plugin):
    name = "my-filters"
    version = "1.0.0"

    def register(self, registry: PluginRegistry) -> None:
        registry.add_template_filter("currency", currency)
```

`add_template_filter` is a stable, supported entry point: registered filters
are applied to every template environment during the build, and the frozen
registry is safe to share across parallel render workers.

:::{/step}
:::{step} Declare the Entry Point and Install

Expose the plugin through the `bengal.plugins` entry point group so Bengal
discovers it automatically:

```toml
# pyproject.toml
[project.entry-points."bengal.plugins"]
my-filters = "my_bengal_plugin:MyFiltersPlugin"
```

Install the plugin into the same environment as Bengal:

```bash
uv pip install -e ./my-bengal-plugin
```

On the next build, Bengal discovers the plugin and registers your filter — no
build script or internal-attribute access required. Verify it is picked up with:

```bash
bengal plugin list
bengal plugin info my-filters
```

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

Register it in your plugin:

```python
# my_bengal_plugin/__init__.py (inside register())
registry.add_template_filter("truncate_words", truncate_words)
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
# my_bengal_plugin/__init__.py (inside register())
# Kida passes template context when the filter accepts it as a parameter.
registry.add_template_filter("relative_date", relative_date)
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
# my_bengal_plugin/__init__.py (inside register())
registry.add_template_filter("where_contains", where_contains)
```

```kida
{% let matching_posts = site.pages
  |> where('type', 'blog')
  |> where_contains('title', 'python') %}
```

## Registering Multiple Filters

A single plugin can register any number of filters in one `register()` call:

```python
# my_bengal_plugin/__init__.py
from bengal.plugins.protocol import Plugin
from bengal.plugins.registry import PluginRegistry

from .filters import currency, truncate_words, where_contains


class MyFiltersPlugin(Plugin):
    name = "my-filters"
    version = "1.0.0"

    def register(self, registry: PluginRegistry) -> None:
        registry.add_template_filter("currency", currency)
        registry.add_template_filter("truncate_words", truncate_words)
        registry.add_template_filter("where_contains", where_contains)
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
6. **Registration**: Register filters through a plugin's `registry.add_template_filter()` — the supported, thread-safe entry point

## Troubleshooting

### Filter Not Found

If your filter isn't available in templates:

:::{dropdown} Verify the plugin is discovered
:icon: search

Run `bengal plugin list` and `bengal plugin info <name>`. If your plugin is
missing, confirm it is installed in the same environment as Bengal and that the
`bengal.plugins` entry point in `pyproject.toml` points at your plugin class.
:::

:::{dropdown} Check the filter is registered
:icon: settings

Confirm `register()` calls `registry.add_template_filter("name", fn)` and that
`bengal plugin info <name>` reports a non-zero `template_filters` count.
:::

:::{dropdown} Check filter name
:icon: tag

Filter names are case-sensitive and must match the name passed to
`add_template_filter` exactly.
:::

### Plugin Not Discovered

If `bengal plugin list` does not show your plugin:

- Reinstall the plugin after editing `pyproject.toml`: `uv pip install -e ./my-bengal-plugin`
- Confirm the entry point group is exactly `bengal.plugins`
- Make sure the class implements `name`, `version`, and `register()`

### Context Not Passed to Filters

Kida doesn't automatically inject context into filters. If you need template context:

:::{dropdown} Accept context parameter
:icon: puzzle-piece

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

:::{tip}
**Supported API**: `registry.add_template_filter()` is the stable, supported way
to register filters. Avoid reaching into internal attributes such as
`site._template_engine._env` — those are private and may change between releases.
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
# my_bengal_plugin/__init__.py
"""Plugin that registers custom Kida filters."""
from bengal.plugins.protocol import Plugin
from bengal.plugins.registry import PluginRegistry

from .filters import currency, truncate_words, relative_date


class MyFiltersPlugin(Plugin):
    name = "my-filters"
    version = "1.0.0"

    def register(self, registry: PluginRegistry) -> None:
        registry.add_template_filter("currency", currency)
        registry.add_template_filter("truncate_words", truncate_words)
        registry.add_template_filter("relative_date", relative_date)
```

**Declaring the entry point:**

```toml
# pyproject.toml
[project.entry-points."bengal.plugins"]
my-filters = "my_bengal_plugin:MyFiltersPlugin"
```

Install the plugin and build — Bengal discovers it automatically and your
filters are available in every template:

```bash
uv pip install -e ./my-bengal-plugin
bengal build
```

## Next Steps

- [Use Pipeline Operator](/docs/build-sites/customize/templating/kida/syntax/operators/#pipeline-operator) — Chain filters together
- [Create Custom Template](/docs/build-sites/customize/templating/kida/create-custom-template/) — Build templates with your filters
- [Kida Syntax Reference](/docs/reference/kida-syntax/) — Complete syntax documentation

:::{seealso}
- [Template Functions Reference](/docs/reference/template-functions/) — Built-in filters
- [Writing Plugins](/docs/build-sites/extend/plugins/) — Full plugin authoring guide
:::
