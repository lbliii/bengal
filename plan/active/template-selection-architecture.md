# Template Selection Architecture Analysis

## Current State

### Problem: Disconnect Between Architecture and Implementation

**Architecture Docs** (`architecture/content-types.md`) describe:
- Content strategies should have `get_template(page: Page)` method
- Strategies handle template selection for different page types (home, list, single)
- Fully extensible via strategy registration

**Current Implementation** (`bengal/rendering/renderer.py`):
- Hardcoded `type_mappings` dict in `_get_template_name()`
- Hardcoded template naming conventions (`{type}/home.html`, `{type}/list.html`, `{type}/single.html`)
- Special-case logic for home pages
- **Does NOT delegate to content type strategies** for template selection

**Content Type Strategies** (`bengal/content_types/`):
- Have `get_template()` method but it takes no `page` parameter
- Only returns a single template name (e.g., `"blog/list.html"`)
- **Not used by Renderer** for template selection

### Issues with Current Approach

1. **Duplication**: Template selection logic duplicated in Renderer instead of in strategies
2. **Hardcoded mappings**: `type_mappings` dict requires code changes to add new archetypes
3. **Inconsistent**: Strategies exist but aren't used for their primary purpose (template selection)
4. **Not extensible**: Adding new archetype requires modifying Renderer code
5. **Maintenance burden**: Template selection logic scattered across Renderer (150+ lines)

## Proposed Solution: Strategy-Based Template Selection

### Core Principle

**Delegate template selection to content type strategies**, matching the architecture docs.

### Implementation Plan

#### 1. Update ContentTypeStrategy Interface

```python
# bengal/content_types/base.py

class ContentTypeStrategy:
    """Base strategy for content type behavior."""

    # ... existing methods ...

    def get_template(self, page: Page, template_engine: TemplateEngine) -> str:
        """
        Determine which template to use for a page.

        Args:
            page: Page to get template for
            template_engine: Template engine for checking template existence

        Returns:
            Template name (e.g., "blog/home.html", "doc/single.html")

        Default implementation provides sensible fallbacks:
        - Home pages: try {type}/home.html, then home.html, then index.html
        - Section indexes: try {type}/list.html, then list.html
        - Regular pages: try {type}/single.html, then single.html
        """
        is_home = page.is_home or page.url == "/"
        is_section_index = page.source_path.stem == "_index"

        # Get type name (e.g., "blog", "doc")
        type_name = self._get_type_name()

        if is_home:
            templates_to_try = [
                f"{type_name}/home.html",
                f"{type_name}/index.html",
                "home.html",
                "index.html",
            ]
        elif is_section_index:
            templates_to_try = [
                f"{type_name}/list.html",
                f"{type_name}/index.html",
                "list.html",
                "index.html",
            ]
        else:
            templates_to_try = [
                f"{type_name}/single.html",
                f"{type_name}/page.html",
                "single.html",
                "page.html",
            ]

        # Try each template in order
        for template_name in templates_to_try:
            if template_engine.template_exists(template_name):
                return template_name

        # Final fallback
        return "index.html"

    def _get_type_name(self) -> str:
        """Get the type name for this strategy (e.g., "blog", "doc")."""
        # Default: use class name minus "Strategy"
        class_name = self.__class__.__name__
        return class_name.replace("Strategy", "").lower()
```

#### 2. Update Concrete Strategies

```python
# bengal/content_types/strategies.py

class BlogStrategy(ContentTypeStrategy):
    """Strategy for blog/news content."""

    def get_template(self, page: Page, template_engine: TemplateEngine) -> str:
        """Blog-specific template selection."""
        is_home = page.is_home or page.url == "/"
        is_section_index = page.source_path.stem == "_index"

        if is_home:
            # Try blog/home.html first
            if template_engine.template_exists("blog/home.html"):
                return "blog/home.html"
            # Fallback to generic home
            return super().get_template(page, template_engine)
        elif is_section_index:
            return "blog/list.html"
        else:
            return "blog/single.html"

class DocsStrategy(ContentTypeStrategy):
    """Strategy for documentation."""

    def get_template(self, page: Page, template_engine: TemplateEngine) -> str:
        """Docs-specific template selection."""
        is_home = page.is_home or page.url == "/"
        is_section_index = page.source_path.stem == "_index"

        if is_home:
            # Try doc/home.html first
            if template_engine.template_exists("doc/home.html"):
                return "doc/home.html"
            # Fallback to generic home
            return super().get_template(page, template_engine)
        elif is_section_index:
            return "doc/list.html"
        else:
            return "doc/single.html"
```

