
---
title: "mistune"
type: "python-module"
source_file: "../bengal/bengal/rendering/parsers/mistune.py"
line_number: 1
description: "Mistune parser implementation - fast with full documentation features."
---

# mistune
**Type:** Module
**Source:** [View source](../bengal/bengal/rendering/parsers/mistune.py#L1)



**Navigation:**
[bengal](/api/bengal/) ›[rendering](/api/bengal/rendering/) ›[parsers](/api/bengal/rendering/parsers/) ›mistune

Mistune parser implementation - fast with full documentation features.

## Classes




### `MistuneParser`


**Inherits from:**`BaseMarkdownParser`Parser using mistune library.
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









## Methods



#### `__init__`
```python
def __init__(self, enable_highlighting: bool = True) -> None
```


Initialize the mistune parser with plugins.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `enable_highlighting` | `bool` | `True` | Enable Pygments syntax highlighting for code blocks (defaults to True for backward compatibility) Parser Instances: This parser is typically created via thread-local caching. With parallel builds (max_workers=N), you'll see N instances created - one per worker thread. This is OPTIMAL, not a bug! Internal Structure: - self.md: Main mistune instance for standard parsing - self._md_with_vars: Created lazily for pages with {{ var }} syntax Both instances share plugins (cross-references, etc.) but have different preprocessing (variable substitution). |







**Returns**


`None`
:::{rubric} Raises
:class: rubric-raises
:::

- **`ImportError`**:If mistune is not installed





#### `parse`
```python
def parse(self, content: str, metadata: dict[str, Any]) -> str
```


Parse Markdown content into HTML.


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `content` | `str` | - | Markdown content to parse |
| `metadata` | `dict[str, Any]` | - | Page metadata (includes source path for validation warnings) |







**Returns**


`str` - Rendered HTML string



#### `parse_with_toc`
```python
def parse_with_toc(self, content: str, metadata: dict[str, Any]) -> tuple[str, str]
```


Parse Markdown content and extract table of contents.

Two-stage process:
1. Parse markdown to HTML
2. Inject heading anchors (IDs and headerlinks)
3. Extract TOC from anchored headings


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `content` | `str` | - | Markdown content to parse |
| `metadata` | `dict[str, Any]` | - | Page metadata (includes source path for validation warnings) |







**Returns**


`tuple[str, str]` - Tuple of (HTML with anchored headings, TOC HTML)



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


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `content` | `str` | - | Markdown content to parse |
| `metadata` | `dict[str, Any]` | - | Page metadata |
| `context` | `dict[str, Any]` | - | Variable context (page, site, config) |







**Returns**


`str` - Rendered HTML with variables substituted

Performance:
    - First call (per thread): Creates _md_with_vars (~10ms)
    - Subsequent calls: Reuses cached parser (~0ms overhead)
    - Variable preprocessing: ~0.5ms per page
    - Markdown parsing: ~1-5ms per page




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


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `content` | `str` | - | Markdown content to parse |
| `metadata` | `dict[str, Any]` | - | Page metadata |
| `context` | `dict[str, Any]` | - | Variable context (page, site, config) |







**Returns**


`tuple[str, str]` - Tuple of (HTML with anchored headings, TOC HTML)



#### `enable_cross_references`
```python
def enable_cross_references(self, xref_index: dict[str, Any]) -> None
```


Enable cross-reference support with [[link]] syntax.

Should be called after content discovery when xref_index is built.
Creates CrossReferencePlugin for post-processing HTML output.

Performance: O(1) - just stores reference to index
Thread-safe: Each thread-local parser instance needs this called once


**Parameters:**

| Name | Type | Default | Description |
|:-----|:-----|:--------|:------------|
| `xref_index` | `dict[str, Any]` | - | Pre-built cross-reference index from site discovery |







**Returns**


`None`
:::{rubric} Raises
:class: rubric-raises
:::

- **`ImportError`**:If CrossReferencePlugin cannot be imported

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
*Generated by Bengal autodoc from `../bengal/bengal/rendering/parsers/mistune.py`*
