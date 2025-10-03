---
title: "Advanced Markdown Features"
date: 2025-10-03
tags: ["markdown", "writing", "tutorial"]
categories: ["Documentation", "Writing"]
type: "reference"
description: "Comprehensive guide to all extended Markdown features supported by Bengal"
author: "Bengal Documentation Team"
---

# Advanced Markdown Features

Bengal supports extended Markdown via Python-Markdown, providing powerful formatting options beyond basic Markdown.

## Tables

Create rich tables with alignment options:

| Feature | Status | Performance | Notes |
|---------|:------:|------------:|:------|
| Incremental Builds | ✅ Done | 18-42x faster | Production ready |
| Parallel Processing | ✅ Done | 2-4x faster | Auto-enabled |
| Theme System | ✅ Done | N/A | Full featured |
| Plugin System | 🚧 WIP | N/A | Coming soon |

**Alignment**:
- `:---` - Left aligned (default)
- `:---:` - Center aligned
- `---:` - Right aligned

### Simple Tables

| Name | Role |
|------|------|
| Alice | Developer |
| Bob | Designer |
| Carol | Manager |

### Complex Tables

| Method | GET | POST | PUT | DELETE |
|--------|-----|------|-----|--------|
| Safe | ✅ | ❌ | ❌ | ❌ |
| Idempotent | ✅ | ❌ | ✅ | ✅ |
| Cacheable | ✅ | ⚠️ | ❌ | ❌ |

## Footnotes

Add footnotes for citations and additional context[^1]. You can reference them multiple times[^1] or create new ones[^2].

Footnotes automatically appear at the bottom of the page with backlinks[^3].

[^1]: This is the first footnote with detailed information.
[^2]: This is another footnote. You can use any identifier.
[^3]: Footnotes are perfect for citations, additional context, or tangential information that would disrupt the flow.

## Definition Lists

Perfect for glossaries and terminology:

Incremental Build
:   A build process that only rebuilds files that have changed since the last build, dramatically improving build speed.

Parallel Processing
:   The simultaneous execution of multiple tasks across CPU cores to reduce total processing time.

Static Site Generator
:   A tool that generates HTML files at build time rather than runtime, providing better performance and security.

Template Engine
:   A system for combining templates with data to produce rendered output, typically HTML pages.

### Multi-line Definitions

Term with Multiple Definitions
:   First definition explaining one aspect of the term.
:   Second definition providing another perspective or use case.
:   Third definition with additional context.

## Admonitions (Callouts)

Highlight important information with styled callout boxes:

!!! note "Quick Note"
    This is an informational callout. Great for highlighting tips, notes, and important information.

!!! warning "Caution"
    This is a warning callout. Use for important cautions that users should be aware of.

!!! danger "Critical Warning"
    This is a danger/error callout. Use sparingly for serious issues or breaking changes.

!!! tip "Pro Tip"
    This is a tip callout. Perfect for helpful suggestions and best practices.

!!! example "Example"
    This is an example callout. Use for code examples and demonstrations.

!!! info "Information"
    This is an info callout. Good for neutral informational content.

!!! success "Success"
    This is a success callout. Use for positive outcomes and completions.

### Collapsible Admonitions

!!! note "Click to expand"
    This content is hidden by default and can be expanded by clicking.
    
    Perfect for optional detailed information or long examples.

## Attribute Lists

Add custom CSS classes and IDs to elements:

