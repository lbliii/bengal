---
title: "Kitchen Sink - All Features Demo"
description: "A comprehensive demonstration of EVERY Bengal feature in one page"
date: 2025-10-04
weight: 99
tags: ["features", "demo", "comprehensive", "directives", "markdown"]
toc: true
---

# Kitchen Sink: Every Feature in One Page

This page demonstrates **every single feature** that Bengal SSG offers. It's a living showcase of markdown capabilities, directives, template functions, and more.

---

## 🎯 Admonitions (9 Types)

Bengal supports 9 different admonition types for highlighting important information.

### Note Admonition

```{note} This is a Note
This is useful for highlighting important information without urgency.

You can include **markdown** formatting, `code snippets`, and even:

- Bullet points
- Multiple lines
- [Links](https://example.com)
```

### Tip Admonition

```{tip} Pro Tip!
Use admonitions sparingly for maximum impact. Too many callouts can overwhelm readers.
```

### Info Admonition

```{info} Information
The `info` admonition is great for providing additional context or background information.
```

### Warning Admonition

```{warning} Pay Attention!
Warnings should be used for important caveats, potential issues, or things users need to be careful about.

```python
# Be careful with this code!
dangerous_operation()
```
```

### Danger Admonition

```{danger} Critical Warning!
The `danger` admonition should be reserved for critical warnings about data loss, security issues, or breaking changes.

**Use this sparingly and only for serious matters.**
```

### Error Admonition

```{error} Common Error
Users might encounter this error when configuration is incorrect:

```
Error: Config file not found
```

**Solution:** Create a `bengal.toml` file in your project root.
```

### Success Admonition

```{success} Great Job!
Your site built successfully! All 150 pages generated in 0.3 seconds.

✨ Build metrics:
- Pages: 150
- Assets: 42
- Total time: 0.3s
```

### Example Admonition

```{example} Code Example
Here's how to use the `truncatewords` filter:

```jinja2
{{/* post.content | truncatewords(50) */}}
```

This will truncate the content to 50 words with an ellipsis.
```

### Caution Admonition

```{caution} Proceed with Caution
This feature is experimental and may change in future versions. Use at your own risk.
```

---

## 📑 Tabs Directive

Tabs are perfect for showing platform-specific instructions or alternative approaches.

````{tabs}
:id: installation-tabs

### Tab: macOS

Install Bengal on macOS using Homebrew:

```bash
brew install python3
pip3 install bengal-ssg
```

Or using pip directly:

```bash
python3 -m pip install bengal-ssg
```

### Tab: Linux

Install Bengal on Linux:

```bash
sudo apt update
sudo apt install python3 python3-pip
pip3 install bengal-ssg
```

For Arch Linux:

```bash
pacman -S python python-pip
pip install bengal-ssg
```

### Tab: Windows

Install Bengal on Windows:

```powershell
# Using pip
python -m pip install bengal-ssg
```

