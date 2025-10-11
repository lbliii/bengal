---
title: Tabs
description: Create tabbed content for alternative views and multi-platform instructions
type: doc
weight: 3
tags: ["directives", "tabs", "ui"]
toc: true
---

# Tabs

**Purpose**: Present alternative content views in tabbed interfaces.

## What You'll Learn

- Create tabbed content sections
- Write platform-specific instructions
- Show code in multiple languages
- Nest markdown inside tabs

## Basic Syntax

Create tabs with the `{tabs}` directive:

````markdown
```{tabs}
:id: unique-identifier

### Tab: First Tab

Content for the first tab.

### Tab: Second Tab

Content for the second tab.
```
````

**Key components:**
- ` ```{tabs} ` - Starts the tabs directive
- `:id:` - Unique identifier (required)
- `### Tab: Name` - Tab markers (h3 heading with "Tab:" prefix)
- Content between tab markers

## Simple Example

````markdown
```{tabs}
:id: simple-example

### Tab: Python

Python is great for beginners.

### Tab: JavaScript

JavaScript powers the web.

### Tab: Ruby

Ruby emphasizes simplicity.
```
````

## Use Cases

### Platform-Specific Instructions

Show different instructions for different operating systems:

````markdown
```{tabs}
:id: installation

### Tab: macOS

Install with Homebrew:

\`\`\`bash
brew install bengal
\`\`\`

### Tab: Linux

Install with apt:

\`\`\`bash
sudo apt install bengal
\`\`\`

### Tab: Windows

Download from [releases page](https://github.com/bengal/releases).
```
````

### Multi-Language Code Examples

Show the same example in different languages:

````markdown
```{tabs}
:id: hello-world

### Tab: Python

\`\`\`python
def hello():
    print("Hello, World!")
    
hello()
\`\`\`

### Tab: JavaScript

\`\`\`javascript
function hello() {
  console.log("Hello, World!");
}

hello();
\`\`\`

### Tab: Ruby

\`\`\`ruby
def hello
  puts "Hello, World!"
end

hello
\`\`\`
```
````

### Configuration Options

Show different configuration formats:

````markdown
```{tabs}
:id: config-format

### Tab: TOML

\`\`\`toml
[site]
title = "My Site"
baseurl = "https://example.com"
\`\`\`

### Tab: YAML

\`\`\`yaml
site:
  title: My Site
  baseurl: https://example.com
\`\`\`

### Tab: JSON

\`\`\`json
{
  "site": {
    "title": "My Site",
    "baseurl": "https://example.com"
  }
}
\`\`\`
```
````

### Package Manager Choices

Show installation across package managers:

````markdown
```{tabs}
:id: package-managers

### Tab: npm

\`\`\`bash
npm install package-name
\`\`\`

### Tab: yarn

\`\`\`bash
yarn add package-name
\`\`\`

### Tab: pnpm

\`\`\`bash
pnpm add package-name
\`\`\`
```
````

## Markdown Support

Tabs support full markdown formatting:

````markdown
```{tabs}
:id: markdown-support

### Tab: Formatting

You can use:

- **Bold** and *italic*
- `Inline code`
- [Links](https://example.com)
- Lists

### Tab: Images

![Example image](/assets/images/example.png)

Images work perfectly in tabs!

### Tab: Code Blocks

\`\`\`python
# Full syntax highlighting
def calculate(x, y):
    return x + y
\`\`\`
```
````

## Tab Options

### Required: id

Every tabs directive needs a unique ID:

````markdown
```{tabs}
:id: my-unique-tabs
...
```
````

IDs should be:
- Unique across the page
- Descriptive (not `tabs1`, `tabs2`)
- Lowercase with hyphens

```{tip} Good ID Names
Use descriptive IDs: `install-instructions`, `code-examples`, `platform-choices`
```

### Optional: class

Add custom CSS classes:

````markdown
```{tabs}
:id: styled-tabs
:class: custom-style another-class
...
```
````

## Tab Naming

Tab names appear in the UI:

````markdown
### Tab: Short Name
````

**Best practices:**
- Keep names short (1-3 words)
- Be consistent (`macOS` not `Mac OS`, `MacOS`, `OSX`)
- Use proper capitalization
- Avoid redundancy ("Python Code" → "Python")

**Good names:**
```markdown
### Tab: Python
### Tab: macOS
### Tab: TOML
### Tab: Option A
```

**Avoid:**
```markdown
### Tab: Python Programming Language Code Example
### Tab: tab1
### Tab: Click here
```

## Nesting in Tabs

### Admonitions in Tabs

````markdown
```{tabs}
:id: with-admonitions

### Tab: macOS

```{note} macOS Note
Requires macOS 10.15 or higher.
```

\`\`\`bash
brew install bengal
\`\`\`

### Tab: Linux

```{warning} Dependencies
Install dependencies first: `apt install deps`
```

\`\`\`bash
sudo apt install bengal
\`\`\`
```
````

