---
title: Dropdown
description: Create collapsible sections for optional content and FAQs
type: doc
weight: 4
tags: ["directives", "dropdown", "collapsible"]
toc: true
---

# Dropdown

**Purpose**: Create collapsible sections to hide optional content until needed.

## What You'll Learn

- Create collapsible content sections
- Build FAQ sections
- Control initial open/closed state
- Nest markdown in dropdowns

## Basic Syntax

Create dropdowns with the `{dropdown}` directive:

````markdown
```{dropdown} Click to Expand
Content hidden until the user clicks.
```
````

**Result:** A collapsible section with "Click to Expand" as the header.

**Format:** ` ```{dropdown} Title `

## Simple Example

````markdown
```{dropdown} Additional Information
This content is hidden by default. Users can expand it if they want more details.

Supports **full markdown** including:
- Lists
- Links
- Code blocks
```
````

## Use Cases

### FAQ Sections

Perfect for frequently asked questions:

````markdown
## Frequently Asked Questions

```{dropdown} How do I install Bengal?
Follow these steps:

1. Install Python 3.8+
2. Run: `pip install bengal`
3. Verify: `bengal --version`

See the [installation guide](../writing/getting-started.md) for details.
```

```{dropdown} How do I deploy my site?
Bengal generates static HTML in the `public/` directory.

Deploy options:
- **Netlify**: Drag-and-drop `public/` folder
- **GitHub Pages**: Push to gh-pages branch
- **Any web server**: Upload `public/` contents

See [deployment guide](../advanced/publishing.md).
```

```{dropdown} What themes are available?
Bengal includes a default theme. Custom themes coming soon!
```
````

### Optional Details

Hide supplementary information:

````markdown
## Installation

Install Bengal with pip:

\`\`\`bash
pip install bengal
\`\`\`

```{dropdown} Advanced Installation Options
:open: false

### From Source

Clone and install:
\`\`\`bash
git clone https://github.com/user/bengal
cd bengal
pip install -e .
\`\`\`

### With Optional Dependencies

\`\`\`bash
pip install bengal[dev,docs]
\`\`\`
```
````

### Detailed Explanations

Keep pages scannable:

````markdown
## Features

Bengal offers fast builds, rich content, and SEO optimization.

```{dropdown} How Fast Are Builds?
:open: false

Bengal uses:
- Incremental builds (18-42x faster)
- Parallel processing (2-4x speedup)
- Smart caching

Typical performance:
- 10 pages: 0.012s (incremental)
- 100 pages: 0.047s (incremental)
- 1000 pages: ~0.5s (incremental)
```
````

### Technical Details

Hide complex information:

````markdown
## Configuration

Basic configuration in `bengal.toml`:

\`\`\`toml
[site]
title = "My Site"
\`\`\`

```{dropdown} Advanced Configuration Options
:open: false

### Build Options

\`\`\`toml
[build]
parallel = true
incremental = true
strict = false
\`\`\`

### Asset Processing

\`\`\`toml
[assets]
minify = true
fingerprint = true
\`\`\`

See [full configuration reference](../advanced/configuration.md).
```
````

## Dropdown Options

### open

Control initial state (open or closed):

````markdown
```{dropdown} Open by Default
:open: true

This dropdown starts expanded.
```

```{dropdown} Closed by Default
:open: false

This dropdown starts collapsed (default).
```
````

**Default:** `false` (closed)

**Use `:open: true` for:**
- Most important FAQ
- Critical information
- Primary option

### class

Add custom CSS classes:

````markdown
```{dropdown} Custom Styled
:class: my-custom-class

Content with custom styling.
```
````

## Markdown Support

Dropdowns support full markdown:

````markdown
```{dropdown} Full Markdown Support
:open: false

## Headings Work

Regular paragraphs with **bold** and *italic*.

### Lists

- Unordered lists
- With multiple items

### Code Blocks

\`\`\`python
def example():
    return "Syntax highlighting works!"
\`\`\`

### Links and Images

Visit [Bengal](https://bengal-ssg.org)

![Image](/assets/image.png)
```
````

## Nesting Directives

### Admonitions in Dropdowns

````markdown
```{dropdown} Installation Notes
:open: false

```{warning} Requirements
Python 3.8+ required. Check with `python --version`.
```

Install command:
\`\`\`bash
pip install bengal
\`\`\`

```{tip} Virtual Environment
Use a virtual environment to avoid conflicts:
\`\`\`bash
python -m venv venv
source venv/bin/activate
pip install bengal
\`\`\`
```
````

### Dropdowns in Tabs

````markdown
```{tabs}
:id: platform-install

### Tab: macOS

\`\`\`bash
brew install bengal
\`\`\`

```{dropdown} Troubleshooting macOS
:open: false

