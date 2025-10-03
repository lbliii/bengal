# Debugging & Testing Improvements

**Date:** October 2, 2025  
**Context:** After painful debugging of template rendering bug

## What Made This Bug So Hard to Debug

1. **Silent failures** - Exceptions caught and converted to fallback HTML with just a warning
2. **Misleading error message** - "'page' is undefined" when page WAS defined
3. **Exception location mismatch** - Error appeared in renderer but bug was in template_engine
4. **No test coverage** - No tests validated actual rendered output quality
5. **Fallback behavior masked severity** - Pages "worked" but looked broken

## Proposed Improvements

### 1. Strict Mode / Debug Configuration

**Add a `strict` mode that fails loudly instead of falling back:**

```python
# In bengal/config/loader.py - add to default config
DEFAULT_CONFIG = {
    # ... existing ...
    "strict_mode": False,  # Fail on template errors instead of fallback
    "debug": False,        # Verbose debug output
}
```

**Update renderer to respect strict mode:**

```python
# In bengal/rendering/renderer.py
def render_page(self, page: Page, content: Optional[str] = None) -> str:
    # ...
    try:
        return self.template_engine.render(template_name, context)
    except Exception as e:
        # In strict mode, don't catch - let it bubble up and fail the build
        if self.site.config.get("strict_mode", False):
            raise
        
        # Otherwise, warn and fall back
        print(f"Warning: Failed to render page {page.source_path} with template {template_name}: {e}")
        
        # In debug mode, show full traceback
        if self.site.config.get("debug", False):
            import traceback
            traceback.print_exc()
        
        return self._render_fallback(page, content)
```

**Default to strict mode in development:**
- `bengal serve` → strict_mode=True (fail fast during development)
- `bengal build` → strict_mode=False (allow fallback for production resilience)
- `bengal build --strict` → strict_mode=True (CI/CD validation)

### 2. Output Validation Tests

**Add integration tests that verify actual rendered output:**

```python
# tests/integration/test_output_quality.py
"""
Integration tests that validate rendered output quality.
"""
import pytest
from pathlib import Path
from bs4 import BeautifulSoup

def test_pages_include_theme_assets(built_site):
    """Verify pages include CSS and JS from theme."""
    index_html = (built_site / "index.html").read_text()
    soup = BeautifulSoup(index_html, 'html.parser')
    
    # Must have stylesheet links
    stylesheets = soup.find_all('link', rel='stylesheet')
    assert len(stylesheets) > 0, "No stylesheets found in output"
    
    # Must have navigation
    nav = soup.find('nav')
    assert nav is not None, "No navigation found in output"
    
    # Must have proper HTML structure
    assert soup.find('html') is not None
    assert soup.find('head') is not None
    assert soup.find('body') is not None


def test_pages_have_reasonable_size(built_site):
    """Verify pages aren't tiny fallback HTML."""
    index_html = built_site / "index.html"
    size = index_html.stat().st_size
    
    # Full themed pages should be at least 3KB
    # Fallback HTML is typically < 2KB
    assert size > 3000, f"Page too small ({size} bytes), likely fallback HTML"


def test_pages_contain_actual_content(built_site):
    """Verify pages include the actual markdown content."""
    about_html = (built_site / "about/index.html").read_text()
    
    # Check for content that should be in about.md
    assert "Bengal" in about_html
    assert "Philosophy" in about_html or "philosophy" in about_html.lower()


def test_no_template_variables_in_output(built_site):
    """Verify no unrendered Jinja2 variables leak through."""
    for html_file in built_site.rglob("*.html"):
        content = html_file.read_text()
        
        # Check for unrendered Jinja2 syntax
        assert "{{" not in content, f"Unrendered variable in {html_file}"
        assert "{%" not in content, f"Unrendered tag in {html_file}"


def test_theme_assets_copied(built_site):
    """Verify theme CSS/JS files are copied to output."""
    assets_dir = built_site / "assets"
    
    # Should have CSS
    css_files = list(assets_dir.glob("css/*.css"))
    assert len(css_files) > 0, "No CSS files in output"
    
    # Should have JS
    js_files = list(assets_dir.glob("js/*.js"))
    assert len(js_files) > 0, "No JS files in output"


@pytest.fixture
def built_site(tmp_path):
    """Build a site and return the output directory."""
    # Copy quickstart example to tmp
    import shutil
    from bengal.core.site import Site
    
    quickstart = Path("examples/quickstart")
    site_dir = tmp_path / "site"
    shutil.copytree(quickstart / "content", site_dir / "content")
    shutil.copy(quickstart / "bengal.toml", site_dir / "bengal.toml")
    
    # Build site in strict mode
    site = Site.from_config(site_dir)
    site.config["strict_mode"] = True  # Fail if rendering broken
    site.build()
    
    return site.output_dir
```

### 3. Better Logging Infrastructure

**Add structured logging instead of print statements:**

