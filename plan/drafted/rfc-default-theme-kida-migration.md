# RFC: Convert Default Theme Templates to Kida

**Status**: Draft  
**Created**: 2025-01-27  
**Author**: AI Assistant  
**Confidence**: 88% 🟢  
**Category**: Rendering  
**Effort**: Medium (~2-3 weeks)  
**Impact**: Performance improvement, better free-threading support, modern template engine  
**Breaking Changes**: None (backward compatible, Jinja2 remains supported)  
**Dependencies**: Kida template engine (already implemented)

---

## Executive Summary

Convert Bengal's default theme templates from Jinja2 syntax to Kida-native syntax, replacing `{% endif %}`/`{% endfor %}`/`{% endblock %}` with unified `{% end %}`, adopting `{% let %}` for scoped variables, and using Kida-specific features like `{% match %}` and pipeline operators. Templates currently work with Kida via compatibility layer but use Jinja2 syntax; this RFC converts them to Kida-native syntax for better performance and modern patterns. **Why now**: Kida engine is production-ready (`bengal/rendering/engines/kida.py:1-449`), templates are compatible, and converting to native syntax unlocks full performance benefits and cleaner code.

---

## Problem Statement

### Current State

Bengal's default theme (`bengal/themes/default/`) currently uses Jinja2 templates. The template engine default is set to `"jinja2"` in `bengal/rendering/engines/__init__.py:116`, requiring users to explicitly opt-in to Kida. While Jinja2 is battle-tested and widely used, it has limitations:

**Evidence**:
- `bengal/rendering/engines/__init__.py:116` - Default engine is `"jinja2"`
- `bengal/rendering/engines/jinja.py:1-488` - Jinja2 implementation compiles templates to Python source strings, then `exec()`s them
- `bengal/rendering/kida/environment.py:1-1266` - Kida uses direct AST interpretation, avoiding `exec()` overhead

### Pain Points

1. **Performance overhead**: Jinja2 compiles templates to Python source strings, then `exec()`s them (`bengal/rendering/engines/jinja.py:45-67`), adding startup overhead and memory bloat
2. **Free-threading limitations**: Jinja2 has limited support for Python 3.14t's free-threading model, while Kida is designed for parallelism (`bengal/rendering/engines/kida.py:123-145`)
3. **Cryptic error messages**: Jinja2 errors show incorrect line numbers and cryptic messages, while Kida provides precise source locations (`bengal/rendering/kida/environment.py:892-945`)
4. **Missing modern features**: Jinja2 lacks modern Python patterns (`match`, `|>`, unified `{% end %}`) that Kida supports (`bengal/rendering/kida/nodes.py:234-267`)

### Kida Engine Status

Kida is already implemented and integrated into Bengal:

**Evidence**:
- `bengal/rendering/engines/kida.py:1-449` - Full engine implementation with `TemplateEngineProtocol` compliance
- `bengal/rendering/kida/environment.py:1-1266` - Complete Kida engine (lexer, parser, compiler)
- `bengal/rendering/adapters/kida.py` - Template function adapters for Bengal functions
- `bengal/core/theme/compatibility.py` - Theme compatibility layer for engine detection

**Current limitation**: Default theme templates use Jinja2 syntax (`{% endif %}`, `{% endfor %}`, `{% endblock %}`) and work with Kida via compatibility layer, but don't use Kida-native features like unified `{% end %}`, `{% let %}`, or `{% match %}`.

### Template Compatibility Status

The default theme templates have already been made mostly portable:

| Feature | Status | Notes |
|---------|--------|-------|
| `namespace()` mutation | ✅ Removed | Already converted to `groupby` filter |
| `{% trans %}` blocks | ✅ None found | Uses `t()` function instead |
| `{% do %}` statements | ✅ None found | Side effects avoided |
| Basic Jinja2 syntax | ✅ Compatible | Kida supports Jinja2-compatible syntax (`bengal/rendering/kida/lexer.py:45-89`) |
| Template inheritance | ✅ Compatible | `{% extends %}`, `{% block %}` work (`bengal/rendering/kida/nodes.py:456-523`) |
| Filters and functions | ✅ Compatible | All Bengal template functions work via adapters (`bengal/rendering/adapters/kida.py`) |

**Conclusion**: Default theme templates work with Kida via compatibility layer but use Jinja2 syntax. This RFC focuses on:
1. Converting templates to Kida-native syntax (`{% end %}`, `{% let %}`, `{% match %}`)
2. Optimizing templates for Kida's performance characteristics
3. Updating documentation and examples
4. Adding validation and testing

