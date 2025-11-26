---
title: Reuse Content
description: Write once, publish everywhere using include and literalinclude directives
weight: 51
tags: [content-strategy, snippets, reuse, include]
---

# Content Reuse Strategies

Maintaining consistency across hundreds of pages is hard. If you copy-paste the same "Warning" or "Code Example" into 20 pages, updating it becomes a nightmare.

Bengal provides powerful directives to implement a "Write Once, Publish Everywhere" strategy directly in your Markdown content.

## Strategy 1: Include Markdown Files

Use the `{include}` directive to include entire markdown files or sections.

### Basic Usage

Create a reusable snippet file:

```markdown
<!-- content/snippets/warning.md -->
```{warning}
This feature is in beta. Please report any issues.
```
```

Include it in any page:

```markdown
# My Article

Here is some content.

```{include} snippets/warning.md
```

More content.
```

### Include Specific Lines

Include only a portion of a file:

```markdown
```{include} snippets/api-example.md
:start-line: 5
:end-line: 20
```
```

This includes lines 5-20 from the file.

### Path Resolution

Paths are resolved relative to:
1. **Current page's directory** - If you're in `content/docs/guides/`, `snippets/warning.md` looks in `content/docs/guides/snippets/`
2. **Site root** - Falls back to site root if not found relative to page

**Example:**
- Page: `content/docs/getting-started/installation.md`
- Include: `snippets/warning.md`
- Resolves to: `content/docs/getting-started/snippets/warning.md` (or `content/snippets/warning.md` if not found)

## Strategy 2: Include Code Files

Use the `{literalinclude}` directive to include code files as syntax-highlighted code blocks.

### Basic Usage

```markdown
```{literalinclude} examples/api.py
```
```

This automatically:
- Detects the language from the file extension (`.py` → Python)
- Applies syntax highlighting
- Includes the entire file

### Include Specific Lines

Include only a portion of a code file:

```markdown
```{literalinclude} examples/api.py
:start-line: 10
:end-line: 25
```
```

### Emphasize Lines

Highlight specific lines:

```markdown
```{literalinclude} examples/api.py
:emphasize-lines: 7,8,9
```
```

Or a range:

```markdown
```{literalinclude} examples/api.py
:emphasize-lines: 7-9
```
```

### Specify Language

Override auto-detection:

```markdown
```{literalinclude} examples/config.txt
:language: yaml
```
```

### Line Numbers

Show line numbers:

```markdown
```{literalinclude} examples/api.py
:linenos: true
```
```

### Complete Example

```markdown
```{literalinclude} examples/api.py
:language: python
:start-line: 10
:end-line: 30
:emphasize-lines: 15,16,17
:linenos: true
```
```

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

### Document Your Snippets

Add comments in snippet files explaining their purpose:

```markdown
<!--
Purpose: Beta feature warning
Used in: Installation guides, API docs
Last updated: 2025-01-15
-->

```{warning}
This feature is in beta.
```
```

## Common Patterns

### Reusable Warnings

**Create the snippet:**
```markdown
<!-- content/snippets/warnings/beta.md -->
```{warning}
This feature is in beta. Please report issues.
```
```

**Use in multiple pages:**
```markdown
# My Guide

Here's how to use the new feature.

```{include} snippets/warnings/beta.md
```

Continue with instructions...
```

### Code Examples

**Create the code file:**
```python
# content/snippets/code/api-example.py
def get_user(user_id: int) -> User:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()
```

**Include with emphasis:**
```markdown
Here's the API function:

```{literalinclude} snippets/code/api-example.py
:emphasize-lines: 2
:language: python
```

The docstring explains the function's purpose.
```

### Step-by-Step Instructions

**Create the steps file:**
```markdown
<!-- content/snippets/steps/installation.md -->
1. Download the installer from the website
2. Run the installer: `./installer.sh`
3. Verify installation: `bengal --version`
```

**Include in guides:**
```markdown
## Installation

Follow these steps to install Bengal:

```{include} snippets/steps/installation.md
```

After installation, continue to the next section.
```

## Complete Working Example

Here's a complete, copy-paste ready example of a documentation page using content reuse:

**File Structure:**
```
content/
├── snippets/
│   ├── warnings/
│   │   └── beta-notice.md
│   └── code/
│       └── example-api.py
└── docs/
    └── guides/
        └── api-tutorial.md
```

**1. Create the warning snippet:**
```markdown
<!-- content/snippets/warnings/beta-notice.md -->
```{warning}
This API is currently in beta. Breaking changes may occur in future versions.
```
```

**2. Create the code example:**
```python
# content/snippets/code/example-api.py
from bengal import Site

def create_site():
    """Create a new Bengal site."""
    site = Site(root_path="./my-site")
    site.build()
    return site

if __name__ == "__main__":
    site = create_site()
    print(f"Site built at {site.output_dir}")
```

