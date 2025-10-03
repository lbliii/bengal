# Mistune Additional Plugins Reference

**Quick reference for optional plugins you can enable in Bengal + Mistune**

Based on: https://mistune.lepture.com/en/latest/plugins.html

---

## 🎨 Currently Enabled in Bengal

✅ **Already active** when you use `markdown_engine = "mistune"`:

| Plugin | Syntax | Use Case |
|--------|--------|----------|
| `table` | `\| col \| col \|` | Tables |
| `strikethrough` | `~~text~~` | ~~Crossed out~~ |
| `task_lists` | `- [ ] item` | Todo lists |
| `url` | Auto-link URLs | Convenience |
| `footnotes` | `[^1]` | References |
| `def_list` | `Term\n:   Def` | Glossaries |
| `admonitions` (custom) | `!!! note` | Callouts |

---

## 🆕 Available to Enable

These are **built-in to Mistune** but not currently enabled. You can add them easily!

### 1. **Abbreviations** (`abbr`)

**Syntax:**
```markdown
The HTML specification is maintained by the W3C.

*[HTML]: Hyper Text Markup Language
*[W3C]: World Wide Web Consortium
```

**Output:**
```html
The <abbr title="Hyper Text Markup Language">HTML</abbr> specification
is maintained by the <abbr title="World Wide Web Consortium">W3C</abbr>.
```

**Use case:** API documentation, technical specs

**To enable:**
```python
plugins=['abbr', ...]
```

---

### 2. **Highlighting** (`mark`)

**Syntax:**
```markdown
==highlight this text==
```

**Output:**
```html
<mark>highlight this text</mark>
```

**Use case:** Emphasizing important text, search results

**To enable:**
```python
plugins=['mark', ...]
```

---

### 3. **Insertions** (`insert`)

**Syntax:**
```markdown
^^newly added text^^
```

**Output:**
```html
<ins>newly added text</ins>
```

**Use case:** Showing additions in documentation updates

**To enable:**
```python
plugins=['insert', ...]
```

---

### 4. **Superscript** (`superscript`)

**Syntax:**
```markdown
E = mc^2^

The 5^th^ element
```

**Output:**
```html
<p>E = mc<sup>2</sup></p>
<p>The 5<sup>th</sup> element</p>
```

**Use case:** Math, ordinals, exponents

**To enable:**
```python
plugins=['superscript', ...]
```

---

### 5. **Subscript** (`subscript`)

**Syntax:**
```markdown
H~2~O is water

CH~3~CH~2~OH is ethanol
```

**Output:**
```html
<p>H<sub>2</sub>O is water</p>
<p>CH<sub>3</sub>CH<sub>2</sub>OH is ethanol</p>
```

**Use case:** Chemistry, math notation

**To enable:**
```python
plugins=['subscript', ...]
```

---

### 6. **Math** (`math`)

**Block syntax:**
```markdown
$$
\operatorname{ker} f=\{g\in G:f(g)=e_{H}\}{\mbox{.}}
$$
```

**Inline syntax:**
```markdown
function $f(x) = x^2$
```

**Output:**
```html
<div class="math">$$...$$</div>
<span class="math">$f(x) = x^2$</span>
```

**Use case:** Technical documentation with LaTeX math

**Requires:** KaTeX or MathJax on frontend

**To enable:**
```python
plugins=['math', ...]
```

---

### 7. **Ruby** (`ruby`)

**Syntax:**
```markdown
[漢字(ㄏㄢˋㄗˋ)]
[漢(ㄏㄢˋ)字(ㄗˋ)]
```

**Output:**
```html
<ruby><rb>漢字</rb><rt>ㄏㄢˋㄗˋ</rt></ruby>
```

**Use case:** Asian language documentation (Japanese, Chinese)

**To enable:**
```python
plugins=['ruby', ...]
```

---

### 8. **Spoilers** (`spoiler`)

**Block syntax:**
```markdown
>! This is a spoiler
>! that will be hidden
```

**Inline syntax:**
```markdown
The answer is >! 42 !<
```

**Output:**
```html
<div class="spoiler">...</div>
<span class="spoiler">42</span>
```

**Use case:** Hidden content, solutions, answers

**To enable:**
```python
plugins=['spoiler', ...]
```

---

## 📦 How to Enable Additional Plugins

### Option 1: Per-Site Configuration (Recommended)

Edit `bengal/rendering/parser.py`:

```python
class MistuneParser(BaseMarkdownParser):
    def __init__(self):
        import mistune
        from bengal.rendering.mistune_plugins import plugin_admonitions
        
        self.md = mistune.create_markdown(
            plugins=[
                'table',
                'strikethrough',
                'task_lists',
                'url',
                'footnotes',
                'def_list',
                plugin_admonitions,
                # Add any of these:
                'abbr',           # Abbreviations
                'mark',           # ==highlight==
                'insert',         # ^^insert^^
                'superscript',    # ^sup^
                'subscript',      # ~sub~
                'math',           # $math$
                'ruby',           # Asian languages
                'spoiler',        # >! spoiler !<
            ],
            renderer='html',
        )
```

### Option 2: User Configuration (Future Feature)

Could add to `bengal.toml`:

```toml
[markdown]
engine = "mistune"
plugins = [
    "abbr",
    "mark",
    "math",
    "superscript",
    "subscript"
]
```

