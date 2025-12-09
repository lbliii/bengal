---
title: Content Snippets
description: Reusable content fragments with include directives
weight: 10
draft: false
lang: en
tags:
- snippets
- reuse
- include
keywords:
- snippets
- include
- reuse
- dry
category: guide
---

# Content Snippets

Maintaining consistency across hundreds of pages is hard. If you copy-paste the same "Warning" or "Code Example" into 20 pages, updating it becomes a nightmare.

Bengal provides powerful directives to implement a "Write Once, Publish Everywhere" strategy directly in your Markdown content.

## Strategy 1: Include Markdown Files

Use the `{include}` directive to include entire markdown files or sections.

### Basic Usage

Create a reusable snippet file:

```markdown
<!-- content/snippets/warning.md -->
:::{warning}
This feature is in beta. Please report any issues.
:::
```

Include it in any page:

````markdown
# My Article

Here is some content.

```{include} snippets/warning.md
```

More content.
````

### Include Specific Lines

Include only a portion of a file:

````markdown
```{include} snippets/api-example.md
:start-line: 5
:end-line: 20
```
````

This includes lines 5-20 from the file.

### Path Resolution

Paths are resolved relative to:
1. **Current page's directory** - If you're in `content/docs/content/`, `snippets/warning.md` looks in `content/docs/content/snippets/`
2. **Site root** - Falls back to site root if not found relative to page

## Strategy 2: Include Code Files

Use the `{literalinclude}` directive to include code files as syntax-highlighted code blocks.

### Basic Usage

````markdown
```{literalinclude} examples/api.py
```
````

This automatically:
- Detects the language from the file extension (`.py` → Python)
- Applies syntax highlighting
- Includes the entire file

### Include Specific Lines

Include only a portion of a code file:

````markdown
```{literalinclude} examples/api.py
:start-line: 10
:end-line: 25
```
````

### Emphasize Lines

Highlight specific lines:

````markdown
```{literalinclude} examples/api.py
:emphasize-lines: 7,8,9
```
````

Or a range:

````markdown
```{literalinclude} examples/api.py
:emphasize-lines: 7-9
```
````

### Complete Example

````markdown
```{literalinclude} examples/api.py
:language: python
:start-line: 10
:end-line: 30
:emphasize-lines: 15,16,17
:linenos: true
```
````

## Supported Languages

`literalinclude` auto-detects language from file extensions:

- **Python**: `.py`
- **JavaScript**: `.js`, `.ts`
- **Web**: `.html`, `.css`
- **Config**: `.yaml`, `.yml`, `.json`, `.toml`
- **Shell**: `.sh`, `.bash`, `.zsh`
- **And many more** - See the directive documentation for full list

## Best Practices

### Organize Snippets

Create a dedicated directory for reusable content:

```
content/
├── _snippets/
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

✅ **Good**: `_snippets/warnings/beta-notice.md` - One warning  
❌ **Bad**: `_snippets/all-warnings.md` - Multiple warnings mixed together

### Use Relative Paths

Prefer relative paths for portability:

✅ **Good**: `_snippets/warning.md`  
❌ **Bad**: `/absolute/path/to/warning.md`

## Security Model

Bengal includes built-in security protections to prevent path traversal attacks and unauthorized file access.

### Security Features

**1. Path Traversal Prevention**
- All include paths are validated to ensure they stay within the site root
- Attempts to use `../` to access files outside the site root are blocked
- Absolute paths (starting with `/`) are rejected

**2. Site Root Enforcement**
- Files must be within the site's content directory or site root
- Resolved paths are checked against the site root boundary
- Invalid paths log warnings and fail gracefully

## Troubleshooting

### File Not Found

**Error**: `Include error: File not found: snippets/warning.md`

**Solutions**:
- Check the path is correct relative to your page
- Verify the file exists in the expected location
- Try an absolute path from site root: `content/_snippets/warning.md`
- Check for typos in the filename (case-sensitive on some systems)

### Path Traversal Blocked

**Error**: `Include path traversal rejected` or `Include outside site root`

**Cause**: Attempted to include files outside the site root (security feature)

**Solutions**:
- Move the file into your site's content directory
- Use a relative path that stays within the site root
- Check that your site root is correctly configured in `bengal.toml`

## Summary

| Directive | Best For | Example |
|-----------|----------|---------|
| `{include}` | Reusable markdown content (warnings, steps, explanations) | `{include} _snippets/warning.md` |
| `{literalinclude}` | Code examples, configuration files, scripts | `{literalinclude} examples/api.py` |

Both directives support:
- ✅ Line ranges (`:start-line:`, `:end-line:`)
- ✅ Relative path resolution
- ✅ Security (prevents path traversal)
- ✅ Nested directives (included content can use other directives)

## See Also

- [Content Reuse Overview](/docs/content/reuse/) — DRY content strategies
- [Filtering](/docs/content/reuse/filtering/) — Advanced content queries
