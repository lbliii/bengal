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

```{tip} Using This Page
This is a **reference and showcase**. For learning how to use these features, see the detailed guides below.
```

## 📚 Detailed Documentation

Each feature shown here has complete documentation:

**Writing Guides:**
- [Getting Started](writing/getting-started.md) - Create your first page
- [Markdown Basics](writing/markdown-basics.md) - Essential syntax
- [Extended Markdown](writing/markdown-extended.md) - Tables, footnotes, task lists

**Directive Guides:**
- [Admonitions](directives/admonitions.md) - Note, tip, warning, and more
- [Tabs](directives/tabs.md) - Tabbed content views
- [Dropdown](directives/dropdown.md) - Collapsible sections
- [Code Tabs](directives/code-tabs.md) - Multi-language examples
- [Cards](directives/cards.md) - Visual card grids
- [Buttons](directives/buttons.md) - Call-to-action buttons
- [Quick Reference](directives/quick-reference.md) - All directive syntax

**Other Resources:**
- [Content Types](content-types/) - Page layouts
- [Advanced Features](advanced/) - Variables, SEO, publishing
- [Frontmatter Standard](frontmatter-standard.md) - Complete metadata reference

---

## 🎯 Admonitions

Bengal supports 9 admonition types: `note`, `tip`, `info`, `warning`, `danger`, `error`, `success`, `example`, and `caution`.

```{note} Note
Highlights important information without urgency. Supports **markdown**, `code`, and [links](https://example.com).
```

```{tip} Tip
Use admonitions sparingly for maximum impact.
```

```{warning} Warning
Important caveats or potential issues users should be careful about.
```

```{danger} Danger
Reserved for critical warnings about data loss, security issues, or breaking changes.
```

```{error} Error
Common errors and their solutions. Example: `Config file not found` → Create `bengal.toml` in project root.
```

```{success} Success
Confirmation messages for successful operations.
```

```{caution} Caution
Experimental features or things that may change in future versions.
```

---

## 📑 Tabs Directive

Tabs are perfect for showing platform-specific instructions or alternative approaches.

::::{tab-set}

:::{tab-item} macOS
```bash
brew install python3
pip3 install bengal-ssg
```
:::

:::{tab-item} Linux
```bash
sudo apt update
sudo apt install python3 python3-pip
pip3 install bengal-ssg
```
:::

:::{tab-item} Windows
```powershell
python -m pip install bengal-ssg
```
:::

::::

### Nested Content Example

::::{tab-set}

:::{tab-item} Python
```python
from bengal.core.site import Site

site = Site(".")
site.build()
print(f"Built {len(site.pages)} pages!")
```
:::

:::{tab-item} CLI
```bash
bengal build
bengal serve
bengal new my-site
```
:::

:::{tab-item} Configuration
```toml
[site]
title = "My Site"
baseurl = "https://example.com"

[build]
parallel = true
incremental = true
```
:::

::::

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

::::{tab-set}

:::{tab-item} Option 1
Content for option 1
:::

:::{tab-item} Option 2
Content for option 2
:::

::::

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

---

## 🔗 Cross-References

Bengal supports wiki-style cross-references using `[[link]]` syntax.

**Examples:**
- Link to another doc: [[docs/frontmatter-standard]]
- Link with custom text: [[docs/health-checks|Health Check Guide]]
- Link to homepage: [[_index|Go Home]]
- Link to about page: [[about]]

---

## 🔤 Variable Substitution

Bengal supports `{{ variable }}` syntax in markdown content. This page's title is: **{{ page.title }}**

You can access:
- `{{ page.title }}` - Page title from frontmatter
- `{{ page.date }}` - Page date
- `{{ site.title }}` - Site configuration
- `{{ page.metadata.custom_field }}` - Any frontmatter field

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

```
---

***

___
```

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

::::{tab-set}

:::{tab-item} With Admonitions

````{note} Nested Note in Tab
This demonstrates that you can nest directives deeply.

```{warning} Even Deeper!
And it still works! 🎉
```
````

:::

:::{tab-item} With Code

```python
# Code in a tab, in a dropdown!
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(factorial(5))  # 120
```

:::

:::{tab-item} With Lists

**Features demonstrated:**
1. Tabs inside dropdown
2. Multiple content types
3. Deep nesting support
4. Clean rendering

```{success} It Works!
Bengal handles complex nesting gracefully.
```

:::

::::
`````

