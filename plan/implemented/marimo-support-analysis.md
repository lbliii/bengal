# Marimo Support Analysis

## What is Marimo?

**Marimo** (2024) is a reactive Python notebook system that solves notebook problems:

### Key Innovations
✅ **Pure Python files** - Not JSON, just `.py`
✅ **Reactive execution** - Like Observable.js but for Python
✅ **No hidden state** - Execution order is deterministic
✅ **Git-friendly** - Standard Python files
✅ **Built-in editor** - Modern web UI

### File Format

A Marimo notebook is just a Python file:

```python
import marimo

__generated_with = "0.1.0"

app = marimo.App()

@app.cell
def __():
    import pandas as pd
    import altair as alt
    return pd, alt

@app.cell
def __(pd):
    # This cell re-runs automatically when pd changes
    data = pd.read_csv("data.csv")
    return data,

@app.cell
def __(data, alt):
    # This re-runs when data changes
    chart = alt.Chart(data).mark_bar().encode(
        x='category',
        y='value'
    )
    return chart,

@app.cell
def __(chart):
    # Display the chart
    chart
```

### Reactive Execution Model

```
Cell 1: Import libraries
  ↓
Cell 2: Load data (depends on Cell 1)
  ↓
Cell 3: Create chart (depends on Cell 1 & 2)
  ↓
Cell 4: Display chart (depends on Cell 3)
```

When Cell 2 changes, Cells 3 and 4 automatically re-run. No "Restart & Run All" needed.

---

## Does Marimo Export to HTML?

Let me check the documentation...

### Export Capabilities

Marimo has several export options:

```bash
# Run as interactive app
marimo run notebook.py

# Export to static HTML
marimo export html notebook.py -o output.html

# Export to script
marimo export script notebook.py -o script.py

# Export to Jupyter notebook
marimo export ipynb notebook.py -o notebook.ipynb
```

### HTML Export Details

**Yes!** Marimo can export to static HTML:

```bash
marimo export html analysis.py -o analysis.html
```

This generates:
- ✅ Standalone HTML file
- ✅ All outputs rendered
- ✅ Interactive elements (if any)
- ✅ Styled output
- ❌ Not reactive (static snapshot)

The HTML export is **static** - it shows the last execution state, but doesn't re-run code.

---

## How Would Bengal Support It?

### Option 1: Parser-Based (Like Notebooks)

Treat `.py` Marimo files as content:

```python
# bengal/rendering/parsers/marimo.py
import subprocess
import tempfile
from pathlib import Path

class MarimoParser(BaseMarkdownParser):
    """
    Parser for Marimo reactive notebooks (.py files).

    Marimo files are pure Python with @app.cell decorators.
    We execute them via Marimo CLI and render the HTML output.
    """

    def parse(self, content: str, metadata: dict) -> str:
        """
        Execute Marimo notebook and get HTML output.

        Steps:
        1. Write content to temp .py file
        2. Run: marimo export html temp.py
        3. Read generated HTML
        4. Extract body content
        5. Return rendered output
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            temp_file = Path(f.name)

        try:
            # Execute via Marimo CLI
            output_html = temp_file.with_suffix('.html')

            result = subprocess.run(
                ['marimo', 'export', 'html', str(temp_file), '-o', str(output_html)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return f'<div class="marimo-error">Execution failed: {result.stderr}</div>'

            # Read generated HTML
            html_content = output_html.read_text()

            # Extract body (remove HTML/head/body tags to embed in page)
            body = self._extract_body(html_content)

            return f'<div class="marimo-notebook">{body}</div>'

        finally:
            # Cleanup
            temp_file.unlink(missing_ok=True)
            if output_html.exists():
                output_html.unlink()

    def _extract_body(self, html: str) -> str:
        """Extract content from <body> tag."""
        # Simple extraction - could use BeautifulSoup for robustness
        import re
        match = re.search(r'<body[^>]*>(.*)</body>', html, re.DOTALL | re.IGNORECASE)
        return match.group(1) if match else html
```

