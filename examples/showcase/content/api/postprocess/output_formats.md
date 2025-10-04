---
title: "postprocess.output_formats"
layout: api-reference
type: python-module
source_file: "../../bengal/postprocess/output_formats.py"
---

# postprocess.output_formats

Custom output formats generation (JSON, LLM text, etc.).

Generates alternative output formats for pages to enable:
- Client-side search (JSON index)
- AI/LLM discovery (plain text format)
- Programmatic access (JSON API)

**Source:** `../../bengal/postprocess/output_formats.py`

---

## Classes

### OutputFormatsGenerator


Generates custom output formats for pages.

Supports:
- Per-page JSON output (page.json next to page.html)
- Per-page LLM text output (page.txt next to page.html)
- Site-wide index.json (searchable index of all pages)
- Site-wide llm-full.txt (full site content for AI)




**Methods:**

#### __init__

```python
def __init__(self, site: Any, config: Optional[Dict[str, Any]] = None) -> None
```

Initialize output formats generator.

**Parameters:**

- **self**
- **site** (`Any`) - Site instance
- **config** (`Optional[Dict[str, Any]]`) = `None` - Configuration dict from bengal.toml

**Returns:** `None`






---
#### generate

```python
def generate(self) -> None
```

Generate all enabled output formats.

**Parameters:**

- **self**

**Returns:** `None`






---


