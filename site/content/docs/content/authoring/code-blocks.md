---
title: Code Blocks
nav_title: Code
description: Add syntax-highlighted code, include files, and create multi-language examples
weight: 30
category: how-to
icon: code
---
# Code Blocks

How to add syntax-highlighted code to your documentation.

## Basic Code Blocks

Wrap code in triple backticks with a language identifier:

````markdown
```python
def hello():
    print("Hello, World!")
```
````

**Result**:

```python
def hello():
    print("Hello, World!")
```

### Supported Languages

Bengal uses Pygments for syntax highlighting. Common languages:

| Language | Identifier |
|----------|------------|
| Python | `python`, `py` |
| JavaScript | `javascript`, `js` |
| TypeScript | `typescript`, `ts` |
| Bash/Shell | `bash`, `sh`, `shell` |
| YAML | `yaml`, `yml` |
| JSON | `json` |
| HTML | `html` |
| CSS | `css` |
| Markdown | `markdown`, `md` |
| SQL | `sql` |
| Rust | `rust` |
| Go | `go` |

:::{tip}
For a complete list, see [Pygments lexers](https://pygments.org/docs/lexers/).
:::

## Line Highlighting

Draw attention to specific lines with `{hl_lines="..."}`:

````markdown
```python {hl_lines="2"}
def hello():
    print("This line is highlighted!")
    return True
```
````

### Highlight Multiple Lines

```markdown
{hl_lines="2 4"}     # Lines 2 and 4
{hl_lines="2-5"}     # Lines 2 through 5
{hl_lines="1 3-5 8"} # Lines 1, 3-5, and 8
```

## Line Numbers

Add line numbers for reference:

````markdown
```python {linenos=true}
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```
````

### Start from a Specific Line

````markdown
```python {linenos=true, linenostart=42}
# This starts at line 42
def important_function():
    pass
```
````

## Include Code from Files

Use `literalinclude` to include code directly from source files:

```markdown
:::{literalinclude} /path/to/file.py
:language: python
:::
```

### Include Specific Lines

```markdown
:::{literalinclude} /path/to/file.py
:language: python
:lines: 10-25
:::
```

### Include by Function/Class Name

```markdown
:::{literalinclude} /path/to/file.py
:language: python
:pyobject: MyClass.my_method
:::
```

### With Line Numbers and Highlighting

```markdown
:::{literalinclude} /path/to/file.py
:language: python
:linenos:
:emphasize-lines: 3,5
:::
```

:::{tip}
Use `literalinclude` to keep documentation in sync with actual source code. When the source changes, your docs update automatically.
:::

## Multi-Language Examples

Show the same concept in multiple languages with code tabs:

```markdown
:::{code-tabs}

```python
# Python
print("Hello")
```

```javascript
// JavaScript
console.log("Hello");
```

```bash
# Bash
echo "Hello"
```

:::{/code-tabs}
```

**Result**: Readers can switch between languages with tabs.

## Inline Code

For inline code, use single backticks:

```markdown
Run `bengal build` to generate your site.
```

**Result**: Run `bengal build` to generate your site.

## Code with Caption

Add a caption to your code block:

````markdown
```python
:caption: Example: Hello World function

def hello():
    print("Hello, World!")
```
````

## Diff Highlighting

Show code changes with diff syntax:

````markdown
```diff
- old_function()
+ new_function()
  unchanged_line()
```
````

## Console/Terminal Output

For terminal sessions, use `console` or `shell-session`:

````markdown
```console
$ bengal build
Building site...
✓ Built 42 pages in 1.2s
```
````

## Best Practices

:::{checklist}
- Always specify a language for syntax highlighting
- Use `literalinclude` for code that must stay in sync with source
- Highlight the important lines to guide readers
- Keep code examples short and focused on one concept
- Add line numbers when referencing specific lines in text
:::

## See Also

- [[docs/reference/directives/formatting|Formatting Directives Reference]] - Complete `literalinclude` options
- [[docs/content/authoring|Authoring Overview]] - Other authoring features
