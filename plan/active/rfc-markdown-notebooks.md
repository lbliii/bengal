# RFC: Markdown-Native Notebook Format

**Status**: Draft  
**Created**: 2025-10-29  
**Author**: System (based on user proposal)  

---

## Executive Summary

Introduce a markdown-native notebook format (`.mdnb` or `.bengal`) that allows sequential executable code cells without Jupyter's JSON overhead. This format prioritizes human readability, version control friendliness, and Bengal's markdown-first philosophy while enabling literate programming and computational documentation.

**Key Innovation**: Stay true to markdown syntax while supporting stateful, sequential code execution—combining the best of Jupytext's text-based approach with Bengal's existing rendering pipeline.

---

## Problem Statement

### Current State

Bengal supports executable code through the Marimo directive:

```markdown
```{marimo}
:show-code: true
import pandas as pd
pd.DataFrame({"x": [1, 2, 3]})
```
```

**Limitations**:
1. Each `{marimo}` block is isolated—no shared state between cells
2. Requires explicit directive syntax for every executable block
3. No first-class "notebook" concept in Bengal's content types
4. Manual orchestration needed for sequential execution
5. Verbose for data analysis workflows with many cells

### Pain Points

**For Data Scientists**:
- Want literate programming (narrative + code + outputs)
- Need sequential execution with shared state (like Jupyter)
- Hate JSON notebook formats (merge conflicts, version control)

**For Documentation Authors**:
- Want to include live examples that auto-update
- Need to show code and output without manual screenshots
- Want markdown simplicity with computational power

**For Bengal Users**:
- Current Marimo directive is powerful but not designed for multi-cell workflows
- No way to mark a content file as "executable document"
- Missing incremental execution and caching for notebook-style content

### Evidence

**Existing file**: `bengal/rendering/plugins/directives/marimo.py`
```python
# Each page gets its own generator to maintain execution context
if page_id not in self.generators:
    self.generators[page_id] = MarimoIslandGenerator(app_id=page_id)
```

**Limitation**: The Marimo directive maintains per-page context, but each directive call is independent. There's no concept of "cell 1, then cell 2, then cell 3" with shared variables.

---

## Goals

### Primary Goals

1. **Markdown-Native Format**: Pure markdown syntax with minimal special markers
2. **Sequential Execution**: Cells execute in order with shared state (like Jupyter)
3. **Version Control Friendly**: Plain text, readable diffs, no JSON
4. **Incremental Execution**: Cache outputs, re-run only changed cells
5. **Bengal Integration**: Leverage existing rendering pipeline, caching, and build system

### Non-Goals

1. **Interactive Runtime**: This is build-time execution (not a Jupyter replacement for live exploration)
2. **Multiple Languages**: Focus on Python initially (though extensible)
3. **Rich Outputs**: Start with text/HTML/images (not interactive widgets)
4. **IDE Integration**: Terminal-friendly first (IDE extensions can come later)

---

## Design Options

### Option 1: Percent Format (Jupytext-Inspired)

**Syntax**: Use `# %%` markers to delimit cells in markdown

```markdown
---
title: "Data Analysis Tutorial"
type: notebook
execute: true
---

# Introduction

This is a computational document.

# %% [markdown]
Let's start with imports:

# %% [code]
import pandas as pd
import matplotlib.pyplot as plt

# %% [markdown]
Now load the data:

# %% [code]
data = pd.read_csv("sales.csv")
data.head()

# %% [markdown]
The data shows...
```

**Pros**:
- ✅ Industry standard (VS Code, PyCharm, Spyder all support `# %%`)
- ✅ Already implemented by Jupytext
- ✅ Clean diffs (no JSON)
- ✅ Works with Python syntax highlighters

**Cons**:
- ❌ Mixes markdown and Python comment syntax
- ❌ Requires `[markdown]` and `[code]` annotations
- ❌ Less markdown-native than pure fences
- ❌ Comment-based syntax feels hacky in markdown files

**File Extension**: `.mdnb`, `.pynb`, or `.md` with `type: notebook` in frontmatter

---

### Option 2: Enhanced Fenced Code Blocks (MyST-Style)

**Syntax**: Use directive-style fences with cell metadata

```markdown
---
title: "Data Analysis Tutorial"
type: notebook
---

# Introduction

This is a computational document.

```{cell}
:label: imports
:cache: true

import pandas as pd
import matplotlib.pyplot as plt
```

Now load the data:

```{cell}
:label: load-data
:depends: imports

data = pd.read_csv("sales.csv")
data.head()
```

The output shows that we have {{ data.shape[0] }} rows.
```

**Pros**:
- ✅ Pure markdown syntax (no comment hacks)
- ✅ Consistent with Bengal's existing directive system (`{tabs}`, `{admonition}`, etc.)
- ✅ Explicit dependency tracking (`:depends:`)
- ✅ Natural cache keys (`:label:`)
- ✅ Already have directive parsing infrastructure

**Cons**:
- ❌ More verbose than `# %%`
- ❌ Not standard in other tools (less editor support)
- ❌ Requires directive syntax knowledge

**File Extension**: `.mdnb`, `.bengal`, or `.md` with `type: notebook`

---

### Option 3: Implicit Cell Detection (Minimalist)

**Syntax**: Any Python fenced code block is a cell if file type is `notebook`

