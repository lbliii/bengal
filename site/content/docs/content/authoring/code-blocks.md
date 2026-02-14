---
title: Code Blocks
nav_title: Code
description: Add syntax-highlighted code with Rosettes, include files, configure themes, and create multi-language examples
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

Bengal uses **[[ext:rosettes:docs/reference/languages|Rosettes]]** for syntax highlighting—a modern, thread-safe highlighter designed for Python 3.14t free-threading. Rosettes supports 55+ languages:

::::{tab-set}

:::{tab-item} Common
| Language | Identifier |
|----------|------------|
| Python | `python`, `py` |
| JavaScript | `javascript`, `js` |
| TypeScript | `typescript`, `ts` |
| Bash/Shell | `bash`, `sh`, `shell`, `zsh` |
| YAML | `yaml`, `yml` |
| JSON | `json` |
| TOML | `toml` |
| HTML | `html` |
| CSS | `css` |
| Markdown | `markdown`, `md` |
:::

:::{tab-item} Systems
| Language | Identifier |
|----------|------------|
| Rust | `rust`, `rs` |
| Go | `go`, `golang` |
| C | `c`, `h` |
| C++ | `cpp`, `c++`, `cxx` |
| Zig | `zig` |
| Nim | `nim` |
| V | `v`, `vlang` |
| Mojo | `mojo`, `🔥` |
:::

:::{tab-item} JVM & .NET
| Language | Identifier |
|----------|------------|
| Java | `java` |
| Kotlin | `kotlin`, `kt` |
| Scala | `scala`, `sc` |
| Groovy | `groovy`, `gradle` |
| Clojure | `clojure`, `clj` |
:::

:::{tab-item} Data & Config
| Language | Identifier |
|----------|------------|
| SQL | `sql`, `mysql`, `postgresql` |
| GraphQL | `graphql`, `gql` |
| HCL/Terraform | `hcl`, `terraform`, `tf` |
| Dockerfile | `dockerfile`, `docker` |
| Nginx | `nginx` |
| INI | `ini`, `cfg`, `conf` |
| Protobuf | `protobuf`, `proto` |
| Prisma | `prisma` |
| CUE | `cue` |
| Pkl | `pkl` |
:::

:::{tab-item} Scripting
| Language | Identifier |
|----------|------------|
| Ruby | `ruby`, `rb` |
| PHP | `php` |
| Perl | `perl`, `pl` |
| Lua | `lua` |
| R | `r`, `rlang` |
| Julia | `julia`, `jl` |
| Elixir | `elixir`, `ex` |
| PowerShell | `powershell`, `ps1`, `pwsh` |
| Fish | `fish` |
| AWK | `awk`, `gawk` |
:::

:::{tab-item} Web & Templates
| Language | Identifier |
|----------|------------|
| SCSS/Sass | `scss`, `sass` |
| Vue | `vue` |
| Svelte | `svelte` |
| Jinja2 | `jinja2`, `jinja`, `j2` |
| Liquid | `liquid`, `jekyll` |
| Handlebars | `handlebars`, `hbs` |
| Nunjucks | `nunjucks`, `njk` |
| Twig | `twig` |
:::

:::{tab-item} Markup & Docs
| Language | Identifier |
|----------|------------|
| Diff | `diff`, `patch` |
| reStructuredText | `rst`, `restructuredtext` |
| AsciiDoc | `asciidoc`, `adoc` |
| LaTeX | `latex`, `tex` |
| MyST | `myst`, `mystmd` |
| Mermaid | `mermaid`, `mmd` |
| XML | `xml`, `xsl`, `svg` |
| HTTP | `http`, `https` |
| Regex | `regex`, `regexp` |
:::

:::{seealso}
For inline and block math ($...$, $$...$$), see [[docs/content/authoring/math|Math and LaTeX]]. The LaTeX identifier above is for syntax-highlighting LaTeX *code* in fenced blocks.
:::

