# RFC: Autodoc Package Handling

**Status**: Evaluated  
**Created**: 2024-12-21  
**Updated**: 2024-12-21  
**Author**: AI Assistant  
**Related**: `rfc-url-ownership-architecture.md`, `rfc-url-collision-detection.md`  
**Confidence**: 88% 🟢

## Executive Summary

`__init__.py` package files currently generate module pages that become section index pages, but this creates poor UX (users see import statements instead of navigation) and causes URL collision issues.

**Proposal**: Don't create separate pages for packages. Instead, extract package metadata from `__init__.py` and inject it into section-index pages, giving users a navigation-first experience with package context.

## Problem Statement

### Current Behavior

```
bengal/autodoc/models/__init__.py
         ↓
DocElement(qualified_name="autodoc.models", element_type="module", is_package=True)
         ↓
Output path: _index.md (via module_info.py:157-170)
         ↓
Page at /api/bengal/autodoc/models/ (module template)
         ↓
Assigned as section.index_page (via page_builders.py:186)
```

**Existing code paths involved:**

| Component | File | Lines | What it does |
|-----------|------|-------|--------------|
| Package detection | `extractor.py` | 326 | Sets `is_package = file_path.name == "__init__.py"` |
| `_index.md` paths | `module_info.py` | 157-170 | Packages get `_index.md` output paths |
| Section descriptions | `section_builders.py` | 51-57, 94-105 | Extracts descriptions from `__init__.py` into section metadata |
| Index assignment | `page_builders.py` | 161-186 | Assigns package pages as `section.index_page` |
| `__all__` extraction | `aliases.py` | 68+ | Extracts `__all__` exports from modules |

### Issues

| Problem | Impact |
|---------|--------|
| **Poor UX** | Package pages show import statements (`from .common import X`) instead of useful navigation |
| **URL collisions** | When both `foo.py` and `foo/` exist, same qualified name generates duplicate pages |
| **Template mismatch** | Packages use module template but need section-index template for navigation |
| **Complexity** | Special handling to assign package pages as section.index_page |

### Evidence

1. **URL collision in build output**:
   ```
   url_collision url=/api/bengal/rendering/template_functions/
   first_source=api/bengal/rendering/template_functions.md
   second_source=api/bengal/rendering/template_functions.md
   ```

2. **Module+Package naming conflict**:
   ```
   bengal/rendering/template_functions.py   ← Module file
   bengal/rendering/template_functions/     ← Package directory
   ```

3. **Package `__init__.py` content** (typical):
   ```python
   """Typed metadata models for autodoc system."""
   from bengal.autodoc.models.cli import CLICommandMetadata
   from bengal.autodoc.models.common import QualifiedName
   # ... more imports
   __all__ = ["CLICommandMetadata", "QualifiedName", ...]
   ```

   Users want to see child modules, not this.

## Proposed Solution

### Core Principle

**Packages are sections, not pages.**

`__init__.py` provides metadata for the section (description, exports), but the section-index template provides the user experience (navigation, child listings).

### Integration with Existing Code

This proposal **extends** existing functionality rather than replacing it:

| Existing | Proposed Change |
|----------|-----------------|
| `section_builders.py` extracts `description` from `__init__.py` docstrings | **Keep** - adds `package_docstring` and `package_exports` metadata |
| `module_info.py` returns `_index.md` paths for packages | **Modify** - no longer used since packages won't create pages |
| `page_builders.py` assigns package pages as `section.index_page` | **Remove** - sections use generated index pages instead |
| `aliases.py` extracts `__all__` exports | **Reuse** - `typed_metadata.all_exports` already available |

**Key insight**: `PythonModuleMetadata` already has `all_exports` (extracted at `extractor.py:336`). We just need to surface it in section metadata.

### Design

```
┌─────────────────────────────────────────────────────────────┐
│  /api/bengal/autodoc/models/                                │
├─────────────────────────────────────────────────────────────┤
│  📦 autodoc.models                                          │
│  ─────────────────────────────────────────────────────────  │
│  Typed metadata models for autodoc system.  ◄── __init__.py docstring
│                                                             │
│  Subpackages           Modules                              │
│  (none)                ┌─────────┐ ┌─────────┐              │
│                        │ common  │ │  cli    │              │
│                        └─────────┘ └─────────┘              │
│                        ┌─────────┐ ┌─────────┐              │
│                        │ python  │ │ openapi │              │
│                        └─────────┘ └─────────┘              │
│                                                             │
│  Public API (from __all__)                                  │
│  • CLICommandMetadata    • PythonClassMetadata              │
│  • QualifiedName         • OpenAPIEndpointMetadata          │
└─────────────────────────────────────────────────────────────┘
```