```markdown
---
title: "Data Analysis Tutorial"
type: notebook
execute: true
---

# Introduction

This is a computational document. All Python code blocks execute sequentially.

```python
import pandas as pd
import matplotlib.pyplot as plt
```

Now load the data:

```python
data = pd.read_csv("sales.csv")
data.head()
```

The output shows we have {{ data.shape[0] }} rows.
```

**Pros**:
- ✅ **Cleanest syntax** (looks like regular markdown)
- ✅ No special markers needed
- ✅ Easy to read and write
- ✅ Perfect for simple tutorials

**Cons**:
- ❌ No explicit cell boundaries (all Python blocks are cells)
- ❌ Can't mix "example code" with "executable code"
- ❌ No per-cell metadata (labels, caching, dependencies)
- ❌ Harder to implement selective execution

**File Extension**: `.mdnb`, `.bengal`, or `.md` with `type: notebook`

---

### Option 4: Hybrid Approach (Recommended)

**Syntax**: Combine implicit detection with explicit opt-in

```markdown
---
title: "Data Analysis Tutorial"
type: notebook
---

# Introduction

Regular Python code blocks are just examples (not executed):

```python
# This is just documentation
example_function()
```

Use `{cell}` for executable cells:

```{cell}
import pandas as pd
import matplotlib.pyplot as plt
```

Or use `execute: true` for all Python blocks:

```markdown
---
execute_python_blocks: true
---

```python
# Now this executes automatically
data = pd.DataFrame({"x": [1, 2, 3]})
```
```

**Pros**:
- ✅ Flexible: Implicit for simple docs, explicit for complex ones
- ✅ Backwards compatible with existing markdown
- ✅ Clear intent (cell directive = executable, regular fence = example)
- ✅ Best of both worlds

**Cons**:
- ❌ Two ways to do things (can confuse users)
- ❌ Requires clear documentation of behavior

**File Extension**: `.mdnb` or `.bengal` for notebook mode, `.md` for regular content

---

## Recommended Approach

**Option 2 (Enhanced Fenced Code Blocks)** with influences from Option 4's flexibility.

### Why This Choice?

1. **Consistency**: Aligns with Bengal's existing directive system (`{tabs}`, `{admonition}`, `{marimo}`)
2. **Explicit Intent**: Clear distinction between example code and executable cells
3. **Powerful Metadata**: Labels, caching, dependencies, output control
4. **Extensibility**: Easy to add new cell types (SQL, R, shell commands)
5. **Backward Compatible**: Existing markdown files work unchanged

### Syntax Specification

```markdown
---
title: "My Analysis"
type: notebook
kernel: python
cache_outputs: true
---

# Title

Regular markdown text here.

```{cell}
:label: imports
:cache: true
:show-code: true
:show-output: true

import pandas as pd
```

More text.

```{cell}
:label: load-data
:depends: imports
:cache: false

data = pd.read_csv("data.csv")
data.head()
```

Access outputs in markdown: {{ cells["load-data"].data["row_count"] }} rows.
```

### Cell Options

- `:label:` - Unique identifier (for caching, dependencies, references)
- `:cache:` - Cache output (default: true)
- `:depends:` - Comma-separated labels (explicit dependencies)
- `:inputs:` - External files/globs whose hashes participate in cache fingerprinting
- `:env:` - Allowlisted environment variables exposed during execution
- `:show-code:` - Display source code (default: true)
- `:show-output:` - Display execution output (default: true)
- `:error:` - Behavior on error: `stop` (default), `continue`, `hide`
- `:timeout:` - Per-cell timeout override in seconds (defaults to global `notebooks.timeout`)

### File Extension

**Recommended: Content Detection (No New Extension Required)**

Use regular `.md` files with optional `.mdnb` extension for explicit intent:

```python
def should_execute_cells(file_path: Path, metadata: dict) -> bool:
    """Determine if cells should execute."""

    # Explicit flag always wins
    if "execute_cells" in metadata:
        return metadata["execute_cells"]

    # .mdnb extension implies execution
    if file_path.suffix == ".mdnb":
        return True

    # .md files don't auto-execute (safe default)
    return False
```

**Usage Patterns**:

1. **Simple Tutorial** (`.md` with flag):
```markdown
---
title: "Pandas Intro"
execute_cells: true
---
```{cell}
import pandas as pd
```
```

2. **Dedicated Notebook** (`.mdnb` extension):
```markdown
---
title: "Data Analysis"
# execute_cells: true implied by .mdnb extension
---
```{cell}
import pandas as pd
```
```

3. **Documentation with Examples** (`.md` without flag):
```markdown
---
title: "API Docs"
# execute_cells: false (default)
---
```{cell}
# This renders as example code (not executed)
import mylib
```
```

**Why This Approach**:
- ✅ No new extension required (simpler)
- ✅ Works with existing markdown (gradual adoption)
- ✅ `.mdnb` available for explicit notebooks (optional)
- ✅ Safe default (.md files don't surprise you)
- ✅ GitHub-friendly (renders normally)
- ✅ Clear migration path (.md → .mdnb when ready)

---

## Architecture

### Content Type

Notebook detection and rendering slots into the existing strategy registry (no parallel hierarchy required):

```python
# bengal/content_types/notebook.py