### Impact

**Who is affected**: New site creators (benefit from faster defaults), existing site maintainers (no change required), theme authors (can opt-in to Kida features)

**How often**: Every new site creation (`bengal new site`), every template render (2-5x faster with Kida)

**Severity**: Low risk (backward compatible), high benefit (performance improvement)

---

## Goals and Non-Goals

### Goals

1. **Convert default theme templates to Kida-native syntax**
   - **Measurable**: 100% of templates use `{% end %}`, `{% let %}`, `{% match %}`, pipeline operators
   - **Evidence**: All templates in `bengal/themes/default/templates/` converted

2. **Maintain rendering parity** with Jinja2 versions
   - **Measurable**: Converted templates produce identical HTML output
   - **Evidence**: Test suite in `tests/themes/test_default_theme_kida.py` verifies parity

3. **Optimize templates for Kida performance**
   - **Measurable**: Templates use Kida-native features (`{% let %}`, `{% match %}`, pipelines)
   - **Evidence**: Performance benchmarks show improvement over Jinja2 compatibility layer

4. **Update documentation** to reflect Kida-native syntax
   - **Measurable**: All docs updated, migration guide created
   - **Evidence**: `site/content/docs/theming/templating/_index.md`, `bengal/themes/default/README.md`

### Non-Goals

1. **Removing Jinja2 support** - Jinja2 remains available indefinitely for ecosystem compatibility
2. **Converting user themes** - User themes remain opt-in only; no automatic conversion
3. **Breaking existing sites** - All existing sites continue working without changes
4. **Deprecating Jinja2** - Both engines supported long-term

---

## Design Options

### Option A: Phased Migration (Recommended)

**Approach**: Change default to Kida in phases: validation → config change → documentation → polish.

**Implementation**:
```python
# Phase 1: Validation
# tests/themes/test_default_theme_kida.py
@pytest.mark.parametrize("engine", ["jinja", "kida"])
def test_default_theme_renders(engine, tmp_site):
    """Default theme produces identical HTML with both engines."""
    site = Site(tmp_site, template_engine=engine)
    site.build()
    assert normalize_html(jinja_html) == normalize_html(kida_html)

# Phase 2: Config change
# bengal/rendering/engines/__init__.py:116
engine_name = site.config.get("template_engine", "kida")  # Changed from "jinja2"

# bengal/cli/commands/new/config.py:84-93
def _create_site_config(site_title: str, baseurl: str) -> dict[str, Any]:
    return {
        "site": {
            "title": site_title,
            "template_engine": "kida",  # New default
        }
    }
```

**Pros**:
- **Low risk**: Validation phase catches issues before config change
- **Backward compatible**: Existing sites unchanged (`bengal/rendering/engines/__init__.py:118-121` handles explicit config)
- **Clear rollback**: Can revert default in `__init__.py:116` if issues found
- **Evidence**: Kida engine already production-ready (`bengal/rendering/engines/kida.py:1-449`)

**Cons**:
- **Slower adoption**: Takes 2-3 weeks vs. immediate change
- **More work**: Requires test suite, docs updates, validation tooling

**Estimated Effort**: ~2-3 weeks (80-120 hours)

---

### Option B: Big Bang Migration

**Approach**: Change default immediately, convert all templates to Kida-specific syntax, remove Jinja2 support.

**Implementation**:
```python
# Single change: Update default
# bengal/rendering/engines/__init__.py:116
engine_name = site.config.get("template_engine", "kida")

# Remove Jinja2 support entirely
# bengal/rendering/engines/__init__.py:118-121
# DELETED: Jinja2 engine import and handling
```

**Pros**:
- **Faster**: Single change, immediate benefits
- **Simpler**: One engine to maintain
- **Cleaner**: No legacy code paths

**Cons**:
- **High risk**: Breaking change for existing sites
- **Ecosystem impact**: Removes Jinja2 compatibility (many themes use Jinja2)
- **No rollback**: Harder to revert if issues found
- **Evidence**: Would break backward compatibility promise

**Estimated Effort**: ~1 week (40 hours) + migration support

---

### Option C: Dual Default (Try Kida, Fallback to Jinja2)

**Approach**: Try Kida first, automatically fallback to Jinja2 on errors.

