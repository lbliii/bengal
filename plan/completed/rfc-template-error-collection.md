# RFC: Robust Template Error Collection During Builds

| Field | Value |
|-------|-------|
| **Title** | Robust Template Error Collection During Builds |
| **Author** | AI + Human reviewer |
| **Date** | 2025-12-10 |
| **Status** | Draft |
| **Confidence** | 85% 🟢 |

---

## Executive Summary

Template syntax errors during site builds are not reliably collected in `BuildStats.template_errors`. When a page specifies a broken template (e.g., `template = "broken.html"` in frontmatter), the build may silently succeed by falling back to default theme templates, masking the error. This RFC proposes changes to ensure template errors are consistently detected, collected, and reported.

---

## Problem Statement

### Current State

Template error handling exists in multiple places:

1. **TemplateEngine.render()** (`bengal/rendering/template_engine/core.py:160-182`):
   - Calls `env.get_template(template_name)` which can raise `TemplateSyntaxError`
   - Catches exceptions, logs them, and re-raises

2. **Renderer.render_page()** (`bengal/rendering/renderer.py:258-302`):
   - Wraps `template_engine.render()` in try/except
   - Creates `TemplateRenderError` from Jinja2 errors
   - Adds errors to `build_stats.template_errors` in production mode
   - Returns empty string to allow build to continue

3. **Jinja2 FileSystemLoader** (`bengal/rendering/template_engine/environment.py:132-214`):
   - Searches template directories in order: custom templates → theme templates → bundled default
   - Raises `TemplateNotFound` if template doesn't exist in any directory

### Pain Points

1. **Fallback Masking**: When a custom template has syntax errors, Jinja2 may not find it if the search path isn't properly configured, causing silent fallback to default theme's `page.html`

2. **No Proactive Validation**: Template syntax errors are only discovered during page rendering, not during build initialization

3. **Template Discovery Gap**: The system doesn't validate that explicitly specified templates (from frontmatter) exist before rendering

4. **Integration Test Failures**: Tests in `tests/integration/test_template_error_collection.py` are currently skipped because template errors aren't reliably collected

### User Impact

- **Site authors**: Broken templates may not produce errors, leading to unexpected fallback behavior
- **Theme developers**: Syntax errors in theme templates may go unnoticed during development
- **CI/CD pipelines**: Builds may pass despite template issues, only discovered in production

---

## Goals & Non-Goals

### Goals

1. **Reliable Error Collection**: All template syntax errors are detected and collected in `BuildStats.template_errors`
2. **Early Detection**: Template errors are detected as early as possible (during initialization, not just rendering)
3. **Clear Feedback**: Users receive actionable error messages with template location and syntax details
4. **Graceful Degradation**: Non-strict mode builds continue with warnings; strict mode fails fast

### Non-Goals

- **Template Auto-Repair**: We won't attempt to fix broken templates automatically
- **Template Linting**: Beyond syntax validation, we won't enforce style or best practices
- **Live Reloading Changes**: Changes to dev server template reloading are out of scope

---

## Architecture Impact

### Affected Subsystems

- **Rendering** (`bengal/rendering/`):
  - `template_engine/core.py`: Add proactive template validation
  - `template_engine/environment.py`: Enhance template discovery reporting
  - `renderer.py`: Improve error context and collection
  - `validator.py`: Extend existing validation capabilities

- **Orchestration** (`bengal/orchestration/`):
  - `build.py`: Add template validation phase to build lifecycle

- **Utils** (`bengal/utils/`):
  - `build_stats.py`: Already has `template_errors` list; may need categorization

- **Health** (`bengal/health/`):
  - Potential new validator for template syntax checking

### Integration Points

```
Build Initialization
       │
       ▼
┌──────────────────┐
│ Template Engine  │──► Create Jinja2 Environment
│   Initialization │
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Template         │──► Validate all templates in search path (NEW)
│   Validation     │──► Report broken templates to BuildStats
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ Page Rendering   │──► Catch remaining errors during render
│                  │──► Collect to BuildStats.template_errors
└──────────────────┘
```

---

## Design Options

### Option A: Proactive Template Validation Phase

**Description**: Add a template validation phase during build initialization that parses all discoverable templates.

**Implementation**:
```python
# In TemplateEngine or RenderingPipeline initialization
def validate_all_templates(self) -> list[TemplateRenderError]:
    """Validate syntax of all templates in search path."""
    errors = []
    for template_dir in self.template_dirs:
        for template_file in Path(template_dir).rglob("*.html"):
            rel_name = template_file.relative_to(template_dir)
            try:
                self.env.get_template(str(rel_name))
            except TemplateSyntaxError as e:
                errors.append(TemplateRenderError.from_jinja2_error(
                    e, str(rel_name), None, self
                ))
    return errors
```

