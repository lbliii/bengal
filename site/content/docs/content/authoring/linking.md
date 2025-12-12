---
title: Linking Guide
nav_title: Linking
description: Complete guide to creating links between pages, headings, and external resources
weight: 10
category: guide
tags:
- linking
- cross-references
- markdown
- templates
keywords:
- links
- cross-references
- anchors
- templates
- markdown links
---

# Linking Guide

Bengal provides multiple ways to create links between pages, headings, and external resources. Choose the method that best fits your use case.

:::{tip}
**Try it out**: This guide includes a [[!test-target|test target anchor]] that demonstrates arbitrary reference targets. Scroll down to see it in action!
:::

## Quick Reference

| Method | Use Case | Syntax |
|--------|----------|--------|
| **Markdown Links** | Standard links, external URLs | `[text](url)` |
| **Cross-References** | Internal page links with auto-title | `[[path]]` |
| **Template Functions** | Dynamic links in templates | `{{ ref('path') }}` |
| **Anchor Links** | Link to headings | `[[#heading]]` or `#heading` |
| **Target Directives** | Arbitrary anchors mid-page | `:::{target} id` |
| **Target References** | Link to target directives | `[[!target-id]]` |

## Standard Markdown Links

Use standard Markdown link syntax for external URLs and simple internal links.

### External Links

```markdown
[Visit GitHub](https://github.com)
[Email us](mailto:hello@example.com)
```

### Internal Links

**Absolute paths** (from site root):

```markdown
[Get Started](/docs/get-started/)
[API Reference](/docs/reference/api/)
```

**Relative paths** (from current page):

```markdown
<!-- From docs/get-started/installation.md -->
[Quickstart](./quickstart.md)
[Configuration](../reference/config.md)
[Home](../../_index.md)
```

**Path Resolution Rules**:

- `.md` extension is optional — Bengal resolves both `page.md` and `page`
- Relative paths resolve from the current page's directory
- `./` refers to current directory, `../` goes up one level
- Paths are normalized automatically (trailing slashes, etc.)

### Link with Title

```markdown
[Link text](https://example.com "Optional title")
```

## Cross-References (`[[link]]` Syntax)

Cross-references provide intelligent linking with automatic title resolution and O(1) lookup performance. Use them for internal page links.

### Basic Cross-Reference

```markdown
[[docs/getting-started]]
```

This automatically:
- Resolves to the page at `docs/getting-started.md`
- Uses the page's title as link text
- Handles path normalization automatically

### Custom Link Text

```markdown
[[docs/getting-started|Get Started Guide]]
```

The `|` separator lets you specify custom link text while still using intelligent path resolution.

### Link by Custom ID

If a page has a custom `id` in frontmatter:

```yaml
---
id: install-guide
title: Installation Guide
---
```

Link to it by ID:

```markdown
[[id:install-guide]]
[[id:install-guide|Installation]]
```

**Benefits of ID-based links**:
- Stable even if page path changes
- Shorter syntax
- Works across site restructures

### Link to Headings

Link to any heading in your site:

```markdown
[[#installation]]
[[#configuration]]
```

This finds the heading text (case-insensitive) and links to it. If multiple pages have the same heading, it uses the first match.

**Link to heading in specific page**:

```markdown
[[docs/getting-started#installation]]
```

### Path Resolution

Cross-references support multiple path formats:

```markdown
[[docs/getting-started]]        # Path without extension
[[docs/getting-started.md]]     # Path with extension (also works)
[[getting-started]]             # Slug (if unique)
[[id:install-guide]]            # Custom ID
```

**Resolution order**:
1. Custom ID (`id:xxx`)
2. Path lookup (`docs/page`)
3. Slug lookup (`page-name`)

### Broken References

If a cross-reference can't be resolved, Bengal shows a broken reference indicator:

```markdown
[[nonexistent-page]]
```

Renders as: `[nonexistent-page]` with a visual indicator for debugging.

## Anchor Links

Link to headings within the same page or across pages.

### Same-Page Anchors

```markdown
[Installation](#installation)
[Configuration](#configuration)
```

