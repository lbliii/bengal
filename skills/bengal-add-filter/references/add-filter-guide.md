# Bengal Add Filter Reference

## Registration

Filter registration requires access to the template engine. Options:

1. **Custom build script** — Load site, register filters, then build (recommended)
2. **Internal API** — `site._template_engine._env.add_filter()` (may change)

## coerce_int

```python
from bengal.config.utils import coerce_int

def my_filter(text: str, count: int = 30) -> str:
    count = coerce_int(count, 30)
    # ...
```

## @template_safe

For functions that may receive invalid types from YAML/config:

```python
from bengal.rendering.utils.template_safe import template_safe

@template_safe(default="")
def format_date(value: str, fmt: str = "%Y-%m-%d") -> str:
    return datetime.strptime(value, fmt).strftime(fmt)
```

## Full Docs

See `site/content/docs/theming/templating/kida/add-custom-filter.md` in Bengal repo.