#### 3. Update Renderer to Delegate

```python
# bengal/rendering/renderer.py

def _get_template_name(self, page: Page) -> str:
    """
    Determine which template to use for a page.

    Priority order:
    1. Explicit template in frontmatter
    2. Content type strategy (NEW - delegates to strategy)
    3. Section-based auto-detection
    4. Default fallback
    """
    # 1. Explicit template (highest priority)
    if "template" in page.metadata:
        return page.metadata["template"]

    # 2. Get content type strategy and delegate
    page_type = page.metadata.get("type")
    content_type = None

    if hasattr(page, "_section") and page._section:
        content_type = page._section.metadata.get("content_type")

    # Determine which strategy to use
    from bengal.content_types.registry import get_strategy

    # Prefer page type over section content_type
    strategy_type = page_type or content_type or "page"
    strategy = get_strategy(strategy_type)

    # Delegate to strategy
    template_name = strategy.get_template(page, self._template_engine)
    if template_name:
        return template_name

    # 3. Section-based fallback (existing logic)
    # ... keep existing section-based detection ...

    # 4. Final fallback
    return "index.html"
```

#### 4. Add Template Engine Access

```python
# bengal/rendering/renderer.py

class Renderer:
    def __init__(self, template_engine: TemplateEngine):
        self._template_engine = template_engine

    # Expose template_exists for strategies
    def _template_exists(self, name: str) -> bool:
        return self._template_engine.template_exists(name)
```

### Key Considerations

1. **Section orchestrator dependency**: `bengal/orchestration/section.py` still calls `strategy.get_template()` while generating synthetic archive/index pages. When we change the method signature to accept `(page, template_engine)`, we must either:
   - pass the generated `Page` instance and renderer/template-engine context into the orchestrator, or
   - provide a backward-compatible shim so auto-generated pages continue to receive a list template without needing a renderer.
2. **Renderer already exposes template checks**: `Renderer._template_exists()` is a thin wrapper around `self.template_engine.env.get_template(...)`, so Step 4 (“Add Template Engine Access”) should reuse this helper or rename `self.template_engine` to `_template_engine`—that keeps the surface area unchanged.
3. **Test impact**: `tests/unit/rendering/test_renderer_template_selection.py` and `tests/unit/content_types/test_strategies.py` assert today’s fixed selection logic. Add explicit steps in the migration plan for updating or replacing those tests once strategy delegation takes over to avoid regressions.

### Benefits

1. **Single Responsibility**: Strategies own template selection logic
2. **Extensibility**: New archetypes just register a strategy - no Renderer changes
3. **Consistency**: Matches architecture docs
4. **Maintainability**: Template logic centralized in strategies
5. **Testability**: Strategies can be tested independently
6. **Flexibility**: Strategies can override defaults per page type

### Migration Path

1. **Phase 1**: Add `get_template(page, template_engine)` to base strategy with default implementation
2. **Phase 2**: Update concrete strategies to override `get_template()` where needed
3. **Phase 3**: Update Renderer to delegate to strategies
4. **Phase 4**: Remove hardcoded `type_mappings` from Renderer
5. **Phase 5**: Update tests

### Backward Compatibility

- Default strategy implementation provides same fallback behavior
- Existing templates continue to work
- Explicit `template:` frontmatter still takes priority
- Section-based detection still works as fallback

## Alternative: Keep Current Approach

### Pros
- Already implemented
- Works for current use cases
- No refactoring needed

### Cons
- Doesn't match architecture docs
- Not extensible (requires code changes)
- Duplicated logic
- Harder to test

## Recommendation

**Implement strategy-based template selection** because:
1. Matches documented architecture
2. More extensible and maintainable
3. Better separation of concerns
4. Enables custom archetypes without core changes
5. Cleaner codebase long-term

The current approach is a **workaround** that works but doesn't scale. The strategy-based approach is the **proper solution** that aligns with Bengal's architecture.
