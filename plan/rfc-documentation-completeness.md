# RFC: Documentation Completeness and Reference Improvements

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Created** | 2026-01-02 |
| **Author** | Documentation Team |
| **Priority** | P2 (Medium) |
| **Related** | `site/content/docs/`, `bengal/autodoc/`, `bengal/themes/default/templates/autodoc/` |
| **Confidence** | 85% 🟢 |

---

## Executive Summary

This RFC proposes targeted improvements to Bengal's documentation system. Bengal already provides comprehensive autodoc coverage for Python APIs, CLI commands, and OpenAPI specs—including self-documentation of its own tooling. This RFC addresses the remaining gaps identified through comparison with Sphinx.

**Actual Gaps:**
1. **MRO & Inheritance Visualization**: Class hierarchy display and diagrams
2. **Cross-Project Documentation**: Intersphinx-like linking to external docs
3. **Auto-Generated Indexes**: genindex/modindex equivalents
4. **Extension Tutorial Cohesion**: Consolidate existing docs into step-by-step guide

**Estimated Effort**: 5-7 weeks (reduced from original estimate after audit)

---

## Current State

### What Bengal Does Well

Bengal's autodoc system is more complete than initially assessed:

| Capability | Status | Evidence |
|------------|--------|----------|
| **Python Autodoc** | ✅ Complete | AST-based extraction with signatures, params, returns, decorators, examples |
| **Raises/Exceptions** | ✅ Implemented | `docstring_parser.py` extracts; `raises.html` renders |
| **CLI Autodoc** | ✅ Complete | Click/argparse/Typer introspection with options, arguments, types |
| **OpenAPI Autodoc** | ✅ Complete | Endpoints, parameters, request bodies, responses, schemas |
| **Self-Documentation** | ✅ Yes | Bengal documents its own CLI and API (`site/api/openapi.yaml`) |
| **Extension Docs** | ⚠️ Exists | 6 pages in `extending/`; needs tutorial consolidation |

### Actual Gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| MRO display | Users can't see method resolution order | Medium |
| Inheritance diagrams | No visual class hierarchies | Low |
| Cross-project links | Can't reference external docs (Python stdlib, etc.) | High |
| Index pages | No genindex/modindex equivalents | Medium |
| Extension tutorial | Existing docs scattered; no single walkthrough | Medium |

---

## Proposed Solutions

### 1. MRO & Inheritance Visualization

#### 1.1 MRO Documentation

Display Method Resolution Order for classes with multiple inheritance.

**Implementation:**

```python
# bengal/autodoc/extractors/python/extractor.py

def extract_mro(cls_node: ast.ClassDef, module_name: str) -> list[str]:
    """Extract MRO from class bases (static approximation)."""
    # Build linearized MRO from base classes
    # Return list of qualified class names
    pass
```

**Template Addition:**

```html
<!-- bengal/themes/default/templates/autodoc/partials/mro.html -->
{% let mro = element.metadata.mro ?? [] %}
{% if mro | length > 1 %}
<section class="autodoc-section" data-section="mro">
  <h3 class="autodoc-section-title">Method Resolution Order</h3>
  <ol class="autodoc-mro-list">
    {% for cls_name in mro %}
    <li><code>{{ cls_name }}</code></li>
    {% end %}
  </ol>
</section>
{% end %}
```

#### 1.2 Inheritance Diagrams (Optional)

Generate Mermaid diagrams for class hierarchies.

**Decision Required:** Use Mermaid (built-in, no deps) or skip for v1?

**If implemented:**

```python
# bengal/autodoc/utils.py

def generate_inheritance_diagram(class_elem: DocElement) -> str:
    """Generate Mermaid class diagram."""
    bases = class_elem.metadata.get("bases", [])
    if not bases:
        return ""
    
    lines = ["classDiagram"]
    for base in bases:
        lines.append(f"    {base} <|-- {class_elem.name}")
    return "\n".join(lines)
```

---

### 2. Cross-Project Documentation

#### 2.1 Intersphinx-Compatible Linking

Enable references to external documentation sets (Python docs, third-party libraries).

**Configuration:**

```toml
# bengal.toml
[autodoc.external_refs]
enabled = true

[[autodoc.external_refs.mappings]]
name = "python"
url = "https://docs.python.org/3"
inventory = "https://docs.python.org/3/objects.inv"

[[autodoc.external_refs.mappings]]
name = "requests"
url = "https://requests.readthedocs.io/en/latest"
inventory = "https://requests.readthedocs.io/en/latest/objects.inv"
```

