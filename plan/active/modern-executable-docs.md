# Modern Executable Documentation Format

## The Problem with Notebooks

Jupyter notebooks (2011) feel old because they are:

### Technical Debt
❌ **JSON format** - Not human-readable in version control
❌ **Embedded outputs** - Binary blobs in git (images, plots)
❌ **Execution state** - "Restart and run all" to verify
❌ **Merge conflicts** - Nightmare with JSON structure
❌ **Opaque metadata** - Cell metadata is buried
❌ **Heavy files** - 5MB notebook for 20 lines of code

### Workflow Issues
❌ **Notebook apps required** - JupyterLab, VS Code, etc.
❌ **Server-based** - Not just "open in editor"
❌ **Not plain text** - Can't easily grep/diff
❌ **Dual authoring** - Code cells vs markdown cells feel separate

---

## What Would a Modern Format Look Like?

### Option 1: Observable Framework Style (JavaScript/Modern)

**Observable** (2017-present) got this right for JavaScript:

```markdown
# My Analysis

Here's our data:

\`\`\`js
data = await fetch("data.json").then(r => r.json())
\`\`\`

Now let's visualize:

\`\`\`js
Plot.plot({
  marks: [
    Plot.dot(data, {x: "x", y: "y"})
  ]
})
\`\`\`

The chart above shows...
```

**Key innovations:**
✅ **Plain markdown** - Just markdown with reactive code blocks
✅ **Git-friendly** - Human-readable diffs
✅ **Reactive** - Variables auto-update when dependencies change
✅ **No separate cells** - Just code blocks in narrative
✅ **Literate programming** - Code is documentation

**But:** JavaScript-only, proprietary runtime

---

### Option 2: Quarto (R/Python, 2022)

**Quarto** is Posit's (RStudio) modern take:

```markdown
---
title: "My Analysis"
format: html
execute:
  echo: true
  warning: false
---

# Introduction

Let's load our data:

\`\`\`{python}
import pandas as pd
data = pd.read_csv("data.csv")
data.head()
\`\`\`

The data shows {python} len(data) rows.

## Analysis

\`\`\`{python}
#| label: fig-scatter
#| fig-cap: "Relationship between X and Y"

import matplotlib.pyplot as plt
plt.scatter(data.x, data.y)
\`\`\`

See @fig-scatter for the correlation.
```

**Key innovations:**
✅ **QMD format** - Enhanced markdown (plain text)
✅ **Multi-language** - Python, R, Julia, Observable JS
✅ **Cross-references** - `@fig-scatter` linking
✅ **Inline code** - `` `{python} expr` `` in text
✅ **Cell options** - `#| label: fig-1` metadata
✅ **Git-friendly** - Plain text, easy diffs
✅ **Outputs separate** - Not in source file
✅ **Renders to many formats** - HTML, PDF, docx, slides

**Industry adoption:**
- RStudio/Posit's successor to R Markdown
- Used by data science teams at major companies
- Open source, active development

---

### Option 3: Marimo (Python, 2024)

**Marimo** is a reactive Python notebook (brand new):

```python
import marimo

__generated_with = "0.1.0"
app = marimo.App()

@app.cell
def __():
    import pandas as pd
    data = pd.read_csv("data.csv")
    return data

@app.cell
def __(data):
    # Automatically re-runs when data changes
    filtered = data[data.value > 10]
    return filtered
```

**Key innovations:**
✅ **Pure Python** - No JSON, just `.py` files
✅ **Reactive** - Like Observable, but for Python
✅ **Git-friendly** - Standard Python files
✅ **No hidden state** - Execution order is guaranteed
✅ **Built-in editor** - Modern web UI

**But:** Very new (2024), small ecosystem

---

### Option 4: MyST Markdown (Sphinx, 2020+)

**MyST** (Markedly Structured Text) is what Jupyter Book uses:

```markdown
---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
kernelspec:
  name: python3
---

# My Analysis

\`\`\`{code-cell} python
import numpy as np
data = np.random.randn(100)
\`\`\```

The mean is {eval}\`data.mean()\`.
```

**Key innovations:**
✅ **Markdown-native** - Plain text, not JSON
✅ **Jupytext compatible** - Sync with `.ipynb`
✅ **Sphinx integration** - Full docs toolchain
✅ **Directives** - Rich syntax (like your plugins!)

---

## What Should Bengal Support?

### The Modern Format Matrix