### Changes

#### 1. Skip page creation for `__init__.py` packages

```python
# bengal/autodoc/orchestration/page_builders.py

for element in elements:
    # Skip packages - they're represented by section-index pages
    if _is_package_init(element):
        # Extract metadata for section instead
        _enrich_section_from_package(element, sections, resolve_output_prefix)
        continue

    # Create page for regular modules...

def _is_package_init(element: DocElement) -> bool:
    """Check if element is from __init__.py (package, not module)."""
    return (
        element.element_type == "module" and
        element.source_file and
        element.source_file.name == "__init__.py"
    )

def _enrich_section_from_package(
    element: DocElement,
    sections: dict[str, Section],
    resolve_output_prefix: callable,
) -> None:
    """
    Inject package metadata into corresponding section.

    Note: section_builders.py already extracts basic descriptions (lines 51-57).
    This adds package-specific metadata: qualified_name, exports, source_file.
    """
    prefix = resolve_output_prefix("python")
    section_path = f"{prefix}/{element.qualified_name.replace('.', '/')}"
    section = sections.get(section_path)

    if section:
        # Enrich section with package-specific metadata
        # (Complements existing 'description' from section_builders.py)
        section.metadata["package_docstring"] = element.description
        section.metadata["qualified_name"] = element.qualified_name
        section.metadata["source_file"] = str(element.source_file) if element.source_file else None

        # Reuse existing __all__ extraction from typed_metadata
        if hasattr(element, "typed_metadata") and element.typed_metadata:
            meta = element.typed_metadata
            if hasattr(meta, "all_exports") and meta.all_exports:
                section.metadata["package_exports"] = list(meta.all_exports)
```

#### 2. Skip module files that shadow packages

```python
# bengal/autodoc/extractors/python/extractor.py

def _should_skip(self, path: Path) -> bool:
    """Check if file should be skipped during extraction."""
    # Existing skip logic...
    if should_skip(path, self.exclude_patterns):
        return True

    # Skip module files that shadow package directories
    # e.g., skip template_functions.py if template_functions/ exists
    if path.suffix == ".py" and path.stem != "__init__":
        package_dir = path.parent / path.stem
        if package_dir.is_dir() and (package_dir / "__init__.py").exists():
            logger.warning(
                "autodoc_skip_shadowed_module",
                module=str(path),
                package=str(package_dir),
                reason="Module file shadows package directory",
            )
            return True

    return False
```

#### 3. Enhance section-index template

```html
{# autodoc/python/section-index.html #}
<div class="api-section">
    <header class="api-section__header">
        <h1>{{ section.title }}</h1>
        {% if section.metadata.qualified_name %}
        <code class="api-section__qualified-name">
            {{ section.metadata.qualified_name }}
        </code>
        {% endif %}
    </header>

    {# Package description from __init__.py docstring #}
    {% if section.metadata.package_docstring %}
    <div class="api-section__description">
        {{ section.metadata.package_docstring | safe }}
    </div>
    {% elif section.metadata.description %}
    <div class="api-section__description">
        {{ section.metadata.description }}
    </div>
    {% endif %}

    {# Stats bar #}
    <div class="api-stats">
        {% if section.subsections %}
        <span class="api-stat">
            <span class="api-stat__count">{{ section.subsections | length }}</span>
            <span class="api-stat__label">Subpackages</span>
        </span>
        {% endif %}
        {% set module_pages = section.pages | rejectattr("metadata.is_section_index") | list %}
        {% if module_pages %}
        <span class="api-stat">
            <span class="api-stat__count">{{ module_pages | length }}</span>
            <span class="api-stat__label">Modules</span>
        </span>
        {% endif %}
    </div>

    {# Subpackages grid #}
    {% if section.sorted_subsections %}
    <section class="api-section__subsections">
        <h2>Subpackages</h2>
        <div class="api-card-grid">
            {% for subsection in section.sorted_subsections %}
            <a href="{{ subsection.relative_url }}" class="api-card">
                <span class="api-card__icon">📦</span>
                <span class="api-card__title">{{ subsection.name }}</span>
                {% if subsection.metadata.package_docstring %}
                <p class="api-card__description">
                    {{ subsection.metadata.package_docstring | first_sentence }}
                </p>
                {% endif %}
            </a>
            {% endfor %}
        </div>
    </section>
    {% endif %}

    {# Modules grid #}
    {% set module_pages = section.pages | rejectattr("metadata.is_section_index") | list %}
    {% if module_pages %}
    <section class="api-section__modules">
        <h2>Modules</h2>
        <div class="api-card-grid">
            {% for page in module_pages | sort(attribute='title') %}
            <a href="{{ page.url }}" class="api-card">
                <span class="api-card__icon">📄</span>
                <span class="api-card__title">{{ page.title }}</span>
                {% if page.metadata.description %}
                <p class="api-card__description">
                    {{ page.metadata.description | first_sentence }}
                </p>
                {% endif %}
            </a>
            {% endfor %}
        </div>
    </section>
    {% endif %}

    {# Public exports from __all__ #}
    {% if section.metadata.package_exports %}
    <section class="api-section__exports">
        <h2>Public API</h2>
        <p class="api-section__exports-note">
            These symbols are exported from this package's <code>__init__.py</code>:
        </p>
        <div class="api-export-grid">
            {% for export in section.metadata.package_exports %}
            <code class="api-export">{{ export }}</code>
            {% endfor %}
        </div>
    </section>
    {% endif %}
</div>
```

