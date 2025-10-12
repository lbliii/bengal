---
title: Directives
description: Rich content features including callouts, tabs, cards, and more
type: doc
weight: 20
cascade:
  type: doc
tags: ["directives", "admonitions", "tabs", "cards"]
---

# Directives

Create rich, interactive content with Bengal's directive system. Directives are special markdown syntax for callouts, tabs, collapsible sections, and more.

## What Are Directives?

Directives are fenced code blocks with special names that render as rich UI components:

````markdown
```{note} Important Information
This is a **note** directive with markdown support!
```
````

**Result:**

```{note} Important Information
This is a **note** directive with markdown support!
```

## Quick Start

Choose the directive you need:

| Directive | Purpose | Example |
|-----------|---------|---------|
| **Admonitions** | Highlight important info | Note, tip, warning, danger |
| **Tabs** | Alternative content views | Multi-language code, platforms |
| **Dropdown** | Collapsible sections | FAQs, optional details |
| **Cards** | Visual content grids | Features, links, galleries |
| **Code Tabs** | Multi-language code | Show code in multiple languages |
| **Buttons** | Call-to-action links | Downloads, external links |

## Common Syntax Pattern

All directives follow this pattern:

````markdown
```{directive-name} Title
:option1: value1
:option2: value2

Content goes here with **markdown** support.
```
````

**Components:**
- ` ```{directive-name} ` - Directive type
- `Title` - Optional title (after directive name)
- `:options:` - Optional configuration
- `Content` - Markdown-formatted content

## Available Directives

### Callouts and Highlights

**[Admonitions](admonitions.md)** - Callout boxes for notes, tips, warnings

```{tip} Quick Example
Use admonitions to highlight important information!
```

**9 types:** note, tip, info, warning, danger, error, success, example, caution

### Organization

**[Tabs](tabs.md)** - Tabbed content for alternatives

Show different approaches, platforms, or languages side-by-side.

**[Dropdown](dropdown.md)** - Collapsible sections

Hide optional details, FAQs, or supplementary information.

### Visual

**[Cards](cards.md)** - Card grids for features and links

Present content in attractive card layouts.

**[Buttons](buttons.md)** - Styled call-to-action buttons

Create prominent links and downloads.

### Code

**[Code Tabs](code-tabs.md)** - Multi-language code examples

Show the same example in Python, JavaScript, etc.

## IDE Support

Get syntax highlighting for directives:

```{success} Bengal Syntax Highlighter
Install the [Bengal VS Code extension](https://github.com/yourusername/bengal-syntax-highlighter) for directive syntax highlighting!
```

Features:
- Color-coded directive types
- Tab marker highlighting
- Option syntax highlighting
- Works in VS Code and Cursor

## Quick Reference

See the **[Quick Reference](quick-reference.md)** for syntax cheatsheet of all directives.

## When to Use Directives

### Use Directives For

✅ **Highlighting important information**
```markdown
Use `{warning}` for critical information
```

✅ **Alternative content views**
```markdown
Use `{tabs}` for platform-specific instructions
```

✅ **Optional or supplementary content**
```markdown
Use `{dropdown}` for FAQs
```

✅ **Visual organization**
```markdown
Use `{cards}` for feature grids
```

### Use Plain Markdown For

❌ **Regular content**
Use paragraphs, not directives for body text

❌ **Simple emphasis**
Use bold or italic, not admonitions

❌ **Basic lists**
Use markdown lists, not cards for simple lists

## Common Patterns

### Documentation Warning

````markdown
```{warning} Breaking Change
Version 2.0 removes the deprecated `oldFunction()`. Use `newFunction()` instead.
```
````

### Multi-Platform Instructions

````markdown
```{tabs}
:id: install-tabs

### Tab: macOS

Install with Homebrew:
\`\`\`bash
brew install bengal
\`\`\`

### Tab: Linux

Install with apt:
\`\`\`bash
apt install bengal
\`\`\`

### Tab: Windows

Download from [releases page](https://github.com/bengal/releases).
```
````

### FAQ Section

````markdown
```{dropdown} How do I install Bengal?
:open: false

Follow the [installation guide](../writing/getting-started.md).
```

```{dropdown} How do I deploy my site?
:open: false

See the [deployment guide](../advanced/publishing.md).
```
````

### Feature Grid

````markdown
```{cards}
:columns: 3

```{card} Fast Builds
:icon: ⚡
Incremental builds rebuild only what changed.
```

```{card} Rich Content
:icon: 📝
Directives, shortcodes, and template functions.
```

```{card} SEO Ready
:icon: 🔍
Automatic sitemaps, RSS, and metadata.
```
````

## Nesting Directives

You can nest directives inside each other:

````markdown
```{tabs}
:id: nested-example

### Tab: Python

```{note} Python Note
Python requires version 3.8 or higher.
```

\`\`\`python
print("Hello, World!")
\`\`\`

### Tab: JavaScript

```{tip} JavaScript Tip
Use modern ES6+ syntax for better readability.
```

\`\`\`javascript
console.log("Hello, World!");
\`\`\`
```
````

```{warning} Escaping Fences
When nesting code blocks in directives, use more backticks for the outer fence: ```` for outer, ``` for inner.
```

## Best Practices

### Don't Overuse

```{warning} Use Sparingly
Too many callouts reduce their impact. Use directives for truly important information.
```

**Good:** 1-3 admonitions per page  
**Too much:** 10+ admonitions per page

### Choose the Right Type

```markdown
✅ Use {warning} for critical information
✅ Use {tip} for helpful suggestions
✅ Use {note} for important context
❌ Don't use {danger} for minor issues
```

### Keep Content Focused

**Good:**
````markdown
```{tip} Performance Tip
Enable parallel builds for 2-4x faster performance.
```
````

**Too verbose:**
````markdown
```{tip} Performance Tip
Here's a really long tip that goes on and on about performance and covers multiple topics and should probably be split into separate tips or just regular content...
```
````

## Testing Directives

Use the dev server to preview directives:

```bash
bengal serve
```

Changes appear immediately with live reload.

## All Directives

Browse complete documentation:

### Essential
- **[Admonitions](admonitions.md)** - Note, tip, warning, and more
- **[Quick Reference](quick-reference.md)** - Syntax cheatsheet

### Organization
- **[Tabs](tabs.md)** - Tabbed content views
- **[Dropdown](dropdown.md)** - Collapsible sections

### Visual
- **[Cards](cards.md)** - Card grids and layouts
- **[Buttons](buttons.md)** - Call-to-action buttons

### Code
- **[Code Tabs](code-tabs.md)** - Multi-language code blocks

## See It In Action

Check the **[Kitchen Sink](../kitchen-sink.md)** for live examples of every directive.

## Next Steps

- **[Admonitions](admonitions.md)** - Start with the most common directive
- **[Quick Reference](quick-reference.md)** - Get the syntax cheatsheet
- **[Tabs](tabs.md)** - Learn tabbed content
- **[Kitchen Sink](../kitchen-sink.md)** - See all directives in action

## Related

- [Markdown Basics](../writing/markdown-basics.md) - Essential markdown syntax
- [Extended Markdown](../writing/markdown-extended.md) - Tables, footnotes, and more
- [Content Types](../content-types/) - Different page layouts
