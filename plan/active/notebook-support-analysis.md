# Jupyter Notebook Support Analysis

## Executive Summary

**TL;DR**: Native notebook support would be **moderately easy** to implement. The best approach is a **triple hybrid**:
1. **NotebookParser** - for standalone `.ipynb` files as pages
2. **NotebookStrategy** - for specialized notebook collections
3. **NotebookDirective** - Mistune custom renderer for embedding notebooks in markdown 🎯

**Difficulty**: 🟢 Medium (2-3 days of focused work)
**Value**: 🟢 High (opens Bengal to data science/ML documentation use cases)
**Maintenance**: 🟢 Low (stable JSON format, good libraries available)

### Key Insight: Mistune Custom Renderers

You correctly pointed out that **Mistune supports custom renderers**! This opens up a powerful new approach:

Instead of just treating notebooks as standalone pages, we can use Mistune's `DirectivePlugin` system (like your existing `AdmonitionDirective`, `TabsDirective`, `CardDirective`) to **embed notebooks inside markdown pages**.

This means:
- ✅ Mix markdown prose with notebook outputs
- ✅ Embed multiple notebooks in one page
- ✅ Use `{notebook}` directive syntax (consistent with your architecture)
- ✅ Follows the exact same pattern as your existing plugins

---

## Current Architecture Context

Bengal has several extension points that could support notebooks:

### 1. **Content Discovery** (`bengal/discovery/content_discovery.py`)
- Currently recognizes: `.md`, `.markdown`, `.rst`, `.txt` (line 268)
- Would need to add `.ipynb` to `content_extensions`
- Already has robust file parsing with error handling

### 2. **Parser System** (`bengal/rendering/parsers/`)
- Interface: `BaseMarkdownParser` with `parse()` and `parse_with_toc()`
- Current implementations: `MistuneParser`, `PythonMarkdownParser`
- Could add: `NotebookParser` following the same interface

### 3. **Content Type Strategies** (`bengal/content_types/`)
- Currently has: blog, docs, tutorial, api-reference, etc.
- Could add: `NotebookStrategy` for specialized notebook sections
- Defines sorting, pagination, templates

### 4. **Autodoc System** (`bengal/autodoc/`)
- Uses AST-based extraction for Python modules
- Interface: `Extractor` with `extract()`, `get_template_dir()`, `get_output_path()`
- Could add: `NotebookExtractor` for notebook metadata extraction

---

## Proposed Approaches

### Option A: Parser-Based (Recommended for standalone notebooks ✅)

**Concept**: Treat `.ipynb` files like markdown files, but with a specialized parser.

**Note**: Since notebooks are JSON (not markdown), this doesn't use Mistune's custom renderer system. The parser converts JSON → HTML directly.

**Implementation**:
```python
# bengal/rendering/parsers/notebook.py
class NotebookParser(BaseMarkdownParser):
    """Parse Jupyter notebooks into HTML."""

    def parse(self, content: str, metadata: dict) -> str:
        """
        Convert notebook JSON to HTML.

        Args:
            content: Raw .ipynb JSON string
            metadata: Page metadata from frontmatter (if any)

        Returns:
            HTML representation of notebook
        """
        import nbformat
        from nbconvert import HTMLExporter

        notebook = nbformat.reads(content, as_version=4)
        html_exporter = HTMLExporter()

        # Configure exporter
        html_exporter.exclude_input_prompt = metadata.get('hide_prompts', False)
        html_exporter.exclude_output_prompt = metadata.get('hide_prompts', False)

        (body, resources) = html_exporter.from_notebook_node(notebook)
        return body

    def parse_with_toc(self, content: str, metadata: dict) -> tuple[str, str]:
        """Extract TOC from markdown cells with headers."""
        notebook = nbformat.reads(content, as_version=4)

        # Build TOC from markdown cells
        toc_items = []
        for cell in notebook.cells:
            if cell.cell_type == 'markdown':
                # Parse headers like "## My Section"
                for line in cell.source.split('\n'):
                    if line.startswith('#'):
                        level = len(line) - len(line.lstrip('#'))
                        title = line.lstrip('#').strip()
                        toc_items.append((level, title))

        html = self.parse(content, metadata)
        toc_html = self._render_toc(toc_items)

        return (html, toc_html)
```