| Format | Plain Text | Multi-Lang | Reactive | Git-Friendly | Mature |
|--------|-----------|------------|----------|--------------|---------|
| **Jupyter .ipynb** | ❌ JSON | ✅ | ❌ | ❌ | ✅ 13 years |
| **Observable** | ✅ | ❌ JS only | ✅ | ✅ | ✅ 7 years |
| **Quarto .qmd** | ✅ | ✅ | ❌ | ✅ | ✅ 3 years |
| **Marimo .py** | ✅ | ❌ Py only | ✅ | ✅ | ⚠️ 1 year |
| **MyST .md** | ✅ | ✅ | ❌ | ✅ | ✅ 4 years |

### Recommendation: Quarto (.qmd) as "Native" Format 🎯

**Why Quarto?**

1. **Modern & Mature** - 3 years old, industry adoption
2. **Plain text** - `.qmd` files are just markdown with execution
3. **Multi-language** - Python, R, Julia, Observable JS
4. **Git-friendly** - Easy diffs, no binary blobs
5. **Extensible** - Uses Pandoc, can add custom features
6. **Cross-references** - Native `@fig-1`, `@tbl-1` linking
7. **Multiple outputs** - HTML, PDF, slides from same source
8. **Industry momentum** - Posit backing, growing ecosystem

**What it looks like:**

```markdown
---
title: "API Performance Analysis"
author: "Engineering Team"
date: 2024-10-14
format:
  bengal-html:
    theme: default
    toc: true
execute:
  cache: true
---

# Overview

Our API performance has {python} f"{improvement}%" improvement.

## Load Testing Results

\`\`\`{python}
#| label: fig-response-times
#| fig-cap: "API response times over 24 hours"

import matplotlib.pyplot as plt
plt.plot(timestamps, response_times)
plt.xlabel("Time")
plt.ylabel("Response Time (ms)")
\`\`\`

As shown in @fig-response-times, peak hours are problematic.

## Recommendations

Based on the analysis, we should:

1. Scale up during {python} peak_hour
2. Add caching for {python} len(slow_endpoints) endpoints
```

**Benefits for Bengal users:**

✅ **Write docs in plain markdown** - No special tools
✅ **Execute code inline** - Like notebooks, but cleaner
✅ **Version control friendly** - Meaningful diffs
✅ **Professional output** - Publication-quality rendering
✅ **Inline values** - `` `{python} expr` `` in text
✅ **Cross-references** - Link figures, tables, sections
✅ **No execution state issues** - Linear execution guaranteed

---

## Implementation for Bengal

### Phase 1: Quarto Support (3-5 days)

```python
# bengal/rendering/parsers/quarto.py
class QuartoParser(BaseMarkdownParser):
    """
    Parser for Quarto (.qmd) files.

    Quarto files are markdown with executable code blocks.
    We execute them via Quarto CLI and render the output.
    """

    def parse(self, content: str, metadata: dict) -> str:
        # 1. Write .qmd content to temp file
        # 2. Run: quarto render temp.qmd --to html
        # 3. Extract body HTML
        # 4. Return rendered output
        pass
```

**Discovery changes:**
```python
def _is_content_file(self, file_path: Path) -> bool:
    content_extensions = {".md", ".markdown", ".qmd"}  # Add .qmd
    return file_path.suffix.lower() in content_extensions
```

**Benefits:**
- ✅ Quarto handles execution
- ✅ We just render the output
- ✅ Users get modern executable docs
- ✅ Git-friendly workflow

### Phase 2: Direct Execution (Advanced)

Instead of shelling out to Quarto CLI, parse and execute directly:

```python
# Parse .qmd ourselves
# Execute Python/R/Julia code blocks
# Render inline expressions
# Generate cross-references
```

But honestly, **let Quarto do the work**. They've solved the hard problems.

---

## The Format Ladder (by modernity)

```
📊 2011: Jupyter Notebooks (.ipynb)
       ↓
       Still useful, but showing age
       JSON, merge conflicts, binary outputs

📊 2020: MyST Markdown (.md with kernels)
       ↓
       Better: plain text, but still tied to Jupyter

📊 2022: Quarto (.qmd)                    ← MODERN ✨
       ↓
       Best of all worlds:
       - Plain text
       - Multi-language
       - Professional output
       - Industry backing
       - Git-friendly

📊 2024: Marimo (.py reactive)
       ↓
       Future? Reactive, pure Python
       Too new to recommend yet
```

---