**Discovery:**
```python
# bengal/discovery/content_discovery.py
def _is_content_file(self, file_path: Path) -> bool:
    # Check if .py file is a Marimo notebook
    if file_path.suffix == '.py':
        # Read first few lines to detect marimo
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        if 'import marimo' in content[:500] and '@app.cell' in content:
            return True

    return file_path.suffix.lower() in {".md", ".markdown", ".qmd", ".ipynb"}
```

**Pros:**
✅ Marimo notebooks as pages (like markdown files)
✅ Full execution on build
✅ Reactive features preserved in development
✅ Clean separation (parsing vs content)

**Cons:**
⚠️ Requires Marimo CLI installed
⚠️ Execution at build time (slow)
⚠️ Static output (not reactive in docs)

---

### Option 2: Directive-Based (Embedded)

Embed Marimo notebooks in markdown pages:

```python
# bengal/rendering/plugins/directives/marimo.py
from mistune.directives import DirectivePlugin

class MarimoDirective(DirectivePlugin):
    """
    Embed Marimo reactive notebooks in markdown.

    Syntax:
        ```{marimo} path/to/notebook.py
        :show-code: true
        :execute: true
        ```
    """

    def parse(self, block, m, state):
        marimo_path = self.parse_title(m)
        options = self.parse_options(m)

        # Load and execute Marimo notebook
        notebook_html = self._execute_marimo(
            marimo_path,
            show_code=options.get('show-code') == 'true',
            execute=options.get('execute', 'true') == 'true'
        )

        return {
            "type": "marimo_notebook",
            "attrs": {
                "html": notebook_html,
                "path": marimo_path,
            }
        }

    def _execute_marimo(self, path: str, show_code: bool, execute: bool) -> str:
        """Execute Marimo notebook and get HTML."""
        import subprocess
        from pathlib import Path

        notebook_file = Path(path)
        output_html = Path(f".bengal-cache/marimo/{notebook_file.stem}.html")
        output_html.parent.mkdir(parents=True, exist_ok=True)

        # Export to HTML
        result = subprocess.run(
            ['marimo', 'export', 'html', str(notebook_file), '-o', str(output_html)],
            capture_output=True,
            timeout=30
        )

        if result.returncode != 0:
            return f'<div class="error">Failed to execute {path}</div>'

        return output_html.read_text()

    def __call__(self, directive, md):
        directive.register("marimo", self.parse)
        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("marimo_notebook", render_marimo)

def render_marimo(renderer, html: str, path: str) -> str:
    return f'<div class="embedded-marimo" data-source="{path}">{html}</div>'
```

**Usage:**
```markdown
# Data Analysis Tutorial

Let's explore the data:

\```{marimo} notebooks/analysis.py
:show-code: true
\```

The chart above shows...
```

**Pros:**
✅ Embed in markdown (narrative control)
✅ Multiple notebooks per page
✅ Consistent with other directives
✅ Clean authoring experience

**Cons:**
⚠️ Requires Marimo CLI
⚠️ Build-time execution
⚠️ Static output (loses reactivity)

---

### Option 3: Interactive Embedding (Advanced)

**Challenge:** Marimo's killer feature is **reactivity**. Static HTML export loses this.

**Solution:** Embed the interactive Marimo app:

```python
class MarimoInteractiveDirective(DirectivePlugin):
    """
    Embed interactive Marimo notebooks using iframe.

    Requires running Marimo server during dev/deploy.
    """

    def parse(self, block, m, state):
        marimo_path = self.parse_title(m)
        options = self.parse_options(m)

        # Generate iframe to Marimo server
        iframe_html = f'''
        <iframe
            src="/marimo/{marimo_path}"
            width="100%"
            height="{options.get('height', '600')}px"
            frameborder="0"
            class="marimo-interactive">
        </iframe>
        '''

        return {
            "type": "marimo_interactive",
            "attrs": {"html": iframe_html}
        }
```

**Architecture:**
```
Bengal Dev Server (port 8000)
  ├─ Static pages (HTML)
  └─ /marimo/* → Proxy to Marimo server (port 2718)

Marimo Server (port 2718)
  └─ Serves interactive notebooks
```

**Pros:**
✅ **Preserves reactivity** - Full Marimo interactivity
✅ Live editing during development
✅ True notebook experience

**Cons:**
❌ **Complex deployment** - Need Marimo server in production
❌ Can't export to static HTML
❌ Requires iframe (security/styling issues)