**Discovery Changes**:
```python
# bengal/discovery/content_discovery.py:268
def _is_content_file(self, file_path: Path) -> bool:
    content_extensions = {".md", ".markdown", ".rst", ".txt", ".ipynb"}  # Add .ipynb
    return file_path.suffix.lower() in content_extensions
```

**Parser Factory Update**:
```python
# bengal/rendering/parsers/__init__.py
from bengal.rendering.parsers.notebook import NotebookParser

def create_parser_for_file(file_path: Path, engine: str = 'mistune') -> BaseMarkdownParser:
    """Create appropriate parser based on file extension."""
    if file_path.suffix.lower() == '.ipynb':
        return NotebookParser()
    else:
        return create_markdown_parser(engine)
```

**Pros**:
- ✅ Consistent with existing architecture
- ✅ Notebooks behave like regular pages (templates, menus, TOC)
- ✅ Minimal changes to core system
- ✅ Can use existing page metadata features
- ✅ Full rendering pipeline support (caching, incremental builds)

**Cons**:
- ⚠️ Notebooks are JSON, not text with frontmatter
- ⚠️ Need to handle notebook metadata separately

---

### Option B: Content Type Strategy

**Concept**: Add a specialized content type for notebook collections.

```python
# bengal/content_types/strategies.py
class NotebookStrategy(ContentTypeStrategy):
    """Strategy for Jupyter notebook collections."""

    default_template = "notebook/list.html"
    allows_pagination = True

    def sort_pages(self, pages: list[Page]) -> list[Page]:
        """Sort by notebook execution order or date."""
        return sorted(pages, key=lambda p: p.metadata.get('notebook_order', 999))

    def detect_from_section(self, section: Section) -> bool:
        """Detect notebook sections."""
        if section.name.lower() in ('notebooks', 'examples', 'tutorials'):
            # Check if most files are .ipynb
            ipynb_count = sum(1 for p in section.pages
                            if p.source_path.suffix == '.ipynb')
            return ipynb_count > len(section.pages) * 0.5
        return False
```

**Pros**:
- ✅ Specialized behavior for notebook collections
- ✅ Custom templates for notebook galleries
- ✅ Auto-detection of notebook sections

**Cons**:
- ⚠️ Still needs parser approach for rendering
- ⚠️ More of an enhancement than a solution

**Verdict**: Use this **in addition to** Option A for better UX.

---

### Option C: Autodoc Extractor Approach

**Concept**: Use autodoc to extract notebook metadata and generate documentation pages.

```python
# bengal/autodoc/extractors/notebook.py
class NotebookExtractor(Extractor):
    """Extract documentation from Jupyter notebooks."""

    def extract(self, source: Path) -> list[DocElement]:
        """
        Extract metadata and structure from notebooks.

        Returns DocElements for:
        - Notebook overview
        - Code cells as "functions"
        - Markdown cells as documentation
        """
        notebook = nbformat.read(source, as_version=4)

        # Extract notebook-level metadata
        nb_element = DocElement(
            name=source.stem,
            qualified_name=str(source),
            description=self._extract_description(notebook),
            element_type='notebook',
            metadata={
                'kernel': notebook.metadata.get('kernelspec', {}).get('name'),
                'language': notebook.metadata.get('language_info', {}).get('name'),
                'cell_count': len(notebook.cells),
                'code_cells': sum(1 for c in notebook.cells if c.cell_type == 'code'),
            }
        )

        # Extract cells as children
        for idx, cell in enumerate(notebook.cells):
            if cell.cell_type == 'code':
                # Treat code cells as functions
                nb_element.children.append(DocElement(
                    name=f"cell_{idx}",
                    qualified_name=f"{source.stem}.cell_{idx}",
                    description=self._extract_cell_description(cell),
                    element_type='code_cell',
                    metadata={
                        'source': cell.source,
                        'outputs': cell.get('outputs', []),
                    }
                ))

        return [nb_element]

    def get_template_dir(self) -> str:
        return "notebook"

    def get_output_path(self, element: DocElement) -> Path:
        """notebooks/example.ipynb → notebooks/example.md"""
        return Path(element.qualified_name).with_suffix('.md')
```

