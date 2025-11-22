# Design: Direct HTML Autodoc Generation

## Overview

This design replaces Bengal's complex Markdown+Jinja2 autodoc templates with direct HTML generation while maintaining full integration with Bengal's page system. The approach uses "synthetic pages" - real Page objects with generated HTML content that participate fully in Bengal's build pipeline.

## Architecture

### High-Level Flow

```
DocElement (AST) → HTMLRenderer → HTML Content → SyntheticPage → Bengal Pipeline → Public Directory
```

Instead of:
```
DocElement → Jinja2+MD Template → Markdown → Bengal Parser → HTML → Page
```

### Output Path Management

**Critical Requirement**: Synthetic pages must be generated in the correct output directory structure without overwriting existing site directories.

**Key Principles**:
- Synthetic pages are created as virtual Page objects during content discovery
- They participate in Bengal's normal build pipeline
- Final HTML output goes to `site/public/` directory (not source directories)
- URL generation must not conflict with existing site structure
- Must preserve existing `config/`, `content/`, and other source directories

### Core Components

#### 1. HTMLRenderer System

**Purpose**: Generate clean HTML directly from DocElement objects

```python
# bengal/autodoc/html_renderer.py

class HTMLRenderer:
    """Renders DocElements directly to HTML."""

    def render_module(self, element: DocElement) -> str:
        """Render module to complete HTML."""

    def render_class(self, element: DocElement) -> str:
        """Render class to complete HTML."""

    def render_function(self, element: DocElement) -> str:
        """Render function to complete HTML."""

class ComponentRenderer:
    """Renders individual HTML components."""

    def render_parameters_table(self, args: list) -> str:
        """Generate parameters table HTML."""

    def render_inheritance_chain(self, bases: list) -> str:
        """Generate inheritance display HTML."""

    def render_examples_section(self, examples: list) -> str:
        """Generate examples section HTML."""
```

#### 2. SyntheticPage System

**Purpose**: Create real Page objects from generated HTML that integrate fully with Bengal

```python
# bengal/core/synthetic_page.py

class SyntheticPage(Page):
    """Page object created from generated content rather than source file."""

    def __init__(self,
                 url_path: str,
                 html_content: str,
                 metadata: dict,
                 source_info: dict):
        # Create page without source file
        # Set rendered_html directly
        # Populate all required Page attributes

    @property
    def source_path(self) -> Path:
        """Return virtual source path for compatibility."""
        return Path(f"<generated>/{self.url_path}")

    @property
    def content_hash(self) -> str:
        """Hash based on generated content for caching."""
        return hashlib.sha256(self.html_content.encode()).hexdigest()
```

#### 3. Enhanced AutodocGenerator

**Purpose**: Orchestrate HTML generation and page creation

```python
# bengal/autodoc/generator.py (modified)

class AutodocGenerator:
    def __init__(self, config: dict):
        self.html_renderer = HTMLRenderer(config)
        self.synthetic_pages = []

    def generate_pages(self, elements: list[DocElement]) -> list[SyntheticPage]:
        """Generate synthetic pages from doc elements."""
        pages = []

        for element in elements:
            # Generate HTML directly
            html_content = self.html_renderer.render(element)

            # Create metadata
            metadata = self._build_metadata(element)

            # Create synthetic page
            page = SyntheticPage(
                url_path=self._get_url_path(element),
                html_content=html_content,
                metadata=metadata,
                source_info={'generator': 'autodoc', 'element_type': element.element_type}
            )

            pages.append(page)

        return pages
```

### Integration Points

#### 1. Discovery Phase Integration

```python
# bengal/discovery/content_discovery.py (modified)

class ContentDiscovery:
    def discover_all_content(self) -> tuple[list[Page], list[Section]]:
        # Existing file-based discovery
        file_pages, sections = self._discover_file_content()

        # Add autodoc synthetic pages
        if self.config.get('autodoc', {}).get('enabled'):
            autodoc_pages = self._discover_autodoc_content()
            file_pages.extend(autodoc_pages)

        return file_pages, sections

    def _discover_autodoc_content(self) -> list[SyntheticPage]:
        """Generate autodoc synthetic pages."""
        generator = AutodocGenerator(self.config)

        # Extract documentation elements
        elements = generator.extract_elements()

        # Generate synthetic pages
        return generator.generate_pages(elements)
```

#### 2. Caching Integration

```python
# Synthetic pages participate in incremental builds
class SyntheticPage(Page):
    def needs_rebuild(self, cache: BuildCache) -> bool:
        """Check if synthetic page needs regeneration."""
        # Check source file timestamps
        # Check config changes
        # Check template changes (if any)

    def get_cache_key(self) -> str:
        """Unique cache key for synthetic page."""
        return f"autodoc:{self.element_type}:{self.source_info['module']}:{self.name}"
```

