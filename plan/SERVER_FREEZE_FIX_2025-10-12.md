# Server Freeze Fix & Enhanced Error Handling

**Date:** 2025-10-12  
**Status:** ✅ Complete  
**Impact:** High - Improved developer experience and error detection

## Problem Summary

The `bengal serve` command was exposing template errors that were silently ignored during `bengal build`:

1. **`UndefinedError: 'dict object' has no attribute 'image'`**
   - Root cause: Using `site.config.og_image` instead of `site.config.get('og_image')`
   - Also occurred with `page.metadata.image`, `page.metadata.css_class`, etc.

2. **`UndefinedError: 'types.SimpleNamespace object' has no attribute 'keywords'`**
   - Root cause: Special pages (404, search) created with incomplete `SimpleNamespace` objects
   - Missing `keywords` and proper `metadata` attributes

3. **`UndefinedError: 'site' is undefined`**
   - Root cause: Macros imported without `with context` couldn't access template variables

## Why These Errors Were Hidden

**Key Insight:** `bengal serve` enables `strict_mode=True` by default, while `bengal build` only enables it with the `--strict` flag.

```python
# In serve command (cli.py:1683)
site.config["strict_mode"] = True  # Always strict in dev mode

# In build command (cli.py:403-404)
if strict:  # Only if --strict flag passed
    site.config["strict_mode"] = True
```

**Jinja2 Behavior:**
- **Strict mode:** Raises `UndefinedError` on missing attributes/variables
- **Non-strict mode:** Silently renders undefined as empty string

This was actually **good accident** - strict mode in serve catches errors early!

## Solutions Implemented

### 1. **Enhanced Error Detection** (`bengal/rendering/errors.py`)

Added specific detection for dict access patterns:

```python
# BEFORE: Generic "undefined variable" error
UndefinedError: 'dict object' has no attribute 'image'

# AFTER: Specific actionable guidance
[red bold]Unsafe dict access detected![/red bold] Dict keys should use .get() method
Replace [red]dict.image[/red] with [green]dict.get('image')[/green] or [green]dict.get('image', 'default')[/green]
Common locations: [cyan]page.metadata[/cyan], [cyan]site.config[/cyan], [cyan]section.metadata[/cyan]
[yellow]Note:[/yellow] This error only appears in strict mode (serve). Use [cyan]bengal build --strict[/cyan] to catch in builds.
```

**Changes:**
- Added `_extract_dict_attribute()` helper to parse error messages
- Enhanced `_generate_enhanced_suggestions()` to detect dict access pattern
- Provides context-aware fix suggestions with color coding

### 2. **Health Check Command** (`bengal/cli/commands/health.py`)

New command to proactively validate templates:

```bash
bengal health              # Check templates and config
bengal health --strict     # Fail on warnings
bengal health --fix        # Auto-fix issues (future)
```

**Detects:**
- ✅ Unsafe dict access patterns (`dict.key` instead of `dict.get('key')`)
- ✅ Missing `with context` in macro imports
- ✅ Deprecated usage patterns
- ✅ Missing config values

**Example output:**
```
🏥 Running Bengal health check...

📊 Found 3 issue(s):

  ❌ 2 error(s)
  ⚠️  1 warning(s)

❌ Unsafe dict access
   File: templates/base.html
   Line: 45
   Issue: Using page.metadata.image without .get() method
   Fix: Replace with page.metadata.get('image') or page.metadata.get('image', 'default')
```

### 3. **Template Fixes**

Fixed **14 template files** with unsafe dict access:

| File | Issues Fixed |
|------|-------------|
| `base.html` | `metadata.image`, `config.og_image`, `config.favicon`, `keywords`, `tags`, `kind`, `draft` |
| `special_pages.py` | Added `keywords=[]` and `metadata={}` to SimpleNamespace objects |
| `api-reference/single.html` | `metadata.css_class`, `metadata.description`, `metadata.module_path`, `metadata.source_file` |
| `cli-reference/single.html` | `metadata.usage`, `metadata.emoji`, `metadata.description`, `metadata.source_file`, `metadata.source_line` |
| `cli-reference/list.html` | `metadata.usage`, `metadata.description` |
| `tutorial/single.html` | 12 metadata fields |
| `tutorial/list.html` | 6 metadata fields |
| `blog/single.html` | 11 metadata fields |
| `home.html` | 6 metadata fields |
| `page.html` | `metadata.css_class`, `metadata.author` + added `with context` |
| `post.html` | `metadata.author` |
| `doc/single.html` | `metadata.css_class`, `metadata.description` + added `with context` |
| `doc/list.html` | Same as single + added `with context` |
| `toc-sidebar.html` | `metadata.edit_url`, `config.github_edit_base`, `metadata.contributors` |

**Pattern used:**
```jinja2
# BEFORE (unsafe)
{{ page.metadata.description }}
{% if page.metadata.author %}

# AFTER (safe)
{{ page.metadata.get('description', '') }}
{% if page.metadata.get('author') %}
```

### 4. **Regression Prevention Tests** (`tests/unit/test_template_safety.py`)

Created comprehensive test suite:

```python
def test_detects_unsafe_dict_access_page_metadata(self, tmp_path):
    """Should detect unsafe page.metadata.key access."""

def test_detects_unsafe_dict_access_site_config(self, tmp_path):
    """Should detect unsafe site.config.key access."""

def test_detects_missing_with_context(self, tmp_path):
    """Should detect macro imports without 'with context'."""

def test_allows_safe_dict_access(self, tmp_path):
    """Should NOT flag safe .get() access."""
```