#### 4. Extract exports from `__init__.py`

```python
# bengal/autodoc/utils.py

def extract_package_exports(element: DocElement) -> list[str]:
    """
    Extract public exports from package element.

    Looks for:
    1. __all__ definition
    2. Public symbols (not starting with _)

    Returns:
        List of exported symbol names
    """
    exports = []

    # Check for __all__ in metadata
    if hasattr(element, "metadata") and element.metadata:
        all_exports = element.metadata.get("__all__")
        if all_exports:
            return list(all_exports)

    # Fallback: extract from children (functions, classes)
    if hasattr(element, "children") and element.children:
        for child in element.children:
            if not child.name.startswith("_"):
                exports.append(child.name)

    return sorted(exports)
```

## Migration Path

### Phase 1: Skip shadowed modules (Low risk)
- Detect and skip `foo.py` when `foo/` exists
- Log warning for visibility
- **No breaking changes**

### Phase 2: Enrich sections from packages (Low risk)
- Extract metadata from `__init__.py` into section.metadata
- Existing templates continue to work
- **Additive only**

### Phase 3: Skip package page creation (Medium risk)
- Stop creating pages for `__init__.py` files
- Section-index pages now serve package URLs
- **Breaking**: Sites relying on package page content

### Phase 4: Enhanced section-index template (Low risk)
- Update template to show package metadata + navigation
- **Visual change only**

## Trade-offs

### Pros
| Benefit | Impact |
|---------|--------|
| Better UX | Users see navigation, not imports |
| Simpler code | Remove special package→section.index_page handling |
| No URL collisions | Packages don't create pages |
| Consistent model | All sections rendered the same way |
| Matches expectations | Like Sphinx/Read the Docs |

### Cons
| Drawback | Mitigation |
|----------|------------|
| `__init__.py` code not visible | Rarely useful; link to source if needed |
| Different from current behavior | Phased rollout, documentation |
| Template changes needed | Ship improved default template |

## Alternatives Considered

### A: Keep current behavior, fix collisions only
- Skip shadowed modules
- Keep package pages as section indexes
- **Rejected**: Still shows imports instead of navigation

### B: Merge package page + section-index at render time
- Create both, merge content in template
- **Rejected**: Complex, two sources of truth

### C: Use package page for section, auto-inject navigation
- Keep package page, add child listings via template
- **Rejected**: Template becomes complex, mixing concerns

## Testing Strategy

```python
# tests/unit/autodoc/test_package_handling.py

def test_package_init_not_in_returned_pages():
    """__init__.py packages should not create pages."""
    elements = extract_from_package_with_init()
    pages, _ = create_pages(elements, sections, ...)

    init_pages = [p for p in pages if p.source_id.endswith("__init__.md")]
    assert len(init_pages) == 0

def test_section_enriched_from_package():
    """Section should have package metadata."""
    elements = extract_from_package_with_init()
    sections = create_python_sections(elements, ...)
    create_pages(elements, sections, ...)  # Enriches sections

    section = sections["api/bengal/autodoc/models"]
    assert section.metadata.get("package_docstring") is not None
    assert section.metadata.get("qualified_name") == "autodoc.models"
    assert "QualifiedName" in section.metadata.get("package_exports", [])

def test_shadowed_module_skipped():
    """Module files that shadow packages should be skipped."""
    # Create temp directory with both foo.py and foo/__init__.py
    extractor = PythonExtractor(config)
    elements = extractor.extract(temp_dir)

    foo_elements = [e for e in elements if e.qualified_name == "foo"]
    assert len(foo_elements) == 1  # Only package, not module
    assert foo_elements[0].source_file.name == "__init__.py"

def test_real_shadowing_case_template_functions():
    """Verify bengal/rendering/template_functions shadowing is handled.

    This tests a real case in the codebase:
    - bengal/rendering/template_functions.py (module)
    - bengal/rendering/template_functions/ (package)

    The module file should be skipped in favor of the package.
    """
    from pathlib import Path
    extractor = PythonExtractor(config)
    rendering_path = Path("bengal/rendering")

    # Both exist
    assert (rendering_path / "template_functions.py").exists()
    assert (rendering_path / "template_functions" / "__init__.py").exists()

    elements = extractor.extract(rendering_path)
    tf_elements = [e for e in elements if "template_functions" in e.qualified_name]

    # Should only have the package, not the shadowed module
    root_tf = [e for e in tf_elements if e.qualified_name.endswith("template_functions")]
    assert len(root_tf) == 1
    assert root_tf[0].source_file.name == "__init__.py"
```