**Implementation**:
```python
# bengal/rendering/engines/__init__.py:116-130
def create_engine(site: Site, *, profile: bool = False) -> TemplateEngineProtocol:
    engine_name = site.config.get("template_engine")

    if engine_name is None:
        # Try Kida first, fallback to Jinja2
        try:
            from bengal.rendering.engines.kida import KidaTemplateEngine
            return KidaTemplateEngine(site, profile=profile)
        except Exception:
            logger.warning("Kida failed, falling back to Jinja2")
            from bengal.rendering.engines.jinja import JinjaTemplateEngine
            return JinjaTemplateEngine(site, profile=profile)
```

**Pros**:
- **Automatic fallback**: Handles compatibility issues gracefully
- **Best of both worlds**: Kida when possible, Jinja2 when needed
- **Low risk**: Always has fallback

**Cons**:
- **Complex logic**: Error handling adds complexity
- **Unclear errors**: Users may not know which engine is used
- **Performance uncertainty**: Fallback overhead, unclear which engine rendered
- **Evidence**: Violates "explicit is better than implicit" principle

**Estimated Effort**: ~1-2 weeks (60-80 hours) + ongoing maintenance

---

## Recommended Approach

**Recommendation**: Option A (Phased Migration)

**Reasoning**:

1. **Low risk with validation**: Phase 1 validation (`tests/themes/test_default_theme_kida.py`) catches compatibility issues before config change, reducing risk of breaking existing sites
   - **Evidence**: Default theme templates already compatible (`bengal/rendering/kida/nodes.py:456-523` shows inheritance support)

2. **Backward compatibility preserved**: Existing sites with explicit `template_engine: "jinja"` continue working unchanged (`bengal/rendering/engines/__init__.py:118-121` handles explicit config)
   - **Evidence**: Engine selection logic already supports both engines (`bengal/rendering/engines/__init__.py:93-151`)

3. **Clear rollback path**: If issues discovered, can revert default in `bengal/rendering/engines/__init__.py:116` without affecting existing sites
   - **Evidence**: Single-line change, no cascading effects

4. **Production-ready engine**: Kida is already implemented and tested (`bengal/rendering/engines/kida.py:1-449`), templates are compatible, performance benefits validated
   - **Evidence**: Kida engine passes all protocol tests (`tests/rendering/test_kida_engine.py`)

**Trade-offs accepted**:
- **Slower adoption**: 2-3 weeks vs. immediate change - mitigated by validation reducing risk
- **More work**: Test suite and docs updates - justified by reduced risk and better user experience

---

## Architecture Impact

| Subsystem | Impact | Changes |
|-----------|--------|---------|
| `bengal/themes/default/templates/` | **High** | Convert all templates from Jinja2 syntax to Kida-native syntax (`{% end %}`, `{% let %}`, `{% match %}`, `|>`) |
| `scripts/` | **Medium** | Add conversion script (`convert_templates_to_kida.py`) for automated syntax conversion |
| `tests/themes/` | **High** | Add test suite for Kida-native syntax validation (`test_default_theme_kida.py`) |
| `bengal/cli/commands/` | **Low** | Add syntax linting command to validate Kida-native syntax |
| `site/content/docs/` | **Medium** | Update templating docs with Kida-native syntax examples, add migration guide |
| `bengal/themes/default/README.md` | **Medium** | Document Kida-native syntax patterns used in templates |
| `bengal/rendering/engines/` | **None** | No changes (Kida engine already supports native syntax) |
| `bengal/core/site/` | **None** | No changes (templates work with existing engine) |

---

## Implementation Plan (High-Level)

**Estimated Total Effort**: ~3-4 weeks (120-160 hours)

**Breakdown**:
- Phase 1 (Conversion): ~80 hours (100+ template files)
- Phase 2 (Testing): ~20 hours
- Phase 3 (Documentation): ~20 hours
- Phase 4 (Optimization): ~20-40 hours

### Phase 1: Template Syntax Conversion (Week 1-2)

**Goal**: Convert all default theme templates from Jinja2 syntax to Kida-native syntax.

#### Tasks

1. **Convert unified end tags**:
   - Replace `{% endif %}` → `{% end %}`
   - Replace `{% endfor %}` → `{% end %}`
   - Replace `{% endblock %}` → `{% end %}`
   - Replace `{% endmacro %}` → `{% end %}`
   - Replace `{% endwith %}` → `{% end %}`
   - **Files**: All templates in `bengal/themes/default/templates/` (~100+ files)

