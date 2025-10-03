# Jinja2 Preprocessing - Non-Brittle Architecture

**Date:** October 3, 2025  
**Status:** Architectural Design

---

## Problem Analysis

### What We Built (Quick Fix)
```python
# Ad-hoc preprocessing in pipeline
def _preprocess_content(self, page: Page) -> str:
    if page.metadata.get('preprocess') is False:  # Per-page flag
        return page.content
    
    try:
        template = Template(page.content)
        return template.render(page=page, site=self.site, config=self.site.config)
    except Exception:
        return page.content  # Silent failure
```

**Issues:**
- ❌ Per-page flags (doesn't scale, easy to forget)
- ❌ Try/except error handling (reactive, not proactive)
- ❌ No validation phase (errors found during rendering)
- ❌ Mixed concerns (preprocessing + parsing in same stage)
- ❌ No clear content type distinction (docs vs content)

---

## Bengal's Architecture Principles

From `ARCHITECTURE.md` and recent brittleness fixes:

1. **Modular Architecture** - No God objects, single responsibility
2. **Clear Stage Separation** - Each pipeline stage has one job
3. **Factory Pattern** - Select implementations via config (like parsers)
4. **Validation at Boundaries** - Catch errors before processing
5. **Environment-Based Behavior** - Not per-file flags
6. **Graceful Degradation** - With helpful warnings
7. **Developer Experience** - Fail fast in dev, warn in production
8. **Type Safety** - Strong boundaries, clear contracts

---

## Non-Brittle Solution: Content Type System

### Core Insight

**The real problem:** Not all markdown is the same.

```
Regular Content:         Technical Docs:          Examples/Tests:
- Blog posts            - Template guides        - Jinja2 examples
- Documentation         - API references         - Test fixtures
- Product pages         - HOWTOs                - Code samples
                        
Should preprocess:      Should NOT preprocess:   Never preprocess:
✅ Yes (dynamic)        ❌ No (shows syntax)     ❌ Never (literal)
```

### Solution: Content Type Classification

**Like parser selection, but for preprocessing behavior.**

```toml
[build]
# Preprocessing modes (like markdown_engine)
preprocess_mode = "auto"  # Options: "auto", "all", "none", "smart"

# Content type patterns (like asset fingerprinting)
[preprocessing]
# Patterns for content that should NOT be preprocessed
skip_patterns = [
    "docs/template-*.md",      # Template documentation
    "examples/**/*.md",        # Code examples  
    "tests/**/*.md",           # Test fixtures
]

# OR use content types (like Hugo)
[preprocessing.by_type]
"page" = true          # Regular pages: preprocess
"post" = true          # Blog posts: preprocess  
"docs" = false         # Documentation: skip
"example" = false      # Examples: skip
```

---

## Architecture Design

### 1. Preprocessing Strategy (Factory Pattern)

**Follow parser pattern from `bengal/rendering/parser.py`:**

```python
# bengal/rendering/preprocessor.py (NEW)

from abc import ABC, abstractmethod
from typing import Dict, Any
from bengal.core.page import Page

class PreprocessingStrategy(ABC):
    """Base class for content preprocessing strategies."""
    
    @abstractmethod
    def should_preprocess(self, page: Page) -> bool:
        """Determine if page should be preprocessed."""
        pass
    
    @abstractmethod
    def preprocess(self, page: Page, context: Dict[str, Any]) -> str:
        """Preprocess page content."""
        pass


class NoPreprocessing(PreprocessingStrategy):
    """Skip all preprocessing."""
    
    def should_preprocess(self, page: Page) -> bool:
        return False
    
    def preprocess(self, page: Page, context: Dict[str, Any]) -> str:
        return page.content


class Jinja2Preprocessing(PreprocessingStrategy):
    """Preprocess with Jinja2 templates."""
    
    def __init__(self, skip_patterns: list = None):
        self.skip_patterns = skip_patterns or []
        self._compile_patterns()
    
    def should_preprocess(self, page: Page) -> bool:
        """Check if page matches skip patterns."""
        # Check explicit frontmatter first (escape hatch)
        if page.metadata.get('preprocess') is False:
            return False
        
        # Check skip patterns
        page_path = str(page.source_path)
        for pattern in self.compiled_patterns:
            if pattern.match(page_path):
                return False
        
        # Default: preprocess if has Jinja2 syntax
        return '{{' in page.content or '{%' in page.content
    
    def preprocess(self, page: Page, context: Dict[str, Any]) -> str:
        """Preprocess with Jinja2."""
        from jinja2 import Template, TemplateSyntaxError, UndefinedError
        
        try:
            template = Template(page.content)
            return template.render(**context)
        
        except TemplateSyntaxError as e:
            raise PreprocessingError(
                f"Jinja2 syntax error in {page.source_path}:{e.lineno}\n"
                f"  {e.message}"
            )
        
        except UndefinedError as e:
            raise PreprocessingError(
                f"Undefined variable in {page.source_path}: {e}"
            )


class SmartPreprocessing(Jinja2Preprocessing):
    """Intelligent preprocessing based on content type."""
    
    def should_preprocess(self, page: Page) -> bool:
        """Smart detection based on content type and patterns."""
        # Explicit frontmatter wins
        if 'preprocess' in page.metadata:
            return page.metadata['preprocess']
        
        # Check content type
        content_type = page.metadata.get('type', 'page')
        if content_type in ['docs', 'example', 'test']:
            return False
        
        # Check patterns
        if super()._matches_skip_pattern(page):
            return False
        
        # Check if it looks like documentation
        if self._looks_like_docs(page):
            return False
        
        # Has Jinja2 syntax?
        return '{{' in page.content or '{%' in page.content
    
    def _looks_like_docs(self, page: Page) -> bool:
        """Heuristic: does page look like Jinja2 documentation?"""
        content = page.content
        
        # Count code blocks with Jinja2 syntax
        jinja_in_code = content.count('```jinja') + content.count('```html')
        
        # Count raw Jinja2 syntax
        jinja_raw = content.count('{{') + content.count('{%')
        
        # If most Jinja2 is in code blocks, probably docs
        return jinja_in_code > 3 and jinja_raw > jinja_in_code * 2


# Factory function (like create_markdown_parser)
def create_preprocessor(mode: str = 'auto', config: Dict[str, Any] = None) -> PreprocessingStrategy:
    """
    Create preprocessing strategy based on mode.
    
    Args:
        mode: 'auto', 'all', 'none', 'smart'
        config: Configuration dict with skip_patterns, etc.
    """
    config = config or {}
    
    if mode == 'none':
        return NoPreprocessing()
    
    elif mode == 'smart':
        return SmartPreprocessing(
            skip_patterns=config.get('skip_patterns', [])
        )
    
    elif mode in ('auto', 'all'):
        return Jinja2Preprocessing(
            skip_patterns=config.get('skip_patterns', [])
        )
    
    else:
        raise ValueError(f"Unknown preprocessing mode: {mode}")
```

### 2. Validation Phase (Separate Stage)

**Add validation BEFORE rendering pipeline:**

```python
# bengal/rendering/preprocessor.py

class PreprocessingValidator:
    """Validate Jinja2 syntax before rendering."""
    
    def validate_page(self, page: Page) -> list[str]:
        """
        Validate Jinja2 syntax without rendering.
        
        Returns:
            List of error messages (empty if valid)
        """
        from jinja2 import Template, TemplateSyntaxError
        
        if not ('{{' in page.content or '{%' in page.content):
            return []  # No Jinja2 syntax
        
        errors = []
        
        try:
            # Compile template (fast, no rendering)
            Template(page.content)
        
        except TemplateSyntaxError as e:
            errors.append(
                f"Line {e.lineno}: {e.message}\n"
                f"  {self._get_snippet(page.content, e.lineno)}"
            )
        
        except Exception as e:
            errors.append(f"Parse error: {e}")
        
        return errors
    
    def validate_site(self, pages: list[Page], preprocessor: PreprocessingStrategy) -> Dict[str, list[str]]:
        """
        Validate all pages that will be preprocessed.
        
        Returns:
            Dict mapping page paths to error lists
        """
        errors = {}
        
        for page in pages:
            if preprocessor.should_preprocess(page):
                page_errors = self.validate_page(page)
                if page_errors:
                    errors[str(page.source_path)] = page_errors
        
        return errors
    
    def _get_snippet(self, content: str, lineno: int, context: int = 2) -> str:
        """Get code snippet around error line."""
        lines = content.split('\n')
        start = max(0, lineno - context - 1)
        end = min(len(lines), lineno + context)
        
        snippet = []
        for i in range(start, end):
            marker = ">>> " if i == lineno - 1 else "    "
            snippet.append(f"{marker}{i+1:3d}| {lines[i]}")
        
        return '\n  '.join(snippet)
```

### 3. Integration with Pipeline

**Update `RenderingPipeline` to use strategy:**

```python
# bengal/rendering/pipeline.py

class RenderingPipeline:
    
    def __init__(self, site, dependency_tracker=None, quiet=False, build_stats=None):
        self.site = site
        self.parser = _get_thread_parser(site.config.get('markdown_engine'))
        self.dependency_tracker = dependency_tracker
        self.quiet = quiet
        self.build_stats = build_stats
        self.template_engine = TemplateEngine(site)
        self.renderer = Renderer(self.template_engine)
        
        # Create preprocessing strategy
        preprocess_mode = site.config.get('preprocess_mode', 'auto')
        preprocess_config = site.config.get('preprocessing', {})
        self.preprocessor = create_preprocessor(preprocess_mode, preprocess_config)
    
    def process_page(self, page: Page) -> None:
        """Process page through rendering pipeline."""
        # Determine output path
        if not page.output_path:
            page.output_path = self._determine_output_path(page)
        
        # STAGE 1: Preprocess (if needed)
        content = page.content
        if self.preprocessor.should_preprocess(page):
            content = self._preprocess_content(page)
        
        # STAGE 2: Parse markdown
        parsed_content, toc = self.parser.parse_with_toc(content, page.metadata)
        page.parsed_ast = parsed_content
        page.toc = toc
        page.toc_items = self._extract_toc_structure(toc)
        
        # STAGE 3: Extract links
        page.extract_links()
        
        # STAGE 4: Render to HTML
        html_content = self.renderer.render_content(parsed_content)
        
        # STAGE 5: Apply template
        page.rendered_html = self.renderer.render_page(page, html_content)
        
        # STAGE 6: Write output
        self._write_output(page)
    
    def _preprocess_content(self, page: Page) -> str:
        """Preprocess page content using strategy."""
        try:
            context = {
                'page': page,
                'site': self.site,
                'config': self.site.config
            }
            return self.preprocessor.preprocess(page, context)
        
        except PreprocessingError as e:
            # Log to build stats
            if self.build_stats:
                self.build_stats.add_warning(
                    str(page.source_path), 
                    str(e), 
                    'jinja2'
                )
            
            # Check strict mode
            strict = self.site.config.get('strict_preprocessing', False)
            if strict:
                raise  # Fail build in strict mode
            
            # Warn and continue with original content
            if not self.quiet:
                print(f"⚠️  {e}")
            
            return page.content
```

### 4. Site-Level Validation

**Add validation to Site.build():**

```python
# bengal/core/site.py

def build(self, parallel=True, incremental=False, verbose=False):
    """Build site with preprocessing validation."""
    # ... existing discovery code ...
    
    # VALIDATE PREPROCESSING (early, before render)
    if self.config.get('validate_preprocessing', True):
        validation_start = time.time()
        validation_errors = self._validate_preprocessing()
        
        if validation_errors:
            print(f"\n⚠️  Preprocessing Validation Errors ({len(validation_errors)}):")
            for path, errors in list(validation_errors.items())[:5]:
                print(f"  • {path}")
                for error in errors:
                    print(f"    {error}")
            
            if len(validation_errors) > 5:
                print(f"  ... and {len(validation_errors) - 5} more")
            
            if self.config.get('strict_preprocessing', False):
                raise BuildValidationError(
                    f"{len(validation_errors)} preprocessing validation error(s)"
                )
            else:
                print("  (Continuing build - disable with strict_preprocessing=true)")
    
    # ... rest of build ...


def _validate_preprocessing(self) -> Dict[str, list[str]]:
    """Validate all pages that will be preprocessed."""
    from bengal.rendering.preprocessor import PreprocessingValidator, create_preprocessor
    
    # Create validator and strategy
    validator = PreprocessingValidator()
    preprocessor = create_preprocessor(
        self.config.get('preprocess_mode', 'auto'),
        self.config.get('preprocessing', {})
    )
    
    # Validate all pages
    return validator.validate_site(self.pages, preprocessor)
```

---

## Configuration

### Minimal (Auto Mode - Default)
```toml
# bengal.toml
[site]
title = "My Site"

# Preprocessing happens automatically for pages with Jinja2 syntax
# Documentation pages use type: "docs" in frontmatter to skip
```

### Explicit Patterns
```toml
[preprocessing]
mode = "auto"  # "auto", "smart", "all", "none"

# Skip preprocessing for these patterns
skip_patterns = [
    "docs/template-*.md",
    "examples/**/*.md",
]

# Strict mode (fail on errors)
strict = false  # true in CI/CD
```

### Smart Mode (Heuristic)
```toml
[preprocessing]
mode = "smart"  # Auto-detect documentation pages

# Smart mode uses heuristics:
# - Content type from frontmatter
# - Jinja2 in code blocks vs raw
# - File path patterns
```

---

## Benefits of This Architecture

### 1. **Follows Bengal Patterns** ✅
- Factory pattern (like parsers)
- Strategy pattern (pluggable)
- Validation at boundaries
- Clear stage separation

### 2. **Non-Brittle** ✅
- No per-page flags to remember
- Pattern-based configuration (scales)
- Validation before rendering (fail fast)
- Clear error messages with context

### 3. **Developer Experience** ✅
- Automatic in most cases
- Clear errors with line numbers
- Helpful suggestions
- Escape hatch (frontmatter) when needed

### 4. **Production Safe** ✅
- Warnings by default (continue building)
- Strict mode for CI/CD
- Graceful degradation
- No silent failures

### 5. **Performance** ✅
- Early validation (don't waste time on broken pages)
- Pattern matching is fast
- Caching opportunities (compiled patterns)
- No redundant checks

### 6. **Extensible** ✅
- Easy to add new strategies
- Custom preprocessors possible
- Pluggable validation
- Future: Velocity, Liquid, etc.

---

## Migration Path

### Phase 1: Core Infrastructure (This Week)
- [ ] Create `bengal/rendering/preprocessor.py`
- [ ] Implement `PreprocessingStrategy` hierarchy
- [ ] Add `create_preprocessor()` factory
- [ ] Integrate with `RenderingPipeline`

### Phase 2: Validation (This Week)  
- [ ] Implement `PreprocessingValidator`
- [ ] Add site-level validation phase
- [ ] Integrate with `BuildStats`
- [ ] Add helpful error messages

### Phase 3: Smart Mode (Next Week)
- [ ] Implement `SmartPreprocessing`
- [ ] Add heuristics for documentation detection
- [ ] Test with real documentation sites
- [ ] Tune detection accuracy

### Phase 4: Testing (Next Week)
- [ ] Unit tests for all strategies
- [ ] Integration tests with quickstart
- [ ] Performance benchmarks
- [ ] Documentation and examples

---

## Comparison

### Current (Brittle)
```python
# Ad-hoc, reactive
if page.metadata.get('preprocess') is False:  # Per-page
    return page.content

try:
    return Template(page.content).render(...)
except:
    return page.content  # Silent failure
```

### Proposed (Robust)
```python
# Strategy pattern, proactive
strategy = create_preprocessor(config.get('preprocess_mode'))

if strategy.should_preprocess(page):  # Pattern-based
    try:
        return strategy.preprocess(page, context)
    except PreprocessingError as e:
        log_warning(e)  # Clear error
        if strict_mode:
            raise  # Fail in CI
        return page.content  # Graceful
```

---

## Conclusion

This architecture:

1. **Follows Bengal principles** - Modular, clear stages, validation at boundaries
2. **Scales better** - Pattern-based, not per-file flags
3. **Fails better** - Early validation, clear errors, helpful messages
4. **Flexible** - Multiple strategies, extensible
5. **Safe** - Graceful degradation, strict mode for CI

**Result:** A non-brittle, maintainable solution that fits Bengal's architecture.

