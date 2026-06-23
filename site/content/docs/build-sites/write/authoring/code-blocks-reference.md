---


title: Code Blocks Reference
nav_title: Code Reference
description: Multi-language code tabs, Rosettes syntax themes, and advanced options
weight: 31
category: how-to
tags:
- persona-writer
- reference
icon: code
aliases:
  - /docs/content/authoring/code-blocks-reference/
aliases:
  - /docs/build-sites/write/authoring/code-blocks-reference/
  - /docs/content/authoring/code-blocks-reference/
---

# Code Blocks Reference

Advanced code presentation — multi-language tabs and syntax theme configuration.

:::{note}
**Do I need this?** Use for `code-tabs`, theme tuning, or Rosettes configuration.
For everyday fenced code blocks, see
[[docs/build-sites/write/authoring/code-blocks|Code Blocks]].
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
- [[docs/build-sites/write/authoring|Authoring Overview]] — Other authoring features
- [[docs/build-sites/customize|Theming Guide]] — Customize your site's appearance including syntax themes

**[[ext:rosettes:|Rosettes]] Documentation**:
- [[ext:rosettes:docs/reference/languages|Supported Languages]] — Full list of 55+ supported languages
- [[ext:rosettes:docs/styling/custom-themes|Custom Themes]] — Create your own syntax themes
- [[ext:rosettes:docs/highlighting/line-highlighting|Line Highlighting]] — Advanced highlighting options
::::