**New Module:**

```
bengal/autodoc/external_refs/
├── __init__.py          # Public API
├── inventory.py         # Parse Sphinx objects.inv files
├── resolver.py          # Resolve cross-references
└── cache.py             # Cache inventories locally
```

**Template Filter:**

```kida
{# Link to Python's pathlib.Path #}
{{ "pathlib.Path" | extref(project="python") }}

{# Returns: <a href="https://docs.python.org/3/library/pathlib.html#pathlib.Path">pathlib.Path</a> #}
```

#### 2.2 Design Decision: Inventory Format

**Option A: Sphinx `objects.inv` compatibility**
- Pro: Works with existing Sphinx documentation
- Con: Complex format (zlib-compressed, domain-specific)

**Option B: Simple JSON inventory**
- Pro: Easy to implement and debug
- Con: Requires custom inventory generation for external projects

**Recommendation:** Option A for read-only compatibility; don't generate our own inventories.

---

### 3. Auto-Generated Index Pages

#### 3.1 Index Page Generator

Generate comprehensive index pages similar to Sphinx's genindex and modindex.

**Implementation:**

```python
# bengal/autodoc/orchestration/index_generator.py

def generate_index_pages(elements: list[DocElement]) -> list[Page]:
    """Generate alphabetical and categorical indexes."""
    return [
        generate_general_index(elements),    # All documented items A-Z
        generate_module_index(elements),     # Python modules
        generate_function_index(elements),   # All functions
        generate_class_index(elements),      # All classes
    ]
```

**Output:**

```
site/output/api/
├── genindex/           # General index (A-Z)
├── modindex/           # Module index
├── funcindex/          # Function index
└── classindex/         # Class index
```

**Template:**

```html
<!-- bengal/themes/default/templates/autodoc/index.html -->
<nav class="autodoc-index">
  <div class="autodoc-index-letters">
    {% for letter in index_letters %}
    <a href="#{{ letter }}">{{ letter }}</a>
    {% end %}
  </div>
  
  {% for letter, items in index_by_letter.items() %}
  <section id="{{ letter }}">
    <h2>{{ letter }}</h2>
    <dl>
      {% for item in items %}
      <dt><a href="{{ item.href }}"><code>{{ item.name }}</code></a></dt>
      <dd>{{ item.summary }}</dd>
      {% end %}
    </dl>
  </section>
  {% end %}
</nav>
```

---

### 4. Extension Tutorial Consolidation

#### 4.1 Tutorial Structure

Consolidate existing extension documentation into a cohesive tutorial series.

**Current State:**
- `extending/_index.md` - Overview
- `extending/build-hooks.md` - Build hooks
- `extending/collections.md` - Collections
- `extending/custom-directives.md` - Directives
- `extending/custom-sources.md` - Content sources
- `extending/theme-customization.md` - Theming

**Proposed Addition:**

```
extending/
├── _index.md                    # Overview (exists)
├── tutorial/                    # NEW: Step-by-step guide
│   ├── _index.md               # Tutorial overview
│   ├── your-first-directive.md # Complete walkthrough
│   ├── testing-extensions.md   # Testing strategies
│   └── packaging.md            # Distribution guide
├── build-hooks.md              # Reference (exists)
├── collections.md              # Reference (exists)
├── custom-directives.md        # Reference (exists)
├── custom-sources.md           # Reference (exists)
└── theme-customization.md      # Reference (exists)
```

**Tutorial Content:**

```markdown
# Your First Extension: GitHub Gist Directive

## What You'll Build
A directive that embeds GitHub Gists in your documentation.

## Prerequisites
- Python 3.14+
- Basic understanding of Bengal's build pipeline

## Step 1: Create the Directive Class
[Complete code with line-by-line explanation]

## Step 2: Register with Bengal
[Configuration in bengal.toml]

## Step 3: Test Your Directive
[Unit test example using pytest]

## Step 4: Use in Documentation
[Markdown example]

## Next Steps
- [Testing Extensions](testing-extensions.md)
- [Packaging for Distribution](packaging.md)
```

---

## Implementation Plan

### Phase 1: Extension Tutorial (Week 1-2)

**Effort:** 1-2 weeks (content work, no code changes)

