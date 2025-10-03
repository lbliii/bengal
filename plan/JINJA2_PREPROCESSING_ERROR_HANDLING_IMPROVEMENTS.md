# Jinja2 Preprocessing - Error Handling & Test Coverage Analysis

**Date:** October 3, 2025  
**Status:** Analysis & Recommendations

---

## Current State Assessment

### ✅ What's Working
1. **Error detection** - Catches `TemplateSyntaxError` and general exceptions
2. **Build stats tracking** - Warnings logged to `BuildStats` with categorization
3. **Health checks** - Post-build validation detects unrendered Jinja2 in output
4. **Warning display** - Grouped, colorful warnings shown at end of build
5. **Opt-out mechanism** - `preprocess: false` allows skipping preprocessing

### ❌ What's Missing

#### 1. **No Test Coverage** (Critical Gap)
- ❌ No tests for Jinja2 preprocessing feature
- ❌ No tests for `preprocess: false` flag
- ❌ No tests for cascade metadata + Jinja2 variables
- ❌ No tests for error handling in preprocessing
- ❌ No tests for malformed Jinja2 syntax detection

#### 2. **Silent Failures in Parallel Builds**
- ⚠️  Warnings printed but can be missed in parallel output
- ⚠️  Build continues even with preprocessing errors
- ⚠️  No way to fail fast on Jinja2 errors

#### 3. **Error Messages Could Be More Helpful**
- ⚠️  Error messages don't show the problematic line/snippet
- ⚠️  No context about what variables are available
- ⚠️  No suggestions for fixing the issue

#### 4. **Health Check Runs Too Late**
- ⚠️  Detects issues AFTER entire build completes
- ⚠️  Wasted time building other pages if one has errors

---

## Recommended Improvements

### Priority 1: Add Test Coverage (Critical)

**File:** `tests/unit/test_jinja2_preprocessing.py` (NEW)

```python
"""Test Jinja2 preprocessing in markdown content."""
import pytest
from pathlib import Path
from bengal.core.page import Page
from bengal.core.site import Site
from bengal.rendering.pipeline import RenderingPipeline


class TestJinja2Preprocessing:
    """Test Jinja2 variable substitution in markdown content."""
    
    def test_basic_variable_substitution(self, tmp_path):
        """Test that {{ page.metadata.xxx }} variables are rendered."""
        # Setup
        site = Site(root_path=tmp_path, config={})
        page = Page(
            source_path=tmp_path / "test.md",
            content="# {{ page.metadata.title }}\n\nBy {{ page.metadata.author }}",
            metadata={"title": "Test Page", "author": "John Doe"}
        )
        
        # Execute
        pipeline = RenderingPipeline(site)
        rendered = pipeline._preprocess_content(page)
        
        # Assert
        assert "# Test Page" in rendered
        assert "By John Doe" in rendered
        assert "{{" not in rendered  # No unrendered syntax
    
    def test_conditional_blocks(self, tmp_path):
        """Test that {% if %} blocks work in preprocessing."""
        site = Site(root_path=tmp_path, config={})
        page = Page(
            source_path=tmp_path / "test.md",
            content="""
{% if page.metadata.show_author %}
Author: {{ page.metadata.author }}
{% endif %}
            """,
            metadata={"show_author": True, "author": "Jane Doe"}
        )
        
        pipeline = RenderingPipeline(site)
        rendered = pipeline._preprocess_content(page)
        
        assert "Author: Jane Doe" in rendered
        assert "{%" not in rendered
    
    def test_cascade_metadata_in_preprocessing(self, tmp_path):
        """Test that cascade metadata is accessible in preprocessing."""
        site = Site(root_path=tmp_path, config={})
        page = Page(
            source_path=tmp_path / "api/endpoint.md",
            content="API Base: {{ page.metadata.api_base_url }}",
            metadata={
                "title": "Endpoint",
                "api_base_url": "https://api.example.com"  # From cascade
            }
        )
        
        pipeline = RenderingPipeline(site)
        rendered = pipeline._preprocess_content(page)
        
        assert "API Base: https://api.example.com" in rendered
    
    def test_preprocess_false_skips_rendering(self, tmp_path):
        """Test that preprocess: false disables preprocessing."""
        site = Site(root_path=tmp_path, config={})
        page = Page(
            source_path=tmp_path / "docs.md",
            content="Use {{ page.title }} to show the title",
            metadata={"title": "Docs", "preprocess": False}
        )
        
        pipeline = RenderingPipeline(site)
        rendered = pipeline._preprocess_content(page)
        
        # Should NOT be processed
        assert "{{ page.title }}" in rendered
    
    def test_syntax_error_returns_original_content(self, tmp_path):
        """Test that syntax errors don't break the build."""
        site = Site(root_path=tmp_path, config={})
        page = Page(
            source_path=tmp_path / "bad.md",
            content="{% if condition %} missing endif",
            metadata={"title": "Bad"}
        )
        
        from bengal.utils.build_stats import BuildStats
        stats = BuildStats()
        pipeline = RenderingPipeline(site, build_stats=stats)
        rendered = pipeline._preprocess_content(page)
        
        # Should return original content
        assert "{% if condition %}" in rendered
        
        # Should log warning
        assert len(stats.warnings) == 1
        assert stats.warnings[0].warning_type == 'jinja2'
    
    def test_undefined_variable_error_handling(self, tmp_path):
        """Test handling of undefined variables."""
        site = Site(root_path=tmp_path, config={})
        page = Page(
            source_path=tmp_path / "test.md",
            content="Value: {{ page.metadata.nonexistent }}",
            metadata={"title": "Test"}
        )
        
        from bengal.utils.build_stats import BuildStats
        stats = BuildStats()
        pipeline = RenderingPipeline(site, build_stats=stats)
        rendered = pipeline._preprocess_content(page)
        
        # Should log warning but continue
        # Jinja2 default is to render empty string for undefined vars
        assert "Value: " in rendered or len(stats.warnings) > 0
```