**Pros**:
- ✅ Leverages existing autodoc infrastructure
- ✅ Can extract code cell metadata for analysis
- ✅ Good for "notebook gallery" style documentation

**Cons**:
- ❌ Doesn't render notebook outputs (just extracts metadata)
- ❌ Loses execution results
- ❌ Not suitable for actual notebook display

**Verdict**: **Not recommended** as primary approach, but could be useful for notebook cataloging.

---

### Option D: Mistune Custom Renderer / Directive (NEW! 🎯)

**Concept**: Use Mistune's custom directive system to **embed notebooks** in markdown pages.

Following the pattern of `AdmonitionDirective`, `TabsDirective`, etc., we could create a `NotebookDirective`:

```python
# bengal/rendering/plugins/directives/notebook.py
from mistune.directives import DirectivePlugin

class NotebookDirective(DirectivePlugin):
    """
    Embed Jupyter notebooks in markdown pages.

    Syntax:
        ```{notebook} path/to/analysis.ipynb
        :hide-code: false
        :hide-prompts: true
        :execute: false
        ```
    """

    def parse(self, block, m, state):
        """Parse notebook directive."""
        # Get notebook path from directive
        notebook_path = self.parse_title(m)  # e.g., "analysis.ipynb"

        # Parse options
        options = self.parse_options(m)  # hide-code, hide-prompts, execute, etc.

        # Note: We don't parse the content here - it's handled at render time
        return {
            "type": "notebook_embed",
            "attrs": {
                "path": notebook_path,
                "hide_code": options.get("hide-code", "false") == "true",
                "hide_prompts": options.get("hide-prompts", "false") == "true",
                "execute": options.get("execute", "false") == "true",
            }
        }

    def __call__(self, directive, md):
        """Register the directive with mistune."""
        directive.register("notebook", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("notebook_embed", render_notebook_embed)


def render_notebook_embed(renderer, path: str, hide_code: bool, hide_prompts: bool, execute: bool) -> str:
    """
    Render embedded notebook to HTML.

    This is called during markdown rendering with the notebook metadata.
    We need to:
    1. Resolve the notebook path (relative to content directory)
    2. Load and convert the notebook to HTML
    3. Return the HTML for inline embedding
    """
    import nbformat
    from nbconvert import HTMLExporter
    from pathlib import Path

    # Resolve notebook path
    # (This needs access to the site/page context - see below)
    try:
        notebook_file = Path(path)
        if not notebook_file.is_absolute():
            # Relative to current page's directory
            # TODO: Need to pass page context to renderer
            pass

        # Load notebook
        notebook = nbformat.read(notebook_file, as_version=4)

        # Configure exporter
        html_exporter = HTMLExporter()
        html_exporter.exclude_input = hide_code
        html_exporter.exclude_input_prompt = hide_prompts
        html_exporter.exclude_output_prompt = hide_prompts

        # Convert to HTML
        (body, resources) = html_exporter.from_notebook_node(notebook)

        return f'<div class="embedded-notebook">\n{body}\n</div>'

    except Exception as e:
        return f'<div class="notebook-error">Failed to load notebook: {path}<br>Error: {e}</div>'
```

**Usage in Markdown**:
```markdown
# My Data Analysis Tutorial

Here's a complete analysis workflow:

\```{notebook} examples/data-cleaning.ipynb
:hide-prompts: true
\```

The above notebook demonstrates...
```

