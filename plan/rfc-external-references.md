# RFC: External References (Cross-Project Documentation Links)

| Field | Value |
|-------|-------|
| **Status** | Implementing |
| **Created** | 2026-01-02 |
| **Updated** | 2026-01-10 |
| **Author** | Documentation Team |
| **Priority** | P2 (Medium) |
| **Related** | `bengal/rendering/plugins/cross_references.py`, `bengal/rendering/external_refs/`, `bengal/postprocess/xref_index.py` |
| **Confidence** | 95% 🟢 |

---

## Executive Summary

This RFC proposes **External References** — a Bengal-native system for linking to external documentation. Unlike Sphinx's intersphinx (which requires network access and can fail builds), Bengal's solution prioritizes:

1. **Offline-first**: URL templates work without network
2. **Never break builds**: Missing refs = warning, not error
3. **Simple configuration**: No complex inventory setup
4. **Bengal ecosystem**: JSON-based index sharing between Bengal sites

**Syntax:**
```markdown
[[ext:python:pathlib.Path]]              # URL template resolution
[[ext:bengal:BengalDirective]]           # Bengal ecosystem index
[[ext:numpy:ndarray|NumPy Arrays]]       # Custom link text
```

> **Design Decision**: The `ext:` prefix explicitly distinguishes external references from cross-version links (`[[v2:path]]`), avoiding parser ambiguity.

**Estimated Effort**: 2-3 weeks

---

## Problem Statement

### User Need

Documentation authors want to link to external documentation (Python stdlib, third-party libraries, other Bengal sites) without:
- Manually maintaining URLs
- Breaking builds when external sites are down
- Complex configuration

### Intersphinx Pain Points (Research-Based)

| Problem | Impact | Frequency |
|---------|--------|-----------|
| **Network dependency** | Builds fail if external site down | Common |
| **No offline mode** | Can't build on airplane/restricted CI | Common |
| **Slow builds** | Fetching inventories adds latency | Every build |
| **Timeout failures** | Flaky servers cause random CI failures | Intermittent |
| **Large inventories** | Python's `objects.inv` is ~1MB | Memory/bandwidth |
| **Complex config** | Steep learning curve | Onboarding |
| **Missing inventories** | Not all projects publish them | Frequent |

### Design Goals

1. **Offline by default** — Most links resolve without network
2. **Builds never fail** — External issues = warnings only
3. **Progressive enhancement** — Start simple, add features as needed
4. **Bengal-native** — Own format, not Sphinx compatibility

---

## Proposed Solution

### Three-Tier Resolution

```
┌─────────────────────────────────────────────────────────────┐
│                   [[ext:project:target]]                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Tier 1: URL Templates (Instant, Offline)                    │
│ ─────────────────────────────────────────                   │
│ Configured patterns resolve immediately                      │
│ Example: python → docs.python.org/3/library/{module}#{name} │
└─────────────────────────────────────────────────────────────┘
                            │
                     Not found?
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Tier 2: Bengal Index (Cached, Async)                        │
│ ─────────────────────────────────────                       │
│ Fetch xref.json from Bengal sites                           │
│ Cache aggressively (7 days default)                         │
│ Stale-while-revalidate pattern                              │
└─────────────────────────────────────────────────────────────┘
                            │
                     Not found?
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Tier 3: Graceful Fallback                                   │
│ ─────────────────────────────                               │
│ Render as plain text + emit warning                         │
│ Build continues successfully                                 │
└─────────────────────────────────────────────────────────────┘
```

---

### Tier 1: URL Templates

**Zero network, instant resolution.**

Most external documentation has predictable URL patterns. Configure once, resolve forever:

```toml
# bengal.toml
[external_refs]

[external_refs.templates]
# Python standard library
python = "https://docs.python.org/3/library/{module}.html#{name}"

# Popular libraries with predictable URLs  
requests = "https://requests.readthedocs.io/en/latest/api/#{name}"
fastapi = "https://fastapi.tiangolo.com/reference/{module}/#{name}"
pydantic = "https://docs.pydantic.dev/latest/api/{module}/#{name}"

# NumPy/SciPy style
numpy = "https://numpy.org/doc/stable/reference/generated/numpy.{name}.html"
pandas = "https://pandas.pydata.org/docs/reference/api/pandas.{name}.html"
```