class NotebookContentStrategy(ContentTypeStrategy):
    default_template = "notebook/detail.html"
    allows_pagination = False

    def can_handle(self, page: Page) -> bool:
        return page.metadata.get("type") == "notebook" or page.source_path.suffix == ".mdnb"

    def prepare(self, page: Page, context: BuildContext) -> None:
        if should_execute_cells(page.source_path, page.metadata):
            notebook_engine.execute(page, context)
```

Registry wiring:

- Register `"notebook" -> NotebookContentStrategy()` in `CONTENT_TYPE_REGISTRY`
- Update `detect_content_type` to treat `.mdnb` files as notebook candidates when no explicit type is set
- Ensure `RenderOrchestrator` routes notebook pages through the execution pipeline before handing them to the template engine

This keeps notebook detection compatible with existing frontmatter-based overrides (`type: notebook`) while allowing `.mdnb` to opt-in automatically.

### Parser Extension

Extend Mistune parser with new `CellDirective`:

```python
# bengal/rendering/plugins/directives/cell.py

class CellDirective(DirectivePlugin):
    """Executable code cell for notebook documents."""

    def parse(self, block, m, state):
        # Parse cell options
        # Extract code
        # Return token for deferred execution

    def execute(self, cells: list, namespace: dict) -> list[CellOutput]:
        """Execute cells sequentially with shared namespace."""
        # For each cell:
        #   1. Check cache
        #   2. Execute if needed
        #   3. Capture output
        #   4. Update namespace
        #   5. Store in cache
```

### Execution Model

**Two-Pass Rendering** (with dependency graph):

1. **Parse Pass**
   - Extract every `{cell}` directive into an in-memory `CellSpec` (label, code, metadata)
   - Validate unique labels, normalize `:depends:` declarations, and materialize a directed acyclic graph (DAG)
   - Surface duplicate-label or dangling-dependency errors with file/line context before executing anything

2. **Plan Pass**
   - Run a topological sort (Kahn’s algorithm) across the DAG to obtain a stable execution order
   - Detect cycles early and raise a descriptive `NotebookCycleError` listing the participating labels
   - Compute an execution fingerprint for each cell: `hash(code) + hash(resolved_dependency_fingerprints) + hash(external_inputs)`
   - Compare fingerprints against the cache to decide whether a cell can be skipped, rehydrated from cache, or must run

3. **Execute Pass**
   - Reuse one shared namespace seeded with build context (`page`, `site`, `config`, etc.)
   - For each cell in the sorted order:
     - If cache hit, rehydrate `NotebookCellResult` (stdout, display payloads, artifacts, metadata)
     - If cache miss, run `run_cell(cell, namespace)` which wraps `exec` with:
       - A temporary `sys.displayhook` to capture the “last expression” result (DataFrames, plots, rich reprs)
       - Stdout/stderr capture
       - Library-specific hooks (e.g., matplotlib inspection via `plt.get_fignums()` to inline images)
     - Persist the resulting `NotebookCellResult` to the cache and namespace, and expose it via `cells[label]`

```python
graph = build_dependency_graph(cell_specs)                # Labels → downstream dependents
order = topological_sort(graph)                           # Raises NotebookCycleError if cycle detected

namespace = {
    "page": page,
    "site": site,
    "config": site.config,
}

for cell in order:
    fingerprint = calc_fingerprint(cell, cache, namespace)
    cached = cache.lookup(cell.label, fingerprint)
    if cached:
        result = cached
    else:
        result = run_cell(cell, namespace)                # Handles stdout, display hook, artifacts
        cache.store(cell.label, fingerprint, result)

    namespace.update(result.bindings)                     # e.g., injected variables from `run_cell`
    notebook_cells.set(cell.label, result)                 # Stored on the page for templates
```

The execution pipeline intentionally separates planning from runtime work so that future enhancements (e.g., selective re-execution, parallel execution of independent subgraphs) have a well-defined insertion point.

### Notebook Cells Data Model

Outputs are stored in a dedicated container that extends Bengal’s cache contract:

```python
@dataclass(slots=True)
class NotebookCellResult(Cacheable):
    label: str
    fingerprint: str
    stdout: str
    stderr: str
    display_html: str | None = None
    display_text: str | None = None
    data: dict[str, Any] = field(default_factory=dict)          # e.g., DataFrame schema, stats
    artifacts: list[NotebookArtifact] = field(default_factory=list)
    execution_time_ms: float = 0.0

@dataclass(slots=True)
class NotebookCells(Cacheable):
    results: dict[str, NotebookCellResult] = field(default_factory=dict)

    def set(self, label: str, result: NotebookCellResult) -> None:
        self.results[label] = result

    def __getitem__(self, label: str) -> NotebookCellResult:
        return self.results[label]