**Pros**:
- ✅ **Follows your existing architecture** (just like tabs, admonitions, cards)
- ✅ Embed notebooks **inside markdown pages** (not just standalone)
- ✅ Can have multiple notebooks in one page
- ✅ Mistune handles the directive syntax parsing
- ✅ Options for showing/hiding code, prompts, etc.
- ✅ Markdown before/after the notebook
- ✅ Works with all existing features (TOC, cross-refs, etc.)

**Cons**:
- ⚠️ Renderer needs access to file system to load notebooks
- ⚠️ Need to pass page context to resolve relative paths
- ⚠️ Doesn't support standalone `.ipynb` files as pages (need Option A for that)

**Context Challenge**:

Mistune renderers don't have access to page context by default. We'd need to:
1. Store context in renderer (like you do with `VariableSubstitutionPlugin`)
2. Or resolve paths during parsing (before rendering)
3. Or pre-load notebooks and pass HTML as directive content

**Better implementation** (with context):
```python
class NotebookDirective(DirectivePlugin):
    def __init__(self, page_context: dict = None):
        self.page_context = page_context or {}

    def parse(self, block, m, state):
        notebook_path = self.parse_title(m)
        options = self.parse_options(m)

        # Load notebook at PARSE time (we have context here)
        from pathlib import Path

        # Resolve path relative to current page
        current_page_dir = self.page_context.get('page_dir', Path.cwd())
        full_path = (current_page_dir / notebook_path).resolve()

        # Load and convert NOW (during parsing, not rendering)
        notebook_html = self._load_and_convert_notebook(
            full_path,
            hide_code=options.get('hide-code') == 'true',
            hide_prompts=options.get('hide-prompts') == 'true'
        )

        return {
            "type": "notebook_embed",
            "attrs": {
                "html": notebook_html,  # Pre-rendered HTML
                "path": str(notebook_path),
            }
        }
```

---

## Recommended Solution: Triple Hybrid! 🚀

Combine **Option A** (parser) + **Option B** (strategy) + **Option D** (Mistune directive):

### Phase 1: Core Notebook Rendering (2 days)

**Track 1: Standalone Notebooks** (Option A)
1. **Add NotebookParser** (`bengal/rendering/parsers/notebook.py`)
   - Use `nbconvert` library for HTML generation
   - Extract TOC from markdown cells
   - Support metadata for rendering options

2. **Update Content Discovery**
   - Add `.ipynb` to recognized extensions
   - Handle notebook metadata extraction

3. **Parser Selection Logic**
   - File extension-based parser routing
   - Fallback to markdown for unknown types

**Track 2: Embedded Notebooks** (Option D - uses Mistune custom renderers!)
1. **Add NotebookDirective** (`bengal/rendering/plugins/directives/notebook.py`)
   - Follows pattern of `AdmonitionDirective`, `TabsDirective`, etc.
   - Parse `{notebook}` directive syntax
   - Load and convert notebooks during parse phase
   - Return pre-rendered HTML

2. **Register with MistuneParser**
   ```python
   # bengal/rendering/parsers/mistune.py
   from bengal.rendering.plugins.directives.notebook import NotebookDirective

   plugins = [
       # ... existing ...
       NotebookDirective(),  # Add to plugin list
   ]
   ```

3. **Update documentation directives loader**
   ```python
   # bengal/rendering/plugins/directives/__init__.py
   from .notebook import NotebookDirective

   directive = FencedDirective([
       # ... existing ...
       NotebookDirective(),  # Register notebook embedding
   ])
   ```

**Dependencies** (both tracks):
```toml
# pyproject.toml
[project]
dependencies = [
    # ... existing ...
    "nbformat>=5.0.0",
    "nbconvert>=7.0.0",
]
```

### Phase 2: Enhanced Notebook Features (1 day)

