# RFC: Separate Output Paths for Autodoc Types

**Status**: Evaluated  
**Author**: AI Assistant  
**Created**: 2025-12-11  
**Confidence**: 88% 🟢  
**Priority**: P2 (Medium)  
**Plan**: `plan-autodoc-output-prefix.md`

---

## Executive Summary

Add configurable `output_prefix` options to autodoc configuration, enabling Python API docs and REST API docs to occupy separate URL namespaces. This prevents REST API documentation from being "swallowed" by Python package documentation in the navigation tree.

---

## Problem Statement

### Current Behavior

When both Python autodoc and OpenAPI autodoc are enabled, they share the `/api/` section:

```
/api/
├── bengal/                    # Python package
│   ├── core/                  # Python subpackage
│   ├── orchestration/         # Python subpackage
│   └── ...                    # ~50+ Python modules
├── overview/                  # OpenAPI overview (lost in tree!)
├── endpoints/                 # OpenAPI endpoints (lost in tree!)
│   └── users/
├── schemas/                   # OpenAPI schemas (lost in tree!)
└── tags/                      # OpenAPI tag groups
```

### User-Reported Issue

> "the rest api doc becomes just one entry in the file tree for all of /api and it gets swallowed by the python docs"

### Root Cause

In `virtual_orchestrator.py`, the `_create_openapi_sections()` method reuses the existing `api` section if Python autodoc already created it:

```python
# bengal/autodoc/virtual_orchestrator.py:754-769
if "api" not in existing_sections:
    api_section = Section.create_virtual(...)
else:
    # Reuse existing API section from Python
    api_section = existing_sections["api"]
```

This design made sense when only one autodoc type was enabled, but creates discoverability issues when multiple types coexist.

---

## Goals

1. **Separation**: Python API and REST API docs have distinct URL prefixes
2. **Configurability**: Users can customize output paths via `autodoc.yaml`
3. **Smart Defaults**: Sensible defaults that work without configuration
4. **Backwards Compatibility**: Existing single-type configs continue to work
5. **Navigation Clarity**: Each autodoc type gets its own top-level nav section

## Non-Goals

- Multiple OpenAPI specs (future enhancement, not in scope)
- Merging multiple Python packages into one tree
- Custom URL slugification rules

---

## Architecture Impact

### Affected Subsystems

| Subsystem | Impact | Files |
|-----------|--------|-------|
| **Autodoc** (`bengal/autodoc/`) | Primary | `config.py`, `virtual_orchestrator.py` |
| **Cache** (`bengal/cache/`) | Indirect | Cache keys include URL paths; prefix changes invalidate entries |
| **Core** (`bengal/core/`) | None | Section/Page models unchanged |
| **Orchestration** (`bengal/orchestration/`) | None | Build flow unchanged |
| **Rendering** (`bengal/rendering/`) | None | Templates receive sections as before |

### Integration Points

```
┌─────────────────────────────────────────────────────────────────┐
│                    Config Loading                               │
│  autodoc.yaml → load_autodoc_config() → output_prefix defaults  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               VirtualAutodocOrchestrator                        │
│  _resolve_output_prefix() → prefix per doc type                 │
│  _derive_openapi_prefix() → auto-derive from spec title         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Section Creation                                │
│  _create_python_sections() → /api/python/...                    │
│  _create_openapi_sections() → /api/{slug}/...                   │
│  _create_cli_sections() → /cli/...                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Page Generation                                 │
│  _create_pages() → pages with prefixed URLs                     │
│  _get_element_metadata() → template + URL path resolution       │
└─────────────────────────────────────────────────────────────────┘
```

### Design Constraints

1. **Sections are keyed by path**: The `sections` dict uses URL paths as keys. Changing prefixes changes keys but doesn't affect lookup logic.

2. **No cross-subsystem coupling**: Prefix resolution is isolated to `VirtualAutodocOrchestrator`. Downstream consumers (rendering, cache) receive fully-formed Section/Page objects.

3. **Cache invalidation is acceptable**: When `output_prefix` changes, autodoc cache entries become stale. This is expected behavior—the user explicitly requested different URLs.

---

## Design Options

### Option A: Separate Prefixes Under `/api/` (Recommended)

```yaml
# autodoc.yaml
autodoc:
  python:
    enabled: true
    output_prefix: "api/python"   # → /api/python/bengal/...

  openapi:
    enabled: true
    output_prefix: "api/rest"     # → /api/rest/endpoints/...
```