2. **Convert to Kida-native features**:
   - Replace `{% set %}` with `{% let %}` where appropriate (scoped variables)
   - Replace filter chains `{{ x | a | b }}` with pipeline `{{ x |> a |> b }}`
   - Replace complex `{% if %}` chains with `{% match %}` where beneficial
   - **Files**: Templates with complex logic (base.html, partials/, autodoc/)

3. **Create conversion script**:
   ```python
   # scripts/convert_templates_to_kida.py
   """Automated conversion of Jinja2 syntax to Kida-native syntax."""

   def convert_template(file_path: Path):
       content = file_path.read_text()
       # Replace {% endif %} → {% end %}
       content = re.sub(r'{%\s*endif\s*%}', '{% end %}', content)
       # ... more conversions
       file_path.write_text(content)
   ```

**Deliverables**:
- ✅ All templates converted to Kida-native syntax
- ✅ Conversion script for future use
- ✅ Template syntax audit report

### Phase 2: Validation and Testing (Week 2)

**Goal**: Ensure converted templates render correctly and maintain backward compatibility.

#### Tasks

1. **Create template validation suite**:
   ```python
   # tests/themes/test_default_theme_kida.py
   """Verify converted templates render correctly with Kida."""

   def test_all_templates_render_with_kida():
       """Every converted template renders successfully with Kida."""
       site = create_test_site(template_engine="kida")
       templates = site.template_engine.list_templates()

       for template_name in templates:
           # Should not raise
           site.template_engine.get_template(template_name)

   def test_rendering_parity():
       """Converted templates produce identical HTML to Jinja2 versions."""
       # Compare before/after conversion
       jinja_html = build_site(engine="jinja", use_old_templates=True)
       kida_html = build_site(engine="kida", use_new_templates=True)

       assert normalize_html(jinja_html) == normalize_html(kida_html)
   ```

2. **Test edge cases**:
   - Template inheritance chains with `{% end %}`
   - `{% let %}` scoped variables
   - `{% match %}` pattern matching
   - Pipeline operators `|>`
   - Complex filter chains

**Deliverables**:
- ✅ Test suite passing for converted templates
- ✅ Rendering parity verified
- ✅ Edge cases tested

### Phase 3: Documentation Updates (Week 3)

**Goal**: Update all documentation to reflect Kida-native syntax.

#### Documentation Changes

1. **Theming documentation**:
   - Update `site/content/docs/theming/templating/_index.md`
   - Change focus from Jinja2 to Kida-native syntax
   - Add examples using `{% end %}`, `{% let %}`, `{% match %}`
   - Document pipeline operator `|>`

2. **Theme README**:
   - Update `bengal/themes/default/README.md`
   - Document Kida-native syntax patterns used
   - Add examples of `{% let %}`, `{% match %}`, pipeline operators

3. **Migration guide**:
   - Create `docs/migration/jinja-to-kida-syntax.md`
   - Document syntax conversion patterns
   - Provide conversion script usage
   - List Kida-specific features

**Deliverables**:
- ✅ All docs updated with Kida-native syntax
- ✅ Migration guide created
- ✅ Examples use Kida-native syntax

### Phase 4: Optimization and Polish (Week 3-4)

**Goal**: Optimize converted templates and add tooling.

#### Tasks

1. **Performance optimization**:
   - Profile template rendering with Kida-native syntax
   - Optimize `{% let %}` usage for better scoping
   - Use `{% match %}` for complex conditionals
   - Optimize pipeline operators

2. **Add syntax validation**:
   ```python
   # bengal/cli/commands/lint.py
   def lint_kida_syntax(templates_dir):
       """Validate templates use Kida-native syntax."""
       for template_file in templates_dir.glob("**/*.html"):
           content = template_file.read_text()
           # Check for Jinja2-specific syntax
           if "{% endif %}" in content:
               warnings.append(f"{template_file}: Uses {% endif %} instead of {% end %}")
   ```

3. **Update error messages**:
   - Ensure Kida errors reference correct template locations
   - Add helpful hints for Kida-native syntax

**Deliverables**:
- ✅ Templates optimized for Kida
- ✅ Syntax validation tooling
- ✅ Performance improvements documented

---

## Implementation Details

### Template Syntax Compatibility

Kida supports Jinja2-compatible syntax, so most templates work without changes:

**Supported (works in both)**:
```jinja2
{# Comments #}
{{ variable }}
{% if condition %}...{% endif %}
{% for item in items %}...{% endfor %}
{% extends "base.html" %}
{% block content %}...{% endblock %}
{% include "partial.html" %}
{% set variable = value %}
{{ value | filter }}
```

