
---
title: "fonts.generator"
type: python-module
source_file: "bengal/fonts/generator.py"
css_class: api-content
description: "Generate CSS for self-hosted fonts."
---

# fonts.generator

Generate CSS for self-hosted fonts.

---

## Classes

### `FontCSSGenerator`


Generates @font-face CSS for downloaded fonts.




:::{rubric} Methods
:class: rubric-methods
:::
#### `generate`
```python
def generate(self, font_mapping: dict[str, list[FontVariant]], font_path_prefix: str = '/fonts') -> str
```

Generate fonts.css content.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`font_mapping`** (`dict[str, list[FontVariant]]`) - Dict of font name -> list of variants
- **`font_path_prefix`** (`str`) = `'/fonts'` - URL prefix for font files

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Complete CSS content as string




---
