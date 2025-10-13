
---
title: "rendering.parser"
type: python-module
source_file: "bengal/rendering/parser.py"
css_class: api-content
description: "Content parser for Markdown and other formats.  Supports multiple parser engines: - python-markdown: Full-featured, slower (default) - mistune: Fast, subset of features"
---

# rendering.parser

Content parser for Markdown and other formats.

Supports multiple parser engines:
- python-markdown: Full-featured, slower (default)
- mistune: Fast, subset of features

---

## Classes

### `BaseMarkdownParser`

**Inherits from:** `ABC`
Abstract base class for Markdown parsers.
All parser implementations must implement this interface.




:::{rubric} Methods
:class: rubric-methods
:::
#### `parse`
```python
def parse(self, content: str, metadata: dict[str, Any]) -> str
```

Parse Markdown content into HTML.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`content`** (`str`) - Raw Markdown content
- **`metadata`** (`dict[str, Any]`) - Page metadata

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Parsed HTML content




---
#### `parse_with_toc`
```python
def parse_with_toc(self, content: str, metadata: dict[str, Any]) -> tuple[str, str]
```

Parse Markdown content and extract table of contents.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`content`** (`str`) - Raw Markdown content
- **`metadata`** (`dict[str, Any]`) - Page metadata

:::{rubric} Returns
:class: rubric-returns
:::
`tuple[str, str]` - Tuple of (parsed HTML, table of contents HTML)




---

### `PythonMarkdownParser`

**Inherits from:** `BaseMarkdownParser`
Parser using python-markdown library.
Full-featured with all extensions.

Performance Note:
    Uses cached Pygments lexers to avoid expensive plugin discovery
    on every code block. This provides 3-10× speedup on sites with
    many code blocks.




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self) -> None
```

Initialize the python-markdown parser with extensions.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**

:::{rubric} Returns
:class: rubric-returns
:::
`None`




---
#### `parse`
```python
def parse(self, content: str, metadata: dict[str, Any]) -> str
```

Parse Markdown content into HTML.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`content`** (`str`)
- **`metadata`** (`dict[str, Any]`)

:::{rubric} Returns
:class: rubric-returns
:::
`str`




---
#### `parse_with_toc`
```python
def parse_with_toc(self, content: str, metadata: dict[str, Any]) -> tuple[str, str]
```

Parse Markdown content and extract table of contents.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`content`** (`str`)
- **`metadata`** (`dict[str, Any]`)

:::{rubric} Returns
:class: rubric-returns
:::
`tuple[str, str]`




---

### `MistuneParser`

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




:::{rubric} Methods
:class: rubric-methods
:::
#### `__init__`
```python
def __init__(self, enable_highlighting: bool = True) -> None
```

Initialize the mistune parser with plugins.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`enable_highlighting`** (`bool`) = `True` - Enable Pygments syntax highlighting for code blocks (defaults to True for backward compatibility) Parser Instances: This parser is typically created via thread-local caching. With parallel builds (max_workers=N), you'll see N instances created - one per worker thread. This is OPTIMAL, not a bug! Internal Structure: - self.md: Main mistune instance for standard parsing - self._md_with_vars: Created lazily for pages with {{ var }} syntax Both instances share plugins (cross-references, etc.) but have different preprocessing (variable substitution).

:::{rubric} Returns
:class: rubric-returns
:::
`None`

:::{rubric} Raises
:class: rubric-raises
:::
- **`ImportError`**: If mistune is not installed



---
#### `parse`
```python
def parse(self, content: str, metadata: dict[str, Any]) -> str
```

Parse Markdown content into HTML.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`content`** (`str`) - Markdown content to parse
- **`metadata`** (`dict[str, Any]`) - Page metadata (includes source path for validation warnings)

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Rendered HTML string




---
#### `parse_with_toc`
```python
def parse_with_toc(self, content: str, metadata: dict[str, Any]) -> tuple[str, str]
```

Parse Markdown content and extract table of contents.

Two-stage process:
1. Parse markdown to HTML
2. Inject heading anchors (IDs and headerlinks)
3. Extract TOC from anchored headings



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`content`** (`str`) - Markdown content to parse
- **`metadata`** (`dict[str, Any]`) - Page metadata (includes source path for validation warnings)

:::{rubric} Returns
:class: rubric-returns
:::
`tuple[str, str]` - Tuple of (HTML with anchored headings, TOC HTML)




---
#### `parse_with_context`
```python
def parse_with_context(self, content: str, metadata: dict[str, Any], context: dict[str, Any]) -> str
```

Parse Markdown with variable substitution support.

Variable Substitution:
    Enables {{ page.title }}, {{ site.baseurl }}, etc. in markdown content.
    Uses a separate mistune instance (_md_with_vars) with preprocessing.

Lazy Initialization:
    _md_with_vars is created on first use and cached thereafter.
    This happens once per parser instance (i.e., once per thread).

    Important: In parallel builds with max_workers=N:
    - N parser instances created (main: self.md)
    - N variable parser instances created (vars: self._md_with_vars)
    - Total: 2N mistune instances, but only 1 of each per thread
    - This is optimal - each thread uses its cached instances

Parser Reuse:
    The parser with VariableSubstitutionPlugin is cached and reused.
    Only the context is updated per page (fast operation).
    This avoids expensive parser re-initialization (~10ms) for every page.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`content`** (`str`) - Markdown content to parse
- **`metadata`** (`dict[str, Any]`) - Page metadata
- **`context`** (`dict[str, Any]`) - Variable context (page, site, config)

:::{rubric} Returns
:class: rubric-returns
:::
`str` - Rendered HTML with variables substituted

Performance:
    - First call (per thread): Creates _md_with_vars (~10ms)
    - Subsequent calls: Reuses cached parser (~0ms overhead)
    - Variable preprocessing: ~0.5ms per page
    - Markdown parsing: ~1-5ms per page




---
#### `parse_with_toc_and_context`
```python
def parse_with_toc_and_context(self, content: str, metadata: dict[str, Any], context: dict[str, Any]) -> tuple[str, str]
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



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`content`** (`str`) - Markdown content to parse
- **`metadata`** (`dict[str, Any]`) - Page metadata
- **`context`** (`dict[str, Any]`) - Variable context (page, site, config)