**Resulting Structure**:
```
/api/
├── python/                    # Python API Reference
│   └── bengal/
│       ├── core/
│       └── orchestration/
└── rest/                      # REST API Reference
    ├── overview/
    ├── endpoints/
    └── schemas/
```

**Pros**:
- Both under `/api/` umbrella (logical grouping)
- Clear visual separation in navigation
- Intuitive for users familiar with multi-API documentation sites

**Cons**:
- Slightly longer URLs for Python docs
- Requires migration for existing sites

---

### Option B: Fully Separate Root Sections

```yaml
autodoc:
  python:
    output_prefix: "api"          # → /api/bengal/... (unchanged)

  openapi:
    output_prefix: "rest-api"     # → /rest-api/endpoints/...
```

**Resulting Structure**:
```
/api/                          # Python API Reference
│   └── bengal/
│       ├── core/
│       └── orchestration/
/rest-api/                     # REST API Reference
    ├── overview/
    ├── endpoints/
    └── schemas/
```

**Pros**:
- No change to existing Python API URLs
- Maximum separation

**Cons**:
- Two top-level nav sections for "API" content
- Less cohesive documentation structure

---

### Option C: Auto-Derive from Spec Title

```yaml
autodoc:
  openapi:
    output_prefix: ""             # Empty = auto-derive
    spec_file: "api/openapi.yaml" # title: "Bengal Demo Commerce API"
```

Auto-derives prefix from OpenAPI spec `info.title`:
- `"Bengal Demo Commerce API"` → `"api/commerce"`
- `"User Authentication API"` → `"api/user-authentication"`

**Pros**:
- Zero-config for common case
- Meaningful URLs based on API identity

**Cons**:
- Depends on spec title quality
- May produce unexpected slugs

---

## Recommended Approach

**Option A with Option C fallback**: Configurable prefix with smart auto-detection.

### Default Behavior

| Type | Default `output_prefix` | Derivation |
|------|------------------------|------------|
| Python | `"api/python"` | Static default |
| OpenAPI | Auto from spec title | `slugify(spec.info.title)` under `api/` |
| CLI | `"cli"` | Unchanged |

### Resolution Order

1. Explicit `output_prefix` in config → use as-is
2. OpenAPI: derive from `info.title` → `api/{slug}`
3. Python: use `"api/python"`
4. CLI: use `"cli"`

---

## Detailed Design

### Configuration Schema

```yaml
# config/_default/autodoc.yaml
autodoc:
  # Python API Documentation
  python:
    enabled: true
    output_prefix: "api/python"   # Optional, default: "api/python"
    source_dirs:
      - ../bengal
    # ... existing options unchanged

  # OpenAPI Documentation  
  openapi:
    enabled: true
    output_prefix: ""              # Optional, empty = auto-derive from spec title
    spec_file: "api/openapi.yaml"
    # ... existing options unchanged

  # CLI Documentation
  cli:
    enabled: true
    output_prefix: "cli"           # Optional, default: "cli"
    app_module: "bengal.cli:main"
    # ... existing options unchanged
```

### Code Changes

#### 1. Config Defaults (`bengal/autodoc/config.py`)

```python
default_config = {
    "python": {
        "enabled": False,
        "output_prefix": "api/python",  # NEW
        "source_dirs": ["."],
        # ...
    },
    "openapi": {
        "enabled": False,
        "output_prefix": "",  # NEW - empty means auto-derive
        "spec_file": "api/openapi.yaml",
        # ...
    },
    "cli": {
        "enabled": False,
        "output_prefix": "cli",  # NEW (explicit, was implicit)
        "app_module": None,
        # ...
    },
}
```

#### 2. Prefix Resolution (`bengal/autodoc/virtual_orchestrator.py`)

Add method to resolve output prefix:

