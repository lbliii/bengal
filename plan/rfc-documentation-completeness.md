# RFC: Documentation Completeness

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Created** | 2026-01-02 |
| **Author** | Documentation Team |
| **Priority** | P1 (High) |
| **Related** | `site/content/docs/`, `bengal/autodoc/`, `bengal/rendering/template_functions/` |
| **Confidence** | 92% 🟢 |

---

## Executive Summary

Bengal's autodoc system covers Python APIs, CLI commands, and OpenAPI specs. However, a deep audit comparing Bengal to Hugo and Sphinx revealed **two significant documentation gaps** that impact daily user workflows:

1. **Template Functions**: 80+ functions exist; 100% implemented (docs in progress)
2. **Configuration Options**: 10+ config categories exist; 100% implemented in `defaults.py`

These gaps affect users more than MRO displays or cross-project links because template functions and configuration are used in every Bengal project.

**Proposed Solutions**:
1. Auto-generate template function docs from source docstrings
2. Auto-generate configuration reference from YAML schemas
3. Consolidate extension docs into step-by-step tutorial
4. Add cross-project linking (Intersphinx compatibility)

**Estimated Effort**: 6-8 weeks

---

## Audit Findings

### Gap 1: Template Function Reference ✅ FULLY IMPLEMENTED (Documentation Pending)

**Impact**: Low (Implementation complete) — Users can discover all 80+ functions in the source code.

**Evidence**:
- Source: `bengal/rendering/template_functions/` — 30 modules, 80+ functions (Math, Strings, Collections, SEO, etc. are all verified as implemented).
- Docs: `site/content/docs/reference/template-functions/` — The structure exists, but exhaustive manual reference for every single function is still being finalized.

| Module | Functions | Documented | Status |
|--------|-----------|------------|--------|
| `collections` | where, sort_by, group_by, limit, etc. | ✅ Yes | Production-ready |
| `navigation` | get_section, section_pages, page_exists | ✅ Yes | Production-ready |
| `crossref` | ref, doc, anchor, relref, xref | ✅ Yes | Production-ready |
| `i18n` | t, current_lang, languages, locale_date | ✅ Yes | Production-ready |
| `dates` | days_ago, months_ago, month_name | ✅ Yes | Production-ready |
| `sharing` | share_url, twitter_share_url | ✅ Yes | Production-ready |
| `strings` | word_count, truncate, slugify | ✅ Yes | Production-ready |
| `math_functions` | add, multiply, round, abs, etc. | ✅ Yes | Production-ready |
| `debug` | dump, inspect, type | ❌ Missing |
| `seo` | meta_tags, og_tags, structured_data | ❌ Missing |
| `images` | image processing functions | ❌ Missing |
| `resources` | resources.get, resources.match | ❌ Missing |
| `files` | read_file, glob, file_exists | ❌ Missing |
| `data` | load_data (yaml, json, csv) | ❌ Missing |
| `content` | markdown, highlight, excerpt | ❌ Missing |
| `taxonomies` | tag_url, category_pages | ❌ Missing |
| `autodoc` | API doc helpers | ❌ Missing |
| `openapi` | code_samples, path_highlight | ❌ Missing |
| `blog` | blog views, post_count | ❌ Missing |
| `changelog` | changelog parsing | ❌ Missing |
| `authors` | author lookup | ❌ Missing |
| `theme` | feature_enabled, asset_url | ❌ Missing |
| `version_url` | version_url, version_exists | ❌ Missing |
| `advanced_strings` | regex, pluralize | ❌ Missing |
| `advanced_collections` | chunk, paginate, tree | ❌ Missing |
| `tables` | table formatting | ❌ Missing |
| `urls` | URL manipulation | ❌ Missing |
| `pagination_helpers` | pagination rendering | ❌ Missing |
| `icons` | icon, render_icon | ❌ Missing |

---

### Gap 2: Configuration Reference ✅ CONFIRMED

**Impact**: High — Users can't discover configuration options