**Resolution Logic:**

```python
def resolve_template(project: str, target: str) -> str | None:
    """Resolve using URL template. O(1), no network."""
    template = config.external_refs.templates.get(project)
    if not template:
        return None

    # Parse target: "pathlib.Path" → module="pathlib", name="Path"
    parts = target.rsplit(".", 1)
    module = parts[0] if len(parts) > 1 else target
    name = parts[-1]

    return template.format(
        target=target,
        module=module,
        name=name,
        name_lower=name.lower(),
    )
```

**Usage:**

```markdown
See [[ext:python:pathlib.Path]] for path handling.
Use [[ext:requests:Session]] for connection pooling.
```

**Output:**

```html
See <a href="https://docs.python.org/3/library/pathlib.html#Path">pathlib.Path</a> for path handling.
Use <a href="https://requests.readthedocs.io/en/latest/api/#Session">Session</a> for connection pooling.
```

---

### Tier 2: Bengal Ecosystem Index

**For Bengal-to-Bengal linking with rich metadata.**

#### 2.1 Index Format (xref.json)

Bengal sites export a JSON index during production builds:

```json
{
  "version": "1",
  "generator": "bengal/0.2.0",
  "project": {
    "name": "Bengal",
    "url": "https://lbliii.github.io/bengal/docs/"
  },
  "generated": "2026-01-02T12:00:00Z",
  "entries": {
    "BengalDirective": {
      "type": "class",
      "path": "/api/python/bengal/directives/#BengalDirective",
      "title": "BengalDirective",
      "summary": "Base class for custom directives"
    },
    "get_page": {
      "type": "function",
      "path": "/api/python/bengal/rendering/template_functions/#get_page",
      "title": "get_page()",
      "summary": "Retrieve a page by path"
    },
    "build": {
      "type": "cli",
      "path": "/cli/build/",
      "title": "bengal build",
      "summary": "Build site to output directory"
    },
    "getting-started": {
      "type": "page",
      "path": "/docs/get-started/",
      "title": "Getting Started"
    }
  }
}
```

**Entry Types:**

| Type | Source | Example |
|------|--------|---------|
| `page` | Content pages | Getting Started guide |
| `class` | Python autodoc | BengalDirective |
| `function` | Python autodoc | get_page() |
| `method` | Python autodoc | Site.build() |
| `module` | Python autodoc | bengal.core |
| `cli` | CLI autodoc | bengal build |
| `endpoint` | OpenAPI autodoc | POST /api/users |

#### 2.2 Index Configuration

```toml
# bengal.toml
[external_refs]

# Export index for other sites
export_index = true  # Generates xref.json on production builds

# Import indexes from Bengal ecosystem
[[external_refs.indexes]]
name = "bengal"
url = "https://lbliii.github.io/bengal/docs/xref.json"
cache_days = 7

[[external_refs.indexes]]
name = "mycompany-docs"
url = "https://docs.mycompany.com/xref.json"
cache_days = 1  # Internal docs change frequently
```

#### 2.3 Caching Strategy

```python
@dataclass
class IndexCache:
    """Aggressive caching with stale-while-revalidate."""

    cache_dir: Path = Path(".bengal/cache/external_refs")

    async def get(self, project: str, url: str, max_age_days: int = 7) -> dict | None:
        cache_file = self.cache_dir / f"{project}.json"

        # Check cache
        if cache_file.exists():
            age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            cached = json.loads(cache_file.read_text())

            if age.days < max_age_days:
                return cached  # Fresh cache

            # Stale cache — try refresh in background, return stale immediately
            asyncio.create_task(self._refresh(project, url, cache_file))
            return cached

        # No cache — fetch synchronously (first time only)
        return await self._fetch(url, cache_file)

    async def _fetch(self, url: str, cache_file: Path) -> dict | None:
        """Fetch with timeout, never raise."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    cache_file.write_text(json.dumps(data))
                    return data
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
        return None
```

**Key behaviors:**
- **First build**: Fetch index, cache locally
- **Subsequent builds**: Use cache, refresh in background if stale
- **Offline**: Use stale cache indefinitely
- **Fetch failure**: Use stale cache, log warning, continue build

---

### Tier 3: Graceful Fallback

**Builds never break due to external references.**