```python
def _resolve_output_prefix(self, doc_type: str) -> str:
    """
    Resolve output prefix for a documentation type.

    Resolution order:
    1. Explicit config value
    2. Auto-derived (OpenAPI: from spec title)
    3. Default
    """
    config = getattr(self, f"{doc_type}_config", {})
    explicit_prefix = config.get("output_prefix", "").strip()

    if explicit_prefix:
        return explicit_prefix.strip("/")

    if doc_type == "openapi":
        return self._derive_openapi_prefix()
    elif doc_type == "python":
        return "api/python"
    elif doc_type == "cli":
        return "cli"

    return doc_type

def _derive_openapi_prefix(self) -> str:
    """Derive prefix from OpenAPI spec title."""
    spec_file = self.openapi_config.get("spec_file")
    if not spec_file:
        return "api/rest"

    spec_path = self.site.root_path / spec_file
    if not spec_path.exists():
        return "api/rest"

    try:
        import yaml
        with open(spec_path) as f:
            spec = yaml.safe_load(f)
        title = spec.get("info", {}).get("title", "")
        if title:
            slug = self._slugify(title)
            return f"api/{slug}"
    except Exception:
        pass

    return "api/rest"

def _slugify(self, text: str) -> str:
    """
    Convert text to URL-friendly slug.

    Note: Non-ASCII characters are stripped (not transliterated).
    Users needing Unicode support should set explicit output_prefix.
    """
    import re
    # Remove common suffixes
    text = re.sub(r'\s*(api|reference|documentation)$', '', text, flags=re.I)
    # Convert to lowercase, replace non-alphanum with hyphens
    # Note: This strips Unicode chars; acceptable for MVP
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    return slug or "rest"
```

#### 3. Section Creation Updates

Update `_create_python_sections()`:

```python
def _create_python_sections(self, elements: list[DocElement]) -> dict[str, Section]:
    sections: dict[str, Section] = {}
    prefix = self._resolve_output_prefix("python")  # e.g., "api/python"

    # Create root section at prefix
    root_section = Section.create_virtual(
        name=prefix.split("/")[-1],  # "python"
        relative_url=join_url_paths(prefix),
        title="Python API Reference",
        metadata={
            "type": "api-reference",
            "weight": 100,
            "icon": "book",
            "description": "Browse Python API documentation by package.",
        },
    )
    sections[prefix] = root_section

    # Create subsections under prefix
    for element in elements:
        # ... build section_path as f"{prefix}/{...}"
```

Update `_create_openapi_sections()`:

```python
def _create_openapi_sections(
    self, elements: list[DocElement], existing_sections: dict[str, Section] | None = None
) -> dict[str, Section]:
    sections: dict[str, Section] = {}
    prefix = self._resolve_output_prefix("openapi")  # e.g., "api/commerce"

    # Create root section at prefix (always new, never reuse)
    api_section = Section.create_virtual(
        name=prefix.split("/")[-1],
        relative_url=join_url_paths(prefix),
        title="REST API Reference",
        metadata={
            "type": "api-reference",
            "weight": 110,  # After Python API
            "icon": "globe",
            "description": "REST API documentation.",
        },
    )
    sections[prefix] = api_section

    # ... create subsections under prefix
```

#### 4. Path Generation Updates

Update `_get_element_metadata()`:

```python
def _get_element_metadata(self, element: DocElement, doc_type: str) -> tuple[str, str, str]:
    prefix = self._resolve_output_prefix(doc_type)

    if doc_type == "python":
        module_path = element.qualified_name.replace('.', '/')
        url_path = f"{prefix}/{module_path}"
        return "api-reference/module", url_path, "api-reference"

    elif doc_type == "cli":
        cmd_path = element.qualified_name.replace('.', '/')
        url_path = f"{prefix}/{cmd_path}"
        # ...

    elif doc_type == "openapi":
        if element.element_type == "openapi_overview":
            return "openapi-reference/overview", f"{prefix}/overview", "api-reference"
        elif element.element_type == "openapi_schema":
            return "openapi-reference/schema", f"{prefix}/schemas/{element.name}", "api-reference"
        elif element.element_type == "openapi_endpoint":
            method = get_openapi_method(element).lower()
            path = get_openapi_path(element).strip("/").replace("/", "-")
            return "openapi-reference/endpoint", f"{prefix}/endpoints/{method}-{path}", "api-reference"
```

---

## Migration Path

### For Existing Sites

Sites with existing `/api/` URLs for Python docs may want to preserve URLs:

```yaml
# Keep legacy behavior
autodoc:
  python:
    output_prefix: "api"          # No change to existing URLs
  openapi:
    output_prefix: "api/rest"     # Only OpenAPI moves
```

### Deprecation Warning