**3. Create the tutorial page:**
```markdown
---
title: API Tutorial
description: Learn how to use Bengal's API
tags: [api, tutorial]
---

# API Tutorial

```{include} snippets/warnings/beta-notice.md
```

## Getting Started

Let's create a simple site using the API:

```{literalinclude} snippets/code/example-api.py
:language: python
:emphasize-lines: 3,4
:linenos: true
```

**Explanation:**
- Line 3: Creates a new `Site` instance
- Line 4: Builds the site

## Next Steps

Continue to the [advanced guide](/docs/guides/advanced/).
```

**Result:** The tutorial page includes the warning and code example, and both can be reused across multiple pages. Update once, use everywhere!

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

**3. Path Resolution Order**
1. **Current page's directory** - Relative paths resolve from the page's location
2. **Site root** - Falls back to site root if not found relative to page
3. **Security check** - Final validation ensures path is within site root

**Example of Blocked Paths:**
```markdown
# These will be rejected:
```{include} ../../../etc/passwd
```{include} /absolute/path/to/file.md
```{include} ../../../../outside/site.md
```
```

**Example of Allowed Paths:**
```markdown
# These are allowed:
```{include} snippets/warning.md          # Relative to current page
```{include} ../shared/common.md          # Relative, but within site root
```{include} content/snippets/warning.md  # From site root
```
```

### Security Best Practices

1. **Keep snippets in dedicated directories** - Organize reusable content in `content/snippets/` or similar
2. **Use relative paths** - Prefer relative paths for portability
3. **Validate included files** - Test snippets independently before including
4. **Review included content** - Be aware of what content is being included, especially from external sources

```{warning}
**Security Note:** While Bengal prevents path traversal, always review content from external sources before including it. Included markdown is processed and can execute directives, so ensure you trust the source.
```

## Troubleshooting

### File Not Found

**Error**: `Include error: File not found: snippets/warning.md`

**Solutions**:
- Check the path is correct relative to your page
- Verify the file exists in the expected location
- Try an absolute path from site root: `content/snippets/warning.md`
- Check for typos in the filename (case-sensitive on some systems)

**Diagnostic Steps:**
```bash
# Check if file exists
ls content/snippets/warning.md

# Check from your page's directory
cd content/docs/guides/
ls ../../snippets/warning.md

# Verify site root location
bengal site build --verbose  # Shows resolved paths
```

### Path Traversal Blocked

**Error**: `Include path traversal rejected` or `Include outside site root`

**Cause**: Attempted to include files outside the site root (security feature)

**Solutions**:
- Move the file into your site's content directory
- Use a relative path that stays within the site root
- Check that your site root is correctly configured in `bengal.toml`

**Example Fix:**
```markdown
# Before (blocked):
```{include} ../../outside/snippet.md

# After (allowed):
```{include} snippets/snippet.md  # File moved to content/snippets/
```
```

### Syntax Errors in Included Content

**Symptom**: Markdown syntax errors appear in the rendered page

**Cause**: Included markdown files have syntax errors

**Solutions**:
- Validate snippet files independently before including them
- Check for unclosed code blocks, lists, or directives
- Use a markdown linter to validate snippets

**Diagnostic:**
```bash
# Test rendering a snippet directly
bengal site build --verbose  # Shows parsing errors
```

### Circular Include Detection

**Symptom**: Build hangs or includes appear multiple times

**Cause**: File A includes File B, which includes File A (circular dependency)

**Solutions**:
- Break the circular dependency by extracting shared content
- Use a third file that both can include
- Restructure your content organization

**Example:**
```markdown
# Bad: circular dependency
# file-a.md includes file-b.md
# file-b.md includes file-a.md

# Good: shared content
# file-a.md includes shared.md
# file-b.md includes shared.md
```

### Include Depth Limits

**Question**: Is there a limit to how deeply I can nest includes?

**Answer**: Bengal supports nested includes, but for performance and maintainability:
- **Recommended**: Keep nesting to 2-3 levels deep
- **Maximum**: No hard limit, but deep nesting can slow builds
- **Best Practice**: Extract deeply nested content into separate pages

### Performance Considerations

**Large Includes:**
- Including very large files (>100KB) can slow builds
- Consider splitting large files into smaller, focused snippets
- Use line ranges (`:start-line:`, `:end-line:`) to include only needed portions

**Many Includes:**
- Pages with many includes (>20) may take longer to build
- Consider caching strategies or restructuring content
- Monitor build times with `bengal site build --verbose`

## Summary

| Directive | Best For | Example |
|-----------|----------|---------|
| `{include}` | Reusable markdown content (warnings, steps, explanations) | `{include} snippets/warning.md` |
| `{literalinclude}` | Code examples, configuration files, scripts | `{literalinclude} examples/api.py` |

Both directives support:
- ✅ Line ranges (`:start-line:`, `:end-line:`)
- ✅ Relative path resolution
- ✅ Security (prevents path traversal)
- ✅ Nested directives (included content can use other directives)

## Next Steps

- **[Writer Quickstart](/docs/getting-started/writer-quickstart/)** - Learn the basics of writing content
- **[Markdown Guide](/docs/about/concepts/templating/)** - Advanced markdown features
- **[Content Organization](/docs/about/concepts/content-organization/)** - Organize your content effectively