**File:** `tests/integration/test_jinja2_preprocessing_e2e.py` (NEW)

```python
"""End-to-end tests for Jinja2 preprocessing feature."""
import pytest
from pathlib import Path


class TestJinja2PreprocessingE2E:
    """Test full build with Jinja2 preprocessing."""
    
    def test_cascade_metadata_renders_in_output(self, quickstart_site):
        """Test that cascade metadata variables render in final HTML."""
        # Build site
        quickstart_site.build()
        
        # Check api/v2/_index.md output
        output = quickstart_site.output_dir / "api" / "v2" / "index.html"
        assert output.exists()
        
        content = output.read_text()
        
        # Should have rendered values, not template syntax
        assert "DataFlow API" in content
        assert "2.0" in content
        assert "2025-10-01" in content
        assert "{{ page.metadata" not in content  # No unrendered syntax
    
    def test_documentation_with_preprocess_false(self, quickstart_site):
        """Test that docs with preprocess:false preserve Jinja2 syntax."""
        quickstart_site.build()
        
        output = quickstart_site.output_dir / "docs" / "template-system" / "index.html"
        assert output.exists()
        
        content = output.read_text()
        
        # Should have Jinja2 syntax in code blocks (for documentation)
        assert "{{ page.title }}" in content  # In code examples
    
    def test_build_fails_in_strict_mode_with_jinja2_errors(self, tmp_path):
        """Test that strict mode fails build on Jinja2 errors."""
        # Create site with bad Jinja2
        (tmp_path / "content").mkdir()
        (tmp_path / "content" / "bad.md").write_text(
            "---\ntitle: Bad\n---\n{% if x %} missing endif"
        )
        (tmp_path / "bengal.toml").write_text(
            "[site]\ntitle='Test'\n[build]\nstrict_mode=true"
        )
        
        from bengal.config.loader import ConfigLoader
        from bengal.core.site import Site
        
        config = ConfigLoader(tmp_path).load()
        site = Site(root_path=tmp_path, config=config)
        site.discover_content()
        
        # Should raise in strict mode
        with pytest.raises(Exception):  # Build validation error
            site.build()
```

---

### Priority 2: Improve Error Messages

**Current:**
```
⚠️  Jinja2 syntax error in content/api/v2/_index.md: Expected an expression, got 'end of print statement'
```