#### 3. Navigation Integration

Synthetic pages automatically participate in navigation because they're real Page objects:

```python
# No changes needed - existing navigation system works
# Pages have proper URLs, titles, sections, etc.
```

## HTML Generation Strategy

### Option 1: Template-Based HTML (Recommended)

Use simple HTML templates instead of Markdown+Jinja2:

```html
<!-- bengal/autodoc/html_templates/module.html -->
<article class="autodoc-module">
    <header class="module-header">
        <h1>{{ element.name }}</h1>
        <p class="module-path">{{ element.source_file }}</p>
    </header>

    {% if element.description %}
    <div class="module-description">
        {{ element.description | markdown }}
    </div>
    {% endif %}

    {% if classes %}
    <section class="classes-section">
        <h2>Classes</h2>
        {% for cls in classes %}
            {{ render_class(cls) }}
        {% endfor %}
    </section>
    {% endif %}
</article>
```

**Benefits**:
- Much simpler than current templates
- Direct HTML control
- Still templateable for customization
- Familiar Jinja2 syntax

### Option 2: Programmatic HTML Generation

Generate HTML directly in Python:

```python
class HTMLRenderer:
    def render_module(self, element: DocElement) -> str:
        html = HTMLBuilder()

        html.article(class_="autodoc-module")
        html.header(class_="module-header")
        html.h1(element.name)
        html.p(element.source_file, class_="module-path")
        html.close_header()

        if element.description:
            html.div(class_="module-description")
            html.raw(markdown(element.description))
            html.close_div()

        # ... continue building

        return html.build()
```

**Benefits**:
- Full programmatic control
- Type safety
- Easy to test
- No template files to maintain

### Recommended Approach: Hybrid

- Use simple HTML templates for layout structure
- Use programmatic generation for complex components (tables, inheritance trees)
- Keep templates under 50 lines each

## Error Handling & Reliability

### Robust HTML Generation

```python
class HTMLRenderer:
    def render(self, element: DocElement) -> str:
        try:
            html = self._render_element(element)

            # Validate HTML
            self._validate_html(html)

            return html

        except Exception as e:
            # Generate error page instead of failing
            return self._render_error_page(element, e)

    def _validate_html(self, html: str) -> None:
        """Validate generated HTML."""
        # Basic HTML validation
        # Check for unclosed tags
        # Verify structure
```

### Graceful Degradation

```python
def _render_error_page(self, element: DocElement, error: Exception) -> str:
    """Generate error page when rendering fails."""
    return f"""
    <article class="autodoc-error">
        <h1>Documentation Generation Error</h1>
        <p>Failed to generate documentation for {element.name}</p>
        <details>
            <summary>Error Details</summary>
            <pre>{str(error)}</pre>
        </details>
    </article>
    """
```

## Migration Strategy

### Phase 1: Parallel Implementation

1. Implement HTMLRenderer system alongside existing templates
2. Add feature flag: `autodoc.use_html_renderer = true`
3. Test with Bengal's own documentation
4. Compare output quality

### Phase 2: Switch Default

1. Make HTML renderer the default
2. Keep Markdown templates as fallback option
3. Update documentation and examples

### Phase 3: Cleanup

1. Remove Markdown template system
2. Clean up related code
3. Update tests

## Benefits of This Approach

### 1. Eliminates Template Complexity
- No more 300+ line Jinja2+Markdown templates
- Simple HTML templates or programmatic generation
- Much easier to maintain and debug

### 2. Maintains Full Integration
- SyntheticPage objects are real Pages
- Automatic participation in navigation, search, health checks
- Full support for output formats (JSON, LLM text)
- Incremental build support

### 3. Improves Reliability
- Direct HTML generation eliminates Markdown parsing issues
- Better error handling and graceful degradation
- Validation of generated HTML

### 4. Preserves Performance
- No additional parsing steps
- Caching at the HTML level
- Parallel generation support

### 5. Maintains Customization
- HTML templates can still be overridden
- Programmatic hooks for custom rendering
- Theme system integration

## Implementation Considerations

### Styling Integration

Generated HTML needs to work with Bengal's theme system:

```python
class HTMLRenderer:
    def __init__(self, config: dict):
        self.theme_classes = self._load_theme_classes(config)

    def _load_theme_classes(self, config: dict) -> dict:
        """Load CSS classes from theme configuration."""
        # Read theme-specific class mappings
        # Allow customization of generated HTML classes
```

### Content Processing

Some content still needs processing (markdown in docstrings):

```python
def render_description(self, description: str) -> str:
    """Process description text."""
    # Apply markdown processing
    # Handle cross-references
    # Process code blocks
    return processed_html
```

This design should solve your core issues while maintaining all the integration benefits that make Bengal's autodoc unique.