**Tasks:**
1. Create `extending/tutorial/` directory structure
2. Write step-by-step directive tutorial
3. Add testing guide with pytest examples
4. Add packaging/distribution guide
5. Update `extending/_index.md` to link to tutorial

**Deliverables:**
- Complete tutorial series (3-4 pages)
- Updated extension overview

---

### Phase 2: MRO Display (Week 2-3)

**Effort:** 1 week

**Tasks:**
1. Add MRO extraction to Python extractor
2. Create `mro.html` partial template
3. Include MRO in class pages
4. Add tests for MRO extraction

**Deliverables:**
- MRO display on class documentation pages
- Unit tests

**Inheritance diagrams:** Defer to future release (optional enhancement)

---

### Phase 3: Index Pages (Week 3-4)

**Effort:** 1-2 weeks

**Tasks:**
1. Implement index page generator
2. Create index templates (genindex, modindex)
3. Add index generation to build pipeline
4. Add navigation links to indexes

**Deliverables:**
- Auto-generated index pages
- Navigation integration

---

### Phase 4: Cross-Project Links (Week 5-7)

**Effort:** 2-3 weeks

**Tasks:**
1. Implement Sphinx inventory parser
2. Create reference resolver
3. Add `extref` template filter
4. Implement inventory caching
5. Write configuration documentation
6. Add tests

**Deliverables:**
- `bengal/autodoc/external_refs/` module
- Configuration documentation
- Working cross-project links

---

## Success Criteria

### MRO Display
- [ ] MRO section appears for classes with multiple inheritance
- [ ] MRO correctly reflects Python's C3 linearization
- [ ] MRO links to documented base classes when available

### Index Pages
- [ ] General index lists all documented items alphabetically
- [ ] Module index lists all Python modules
- [ ] Indexes are generated automatically during build
- [ ] Navigation includes links to indexes

### Cross-Project Links
- [ ] Can link to Python standard library docs
- [ ] Can link to popular third-party libraries (requests, numpy)
- [ ] Inventories are cached locally
- [ ] Broken external refs logged as warnings

### Extension Tutorial
- [ ] Complete step-by-step tutorial exists
- [ ] Tutorial includes working code examples
- [ ] Testing guide covers unit and integration tests
- [ ] Packaging guide covers distribution

---

## Comparison with Sphinx (Revised)

| Feature | Sphinx | Bengal (Current) | Bengal (After RFC) |
|---------|--------|------------------|-------------------|
| Python Autodoc | ✅ | ✅ | ✅ |
| CLI Autodoc | ⚠️ Via extension | ✅ Built-in | ✅ |
| OpenAPI Autodoc | ⚠️ Via extension | ✅ Built-in | ✅ |
| Raises/Exceptions | ✅ | ✅ | ✅ |
| MRO Documentation | ✅ | ❌ | ✅ |
| Inheritance Diagrams | ✅ Via extension | ❌ | ⚠️ Deferred |
| Cross-Project Links | ✅ Intersphinx | ❌ | ✅ |
| Index Pages | ✅ | ❌ | ✅ |
| Extension Tutorial | ✅ Complete | ⚠️ Scattered | ✅ Cohesive |

---

## Open Questions

1. **Inheritance Diagrams:** Include in this RFC or defer?
   - Recommendation: Defer to future release; MRO text display is sufficient for v1

2. **Inventory Caching:** How long to cache external inventories?
   - Recommendation: 24 hours by default, configurable

3. **Index Page Generation:** On every build or only production?
   - Recommendation: Production builds only (skip in dev for speed)

4. **External Ref Failures:** Warn or error on broken external refs?
   - Recommendation: Warn (don't break builds for external issues)

---

## References

- **Sphinx Intersphinx**: https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html
- **Sphinx objects.inv format**: https://sphobjinv.readthedocs.io/
- **Bengal Autodoc Architecture**: `site/content/docs/reference/architecture/subsystems/autodoc.md`
- **Existing Extension Docs**: `site/content/docs/extending/`

---

## Appendix: Inventory Format

Sphinx `objects.inv` files use zlib compression with a text header:

```
# Sphinx inventory version 2
# Project: Python
# Version: 3.12
# The remainder of this file is compressed using zlib.
<zlib-compressed data>
```

Decompressed format (one entry per line):
```
name domain:role priority uri dispname
pathlib.Path py:class 1 library/pathlib.html#pathlib.Path -
```

Libraries for parsing:
- `sphobjinv` (Python): Full read/write support
- Manual parsing: ~100 lines of Python with `zlib`

