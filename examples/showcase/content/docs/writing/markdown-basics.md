---
title: Markdown Basics
description: Essential markdown syntax for content writers
type: doc
weight: 2
tags: ["markdown", "syntax", "basics"]
toc: true
---

# Markdown Basics

**Purpose**: Learn the essential markdown syntax you'll use every day in Bengal.

## What You'll Learn

- Format text with bold, italic, and emphasis
- Create headings and structure
- Write lists and organize information
- Add links and images
- Include code snippets

## Headings

Create headings with `#` symbols. Use one `#` for top-level, add more for subheadings:

```markdown
# Heading 1
## Heading 2
### Heading 3
#### Heading 4
##### Heading 5
###### Heading 6
```

**Result:**

# Heading 1
## Heading 2
### Heading 3
#### Heading 4

```{tip} Heading Best Practices
- Use one H1 (`#`) per page (usually matches your frontmatter title)
- Don't skip levels (don't jump from H2 to H4)
- Keep headings descriptive and concise
```

## Paragraphs

Write paragraphs as plain text. Separate paragraphs with a blank line:

```markdown
This is the first paragraph. It contains multiple sentences that flow together.

This is the second paragraph. Notice the blank line between them.
```

**Result:**

This is the first paragraph. It contains multiple sentences that flow together.

This is the second paragraph. Notice the blank line between them.

## Text Emphasis

### Bold

Make text bold with `**` or `__`:

```markdown
This is **bold text** using asterisks.
This is __bold text__ using underscores.
```

**Result:** This is **bold text** using asterisks.

### Italic

Make text italic with `*` or `_`:

```markdown
This is *italic text* using asterisks.
This is _italic text_ using underscores.
```

**Result:** This is *italic text* using asterisks.

### Bold and Italic

Combine them:

```markdown
This is ***bold and italic*** text.
This is **_also bold and italic_** text.
```

**Result:** This is ***bold and italic*** text.

## Lists

### Unordered Lists

Create bullet lists with `-`, `*`, or `+`:

```markdown
- First item
- Second item
- Third item
  - Nested item
  - Another nested item
- Fourth item
```

**Result:**

- First item
- Second item
- Third item
  - Nested item
  - Another nested item
- Fourth item

### Ordered Lists

Create numbered lists with numbers and periods:

```markdown
1. First step
2. Second step
3. Third step
   1. Sub-step A
   2. Sub-step B
4. Fourth step
```

**Result:**

1. First step
2. Second step
3. Third step
   1. Sub-step A
   2. Sub-step B
4. Fourth step

```{tip} List Numbers
Markdown automatically renumbers lists, so you can use `1.` for every item if you want!
```

## Links

### Basic Links

Create links with `[text](url)`:

```markdown
Visit the [Bengal documentation](https://bengal-ssg.org/docs/).
```

**Result:** Visit the [Bengal documentation](https://bengal-ssg.org/docs/).

### Link Titles

Add hover text with quotes:

```markdown
Check out [Bengal](https://bengal-ssg.org "Bengal SSG Homepage").
```

### Internal Links

Link to other pages in your site:

```markdown
See the [getting started guide](getting-started.md).
Read more in the [frontmatter guide](frontmatter-guide.md).
```

See [Internal Links](internal-links.md) for advanced cross-referencing.

## Images

Add images with `![alt text](path)`:

```markdown
![Bengal Logo](/assets/images/logo.png)
```

**Alt text** describes the image for accessibility and SEO. Always include it!

```markdown
![Sunset over mountains showing orange and purple sky](/assets/sunset.jpg)
```

See [Images and Assets](images-and-assets.md) for more details.

## Code

### Inline Code

Wrap code with backticks:

```markdown
Use the `bengal build` command to build your site.
Install with `pip install bengal`.
```

**Result:** Use the `bengal build` command to build your site.

### Code Blocks

Create code blocks with triple backticks:

````markdown
```python
def hello():
    print("Hello, World!")
```
````

**Result:**

```python
def hello():
    print("Hello, World!")
```

Specify the language for syntax highlighting: `python`, `javascript`, `bash`, `html`, `css`, etc.

## Blockquotes

Create quotes with `>`:

```markdown
> This is a blockquote.
> It can span multiple lines.
>
> And even multiple paragraphs.
```

**Result:**

> This is a blockquote.
> It can span multiple lines.
>
> And even multiple paragraphs.

### Nested Blockquotes

```markdown
> Main quote
>> Nested quote
>>> Deeper nesting
```

## Horizontal Rules

Create dividers with `---`, `***`, or `___`:

```markdown
Above the line

---

Below the line
```

**Result:**

Above the line

---

Below the line

## Line Breaks

### Paragraph Break

Use a blank line for new paragraphs:

```markdown
First paragraph.

Second paragraph.
```

### Soft Break

End a line with two spaces for a line break within a paragraph:

```markdown
First line  
Second line (note two spaces after "line" above)
```

## Escaping Characters

Use backslash `\` to display special characters literally:

```markdown
\*This is not italic\*
\[This is not a link\]
\`This is not code\`
```

**Result:** \*This is not italic\*

## Quick Reference

| Element | Syntax |
|---------|--------|
| **Bold** | `**text**` or `__text__` |
| *Italic* | `*text*` or `_text_` |
| Heading | `## Heading` |
| Link | `[text](url)` |
| Image | `![alt](path)` |
| Code | `` `code` `` |
| Code block | ` ```language ` |
| List | `- item` or `1. item` |
| Blockquote | `> quote` |
| Horizontal rule | `---` |

## Common Patterns

### Documentation Section

```markdown
## Installation

Install Bengal with pip:

\`\`\`bash
pip install bengal
\`\`\`

For more options, see the [installation guide](installation.md).
```

### Tutorial Step

```markdown
### Step 2: Configure Your Site

Edit the `bengal.toml` file:

\`\`\`toml
[site]
title = "My Site"
baseurl = "https://example.com"
\`\`\`

**Important:** Replace `example.com` with your actual domain.
```

### Feature List

```markdown
## Key Features

Bengal offers:

- **Fast builds** - Incremental compilation
- **Rich content** - Directives and shortcodes
- **SEO ready** - Automatic sitemaps and RSS
```

## Next Steps

Master these basics, then explore:

- **[Extended Markdown](markdown-extended.md)** - Tables, footnotes, task lists
- **[Directives](../directives/)** - Callouts, tabs, and rich content
- **[Internal Links](internal-links.md)** - Cross-reference pages
- **[Images and Assets](images-and-assets.md)** - Working with media

## Related

- [Getting Started](getting-started.md) - Create your first page
- [Frontmatter Guide](frontmatter-guide.md) - Page metadata
- [Kitchen Sink](../kitchen-sink.md) - See all features in action

