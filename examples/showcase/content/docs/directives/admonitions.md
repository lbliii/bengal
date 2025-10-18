---
title: Admonitions
description: Callout boxes for notes, tips, warnings, and more
type: doc
weight: 2
tags: ["directives", "admonitions", "callouts"]
toc: true
---

# Admonitions

**Purpose**: Highlight important information with callout boxes.

## What You'll Learn

- Create admonition callouts
- Choose the right admonition type
- Nest markdown inside admonitions
- Use admonitions effectively

## Basic Syntax

Create admonitions with fenced code blocks:

````markdown
```{note} Note Title
This is important information readers should know.
```
````

**Result:**

```{note} Note Title
This is important information readers should know.
```

**Format:** ` ```{type} Title `

## Admonition Types

Bengal supports 9 admonition types:

### note

General important information:

````markdown
```{note} Important Note
This feature requires Bengal 0.2.0 or higher.
```
````

```{note} Important Note
This feature requires Bengal 0.2.0 or higher.
```

### tip

Helpful suggestions and best practices:

````markdown
```{tip} Pro Tip
Use `bengal site serve` for live reload during development.
```
````

```{tip} Pro Tip
Use `bengal site serve` for live reload during development.
```

### info

Additional context or background:

````markdown
```{info} Additional Information
Bengal uses Jinja2 for templating and Mistune for markdown parsing.
```
````

```{info} Additional Information
Bengal uses Jinja2 for templating and Mistune for markdown parsing.
```

### warning

Cautions that users should be aware of:

````markdown
```{warning} Be Careful
Deleting the output directory removes all generated files permanently.
```
````

```{warning} Be Careful
Deleting the output directory removes all generated files permanently.
```

### danger

Critical warnings about destructive or irreversible actions:

````markdown
```{danger} Data Loss Warning
Running `bengal site clean --all` deletes the output directory and build cache. This cannot be undone.
```
````

```{danger} Data Loss Warning
Running `bengal site clean --all` deletes the output directory and build cache. This cannot be undone.
```

### error

Error messages or common errors:

````markdown
```{error} Common Error
**Error:** Config file not found

**Solution:** Create a `bengal.toml` file in your project root.
```
````

```{error} Common Error
**Error:** Config file not found

**Solution:** Create a `bengal.toml` file in your project root.
```

### success

Positive outcomes or completion confirmations:

````markdown
```{success} Build Complete
✓ Site built successfully!  
✓ 150 pages generated in 0.8 seconds  
✓ Ready to deploy
```
````

```{success} Build Complete
✓ Site built successfully!  
✓ 150 pages generated in 0.8 seconds  
✓ Ready to deploy
```

### example

Code examples or usage demonstrations:

````markdown
```{example} Usage Example
To build your site:

\`\`\`bash
bengal site build --parallel
\`\`\`
```
````

```{example} Usage Example
To build your site:

\`\`\`bash
bengal site build --parallel
\`\`\`
```

### caution

Situations requiring careful attention:

````markdown
```{caution} Proceed with Caution
Modifying template files while the dev server is running may cause temporary rendering issues.
```
````

```{caution} Proceed with Caution
Modifying template files while the dev server is running may cause temporary rendering issues.
```

## When to Use Each Type

| Type | Use For | Example |
|------|---------|---------|
| **note** | Important information | Version requirements, prerequisites |
| **tip** | Helpful suggestions | Performance tips, shortcuts |
| **info** | Additional context | Background information, explanations |
| **warning** | Important cautions | Configuration warnings, breaking changes |
| **danger** | Critical warnings | Data loss, security issues |
| **error** | Error messages | Common errors and solutions |
| **success** | Positive outcomes | Completion messages, confirmations |
| **example** | Code examples | Usage demonstrations |
| **caution** | Careful attention | Potential issues, edge cases |

## Markdown Support

Admonitions support full markdown:

````markdown
```{tip} Formatting Support
You can use:

- **Bold** and *italic* text
- `Inline code`
- [Links](https://example.com)
- Lists (ordered and unordered)

\`\`\`python
# Even code blocks!
print("Hello")
\`\`\`
```
````

```{tip} Formatting Support
You can use:

- **Bold** and *italic* text
- `Inline code`
- [Links](https://example.com)
- Lists (ordered and unordered)

\`\`\`python
# Even code blocks!
print("Hello")
\`\`\`
```

## Common Patterns

### Prerequisites

````markdown
```{note} Prerequisites
Before starting, ensure you have:

- Python 3.8 or higher
- pip package manager
- Git installed
```
````

### Breaking Changes

````markdown
```{warning} Breaking Change in 2.0
The `oldFunction()` has been removed. Use `newFunction()` instead:

\`\`\`python
# Old (no longer works)
oldFunction(arg)

# New
newFunction(arg)
\`\`\`
```
````