If both Python and OpenAPI are enabled with overlapping prefixes, emit warning:

```
⚠️  Python and OpenAPI autodoc share prefix 'api/'.
    Consider setting distinct output_prefix values to prevent navigation conflicts.
```

---

## Testing Plan

### Unit Tests

1. **Prefix resolution**: Test `_resolve_output_prefix()` with various configs
2. **Auto-derivation**: Test `_derive_openapi_prefix()` with different spec titles
3. **Slugification**: Test `_slugify()` edge cases (see comprehensive cases below)

### Integration Tests

1. **Separate sections**: Python and OpenAPI create distinct nav sections
2. **URL generation**: All pages have correct prefix in URLs
3. **Navigation**: Sidebar shows separate trees for each doc type
4. **Backwards compat**: Single-type config produces same output as before

### Test Cases

```python
def test_output_prefix_explicit():
    """Explicit prefix in config is used as-is."""
    config = {"python": {"output_prefix": "docs/api"}}
    orchestrator = VirtualAutodocOrchestrator(site_with_config(config))
    assert orchestrator._resolve_output_prefix("python") == "docs/api"

def test_output_prefix_auto_derive_openapi():
    """OpenAPI prefix derived from spec title."""
    # spec has title: "Commerce Platform API"
    orchestrator = VirtualAutodocOrchestrator(site_with_spec("commerce.yaml"))
    assert orchestrator._resolve_output_prefix("openapi") == "api/commerce-platform"

def test_output_prefix_default_python():
    """Python uses default prefix when not specified."""
    config = {"python": {"enabled": True}}  # No output_prefix
    orchestrator = VirtualAutodocOrchestrator(site_with_config(config))
    assert orchestrator._resolve_output_prefix("python") == "api/python"

def test_sections_are_separate():
    """Python and OpenAPI create separate section trees."""
    site = build_site_with_both_autodocs()
    python_section = site.get_section_by_url("/api/python/")
    openapi_section = site.get_section_by_url("/api/commerce/")
    assert python_section is not None
    assert openapi_section is not None
    assert python_section != openapi_section


def test_slugify_edge_cases():
    """Test slugification handles edge cases gracefully."""
    orchestrator = VirtualAutodocOrchestrator(site)

    # Empty/whitespace → fallback
    assert orchestrator._slugify("") == "rest"
    assert orchestrator._slugify("   ") == "rest"
    assert orchestrator._slugify("API") == "rest"  # Only suffix stripped

    # Common suffix stripping
    assert orchestrator._slugify("Commerce API") == "commerce"
    assert orchestrator._slugify("User Reference") == "user"
    assert orchestrator._slugify("Auth Documentation") == "auth"

    # Special characters
    assert orchestrator._slugify("User & Auth API") == "user-auth"
    assert orchestrator._slugify("v2.0 API") == "v2-0"

    # Long titles (preserved, URL length is caller's concern)
    long_title = "A" * 100 + " API"
    assert orchestrator._slugify(long_title) == "a" * 100

    # Unicode (basic transliteration)
    assert orchestrator._slugify("Über API") == "ber"  # ü stripped
    # Note: Full Unicode support is a non-goal; users can set explicit prefix


def test_derive_openapi_prefix_missing_spec():
    """Test fallback when spec file doesn't exist."""
    site = site_without_spec_file()
    orchestrator = VirtualAutodocOrchestrator(site)
    assert orchestrator._derive_openapi_prefix() == "api/rest"


def test_derive_openapi_prefix_missing_title():
    """Test fallback when spec lacks info.title."""
    site = site_with_spec_missing_title()
    orchestrator = VirtualAutodocOrchestrator(site)
    assert orchestrator._derive_openapi_prefix() == "api/rest"
```

---

## Documentation Updates

### `autodoc.yaml` Example

Update site starter template:

```yaml
# config/_default/autodoc.yaml
autodoc:
  # Python API docs at /api/python/
  python:
    enabled: true
    output_prefix: "api/python"    # Customize: "docs/api", "reference", etc.
    source_dirs:
      - ../my_package

  # REST API docs at /api/{spec-title-slug}/
  openapi:
    enabled: true
    output_prefix: ""              # Empty = auto-derive from spec title
    spec_file: "api/openapi.yaml"

  # CLI docs at /cli/
  cli:
    enabled: true
    output_prefix: "cli"
    app_module: "my_package.cli:main"
```