Headings automatically get anchor IDs based on their text. For example:

```markdown
## Installation

This heading gets ID: `installation`
```

### Custom Anchor IDs

Use `{#custom-id}` syntax for custom anchor IDs on headings:

```markdown
## Installation {#install-guide}

Link to it: [[#install-guide]]
```

### Arbitrary Reference Targets

Create anchor targets anywhere in content (not just on headings) using the `{target}` directive. This is similar to RST's `.. _label:` syntax.

**Syntax**:

```markdown
:::{target} my-anchor-id
:::
```

**Example**:

```markdown
:::{target} important-caveat
:::

:::{warning}
This caveat is critical for production use.
:::

See [[!important-caveat|the caveat]] for details.
```

**Reference Syntax**:

Use `[[!target-id]]` to explicitly reference target directives:

```markdown
[[!test-target]]              # Link with auto-generated text
[[!test-target|Custom Text]]   # Link with custom text
```

**Why `!` instead of `#`?**

The `!` prefix distinguishes target directive references from heading anchor references:
- `[[#heading]]` - References heading anchors (auto-generated or custom `{#id}`)
- `[[!target-id]]` - References target directives (explicit `:::{target}`)

This eliminates collisions and makes your intent explicit.

**Use cases**:
- Anchor before a note/warning that users should link to
- Stable anchor that survives heading text changes
- Anchor in middle of content (not tied to heading)
- Migration from Sphinx (`.. _label:`) or RST reference targets

**Anchor ID requirements**:
- Must start with a letter (a-z, A-Z)
- May contain letters, numbers, hyphens, underscores
- Case-sensitive in output, case-insensitive for resolution

**Note**: The target renders as an invisible anchor element. Any content inside the directive is ignored (targets are point anchors, not containers).

**Try it**: This page has a test target below. Jump to it: [[!test-target|Test Target]]

:::{target} test-target
:::

This is a test target anchor. You can link to it using `[[!test-target]]` from anywhere in your site.

### Cross-Page Anchors

```markdown
[Installation](/docs/getting-started/#installation)
[[docs/getting-started#installation]]
```

Both syntaxes work. Cross-references are preferred for internal links.

## Template Functions

Use template functions in Jinja2 templates for dynamic link generation.

### `ref(path, text=None)`

Generate a cross-reference link:

```jinja2
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

```jinja2
{% set page = doc('docs/getting-started') %}
{% if page %}
  <a href="{{ page.url }}">{{ page.title }}</a>
  <p>{{ page.description }}</p>
{% endif %}
```

**Returns**: `Page` object or `None`

**Use cases**:
- Custom link formatting
- Accessing page metadata
- Conditional rendering

### `anchor(heading, page_path=None)`

Link to a heading:

```jinja2
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

```jinja2
<a href="{{ relref('docs/api') }}" class="btn">API Docs</a>

{% set api_url = relref('docs/api') %}
{% if api_url %}
  <link rel="preload" href="{{ api_url }}" as="document">
{% endif %}
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

```jinja2
<nav>
  {% for item in site.menus.main %}
    <a href="{{ item.url }}">{{ item.name }}</a>
  {% endfor %}
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

```jinja2
{% set related = site.pages | where('tags', page.tags, 'in') | limit(5) %}
{% if related %}
  <h2>Related Pages</h2>
  <ul>
    {% for page in related %}
      <li>{{ ref(page.path) }}</li>
    {% endfor %}
  </ul>
{% endif %}
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
2. **Verify page exists** — Use `bengal validate` to check
3. **Check path format** — Use path without `.md` extension
4. **Try absolute path** — Use `/docs/page` instead of relative

### Link Validation

Bengal validates links during build:

```bash
bengal validate
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

- [[docs/content/authoring|Content Authoring]] — Markdown and MyST syntax
- [[docs/reference/template-functions|Template Functions]] — All template helpers
- [[docs/content/validation|Content Validation]] — Link validation and health checks
- [[docs/content/analysis/graph|Graph Analysis]] — Analyze site connectivity