When resolution fails at all tiers:

```python
def resolve_external_ref(ref: str, text: str | None = None) -> str:
    """Resolve [[ext:project:target]] with graceful fallback."""
    # Parse ext:project:target format
    parts = ref.split(":", 2)  # ext, project, target
    if len(parts) != 3 or parts[0] != "ext":
        return None  # Not an external ref

    _, project, target = parts

    # Tier 1: URL template
    if url := resolve_template(project, target):
        return f'<a href="{url}" class="extref">{text or target}</a>'

    # Tier 2: Bengal index
    if entry := resolve_index(project, target):
        title = text or entry.title
        return f'<a href="{entry.url}" class="extref" title="{entry.summary}">{title}</a>'

    # Tier 3: Fallback — render as code, emit warning
    logger.warning(
        "unresolved_external_ref",
        project=project,
        target=target,
        suggestion=f"Add '{project}' to external_refs.templates or external_refs.indexes",
    )
    return f'<code class="extref extref-unresolved">ext:{project}:{target}</code>'
```

**Build output:**
```
⚠️  Unresolved external reference: [[ext:scipy:optimize]]
    Suggestion: Add 'scipy' to external_refs.templates in bengal.toml
```

**Health check integration:**
```python
# bengal/health/validators/external_refs.py
class ExternalRefValidator(BaseValidator):
    """Report unresolved external references."""

    def validate(self, site: Site) -> list[CheckResult]:
        results = []
        for ref in site.unresolved_external_refs:
            results.append(CheckResult(
                status=CheckStatus.WARNING,
                message=f"Unresolved: [[ext:{ref.project}:{ref.target}]]",
                file_path=ref.source_file,
                line=ref.line,
                suggestion=f"Add '{ref.project}' to external_refs config",
            ))
        return results
```

---

### Syntax

Extends existing `[[link]]` cross-reference syntax with `ext:` prefix:

```markdown
# Basic external reference
[[ext:python:pathlib.Path]]

# With custom text
[[ext:python:pathlib.Path|Path objects]]

# Multiple parts
[[ext:numpy:numpy.ndarray]]

# CLI commands
[[ext:bengal:build]]

# Pages
[[ext:bengal:getting-started]]
```

**Prefix reference:**
- `ext:` — **External references** (this RFC)
- `id:` — Custom ID lookup
- `v:` or version names — Cross-version links (e.g., `[[v2:docs/guide]]`)
- `#` — Heading anchors
- `!` — Target directive anchors

The `ext:` prefix ensures no collision with existing prefixes and is self-documenting.

---

### Template Function

For dynamic external refs in templates:

```kida
{# Basic #}
{{ ext('python', 'pathlib.Path') }}

{# With custom text #}
{{ ext('python', 'pathlib.Path', text='Path class') }}

{# Check if resolvable #}
{% if ext_exists('numpy', 'ndarray') %}
  See {{ ext('numpy', 'ndarray') }} for array operations.
{% end %}
```

> Template function uses `ext()` for brevity. The `ext:` prefix in markdown keeps authoring clear while templates use a shorter form.

**Implementation:**

```python
# bengal/rendering/template_functions/external_refs.py

def register(env: TemplateEnvironment, site: Site) -> None:
    resolver = ExternalRefResolver(site.config)

    def ext(project: str, target: str, text: str | None = None) -> Markup:
        """Render external reference link."""
        return Markup(resolver.resolve(project, target, text))

    def ext_exists(project: str, target: str) -> bool:
        """Check if external reference is resolvable."""
        return resolver.can_resolve(project, target)

    env.globals["ext"] = ext
    env.globals["ext_exists"] = ext_exists
```

---

## Implementation Plan

### Phase 1: URL Templates (Week 1)

**Effort**: 3-4 days

**Tasks:**
1. Add `external_refs.templates` config parsing
2. Extend `CrossReferencePlugin` to handle `[[ext:project:target]]` syntax
3. Implement template resolution logic
4. Add built-in templates for Python, common libraries
5. Write tests

**Deliverables:**
- `[[ext:python:pathlib.Path]]` works with zero config
- Custom templates configurable in `bengal.toml`

---

### Phase 2: Bengal Index (Week 2)

**Effort**: 4-5 days