---

## Comparison: Marimo vs Jupyter vs Quarto

| Feature | Jupyter | Marimo | Quarto |
|---------|---------|--------|--------|
| **File Format** | JSON | Python | Markdown |
| **Git-Friendly** | ❌ | ✅ | ✅ |
| **Reactive** | ❌ | ✅ | ❌ |
| **Multi-Language** | ✅ | ❌ Python only | ✅ |
| **HTML Export** | ✅ nbconvert | ✅ CLI | ✅ CLI |
| **Interactive Export** | ❌ | ⚠️ (needs server) | ⚠️ (limited) |
| **Maturity** | ✅ 13 years | ⚠️ 1 year | ✅ 3 years |
| **Ecosystem** | ✅ Huge | 🔨 Growing | ✅ Growing |

---

## Marimo-Specific Considerations

### 1. Pure Python Detection

How do we know a `.py` file is a Marimo notebook?

```python
def is_marimo_notebook(file_path: Path) -> bool:
    """Detect if Python file is a Marimo notebook."""
    if file_path.suffix != '.py':
        return False

    try:
        content = file_path.read_text(encoding='utf-8')

        # Check for Marimo markers
        has_import = 'import marimo' in content
        has_app = 'app = marimo.App()' in content
        has_cells = '@app.cell' in content

        return has_import and (has_app or has_cells)
    except:
        return False
```

### 2. Execution Model

Marimo notebooks **must be executed** to generate output. Options:

**A. Build-time execution** (Recommended)
- Execute during `bengal site build`
- Cache results
- Fast rebuilds
- Static output

**B. On-demand execution**
- Execute when page is requested
- Slower page loads
- Fresh results
- Requires Marimo runtime

**C. Pre-executed notebooks**
- Developer runs `marimo export html` manually
- Bengal just includes the HTML
- No execution needed
- Manual workflow

### 3. Dependency Management

Marimo notebooks have Python dependencies:

```python
# analysis.py
import marimo
app = marimo.App()

@app.cell
def __():
    import pandas as pd  # Needs pandas installed
    import altair as alt  # Needs altair installed
    return pd, alt
```

**Challenge:** Bengal build must have these dependencies.

**Solutions:**
1. Document in notebook frontmatter:
   ```python
   # /// script
   # dependencies = ["pandas", "altair"]
   # ///
   ```

2. Use virtual environments per notebook
3. Container-based execution (Docker)

---

## Recommended Approach for Bengal

### Phase 1: Basic Support (Directive)

Start with **Option 2** (Directive-based):

```markdown
\```{marimo} notebooks/analysis.py
\```
```

**Why?**
- ✅ Simple to implement (2-3 days)
- ✅ Consistent with other directives
- ✅ No parser changes needed
- ✅ Embeddable in markdown
- ⚠️ Loses reactivity (static export)

**Implementation:**
1. Create `MarimoDirective` (like `NotebookDirective`)
2. Call `marimo export html` during parsing
3. Embed HTML in page
4. Cache results

### Phase 2: Standalone Pages (Parser)

Add **Option 1** (Parser-based) if there's demand:

```
content/
└── analyses/
    ├── sales.py        ← Marimo notebook as page
    └── performance.py  ← Marimo notebook as page
```

**Why?**
- For notebook collections
- When notebook IS the content
- Less common use case

### Phase 3: Interactive (Future)

**Only if there's strong demand** for preserving reactivity:

- Proxy to Marimo server during dev
- Explore static alternatives (WASM?)
- Wait for Marimo to mature

---

## The Reactivity Problem

**The Issue:** Marimo's killer feature is **reactivity**, but that requires:
1. Running Python code
2. Maintaining execution state
3. Re-executing on changes

**Static HTML export loses this.**

### Possible Solutions

**A. Accept Static Export** ✅
- Most documentation doesn't need reactivity
- Showing outputs is enough
- Simplest to implement

**B. Marimo Server Integration** ⚠️
- Keep reactivity
- Complex deployment
- Not suitable for static sites

**C. Wait for WebAssembly** 🔮
- Marimo could potentially run in browser via Pyodide
- Pure client-side execution
- Future technology

**D. Hybrid Approach** 🎯
- Static export for production
- Interactive during development
- Best of both worlds