### Lists in Tabs

````markdown
```{tabs}
:id: with-lists

### Tab: Features

Key features:

1. Fast builds
2. Rich content
3. SEO ready

### Tab: Benefits

Why choose this:

- Easy to use
- Well documented
- Active community
```
````

## Common Patterns

### Installation Guide

````markdown
## Installation

Choose your platform:

```{tabs}
:id: install-guide

### Tab: macOS

**Requirements:** macOS 10.15+

\`\`\`bash
# Install with Homebrew
brew tap user/repo
brew install bengal
\`\`\`

**Verify installation:**
\`\`\`bash
bengal --version
\`\`\`

### Tab: Linux

**Requirements:** Ubuntu 20.04+ or equivalent

\`\`\`bash
# Add repository
sudo add-apt-repository ppa:user/bengal
# Install
sudo apt update && sudo apt install bengal
\`\`\`

**Verify installation:**
\`\`\`bash
bengal --version
\`\`\`

### Tab: Windows

**Requirements:** Windows 10+

1. Download from [releases page](https://github.com/user/repo/releases)
2. Run the installer
3. Follow the installation wizard

**Verify installation:**
\`\`\`powershell
bengal --version
\`\`\`
```
````

### Quick Start Examples

````markdown
## Quick Start

Choose your preferred language:

```{tabs}
:id: quickstart

### Tab: Python

\`\`\`python
from bengal import Site

site = Site.from_config("bengal.toml")
site.build()
\`\`\`

### Tab: CLI

\`\`\`bash
bengal build --parallel
\`\`\`
```
````

### API Examples

````markdown
## Making Requests

```{tabs}
:id: api-requests

### Tab: cURL

\`\`\`bash
curl -X GET https://api.example.com/users
\`\`\`

### Tab: Python

\`\`\`python
import requests
response = requests.get("https://api.example.com/users")
\`\`\`

### Tab: JavaScript

\`\`\`javascript
fetch("https://api.example.com/users")
  .then(response => response.json())
  .then(data => console.log(data));
\`\`\`
```
````

## Best Practices

### Use for Genuine Alternatives

```{success} Good Use Cases
- Platform-specific instructions (macOS, Linux, Windows)
- Language alternatives (Python, JavaScript, Ruby)
- Configuration formats (TOML, YAML, JSON)
- Package managers (npm, yarn, pnpm)
```

```{warning} Avoid Overuse
Don't use tabs for:
- Sequential steps (use numbered lists)
- Unrelated content (use sections)
- Single option (no need for tabs)
```

### Keep Tab Count Reasonable

**Good:** 2-4 tabs  
**Maximum:** 5-6 tabs  
**Too many:** 7+ tabs (consider restructuring)

### Make Content Parallel

Tabs should present the same information in different forms:

````markdown
✅ Good (parallel structure):
```{tabs}
:id: parallel-example

### Tab: Python
\`\`\`python
print("Hello")
\`\`\`

### Tab: JavaScript
\`\`\`javascript
console.log("Hello");
\`\`\`
```

❌ Poor (different content):
```{tabs}
:id: non-parallel

### Tab: Installation
Install the package...

### Tab: Features
Here are the features...
```
(These should be separate sections, not tabs)
````

### Test All Tabs

Always test that:
- All tabs render correctly
- Content formatting is preserved
- Code blocks have syntax highlighting
- Nested directives work

## Troubleshooting

### Tab Not Showing

```{error} Common Issues
- **Missing ID:** Every tabs directive needs `:id:`
- **Wrong marker:** Must use `### Tab:` exactly
- **Nesting depth:** Check backtick count for nested code
```

### Content Formatting Issues

```{tip} Escaping Code Blocks
Use 4 backticks for outer fence when nesting code blocks:

\`\`\`\`markdown
```{tabs}
...
\`\`\`python
code here
\`\`\`
...
```
\`\`\`\`
```

## Quick Reference

**Basic syntax:**
````markdown
```{tabs}
:id: unique-id

### Tab: Name 1
Content 1

### Tab: Name 2
Content 2
```
````

**With options:**
````markdown
```{tabs}
:id: my-tabs
:class: custom-class

### Tab: First
Content here
```
````

## Next Steps

- **[Code Tabs](code-tabs.md)** - Specialized for code examples
- **[Dropdown](dropdown.md)** - Collapsible content
- **[Admonitions](admonitions.md)** - Callout boxes
- **[Kitchen Sink](../kitchen-sink.md)** - See tabs in action

## Related

- [Directives Overview](index.md) - All directives
- [Quick Reference](quick-reference.md) - Syntax cheatsheet
- [Markdown Basics](../writing/markdown-basics.md) - Markdown syntax