**Pros**:
- Catches ALL template errors upfront
- Works regardless of which pages use which templates
- Can be run independently (e.g., `bengal template validate`)

**Cons**:
- Performance overhead scanning all templates
- May validate templates that are never actually used
- Complexity: Need to handle multiple templates with same name in different dirs

**Complexity**: Moderate

**Evidence**: Existing `TemplateValidator` class (`bengal/rendering/validator.py:18-76`) provides similar functionality but isn't integrated into build flow.

### Option B: Enhanced Error Capture at Render Time

**Description**: Improve the existing render-time error capture to ensure errors aren't masked.

**Implementation**:
```python
# In TemplateEngine.render()
def render(self, template_name: str, context: dict) -> str:
    try:
        template = self.env.get_template(template_name)
    except TemplateSyntaxError as e:
        # Return error info instead of re-raising
        return None, TemplateRenderError.from_jinja2_error(e, template_name, ...)
    except TemplateNotFound as e:
        # Also capture template not found errors
        return None, TemplateNotFoundError(template_name, self.template_dirs)

    try:
        return template.render(**context), None
    except Exception as e:
        return None, TemplateRenderError.from_jinja2_error(e, template_name, ...)
```

**Pros**:
- Minimal changes to existing flow
- Only validates templates that are actually used
- Lower performance overhead

**Cons**:
- Errors discovered late in build process
- Doesn't catch issues in unused templates
- More complex API (tuple return or exception wrapping)

**Complexity**: Simple

**Evidence**: Current `Renderer.render_page()` already catches and collects errors, but the error may be masked by template fallback before reaching this point.

### Option C: Template Resolution with Fallback Tracking

**Description**: Modify template resolution to track when fallbacks occur and report them as warnings.

**Implementation**:
```python
# In create_jinja_environment() or TemplateEngine
class FallbackAwareLoader(FileSystemLoader):
    """Loader that tracks fallback behavior."""

    def get_source(self, environment, template):
        fallbacks_tried = []
        for searchpath in self.searchpath:
            try:
                return super().get_source(environment, template)
            except TemplateNotFound:
                fallbacks_tried.append(searchpath)

        # If we get here, template wasn't found
        # But we can log which paths were tried
        raise TemplateNotFound(template, fallbacks_tried)
```

**Pros**:
- Tracks exactly which template is used
- Can warn when unexpected fallback occurs
- Minimal changes to rendering logic

**Cons**:
- Doesn't catch syntax errors before render
- Custom loader adds maintenance burden
- Jinja2 doesn't support tracking which directory a template came from

**Complexity**: Moderate

### Recommended: Option A + B Hybrid

**Rationale**:
- Use **Option A** (proactive validation) as an optional build phase that can be enabled for development/CI
- Use **Option B** (enhanced capture) as the baseline for all builds

**Why not Option C alone**: Tracking fallbacks is useful but doesn't address the core issue of catching syntax errors.

---

## Detailed Design (Hybrid Approach)

### API Changes

**New TemplateEngine method**:
```python
def validate_templates(
    self,
    include_patterns: list[str] | None = None
) -> list[TemplateRenderError]:
    """
    Validate syntax of all templates in search path.

    Args:
        include_patterns: Optional glob patterns to limit validation
                          (e.g., ["page.html", "partials/*.html"])

    Returns:
        List of TemplateRenderError for any broken templates
    """
```

**Enhanced TemplateEngine.render() signature** (internal change):
```python
def render(
    self,
    template_name: str,
    context: dict[str, Any],
    collect_errors: bool = True  # NEW: Whether to return errors or raise
) -> str:
    """
    Returns rendered HTML.
    Raises TemplateError in strict mode.
    Returns empty string and logs error otherwise.
    """
```

### Data Flow

```
1. Build Start
       │
       ├─► [If validate_templates enabled]
       │         │
       │         ▼
       │    TemplateEngine.validate_templates()
       │         │
       │         ▼
       │    Collect errors to BuildStats
       │         │
       │         ▼
       │    [If strict mode + errors] → Fail build
       │
       ▼
2. Discovery Phase (unchanged)
       │
       ▼
3. Rendering Phase
       │
       ├─► For each page:
       │         │
       │         ▼
       │    Renderer.render_page()
       │         │
       │         ▼
       │    TemplateEngine.render()
       │         │
       │         ├─► Success → Return HTML
       │         │
       │         └─► Failure →
       │                  │
       │                  ├─► [Strict] Fail immediately
       │                  │
       │                  └─► [Normal] Collect error, return ""
       │
       ▼
4. Build Complete
       │
       ▼
   Display BuildStats (including template_errors)
```