## Implementation Checklist

- [ ] **Phase 1**: Skip shadowed modules in extractor
  - [ ] Add `_should_skip_shadowed_module()` check
  - [ ] Add warning log for visibility
  - [ ] Add unit test

- [ ] **Phase 2**: Enrich sections from packages
  - [ ] Add `_enrich_section_from_package()` function
  - [ ] Extract docstring and exports
  - [ ] Add to section.metadata
  - [ ] Add unit tests

- [ ] **Phase 3**: Skip package page creation
  - [ ] Add `_is_package_init()` check in page_builders
  - [ ] Skip page creation, call enrichment instead
  - [ ] Remove package→section.index_page assignment code
  - [ ] Update integration tests

- [ ] **Phase 4**: Enhanced section-index template
  - [ ] Update `autodoc/python/section-index.html`
  - [ ] Show package description
  - [ ] Show public exports
  - [ ] Add styling

## Open Questions

1. **Should we link to source for `__init__.py`?**
   - ✅ **Resolved**: Yes, add "View source" link using `section.metadata.source_file`
   - Template addition: `{% if section.metadata.source_file %}<a href="...">View source</a>{% endif %}`

2. **What about packages with significant `__init__.py` code?**
   - Rare in practice (Bengal codebase has ~0 such cases)
   - Could add config option `autodoc.force_package_pages: ["bengal.some.special"]`
   - **Deferred**: Not MVP, can add if users request

3. **Should exports link to their documentation?**
   - Would need to resolve symbol → page URL
   - **Deferred**: Nice-to-have, not MVP
   - Future: Could use `{% set export_page = site.get_page_by_qualified_name(export) %}`

4. **~~How does this interact with URL ownership?~~** *(Resolved)*
   - ✅ Compatible: Section index pages already claim URLs at priority 70
   - Packages will no longer claim URLs separately, eliminating collision

## Success Criteria

- [ ] No URL collisions from module+package naming (verify with `template_functions` case)
- [ ] Package URLs show navigation, not imports
- [ ] Package docstrings visible in section pages (via `section.metadata.package_docstring`)
- [ ] `__all__` exports visible in section pages (via `section.metadata.package_exports`)
- [ ] All existing tests pass
- [ ] Build time not significantly impacted (<5% increase)
- [ ] No regressions in autodoc navigation

---

## Verification

### Evidence Gathered

| Claim | File:Line | Status |
|-------|-----------|--------|
| Package pages become section index pages | `page_builders.py:186` | ✅ Verified |
| URL collisions exist | 10 files reference pattern | ✅ Verified |
| Module+package shadowing exists | `template_functions.py` + `template_functions/` | ✅ Verified |
| `is_package` metadata tracked | `extractor.py:326` | ✅ Verified |
| `__all__` exports extracted | `extractor.py:329`, `aliases.py:68` | ✅ Verified |
| Section descriptions already extracted | `section_builders.py:51-57` | ✅ Verified |
| `_index.md` output paths for packages | `module_info.py:157-170` | ✅ Verified |

### Confidence Scoring

| Component | Score | Reasoning |
|-----------|-------|-----------|
| Evidence Strength | 38/40 | Strong code references with line numbers |
| Consistency | 28/30 | All paths verified; integration points documented |
| Recency | 12/15 | Recent codebase; files updated within 3 months |
| Test Coverage | 10/15 | Tests proposed; integration tests needed |
| **Total** | **88/100** | High confidence 🟢 |

---

**Status**: Ready for implementation. Move to `plan/ready/` when approved.