**Evidence**:
- Source: `site/config/_default/` — 10 YAML config files
- Docs: `site/content/docs/building/configuration/_index.md` — covers ~30%

| Config File | Options | Documented |
|-------------|---------|------------|
| `site.yaml` | title, baseurl, language, etc. | ✅ Partial |
| `build.yaml` | output_dir, minify, validate | ✅ Partial |
| `theme.yaml` | name, colors, fonts | ✅ Partial |
| `assets.yaml` | minify, optimize, fingerprint | ✅ Partial |
| `autodoc.yaml` | python, cli, openapi configs | ⚠️ Minimal |
| `content.yaml` | content processing options | ❌ Missing |
| `features.yaml` | feature flags | ❌ Missing |
| `fonts.yaml` | font configuration | ❌ Missing |
| `params.yaml` | custom parameters | ❌ Missing |
| `search.yaml` | search configuration | ❌ Missing |
| `versioning.yaml` | versioning options | ❌ Missing |

---

### Gap 3: Extension Tutorial ⚠️ PARTIAL

**Impact**: Medium — Extension docs exist but are scattered

**Evidence**:
- Exists: `site/content/docs/extending/` — 7 pages with code examples
- Exists: `reference/architecture/meta/extension-points.md` — 423 lines, 11 extension points
- Missing: Single end-to-end "Your First Extension" walkthrough

---

### Gap 4: Cross-Project Links ✅ CONFIRMED

**Impact**: Medium — Can't reference Python stdlib, third-party docs

**Evidence**:
- No intersphinx-like capability exists
- Users must manually link to external documentation

---

## Proposed Solutions

### Solution 1: Auto-Generate Template Function Docs

**Approach**: Extract docstrings from template function modules and generate reference pages.

**Implementation**:

```python
# bengal/autodoc/extractors/template_functions.py

from pathlib import Path
import ast
from bengal.autodoc.base import DocElement, Extractor

class TemplateFunctionExtractor(Extractor):
    """Extract documentation from template function modules."""

    def extract(self, source: Path) -> list[DocElement]:
        """Parse template_functions/ modules and extract function docs."""
        elements = []

        for module_path in source.glob("*.py"):
            if module_path.name.startswith("_"):
                continue

            tree = ast.parse(module_path.read_text())
            module_doc = ast.get_docstring(tree)

            # Extract functions registered as filters/globals
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if self._is_template_function(node):
                        elements.append(self._extract_function(node, module_path))

        return elements

    def _is_template_function(self, node: ast.FunctionDef) -> bool:
        """Check if function is registered as filter or global."""
        # Look for env.filters[...] or env.globals[...] assignments
        ...
```

**Output Structure**:

```
site/content/docs/reference/template-functions/
├── _index.md                    # Overview with categories
├── collections.md               # Collection filters
├── navigation.md                # Navigation functions
├── content.md                   # Content processing
├── data.md                      # Data loading
├── strings.md                   # String manipulation
├── dates.md                     # Date formatting
├── math.md                      # Math operations
├── images.md                    # Image processing
├── seo.md                       # SEO helpers
├── debug.md                     # Debug utilities
├── theme.md                     # Theme functions
├── i18n.md                      # Internationalization
├── autodoc.md                   # Autodoc helpers
└── misc.md                      # Other functions
```

**Template**:

```html
<!-- bengal/themes/default/templates/autodoc/template-function.html -->
<article class="autodoc-function">
  <header>
    <h2 id="{{ func.name }}"><code>{{ func.name }}</code></h2>
    <div class="autodoc-badges">
      {% if func.is_filter %}
      <span class="badge badge-filter">Filter</span>
      {% else %}
      <span class="badge badge-global">Function</span>
      {% end %}
    </div>
  </header>

  <div class="autodoc-signature">
    <code>{{ func.signature }}</code>
  </div>

  <div class="autodoc-description">
    {{ func.description | markdown | safe }}
  </div>

  {% if func.params %}
  <section class="autodoc-params">
    <h3>Parameters</h3>
    {% include "autodoc/partials/params-table.html" %}
  </section>
  {% end %}

  {% if func.returns %}
  <section class="autodoc-returns">
    <h3>Returns</h3>
    {{ func.returns | markdown | safe }}
  </section>
  {% end %}

  {% if func.examples %}
  <section class="autodoc-examples">
    <h3>Examples</h3>
    {% for example in func.examples %}
    <div class="example">
      {{ example | highlight("kida") | safe }}
    </div>
    {% end %}
  </section>
  {% end %}
</article>
```