**Improved:**
```python
def _preprocess_content(self, page: Page) -> str:
    """Pre-process with better error reporting."""
    # Skip if disabled
    if page.metadata.get('preprocess') is False:
        return page.content
    
    from jinja2 import Template, TemplateSyntaxError, UndefinedError
    
    try:
        template = Template(page.content)
        rendered_content = template.render(
            page=page,
            site=self.site,
            config=self.site.config
        )
        return rendered_content
        
    except TemplateSyntaxError as e:
        # Enhanced error message with context
        error_msg = self._format_jinja2_error(page, e)
        
        if self.build_stats:
            self.build_stats.add_warning(str(page.source_path), error_msg, 'jinja2')
        elif not self.quiet:
            print(f"\n  ⚠️  Jinja2 Syntax Error in {page.source_path}")
            print(f"      Line {e.lineno}: {e.message}")
            print(f"      {self._get_error_snippet(page.content, e.lineno)}")
            print(f"      Tip: Add 'preprocess: false' to frontmatter if this is documentation\n")
        
        return page.content
    
    except UndefinedError as e:
        # Handle undefined variables specifically
        error_msg = f"Undefined variable: {e}"
        
        if self.build_stats:
            self.build_stats.add_warning(str(page.source_path), error_msg, 'jinja2')
        elif not self.quiet:
            print(f"\n  ⚠️  Undefined Variable in {page.source_path}")
            print(f"      {e}")
            print(f"      Available: page.metadata keys: {list(page.metadata.keys())}")
            print(f"      Suggestion: Check if variable exists or use default filter\n")
        
        return page.content
    
    except Exception as e:
        # Generic error handling
        if self.build_stats:
            self.build_stats.add_warning(str(page.source_path), str(e), 'preprocessing')
        elif not self.quiet:
            print(f"  ⚠️  Error pre-processing {page.source_path}: {e}")
        
        return page.content

def _format_jinja2_error(self, page: Page, error: Exception) -> str:
    """Format a Jinja2 error with context."""
    if hasattr(error, 'lineno') and error.lineno:
        return f"{error.message} (line {error.lineno})"
    return str(error)

def _get_error_snippet(self, content: str, lineno: int, context: int = 2) -> str:
    """Get a snippet of content around an error line."""
    lines = content.split('\n')
    start = max(0, lineno - context - 1)
    end = min(len(lines), lineno + context)
    
    snippet_lines = []
    for i in range(start, end):
        marker = ">>> " if i == lineno - 1 else "    "
        snippet_lines.append(f"{marker}{i+1:3d}| {lines[i]}")
    
    return '\n      '.join(snippet_lines)
```

**Better Output:**
```
⚠️  Jinja2 Syntax Error in content/api/v2/_index.md
    Line 24: Expected an expression, got 'end of print statement'
        22| All endpoints are at:
        23| ```
    >>> 24| {{ }}
        25| ```
        26|
    Tip: Add 'preprocess: false' to frontmatter if this is documentation
```

---

### Priority 3: Add Strict Mode for Preprocessing

**Configuration Option:**

```toml
[build]
strict_preprocessing = true  # Fail build on Jinja2 errors (default: false)
```

**Implementation:**

```python
def _preprocess_content(self, page: Page) -> str:
    """Pre-process with optional strict mode."""
    # ... existing code ...
    
    except TemplateSyntaxError as e:
        error_msg = self._format_jinja2_error(page, e)
        
        if self.build_stats:
            self.build_stats.add_warning(str(page.source_path), error_msg, 'jinja2')
        
        # Check if strict mode
        if self.site.config.get('strict_preprocessing', False):
            raise PreprocessingError(
                f"Jinja2 syntax error in {page.source_path}: {error_msg}"
            )
        
        # Otherwise continue with warning
        if not self.quiet:
            print(f"  ⚠️  Jinja2 syntax error in {page.source_path}: {e}")
        return page.content
```

---

### Priority 4: Add Preprocessing Validation Mode

**New Feature:** Validate Jinja2 syntax WITHOUT actually rendering

```python
def validate_preprocessing(self) -> list:
    """
    Validate that all pages with Jinja2 syntax can be preprocessed.
    
    Returns list of validation errors without actually processing.
    Useful for CI/CD pipelines.
    """
    errors = []
    
    for page in self.pages:
        if page.metadata.get('preprocess') is False:
            continue
        
        # Quick check for Jinja2 syntax
        if '{{' not in page.content and '{%' not in page.content:
            continue
        
        # Try to compile template (fast, no rendering)
        from jinja2 import Template, TemplateSyntaxError
        try:
            Template(page.content)
        except TemplateSyntaxError as e:
            errors.append({
                'file': str(page.source_path),
                'error': str(e),
                'line': getattr(e, 'lineno', None)
            })
    
    return errors
```

