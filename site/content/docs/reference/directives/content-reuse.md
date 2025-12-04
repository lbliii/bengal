---
title: Content Reuse Directives
description: Reference for content reuse directives (include, literalinclude)
weight: 15
tags: [reference, directives, include, literalinclude, content-reuse]
keywords: [include, literalinclude, content-reuse, snippets, files]
---

# Content Reuse Directives

Content reuse directives allow you to include external files directly in your markdown content, enabling a "Write Once, Publish Everywhere" strategy.

**See also**: [Content Reuse](/docs/content/reuse/) for detailed strategies, best practices, and common patterns.

## Key Terms

:::{glossary}
:tags: content-reuse
:::

## Include

Include markdown files directly in your content.

**Syntax**:

````markdown
:::{include} path/to/file.md
:::
````

**With Options**:

````markdown
:::{include} path/to/file.md
:start-line: 5
:end-line: 20
:::
````

**Options**:

- `:start-line:` - Starting line number (1-indexed)
- `:end-line:` - Ending line number (1-indexed)

### Path Resolution

Paths are resolved relative to:

1. **Current page's directory** - If you're in `content/docs/content/`, `snippets/warning.md` looks in `content/docs/content/snippets/`
2. **Site root** - Falls back to site root if not found relative to page

**Example**:
- Page: `content/docs/getting-started/installation.md`
- Include: `snippets/warning.md`
- Resolves to: `content/docs/getting-started/snippets/warning.md` (or `content/snippets/warning.md` if not found)

### Examples

**Include Entire File**:

````markdown
:::{include} snippets/warning.md
:::
````

**Include Specific Lines**:

````markdown
:::{include} snippets/api-example.md
:start-line: 5
:end-line: 20
:::
````

**Nested Directives**: Included content can use other directives:

````markdown
<!-- snippets/warning.md -->
:::{warning}
This feature is in beta.
:::
````

## Literal Include

Include code files as syntax-highlighted code blocks.

**Syntax**:

````markdown
:::{literalinclude} path/to/file.py
:::
````

**With Options**:

````markdown
:::{literalinclude} path/to/file.py
:language: python
:start-line: 10
:end-line: 25
:emphasize-lines: 15,16,17
:linenos: true
:::
````

**Options**:

- `:language:` - Override auto-detected language
- `:start-line:` - Starting line number (1-indexed)
- `:end-line:` - Ending line number (1-indexed)
- `:emphasize-lines:` - Highlight specific lines: `7,8,9` or `7-9`
- `:linenos:` - Show line numbers: `true`, `false` (default: `false`)

### Language Detection

`literalinclude` auto-detects language from file extensions:

- **Python**: `.py`
- **JavaScript**: `.js`, `.ts`
- **Web**: `.html`, `.css`
- **Config**: `.yaml`, `.yml`, `.json`, `.toml`
- **Shell**: `.sh`, `.bash`, `.zsh`
- And many more

### Examples

**Basic Include**:

````markdown
:::{literalinclude} examples/api.py
:::
````

**With Line Range**:

````markdown
:::{literalinclude} examples/api.py
:start-line: 10
:end-line: 25
:::
````

**With Emphasized Lines**:

````markdown
:::{literalinclude} examples/api.py
:emphasize-lines: 7,8,9
:::
````

**With Line Numbers**:

````markdown
:::{literalinclude} examples/api.py
:linenos: true
:::
````

**Complete Example**:

````markdown
:::{literalinclude} examples/api.py
:language: python
:start-line: 10
:end-line: 30
:emphasize-lines: 15,16,17
:linenos: true
:::
````

### Path Resolution

Same as `{include}` - paths resolve relative to current page's directory, then site root.

## Security

Both directives prevent path traversal attacks:

- Only allows paths within the site root
- Rejects paths with `..` sequences
- Validates file existence before inclusion

## Best Practices

### Organize Snippets

Create a dedicated directory structure:

```
content/
├── snippets/
│   ├── warnings/
│   │   ├── beta-notice.md
│   │   └── deprecated-feature.md
│   ├── code-examples/
│   │   ├── api-client.py
│   │   └── config.yaml
│   └── common-content/
│       ├── installation-steps.md
│       └── troubleshooting.md
└── docs/
    └── guides/
        └── my-guide.md  # Uses snippets via {include}
```

### Keep Snippets Focused

Each snippet should have a single purpose:

✅ **Good**: `snippets/warnings/beta-notice.md` - One warning  
❌ **Bad**: `snippets/all-warnings.md` - Multiple warnings mixed together

### Use Relative Paths

Prefer relative paths for portability:

✅ **Good**: `snippets/warning.md`  
❌ **Bad**: `/absolute/path/to/warning.md`

### Document Snippets

Add comments explaining purpose:

````markdown
<!--
Purpose: Beta feature warning
Used in: Installation guides, API docs
Last updated: 2025-01-15
-->

:::{warning}
This feature is in beta.
:::
````

## Common Patterns

### Reusable Warnings

````markdown
<!-- snippets/warnings/beta.md -->
:::{warning}
This feature is in beta. Please report issues.
:::
````

Use in multiple pages:

````markdown
:::{include} snippets/warnings/beta.md
:::
````

### Code Examples

```markdown
<!-- snippets/code/api-example.py -->
def get_user(user_id: int) -> User:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()
```

Include with emphasis:

````markdown
:::{literalinclude} snippets/code/api-example.py
:emphasize-lines: 2
:::
````

## Troubleshooting

### File Not Found

**Error**: `Include error: File not found: snippets/warning.md`

**Solutions**:
- Check the path is correct relative to your page
- Verify the file exists
- Try an absolute path from site root: `content/snippets/warning.md`

### Path Traversal Blocked

**Error**: `Include path traversal rejected`

**Cause**: Attempted to include files outside the site root (security feature)

**Solution**: Keep all snippets within your site's content directory

### Syntax Errors in Included Content

If included markdown has syntax errors, they'll appear in the rendered page.

**Solution**: Validate snippet files independently before including them

## Related

- [Content Reuse](/docs/content/reuse/) - Detailed strategies and best practices
- [Formatting Directives](/docs/reference/directives/formatting/) - Other formatting options