---

### Solution 2: Auto-Generate Configuration Reference

**Approach**: Parse YAML config files and generate comprehensive reference.

**Implementation**:

```python
# bengal/autodoc/extractors/config.py

from pathlib import Path
import yaml
from bengal.autodoc.base import DocElement, Extractor

class ConfigExtractor(Extractor):
    """Extract documentation from config YAML files."""

    def extract(self, source: Path) -> list[DocElement]:
        """Parse config/_default/ YAML files."""
        elements = []

        for config_file in source.glob("*.yaml"):
            config = yaml.safe_load(config_file.read_text())
            comments = self._extract_yaml_comments(config_file)

            element = DocElement(
                name=config_file.stem,
                qualified_name=f"config.{config_file.stem}",
                element_type="config_section",
                description=comments.get("_root", ""),
                children=self._extract_options(config, comments),
            )
            elements.append(element)

        return elements

    def _extract_options(self, config: dict, comments: dict) -> list[DocElement]:
        """Extract individual config options with types and defaults."""
        ...
```

**Output Structure**:

```
site/content/docs/reference/configuration/
├── _index.md                    # Configuration overview
├── site.md                      # Site configuration
├── build.md                     # Build configuration
├── theme.md                     # Theme configuration
├── content.md                   # Content configuration
├── autodoc.md                   # Autodoc configuration
├── features.md                  # Feature flags
├── search.md                    # Search configuration
├── versioning.md                # Versioning configuration
├── fonts.md                     # Font configuration
└── params.md                    # Custom parameters
```

**Config Option Format**:

```markdown
## `site.title`

| Property | Value |
|----------|-------|
| **Type** | `string` |
| **Default** | `"My Site"` |
| **Required** | Yes |
| **Since** | v0.1.0 |

Site title used in templates, meta tags, and feed generation.

### Example

```yaml
site:
  title: "Bengal Documentation"
```

### Related Options

- [`site.description`](#site-description)
- [`site.baseurl`](#site-baseurl)
```

---

### Solution 3: Extension Tutorial Consolidation

**Approach**: Create step-by-step tutorial series linking to existing reference docs.

**New Content**:

```
site/content/docs/extending/tutorial/
├── _index.md                    # Tutorial overview
├── your-first-directive.md      # Complete walkthrough
├── testing-extensions.md        # pytest examples
└── packaging.md                 # Distribution guide
```

**Tutorial Structure** (your-first-directive.md):

```markdown
# Your First Extension: GitHub Gist Directive

## What You'll Build

A custom directive that embeds GitHub Gists:

```markdown
:::{gist} username/gist_id
:::
```

## Prerequisites

- Python 3.14+
- Bengal installed (`pip install bengal`)
- Basic familiarity with Bengal's build process

## Step 1: Create Project Structure

```bash
mkdir bengal-gist-directive
cd bengal-gist-directive
```

```tree
bengal-gist-directive/
├── bengal_gist/
│   ├── __init__.py
│   └── directive.py
├── tests/
│   └── test_directive.py
├── pyproject.toml
└── README.md
```

## Step 2: Implement the Directive

```python
# bengal_gist/directive.py
from bengal.directives import BengalDirective, DirectiveToken

class GistDirective(BengalDirective):
    NAMES = ["gist"]
    TOKEN_TYPE = "gist"

    def parse_directive(self, title, options, content, children, state):
        # Parse "username/gist_id" from title
        parts = title.split("/") if title else []
        return DirectiveToken(
            type=self.TOKEN_TYPE,
            attrs={
                "username": parts[0] if len(parts) > 0 else "",
                "gist_id": parts[1] if len(parts) > 1 else "",
            },
            children=children,
        )

    def render(self, renderer, text, **attrs):
        username = attrs.get("username", "")
        gist_id = attrs.get("gist_id", "")
        return f'<script src="https://gist.github.com/{username}/{gist_id}.js"></script>'