**CLI Command:**
```bash
bengal validate --check-preprocessing
```

---

## Should Errors Be Explicit vs Warnings?

### Current Behavior: **Warnings (Continue Building)**
- ✅ Good for development (see all issues at once)
- ✅ Allows progressive enhancement
- ❌ Can miss issues in production
- ❌ May deploy broken pages

### Recommended Approach: **Context-Dependent**

| Scenario | Behavior | Reason |
|----------|----------|--------|
| **Development (`bengal serve`)** | Warning | Fast iteration, see all issues |
| **Production (`bengal build`)** | Warning by default | Existing content shouldn't break |
| **Strict Mode** | Error (fail build) | CI/CD, quality gates |
| **Undefined variables** | Warning | Jinja2 handles gracefully |
| **Syntax errors** | Warning (or error in strict) | Unambiguous mistake |

### Configuration:

```toml
[build]
# When to fail vs warn on preprocessing errors
strict_preprocessing = false  # true = fail build on any error
fail_on_undefined = false     # true = fail on undefined variables
fail_on_syntax_error = false  # true = fail on Jinja2 syntax errors

# Alternative: severity levels
preprocessing_error_level = "warn"  # "ignore", "warn", "error"
```

---

## Implementation Checklist

### Phase 1: Test Coverage (Critical)
- [ ] Create `tests/unit/test_jinja2_preprocessing.py`
- [ ] Create `tests/integration/test_jinja2_preprocessing_e2e.py`
- [ ] Add test for `preprocess: false` flag
- [ ] Add test for cascade metadata + Jinja2
- [ ] Add test for error handling
- [ ] Aim for >90% coverage of `_preprocess_content()`

### Phase 2: Better Error Messages
- [ ] Add `_format_jinja2_error()` helper
- [ ] Add `_get_error_snippet()` for context
- [ ] Handle `UndefinedError` separately
- [ ] Show available variables in errors
- [ ] Add helpful suggestions

### Phase 3: Strict Mode
- [ ] Add `strict_preprocessing` config option
- [ ] Raise exception in strict mode
- [ ] Document in user guide
- [ ] Add to CI/CD examples

### Phase 4: Validation (Nice to Have)
- [ ] Add `validate_preprocessing()` method
- [ ] Add `bengal validate --check-preprocessing` command
- [ ] Fast syntax checking without rendering
- [ ] CI/CD integration example

---

## Examples of Good Error Messages

### Example 1: Syntax Error
```
❌ Jinja2 Syntax Error

File: content/api/v2/_index.md
Line: 24

    22| All endpoints are at:
    23| ```
>>> 24| {{ }}
    25| ```
    26|

Error: Expected an expression, got 'end of print statement'

💡 Tip: Add 'preprocess: false' to frontmatter if this page documents Jinja2 syntax
```

### Example 2: Undefined Variable
```
⚠️  Undefined Variable

File: content/api/endpoint.md
Line: 15

>>> 15| Base URL: {{ page.metadata.api_base_url }}

Error: 'api_base_url' is undefined

Available variables in page.metadata:
  - title
  - description  
  - date

💡 Tips:
  - Check if variable exists: {% if page.metadata.api_base_url %}
  - Use default filter: {{ page.metadata.api_base_url | default('https://api.example.com') }}
  - Check parent _index.md for cascade metadata
```

---

## Conclusion

### Immediate Actions (Do Now)
1. ✅ **Add test coverage** - Most critical gap
2. ✅ **Improve error messages** - Show context and suggestions
3. ✅ **Keep warnings by default** - Don't break existing behavior

### Future Enhancements
4. **Add strict mode** - For production/CI environments
5. **Add validation command** - Fast syntax checking
6. **Better documentation** - Examples of using Jinja2 in markdown

### Answer to User's Question

**"Should errors be explicit when Jinja2 stuff fails?"**

**Answer:** It depends on context:

- **Development:** Warnings are better (see all issues, keep iterating)
- **Production/CI:** Should be errors in strict mode
- **Current behavior (warnings) is good** - just needs better visibility and messages

**The real improvements needed are:**
1. **Better error messages** with context and suggestions
2. **Test coverage** to prevent regressions  
3. **Optional strict mode** for CI/CD pipelines
4. **Clear documentation** on when/how to use preprocessing