## Recommendations for Bengal

### Short Term: Support Jupyter Notebooks
- ✅ Large existing ecosystem
- ✅ Many users have `.ipynb` files
- ✅ Quick to implement
- ⚠️ But acknowledge it's legacy support

### Medium Term: Add Quarto (.qmd) Support 🎯
- ✅ **This is the modern format**
- ✅ Plain text, git-friendly
- ✅ Professional output
- ✅ Growing industry adoption
- ✅ Multi-language support
- ✅ Makes Bengal competitive with Quarto's built-in site generator

### Long Term: Watch Marimo
- Reactive notebooks in pure Python
- Still very new (2024)
- Could be the future
- Wait for ecosystem to mature

---

## Example: Modern Doc with Quarto

```markdown
---
title: "Bengal SSG Performance Analysis"
date: 2024-10-14
format:
  bengal-html:
    theme: dark
    toc: true
execute:
  echo: false  # Hide code, show outputs only
---

# Build Performance

Our latest optimizations improved build time by
{python} f"{(old_time - new_time) / old_time * 100:.1f}%".

\`\`\`{python}
#| label: fig-build-times
#| fig-cap: "Build time comparison"

import pandas as pd
import plotly.express as px

data = pd.DataFrame({
    'version': ['v0.1.0', 'v0.2.0', 'v0.3.0'],
    'build_time': [45, 38, 22]
})

fig = px.bar(data, x='version', y='build_time')
fig.show()
\`\`\`

See @fig-build-times for the trend.

## Key Improvements

The {python} len(improvements) optimizations were:

\`\`\`{python}
improvements = [
    "Parallel rendering",
    "Template caching",
    "Incremental builds"
]

for i, imp in enumerate(improvements, 1):
    print(f"{i}. {imp}")
\`\`\`
```

**Output:** Professional HTML with:
- Inline calculated values
- Interactive plots
- Cross-referenced figures
- Hidden code (clean presentation)
- All from plain text source

---

## Competitive Analysis

### Quarto's Built-in Site Generator

Quarto has its own SSG:
```bash
quarto create-project mysite --type website
```

**Features:**
- Multi-page sites
- Navigation
- Search
- Themes

**Why Bengal + Quarto > Quarto alone?**

Bengal adds:
✅ **Better architecture** - Your clean separation of concerns
✅ **Plugin system** - Custom directives, extensions
✅ **Asset pipeline** - SCSS, TypeScript, bundling
✅ **Advanced features** - Cross-references, link validation, health checks
✅ **Python-native** - Not a CLI wrapper around Pandoc
✅ **Performance** - Incremental builds, caching
✅ **Flexibility** - Not opinionated about structure

**Positioning:**
"Bengal: A modern SSG that supports executable docs via Quarto, with better architecture and more flexibility than Quarto's built-in site generator."

---

## Summary

### The Modern Stack

❌ **Old:** Jupyter Notebooks (.ipynb)
  - JSON format
  - Git-unfriendly
  - Legacy

✅ **Modern:** Quarto Documents (.qmd)
  - Plain markdown
  - Git-friendly  
  - Multi-language
  - Professional output
  - Industry momentum

🔮 **Future:** Marimo (reactive .py)
  - Pure Python
  - Reactive execution
  - Too new to bet on

### Action Items

1. **Support .ipynb** (for legacy content)
   - Via directive: `{notebook}`
   - 2-3 days work

2. **Support .qmd** (for modern executable docs) 🎯
   - Via parser: `QuartoParser`
   - 3-5 days work
   - **This is the differentiator**

3. **Market as:** "Modern SSG for technical documentation with native support for executable documents"

### Why This Matters

Quarto is where the industry is going:
- Posit (RStudio) backing
- Used by data science teams at Netflix, Airbnb, etc.
- Academic adoption (computational research papers)
- Book publishing (O'Reilly exploring)

**Bengal supporting Quarto = instant credibility in data science/ML docs space.**

---

## Verdict

**Yes, notebooks are antiquated. Quarto (.qmd) is the modern alternative.**

Build both:
1. Notebook support (backward compatibility)
2. Quarto support (future-facing)

Position Bengal as: **"The modern SSG that speaks both legacy (notebooks) and modern (Quarto) executable documentation formats."**

This makes you competitive with:
- Jupyter Book (notebooks only)
- Quarto's SSG (less flexible)
- MkDocs (no executable docs)

**You'd be the only SSG with both!** 🚀
