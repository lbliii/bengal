# Rendering Pipeline

The rendering pipeline is divided into clear stages:

```
Parse → Build AST → Apply Templates → Render Output → Post-process
```

## Rendering Flow Detail

```mermaid
flowchart TD
    Start[Markdown File] --> VarSub[Variable Substitution<br/>Preprocessing]
    VarSub --> Parse[Parse Markdown<br/>Mistune]

    Parse --> Plugins{Mistune Plugins}
    Plugins --> P1[Built-in: table, strikethrough,<br/>task_lists, url, footnotes, def_list]
    Plugins --> P2[Custom: Documentation Directives<br/>admonitions, tabs, dropdowns, code_tabs]

    P1 --> AST[Abstract Syntax Tree]
    P2 --> AST

    AST --> HTML1[Generate HTML]
    HTML1 --> PostProc[Post-Processing]
    PostProc --> XRef[Cross-Reference Links [[...]]]
    PostProc --> Anchors[Heading Anchors & IDs]
    PostProc --> TOC[TOC Extraction]

    XRef --> HTML2[HTML with Links & Anchors]
    Anchors --> HTML2
    TOC --> HTML2

    HTML2 --> APIEnhance{API Reference Page?}
    APIEnhance -->|Yes| Badges[Inject Badges<br/>@async, @property, etc.]
    APIEnhance -->|No| HTML3[Enhanced HTML]
    Badges --> HTML3

    HTML3 --> Links[Extract Links<br/>for Validation]
    Links --> Context[Build Template Context]

    Context --> ContextData{Context Includes}
    ContextData --> Page[page object]
    ContextData --> Site[site object]
    ContextData --> Config[config]
    ContextData --> Functions[80+ template functions]
    ContextData --> Content[content HTML]
    ContextData --> TOCData[toc, toc_items]

    Page --> Jinja[Jinja2 Template Engine]
    Site --> Jinja
    Config --> Jinja
    Functions --> Jinja
    Content --> Jinja
    TOCData --> Jinja

    Jinja --> Template[Apply Template]
    Template --> FinalHTML[Final HTML]

    FinalHTML --> Output[Atomic Write to public/]

    style VarSub fill:#ffe6e6
    style Parse fill:#e1f5ff
    style P1 fill:#fff4e6
    style P2 fill:#fff4e6
    style PostProc fill:#f0e6ff
    style APIEnhance fill:#e6ffe6
    style Jinja fill:#e8f5e9
    style FinalHTML fill:#f3e5f5
```

**Key Features:**
- **Three-Stage Processing**: Pre-processing (variables) → Parsing (plugins) → Post-processing (xrefs, anchors)
- **Variable Substitution**: `{{ page.title }}` replaced BEFORE Mistune parsing (natural code block protection)
- **Plugin Architecture**: Built-in Mistune plugins + custom documentation directives during parsing
- **Post-Processing**: Cross-references, heading anchors, and TOC extracted AFTER HTML generation
- **API Enhancement**: Special badge injection for API reference pages (@async, @property markers)
- **Rich Context**: Templates have access to entire site, page navigation, taxonomies, 80+ functions
- **Atomic Writes**: Crash-safe file writing with atomic operations

## Parser (`bengal/rendering/parser.py`)

### Multi-Engine Architecture
Supports multiple Markdown parsers with unified interface

### Base Parser Interface
`BaseMarkdownParser` ABC defines contract for all parsers

### Factory Pattern
`create_markdown_parser(engine)` returns appropriate parser instance

### Thread-Local Caching
Parser instances reused per thread for performance

### Uses Utilities
Delegates to `bengal.utils.text.slugify()` for heading ID generation

### Supported Engines

- **`python-markdown`** (default): Feature-rich (3.78s for 78 pages)
- **`mistune`** (recommended): Faster parser with full doc features (2.18s for 78 pages, 42% faster)

### Configuration

Select engine via `bengal.toml`:

```toml
[build]
markdown_engine = "mistune"  # or "python-markdown"
```

## Mistune Parser

### Performance
52% faster rendering, 42% faster total builds

### Built-in Features
- GFM tables, footnotes, definition lists
- Task lists, strikethrough, autolinks
- Code blocks (fenced + inline)