Or download from [PyPI](https://pypi.org/project/bengal-ssg/)
````

### Nested Tabs Example

````{tabs}
:id: framework-examples

### Tab: Python

```python
# Bengal build script
from bengal.core.site import Site

site = Site(".")
site.build()
print(f"Built {len(site.pages)} pages!")
```

**Key features:**
- Type hints
- Clean API
- Fast builds

### Tab: CLI

```bash
# Using Bengal CLI
bengal build
bengal serve
bengal new my-site
```

Simple and intuitive commands!

### Tab: Configuration

```toml
[site]
title = "My Site"
baseurl = "https://example.com"

[build]
parallel = true
incremental = true
```

TOML configuration is clean and readable.
````

---

## 🔽 Dropdown Directive

Use dropdowns to hide optional or advanced content.

````{dropdown} Click to Expand: Advanced Configuration
:open: false

Here's an advanced configuration example:

```toml
[build]
content_dir = "content"
output_dir = "public"
theme = "default"
parallel = true
incremental = true
minify_html = true
strict_mode = true

[build.output_formats]
html = true
json = true
llm_txt = true

[markdown]
parser = "mistune"
gfm = true
table_of_contents = true
```

This configuration enables:
- Parallel processing for faster builds
- Incremental builds (18-42x faster!)
- Multiple output formats
- Strict mode for error checking
````

```{dropdown} Default Open Dropdown
:open: true

This dropdown is open by default! Great for showing important information that users might want to collapse later.

**Example use cases:**
- Installation instructions
- Quick start guides
- Frequently needed references
```

````{dropdown} Another Advanced Example

You can nest almost anything in dropdowns:

```{note} Nested Note
This is a note inside a dropdown! 🎉
```

```{tabs}
:id: nested-tabs-in-dropdown

### Tab: Option 1
Content for option 1

### Tab: Option 2
Content for option 2
```

Even nested tabs work!
````

---

## 💻 Code-Tabs Directive

Perfect for showing the same example in multiple programming languages.

````{code-tabs}
:id: hello-world-example

### Tab: Python
```python
# Hello World in Python
def hello(name):
    return f"Hello, {name}!"

print(hello("Bengal"))
```

### Tab: JavaScript
```javascript
// Hello World in JavaScript
function hello(name) {
  return `Hello, ${name}!`;
}

console.log(hello("Bengal"));
```

### Tab: Ruby
```ruby
# Hello World in Ruby
def hello(name)
  "Hello, #{name}!"
end

puts hello("Bengal")
```

### Tab: Go
```go
// Hello World in Go
package main

import "fmt"

func hello(name string) string {
    return fmt.Sprintf("Hello, %s!", name)
}

func main() {
    fmt.Println(hello("Bengal"))
}
```
````

### Another Code-Tabs Example

````{code-tabs}
:id: api-example

### Tab: Python
```python
import requests

response = requests.get("https://api.example.com/data")
data = response.json()
print(data)
```

### Tab: JavaScript
```javascript
fetch("https://api.example.com/data")
  .then(response => response.json())
  .then(data => console.log(data));
```

### Tab: cURL
```bash
curl -X GET "https://api.example.com/data" \
  -H "Accept: application/json"
```
````

---

## 🔗 Cross-References

Bengal supports wiki-style cross-references using `[[link]]` syntax.

**Examples:**
- Link to another doc: [[docs/templates/function-reference]]
- Link with custom text: [[docs/templates/strings|String Functions]]
- Link to homepage: [[index|Go Home]]

*(Note: Cross-reference rendering depends on your content structure)*

---

## 🔤 Variable Substitution

You can use template variables directly in markdown:

- **Page Title:** {{/* page.title */}}
- **Site Title:** {{/* site.title */}}
- **Build Date:** {{/* page.date */}}
- **Reading Time:** {{/* page.content | reading_time */}} min read
*(Note: Actual substitution depends on your template configuration)*

---

## 📝 GFM Features

### Tables

| Feature | Status | Performance | Notes |
|---------|--------|-------------|-------|
| Incremental builds | ✅ | 18-42x faster | Best-in-class |
| Parallel processing | ✅ | 2-4x speedup | Automatic |
| Health checks | ✅ | Instant | 9 validators |
| Output formats | ✅ | Negligible | JSON, LLM-txt |

### Alignment

| Left | Center | Right |
|:-----|:------:|------:|
| A | B | C |
| 1 | 2 | 3 |

### Task Lists

- [x] Create kitchen sink page
- [x] Document all admonitions
- [x] Add tabs examples
- [x] Add dropdown examples
- [x] Add code-tabs examples
- [ ] Add even more examples
- [ ] Test everything
- [ ] Deploy showcase site

### Strikethrough

~~This text is struck through~~

### Footnotes

Here's a sentence with a footnote[^1].

Another reference to a longer footnote[^longnote].

[^1]: This is the first footnote.

[^longnote]: This is a longer footnote with multiple paragraphs.

    You can have multiple paragraphs in footnotes.

### Automatic Links

https://bengal-ssg.dev

### Emoji Support

:rocket: :fire: :sparkles: :zap: :muscle:

---

## 🎨 Code Blocks with Syntax Highlighting

### Python

```python
def build_site(config_path: str) -> None:
    """Build the entire site."""
    from bengal.core.site import Site
    
    site = Site(config_path)
    site.discover_content()
    site.build_all()
    
    print(f"✅ Built {len(site.pages)} pages successfully!")
```

### JavaScript

```javascript
// Bengal dev server hot reload
const watcher = fs.watch('./content', { recursive: true }, (event, filename) => {
  console.log(`File changed: ${filename}`);
  rebuild();
  browserSync.reload();
});
```

### TOML

```toml
[site]
title = "Bengal Showcase"
description = "Comprehensive example"

[build]
parallel = true
incremental = true

[[menus.main]]
name = "Docs"
url = "/docs/"
weight = 1
```

### Shell

```bash
# Build and serve
bengal build --parallel
bengal serve --port 8000

# Watch for changes
bengal serve --watch
```

---

## 📊 Blockquotes

> This is a simple blockquote.

> ### Blockquote with Heading
> 
> You can include headings, **formatting**, and even code:
> 
> ```python
> print("Hello from blockquote!")
> ```

> **Multi-paragraph blockquote**
>
> This is the first paragraph.
>
> This is the second paragraph with a [link](https://example.com).

---

## 📋 Lists

### Unordered Lists

- First item
- Second item
  - Nested item 1
  - Nested item 2
    - Double nested
- Third item

### Ordered Lists

1. First step
2. Second step
   1. Sub-step A
   2. Sub-step B
3. Third step

### Mixed Lists

1. Main point one
   - Supporting detail
   - Another detail
2. Main point two
   * Different marker
   + Another marker
3. Main point three

---

## 🖼️ Images

![Bengal Logo](https://via.placeholder.com/600x400?text=Bengal+SSG+Logo)

*Caption: Bengal SSG makes static sites beautiful*

### Image with Link

[![Clickable Image](https://via.placeholder.com/400x300?text=Click+Me)](https://bengal-ssg.dev)

---

## 🔢 Horizontal Rules

You can create horizontal rules with different syntax:

---

***

___

---

## 🎭 Inline Formatting

**Bold text** and __also bold__

*Italic text* and _also italic_

***Bold and italic*** and ___also bold and italic___

`Inline code` with backticks

~~Strikethrough text~~

Superscript: E = mc^2^

Subscript: H~2~O

---

## 📐 Definition Lists

Term 1
: Definition 1a
: Definition 1b

Term 2
: Definition 2

---

## 🧪 Nested Directives

Here's a complex nesting example:

`````{dropdown} Complex Nesting Example
:open: true

````{tabs}
:id: complex-nesting

### Tab: With Admonitions

```{note} Nested Note in Tab
This demonstrates that you can nest directives deeply.

```{warning} Even Deeper!
And it still works! 🎉
```
```

### Tab: With Code

```python
# Code in a tab, in a dropdown!
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(factorial(5))  # 120
```

### Tab: With Lists

**Features demonstrated:**
1. Tabs inside dropdown
2. Multiple content types
3. Deep nesting support
4. Clean rendering

```{success} It Works!
Bengal handles complex nesting gracefully.
```
````
`````

---

## 🎯 Everything Combined

Let's combine multiple features in one section:

`````{tabs}
:id: ultimate-example

### Tab: Directives Reference

```{note} Quick Reference
Here are all the directive types:
```

| Directive | Purpose | Example |
|-----------|---------|---------|
| note | General info | `{note}` |
| tip | Helpful hints | `{tip}` |
| warning | Cautions | `{warning}` |
| danger | Critical | `{danger}` |
| tabs | Multi-option | `{tabs}` |
| dropdown | Collapsible | `{dropdown}` |
| code-tabs | Code examples | `{code-tabs}` |

### Tab: Template Functions

Bengal provides **75+ template functions**:

```{dropdown} String Functions (11)

- `truncatewords` - Truncate to word count
- `slugify` - Create URL slugs  
- `strip_html` - Remove HTML tags
- `markdownify` - Render markdown
- `reading_time` - Calculate read time
- `excerpt` - Extract excerpt
- And more...

[Full reference →](../templates/function-reference/strings.md)
```

```{dropdown} Collection Functions (8)

- `where` - Filter collections
- `group_by` - Group items
- `sort_by` - Sort by field
- `unique` - Remove duplicates
- `first` / `last` - Get items
- And more...

[Full reference →](../templates/function-reference/collections.md)
```

### Tab: Performance

```{success} Performance Metrics
**Bengal SSG Benchmarks:**

- ⚡ **0.3s** to build 100 pages
- 🚀 **18-42x** faster incremental builds
- 💪 **2-4x** speedup with parallel processing
- ✅ **9** health check validators
- 📦 **75+** template functions
```

````{code-tabs}
:id: performance-comparison

### Tab: Bash
```bash
# Bengal build time
$ time bengal build
✅ Built 1000 pages in 2.8s

# Incremental rebuild
$ time bengal build
✅ Built 3 pages in 0.07s (42x faster!)
```

### Tab: Python
```python
from bengal.utils.build_stats import BuildStats

stats = BuildStats()
stats.record_build()
print(f"Pages: {stats.pages_built}")
print(f"Time: {stats.build_time}s")
print(f"Speed: {stats.pages_per_second} pages/s")
```
````
`````

---

## 🎉 Conclusion

This page demonstrates **every major feature** of Bengal SSG:

✅ **9 admonition types** - note, tip, info, warning, danger, error, success, example, caution
✅ **Tabs directive** - multi-platform instructions, nested content
✅ **Dropdown directive** - collapsible sections, open/closed states
✅ **Code-tabs directive** - multi-language code examples
✅ **Cross-references** - wiki-style links
✅ **Variable substitution** - dynamic content
✅ **GFM features** - tables, task lists, footnotes, strikethrough
✅ **Syntax highlighting** - 100+ languages supported
✅ **Complex nesting** - directives within directives
✅ **Rich content** - images, lists, quotes, horizontal rules

**This is what makes Bengal powerful!** 🚀

---

## 📚 Next Steps

Want to learn more? Check out these resources:

````{tabs}
:id: next-steps

### Tab: For Beginners

1. [[docs/getting-started/installation|Installation Guide]]
2. [[docs/getting-started/quick-start|Quick Start Tutorial]]
3. [[docs/getting-started/first-site|Build Your First Site]]

### Tab: For Advanced Users

1. [[docs/templates/function-reference|Template Functions Reference]]
2. [[docs/advanced/plugin-development|Plugin Development]]
3. [[docs/performance/optimization-tips|Performance Optimization]]

### Tab: For Migrators

1. [[tutorials/migration/from-hugo|Migrating from Hugo]]
2. [[tutorials/migration/from-jekyll|Migrating from Jekyll]]
3. [[tutorials/migration/from-eleventy|Migrating from Eleventy]]
````

---

**Last Updated:** October 4, 2025  
**Version:** 1.0.0  
**Build Time:** {{/* page.content | reading_time */}} min read