If Homebrew fails:
1. Update Homebrew: `brew update`
2. Try again
```

### Tab: Linux

\`\`\`bash
apt install bengal
\`\`\`

```{dropdown} Troubleshooting Linux
:open: false

If apt fails:
1. Update: `sudo apt update`
2. Try again
```
```
````

## Common Patterns

### FAQ Section

````markdown
# Frequently Asked Questions

```{dropdown} Q: What is Bengal?
Bengal is a fast static site generator built in Python.
```

```{dropdown} Q: Is it free?
Yes! Bengal is open source and free to use.
```

```{dropdown} Q: How do I get help?
- Check the [documentation](../writing/)
- Open an [issue on GitHub](https://github.com/user/repo/issues)
- Join our [Discord community](https://discord.gg/example)
```
````

### Troubleshooting Guide

````markdown
## Troubleshooting

```{dropdown} Build fails with "Config not found"
:open: false

**Cause:** Missing `bengal.toml` file.

**Solution:**
1. Create `bengal.toml` in project root
2. Add minimal config:
   \`\`\`toml
   [site]
   title = "My Site"
   \`\`\`
3. Run `bengal build` again
```

```{dropdown} Pages not updating
:open: false

**Cause:** Cached content or dev server issue.

**Solution:**
1. Stop the dev server (Ctrl+C)
2. Clear cache: `bengal clean`
3. Rebuild: `bengal build`
4. Restart server: `bengal serve`
```
````

### Technical Documentation

````markdown
## API Reference

### authenticate(username, password)

Authenticates a user.

**Parameters:**
- `username` (str): User's username
- `password` (str): User's password

**Returns:** `bool` - True if authenticated

```{dropdown} Example Usage
:open: false

\`\`\`python
# Basic usage
result = authenticate("user", "pass")

# With error handling
try:
    if authenticate(username, password):
        print("Login successful")
    else:
        print("Invalid credentials")
except AuthenticationError as e:
    print(f"Error: {e}")
\`\`\`
```

```{dropdown} Error Handling
:open: false

Raises:
- `AuthenticationError`: Invalid credentials
- `ConnectionError`: Database unavailable
- `ValueError`: Invalid input format
```
````

## Best Practices

### Use for Optional Content

```{success} Good Use Cases
- FAQ sections
- Optional details/explanations
- Troubleshooting steps
- Advanced options
- Example code
```

```{warning} Avoid for Essential Content
Don't hide:
- Critical information users need
- Primary instructions
- Required steps
- Important warnings
```

### Write Clear Titles

````markdown
✅ Good titles:
```{dropdown} How do I install Bengal?
```{dropdown} Troubleshooting Build Errors
```{dropdown} Advanced Configuration Options

❌ Vague titles:
```{dropdown} Click here
```{dropdown} More info
```{dropdown} Details
````

### Keep Content Focused

Each dropdown should address one topic:

````markdown
✅ Focused:
```{dropdown} Installation on macOS
macOS-specific installation steps...
```

```{dropdown} Installation on Linux
Linux-specific installation steps...
```

❌ Too broad:
```{dropdown} Installation and Configuration
Mixed installation, configuration, and usage information...
(Split into separate dropdowns)
```
````

### Use Sparingly

**Good:** 3-5 dropdowns in an FAQ section  
**Too many:** 20+ dropdowns on one page (consider restructuring)

## Accessibility

Dropdowns are accessible by default:
- Keyboard navigable (Tab, Enter/Space, Arrow keys)
- Screen reader friendly
- Focus states clearly visible
- ARIA labels included

```{tip} Accessibility Note
Dropdowns use semantic HTML with proper ARIA attributes for screen readers.
```

## Quick Reference

**Basic dropdown:**
````markdown
```{dropdown} Title
Content here
```
````

**Open by default:**
````markdown
```{dropdown} Title
:open: true

Content here
```
````

**With custom class:**
````markdown
```{dropdown} Title
:class: custom-style

Content here
```
````

## Troubleshooting

### Dropdown Not Collapsing

```{error} Common Issues
- **Nested code blocks:** Use 4 backticks for outer fence
- **Missing title:** Dropdown must have a title
- **Invalid options:** Check `:open:` is true/false
```

### Content Not Rendering

```{tip} Check Markdown
Ensure proper markdown formatting:
- Blank lines between elements
- Correct code block fencing
- Valid directive syntax
```

## Next Steps

- **[Admonitions](admonitions.md)** - Callout boxes
- **[Tabs](tabs.md)** - Tabbed content
- **[Cards](cards.md)** - Visual card grids
- **[Kitchen Sink](../kitchen-sink.md)** - See dropdowns in action

## Related

- [Directives Overview](index.md) - All directive types
- [Quick Reference](quick-reference.md) - Syntax cheatsheet
- [Markdown Basics](../writing/markdown-basics.md) - Markdown syntax