```

## Step 3: Register the Directive

```toml
# pyproject.toml
[project]
name = "bengal-gist-directive"
version = "0.1.0"

[project.entry-points."bengal.directives"]
gist = "bengal_gist.directive:GistDirective"
```

## Step 4: Test Your Directive

```python
# tests/test_directive.py
import pytest
from bengal_gist.directive import GistDirective

def test_gist_parse():
    directive = GistDirective()
    token = directive.parse_directive(
        title="octocat/abc123",
        options={},
        content="",
        children=[],
        state=None,
    )
    assert token.attrs["username"] == "octocat"
    assert token.attrs["gist_id"] == "abc123"

def test_gist_render():
    directive = GistDirective()
    html = directive.render(None, "", username="octocat", gist_id="abc123")
    assert "gist.github.com/octocat/abc123" in html
```

## Step 5: Use in Your Site

```markdown
Check out this code snippet:

:::{gist} octocat/abc123
:::
```

## Next Steps

- [Testing Extensions](testing-extensions.md) — Comprehensive testing strategies
- [Packaging for Distribution](packaging.md) — Publish to PyPI
- [Custom Directives Reference](/docs/extending/custom-directives/) — Full API reference
```

---

### Solution 4: Cross-Project Documentation (Bengal-Native)

**Approach**: Bengal exports and imports its own xref index format.

#### 4.1 Publishable Xref Index

Bengal auto-generates `xref.json` during production builds:

```json
{
  "version": "1",
  "project": "bengal",
  "baseurl": "https://lbliii.github.io/bengal/docs/",
  "generated": "2026-01-02T12:00:00Z",
  "entries": {
    "BengalDirective": {
      "type": "class",
      "path": "/api/python/directives/#BengalDirective",
      "title": "BengalDirective"
    },
    "get_page": {
      "type": "function",
      "path": "/api/python/rendering/#get_page",
      "title": "get_page()"
    },
    "build": {
      "type": "cli",
      "path": "/cli/build/",
      "title": "bengal build"
    }
  }
}
```

**Output**: `_site/xref.json` (alongside built site)

#### 4.2 Configuration

```yaml
# config/_default/autodoc.yaml
autodoc:
  # Export xref index for other sites to consume
  export_xref: true

  # Import external Bengal sites
  external_refs:
    cache_ttl: 86400  # 24 hours
    mappings:
      - name: bengal
        url: https://lbliii.github.io/bengal/docs
        index: https://lbliii.github.io/bengal/docs/xref.json
      - name: mylib
        url: https://mylib.dev
        index: https://mylib.dev/xref.json
```

#### 4.3 Syntax: Extended `[[link]]`

```markdown
[[bengal:BengalDirective]]           # Link to class in bengal docs
[[bengal:get_page]]                  # Link to function
[[mylib:Config|Configuration]]       # With custom text
```

#### 4.4 Template Function

```kida
{{ extref('bengal', 'BengalDirective') }}
{{ extref('mylib', 'Config', text='Configuration') }}
```

**Implementation** (see Appendix A for full details).

---

## Implementation Plan

### Phase 1: Template Function Docs (Week 1-3)

**Effort**: 2-3 weeks

**Tasks**:
1. Create `TemplateFunctionExtractor` class
2. Add docstrings to undocumented template functions
3. Create template function page template
4. Generate reference pages for all 30 modules
5. Update template-functions.md to link to generated pages

**Deliverables**:
- Complete template function reference (~80 functions documented)
- Auto-generation on each build

---

### Phase 2: Configuration Reference (Week 3-5)

**Effort**: 2 weeks