1. **Add NotebookStrategy** (Option B) for specialized sections
2. **Create notebook templates** (`themes/default/notebook/`)
3. **Add notebook-specific metadata options**:
   ```yaml
   # In notebook frontmatter (via cell metadata)
   ---
   title: "My Data Analysis"
   hide_prompts: true
   hide_code: false
   execute_on_build: false
   notebook_order: 10
   ---
   ```

### Phase 3: Advanced Features (Optional)

1. **Notebook execution during build**
   - Option to re-run notebooks before rendering
   - Cache execution results
   - Useful for ensuring outputs are up-to-date

2. **Interactive outputs**
   - Preserve interactive widgets (plotly, bokeh)
   - Embed JavaScript for interactivity

3. **Code cell linking**
   - Cross-reference between notebook cells
   - Link to source code in repo

---

## Feature Comparison

| Feature | Markdown Pages | Notebook Pages |
|---------|---------------|----------------|
| Frontmatter | ✅ Yes | ⚠️ Via cell metadata |
| TOC extraction | ✅ Auto | ✅ From markdown cells |
| Code syntax highlighting | ✅ Via fences | ✅ Native |
| Execution outputs | ❌ Static only | ✅ Rendered |
| Interactive widgets | ❌ No | ✅ Yes (with JS) |
| Cross-references | ✅ [[links]] | ✅ Same |
| Templates | ✅ Full support | ✅ Full support |
| Caching | ✅ Yes | ✅ Yes |
| Incremental builds | ✅ Yes | ✅ Yes |

---

## Technical Considerations

### Metadata Handling

Notebooks don't have frontmatter, but have cell metadata:

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {
     "bengal": {
       "title": "My Analysis",
       "weight": 10,
       "toc": true
     }
   },
   "source": ["# My Analysis\n"]
  }
 ]
}
```

Extract this during page creation:
```python
def _parse_notebook_metadata(notebook_json: str) -> dict:
    """Extract Bengal metadata from first cell."""
    notebook = nbformat.reads(notebook_json, as_version=4)

    # Check first cell for Bengal metadata
    if notebook.cells:
        first_cell = notebook.cells[0]
        if 'bengal' in first_cell.metadata:
            return first_cell.metadata['bengal']

    # Fallback: use notebook-level metadata
    return notebook.metadata.get('bengal', {})
```

### Output Size Management

Notebooks can be large (embedded images, dataframes). Consider:

1. **Image externalization**: Extract images to assets folder
2. **Output truncation**: Limit number of output rows shown
3. **Lazy loading**: Load outputs on demand with JavaScript

### Version Control

Notebooks have messy diffs. Recommendations:

1. **Use `.ipynb_checkpoints` in `.gitignore`** (already standard)
2. **Consider `nbstripout`** for CI/CD (removes outputs before commit)
3. **Store "clean" versions** in repo, re-execute during build

---

## Example Usage

### Site Structure
```
content/
├── _index.md
├── docs/
│   ├── _index.md
│   └── getting-started.md
└── notebooks/           # Notebook section
    ├── _index.md        # Section overview
    ├── analysis.ipynb   # Rendered as page
    ├── tutorial.ipynb
    └── examples/
        └── demo.ipynb
```

### Rendering Output
```
public/
├── docs/
│   └── getting-started/index.html
└── notebooks/
    ├── index.html              # Notebook gallery
    ├── analysis/index.html     # Rendered notebook with outputs
    ├── tutorial/index.html
    └── examples/
        └── demo/index.html
