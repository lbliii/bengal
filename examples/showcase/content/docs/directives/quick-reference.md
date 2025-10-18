---
title: Directive Quick Reference
description: Cheatsheet of all directive syntax for quick copy-paste
type: doc
weight: 1
tags: ["directives", "reference", "cheatsheet"]
---

# Directive Quick Reference

Copy-paste ready syntax for all Bengal directives.

## Admonitions

Nine types for different purposes:

````markdown
```{note} Note Title
Important information
```

```{tip} Pro Tip
Helpful suggestion
```

```{info} Information
Additional context
```

```{warning} Warning
Caution needed
```

```{danger} Danger
Critical warning
```

```{error} Error
Error message
```

```{success} Success
Positive outcome
```

```{example} Example
Code or usage example
```

```{caution} Caution
Proceed carefully
```
````

**[Full documentation →](admonitions.md)**

## Tabs

Tabbed content with markdown support:

````markdown
```{tabs}
:id: unique-id
:class: optional-class

### Tab: First Tab

Content for first tab with **markdown**.

### Tab: Second Tab

Content for second tab.

\`\`\`python
# Code blocks work too
print("Hello")
\`\`\`
```
````

**[Full documentation →](tabs.md)**

## Dropdown

Collapsible sections:

````markdown
```{dropdown} Click to Expand
:open: false
:class: custom-class

Hidden content here with **markdown** support.
```
````

**[Full documentation →](dropdown.md)**

## Code Tabs

Multi-language code examples:

````markdown
```{code-tabs}
:id: code-example

### Tab: Python

\`\`\`python
print("Hello, World!")
\`\`\`

### Tab: JavaScript

\`\`\`javascript
console.log("Hello, World!");
\`\`\`

### Tab: Ruby

\`\`\`ruby
puts "Hello, World!"
\`\`\`
```
````

**[Full documentation →](code-tabs.md)**

## Cards

### Single Card

````markdown
```{card} Card Title
:icon: 🎯
:link: /page/

Card description with **markdown**.
```
````

### Card Grid

````markdown
```{cards}
:columns: 3

```{card} First Card
:icon: ⚡
Content here
```

```{card} Second Card
:icon: 📝
More content
```

```{card} Third Card
:icon: 🔍
Even more
```
````

**[Full documentation →](cards.md)**

## Buttons

Call-to-action buttons:

````markdown
```{button} Button Text
:link: https://example.com
:type: primary
```

```{button} Secondary Button
:link: /page/
:type: secondary
```
````

**[Full documentation →](buttons.md)**

## Common Options

### Tabs Options

| Option | Values | Purpose |
|--------|--------|---------|
| `:id:` | string | Unique identifier |
| `:class:` | string | Custom CSS class |

### Dropdown Options

| Option | Values | Purpose |
|--------|--------|---------|
| `:open:` | true/false | Initially expanded |
| `:class:` | string | Custom CSS class |

### Card Options

| Option | Values | Purpose |
|--------|--------|---------|
| `:icon:` | emoji/text | Card icon |
| `:link:` | url | Card link destination |
| `:columns:` | 1-4 | Cards per row (grid only) |

### Button Options

| Option | Values | Purpose |
|--------|--------|---------|
| `:link:` | url | Button destination |
| `:type:` | primary/secondary | Button style |

## Copy-Paste Templates

### Documentation Warning

````markdown
```{warning} Breaking Change
Version 2.0 removes the deprecated feature. Use the new syntax instead.
```
````

### Installation Instructions

````markdown
```{tabs}
:id: install-instructions

### Tab: macOS

\`\`\`bash
brew install package
\`\`\`

### Tab: Linux

\`\`\`bash
apt install package
\`\`\`

### Tab: Windows

Download from [releases page](https://example.com).
```
````

### FAQ Section

````markdown
```{dropdown} Question 1?
:open: false

Answer to question 1.
```

```{dropdown} Question 2?
:open: false

Answer to question 2.
```
````

### Feature Grid

````markdown
```{cards}
:columns: 3

```{card} Fast
:icon: ⚡
Lightning-fast builds
```

```{card} Easy
:icon: 📝
Simple to use
```

```{card} Powerful
:icon: 🔥
Feature-rich
```
````

### Multi-Language Code

````markdown
```{code-tabs}
:id: hello-world

### Tab: Python

\`\`\`python
def hello():
    print("Hello, World!")
\`\`\`

### Tab: JavaScript

\`\`\`javascript
function hello() {
  console.log("Hello, World!");
}
\`\`\`
```
````

### CTA Section

````markdown
```{button} Get Started
:link: /docs/getting-started/
:type: primary
```

```{button} View on GitHub
:link: https://github.com/user/repo
:type: secondary
```
````

## Nesting Example

````markdown
```{tabs}
:id: platform-tabs

### Tab: macOS

```{note} macOS Note
Requires macOS 10.15 or higher.
```

\`\`\`bash
brew install package
\`\`\`

### Tab: Linux

```{warning} Dependencies
Install dependencies first: `apt install deps`
```

\`\`\`bash
apt install package
\`\`\`
```
````

## Quick Tips

```{tip} Syntax Highlighting
Install the Bengal VS Code extension for directive syntax highlighting!
```

```{tip} Test Directives
Use `bengal site serve` to preview directives with live reload.
```

```{warning} Escaping
When nesting code blocks, use 4 backticks ```` for the outer fence and 3 ``` for inner code blocks.
```

## See Also

- **[Admonitions](admonitions.md)** - Callout boxes
- **[Tabs](tabs.md)** - Tabbed content
- **[Cards](cards.md)** - Card grids
- **[Kitchen Sink](../kitchen-sink.md)** - Live examples