```

RFC Impact on existing models:

- `PageCore`: add an optional, JSON-serializable `cells` field that stores cached `NotebookCells` metadata (fingerprints, summary stats) for incremental builds
- `Page` and `PageProxy`: expose a `cells` property delegating to the underlying `NotebookCells`, ensuring templates (`page.cells["label"]`) and post-processing pipelines can access results without forcing a full page load
- `NotebookCells` lives under `bengal/core/notebook_cells.py` (new module) and is registered with the cache serializer alongside `PageCore`

### Caching Strategy

**Fingerprint Components** (per cell):
- Source code hash (normalized for whitespace + metadata)
- Ordered dependency fingerprints (ensures upstream changes invalidate downstream cells)
- External artifact digests declared via `:inputs:` (e.g., CSV files, environment variables)
- Runtime config affecting execution (`notebooks.execute`, `kernel`, `timeout`)

**On-Disk Schema** (`notebook_cache/{page_hash}/{label}.json`):
```python
{
    "fingerprint": "sha256:...",
    "stdout": "...",
    "stderr": "...",
    "display_html": "<div>...</div>",
    "display_text": "DataFrame: 3 rows x 4 cols",
    "data": {
        "schema": {...},
        "summary": {...}
    },
    "artifacts": [
        {"type": "image/png", "path": "monthly_revenue.png", "hash": "sha256:..."}
    ],
    "bindings": {"monthly": "pickle://..."},
    "execution_time_ms": 1234,
    "executed_at": "2025-10-29T10:00:00Z"
}
```

**Invalidation Rules**:
- Fingerprint mismatch (code, dependencies, artifacts, config)
- Missing declared artifact on disk or digest mismatch
- Upstream dependency re-executed with new fingerprint
- Site-wide cache bust (`bengal build --force` or `cache.invalidate_notebook(page_id)`)
- Optional TTL for long-running computations (configurable via `notebooks.cache.ttl`)

Cache writes stream large outputs to disk (images >5 MB, DataFrames >100 KB) to avoid bloating the JSON payload; cache entries keep references to these artifacts for templating and export.

### Template Integration

Notebook outputs accessible in templates via `NotebookCells` proxy:

```html
<!-- templates/notebook.html -->
{% extends "base.html" %}