:::{tab-item} Functional
| Language | Identifier |
|----------|------------|
| Haskell | `haskell`, `hs` |
| OCaml | `ocaml`, `ml`, `reasonml` |
| Dart | `dart` |
| Swift | `swift` |
| WebAssembly | `wasm`, `wat` |
| CUDA | `cuda`, `cu` |
| Triton | `triton` |
| Stan | `stan` |
| Gleam | `gleam` |
| Cypher | `cypher`, `neo4j` |
:::

::::

:::{tip}
Languages not in the list are rendered as plain preformatted text with proper HTML escaping.
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
:start-line: 10
:end-line: 25
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
FROM python:3.14-slim
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

## Syntax Themes

Bengal's syntax highlighting uses **[[ext:rosettes:docs/styling/custom-themes|Rosettes]]**, which provides configurable themes that adapt to light/dark mode.

### Available Themes

| Theme | Description | Mode |
|-------|-------------|------|
| `bengal-tiger` | Bengal brand theme with orange accents | Dark |
| `bengal-snow-lynx` | Light variant with warm teal | Adaptive |
| `bengal-charcoal` | Minimal dark variant | Dark |
| `bengal-blue` | Blue accent variant | Dark |
| `monokai` | Classic warm, vibrant theme | Dark |
| `dracula` | Purple accent theme | Dark |
| `github` | GitHub's syntax theme | Adaptive |
| `github-light` | GitHub light mode only | Light |
| `github-dark` | GitHub dark mode only | Dark |

### Configuration

Configure syntax highlighting in `config/_default/theme.yaml`:

```yaml
theme:
  # Site palette (syntax inherits from this when theme is "auto")
  default_palette: "snow-lynx"

  syntax_highlighting:
    # Theme selection:
    # - "auto": Inherit from default_palette (recommended)
    # - Specific theme name: "monokai", "dracula", etc.
    theme: "auto"

    # CSS class output style:
    # - "semantic": Human-readable classes (.syntax-function, .syntax-string)
    # - "pygments": Pygments-compatible short classes (.nf, .s)
    css_class_style: "semantic"
```

### Palette Inheritance

When `theme: "auto"` is set, the syntax theme automatically inherits from your site's `default_palette`:

| Site Palette | Syntax Theme |
|--------------|--------------|
| `default` / empty | `bengal-tiger` |
| `snow-lynx` | `bengal-snow-lynx` |
| `brown-bengal` | `bengal-tiger` |
| `silver-bengal` | `bengal-charcoal` |
| `charcoal-bengal` | `bengal-charcoal` |
| `blue-bengal` | `bengal-blue` |

### CSS Class Styles

[[ext:rosettes:|Rosettes]] supports two CSS class naming conventions:

::::{tab-set}

:::{tab-item} Semantic (Default)
Human-readable class names that describe the code element's purpose:

```html
<span class="syntax-function">greet</span>
<span class="syntax-string">"Hello"</span>
<span class="syntax-keyword">def</span>
```

**Best for**: New projects, custom themes, semantic CSS.
:::

:::{tab-item} Pygments
Short class names compatible with existing Pygments themes:

```html
<span class="nf">greet</span>
<span class="s">"Hello"</span>
<span class="k">def</span>
```

**Best for**: Migrating from Pygments, using existing Pygments CSS themes.
:::

::::

:::{note}
[[ext:rosettes:|Rosettes]] is designed for Python 3.14t free-threading with zero global mutable state. It provides thread-safe syntax highlighting with O(n) guaranteed parsing. See [[ext:rosettes:docs/about/performance|Rosettes Performance]] for benchmarks.
:::

::::{seealso}
- [[docs/reference/directives/formatting|Formatting Directives Reference]] — Complete `literalinclude` options
- [[docs/content/authoring|Authoring Overview]] — Other authoring features
- [[docs/theming|Theming Guide]] — Customize your site's appearance including syntax themes

**[[ext:rosettes:|Rosettes]] Documentation**:
- [[ext:rosettes:docs/reference/languages|Supported Languages]] — Full list of 55+ supported languages
- [[ext:rosettes:docs/styling/custom-themes|Custom Themes]] — Create your own syntax themes
- [[ext:rosettes:docs/highlighting/line-highlighting|Line Highlighting]] — Advanced highlighting options
::::
