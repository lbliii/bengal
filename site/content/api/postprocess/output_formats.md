
---
title: "postprocess.output_formats"
type: python-module
source_file: "bengal/postprocess/output_formats.py"
css_class: api-content
description: "Custom output formats generation (JSON, LLM text, etc.).  Generates alternative output formats for pages to enable: - Client-side search (JSON index) - AI/LLM discovery (plain text format) - Progra..."
---

# postprocess.output_formats

Custom output formats generation (JSON, LLM text, etc.).

Generates alternative output formats for pages to enable:
- Client-side search (JSON index)
- AI/LLM discovery (plain text format)
- Programmatic access (JSON API)

---

## Classes

### `OutputFormatsGenerator`


Generates custom output formats for pages.

Provides alternative content formats to enable:
- Client-side search via JSON index
- AI/LLM discovery via plain text
- Programmatic API access via JSON

Output Formats:
- Per-page JSON: page.json next to each page.html (metadata + content)
- Per-page LLM text: page.txt next to each page.html (AI-friendly format)
- Site-wide index.json: Searchable index of all pages with summaries
- Site-wide llm-full.txt: Full site content in single text file

Configuration (bengal.toml):
    [output_formats]
    enabled = true
    per_page = ["json", "llm_txt"]
    site_wide = ["index_json", "llm_full"]




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: Any, config: dict[str, Any] | None = None) -> None
```

Initialize output formats generator.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 3 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
* - `site`
  - `Any`
  - -
  - Site instance
* - `config`
  - `dict[str, Any] | None`
  - `None`
  - Configuration dict from bengal.toml
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---
#### `generate`
```python
def generate(self) -> None
```

Generate all enabled output formats.

Checks configuration to determine which formats to generate,
filters pages based on exclusion rules, then generates:
1. Per-page formats (JSON, LLM text)
2. Site-wide formats (index.json, llm-full.txt)

All file writes are atomic to prevent corruption during builds.



:::{rubric} Parameters
:class: rubric-parameters
:::

::::{dropdown} 1 parameters (click to expand)
:open: false

:::{list-table}
:header-rows: 1
:widths: 20 20 20 40

* - Name
  - Type
  - Default
  - Description
* - `self`
  - -
  - -
  - -
:::

::::

:::{rubric} Returns
:class: rubric-returns
:::

`None`




---