{% block content %}
  <article class="notebook">
    {{ content }}  <!-- Rendered cells -->

    <!-- Access specific outputs -->
    <div class="summary">
      Dataset has {{ page.cells["load-data"].data["row_count"] }} rows
    </div>
    {% if page.cells.has("monthly-plot") %}
      {{ page.cells["monthly-plot"].display_html | safe }}
    {% endif %}
  </article>
{% endblock %}
```

`NotebookCells` also exposes helper methods for ergonomic template usage:

- `page.cells.keys()` → iterable of executed labels (for auto-generated tables of contents)
- `page.cells.to_dict()` → serializable structure for downstream JSON feeds
- `page.cells.export("load-data", format="json")` → reuse cached result when generating API documentation

### Error Handling & Reporting

- Each cell execution wraps `run_cell` in a try/except that captures the exception type, message, and traceback snippet (first 10 frames)
- Respect the `:error:` directive:
  - `stop` (default): surface the failure, mark build as failed, emit structured log `notebook_cell_error`
  - `continue`: render an admonition block in-place with the captured traceback while allowing downstream cells to proceed (still marks page as “dirty” in health checks)
  - `hide`: skip rendering output, but attach the error details to `page.cells[label].data["error"]` for debugging tools
- Errors include context: page path, cell label, line numbers, dependency chain (`imports -> load-data -> monthly-plot`)
- Integrate with `bengal health` so notebooks produce actionable validator entries (`notebook-cell-error`)

### Security Posture

- Notebook execution remains opt-in (`execute_cells: true` or `.mdnb` with CLI flag `--allow-notebook-exec`)
- Recommend secrets isolation: environment variable allowlist (`notebooks.env.allow = ["ANALYTICS_TOKEN"]`) with defaults to empty
- Document sandbox options: `RestrictedPython` mode or containerized execution via `bengal notebooks run --in-docker`
- Explicit warning in docs: do not enable notebook execution for untrusted repositories
- Provide config to disable execution entirely in CI (`BENGAL_DISABLE_NOTEBOOKS=1`)

---

## Migration Path

### Phase 1: Core Implementation (v0.2)

- [ ] Add `CellDirective` to Mistune parser
- [ ] Implement dependency-aware planner (topological sort + cycle detection)
- [ ] Shared execution namespace with `NotebookCells` data model wired into `Page`/`PageProxy`
- [ ] Capture stdout + last-expression display hook (HTML + text)
- [ ] Persist results to BuildCache (fingerprints, artifacts, metrics)
- [ ] Register `.mdnb` file extension

### Phase 2: Enhanced Features (v0.3)

- [ ] Rich output rendering (automatic matplotlib/Altair capture)
- [ ] Error handling modes (stop/continue/hide) with structured logging
- [ ] External artifact tracking (`:inputs:` metadata) and cache invalidation
- [ ] CLI + config toggles (`--allow-notebook-exec`, `notebooks.execute`)
- [ ] Template helper methods (`cells.keys()`, `cells.export(...)`)

### Phase 3: Advanced (v0.4+)

- [ ] Multiple kernel support (R, Julia, SQL)
- [ ] Parallel cell execution (for independent cells)
- [ ] Export to Jupyter `.ipynb`
- [ ] Import from `.ipynb`
- [ ] Interactive outputs (optional, via Marimo/Shiny)

---

## Alternatives Considered

### A. Use Jupytext Directly

**Pros**: Mature, well-tested, integrates with Jupyter ecosystem

**Cons**:
- Adds heavy dependency
- Requires Jupyter runtime
- Less control over caching/incremental builds
- Doesn't fit Bengal's build-time philosophy

### B. Extend Marimo Directive

**Pros**: Already have Marimo integration, reactive execution model

**Cons**:
- Marimo is designed for interactive notebooks (not static builds)
- Each directive call is independent (no shared namespace)
- Would require significant refactoring

### C. Adopt MyST Markdown Verbatim

**Pros**: Standard in Jupyter Book/Sphinx ecosystem

**Cons**:
- Heavy Sphinx dependency
- More complex than we need
- Doesn't integrate with Bengal's rendering pipeline

---

## Risks & Mitigations

### Risk: Code Execution Security

**Issue**: Executing arbitrary Python during builds is dangerous

**Mitigation**:
- Clearly document that notebooks should only run trusted code
- Sandbox execution (optional): `RestrictedPython` or Docker containers
- Disable by default, require explicit `execute: true` flag
- Build-time only (never execute user-submitted code)

### Risk: Long Build Times

**Issue**: Executing many notebooks could slow builds

**Mitigation**:
- Aggressive caching (only re-run changed cells)
- Parallel notebook execution (independent files)
- Streaming mode (don't load all outputs in memory)
- Optional: Skip notebook execution with `--skip-notebooks` flag

### Risk: Format Divergence

**Issue**: Creating yet another notebook format fragments ecosystem

**Mitigation**:
- Support Jupytext import/export
- Document conversion workflows
- Focus on markdown-native use case (where JSON notebooks don't fit)
- Consider submitting `.mdnb` as a standard to MyST/Jupytext communities

---

## Success Criteria

### User Experience

- [ ] Can create a tutorial with 10+ code cells in pure markdown
- [ ] Build time < 2s for 5 notebooks with 50 total cells (cached)
- [ ] Git diffs show only changed cells, not JSON noise
- [ ] Can reference cell outputs in markdown text
- [ ] Error messages clearly indicate which cell failed

### Technical

- [ ] Cache hit rate > 90% for unchanged cells
- [ ] Memory usage < 100MB per notebook (streaming outputs)
- [ ] Incremental builds only re-execute changed cells
- [ ] Test coverage > 90% for notebook execution path

### Documentation

- [ ] Tutorial: "Creating Your First Notebook"
- [ ] Guide: "Notebook Best Practices"
- [ ] Reference: "Cell Directive Options"
- [ ] Examples: Data analysis, tutorial, API documentation

---

## Open Questions

1. **Should `.md` files with `type: notebook` execute automatically?**
   - Pro: Simpler (no new extension)
   - Con: Surprising behavior (existing .md files might break)

2. **How to handle cell outputs in static site?**
   - Option A: Inline HTML (simple, but large pages)
   - Option B: Separate JSON files (smaller pages, more requests)
   - Option C: Collapsible outputs (best UX, more complex)

3. **Should we support Jupyter kernels directly?**
   - Pro: Can run R, Julia, etc.
   - Con: Heavy dependency, complex to install
   - Alternative: Start with Python `exec()`, add kernels later

4. **Version control for outputs?**
   - Option A: Commit outputs (like Jupytext `--sync` mode)
   - Option B: Ignore outputs (regenerate on build)
   - Option C: Configurable per-project

5. **CLI for interactive editing?**
   - `bengal notebook edit file.mdnb` → Launch editor?
   - `bengal notebook run file.mdnb` → Execute and show outputs?
   - Or keep it simple: just edit in any text editor?

---

## Next Steps

### Immediate (this week)

1. **Prototype `CellDirective`**: Test basic parsing and execution
2. **Spike caching**: Verify cell-level caching works with BuildCache
3. **Demo notebook**: Create example `.mdnb` file showcasing syntax

### Short-term (this month)

1. Implement Phase 1 (core features)
2. Write tests for cell execution and caching
3. Document the `.mdnb` format specification
4. Create tutorial content

### Long-term (next quarter)

1. Gather user feedback on syntax and workflow
2. Implement Phase 2 (enhanced features)
3. Consider proposing `.mdnb` to MyST/Jupytext communities
4. Add VS Code extension for `.mdnb` syntax highlighting

---

## Dogfooding: Bengal Developer Documentation

### Use Cases for Bengal's Own Docs

Bengal's own documentation (`site/`) would benefit immensely from executable notebooks. This provides **dogfooding validation** and **living developer documentation**.

### Recommended Structure

```
site/content/
├── developers/
│   ├── filters.mdnb              ← Interactive filter reference
│   ├── validators.mdnb           ← Build custom validators
│   ├── plugins.mdnb              ← Write Jinja filters/shortcodes
│   ├── data-models.mdnb          ← Explore Page/Site objects
│   ├── config-system.mdnb        ← Config merging examples
│   └── text-processing.mdnb      ← Utils (slugify, etc.)
├── tutorials/
│   ├── custom-theme.mdnb         ← Theme development
│   └── content-types.mdnb        ← Custom content strategies
```

### Priority Examples to Implement

#### 1. **Template Filters Reference** (`developers/filters.mdnb`) ⭐⭐⭐

**Value**: Every filter is documented with live, tested examples

```markdown
---
title: "Template Filters Reference"
description: "Interactive documentation of Bengal's Jinja2 filters"
type: reference
execute_cells: true
exports:
  jupyter: true
  python: true
---

# Bengal Template Filters

All filters tested live in this document. Download as Jupyter notebook to experiment!

## String Filters

### `slugify`

Convert text to URL-safe slugs.

**Signature**: `slugify(text: str) -> str`

