# Marimo Support Implementation Plan

## Goal

Enable executable Python code blocks in Bengal documentation using Marimo's reactive notebook system.

## Approach: Marimo Islands (Cell-Level Embedding)

Use Marimo's `MarimoIslandGenerator` to embed individual Python cells in markdown:

```markdown
# Sales Analysis

\```{marimo}
import pandas as pd
data = pd.read_csv("sales.csv")
data.head()
\```

Total revenue: \```{marimo-inline}
f"${data.amount.sum():,.2f}"
\```
```

## Why This Approach?

✅ **Granular control** - Embed specific cells, not full notebooks
✅ **Narrative flow** - Python execution inline with markdown prose
✅ **Modern** - Leverages Marimo's cutting-edge reactive system
✅ **Git-friendly** - Plain markdown with code blocks
✅ **Static output** - No server required in production
✅ **Reactive during dev** - Can develop with Marimo, export static for docs

## Architecture

### Three Layers

1. **Directive Layer** - Mistune plugin for `{marimo}` syntax
2. **Execution Layer** - MarimoIslandGenerator for running Python
3. **Rendering Layer** - HTML output with styling

```
Markdown                  Directive                Execution              Output
─────────                 ─────────                ─────────              ──────
```{marimo}          →    MarimoCellDirective  →   MarimoIslandGen    →   HTML
import pandas         →    parse()              →   .add_code()        →   <div>
data.head()           →                         →   .build()           →   table
```                   →                         →   .render_html()     →   </div>
```

## Implementation Phases

### Phase 1: Basic Cell Directive (Day 1-2) 🎯

**File**: `bengal/rendering/plugins/directives/marimo.py`

```python
from mistune.directives import DirectivePlugin

class MarimoCellDirective(DirectivePlugin):
    """
    Embed executable Python cells using Marimo.

    Syntax:
        ```{marimo}
        import pandas as pd
        pd.DataFrame({"x": [1, 2, 3]})
        ```

    Features:
    - Execute Python code at build time
    - Render outputs (text, tables, plots)
    - Cache results for fast rebuilds
    """

    def __init__(self):
        self.cell_counter = 0
        self.generators = {}  # Per-page generators

    def parse(self, block, m, state):
        """Parse {marimo} directive."""
        code = self.parse_content(m)
        options = self.parse_options(m)

        # Execute and render
        html = self._execute_cell(
            code,
            show_code=options.get('show-code', 'true') == 'true',
            page_id=state.env.get('page_id', 'main')
        )

        return {
            "type": "marimo_cell",
            "attrs": {
                "html": html,
                "cell_id": self.cell_counter
            }
        }

    def _execute_cell(self, code: str, show_code: bool, page_id: str) -> str:
        """Execute Python code and return HTML."""
        try:
            from marimo import MarimoIslandGenerator

            # Get or create generator for this page
            if page_id not in self.generators:
                self.generators[page_id] = MarimoIslandGenerator(
                    app_id=page_id
                )

            generator = self.generators[page_id]

            # Add code cell
            generator.add_code(
                code=code,
                display_code=show_code,
                display_output=True
            )

            self.cell_counter += 1

            # Build and render
            generator.build()
            return generator.render_html()

        except ImportError:
            return '''
                <div class="marimo-error">
                    <strong>Error:</strong> Marimo not installed.
                    Install with: <code>pip install marimo</code>
                </div>
            '''
        except Exception as e:
            return f'''
                <div class="marimo-error">
                    <strong>Execution Error:</strong> {e}
                    <pre>{code}</pre>
                </div>
            '''

    def __call__(self, directive, md):
        """Register with Mistune."""
        directive.register("marimo", self.parse)

        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("marimo_cell", render_marimo_cell)


def render_marimo_cell(renderer, html: str, cell_id: int) -> str:
    """Render Marimo cell output."""
    return f'<div class="marimo-cell" data-cell="{cell_id}">{html}</div>'
```

**Register Directive**:
```python
# bengal/rendering/plugins/directives/__init__.py
from .marimo import MarimoCellDirective

def create_documentation_directives():
    def plugin_documentation_directives(md):
        directive = FencedDirective([
            # ... existing directives ...
            MarimoCellDirective(),  # Add Marimo support
        ])
        return directive(md)
    return plugin_documentation_directives
```

**Usage**:
```markdown
# Data Analysis

\```{marimo}
import pandas as pd
data = pd.read_csv("data.csv")
data.head()
\```
```

### Phase 2: Enhanced Features (Day 3)

**Options Support**:
```markdown
\```{marimo}
:show-code: false
:cache: true
:label: fig-sales

import matplotlib.pyplot as plt
plt.plot([1, 2, 3])
\```
```

**Implementation**:
```python
def parse(self, block, m, state):
    code = self.parse_content(m)
    options = self.parse_options(m)

    # Parse options
    show_code = options.get('show-code', 'true') == 'true'
    use_cache = options.get('cache', 'true') == 'true'
    label = options.get('label')

    # Check cache
    if use_cache and label:
        cached = self._get_from_cache(label)
        if cached:
            return cached

    # Execute
    html = self._execute_cell(code, show_code, page_id)

    # Store in cache
    if use_cache and label:
        self._store_in_cache(label, html)

    return {"type": "marimo_cell", "attrs": {"html": html}}
```

