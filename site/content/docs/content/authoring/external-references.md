---
title: External References
description: Link to external documentation like Python stdlib, NumPy, and other Bengal sites
weight: 15
tags:
- linking
- cross-references
- intersphinx
- external
keywords:
- external links
- intersphinx
- cross-references
- python docs
- api links
---

# External References

Bengal's external references feature lets you create rich links to external documentation—Python stdlib, NumPy, other Bengal sites—using the familiar `[[link]]` syntax. Similar to Sphinx's intersphinx, but with an offline-first design and graceful fallback.

## Quick Reference

| Syntax | Resolution | Example |
|--------|------------|---------|
| `[[ext:project:target]]` | URL template or index | `[[ext:python:pathlib.Path]]` |
| `[[ext:project:target\|text]]` | With custom text | `[[ext:numpy:ndarray\|NumPy Arrays]]` |
| `{{ ext('project', 'target') }}` | Template function | `{{ ext('python', 'str.split') }}` |

## Syntax

External references use the `ext:` prefix followed by project and target:

```markdown
[[ext:project:target]]
[[ext:project:target|Custom Link Text]]
```

**Components:**

- `ext:` — Prefix indicating external reference
- `project` — Project name (configured in `external_refs.yaml`)
- `target` — Target identifier (class, function, module, page path)

## Examples

### Python Standard Library

```markdown
See [[ext:python:pathlib.Path]] for filesystem operations.

The [[ext:python:typing.TypedDict|TypedDict class]] enables typed dictionaries.

Check [[ext:python:json.dumps]] for JSON serialization.
```

### Third-Party Libraries

```markdown
Use [[ext:numpy:ndarray]] for efficient array operations.

The [[ext:requests:Session|requests Session]] handles connection pooling.

See [[ext:pydantic:BaseModel]] for data validation.
```

### Bengal Ecosystem

Link to other Bengal-powered documentation sites:

```markdown
Bengal uses [[ext:kida:Markup]] for safe HTML rendering.

Syntax highlighting is powered by [[ext:rosettes:PythonLexer]].
```

## Resolution Strategy

Bengal resolves external references using a **three-tier strategy**:

### Tier 1: URL Templates (Instant, Offline)

For well-known projects, Bengal uses URL templates that resolve instantly without network access:

```yaml
# external_refs.yaml
external_refs:
  templates:
    python: "https://docs.python.org/3/library/{module}.html#{name}"
    numpy: "https://numpy.org/doc/stable/reference/generated/numpy.{name}.html"
    requests: "https://requests.readthedocs.io/en/latest/api/#{name}"
```

**Template variables:**

| Variable | Description | Example |
|----------|-------------|---------|
| `{name}` | Full target name | `pathlib.Path` |
| `{name_lower}` | Lowercase target | `pathlib.path` |
| `{module}` | Module portion | `pathlib` |
| `{class}` | Class portion | `Path` |
| `{function}` | Function portion | `exists` |

### Tier 2: Bengal Indexes (Rich Metadata)

For Bengal ecosystem sites, fetch and cache `xref.json` indexes:

```yaml
# external_refs.yaml
external_refs:
  indexes:
    - name: "kida"
      url: "https://lbliii.github.io/kida/xref.json"
      cache_days: 7

    - name: "rosettes"
      url: "https://rosettes.dev/xref.json"
      cache_days: 7
```

Bengal indexes provide:

- Page titles for automatic link text
- Type information (class, function, module, page)
- Summaries for tooltips
- Accurate URLs

### Tier 3: Graceful Fallback

If resolution fails, Bengal renders the reference as inline code with a warning—builds never break:

```html
<code class="extref extref-unresolved">ext:unknown:Target</code>
```

A warning is logged during build:

```
warning: unresolved_external_ref ref=ext:unknown:Target
```

## Configuration

Configure external references in `config/_default/external_refs.yaml`:

```yaml
external_refs:
  # Enable/disable the feature
  enabled: true

  # Export xref.json for other sites to consume
  export_index: true

  # Cache directory for fetched indexes
  cache_dir: ".bengal/cache/external_refs"

  # Default cache duration
  default_cache_days: 7

  # URL templates (Tier 1) - instant, offline resolution
  templates:
    python: "https://docs.python.org/3/library/{module}.html#{name}"
    typing: "https://docs.python.org/3/library/typing.html#{name}"
    numpy: "https://numpy.org/doc/stable/reference/generated/numpy.{name}.html"
    pandas: "https://pandas.pydata.org/docs/reference/api/pandas.{name}.html"
    requests: "https://requests.readthedocs.io/en/latest/api/#{name}"
    httpx: "https://www.python-httpx.org/api/#{name_lower}"
    fastapi: "https://fastapi.tiangolo.com/reference/{module}/#{name}"
    pydantic: "https://docs.pydantic.dev/latest/api/{module}/#{name}"

  # Bengal ecosystem indexes (Tier 2) - rich metadata
  indexes:
    - name: "kida"
      url: "https://lbliii.github.io/kida/xref.json"
      cache_days: 7

    - name: "rosettes"
      url: "https://rosettes.dev/xref.json"
      cache_days: 7
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | `true` | Enable external references |
| `export_index` | bool | `false` | Generate `xref.json` for your site |
| `cache_dir` | string | `.bengal/cache/external_refs` | Where to cache fetched indexes |
| `default_cache_days` | int | `7` | How long to cache indexes |
| `templates` | dict | (built-in) | URL templates for common projects |
| `indexes` | list | `[]` | Bengal indexes to fetch |

## Template Functions

Use external references in templates with these functions:

### `ext(project, target, text=None)`

Generate an external reference link:

```kida
{{ ext('python', 'pathlib.Path') }}
{{ ext('python', 'pathlib.Path', 'Path class') }}
{{ ext('kida', 'Markup') }}
```

**Returns:** Safe HTML link

### `ext_exists(project, target)`

Check if an external reference is resolvable:

```kida
{% if ext_exists('kida', 'Markup') %}
  See {{ ext('kida', 'Markup') }} for safe HTML.
{% else %}
  See the Kida documentation for Markup.
{% end %}
```

**Returns:** `true` if resolvable, `false` otherwise

## Exporting Your Site's Index

Enable `export_index` to generate `xref.json` for your site:

```yaml
external_refs:
  export_index: true
