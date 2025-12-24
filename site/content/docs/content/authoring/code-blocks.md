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

Show the same concept in multiple languages with code tabs. Use `code-tabs` for a streamlined, code-first experience with auto-sync, language icons, and copy buttons.

### Syntax

Tab labels are automatically derived from the code fence language—no extra markers needed:

````markdown
:::{code-tabs}

```python
print("Hello")
```

```javascript
console.log("Hello");
```

```bash
echo "Hello"
```

:::
````

### Result

:::{code-tabs}

```python
def greet(name):
    """Say hello to someone."""
    print(f"Hello, {name}!")

greet("World")
```

```javascript
function greet(name) {
    // Say hello to someone
    console.log(`Hello, ${name}!`);
}

greet("World");
```

```bash
# Say hello
greet() {
    echo "Hello, $1!"
}

greet "World"
```

:::

### With Filenames and Highlights

Add filenames and line highlights directly in the code fence info string:

:::{code-tabs}

```python client.py {3-4}
import requests

def get_users():
    response = requests.get("/api/users")
    return response.json()
```

```javascript client.js {3-4}
import fetch from 'node-fetch';

async function getUsers() {
    const response = await fetch('/api/users');
    return response.json();
}
```

```bash {2}
# Get all users
curl -X GET "https://api.example.com/users" \
  -H "Authorization: Bearer $API_KEY"
```

:::

### Custom Tab Labels

Use `title="..."` to override the default language-derived label:

````markdown
:::{code-tabs}

```javascript title="React"
const [count, setCount] = useState(0);
```

```javascript title="Vue"
const count = ref(0);
```

:::
````

### Files Without Extensions

For files like `Dockerfile` that have no extension, use `title=`:

````markdown
:::{code-tabs}

```dockerfile title="Dockerfile"
FROM python:3.12-slim
```

```yaml docker-compose.yml
services:
  web:
    build: .
```

:::
````

### Code Tabs vs Tab-Set

| Feature | `code-tabs` | `tab-set` |
|---------|-------------|-----------|
| **Syntax** | Just code fences | Nested `:::{tab-item}` |
| **Auto sync** | ✅ All code-tabs sync by language | Manual with `:sync:` |
| **Language icons** | ✅ Automatic | Manual with `:icon:` |
| **Copy button** | ✅ Built-in | ❌ None |
| **Line numbers** | ✅ Auto for 3+ lines | ❌ None |
| **Best for** | Code examples | Mixed content |

:::{tip}
Use `code-tabs` when you're showing the same concept in multiple programming languages. Use `tab-set` when tabs contain mixed content (text, images, etc.) or aren't code-focused.
:::

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

::::{seealso}
- [[docs/reference/directives/formatting|Formatting Directives Reference]] — Complete `literalinclude` options
- [[docs/content/authoring|Authoring Overview]] — Other authoring features
::::