### Custom Plugins
- **Admonitions**: `!!! note "Title"` syntax (7+ types)
- **Directives**: Fenced directives for rich content (` ```{name} `)
  - **Tabs**: Multi-tab content with markdown support
  - **Dropdowns**: Collapsible sections
  - **Code-tabs**: Multi-language code examples (partial support)
- **Variable Substitution**: `{{ page.metadata.xxx }}` in markdown content
- **TOC Generation**: Extracts h2-h4 headings with slugs
- **Heading IDs**: Auto-generated with permalink anchors

### Nesting Support
Full recursive markdown parsing inside directives

### Plugin Architecture
Extensible via `mistune.DirectivePlugin`

### Location
Core parser in `bengal/rendering/parser.py`, plugins in `bengal/rendering/plugins/`

## Mistune Plugins (`bengal/rendering/plugins/`)

### Structure
Modular plugin package with focused modules (~100-200 lines each)

### Core Plugins

| Plugin | File | Purpose |
|--------|------|---------|
| **Variable Substitution** | `variable_substitution.py` | Substitute `{{ page.metadata.xxx }}` in markdown content |
| **Cross References** | `cross_references.py` | Resolve `[[docs/page]]` references to internal pages |
| **Badges** | `badges.py` | Inject badges for API documentation (@async, @property, etc.) |

### Documentation Directives (`directives/` subdirectory)

| Directive | File | Syntax | Purpose |
|-----------|------|--------|---------|
| **Admonitions** | `admonitions.py` | ` ```{note} Title ` | Callout boxes (note, tip, warning, danger, error, info, example, success, caution) |
| **Tabs** | `tabs.py` | ` ```{tabs} ` | Tabbed content sections with markdown support |
| **Dropdown** | `dropdown.py` | ` ```{dropdown} Title ` | Collapsible sections with open/closed state |
| **Code Tabs** | `code_tabs.py` | ` ```{code-tabs} ` | Multi-language code examples with syntax highlighting |
| **Cards** | `cards.py` | ` ```{cards} ` / ` ```{card} ` | Card layouts with titles, icons, and links |
| **Grid** | `cards.py` | ` ```{grid} ` / ` ```{grid-item-card} ` | Responsive grid layouts for content |
| **Button** | `button.py` | ` ```{button} ` | Styled buttons with various types |
| **Rubric** | `rubric.py` | ` ```{rubric} ` | Rubric headings (minor headings without TOC entries) |

### Supporting Modules

| Module | Purpose |
|--------|---------|
| `directives/validator.py` | Validation and error checking for directives |
| `directives/errors.py` | Error formatting and reporting |
| `directives/cache.py` | Caching for directive parsing (planned) |

### Features
- **Clean API**: Only 3 main exports (`VariableSubstitutionPlugin`, `CrossReferencePlugin`, `create_documentation_directives`)
- **Modular**: Each directive is self-contained and independently testable
- **Extensible**: Add new directives without touching existing code
- **Backward Compatible**: Old imports still work via aliases
- **Error Handling**: Comprehensive validation and error reporting
- **Performance**: Efficient parsing with minimal overhead

### Architecture Pattern

```python
# Old monolithic structure (v0.1.x):
bengal/rendering/mistune_plugins.py (757 lines)

# New modular structure (v1.0.0+):
bengal/rendering/plugins/
├── __init__.py                    # Public API
├── variable_substitution.py       # Core plugin
├── cross_references.py            # Core plugin
├── badges.py                      # API doc enhancement
└── directives/
    ├── __init__.py               # Directive factory
    ├── admonitions.py            # ~150 lines
    ├── tabs.py                   # ~180 lines
    ├── dropdown.py               # ~100 lines
    ├── code_tabs.py              # ~120 lines
    ├── cards.py                  # ~400 lines (3 directives)
    ├── button.py                 # ~100 lines
    ├── rubric.py                 # ~80 lines
    ├── validator.py              # Validation
    └── errors.py                 # Error formatting
```

### Usage

```python
from bengal.rendering.plugins import (
    VariableSubstitutionPlugin,
    CrossReferencePlugin,
    create_documentation_directives
)
import mistune

# Create markdown parser with all plugins
md = mistune.create_markdown(
    plugins=[
        'table',
        'strikethrough',
        create_documentation_directives(),
        VariableSubstitutionPlugin(context),
    ]
)
```

**See**: `bengal/rendering/plugins/README.md` for detailed documentation

## Variable Substitution in Markdown Content

### Purpose
Insert dynamic frontmatter values into markdown content (DRY principle).

### Architecture
Single-pass Mistune plugin at AST level; code blocks stay literal automatically.

### Supported Syntax

```markdown
Welcome to {{ page.metadata.product_name }} version {{ page.metadata.version }}.
Connect to {{ page.metadata.api_url }}/users
```

### What's Supported
`{{ page.metadata.xxx }}`, `{{ page.title }}`, `{{ site.config.xxx }}`

### Not Supported
Conditionals (`{% if %}`), loops (`{% for %}`), complex logic → use templates instead

### Design Rationale
Separation of concerns (like Hugo) - content uses simple variables, templates handle logic. Code blocks remain literal without escaping.

## Parser Performance Comparison

| Parser | Time (78 pages) | Throughput | Features |
|--------|----------------|------------|----------|
| python-markdown | 3.78s | 20.6 pages/s | 100% (attribute lists) |
| **mistune** | **2.18s** | **35.8 pages/s** | 95% (no attribute lists) |

Mistune is recommended for most use cases due to faster performance.

## Template Engine (`bengal/rendering/template_engine.py`)

- Jinja2-based templating
- Supports nested templates and partials
- 75 custom template functions organized in focused modules
- Multiple template directories (custom, theme, default)
- Template dependency tracking for incremental builds
- Tracks includes, extends, and imports automatically

### Behavior Notes

- Bytecode cache: When enabled (default), compiled templates are cached under `output/.bengal-cache/templates` for faster rebuilds. Jinja2 invalidates entries when source templates change.
- Strict/auto-reload: `strict_mode` enables `StrictUndefined` to surface missing variables; `dev_server` enables `auto_reload` for fast iteration.
- Include/extends cycles: Cycle detection relies on Jinja2. Recursive includes or self-extends surface as `TemplateError` or `RecursionError` at render time and are logged with context.

## Renderer (`bengal/rendering/renderer.py`)

- Applies templates to pages
- Determines which template to use based on page metadata
- Fallback rendering for error cases

## Pipeline Coordinator (`bengal/rendering/pipeline.py`)

- Orchestrates all stages for each page
- Handles output path determination
- Writes final output to disk
- Integrates with DependencyTracker for incremental builds
- Tracks template usage during rendering

## Template Functions (`bengal/rendering/template_functions/`)

### Purpose
Provide 75+ custom filters and functions for Jinja2 templates

### Organization
- Modular design with self-registering modules
- 17 focused modules, each with single responsibility
- No monolithic classes
- Comprehensive testing (335+ tests)

### Architecture Principles
- **Built on Utilities**: Many functions delegate to `bengal/utils/` modules for consistent behavior
- **Type Safety**: Full type hints throughout
- **Error Handling**: Graceful fallbacks and error messages
- **Testing**: 71-98% coverage across function modules

### Module Breakdown (17 modules, 75+ functions total)

| Module | Functions | Description |
|--------|-----------|-------------|
| **strings.py** | 11 | `truncatewords`, `slugify`, `markdownify`, `strip_html`, `excerpt`, `reading_time` (uses `bengal.utils.text`) |
| **collections.py** | 8 | `where`, `where_not`, `group_by`, `sort_by`, `limit`, `offset`, `uniq`, `flatten` |
| **math_functions.py** | 6 | `percentage`, `times`, `divided_by`, `ceil`, `floor`, `round` |
| **dates.py** | 3 | `time_ago`, `date_iso`, `date_rfc822` (uses `bengal.utils.dates`) |
| **urls.py** | 3 | `absolute_url`, `url_encode`, `url_decode` |
| **content.py** | 6 | `safe_html`, `html_escape`, `html_unescape`, `nl2br`, `smartquotes`, `emojify` (uses `bengal.utils.text`) |
| **data.py** | 8 | `get_data`, `jsonify`, `merge`, `has_key`, `get_nested`, `keys`, `values`, `items` (uses `bengal.utils.file_io`) |
| **advanced_strings.py** | 5 | `camelize`, `underscore`, `titleize`, `wrap_text`, `indent_text` |
| **files.py** | 3 | `read_file`, `file_exists`, `file_size` (uses `bengal.utils.file_io`) |
| **advanced_collections.py** | 3 | `sample`, `shuffle`, `chunk` |
| **images.py** | 6 | `image_url`, `image_dimensions`, `image_srcset`, `image_srcset_gen`, `image_alt`, `image_data_uri` |
| **seo.py** | 4 | `meta_description`, `meta_keywords`, `canonical_url`, `og_image` |
| **debug.py** | 3 | `debug`, `typeof`, `inspect` |
| **taxonomies.py** | 4 | `related_posts`, `popular_tags`, `tag_url`, `has_tag` (uses `bengal.utils.text`) |
| **pagination_helpers.py** | 3 | `paginate`, `page_url`, `page_range` |
| **crossref.py** | 5 | `ref`, `doc`, `anchor`, `relref`, internal linking helpers |
| **navigation.py** | 4 | `breadcrumbs`, `active_menu`, `menu_tree`, navigation helpers |

**Total**: 75+ functions across 17 modules
