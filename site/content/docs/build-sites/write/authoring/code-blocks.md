---


title: Code Blocks
nav_title: Code
description: Add syntax-highlighted code with Rosettes, include files, configure themes, and create multi-language examples
weight: 30
category: how-to
icon: code
aliases:
  - /docs/content/authoring/code-blocks/
aliases:
  - /docs/build-sites/write/authoring/code-blocks/
  - /docs/content/authoring/code-blocks/
---
# Code Blocks

:::{note}
**Do I need this?** Yes when adding syntax-highlighted code to content.
For multi-language tabs and theme configuration, see
[[docs/build-sites/write/authoring/code-blocks-reference|Code Blocks Reference]].
:::

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
For inline and block math ($...$, $$...$$), see [[docs/build-sites/write/authoring/math|Math and LaTeX]]. The LaTeX identifier above is for syntax-highlighting LaTeX *code* in fenced blocks.
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


:::{seealso}
- [[docs/build-sites/write/authoring/code-blocks-reference|Code Blocks Reference]] — code-tabs and syntax themes
- [[docs/reference/directives/formatting|Formatting Directives]] — literalinclude options
:::