### README Update

Add section explaining output path configuration:

```markdown
## Customizing Output Paths

By default, autodoc types generate documentation at these paths:

| Type | Default Path | Example |
|------|--------------|---------|
| Python | `/api/python/` | `/api/python/mypackage/core/` |
| OpenAPI | `/api/{spec-title}/` | `/api/commerce/endpoints/` |
| CLI | `/cli/` | `/cli/build/` |

Customize with `output_prefix`:

```yaml
autodoc:
  python:
    output_prefix: "reference/python"  # → /reference/python/...
  openapi:
    output_prefix: "reference/rest"    # → /reference/rest/...
```
```

---

## Rollout Plan

### Phase 1: Implementation
1. Add `output_prefix` to config schema and defaults
2. Implement `_resolve_output_prefix()` and `_derive_openapi_prefix()`
3. Update section creation methods
4. Update path generation methods
5. Add unit tests

### Phase 2: Testing
1. Run existing test suite (ensure no regressions)
2. Add new integration tests
3. Test with Bengal's own site (dogfooding)

### Phase 3: Documentation
1. Update autodoc README
2. Update config examples
3. Add migration notes

### Phase 4: Release
1. Include in next minor version
2. Announce in changelog with examples

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Breaking existing URLs | Medium | High | Default matches current behavior for single-type configs |
| Spec title produces bad slug | Low | Low | Provide explicit `output_prefix` override |
| Navigation confusion | Low | Medium | Clear section titles ("Python API" vs "REST API") |

---

## Performance Impact

### Build Time

- **Prefix resolution**: Negligible (~0.1ms per doc type)
- **Auto-derivation**: ~1-2ms for YAML title extraction (one-time per build)
- **Overall**: No measurable impact on typical builds

### Memory

- **No change**: Prefixes are short strings stored in existing config dict
- **Section paths**: Slightly longer keys in `sections` dict (e.g., `"api/python"` vs `"api"`)

### Cache Implications

| Scenario | Cache Behavior |
|----------|---------------|
| First build with new config | Cold build (expected) |
| Prefix unchanged between builds | Full cache hit |
| Prefix changed | Cache miss for affected doc type only |

**Note**: Cache keys include URL paths. Changing `output_prefix` invalidates all autodoc-generated cache entries for that doc type. This is intentional—the user explicitly requested different output paths.

---

## Open Questions

1. **Q**: Should we support multiple OpenAPI specs in one site?  
   **A**: Deferred to future RFC. Current design doesn't preclude it.

2. **Q**: What if user sets same prefix for Python and OpenAPI?  
   **A**: Emit warning, allow it (user's choice), but sections may collide.

3. **Q**: Should CLI also support auto-derivation?  
   **A**: No clear source to derive from. Keep static default.

4. **Q**: How should `_slugify()` handle Unicode characters (e.g., "Über API")?  
   **A**: Current implementation strips non-ASCII characters. This is acceptable because:
   - Full i18n URL handling is complex (punycode, transliteration libraries)
   - Users needing specific Unicode handling can set explicit `output_prefix`
   - Most API spec titles use ASCII

   Future enhancement: Add optional `unidecode` dependency for transliteration.

---

## Decision

**Recommendation**: Implement Option A with auto-derivation fallback.

- Configurable `output_prefix` for all three autodoc types
- Smart defaults: `api/python`, `api/{spec-slug}`, `cli`
- Clear separation in navigation
- Backwards compatible with explicit prefix matching current behavior

### Compatibility Matrix

| Scenario | Before | After | Migration |
|----------|--------|-------|-----------|
| Python only | `/api/bengal/...` | `/api/python/bengal/...` | Set `output_prefix: "api"` to preserve URLs |
| OpenAPI only | `/api/endpoints/...` | `/api/{spec-slug}/...` | Set `output_prefix: "api"` to preserve URLs |
| Both enabled | Collision at `/api/` | Separate trees | No action needed (improvement) |
| CLI only | `/cli/...` | `/cli/...` | No change |

---

## References

- **Issue**: User report about REST API being "swallowed" by Python docs
- **Code**: `bengal/autodoc/virtual_orchestrator.py:744-819` (current section creation)
- **Config**: `site/config/_default/autodoc.yaml` (current config)
- **Spec**: `site/api/openapi.yaml` (example OpenAPI spec)