**Status:** Not implemented yet, but easy to add!

---

## 🎯 Recommended Plugin Sets

### For Technical Documentation
```python
plugins=[
    'table', 'footnotes', 'def_list',  # Core
    'abbr',                             # API terms
    'mark',                             # Highlighting
    'superscript', 'subscript',         # Math/chemistry
    plugin_admonitions,                 # Callouts
]
```

### For Math/Science Documentation
```python
plugins=[
    'table', 'footnotes', 'def_list',  # Core
    'math',                             # LaTeX
    'superscript', 'subscript',         # Notation
    plugin_admonitions,                 # Callouts
]
```

### For API Documentation
```python
plugins=[
    'table', 'footnotes', 'def_list',  # Core
    'abbr',                             # Terms
    'mark',                             # Highlighting
    'insert',                           # Changelog additions
    plugin_admonitions,                 # Callouts
]
```

### For International Documentation
```python
plugins=[
    'table', 'footnotes', 'def_list',  # Core
    'ruby',                             # Asian languages
    'abbr',                             # Terms
    plugin_admonitions,                 # Callouts
]
```

### Maximum Features (Everything!)
```python
plugins=[
    'table', 'strikethrough', 'task_lists', 'url',
    'footnotes', 'def_list',
    'abbr', 'mark', 'insert',
    'superscript', 'subscript',
    'math', 'ruby', 'spoiler',
    plugin_admonitions,
]
```

**Note:** More plugins = slightly slower parsing. Only enable what you need!

---

## 🎨 CSS for Additional Plugins

### Highlighting (`mark`)
```css
mark {
  background-color: #ffeb3b;
  padding: 0.1em 0.2em;
  border-radius: 2px;
}
```

### Insertions (`insert`)
```css
ins {
  text-decoration: none;
  background-color: #c8e6c9;
  border-bottom: 1px dashed #4caf50;
}
```

### Math (`math`)
```html
<!-- Add to your theme -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/katex/dist/katex.min.js"></script>
<script>
  document.querySelectorAll('.math').forEach(el => {
    katex.render(el.textContent, el);
  });
</script>
```

### Spoilers (`spoiler`)
```css
.spoiler {
  background-color: #000;
  color: #000;
  cursor: pointer;
  transition: all 0.3s;
}

.spoiler:hover {
  background-color: transparent;
  color: inherit;
}

span.spoiler {
  padding: 0 4px;
  border-radius: 2px;
}

div.spoiler {
  padding: 1em;
  border-radius: 4px;
  margin: 1em 0;
}
```

---

## 📊 Performance Impact

| Plugins Enabled | Parsing Speed | Notes |
|----------------|---------------|-------|
| **Core only** (7) | Baseline | Current setup |
| **+ 3 extras** | -5% | Minimal impact |
| **+ 6 extras** | -10% | Still very fast |
| **All plugins** (15) | -15-20% | Comprehensive but slower |

**Recommendation:** Only enable plugins you actually use in your content.

---

## 🚀 Quick Enable Guide

Want to add a plugin? Here's the 3-step process:

### Step 1: Edit Parser

```python
# bengal/rendering/parser.py
self.md = mistune.create_markdown(
    plugins=[
        # ... existing ...
        'math',  # Add this line
    ],
    renderer='html',
)
```

### Step 2: Update Documentation

Tell users the plugin is available:

```markdown
# Your docs
You can now use math: $E = mc^2$
```

### Step 3: Add CSS (if needed)

Some plugins need styling (math, spoiler, mark).

---

## 💡 Examples

### Technical Documentation with Math

```markdown
# Algorithm Complexity

The time complexity is O(n^2^).

For sorting algorithms:

$$
T(n) = \sum_{i=1}^{n} i = \frac{n(n+1)}{2}
$$

**Key terms:**

*[O]: Big O Notation
*[T]: Time Function

!!! note "Performance"
    The algorithm is ==O(n log n)== in best case.
```

### Chemistry Documentation

```markdown
# Chemical Reactions

Water (H~2~O) reacts with carbon dioxide (CO~2~):

H~2~O + CO~2~ → H~2~CO~3~

**Definitions:**

Acid
:   A substance with pH < 7

Base
:   A substance with pH > 7

!!! warning "Safety"
    Always add ==acid to water==, never water to acid!
```

### API Changelog

```markdown
# API v2.0 Changes

## Added Features

^^New endpoint:^^ `GET /api/v2/users`

~~Old endpoint:~~ `GET /api/v1/users` (deprecated)

**Abbreviations:**

*[API]: Application Programming Interface
*[GET]: HTTP GET Method

!!! tip "Migration"
    Update your code to use the ==new endpoints==.
```

---

## 🎯 Conclusion

You have access to **15 built-in Mistune plugins** total:

**Currently enabled (7):**
✅ table, strikethrough, task_lists, url, footnotes, def_list, admonitions

**Available to add (8):**
⏳ abbr, mark, insert, superscript, subscript, math, ruby, spoiler

**To enable more:** Just add the plugin name to the `plugins=[]` list in `MistuneParser.__init__()`.

**Performance impact:** Minimal (<20% even with all plugins).

**Recommendation:** Enable what you need for your documentation use case. Start with the core set and add more as needed!