**Tasks:**
1. Implement xref.json exporter
2. Implement index fetcher with caching
3. Add `external_refs.indexes` config
4. Integrate with cross-reference resolution
5. Add `extref` template function
6. Write tests

**Deliverables:**
- Bengal sites export xref.json
- Sites can import other Bengal indexes
- Caching works correctly

---

### Phase 3: Polish & Documentation (Week 3)

**Effort**: 3-4 days

**Tasks:**
1. Add health check validator for unresolved refs
2. Improve error messages and suggestions
3. Write user documentation
4. Add more built-in URL templates
5. Performance optimization

**Deliverables:**
- Complete documentation
- Health check integration
- Production-ready feature

---

## Configuration Reference

```toml
# bengal.toml

[external_refs]
# Enable/disable external references (default: true)
enabled = true

# Export xref.json for other sites (default: false)
export_index = false

# Cache directory (default: .bengal/cache/external_refs)
cache_dir = ".bengal/cache/external_refs"

# Default cache duration in days (default: 7)
default_cache_days = 7

# URL templates for instant, offline resolution
[external_refs.templates]
python = "https://docs.python.org/3/library/{module}.html#{name}"
typing = "https://docs.python.org/3/library/typing.html#{name}"
requests = "https://requests.readthedocs.io/en/latest/api/#{name}"
httpx = "https://www.python-httpx.org/api/#{name_lower}"
fastapi = "https://fastapi.tiangolo.com/reference/{module}/#{name}"
pydantic = "https://docs.pydantic.dev/latest/api/{module}/#{name}"
sqlalchemy = "https://docs.sqlalchemy.org/en/20/core/{module}.html#{name}"
numpy = "https://numpy.org/doc/stable/reference/generated/numpy.{name}.html"
pandas = "https://pandas.pydata.org/docs/reference/api/pandas.{name}.html"

# Bengal ecosystem indexes
[[external_refs.indexes]]
name = "bengal"
url = "https://lbliii.github.io/bengal/docs/xref.json"
cache_days = 7

[[external_refs.indexes]]
name = "internal-docs"
url = "https://docs.internal.company.com/xref.json"
cache_days = 1
# Optional: authentication header
auth_header = "Authorization: Bearer ${DOCS_TOKEN}"
```

---

## Success Criteria

- [ ] `[[ext:python:pathlib.Path]]` resolves without network (URL template)
- [ ] Bengal sites can export xref.json on production builds
- [ ] Indexes cached locally with stale-while-revalidate
- [ ] Unresolved refs render as code + emit warning (never break build)
- [ ] Health check reports unresolved external refs
- [ ] Documentation complete with examples
- [ ] Works offline with cached indexes
- [ ] No collision with cross-version links (`[[v2:path]]` still works)

---

## Comparison: Bengal vs Intersphinx

| Aspect | Intersphinx | Bengal External Refs |
|--------|-------------|---------------------|
| **Offline support** | ❌ Requires network | ✅ URL templates work offline |
| **Build failures** | ❌ Fails if external down | ✅ Never fails, warns only |
| **Configuration** | Complex `intersphinx_mapping` | Simple TOML templates |
| **Index format** | Binary zlib-compressed | Human-readable JSON |
| **Cache control** | Limited | Full control (stale-while-revalidate) |
| **First build** | Slow (fetch all inventories) | Fast (templates instant) |
| **Ecosystem** | Sphinx-only | Bengal-native, extensible |
| **Learning curve** | Steep | Minimal |
| **Syntax** | `:py:class:\`path.Class\`` | `[[ext:python:path.Class]]` |

---

## Future Enhancements

1. **Fuzzy matching**: `[[ext:python:Path]]` → `pathlib.Path` (smart resolution)
2. **Autocomplete**: IDE integration for external ref targets
3. **Link checking**: Validate external URLs in health checks
4. **Analytics**: Track which external refs are most used
5. **Bidirectional**: "Who links to this?" for Bengal ecosystem

---

## References

- **Bengal Cross-References**: `bengal/rendering/plugins/cross_references.py`
- **Intersphinx Docs**: https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html
- **Intersphinx Issues**: https://community.lsst.org/t/how-docs-scipy-org-and-intersphinx-affect-your-doc-builds/1717
- **httpx (async HTTP)**: https://www.python-httpx.org/