```

Bengal generates `public/xref.json` containing:

```json
{
  "version": 1,
  "generator": "bengal",
  "generated_at": "2026-01-10T12:00:00Z",
  "base_url": "https://mysite.dev",
  "entries": [
    {
      "id": "MyClass",
      "type": "class",
      "path": "/docs/api/myclass/",
      "title": "MyClass",
      "summary": "A useful class for doing things."
    },
    {
      "id": "docs/getting-started",
      "type": "page",
      "path": "/docs/getting-started/",
      "title": "Getting Started",
      "summary": "Quick start guide for new users."
    }
  ]
}
```

Other Bengal sites can then link to your documentation:

```yaml
# On another site
external_refs:
  indexes:
    - name: "myproject"
      url: "https://mysite.dev/xref.json"
```

```markdown
See [[ext:myproject:MyClass]] for details.
```

## Use Cases

### API Documentation

Link to standard library and third-party APIs:

```markdown
## HTTP Client

The client uses [[ext:httpx:AsyncClient]] for async requests.
Results are validated with [[ext:pydantic:BaseModel]].

For synchronous code, use [[ext:requests:Session]] instead.
```

### Migration Guides

Reference external documentation when migrating:

```markdown
## Migrating from Requests to HTTPX

Replace [[ext:requests:Session]] with [[ext:httpx:Client]]:

**Before:**
```python
import requests
session = requests.Session()
```

**After:**
```python
import httpx
client = httpx.Client()
```
```

### Cross-Project Documentation

Link between your own projects:

```markdown
## Architecture

Bengal's rendering pipeline uses:

- [[ext:kida:Markup]] for HTML safety
- [[ext:rosettes:PythonLexer]] for syntax highlighting
- [[ext:patitas:MistuneFork]] for Markdown parsing
```

## Comparison with Intersphinx

| Feature | Bengal External Refs | Sphinx Intersphinx |
|---------|---------------------|-------------------|
| **Syntax** | `[[ext:project:target]]` | `:py:class:\`project.Target\`` |
| **Offline support** | ✅ URL templates | ❌ Requires inventory |
| **Build failure on missing** | ❌ Graceful fallback | ✅ Can fail |
| **Index format** | JSON (`xref.json`) | Binary (`objects.inv`) |
| **Configuration** | YAML | `conf.py` |

## Tips

### Use URL Templates for Stability

URL templates (Tier 1) are more reliable than fetched indexes:

- Work offline
- No network latency
- No cache staleness issues

Configure templates for frequently-referenced projects.

### Cache Indexes Appropriately

For actively-developed projects, use shorter cache times:

```yaml
indexes:
  - name: "myproject"
    url: "https://myproject.dev/xref.json"
    cache_days: 1  # Frequent updates
```

For stable projects, longer cache times reduce network calls:

```yaml
indexes:
  - name: "stable-lib"
    url: "https://stable-lib.dev/xref.json"
    cache_days: 30  # Stable API
```

### Don't Overuse

External references are powerful but can clutter content. Use them for:

- API class/function references
- Standard library documentation
- Cross-project links in ecosystem docs

For general external links, standard Markdown links are clearer:

```markdown
<!-- Good: API reference -->
See [[ext:python:pathlib.Path]] for path operations.

<!-- Better as regular link: general resource -->
See [Python's pathlib tutorial](https://docs.python.org/3/library/pathlib.html) for an introduction.
```

## Troubleshooting

### Unresolved References

If a reference shows as unresolved:

1. **Check project name** — Must match configured template or index name
2. **Check target format** — Use the format expected by that project
3. **Check cache** — Clear `.bengal/cache/external_refs/` and rebuild
4. **Check network** — Index fetching requires network access

### Template Not Matching

If URL templates produce wrong URLs:

1. **Check variable names** — Use `{name}`, `{module}`, `{class}`, `{function}`
2. **Check URL format** — Compare with actual documentation URLs
3. **Test manually** — Build and verify generated links

### Index Fetch Failures

If Bengal can't fetch an index:

1. **Check URL** — Ensure the `xref.json` URL is correct
2. **Check network** — Verify network access during build
3. **Check permissions** — Some indexes may require authentication

```yaml
indexes:
  - name: "private-project"
    url: "https://internal.example.com/xref.json"
    auth_header: "Bearer ${DOCS_TOKEN}"  # Environment variable
```

## See Also

- [[docs/content/authoring/linking|Linking Guide]] — All linking methods
- [[docs/content/versioning/cross-version-links|Cross-Version Links]] — Link between versions
- [[docs/reference/template-functions|Template Functions]] — `ext()` and `ext_exists()`