## Best Practices Established

### 1. **Safe Template Access Patterns**

```jinja2
✅ GOOD: page.metadata.get('key', 'default')
❌ BAD:  page.metadata.key

✅ GOOD: site.config.get('key')
❌ BAD:  site.config.key

✅ GOOD: {% if page.keywords is defined and page.keywords %}
❌ BAD:  {% if page.keywords %}

✅ GOOD: {% from '...' import macro with context %}
❌ BAD:  {% from '...' import macro %}
```

### 2. **When to Use Strict Mode**

- **Development (serve):** Always strict (auto-enabled)
- **CI/CD (build):** Use `--strict` flag
- **Production build:** Optional, but recommended for first build

```bash
# Development
bengal serve  # Strict mode auto-enabled

# CI/CD
bengal build --strict  # Fail on template errors

# Pre-commit check
bengal health --strict  # Validate before commit
```

### 3. **Creating Context Objects**

When creating `SimpleNamespace` or dict contexts for rendering:

```python
# COMPLETE context - won't break in strict mode
page_context = SimpleNamespace(
    title="Page Title",
    url="/page.html",
    kind="page",
    draft=False,
    metadata={},      # Always provide metadata dict
    tags=[],          # Always provide tags list  
    keywords=[],      # Always provide keywords list
    content="",
)

# Or use a base factory function
def create_page_context(**kwargs):
    """Create a complete page context with all required fields."""
    defaults = {
        "title": "",
        "url": "",
        "kind": "page",
        "draft": False,
        "metadata": {},
        "tags": [],
        "keywords": [],
        "content": "",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)
```

## Impact

### Immediate Benefits

1. **Catch errors early** - Strict mode in serve catches template bugs before production
2. **Better error messages** - Clear guidance on how to fix dict access errors
3. **Proactive validation** - `bengal health` command finds issues before they cause failures
4. **Regression prevention** - Tests ensure we don't reintroduce these bugs

### Developer Experience

**Before:**
```
UndefinedError: 'dict object' has no attribute 'image'
```
*Developer thinks:* "What dict? Where? What should I do?"

**After:**
```
❌ Unsafe dict access detected! Dict keys should use .get() method
   Replace dict.image with dict.get('image') or dict.get('image', 'default')
   Common locations: page.metadata, site.config, section.metadata
   Note: This error only appears in strict mode (serve). Use 'bengal build --strict' to catch in builds.
```
*Developer thinks:* "Oh! I need to use .get(). Clear fix."

## Workflow Integration

### Pre-commit Hook (Recommended)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: bengal-health
        name: Bengal Template Health Check
        entry: bengal health --strict
        language: system
        pass_filenames: false
```

### CI/CD Pipeline

```yaml
# .github/workflows/build.yml
- name: Validate Templates
  run: bengal health --strict

- name: Build Site (Strict Mode)
  run: bengal build --strict
```

## Future Enhancements

1. **Auto-fix capability** - `bengal health --fix` to automatically convert unsafe patterns
2. **IDE integration** - LSP server for real-time template validation
3. **Template linter** - Pre-parse templates for common issues
4. **Config validation** - Check for missing required config values

## Files Changed

**Core Changes:**
- `bengal/rendering/errors.py` - Enhanced error detection
- `bengal/cli/commands/health.py` - New health check command
- `bengal/cli.py` - Registered health command
- `bengal/postprocess/special_pages.py` - Fixed SimpleNamespace objects

**Template Fixes:** (14 files)
- `bengal/themes/default/templates/base.html`
- `bengal/themes/default/templates/page.html`
- `bengal/themes/default/templates/post.html`
- `bengal/themes/default/templates/home.html`
- `bengal/themes/default/templates/index.html`
- `bengal/themes/default/templates/api-reference/single.html`
- `bengal/themes/default/templates/cli-reference/single.html`
- `bengal/themes/default/templates/cli-reference/list.html`
- `bengal/themes/default/templates/tutorial/single.html`
- `bengal/themes/default/templates/tutorial/list.html`
- `bengal/themes/default/templates/blog/single.html`
- `bengal/themes/default/templates/doc/single.html`
- `bengal/themes/default/templates/doc/list.html`
- `bengal/themes/default/templates/partials/toc-sidebar.html`
- `bengal/themes/default/templates/partials/navigation-components.html`
- `bengal/themes/default/templates/partials/reference-header.html`
- `bengal/themes/default/templates/partials/reference-metadata.html`
- `bengal/themes/default/templates/partials/reference-components.html`

**Tests:**
- `tests/unit/test_template_safety.py` - New test suite

## Lessons Learned

1. **Strict mode is valuable** - The "hidden" strict mode in serve actually saved us from production bugs
2. **Error messages matter** - Generic Jinja2 errors were confusing; context-aware suggestions are much better
3. **Proactive > Reactive** - Health checks catch issues before they become runtime errors
4. **Consistent patterns** - Establishing `.get()` pattern across all templates improves maintainability

## Conclusion

This fix transformed confusing runtime errors into:
1. Clear, actionable error messages
2. Proactive health checking
3. Regression prevention through tests
4. Best practices documentation

The `bengal serve` strict mode behavior, initially unexpected, proved to be a valuable safety net that helped us discover and fix latent template bugs before they reached production.