```{cell}
:label: test_slugify
:cache: true

from bengal.rendering.template_functions.strings import slugify

# Test cases (also serve as documentation)
test_cases = [
    ("Hello World", "hello-world"),
    ("Python 3.14!", "python-314"),
    ("Über cool", "uber-cool"),
    ("What's happening?", "whats-happening"),
    ("São Paulo", "sao-paulo"),
]

print("Input                     → Output")
print("-" * 50)
for input_text, expected in test_cases:
    result = slugify(input_text)
    status = "✅" if result == expected else "❌"
    print(f"{status} {input_text:20} → {result}")
    assert result == expected, f"Expected {expected}, got {result}"
```

**Template usage**:
```jinja2
{{ page.title | slugify }}
```

### `markdownify`

Render Markdown to HTML inline.

```{cell}
:label: test_markdownify
:depends: test_slugify

from bengal.rendering.template_functions.strings import markdownify

markdown = """
# Heading

This is **bold** and *italic*.

- Item 1
- Item 2

[Link](https://example.com)
"""

html = markdownify(markdown)
print(html)

# Verify it renders correctly
assert "<h1>" in html
assert "<strong>bold</strong>" in html
assert '<a href="https://example.com">' in html
```

## Date Filters

### `date_format`

```{cell}
:label: test_date_format

from bengal.rendering.template_functions.dates import date_format
from datetime import datetime

now = datetime(2024, 10, 29, 14, 30)

formats = {
    "%Y-%m-%d": "2024-10-29",
    "%B %d, %Y": "October 29, 2024",
    "%b %d, %Y": "Oct 29, 2024",
}

for fmt, expected in formats.items():
    result = date_format(now, fmt)
    status = "✅" if result == expected else "❌"
    print(f"{status} {fmt:20} → {result}")
```

## Collection Filters

### `group_by`

Group items by attribute.

```{cell}
:label: test_group_by

from bengal.rendering.template_functions.collections import group_by

pages = [
    {"title": "Getting Started", "category": "tutorial"},
    {"title": "Release 0.2", "category": "news"},
    {"title": "Custom Themes", "category": "tutorial"},
    {"title": "Release 0.3", "category": "news"},
]

grouped = group_by(pages, "category")

for category, group_pages in sorted(grouped.items()):
    print(f"\n{category.upper()}:")
    for page in group_pages:
        print(f"  - {page['title']}")

# Verify grouping
assert len(grouped["tutorial"]) == 2
assert len(grouped["news"]) == 2
```

---

**Download this notebook** to experiment with filters in Jupyter!
```

**Benefits**:
- ✅ Filters are **tested on every build** (catch breaking changes)
- ✅ Examples **always work** (living documentation)
- ✅ Developers can **download and experiment**
- ✅ Serves as **regression test suite**

---

#### 2. **Custom Validator Tutorial** (`developers/validators.mdnb`) ⭐⭐⭐

**Value**: Step-by-step guide with working examples

```markdown
---
title: "Writing Custom Validators"
description: "Build health checks for your Bengal site"
execute_cells: true
exports:
  jupyter: true
---

# Writing Custom Validators

Learn to build health validators with live examples.

## Basic Validator Structure

```{cell}
:label: basic_validator

from bengal.health.validators.base import BaseValidator
from typing import List, Dict, Any

class NoOrphanPagesValidator(BaseValidator):
    """Ensure all pages have incoming links."""

    name = "no-orphans"
    description = "Check for pages with no incoming links"

    def validate(self, site) -> List[Dict[str, Any]]:
        """Find orphan pages."""
        issues = []

        # Collect all internal links
        linked_pages = set()
        for page in site.pages:
            for link in page.metadata.get('internal_links', []):
                linked_pages.add(link)

        # Find orphans (excluding homepage)
        for page in site.pages:
            if page.url_path not in linked_pages and page.url_path != '/':
                issues.append({
                    'severity': 'warning',
                    'message': f'Orphan page: {page.url_path}',
                    'file': str(page.source_path),
                    'hint': 'Add links to this page from other content',
                })

        return issues

print(f"✅ Created validator: {NoOrphanPagesValidator.name}")
```

## Testing Your Validator

```{cell}
:label: test_validator
:depends: basic_validator

# Create mock objects for testing
class MockPage:
    def __init__(self, url, source, links=None):
        self.url_path = url
        self.source_path = source
        self.metadata = {'internal_links': links or []}

class MockSite:
    def __init__(self, pages):
        self.pages = pages

# Test case 1: All pages linked
site1 = MockSite([
    MockPage('/', 'content/index.md', ['/about', '/docs']),
    MockPage('/about', 'content/about.md', ['/']),
    MockPage('/docs', 'content/docs.md', ['/']),
])

validator = NoOrphanPagesValidator()
issues1 = validator.validate(site1)
print(f"Test 1 - All linked: {len(issues1)} issues ✅")
assert len(issues1) == 0

# Test case 2: One orphan
site2 = MockSite([
    MockPage('/', 'content/index.md', ['/about']),
    MockPage('/about', 'content/about.md', ['/']),
    MockPage('/orphan', 'content/orphan.md', []),  # No incoming links!
])

issues2 = validator.validate(site2)
print(f"Test 2 - One orphan: {len(issues2)} issues")
for issue in issues2:
    print(f"  ⚠️  {issue['message']}")
assert len(issues2) == 1
assert '/orphan' in issues2[0]['message']

print("\n✅ All validator tests passed!")
```

## Registering Your Validator