```

### Template Example
```html
{# themes/default/notebook/single.html #}
{% extends "base.html" %}

{% block content %}
<article class="notebook">
  <header>
    <h1>{{ page.title }}</h1>
    {% if page.metadata.kernel %}
    <span class="kernel-badge">{{ page.metadata.kernel }}</span>
    {% endif %}
  </header>

  {# Rendered notebook HTML (includes all cells + outputs) #}
  <div class="notebook-content">
    {{ content }}
  </div>

  {# Download link #}
  <footer>
    <a href="{{ page.source_path | relative_url }}" download>
      Download Notebook
    </a>
  </footer>
</article>
{% endblock %}
```

### Use Case 2: Embedded Notebooks in Markdown (Option D - Custom Mistune Directive!)

**Content Structure**:
```
content/
├── tutorials/
│   ├── getting-started.md       # Markdown page
│   └── notebooks/
│       ├── intro.ipynb          # Embedded notebook
│       └── advanced.ipynb
```

**Markdown Page with Embedded Notebook**:
```markdown
---
title: "Getting Started with Data Analysis"
---

# Getting Started

This tutorial walks you through basic data analysis techniques.

## Setup

First, let's import our libraries:

\```{notebook} notebooks/intro.ipynb
:hide-prompts: true
\```

## Advanced Techniques

For more complex analysis, see:

\```{notebook} notebooks/advanced.ipynb
:hide-code: false
:execute: true
\```

The notebook above demonstrates...
```

**Rendered Output**:
- Single HTML page with markdown + embedded notebook outputs
- Notebook cells appear inline in the page
- Full markdown capabilities (headings, links, etc.) before/after notebooks
- TOC includes markdown headings + notebook section headings

**Benefits of this approach**:
1. ✅ Mix markdown prose with executable notebook examples
2. ✅ One page can embed multiple notebooks
3. ✅ Leverages Mistune's custom renderer system (like your tabs, admonitions, cards)
4. ✅ Consistent with your existing plugin architecture
5. ✅ Can show different parts of same notebook on different pages

---

## Comparison to Hugo/MkDocs

### Hugo
- No native notebook support
- Requires shortcodes or external converters
- Notebooks must be pre-converted to markdown

### MkDocs + nbconvert
- Uses `mkdocs-jupyter` plugin
- Similar approach to our Option A
- Bengal would have feature parity with this implementation

### Jupyter Book
- Specialized for notebooks (entire framework)
- More features but less flexible for general sites
- Bengal would be lighter-weight alternative

---

## Recommendation

**Implement all three complementary approaches**:

1. **Option A (Parser)** - Standalone `.ipynb` pages (core functionality)
2. **Option B (Strategy)** - Better UX for notebook collections
3. **Option D (Directive)** - Embed notebooks in markdown via Mistune custom renderer 🎯
4. **Skip Option C (Autodoc)** - Not suitable for rendering

**Why this triple hybrid?**
- ✅ **Option A**: Notebooks can be full pages (like markdown files)
- ✅ **Option D**: Notebooks can be embedded in markdown (like your tabs/cards/admonitions)
- ✅ **Option B**: Notebook sections get specialized behavior
- ✅ Consistent with Bengal's architecture (parsers, strategies, plugins)
- ✅ **Leverages Mistune's custom renderer system** (your existing pattern)
- ✅ Minimal core changes
- ✅ Full feature support (TOC, templates, caching)
- ✅ Opens new use cases (data science docs, ML tutorials)
- ✅ Low maintenance (stable libraries, standard format)
- ✅ Maximum flexibility (standalone OR embedded)

**Estimated effort**: 2-3 days for full implementation (both tracks)

---

## Open Questions

1. **Execution during build?**
   - Yes for "documentation notebooks" (always fresh)
   - No for "archived analyses" (preserve original outputs)
   - Make it configurable per-notebook or per-section

2. **Interactive outputs?**
   - Phase 1: Static HTML rendering (simple)
   - Phase 2: Preserve JavaScript widgets (plotly, etc.)

3. **Frontmatter alternative?**
   - Use first cell metadata (`cell.metadata.bengal`)
   - Or require separate `analysis.ipynb.yaml` sidecar file

4. **Download link?**
   - Should rendered notebooks link to original `.ipynb`?
   - Copy notebooks to public/ for download?

---

## Next Steps

If you want to proceed:

1. **Prototype the NotebookParser** (1-2 hours)
2. **Test with sample notebook** in your showcase example
3. **Iterate on metadata handling**
4. **Add templates and styling**
5. **Document the feature**

Let me know if you want me to start implementing! 🚀