### Phase 3: Inline Expressions (Day 4)

**Inline Python values**:
```markdown
Total revenue: `{marimo} data.amount.sum()`

That's a `{marimo} (revenue / 1000000):.1f`M increase!
```

**Implementation**:
```python
class MarimoInlineDirective(DirectivePlugin):
    """Inline Python expressions."""

    def parse(self, inline, m, state):
        expr = self.parse_content(m)

        # Execute expression
        result = self._eval_expression(expr)

        return {
            "type": "marimo_inline",
            "attrs": {"value": str(result)}
        }

    def _eval_expression(self, expr: str) -> Any:
        """Evaluate Python expression in page context."""
        # TODO: Share namespace across cells in same page
        pass
```

### Phase 4: Advanced Features (Day 5+)

**A. Cell Dependencies**
```markdown
\```{marimo}
:depends: data, analysis
:label: visualization

import matplotlib.pyplot as plt
plt.scatter(data.x, analysis.predictions)
\```
```

**B. Conditional Execution**
```markdown
\```{marimo}
:execute: ${BUILD_ENV} == "production"

# Only run in production builds
expensive_computation()
\```
```

**C. Error Handling**
```markdown
\```{marimo}
:on-error: show
:fallback: "Data unavailable"

# Show error or fallback if this fails
data = fetch_live_data()
\```
```

**D. Interactive Widgets** (Advanced)
```markdown
\```{marimo}
:interactive: true

import marimo as mo
slider = mo.ui.slider(0, 100)
slider
\```
```

Requires Marimo JS runtime in browser.

## Directory Structure

```
bengal/
├── rendering/
│   └── plugins/
│       └── directives/
│           ├── __init__.py
│           ├── marimo.py          ← New file
│           ├── admonitions.py
│           ├── tabs.py
│           └── ...
└── themes/
    └── default/
        └── assets/
            └── css/
                └── marimo.css      ← Styling for cells
```

## Dependencies

```toml
# pyproject.toml
[project.optional-dependencies]
marimo = [
    "marimo>=0.1.0",
]

# Install with:
# pip install bengal[marimo]
```

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_marimo_directive.py

def test_marimo_cell_execution():
    """Test basic cell execution."""
    directive = MarimoCellDirective()

    code = """
import pandas as pd
pd.DataFrame({"x": [1, 2, 3]})
"""

    html = directive._execute_cell(code, show_code=True, page_id="test")
    assert "<table" in html  # DataFrame rendered as table
    assert "pandas" in html  # Code is shown

def test_marimo_cell_error_handling():
    """Test error handling."""
    directive = MarimoCellDirective()

    code = "undefined_variable"

    html = directive._execute_cell(code, show_code=True, page_id="test")
    assert "marimo-error" in html
```

### Integration Tests
```python
# tests/integration/test_marimo_rendering.py

def test_marimo_in_markdown():
    """Test Marimo cells in full markdown rendering."""
    content = """
# Analysis

```{marimo}
import pandas as pd
pd.DataFrame({"x": [1, 2, 3]})
```
"""

    parser = MistuneParser()
    html = parser.parse(content, {})

    assert "marimo-cell" in html
    assert "<table" in html
```

## Example Usage

### Basic Data Analysis
```markdown
---
title: "Sales Report Q4 2024"
---

# Sales Performance

Let's analyze our quarterly sales:

\```{marimo}
import pandas as pd
import matplotlib.pyplot as plt

# Load data
sales = pd.read_csv("data/q4_sales.csv")
sales.head()
\```

Total revenue: \```{marimo-inline}
f"${sales.amount.sum():,.2f}"
\```

## Regional Breakdown

\```{marimo}
:show-code: false

regional = sales.groupby('region')['amount'].sum()
regional.plot(kind='bar')
plt.title("Sales by Region")
\```

Top performer: \```{marimo-inline}
regional.idxmax()
\``` with \```{marimo-inline}
f"${regional.max():,.2f}"
\```.
```

### API Documentation
```markdown
# Performance Benchmarks

\```{marimo}
import requests
import time

# Benchmark API endpoint
start = time.time()
response = requests.get("https://api.example.com/users")
latency = (time.time() - start) * 1000

f"API Latency: {latency:.2f}ms"
\```

Current response time: \```{marimo-inline} f"{latency:.0f}ms" \```
```

### Tutorial with Live Code
```markdown
# Pandas Tutorial

## Loading Data

\```{marimo}
import pandas as pd

# Load CSV
df = pd.read_csv("example.csv")
print(f"Loaded {len(df)} rows")
df.head()
\```

## Filtering

\```{marimo}
:depends: df

# Filter for high-value transactions
high_value = df[df.amount > 1000]
print(f"Found {len(high_value)} high-value transactions")
high_value.describe()
\```
```

## Styling