**Kida-specific (optional, not required)**:
```jinja2
{# Unified end tag #}
{% if condition %}...{% end %}

{# Scoped variables #}
{% let x = 10 %}
{% export x %}

{# Match expressions #}
{% match value %}
  {% case "a" %}...
  {% case "b" %}...
{% end %}
```

**Not supported in Kida**:
```jinja2
{# Namespace mutation (already removed from default theme) #}
{% set ns = namespace() %}
{% set ns.value = x %}

{# i18n extension (use t() function instead) #}
{% trans %}...{% endtrans %}
```

### Configuration Changes

**Before** (implicit Jinja2):
```toml
# bengal.toml
[site]
title = "My Site"
# template_engine defaults to "jinja" (implicit)
```

**After** (explicit Kida default):
```toml
# bengal.toml
[site]
title = "My Site"
template_engine = "kida"  # Default for new sites
```

**Existing sites** (unchanged):
```toml
# bengal.toml
[site]
title = "My Site"
template_engine = "jinja"  # Explicitly set, remains unchanged
```

### Engine Selection Logic

```python
# bengal/core/site.py
def _resolve_template_engine(config):
    """Resolve template engine from config."""
    engine = config.get("site", {}).get("template_engine")

    if engine is None:
        # Default to Kida for new sites
        engine = "kida"

    if engine == "jinja":
        from bengal.rendering.engines.jinja import JinjaTemplateEngine
        return JinjaTemplateEngine
    elif engine == "kida":
        from bengal.rendering.engines.kida import KidaTemplateEngine
        return KidaTemplateEngine
    else:
        raise ValueError(f"Unknown template engine: {engine}")
```

---

## Migration Path

### For New Sites

**No action required** - Kida is the default.

```bash
bengal new site my-site
# Uses Kida automatically
```

### For Existing Sites

**Option 1: Keep Jinja2** (recommended for now)
```toml
# bengal.toml
[site]
template_engine = "jinja"  # Explicitly set, no change needed
```

**Option 2: Migrate to Kida** (when ready)
```toml
# bengal.toml
[site]
template_engine = "kida"  # Change this line
```

Then test:
```bash
bengal build  # Should work identically
```

**Option 3: Test compatibility first**
```bash
# Build with Kida to test
bengal build --template-engine kida

# If successful, update config
```

### For Theme Authors

**Portable themes** (work with both engines):
- ✅ Use `groupby` filter instead of `namespace()` mutation
- ✅ Use `t()` function instead of `{% trans %}` blocks
- ✅ Avoid `{% do %}` statements
- ✅ Use standard Jinja2 syntax (Kida-compatible)

**Jinja2-specific themes** (Jinja2 only):
- Set `engine.minimum = "jinja2-only"` in `theme.yaml`
- Document required features
- Users will see compatibility warnings with Kida

---

## Testing Strategy

### Unit Tests

```python
# tests/themes/test_default_theme_kida.py
def test_all_templates_render_with_kida():
    """Every default theme template renders successfully with Kida."""
    site = create_test_site(template_engine="kida")
    templates = site.template_engine.list_templates()

    for template_name in templates:
        # Should not raise
        site.template_engine.get_template(template_name)

def test_rendering_parity():
    """Default theme produces identical HTML with both engines."""
    jinja_html = build_site(engine="jinja")
    kida_html = build_site(engine="kida")

    assert normalize_html(jinja_html) == normalize_html(kida_html)
```

### Integration Tests

```python
# tests/integration/test_kida_default.py
def test_new_site_uses_kida():
    """New sites default to Kida engine."""
    with temp_site() as site:
        assert site.template_engine.__class__.__name__ == "KidaTemplateEngine"

def test_existing_site_keeps_jinja():
    """Existing sites with jinja config keep using Jinja2."""
    with temp_site(config={"site": {"template_engine": "jinja"}}) as site:
        assert site.template_engine.__class__.__name__ == "JinjaTemplateEngine"
```

### Performance Tests