---

## Comparison: Marimo vs Other Formats

For **Bengal's use case** (documentation site generator):

### Jupyter Notebooks
✅ **Mature ecosystem** - 13 years, battle-tested
✅ **Large existing content** - Lots of `.ipynb` files
✅ **Easy export** - nbconvert is stable
⚠️ **Git-unfriendly** - JSON, merge conflicts

### Quarto (.qmd)
✅ **Plain text** - Markdown-based, git-friendly
✅ **Multi-language** - Python, R, Julia
✅ **Professional output** - Publication-quality
✅ **Industry adoption** - Posit backing
✅ **Best for docs** - Designed for documentation

### Marimo (.py)
✅ **Pure Python** - Developers love this
✅ **Git-friendly** - Standard .py files
✅ **Reactive** - Interactive development
⚠️ **Very new** - 1 year old, small ecosystem
⚠️ **Python-only** - No R, Julia, etc.
⚠️ **Loses reactivity** - When exported to static HTML

---

## Strategic Recommendation

### Priority Order for Bengal

1. **Quarto (.qmd)** 🥇
   - Most mature modern format
   - Plain text, git-friendly
   - Multi-language support
   - Industry momentum
   - **Perfect for documentation**

2. **Jupyter Notebooks (.ipynb)** 🥈
   - Backward compatibility
   - Large ecosystem
   - Easy to implement
   - **Support legacy content**

3. **Marimo (.py)** 🥉
   - Interesting but very new
   - Python-only
   - Loses reactivity in static export
   - **Wait and watch**

### Why This Order?

**Quarto** is what you build first because:
- It's designed for exactly what Bengal does (documentation sites)
- Plain text = git-friendly = modern workflow
- Multi-language = broader audience
- Mature enough to bet on

**Jupyter** is table stakes:
- Too much existing content to ignore
- Easy to implement
- Users expect it

**Marimo** is interesting but premature:
- Too new (1 year old)
- Small ecosystem
- **Main benefit (reactivity) is lost in static export**
- Could be great in 2-3 years

---

## Implementation Plan

### If You Want Marimo Support

**Directive-Based** (2-3 days):

```python
# bengal/rendering/plugins/directives/marimo.py

from mistune.directives import DirectivePlugin
import subprocess
from pathlib import Path

class MarimoDirective(DirectivePlugin):
    def parse(self, block, m, state):
        notebook_path = self.parse_title(m)

        # Execute and cache
        html = self._execute_marimo(notebook_path)

        return {
            "type": "marimo_embed",
            "attrs": {"html": html}
        }

    def _execute_marimo(self, path: str) -> str:
        """Execute via CLI and return HTML."""
        cache_file = Path(f".bengal-cache/marimo/{Path(path).stem}.html")

        # Check cache first
        if cache_file.exists():
            return cache_file.read_text()

        # Execute
        subprocess.run([
            'marimo', 'export', 'html',
            path, '-o', str(cache_file)
        ])

        return cache_file.read_text()
```

**Usage:**
```markdown
# My Analysis

\```{marimo} notebooks/analysis.py
\```
```

**Deps:**
```toml
[project.optional-dependencies]
marimo = ["marimo>=0.1.0"]
```

---

## Verdict

**Marimo is cool, but not ready for prime time in Bengal.**

**Reasons:**
1. **Too new** - Only 1 year old, ecosystem still forming
2. **Loses key feature** - Reactivity is lost in static export
3. **Python-only** - Quarto supports multiple languages
4. **Small audience** - Most Python users still use Jupyter
5. **Can wait** - Support later if it gains traction

**Better strategy:**
1. Build Quarto support first (modern, mature, multi-language)
2. Build Jupyter support second (backward compatibility)
3. Watch Marimo and add support in 1-2 years if it takes off

**Unless...** you personally love Marimo and want to dog-food it! Then build support as a way to:
- Learn Marimo deeply
- Give feedback to Marimo team
- Be an early adopter
- Potentially influence Marimo's direction

But from a "what makes sense for Bengal users" perspective: **Quarto > Jupyter > Marimo**

Want me to prototype Quarto or Jupyter support instead? Those seem more immediately valuable! 🚀