:::{rubric} Returns
:class: rubric-returns
:::
`tuple[str, str]` - Tuple of (HTML with anchored headings, TOC HTML)




---
#### `enable_cross_references`
```python
def enable_cross_references(self, xref_index: dict[str, Any]) -> None
```

Enable cross-reference support with [[link]] syntax.

Should be called after content discovery when xref_index is built.
Creates CrossReferencePlugin for post-processing HTML output.

Performance: O(1) - just stores reference to index
Thread-safe: Each thread-local parser instance needs this called once



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`self`**
- **`xref_index`** (`dict[str, Any]`) - Pre-built cross-reference index from site discovery

:::{rubric} Returns
:class: rubric-returns
:::
`None`

:::{rubric} Raises
:class: rubric-raises
:::
- **`ImportError`**: If CrossReferencePlugin cannot be imported



:::{rubric} Examples
:class: rubric-examples
:::
```python
>>> parser = MistuneParser()
    >>> # ... after content discovery ...
    >>> parser.enable_cross_references(site.xref_index)
    >>> # Now [[docs/installation]] works in markdown!
    >>> html = parser.parse("See [[docs/getting-started]]", {})
    >>> print(html)  # Contains <a href="/docs/getting-started">...</a>
```


---


## Functions

### `create_markdown_parser`
```python
def create_markdown_parser(engine: str | None = None) -> BaseMarkdownParser
```

Factory function to create a markdown parser instance.



:::{rubric} Parameters
:class: rubric-parameters
:::
- **`engine`** (`str | None`) = `None` - Parser engine to use ('python-markdown', 'mistune', or None for default)

:::{rubric} Returns
:class: rubric-returns
:::
`BaseMarkdownParser` - Markdown parser instance

:::{rubric} Raises
:class: rubric-raises
:::
- **`ValueError`**: If engine is not supported



---