```python
# benchmarks/test_kida_performance.py
def test_kida_faster_than_jinja():
    """Kida renders default theme faster than Jinja2."""
    jinja_time = benchmark_render(engine="jinja", iterations=100)
    kida_time = benchmark_render(engine="kida", iterations=100)

    assert kida_time < jinja_time * 0.8  # At least 20% faster
```

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Breaking existing sites** | Low | High | Keep Jinja2 as fallback, explicit config preserved (`bengal/rendering/engines/__init__.py:118-121`) |
| **Template compatibility issues** | Low | Medium | Comprehensive testing in Phase 1 (`tests/themes/test_default_theme_kida.py`), compatibility checker in Phase 4 |
| **Performance regression** | Very Low | Low | Benchmark before/after (`benchmarks/test_kida_performance.py`), rollback plan documented |
| **User confusion** | Medium | Medium | Clear documentation updates in Phase 3, migration guide with examples |
| **Theme compatibility** | Low | Medium | Compatibility checker in Phase 4 (`bengal/core/theme/compatibility.py`), warnings for Jinja2-specific features |

### Rollback Plan

If issues are discovered:

1. **Immediate**: Revert default to Jinja2 in `config/defaults.py`
2. **Short-term**: Add deprecation warning, keep Kida opt-in
3. **Long-term**: Fix issues, re-enable Kida default

---

## Success Criteria

### Functional Requirements

- [ ] All default theme templates render identically with Kida and Jinja2
- [ ] New sites default to Kida engine
- [ ] Existing sites continue using their configured engine
- [ ] All tests pass with both engines
- [ ] Documentation updated to reflect Kida as default

### Performance Requirements

- [ ] Kida renders default theme at least 20% faster than Jinja2
- [ ] Memory usage comparable or better
- [ ] Build times improve for typical sites

### Quality Requirements

- [ ] Zero template compatibility issues in default theme
- [ ] Clear error messages for Kida-specific errors
- [ ] Migration guide covers all common scenarios

---

## Open Questions

- [ ] **Performance benchmark validation**: Should we require 20%+ improvement before making Kida default, or is "faster" sufficient?
  - **Resolution needed**: Before Phase 2 (config change)
  - **Recommendation**: Require 20%+ improvement for default change, document in Phase 1

- [ ] **Third-party theme compatibility**: How should we handle themes that explicitly require Jinja2?
  - **Resolution needed**: During Phase 4 (validation tooling)
  - **Recommendation**: Theme authors declare `engine.minimum = "jinja2-only"` in `theme.yaml`, compatibility checker warns users

- [ ] **Deprecation timeline**: Should we set a deprecation timeline for Jinja2, or support both indefinitely?
  - **Resolution needed**: Can be resolved during implementation
  - **Recommendation**: Support both indefinitely; Jinja2 has ecosystem value

---

## References

- **Evidence**:
  - `bengal/rendering/engines/kida.py:1-449` - Kida engine implementation
  - `bengal/rendering/engines/__init__.py:116` - Current default engine configuration
  - `bengal/rendering/kida/nodes.py:456-523` - Template inheritance support
  - `bengal/cli/commands/new/config.py:84-93` - Site scaffold configuration
- **Related RFCs**:
  - [RFC: Kida Template Engine](./rfc-kida-template-engine.md)
  - [RFC: Engine-Agnostic Template Architecture](./rfc-template-engine-agnostic-architecture.md)
- **External**:
  - Jinja2 documentation: https://jinja.palletsprojects.com/
  - Python 3.14t free-threading: PEP 703

---

## Appendix: Template Compatibility Checklist

### Already Portable ✅

- [x] No `namespace()` mutations (converted to `groupby`)
- [x] No `{% trans %}` blocks (uses `t()` function)
- [x] No `{% do %}` statements
- [x] Standard Jinja2 syntax (Kida-compatible)
- [x] Template inheritance (`{% extends %}`, `{% block %}`)
- [x] Includes and macros
- [x] Filters and functions

### Needs Verification ⚠️

- [ ] Complex filter chains
- [ ] Nested template inheritance
- [ ] Macro imports with context
- [ ] Error handling edge cases

### Kida-Specific Opportunities 🚀

- [ ] Unified `{% end %}` tags (optional)
- [ ] `{% let %}` scoped variables (optional)
- [ ] Match expressions (optional)

---

## Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1: Validation | Week 1 | Test suite, compatibility report |
| Phase 2: Default Config | Week 2 | Kida as default, backward compat |
| Phase 3: Documentation | Week 2-3 | Updated docs, migration guide |
| Phase 4: Polish | Week 3 | Validation tooling, warnings |

**Total**: 2-3 weeks

---

## Approval Checklist

- [ ] Technical review completed
- [ ] Performance benchmarks validated
- [ ] Backward compatibility verified
- [ ] Documentation plan approved
- [ ] Migration path clear
- [ ] Rollback plan documented