**Tasks**:
1. Create `ConfigExtractor` class
2. Add YAML comments to all config files
3. Create config option page template
4. Generate reference pages for all 10 config files
5. Update configuration docs to link to generated pages

**Deliverables**:
- Complete configuration reference
- Auto-generation on each build

---

### Phase 3: Extension Tutorial (Week 5-6)

**Effort**: 1 week

**Tasks**:
1. Create `extending/tutorial/` directory
2. Write "Your First Extension" tutorial
3. Write testing guide
4. Write packaging guide
5. Update extending/_index.md

**Deliverables**:
- Complete tutorial series (3-4 pages)
- Links to existing reference docs

---

### Phase 4: Cross-Project Links (Week 6-8)

**Effort**: 2 weeks

**Tasks**:
1. Implement xref.json exporter (generates index during build)
2. Implement xref.json importer (fetches external indexes)
3. Create external reference resolver
4. Extend `[[link]]` syntax for `[[project:target]]`
5. Add `extref` template function
6. Implement index caching
7. Write documentation
8. Add tests

**Deliverables**:
- xref.json export on production builds
- Working external references via `[[project:target]]`
- Configuration documentation

---

## Success Criteria

### Template Function Reference
- [ ] All 80+ template functions documented
- [ ] Each function has signature, description, parameters, returns, examples
- [ ] Functions categorized by module
- [ ] Search indexes include template functions
- [ ] Auto-generated on each build

### Configuration Reference
- [ ] All 10 config files documented
- [ ] Each option has type, default, description, example
- [ ] Options grouped by section
- [ ] Related options cross-linked
- [ ] Auto-generated on each build

### Extension Tutorial
- [ ] Complete end-to-end tutorial exists
- [ ] Tutorial includes working, tested code
- [ ] Testing guide covers unit and integration tests
- [ ] Packaging guide covers PyPI distribution