### Installation Tips

````markdown
```{tip} Installation Shortcut
Skip the full installation with:

\`\`\`bash
pip install bengal && bengal new site mysite
\`\`\`
```
````

### Security Warnings

````markdown
```{danger} Security Warning
Never commit API keys or secrets to version control. Use environment variables instead.
```
````

### Troubleshooting

````markdown
```{error} Build Fails with "Config Not Found"
**Cause:** Missing `bengal.toml` configuration file.

**Solution:**

1. Create `bengal.toml` in your project root
2. Add minimal configuration:

   \`\`\`toml
   [site]
   title = "My Site"
   \`\`\`
3. Run `bengal site build` again
```
````

### Success Messages

````markdown
```{success} Deployment Successful
Your site is live at https://yoursite.com!

Next steps:
- Test all pages
- Verify links work
- Check analytics setup
```
````

## Title Options

### With Title (Recommended)

````markdown
```{note} Configuration Note
The title provides context.
```
````

### Without Title (Auto-generated)

````markdown
```{note}
Bengal auto-generates "Note" as the title.
```
````

**Result:** Title becomes "Note" (capitalized type name)

## Best Practices

### Use Sparingly

```{warning} Don't Overuse
Too many callouts reduce their impact. Aim for 1-3 admonitions per page.
```

**Good:** Highlight truly important information  
**Too much:** Every paragraph in a callout

### Choose Appropriate Type

```markdown
✅ Use {danger} for data loss warnings
✅ Use {tip} for helpful suggestions  
✅ Use {note} for important information
❌ Don't use {danger} for minor issues
❌ Don't use {success} for errors
```

### Keep Content Focused

**Good:**
````markdown
```{tip} Performance Tip
Enable parallel builds with `--parallel` for 2-4x faster performance.
```
````

**Too verbose:**
````markdown
```{tip} Tips and Tricks
Here are many tips including performance, organization, writing style, deployment strategies, and more...
(Should be split into multiple focused admonitions or regular content)
```
````

### Provide Action Items

Include what users should do:

````markdown
✅ Actionable:
```{warning} Version Mismatch
Your Bengal version (0.1.0) is outdated. Update with:
\`\`\`bash
pip install --upgrade bengal
\`\`\`
```

❌ Vague:
```{warning}
Your version might be old.
```
````

## Nesting Admonitions

You can nest admonitions inside other directives:

````markdown
```{tabs}
:id: install-tabs

### Tab: macOS

```{note} macOS Requirements
Requires macOS 10.15 or higher.
```

\`\`\`bash
brew install bengal
\`\`\`

### Tab: Linux

```{note} Linux Requirements
Requires Ubuntu 20.04 or equivalent.
```

\`\`\`bash
apt install bengal
\`\`\`
```
````

## Examples in Context

### Documentation Page

````markdown
# Installation Guide

```{note} Prerequisites
Ensure Python 3.8+ is installed before proceeding.
```

## Installation Steps

1. Install Bengal...
2. Create a new site...

```{tip} Quick Start
Use `bengal new site mysite` to create a site with example content.
```

## Troubleshooting

```{error} Common Issues
If you see "Command not found", ensure Bengal is in your PATH.
```
````

### Tutorial Page

````markdown
# Python Tutorial

```{info} What You'll Learn
This tutorial covers Python basics for beginners.
```

## Getting Started

```{warning} Python Version
This tutorial requires Python 3.8 or higher.
```

...tutorial content...

```{success} Congratulations!
You've completed the Python basics tutorial!
```
````

## Quick Reference

| Type | Icon | Color | Use Case |
|------|------|-------|----------|
| `{note}` | 📝 | Blue | Important info |
| `{tip}` | 💡 | Green | Helpful hints |
| `{info}` | ℹ️ | Blue | Context |
| `{warning}` | ⚠️ | Orange | Cautions |
| `{danger}` | 🚨 | Red | Critical warnings |
| `{error}` | ❌ | Red | Errors |
| `{success}` | ✅ | Green | Positive outcomes |
| `{example}` | 📋 | Purple | Examples |
| `{caution}` | ⚡ | Yellow | Careful attention |

## Next Steps

- **[Tabs](tabs.md)** - Tabbed content for alternatives
- **[Dropdown](dropdown.md)** - Collapsible sections
- **[Quick Reference](quick-reference.md)** - Syntax cheatsheet
- **[Kitchen Sink](../kitchen-sink.md)** - See all types in action

## Related

- [Directives Overview](index.md) - All directive types
- [Markdown Basics](../writing/markdown-basics.md) - Markdown syntax
- [Content Types](../content-types/) - Page layouts