### Error Handling

**New error categories in BuildStats**:
```python
@dataclass
class BuildStats:
    # Existing
    template_errors: list[TemplateRenderError] = field(default_factory=list)

    # NEW: Categorize template errors
    @property
    def syntax_errors(self) -> list[TemplateRenderError]:
        return [e for e in self.template_errors if e.error_type == "syntax"]

    @property  
    def not_found_errors(self) -> list[TemplateRenderError]:
        return [e for e in self.template_errors if e.error_type == "not_found"]
```

### Configuration

**New config options** (in `bengal.toml`):
```toml
[build]
# Validate all templates before rendering (slower but catches all errors)
validate_templates = false  # default

# Existing
strict_mode = false
```

### Testing Strategy

1. **Unit Tests**:
   - Test `TemplateEngine.validate_templates()` with broken templates
   - Test error categorization in BuildStats

2. **Integration Tests**:
   - Re-enable `tests/integration/test_template_error_collection.py`
   - Test full build with broken templates
   - Test strict mode behavior

3. **Regression Tests**:
   - Ensure existing build behavior unchanged when `validate_templates = false`

---

## Tradeoffs & Risks

### Tradeoffs

| Tradeoff | Gain | Loss |
|----------|------|------|
| Proactive validation | Catch all errors early | Build time overhead (~100-500ms for typical site) |
| Hybrid approach | Flexibility | More code paths to maintain |
| Categorized errors | Better error UX | Slight API complexity |

### Risks

**Risk 1: Performance Regression**
- **Likelihood**: Low (validation is fast, optional)
- **Impact**: Medium
- **Mitigation**: Make proactive validation opt-in via config

**Risk 2: Breaking Existing Workflows**
- **Likelihood**: Low
- **Impact**: High
- **Mitigation**: Default behavior unchanged; new features opt-in

**Risk 3: Edge Cases in Template Loading**
- **Likelihood**: Medium
- **Impact**: Low
- **Mitigation**: Comprehensive test coverage with various template scenarios

---

## Performance & Compatibility

### Performance Impact

- **Build time**: +100-500ms if `validate_templates = true` (depends on template count)
- **Memory**: Negligible (templates already cached by Jinja2)
- **Cache implications**: None (template bytecode cache still works)

### Compatibility

- **Breaking changes**: None (new features are opt-in)
- **Migration path**: N/A
- **Deprecation timeline**: N/A

---

## Migration & Rollout

### Implementation Phases

**Phase 1: Foundation** (1-2 days)
- Add `TemplateEngine.validate_templates()` method
- Add basic integration with BuildStats
- Unit tests

**Phase 2: Build Integration** (1 day)
- Add `validate_templates` config option
- Integrate into `BuildOrchestrator`
- Re-enable integration tests

**Phase 3: UX Polish** (1 day)
- Improve error messages with template location
- Add summary to build output
- Documentation updates

### Rollout Strategy

- **Feature flag**: `[build] validate_templates = true`
- **Beta period**: N/A (opt-in feature)
- **Documentation updates**:
  - Configuration reference
  - Troubleshooting guide for template errors

---

## Open Questions

- [ ] **Q1**: Should `validate_templates` be enabled by default in dev mode? (Need user feedback)
- [ ] **Q2**: Should we add a CLI command `bengal template validate`? (Low priority, nice to have)
- [ ] **Q3**: How should we handle templates with Jinja2 extensions that aren't loaded yet? (Edge case)

---

## Evidence Trail

| Claim | Source | Confidence |
|-------|--------|------------|
| Custom templates directory is added to search path | `environment.py:154-156` | 🟢 High |
| Errors are caught in Renderer.render_page() | `renderer.py:258-302` | 🟢 High |
| BuildStats has template_errors list | `build_stats.py:99` | 🟢 High |
| TemplateValidator exists but isn't integrated | `validator.py:18-76` | 🟢 High |
| Integration tests are skipped | `test_template_error_collection.py:24-28` | 🟢 High |

---

## References

- `bengal/rendering/template_engine/core.py` - TemplateEngine class
- `bengal/rendering/template_engine/environment.py` - Jinja2 environment setup
- `bengal/rendering/renderer.py` - Page rendering with error collection
- `bengal/rendering/validator.py` - Existing template validation (unused)
- `bengal/utils/build_stats.py` - Build statistics container
- `tests/integration/test_template_error_collection.py` - Skipped tests to re-enable