```css
/* themes/default/assets/css/marimo.css */

.marimo-cell {
    margin: 1.5rem 0;
    border-radius: 8px;
    overflow: hidden;
}

.marimo-cell pre {
    background: var(--code-bg);
    padding: 1rem;
    overflow-x: auto;
}

.marimo-cell table {
    width: 100%;
    border-collapse: collapse;
}

.marimo-cell table th,
.marimo-cell table td {
    padding: 0.5rem;
    border: 1px solid var(--border-color);
}

.marimo-error {
    background: #fee;
    border-left: 4px solid #c33;
    padding: 1rem;
    margin: 1rem 0;
}

.marimo-error code {
    background: #fdd;
}
```

## Caching Strategy

### Build-Time Execution
```python
# bengal/cache/marimo_cache.py

class MarimoCache:
    """Cache Marimo cell executions."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir / "marimo"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, cell_id: str, code: str) -> str | None:
        """Get cached cell output."""
        cache_key = self._hash(code)
        cache_file = self.cache_dir / f"{cell_id}_{cache_key}.html"

        if cache_file.exists():
            return cache_file.read_text()
        return None

    def set(self, cell_id: str, code: str, html: str):
        """Store cell output."""
        cache_key = self._hash(code)
        cache_file = self.cache_dir / f"{cell_id}_{cache_key}.html"
        cache_file.write_text(html)

    def _hash(self, code: str) -> str:
        """Generate cache key from code."""
        import hashlib
        return hashlib.sha256(code.encode()).hexdigest()[:16]
```

### Incremental Builds
- Only re-execute cells when code changes
- Track dependencies between cells
- Invalidate downstream cells when dependency changes

## Error Handling

### Graceful Degradation
```python
def _execute_cell(self, code: str, show_code: bool) -> str:
    """Execute with graceful error handling."""
    try:
        # Try execution
        return self._do_execute(code)

    except ImportError as e:
        # Missing dependency
        return self._render_error(
            "Missing Dependency",
            f"Install required package: {e.name}",
            code
        )

    except SyntaxError as e:
        # Code syntax error
        return self._render_error(
            "Syntax Error",
            str(e),
            code,
            line=e.lineno
        )

    except Exception as e:
        # Runtime error
        return self._render_error(
            "Execution Error",
            str(e),
            code
        )

def _render_error(self, title: str, message: str, code: str, line: int = None):
    """Render user-friendly error."""
    line_info = f" (line {line})" if line else ""
    return f'''
        <div class="marimo-error">
            <strong>{title}{line_info}:</strong> {message}
            <details>
                <summary>Show code</summary>
                <pre><code>{code}</code></pre>
            </details>
        </div>
    '''
```

## Security Considerations

### Sandboxing
```python
# Option 1: Restricted execution (basic)
ALLOWED_IMPORTS = {'pandas', 'numpy', 'matplotlib', 'plotly', 'seaborn'}

def _validate_code(code: str):
    """Check for dangerous operations."""
    dangerous = ['os.system', 'subprocess', 'eval', 'exec', '__import__']
    for pattern in dangerous:
        if pattern in code:
            raise SecurityError(f"Dangerous operation not allowed: {pattern}")

# Option 2: Containerized execution (advanced)
# Execute in Docker container with resource limits
```

### Resource Limits
```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Cell execution exceeded time limit")

def _execute_with_timeout(code: str, timeout: int = 30):
    """Execute with timeout."""
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)

    try:
        result = execute(code)
        signal.alarm(0)  # Cancel alarm
        return result
    except TimeoutError:
        return "<div class='error'>Execution timeout (>30s)</div>"
```

## Documentation

### User Guide
Create `docs/features/marimo-cells.md`:

```markdown
# Executable Python Cells

Bengal supports executable Python code blocks using Marimo.

## Basic Usage

\```{marimo}
import pandas as pd
data = pd.read_csv("data.csv")
data.head()
\```

## Options

- `show-code` - Show/hide code (default: true)
- `cache` - Cache execution results (default: true)
- `label` - Cell identifier for caching

## Examples

See [Examples Gallery](/examples/marimo-cells)
```

## Timeline

### Week 1: Core Implementation
- Day 1-2: Basic directive + MarimoIslandGenerator integration
- Day 3: Options support + caching
- Day 4: Testing + error handling
- Day 5: Documentation + examples

### Week 2: Polish & Enhancement
- Day 6-7: Styling + theme integration
- Day 8: Inline expressions
- Day 9: Advanced features
- Day 10: Performance optimization

## Success Metrics

✅ **Functionality**
- [ ] Can execute Python code blocks
- [ ] Renders tables, plots, text output
- [ ] Shows/hides code as requested
- [ ] Caches results for fast rebuilds

✅ **User Experience**
- [ ] Clear error messages
- [ ] Fast execution (<2s per cell)
- [ ] Intuitive syntax
- [ ] Good documentation

✅ **Quality**
- [ ] >80% test coverage
- [ ] Handles errors gracefully
- [ ] No security vulnerabilities
- [ ] Works with existing themes

## Next Steps

1. ✅ Create implementation plan (this document)
2. ⏳ Build Phase 1: Basic directive
3. ⏳ Test with example docs
4. ⏳ Get user feedback
5. ⏳ Iterate and enhance

Ready to start building! 🚀
