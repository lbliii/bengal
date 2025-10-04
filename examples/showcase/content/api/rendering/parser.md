---
title: "rendering.parser"
layout: api-reference
type: python-module
source_file: "../../bengal/rendering/parser.py"
---

# rendering.parser

Content parser for Markdown and other formats.

Supports multiple parser engines:
- python-markdown: Full-featured, slower (default)
- mistune: Fast, subset of features

**Source:** `../../bengal/rendering/parser.py`

---

## Classes

### BaseMarkdownParser

**Inherits from:** `ABC`
Abstract base class for Markdown parsers.
All parser implementations must implement this interface.




**Methods:**

#### parse

```python
def parse(self, content: str, metadata: Dict[str, Any]) -> str
```

Parse Markdown content into HTML.

**Parameters:**

- **self**
- **content** (`str`) - Raw Markdown content
- **metadata** (`Dict[str, Any]`) - Page metadata

**Returns:** `str` - Parsed HTML content






---
#### parse_with_toc

```python
def parse_with_toc(self, content: str, metadata: Dict[str, Any]) -> tuple[str, str]
```

Parse Markdown content and extract table of contents.

**Parameters:**

- **self**
- **content** (`str`) - Raw Markdown content
- **metadata** (`Dict[str, Any]`) - Page metadata

**Returns:** `tuple[str, str]` - Tuple of (parsed HTML, table of contents HTML)






---

### PythonMarkdownParser

**Inherits from:** `BaseMarkdownParser`
Parser using python-markdown library.
Full-featured with all extensions.




**Methods:**

#### __init__

```python
def __init__(self) -> None
```

Initialize the python-markdown parser with extensions.

**Parameters:**

- **self**

**Returns:** `None`






---
#### parse

```python
def parse(self, content: str, metadata: Dict[str, Any]) -> str
```

Parse Markdown content into HTML.

**Parameters:**

- **self**
- **content** (`str`)
- **metadata** (`Dict[str, Any]`)

**Returns:** `str`






---
#### parse_with_toc

```python
def parse_with_toc(self, content: str, metadata: Dict[str, Any]) -> tuple[str, str]
```

Parse Markdown content and extract table of contents.

**Parameters:**

- **self**
- **content** (`str`)
- **metadata** (`Dict[str, Any]`)

**Returns:** `tuple[str, str]`






---

### MistuneParser

**Inherits from:** `BaseMarkdownParser`
Parser using mistune library.
Faster with full documentation features.

Supported features:
- Tables (GFM)
- Fenced code blocks
- Strikethrough
- Task lists
- Autolinks
- TOC generation (custom implementation)
- Admonitions (custom plugin)
- Footnotes (custom plugin)
- Definition lists (custom plugin)
- Variable substitution (custom plugin) - NEW!




**Methods:**

#### __init__

```python
def __init__(self) -> None
```

Initialize the mistune parser with plugins.

**Parameters:**

- **self**

**Returns:** `None`






---
#### parse

```python
def parse(self, content: str, metadata: Dict[str, Any]) -> str
```

Parse Markdown content into HTML.

**Parameters:**

- **self**
- **content** (`str`) - Markdown content to parse
- **metadata** (`Dict[str, Any]`) - Page metadata (unused by Mistune but required by interface)

**Returns:** `str` - Rendered HTML string






---
#### parse_with_toc

```python
def parse_with_toc(self, content: str, metadata: Dict[str, Any]) -> tuple[str, str]
```

Parse Markdown content and extract table of contents.

Two-stage process:
1. Parse markdown to HTML
2. Inject heading anchors (IDs and headerlinks)
3. Extract TOC from anchored headings

**Parameters:**

- **self**
- **content** (`str`) - Markdown content to parse
- **metadata** (`Dict[str, Any]`) - Page metadata (unused)

**Returns:** `tuple[str, str]` - Tuple of (HTML with anchored headings, TOC HTML)






---
#### parse_with_context

```python
def parse_with_context(self, content: str, metadata: Dict[str, Any], context: Dict[str, Any]) -> str
```

Parse Markdown with variable substitution support.

Caches the parser with VariableSubstitutionPlugin and reuses it,
updating only the context per page. This avoids expensive parser
re-initialization for every page.

**Parameters:**

- **self**
- **content** (`str`) - Markdown content to parse
- **metadata** (`Dict[str, Any]`) - Page metadata
- **context** (`Dict[str, Any]`) - Variable context (page, site, config)

**Returns:** `str` - Rendered HTML with variables substituted






---
#### parse_with_toc_and_context

```python
def parse_with_toc_and_context(self, content: str, metadata: Dict[str, Any], context: Dict[str, Any]) -> tuple[str, str]
```

Parse Markdown with variable substitution and extract TOC.

Single-pass parsing with VariableSubstitutionPlugin for {{ vars }}.

ARCHITECTURE DECISION: Separation of Concerns
================================================

SUPPORTED in markdown content:
- {{ page.metadata.xxx }} - Variable substitution
- {{ site.config.xxx }} - Site configuration access
- Code blocks naturally stay literal (AST-level protection)

NOT SUPPORTED in markdown content:
- {% if %} - Conditional blocks
- {% for %} - Loop constructs
- Complex Jinja2 logic

WHY: These belong in TEMPLATES, not markdown content.

Use conditionals and loops in your page templates:

    <!-- templates/page.html -->
    <article>
      {% if page.metadata.enterprise %}
      <div class="enterprise-badge">Enterprise</div>
      {% endif %}
      
      {{ content }}  <!-- Markdown renders here -->
    </article>

This design:
- Keeps parsing simple and fast (single pass)
- Follows Hugo's architecture (content vs logic separation)
- Maintains performance (no preprocessing overhead)
- Makes code blocks work naturally

**Parameters:**

- **self**
- **content** (`str`) - Markdown content to parse
- **metadata** (`Dict[str, Any]`) - Page metadata
- **context** (`Dict[str, Any]`) - Variable context (page, site, config)

**Returns:** `tuple[str, str]` - Tuple of (HTML with anchored headings, TOC HTML)






---
#### enable_cross_references

```python
def enable_cross_references(self, xref_index: Dict[str, Any]) -> None
```

Enable cross-reference support with [[link]] syntax.

Should be called after content discovery when xref_index is built.
Creates CrossReferencePlugin for post-processing HTML output.

Performance: O(1) - just stores reference to index
Thread-safe: Each thread-local parser instance needs this called once

**Parameters:**

- **self**
- **xref_index** (`Dict[str, Any]`) - Pre-built cross-reference index from site discovery Example usage: parser = MistuneParser() # ... after content discovery ... parser.enable_cross_references(site.xref_index) # Now [[docs/installation]] works in markdown!

**Returns:** `None`






---


## Functions

### create_markdown_parser

```python
def create_markdown_parser(engine: Optional[str] = None) -> BaseMarkdownParser
```

Factory function to create a markdown parser instance.

**Parameters:**

- **engine** (`Optional[str]`) = `None` - Parser engine to use ('python-markdown', 'mistune', or None for default)

**Returns:** `BaseMarkdownParser` - Markdown parser instance

**Raises:**

- **ValueError**: If engine is not supported




---
