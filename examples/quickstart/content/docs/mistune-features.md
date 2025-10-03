---
title: "Mistune Features & Directives"
date: 2025-10-03
description: "Comprehensive guide to Bengal's Mistune parser features and custom directives"
tags: ["mistune", "markdown", "directives", "documentation"]
toc: true
---

# Mistune Features & Directives

Bengal uses **Mistune** as its fast Markdown parser, providing **42% faster builds** while maintaining full documentation features. This page demonstrates all supported features and custom directives.

!!! tip "Performance"
    Mistune is **2x faster than MkDocs** and **4x faster than Sphinx**!

## 📚 Standard Markdown Features

### Headings

```markdown
# H1 Heading
## H2 Heading
### H3 Heading
#### H4 Heading
##### H5 Heading
###### H6 Heading
```

### Emphasis

**Bold text** with `**bold**` or `__bold__`

*Italic text* with `*italic*` or `_italic_`

***Bold and italic*** with `***text***`

~~Strikethrough~~ with `~~strikethrough~~`

### Lists

**Unordered:**
- Item 1
- Item 2
  - Nested item 2.1
  - Nested item 2.2
- Item 3

**Ordered:**
1. First item
2. Second item
3. Third item

**Task Lists:**
- [x] Completed task
- [ ] Incomplete task
- [ ] Another task

### Links and Images

