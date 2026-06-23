---


title: Linking Reference
nav_title: Linking Reference
description: Template link functions, path resolution, and linking best practices
weight: 11
category: guide
tags:
- persona-themer
- reference
keywords:
- ref()
- doc()
- anchor()
aliases:
  - /docs/content/authoring/linking-reference/
aliases:
  - /docs/build-sites/write/authoring/linking-reference/
  - /docs/content/authoring/linking-reference/
---

# Linking Reference

Template functions, path resolution rules, and advanced linking patterns.

:::{note}
**Do I need this?** Use when generating links in Kida templates or debugging
path resolution. For Markdown authoring syntax, see
[[docs/build-sites/write/authoring/linking|Linking Guide]].
:::

## Template Functions

Use template functions in [[ext:kida:|Kida]] templates for dynamic link generation.

### `ref(path, text=None)`

Generate a cross-reference link:

```kida
{{ ref('docs/getting-started') }}
{{ ref('docs/getting-started', 'Get Started') }}
{{ ref('id:install-guide') }}
```

**Returns**: Safe HTML link (`<a href="...">...</a>`)

**Use cases**:
- Dynamic navigation menus
- Related pages sections
- Breadcrumbs

### `doc(path)`

Get a page object for custom link generation:

```kida
{% let page = doc('docs/getting-started') %}
{% if page %}
  <a href="{{ page.href }}">{{ page.title }}</a>
  <p>{{ page.description }}</p>
{% end %}
```

**Returns**: `Page` object or `None`

**Use cases**:
- Custom link formatting
- Accessing page metadata
- Conditional rendering

### `anchor(heading, page_path=None)`

Link to a heading:

```kida
{{ anchor('Installation') }}
{{ anchor('Configuration', 'docs/getting-started') }}
```

**Parameters**:
- `heading`: Heading text to find (case-insensitive)
- `page_path`: Optional page path to restrict search

**Returns**: Safe HTML link with anchor fragment

**Use cases**:
- Table of contents
- "Jump to" links
- Cross-page heading references

### `relref(path)`

Get relative URL without generating a link:

```kida
<a href="{{ relref('docs/api') }}" class="btn">API Docs</a>

{% let api_url = relref('docs/api') %}
{% if api_url %}
  <link rel="preload" href="{{ api_url }}" as="document">
{% end %}
```

**Returns**: URL string or empty string if not found

**Use cases**:
- Custom link HTML
- Meta tags
- Preload/prefetch links

## Path Resolution

Understanding how Bengal resolves paths helps you write reliable links.

### Path Formats

Bengal accepts multiple path formats:

```markdown
[[docs/getting-started]]        # Recommended: path without extension
[[docs/getting-started.md]]     # Also works: path with extension
[[getting-started]]             # Slug (if unique across site)
[[id:install-guide]]            # Custom ID
```

### Resolution Order

When resolving a cross-reference:

1. **Custom ID** (`id:xxx`) — Checked first, fastest lookup
2. **Path lookup** (`docs/page`) — Most explicit, recommended
3. **Slug lookup** (`page-name`) — Fallback, may be ambiguous

### Relative Path Resolution

Relative paths resolve from the current page's directory:

```markdown
<!-- File: docs/getting-started/installation.md -->

[[./quickstart]]              # docs/getting-started/quickstart.md
[[../reference/config]]       # docs/reference/config.md
[[../../_index]]              # _index.md (site root)
```

**Rules**:
- `.md` extension is optional
- `./` refers to current directory
- `../` goes up one level
- Paths are normalized (trailing slashes, etc.)

## Best Practices

### When to Use Each Method

**Use Markdown Links** (`[text](url)`) when:
- Linking to external URLs
- You need full control over link text
- Simple relative paths within a section

**Use Cross-References** (`[[path]]`) when:
- Linking to internal pages
- You want automatic title resolution
- You want stable links that survive path changes (with IDs)
- You're writing documentation

**Use Template Functions** (`ref()`, `doc()`, etc.) when:
- Generating links dynamically in templates
- Building navigation menus
- Creating related pages sections
- Conditional link rendering

**Use Anchor Links** (`#heading`) when:
- Linking to specific sections
- Creating table of contents
- Cross-referencing specific content

**Use Target Directives** (`:::{target}`) when:
- Creating anchors not tied to headings
- Need stable anchors that survive content restructuring
- Migrating from RST/Sphinx (`.. _label:`)
- Anchoring before notes/warnings for direct linking

**Reference with `[[!target-id]]`**:
- Explicit syntax avoids collisions with heading anchors
- Makes intent clear (target directive vs heading)
- Required for target directive references

### Link Stability

**Most Stable** (survives path changes):
- Custom IDs: `[[id:my-page]]`
- Template functions with IDs: `{{ ref('id:my-page') }}`

**Moderately Stable** (survives minor changes):
- Path-based cross-references: `[[docs/page]]`
- Absolute markdown links: `[text](/docs/page/)`

**Least Stable** (breaks on path changes):
- Relative markdown links: `[text](../page.md)`
- Slug-based references (if slugs change)

### Performance

All linking methods use O(1) lookups from pre-built indexes:
- Cross-references: Built during discovery phase
- Template functions: Use same index
- Markdown links: Resolved during rendering

**No performance difference** between methods — choose based on use case.

## Examples

### Navigation Menu

```kida
<nav>
  {% for item in site.menus.main %}
    <a href="{{ item.url }}">{{ item.name }}</a>
  {% end %}
</nav>
```

### Related Pages Section

```markdown
## Related Pages

- [[docs/tutorials/getting-started|Getting Started]]
- [[docs/reference/api|API Reference]]
- [[docs/tutorials/examples|Examples]]
```

### Dynamic Related Pages

```kida
{% let related = site.pages | where('tags', page.tags, 'in') | limit(5) %}
{% if related %}
  <h2>Related Pages</h2>
  <ul>
    {% for page in related %}
      <li>{{ ref(page.path) }}</li>
    {% end %}
  </ul>
{% end %}
```

### Table of Contents

```markdown
## Table of Contents

- [[#introduction|Introduction]]
- [[#installation|Installation]]
- [[#configuration|Configuration]]
- [[#usage|Usage]]
```

### Cross-Reference in Content

```markdown
For detailed setup instructions, see [[docs/getting-started/installation|the installation guide]].

Once installed, configure your site as described in [[docs/reference/config#site-settings|Site Settings]].
```

## Troubleshooting

### Broken Links

If a link doesn't resolve:

1. **Check path spelling** — Paths are case-sensitive
2. **Verify page exists** — Use `bengal check` to check
3. **Check path format** — Use path without `.md` extension
4. **Try absolute path** — Use `/docs/page` instead of relative

### Link Validation

Bengal validates links during build:

```bash
bengal check
```

This checks:
- Cross-references resolve
- Markdown links point to existing pages
- Anchor links target valid headings

### Debugging Broken References

Broken cross-references show visual indicators:

```html
<span class="broken-ref" data-ref="nonexistent-page"
      title="Page not found: nonexistent-page">
  [nonexistent-page]
</span>
```

Use browser dev tools to inspect broken references and see what path was attempted.

## See Also

- [[docs/build-sites/write/authoring/linking|Linking Guide]] — Markdown and cross-reference syntax
- [[docs/build-sites/write/authoring/external-references|External References]] — Link to Python stdlib, NumPy, other Bengal sites
- [[docs/reference/template-functions|Template Functions]] — All template helpers
- [[docs/ship/validate|Content Validation]] — Link validation and health checks
- [[docs/build-sites/structure/analysis/graph|Graph Analysis]] — Analyze site connectivity