```{cell}
:label: register_validator

# In your bengal_plugins.py or validators.py
def register_validators():
    """Register custom validators."""
    from bengal.health.registry import validator_registry

    validator_registry.register(NoOrphanPagesValidator)
    print("✅ Validator registered")

# Simulate registration
register_validators()
```

## Running Validators

```bash
# Run all validators
bengal health check

# Run specific validator
bengal health check --validator no-orphans
```
```

**Benefits**:
- ✅ **Tested tutorial** (examples actually work)
- ✅ **Developer playground** (download and modify)
- ✅ **Best practices** (show proper testing)
- ✅ **Quick start** (copy-paste to get started)

---

#### 3. **Plugin Development Guide** (`developers/plugins.mdnb`) ⭐⭐

**Value**: End-to-end plugin examples

```markdown
---
title: "Bengal Plugin Development"
execute_cells: true
exports:
  jupyter: true
  colab_button: true
---

# Bengal Plugin Development

## Custom Jinja2 Filter

```{cell}
:label: custom_filter

def emoji_filter(text: str) -> str:
    """Convert :emoji: syntax to Unicode emoji."""
    emoji_map = {
        ':rocket:': '🚀',
        ':check:': '✅',
        ':fire:': '🔥',
        ':book:': '📚',
        ':warning:': '⚠️',
        ':sparkles:': '✨',
    }

    for code, emoji in emoji_map.items():
        text = text.replace(code, emoji)

    return text

# Test it
test_cases = [
    "Deploy :rocket:",
    "All tests passing :check:",
    "Hot new feature :fire:",
]

for test in test_cases:
    result = emoji_filter(test)
    print(f"{test:30} → {result}")
```

## Register with Jinja2

```{cell}
:label: register_filter
:depends: custom_filter

from jinja2 import Environment

# Simulate Jinja2 registration
env = Environment()
env.filters['emoji'] = emoji_filter

# Test in template
template = env.from_string("{{ content | emoji }}")
output = template.render(content="Build sites :rocket: with Bengal :fire:")
print(f"Template output: {output}")

assert output == "Build sites 🚀 with Bengal 🔥"
print("✅ Filter registered and tested!")
```

## Usage in Templates

```jinja2
<!-- templates/page.html -->
<h1>{{ page.title | emoji }}</h1>
<p>{{ page.description | emoji | safe }}</p>
```

## Creating a Plugin File

```{cell}
:label: plugin_file

plugin_code = '''
"""
Custom Bengal plugins.

Place this file in your project root as bengal_plugins.py
"""

def emoji_filter(text: str) -> str:
    """Convert :emoji: syntax to Unicode."""
    emoji_map = {
        ':rocket:': '🚀',
        ':check:': '✅',
        ':fire:': '🔥',
    }
    for code, emoji in emoji_map.items():
        text = text.replace(code, emoji)
    return text

def register_filters(jinja_env):
    """Called by Bengal to register filters."""
    jinja_env.filters['emoji'] = emoji_filter
    return jinja_env
'''

print("Create bengal_plugins.py with this content:")
print("=" * 50)
print(plugin_code)
```
```

---

#### 4. **Data Models Reference** (`developers/data-models.mdnb`) ⭐

**Value**: Interactive exploration of Bengal's core objects

```markdown
---
title: "Bengal Data Models"
execute_cells: true
---

# Bengal Data Models

Explore Bengal's core data structures interactively.

## Page Object

```{cell}
:label: page_model

from bengal.core.page.page import Page
from pathlib import Path
from datetime import datetime

# Create example page
page = Page(
    source_path=Path("content/blog/my-post.md"),
    output_path=Path("public/blog/my-post/index.html"),
    url_path="/blog/my-post/",
    title="My First Post",
    date=datetime(2024, 10, 29),
    content="# Hello\n\nThis is my post.",
    metadata={
        "description": "My first blog post",
        "tags": ["python", "bengal"],
        "draft": False,
    }
)

# Explore properties
print(f"Title: {page.title}")
print(f"URL: {page.url_path}")
print(f"Date: {page.date}")
print(f"Tags: {page.metadata['tags']}")
print(f"Draft: {page.metadata['draft']}")
```

## Slug Generation

```{cell}
:label: slug_examples
:depends: page_model

from bengal.utils.text import slugify

titles = [
    "My First Post!",
    "Python 3.14 Release",
    "São Paulo Travel Guide",
    "What's New in 2025?",
    "C++ Performance Tips",
]

print("Title                         → Slug")
print("-" * 60)
for title in titles:
    slug = slugify(title)
    print(f"{title:30} → {slug}")
```

## Taxonomy Organization

