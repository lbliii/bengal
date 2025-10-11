---
title: Buttons
description: Create styled call-to-action buttons for downloads and important links
type: doc
weight: 7
tags: ["directives", "buttons", "cta"]
toc: true
---

# Buttons

**Purpose**: Create prominent call-to-action buttons for downloads, sign-ups, and important links.

## What You'll Learn

- Create styled buttons
- Use button types (primary, secondary)
- Link buttons to pages
- Best practices for CTAs

## Basic Syntax

Create buttons with the `{button}` directive:

````markdown
```{button} Button Text
:link: /destination/
:type: primary
```
````

**Components:**
- `Button Text` - Text displayed on button
- `:link:` - Destination URL
- `:type:` - Button style (primary or secondary)

## Button Types

### Primary Button

Main call-to-action:

````markdown
```{button} Get Started
:link: /docs/getting-started/
:type: primary
```
````

Use for:
- Main action on page
- Sign up / Download
- Get started
- Primary conversion goal

### Secondary Button

Supporting action:

````markdown
```{button} View Documentation
:link: /docs/
:type: secondary
```
````

Use for:
- Secondary actions
- Learn more links
- Alternative options
- Supporting CTAs

## Use Cases

### Download Links

````markdown
```{button} Download Bengal
:link: https://github.com/user/bengal/releases/latest
:type: primary
```
````

### Getting Started

````markdown
```{button} Quick Start Guide
:link: /docs/getting-started/
:type: primary
```

```{button} View Examples
:link: /examples/
:type: secondary
```
````

### External Links

````markdown
```{button} View on GitHub
:link: https://github.com/user/repo
:type: primary
```

```{button} Read the Blog
:link: https://blog.example.com
:type: secondary
```
````

## Button Options

### link (Required)

Destination URL:

````markdown
```{button} Click Me
:link: /page/           # Internal link
```

```{button} External
:link: https://example.com   # External link
```
````

### type

Button style:

````markdown
```{button} Primary Action
:link: /page/
:type: primary          # Prominent style
```

```{button} Secondary Action
:link: /page/
:type: secondary        # Subtle style
```
````

**Default:** `primary` if not specified

## Common Patterns

### Hero CTA

````markdown
# Welcome to Bengal

Fast, modern static site generator.

```{button} Get Started
:link: /docs/getting-started/
:type: primary
```

```{button} View Demo
:link: /demo/
:type: secondary
```
````

### Download Section

````markdown
## Download

Get the latest version of Bengal:

```{button} Download for macOS
:link: /downloads/bengal-macos.dmg
:type: primary
```

```{button} Download for Windows
:link: /downloads/bengal-windows.exe
:type: primary
```

```{button} Download for Linux
:link: /downloads/bengal-linux.tar.gz
:type: primary
```
````

### External Resources

````markdown
## Resources

```{button} GitHub Repository
:link: https://github.com/user/repo
:type: primary
```

```{button} Community Discord
:link: https://discord.gg/example
:type: secondary
```

```{button} Report Issues
:link: https://github.com/user/repo/issues
:type: secondary
```
````

### Tutorial Steps

````markdown
## Next Steps

You've completed the basics!

```{button} Continue to Advanced Topics
:link: /docs/advanced/
:type: primary
```

```{button} Back to Overview
:link: /docs/
:type: secondary
```
````

## Best Practices

### Use Sparingly

```{warning} Don't Overuse
Too many buttons reduce their effectiveness. Use 1-3 buttons per section.
```

**Good:** 1-2 buttons for main actions  
**Too many:** 5+ buttons competing for attention

### Clear Action Text

````markdown
✅ Good (action-oriented):
```{button} Download Now
```{button} Get Started
```{button} Sign Up Free

❌ Vague:
```{button} Click Here
```{button} Go
```{button} Link
````

### Prioritize Actions

````markdown
✅ Good (clear hierarchy):
```{button} Start Free Trial      # Primary
:type: primary
```

```{button} Learn More           # Secondary
:type: secondary
```

❌ Unclear (both primary):
```{button} Option A
:type: primary
```

```{button} Option B
:type: primary
```
````

### Combine with Cards

````markdown
```{cards}
:columns: 2

```{card} For Writers
:icon: ✍️

Create content easily with markdown.

```{button} Writing Guide
:link: /docs/writing/
:type: primary
```

```{card} For Developers
:icon: 💻

Build custom themes and features.

```{button} Developer Docs
:link: /docs/developers/
:type: primary
```
````

## Accessibility

Buttons are accessible by default:
- Keyboard navigable (Tab key)
- Clear focus states
- Semantic HTML
- Screen reader friendly

```{tip} Accessibility
Buttons use proper `<a>` tags with button styling for best accessibility.
```

## Quick Reference

**Primary button:**
````markdown
```{button} Text
:link: /page/
:type: primary
```
````

**Secondary button:**
````markdown
```{button} Text
:link: /page/
:type: secondary
```
````

## Next Steps

- **[Cards](cards.md)** - Combine cards with buttons
- **[Admonitions](admonitions.md)** - Highlight important info
- **[External Links](../writing/external-links.md)** - Link best practices
- **[Kitchen Sink](../kitchen-sink.md)** - See buttons in action

## Related

- [Directives Overview](index.md) - All directives
- [Quick Reference](quick-reference.md) - Syntax cheatsheet
- [Content Types](../content-types/) - Page layouts

