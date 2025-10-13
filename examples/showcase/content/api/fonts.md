
---
title: "fonts"
type: python-module
source_file: "bengal/fonts/__init__.py"
css_class: api-content
description: "Font helper for Bengal SSG.  Provides simple font downloading and CSS generation for Google Fonts.  Usage:     [fonts]     primary = "Inter:400,600,700"     heading = "Playfair Display:700" "
---

# fonts

Font helper for Bengal SSG.

Provides simple font downloading and CSS generation for Google Fonts.

Usage:
    # In bengal.toml:
    [fonts]
    primary = "Inter:400,600,700"
    heading = "Playfair Display:700"

    # Bengal automatically downloads fonts and generates CSS

---

## Classes

### `FontHelper`


Main font helper interface.

Usage:
    helper = FontHelper(config)
    helper.process(output_dir)




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, font_config: dict[str, Any])
```

Initialize font helper with configuration.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`font_config`** (`dict[str, Any]`) - [fonts] section from bengal.toml





---
#### `process`
```python
def process(self, assets_dir: Path) -> Path | None
```

Process fonts: download files and generate CSS.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`assets_dir`** (`Path`) - Assets directory (fonts go in assets/fonts/)

:::{rubric} Returns
:class: rubric-returns
:::
`Path | None` - Path to generated fonts.css, or None if no fonts configured




---