This is a paragraph with custom styling.
{: .lead #intro-paragraph }

### Styled Paragraphs

This paragraph will have the "highlight" class applied.
{: .highlight }

### Custom IDs for Deep Linking

This section has a custom ID for direct linking.
{: #custom-section-id }

You can link to it with: `[Link text](#custom-section-id)`

## Code Blocks

### Syntax Highlighting

Python with syntax highlighting:

```python
def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number using recursion."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

# Example usage
result = fibonacci(10)
print(f"The 10th Fibonacci number is {result}")
```

JavaScript example:

```javascript
const greet = (name) => {
    console.log(`Hello, ${name}!`);
};

// Arrow function with destructuring
const { firstName, lastName } = user;
greet(`${firstName} ${lastName}`);
```

### Supported Languages

Bengal supports syntax highlighting for many languages:

```bash
# Shell script
bengal build --incremental --parallel
cd output && python -m http.server
```

```yaml
# YAML configuration
site:
  title: "My Site"
  baseurl: "https://example.com"
build:
  parallel: true
  incremental: true
```

```toml
# TOML configuration
[site]
title = "My Site"
baseurl = "https://example.com"

[build]
parallel = true
incremental = true
```

```css
/* CSS styling */
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}

@media (max-width: 768px) {
    .container {
        padding: 1rem;
    }
}
```

```sql
-- SQL query
SELECT u.name, COUNT(p.id) as post_count
FROM users u
LEFT JOIN posts p ON u.id = p.user_id
WHERE u.active = true
GROUP BY u.id
ORDER BY post_count DESC
LIMIT 10;
```

```go
// Go code
package main

import "fmt"

func main() {
    fmt.Println("Hello, Bengal!")
}
```

```rust
// Rust code
fn main() {
    let greeting = "Hello, Bengal!";
    println!("{}", greeting);
}
```

## Abbreviations

Define abbreviations once, use throughout the document:

*[HTML]: Hyper Text Markup Language
*[CSS]: Cascading Style Sheets
*[SSG]: Static Site Generator
*[API]: Application Programming Interface
*[CLI]: Command Line Interface

Bengal is an SSG that generates HTML and CSS. You can extend it via the API or use the CLI.

Hover over the abbreviations above to see their definitions!

## Task Lists

Track progress directly in your content:

### Project Status

- [x] Core object model
- [x] Rendering pipeline
- [x] CLI interface
- [x] Incremental builds
- [x] Parallel processing
- [x] Theme system
- [ ] Plugin system
- [ ] Search functionality
- [ ] Multi-language support

### Documentation Tasks

- [x] Getting started guide
- [x] Configuration reference
- [x] Template documentation
- [ ] API reference
- [ ] Plugin development guide

## Enhanced Code Features

### Inline Code

Use `backticks` for inline code like `bengal build` or `config.toml`.

You can also use inline code with special characters: `$HOME/.bengal-cache.json` or `npm install -g bengal-ssg`.

### Line Highlights (via comments)

```python
def process_pages(pages):
    results = []
    for page in pages:
        # This line is important!
        result = render_page(page)  # ← Pay attention here
        results.append(result)
    return results
```

## Block Quotes

### Simple Quotes

> "The best way to predict the future is to invent it."
> — Alan Kay

### Nested Quotes

> This is a top-level quote.
>
> > This is a nested quote within the first quote.
> >
> > > You can nest multiple levels if needed.
>
> Back to the first level.

### Quotes with Code

> **Pro Tip**: Always use incremental builds during development:
>
> ```bash
> bengal build --incremental --verbose
> ```
>
> This provides the fastest iteration cycle.

## Lists

### Unordered Lists

- First item
- Second item
  - Nested item
  - Another nested item
    - Even deeper nesting
    - Works naturally
  - Back to second level
- Third item

### Ordered Lists

1. First step
2. Second step
   1. Sub-step A
   2. Sub-step B
      1. Detailed step
      2. Another detail
3. Third step

### Mixed Lists

1. Ordered parent
   - Unordered child
   - Another child
     1. Ordered grandchild
     2. Another grandchild
2. Continue ordered

### Lists with Multiple Paragraphs

1. First item with multiple paragraphs.

   This is the second paragraph of the first item. Notice the indentation.

   You can have multiple paragraphs within a single list item.

2. Second item.

   With its own additional paragraph.

## Horizontal Rules

Separate sections with horizontal rules:

---

Three or more hyphens, asterisks, or underscores:

***

___

## Links

### Basic Links

[Bengal Documentation](https://bengal-ssg.org)

[Relative link to docs](/docs/)

[Relative link with anchor](/docs/configuration-reference/#build-options)

### Reference Links

This is [an example][ref] reference-style link.

You can also use [relative references][relative].

[ref]: https://example.com "Optional Title"
[relative]: /docs/getting-started/

### Automatic Links

<https://github.com/bengal-ssg/bengal>

<contact@bengal-ssg.org>

## Images

### Basic Images

![Bengal Logo](https://placehold.co/600x400/0066cc/ffffff?text=Bengal+SSG)

### Images with Links

[![Bengal Logo](https://placehold.co/300x200/0066cc/ffffff?text=Click+Me)](https://bengal-ssg.org)

### Responsive Images (via HTML)

<picture>
  <source media="(max-width: 768px)" srcset="https://placehold.co/400x300">
  <source media="(min-width: 769px)" srcset="https://placehold.co/800x600">
  <img src="https://placehold.co/800x600" alt="Responsive Image">
</picture>

## Smart Typography

Bengal automatically converts common text patterns:

- "Smart quotes" become "curly quotes"
- 'Single quotes' become 'curly single quotes'  
- Dashes -- become en-dashes –
- Triple dashes --- become em-dashes —
- Ellipsis... becomes …
- (c) becomes ©
- (r) becomes ®
- (tm) becomes ™

## HTML Integration

You can mix HTML directly with Markdown:

<div class="custom-container" style="background: #f0f0f0; padding: 1rem; border-radius: 4px;">
  <strong>Custom HTML Block</strong>
  
  You can combine HTML with **Markdown** formatting!
  
  - List items work
  - Even with `code`
</div>

### HTML Comments

<!-- This is a comment that won't appear in the rendered output -->

You can use HTML comments for notes to yourself or other authors.

## Escaping

### Escaping Special Characters

Use backslashes to escape Markdown syntax:

\*Not italic\*

\[Not a link\]

\`Not code\`

### Escaping in Code

Within code blocks, no escaping is needed:

```
*This asterisk is literal*
[This bracket is literal]
```

## Table of Contents

Bengal automatically generates a table of contents from your headings. Reference it with:

```markdown
[TOC]
```

Or in templates:

```jinja2
{{ '{{ toc }}' }}
```

### 📝 Showing Template Syntax in Documentation

When documenting templates, use **string literals** to display Jinja2 syntax:

```markdown
Use {{ '{{ toc }}' }} to display the table of contents.
Use {{ '{{ page.title }}' }} to show the page title.
```

**More examples**:
- Show variables: `{{ '{{ page.date }}' }}`
- Show filters: `{{ '{{ text | upper }}' }}`  
- Show tags: `{{ '{% for item in items %}' }}`

See [Template System → Escaping Template Syntax](/docs/template-system/#escaping-template-syntax) for complete details.

## Best Practices

### ✅ Do

- Use semantic heading hierarchy (H1 → H2 → H3)
- Add alt text to images
- Use tables for tabular data
- Use lists for sequences
- Add language identifiers to code blocks
- Use admonitions to highlight important information

### ❌ Don't

- Skip heading levels (H1 → H3)
- Use HTML when Markdown suffices
- Create tables for layout (use CSS)
- Overuse bold and italic
- Forget to test links

## Learn More

- [Markdown Guide (Basic)](/posts/markdown-guide/)
- [Template System](/docs/template-system/)
- [Configuration Reference](/docs/configuration-reference/)
- [Python-Markdown Documentation](https://python-markdown.github.io/)

## Extensions Enabled

Bengal enables these Python-Markdown extensions:

| Extension | Purpose |
|-----------|---------|
| `extra` | Multiple useful extensions |
| `codehilite` | Syntax highlighting |
| `fenced_code` | ``` code blocks |
| `tables` | Table support |
| `toc` | Table of contents |
| `meta` | Metadata support |
| `attr_list` | Custom attributes |
| `def_list` | Definition lists |
| `footnotes` | Footnote support |
| `admonition` | Callout boxes |

All extensions are enabled by default—no configuration required!

