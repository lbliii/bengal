---


title: Linking Guide
nav_title: Linking
description: Markdown links, cross-references, anchors, and target directives
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
aliases:
  - /docs/content/authoring/linking/
aliases:
  - /docs/build-sites/write/authoring/linking/
  - /docs/content/authoring/linking/
---

# Linking Guide

:::{note}
**Do I need this?** Yes when linking pages in Markdown content.
For Kida template functions and path resolution details, see
[[docs/build-sites/write/authoring/linking-reference|Linking Reference]].
:::

Bengal provides multiple ways to create links between pages, headings, and external resources. Choose the method that best fits your use case.

:::{tip}
**Try it out**: This guide includes a [[docs/build-sites/write/authoring/linking#test-target|test target anchor]] that demonstrates arbitrary reference targets. Scroll down to see it in action!
:::

## Quick Reference

| Method | Use Case | Syntax |
|--------|----------|--------|
| **Markdown Links** | Standard links, external URLs | `[text](url)` |
| **Cross-References** | Internal page links with auto-title | `[[path]]` |
| **External References** | Link to external docs (Python, NumPy, etc.) | `[[ext:project:target]]` |
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

:::{example-label} Target Directive Usage
:::

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

## See Also

- [[docs/build-sites/write/authoring/linking-reference|Linking Reference]] — template functions and path resolution
- [[docs/build-sites/write/authoring/external-references|External References]] — Python stdlib, NumPy, cross-site links
- [[docs/ship/validate|Content Validation]] — link validation with `bengal check`