```python
# bengal/utils/logger.py
"""
Structured logging for Bengal.
"""
import logging
from enum import Enum

class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR

class BengalLogger:
    """Centralized logger for Bengal."""
    
    def __init__(self, verbose: bool = False, debug: bool = False):
        self.logger = logging.getLogger('bengal')
        
        # Set level based on mode
        if debug:
            self.logger.setLevel(logging.DEBUG)
        elif verbose:
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.WARNING)
        
        # Add handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def debug(self, msg: str, **kwargs):
        """Debug-level message (only in debug mode)."""
        self.logger.debug(msg, extra=kwargs)
    
    def info(self, msg: str, **kwargs):
        """Info-level message (only in verbose mode)."""
        self.logger.info(msg, extra=kwargs)
    
    def warning(self, msg: str, **kwargs):
        """Warning message (always shown)."""
        self.logger.warning(msg, extra=kwargs)
    
    def error(self, msg: str, **kwargs):
        """Error message (always shown)."""
        self.logger.error(msg, extra=kwargs)
    
    def render_error(self, page_path, template, error, traceback_str=None):
        """Specialized logging for render errors."""
        self.error(
            f"Failed to render {page_path} with template {template}: {error}"
        )
        if traceback_str:
            self.debug(f"Traceback:\n{traceback_str}")
```

### 4. Build Health Checks

**Add post-build validation:**

```python
# In bengal/core/site.py
def _validate_build_health(self) -> None:
    """
    Validate build output quality after building.
    Run basic health checks to catch obvious issues.
    """
    if not self.config.get("validate_build", True):
        return
    
    issues = []
    
    # Check 1: Are all pages large enough?
    min_size = self.config.get("min_page_size", 1000)  # 1KB minimum
    for page in self.pages:
        if page.output_path and page.output_path.exists():
            size = page.output_path.stat().st_size
            if size < min_size:
                issues.append(f"Page {page.output_path.name} is suspiciously small ({size} bytes)")
    
    # Check 2: Are theme assets present?
    assets_dir = self.output_dir / "assets"
    if assets_dir.exists():
        css_count = len(list(assets_dir.glob("css/*.css")))
        js_count = len(list(assets_dir.glob("js/*.js")))
        if css_count == 0:
            issues.append("No CSS files found in output")
        if js_count == 0:
            issues.append("No JS files found in output (may be expected)")
    
    # Check 3: Any unrendered templates?
    for html_file in self.output_dir.rglob("*.html"):
        content = html_file.read_text()
        if "{{" in content or "{%" in content:
            issues.append(f"Unrendered Jinja2 syntax in {html_file.name}")
    
    # Report issues
    if issues:
        print("\n⚠️  Build Health Check Issues:")
        for issue in issues[:10]:  # Show first 10
            print(f"  • {issue}")
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more issues")
        
        if self.config.get("strict_mode", False):
            raise BuildValidationError(f"Build failed health checks: {len(issues)} issues found")
        else:
            print("  (These may be acceptable - review output)")
```

### 5. About the Disabled Method

**Recommendation: REMOVE IT ENTIRELY for now.**

Reasons:
1. The current implementation is fundamentally flawed
2. It's disabled anyway, serving no purpose
3. Keeping dead code is confusing
4. Main template tracking is sufficient for incremental builds

**If we need it in the future**, implement it properly:

```python
# Future implementation using Jinja2 meta API
def _track_template_dependencies_v2(self, template_name: str) -> None:
    """
    Track template dependencies by parsing source (not introspecting rendered template).
    
    Uses Jinja2's meta API to find includes/extends BEFORE rendering.
    """
    from jinja2 import meta
    
    # Find the template source file
    template_path = self._find_template_path(template_name)
    if not template_path:
        return
    
    # Parse the template source
    source = template_path.read_text()
    ast = self.env.parse(source)
    
    # Find all referenced templates
    referenced = meta.find_referenced_templates(ast)
    
    # Track each dependency
    for ref_name in referenced:
        ref_path = self._find_template_path(ref_name)
        if ref_path:
            self._dependency_tracker.track_partial(ref_path)
```

But honestly, **we may not need this at all**. Main template tracking + full content directory watching is probably sufficient.

## Priority Implementation Order

1. **HIGH: Strict mode** - Fail fast in development
2. **HIGH: Output validation tests** - Catch broken builds in CI
3. **MEDIUM: Remove disabled method** - Clean up confusing code
4. **MEDIUM: Build health checks** - Automated quality validation
5. **LOW: Structured logging** - Nice to have, but print() works

## Success Criteria

After implementing these improvements, a bug like this would:
1. ✅ Fail the build in development (`bengal serve` with strict mode)
2. ✅ Fail CI tests (output validation tests)
3. ✅ Show clear error with traceback (strict mode + debug logging)
4. ✅ Never silently produce broken output

## Examples

**Before:**
```bash
$ bengal build
Building site...
Warning: Failed to render page about.md with template page.html: 'page' is undefined
  ✓ about/index.html
✓ Site built successfully
```
*Output looks broken but build "succeeded"*

**After:**
```bash
$ bengal build --strict
Building site...
ERROR: Failed to render page about.md with template page.html: 'page' is undefined
Traceback (most recent call last):
  ...
  jinja2.exceptions.UndefinedError: 'page' is undefined
❌ Build failed
```
*Build fails immediately with clear error*

**In CI:**
```bash
$ pytest tests/integration/test_output_quality.py
FAILED test_pages_have_reasonable_size - AssertionError: Page too small (1493 bytes), likely fallback HTML
```
*Tests catch broken output*

## Reflection

This bug was painful because we had **defensive programming** (try/except with fallback) that turned a **fatal error into a warning**. This is a classic trade-off:

- **Production**: Want resilience, graceful degradation
- **Development**: Want fast failure, loud errors

The solution: **Different behaviors for different contexts**, controlled by configuration flags.

The missing tests were equally critical - we tested *units* but not the *integration* (does the actual HTML output look right?). Integration tests are essential for catch regressions in the final user-facing output.