[Link text](https://example.com)

![Alt text](https://via.placeholder.com/150)

### Code

Inline `code` with backticks.

```python
def hello_world():
    """A code block with syntax highlighting."""
    print("Hello, Bengal!")
    return True
```

## 📊 Tables

| Feature | Status | Performance |
|---------|:------:|------------:|
| Tables | ✅ | Fast |
| Footnotes | ✅ | Fast |
| Admonitions | ✅ | Fast |
| Directives | ✅ | Fast |

**With alignment:**

| Left aligned | Center aligned | Right aligned |
|:-------------|:--------------:|--------------:|
| Content | Content | Content |
| More | More | More |

## 📝 Footnotes

Here is a footnote reference[^1].

And another longer one[^longnote].

[^1]: This is the first footnote.

[^longnote]: Here's a longer footnote with multiple lines.
    
    You can have multiple paragraphs in footnotes.

## 📖 Definition Lists

API
:   Application Programming Interface

SSG
:   Static Site Generator

Markdown
:   A lightweight markup language
:   Used for documentation and content

## 🎨 Admonitions

Admonitions are callout boxes for highlighting important information.

### Note

```{note} Important Information
This is a note admonition. Use it for neutral information.

You can include **markdown** inside admonitions!
```

### Tip

```{tip} Pro Tip
Use admonitions to draw attention to important content.
```

### Warning

```{warning} Be Careful
This warns users about potential issues.
```

### Danger

```{danger} Critical Warning
This indicates dangerous or breaking changes.
```

### Example

```{example} Code Example
You can include code blocks in admonitions:

    def example():
        return "Hello!"
```

### Success

```{success} Well Done
Operation completed successfully!
```

### Info

```{info} Did You Know?
Mistune is 42% faster than python-markdown!
```

## 🔧 Custom Directives

Bengal extends Mistune with powerful custom directives for rich documentation.

### Dropdowns (Collapsible Sections)

```{dropdown} Click to expand
:open: false

This content is hidden by default. Click the summary to reveal it!

You can include any markdown:

- Lists
- **Bold text**
- Code blocks

```python
print("Code works too!")
```
```

**Result:**

```{dropdown} Example Dropdown
:open: false

Hidden content with **markdown** support!

- Feature 1
- Feature 2
- Feature 3
```

### Tabs

```{tabs}
:id: example-tabs

### Tab: Python

Here's a Python example:

    def hello():
        print("Hello from Python!")

**Note:** Use indented code blocks (4 spaces) inside tabs.

### Tab: JavaScript

Here's a JavaScript example:

    function hello() {
        console.log("Hello from JavaScript!");
    }

### Tab: Go

And here's Go:

    func hello() {
        fmt.Println("Hello from Go!")
    }
```

**Result:**

```{tabs}
:id: demo-tabs

### Tab: Python

Python code example:

    def fibonacci(n):
        if n <= 1:
            return n
        return fibonacci(n-1) + fibonacci(n-2)

### Tab: JavaScript

JavaScript code example:

    function fibonacci(n) {
        if (n <= 1) return n;
        return fibonacci(n-1) + fibonacci(n-2);
    }
```

## 📦 Nested Features

You can nest different features together!

### Admonition with List and Code

!!! example "Complex Example"
    Here's a list inside an admonition:
    
    1. First item
    2. Second item with `inline code`
    3. Third item
    
    And a code block:
    
    ```python
    def nested_example():
        return "This works!"
    ```

### Dropdown with Admonition

```{dropdown} Advanced Features

!!! tip "Nested Admonition"
    You can nest admonitions inside dropdowns!
    
    - Feature A
    - Feature B
    - Feature C

**And regular markdown** continues to work.
```

### Tabs with Multiple Content Types

```{tabs}

### Tab: Documentation

**This tab** contains *documentation* with various formatting:

- Bullet points
- **Bold** and *italic*
- Links: [Bengal Docs](/)

### Tab: Code

Code example with indentation:

    class Example:
        def __init__(self):
            self.value = 42
        
        def method(self):
            return self.value * 2

### Tab: Notes

!!! note "Important"
    Even admonitions work inside tabs!
```

## ⚠️ Known Limitations

### Nested Code Fences

**Issue:** Triple backticks inside directives can break parsing.

**Solution:** Use indented code blocks (4 spaces) inside directives:

```markdown
\`\`\`{tabs}

### Tab: Example

    # This is indented code (4 spaces)
    print("This works!")
\`\`\`
```

### Code-Tabs Directive

**Status:** Partial support. Use admonitions for code examples instead:

```markdown
!!! example "Python"
    \`\`\`python
    print("hello")
    \`\`\`

!!! example "JavaScript"
    \`\`\`javascript
    console.log("hello")
    \`\`\`
```

## 🎯 Best Practices

### 1. Use Admonitions for Callouts

✅ **Good:**
```markdown
!!! tip "Performance Tip"
    Enable parallel builds for faster performance!
```

❌ **Avoid:** Using blockquotes for callouts
```markdown
> Performance Tip: Enable parallel builds
```

### 2. Use Tabs for Multi-Language Examples

✅ **Good:** Tabs for showing same concept in different languages

❌ **Avoid:** Separate sections for each language

### 3. Use Dropdowns for Optional Details

✅ **Good:** Hide advanced details in dropdowns

❌ **Avoid:** Cluttering main content with optional information

### 4. Nest Carefully

✅ **Good:**
- Dropdowns → Admonitions
- Tabs → Lists/Text
- Admonitions → Code/Lists

⚠️ **Careful:**
- Avoid deeply nested directives (3+ levels)
- Use indented code inside directives

## 🚀 Performance Tips

1. **Mistune is fast** - 42% faster than python-markdown
2. **Parallel builds** - Use `max_workers` in config
3. **Incremental builds** - Only rebuilds changed files
4. **Thread-safe** - Parser instances cached per thread

```toml
# bengal.toml
[build]
markdown_engine = "mistune"
parallel = true
max_workers = 10
incremental = true
```

## 📚 Additional Resources

- [Mistune Documentation](https://mistune.lepture.com/)
- [CommonMark Spec](https://commonmark.org/)
- [GFM Spec](https://github.github.com/gfm/)

---

!!! success "Ready to Use!"
    All these features work out of the box with Bengal's Mistune parser!

**Next steps:**
- Try directives in your content
- Enable parallel builds
- Enjoy faster documentation builds! 🎉