```{cell}
:label: taxonomy_demo

from collections import defaultdict

pages_by_tag = defaultdict(list)

# Sample pages
sample_pages = [
    {"title": "Intro to Bengal", "tags": ["tutorial", "getting-started"]},
    {"title": "Custom Themes", "tags": ["tutorial", "themes"]},
    {"title": "Version 0.2", "tags": ["releases", "news"]},
    {"title": "Config Guide", "tags": ["tutorial", "configuration"]},
]

# Organize by tags
for page_data in sample_pages:
    for tag in page_data["tags"]:
        pages_by_tag[tag].append(page_data["title"])

# Display taxonomy
for tag, pages in sorted(pages_by_tag.items()):
    print(f"\n📁 {tag}")
    for page_title in pages:
        print(f"   - {page_title}")
```
```

---

### Implementation Plan for Bengal Docs

**Phase 1**: Create core developer documentation
```bash
site/content/developers/
├── filters.mdnb         # Template filter reference
├── validators.mdnb      # Custom validator tutorial
└── plugins.mdnb         # Plugin development guide
```

**Phase 2**: Add advanced topics
```bash
site/content/developers/
├── data-models.mdnb     # Page/Site/Section objects
├── config-system.mdnb   # Configuration deep-dive
└── text-processing.mdnb # Utils reference
```

**Phase 3**: Tutorial notebooks
```bash
site/content/tutorials/
├── custom-theme.mdnb    # Theme from scratch
└── content-types.mdnb   # Custom content strategies
```

### Success Metrics

**For Bengal Project**:
- ✅ Developer docs are **always correct** (tested on every build)
- ✅ Plugin API has **working examples** (copy-paste ready)
- ✅ Breaking changes **fail docs build** (early detection)
- ✅ Contributors can **download and experiment** (Jupyter export)

**For Feature Validation**:
- ✅ **Dogfooding** proves the feature works
- ✅ **Real use cases** validate design decisions
- ✅ **Performance testing** with actual content
- ✅ **Documentation** demonstrates value

### Build Configuration

```toml
# site/bengal.toml

[notebooks]
execute = true              # Execute on build
cache_outputs = true        # Cache for speed
timeout = 30                # 30s per cell
fail_on_error = true        # Fail build if cell errors

[notebooks.exports]
jupyter = true              # Generate .ipynb downloads
python = true               # Generate .py scripts
colab_button = true         # Add Colab badges
```

---

## Appendix: Syntax Examples

### Example 1: Simple Tutorial

```markdown
---
title: "Pandas Quick Start"
type: notebook
---

# Getting Started with Pandas

Install pandas: `pip install pandas`

```{cell}
:label: imports

import pandas as pd
import numpy as np

print(f"Pandas version: {pd.__version__}")
```

Create a DataFrame:

```{cell}
:label: create-df
:depends: imports

data = {
    'name': ['Alice', 'Bob', 'Charlie'],
    'age': [25, 30, 35],
    'city': ['NYC', 'SF', 'LA']
}

df = pd.DataFrame(data)
df
```

We have {{ cells["create-df"].data["row_count"] }} people in our dataset.
```

### Example 2: Data Analysis Report

```markdown
---
title: "Sales Analysis Q4 2024"
type: notebook
cache_outputs: true
---

# Executive Summary

This report analyzes sales data for Q4 2024.

```{cell}
:label: setup
:show-code: false

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_style("whitegrid")
```

```{cell}
:label: load-data
:depends: setup

# Load sales data
sales = pd.read_csv("data/sales_q4_2024.csv", parse_dates=['date'])

# Basic stats
print(f"Total records: {len(sales):,}")
print(f"Date range: {sales['date'].min()} to {sales['date'].max()}")
print(f"Total revenue: ${sales['revenue'].sum():,.2f}")
```

```{cell}
:label: monthly-plot
:depends: load-data
:show-code: false

# Monthly revenue trend
monthly = sales.groupby(sales['date'].dt.to_period('M'))['revenue'].sum()

plt.figure(figsize=(10, 6))
monthly.plot(kind='bar', color='steelblue')
plt.title('Monthly Revenue - Q4 2024')
plt.ylabel('Revenue ($)')
plt.xlabel('Month')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('monthly_revenue.png', dpi=150, bbox_inches='tight')
plt.show()
```

## Key Findings

- Total revenue: ${{ "{:,.2f}".format(cells["load-data"].data["revenue_sum"]) }}
- Best month: {{ cells["monthly-plot"].data["best_month"] }}
- Growth rate: {{ cells["monthly-plot"].data["growth_pct"] }}%
```

### Example 3: API Documentation with Examples

```markdown
---
title: "Database API Reference"
type: notebook
---

# Database Connection API

## `connect()`

Connect to the database:

```{cell}
:label: connect-example

from mylib import Database

# Create connection
db = Database.connect(
    host="localhost",
    port=5432,
    database="mydb"
)

print(f"Connected to {db.database}")
```

## `query()`

Execute a SELECT query:

```{cell}
:label: query-example
:depends: connect-example

# Run query
results = db.query("SELECT * FROM users LIMIT 5")

# Display as table
for row in results:
    print(row)
```

Returns {{ cells["query-example"].data["row_count"] }} rows.
```

---

## References

- [Jupytext Documentation](https://jupytext.readthedocs.io/)
- [MyST Markdown Spec](https://myst-parser.readthedocs.io/)
- [Marimo Documentation](https://docs.marimo.io/)
- [Bengal Marimo Directive](../bengal/rendering/plugins/directives/marimo.py)
- [Bengal Directive System](../architecture/rendering.md#directives)

---

**Confidence**: 82% 🟡

**Reasoning**:
- ✅ **Evidence (35/40)**: Strong evidence from existing Marimo directive and directive system
- ✅ **Consistency (28/30)**: Architecture aligns with Bengal's rendering pipeline and caching
- ✅ **Recency (14/15)**: Based on current codebase state and modern tools (Jupytext, MyST)
- ⚠️ **Tests (5/15)**: No prototype yet—implementation complexity unknown

**Next Step**: Build prototype to validate execution model and caching strategy.
