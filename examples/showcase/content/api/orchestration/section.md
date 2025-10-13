
---
title: "orchestration.section"
type: python-module
source_file: "bengal/orchestration/section.py"
css_class: api-content
description: "Section orchestration for Bengal SSG.  Handles section lifecycle: ensuring all sections have index pages, validation, and structural integrity."
---

# orchestration.section

Section orchestration for Bengal SSG.

Handles section lifecycle: ensuring all sections have index pages,
validation, and structural integrity.

---

## Classes

### `SectionOrchestrator`


Handles section structure and completeness.

Responsibilities:
- Ensure all sections have index pages (explicit or auto-generated)
- Generate archive pages for sections without _index.md
- Validate section structure
- Maintain section hierarchy integrity

This orchestrator implements the "structural" concerns of sections,
separate from cross-cutting concerns like taxonomies (tags, categories).




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, site: 'Site')
```

Initialize section orchestrator.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`site`** (`'Site'`) - Site instance to manage sections for





---
#### `finalize_sections`
```python
def finalize_sections(self) -> None
```

Finalize all sections by ensuring they have index pages.

For each section:
- If it has an explicit _index.md, leave it alone
- If it doesn't have an index page, generate an archive page
- Recursively process subsections

This ensures all section URLs resolve to valid pages.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `validate_sections`
```python
def validate_sections(self) -> list[str]
```

Validate that all sections have valid index pages.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`list[str]` - List of validation error messages (empty if all valid)




---
