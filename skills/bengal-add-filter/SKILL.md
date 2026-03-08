---
name: bengal-add-filter
description: Adds a new Jinja/Kida filter to Bengal templates. Use when creating custom filters for formatting, filtering, or transforming template data.
---

# Bengal Add Filter

Add a custom filter to Bengal's Kida template engine.

## Procedure

### Step 1: Create Filter Function

```python
# python/filters.py

def currency(value: float, symbol: str = "$") -> str:
    """Format a number as currency."""
    if value is None:
        return f"{symbol}0.00"
    return f"{symbol}{value:,.2f}"
```

### Step 2: Type Coercion for Numeric Params

Values from YAML/config can arrive as strings. Coerce numeric params:

```python
from bengal.config.utils import coerce_int

def truncate_words(value: str, length: int = 50, suffix: str = "...") -> str:
    length = coerce_int(length, 50)  # Coerce from YAML string
    if not value:
        return ""
    words = value.split()
    if len(words) <= length:
        return value
    return " ".join(words[:length]) + suffix
```

### Step 3: Register Filter

Uses internal API (may change; plugin API planned for v0.4.0):

```python
# python/filter_registration.py

def register_filters(site) -> None:
    if hasattr(site, '_template_engine') and site._template_engine:
        env = site._template_engine._env
        env.add_filter("currency", currency)
        env.add_filter("truncate_words", truncate_words)
```

### Step 4: Call During Build

Use a custom build script:

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

### Step 5: Use in Templates

```kida
{{ 1234.56 | currency }}
{{ 1234.56 | currency("€") }}
{{ page.content | truncate_words(20) }}
```

## Type Coercion Rules

- **Numeric params** (int, float): Use `coerce_int(value, default)` at filter entry
- **YAML/config values**: Can be str; filters must handle or coerce
- **Avoid** arithmetic on raw config/frontmatter values

## Checklist

- [ ] Filter function with clear signature
- [ ] coerce_int() for numeric params from YAML
- [ ] env.add_filter() in registration
- [ ] Call register_filters before build
- [ ] Test with values from frontmatter (may be str)

## Additional Resources

See [references/add-filter-guide.md](references/add-filter-guide.md) for build script options and @template_safe for error-prone functions.