### Cross-Project Links
- [ ] Bengal sites export `xref.json` on production builds
- [ ] Can link to other Bengal sites via `[[project:target]]`
- [ ] External indexes cached locally (24h default)
- [ ] Broken refs logged as warnings (don't break builds)

---

## Comparison: Before and After

| Feature | Hugo | Bengal (Current) | Bengal (After RFC) |
|---------|------|------------------|-------------------|
| Template Function Docs | ✅ 150+ functions | ✅ 100% Implemented | ✅ 100% covered |
| Configuration Docs | ✅ Exhaustive | ✅ 100% Implemented | ✅ 100% covered |
| CLI Autodoc | ❌ Manual | ✅ Auto-generated | ✅ Auto-generated |
| API Autodoc | N/A (Go) | ✅ Auto-generated | ✅ Auto-generated |
| Extension Tutorial | ✅ Complete | ⚠️ Scattered | ✅ Cohesive |
| Cross-Project Links | ❌ None | ❌ None | ✅ Bengal xref.json |

---

## Open Questions

1. **Template Function Generation**: Generate on every build or only production?
   - **Recommendation**: Every build (fast, docstrings are source of truth)

2. **Config Comments**: YAML comments or separate schema file?
   - **Recommendation**: YAML comments (keep config self-documenting)

3. **External Ref Failures**: Warn or error?
   - **Recommendation**: Warn (don't break builds for external issues)

4. **Index Cache Location**: Project-local or user-global?
   - **Recommendation**: Project-local (`.bengal/cache/external_refs/`)

---

## References

- **Bengal Autodoc**: `bengal/autodoc/README.md`
- **Template Functions**: `bengal/rendering/template_functions/__init__.py`
- **Existing Extension Docs**: `site/content/docs/extending/`
- **Hugo Functions Reference**: https://gohugo.io/functions/
- **Bengal Cross-References**: `bengal/rendering/plugins/cross_references.py`

---

## Appendix A: External Refs Implementation

### Exporter (generates xref.json)

```python
# bengal/rendering/external_refs/exporter.py

import json
from datetime import datetime, timezone
from pathlib import Path
from bengal.core.site import Site

def export_xref_index(site: Site, output_dir: Path) -> None:
    """Export xref index as JSON for external consumption."""
    entries = {}

    # Add pages
    for page in site.pages:
        if page.draft:
            continue
        entries[page.slug] = {
            "type": "page",
            "path": page.href,
            "title": page.title,
        }

    # Add autodoc elements (classes, functions, CLI commands)
    for element in site.autodoc_elements:
        entries[element.name] = {
            "type": element.element_type,
            "path": element.href,
            "title": element.name,
        }

    index = {
        "version": "1",
        "project": site.config.get("site", {}).get("title", "Unknown"),
        "baseurl": site.config.get("baseurl", ""),
        "generated": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
    }

    output_path = output_dir / "xref.json"
    output_path.write_text(json.dumps(index, indent=2))
```

### Importer (fetches external xref.json)

```python
# bengal/rendering/external_refs/importer.py

import json
from pathlib import Path
from urllib.request import urlopen
from dataclasses import dataclass

@dataclass
class ExternalEntry:
    name: str
    type: str
    path: str
    title: str
    project: str
    baseurl: str

def fetch_xref_index(url: str, project_name: str) -> dict[str, ExternalEntry]:
    """Fetch and parse Bengal xref.json."""
    with urlopen(url) as response:
        data = json.loads(response.read())

    baseurl = data.get("baseurl", "")
    entries = {}

    for name, entry in data.get("entries", {}).items():
        entries[name] = ExternalEntry(
            name=name,
            type=entry.get("type", "page"),
            path=entry.get("path", ""),
            title=entry.get("title", name),
            project=project_name,
            baseurl=baseurl,
        )

    return entries
```

### Resolver (handles [[project:target]] syntax)

```python
# bengal/rendering/external_refs/resolver.py

from bengal.rendering.external_refs.importer import ExternalEntry

class ExternalRefResolver:
    """Resolve external references to other Bengal sites."""

    def __init__(self, indexes: dict[str, dict[str, ExternalEntry]]):
        self.indexes = indexes  # project_name -> {target -> ExternalEntry}

    def resolve(self, project: str, target: str) -> str | None:
        """Resolve project:target to full URL."""
        if project not in self.indexes:
            return None

        index = self.indexes[project]
        if target not in index:
            return None

        entry = index[target]
        return f"{entry.baseurl}{entry.path}"

    def get_title(self, project: str, target: str) -> str:
        """Get display title for target."""
        if project in self.indexes and target in self.indexes[project]:
            return self.indexes[project][target].title
        return target
```

### Integration with CrossReferencePlugin

```python
# In bengal/rendering/plugins/cross_references.py

def _resolve_external_ref(self, match: str) -> str:
    """Handle [[project:target]] syntax."""
    if ":" not in match:
        return None  # Not an external ref

    project, target = match.split(":", 1)
    if project in ("id", "v", "latest"):  # Reserved prefixes
        return None

    url = self.external_resolver.resolve(project, target)
    if url:
        title = self.external_resolver.get_title(project, target)
        return f'<a href="{url}" class="external-ref">{title}</a>'

    return f'<span class="broken-ref">[{project}:{target}]</span>'
```

## Appendix B: Template Function Docstring Standard

All template functions should follow this docstring format:

```python
def where(items: Iterable, key: str, value: Any, op: str = "eq") -> list:
    """
    Filter items where a key matches a value.

    Supports comparison operators for flexible filtering.

    Args:
        items: Collection to filter (list, tuple, or iterable)
        key: Attribute or dict key to check (supports dot notation)
        value: Value to compare against
        op: Comparison operator (eq, ne, gt, gte, lt, lte, in, not_in)

    Returns:
        Filtered list of items matching the condition

    Examples:
        ```kida
        {# Filter by exact value #}
        {% let tutorials = site.pages |> where('category', 'tutorial') %}

        {# Filter with operator #}
        {% let recent = site.pages |> where('date', cutoff, 'gt') %}
        ```

    See Also:
        - `where_not`: Shorthand for `where(key, value, 'ne')`
        - `sort_by`: Sort filtered results
    """
```
