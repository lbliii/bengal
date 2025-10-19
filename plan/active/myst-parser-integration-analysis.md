# MyST Parser Integration Analysis for Bengal

**Status:** Research & Analysis  
**Date:** October 19, 2025  
**Strategic Value:** High - Enables Sphinx migration path

## Executive Summary

**Verdict: HIGHLY VIABLE and STRATEGICALLY VALUABLE**

MyST parser integration is an excellent strategic fit for Bengal. The LoE is **LOW-to-MEDIUM** because:

1. ✅ **Bengal is already designed for parser swapping** - `BaseMarkdownParser` abstraction exists
2. ✅ **MyST provides comprehensive directives out-of-the-box** - Reduces custom implementation needs
3. ✅ **Strong Sphinx migration value proposition** - Major differentiator vs other SSGs
4. ⚠️ **Some adapter work needed** - MyST uses docutils, Bengal expects HTML strings
5. ⚠️ **Feature parity consideration** - Need to ensure Bengal's custom features still work

---

## Table of Contents

1. [Current Bengal Parser Architecture](#current-bengal-parser-architecture)
2. [MyST Parser Overview](#myst-parser-overview)
3. [Level of Effort Assessment](#level-of-effort-assessment)
4. [Implementation Strategy](#implementation-strategy)
5. [Strategic Benefits](#strategic-benefits)
6. [Risks & Mitigations](#risks--mitigations)
7. [Recommendations](#recommendations)

---

## Current Bengal Parser Architecture

### ✅ Bengal IS Designed for Parser Swapping

Bengal has a **clean parser abstraction** that enables multiple parser backends:

```python
# bengal/rendering/parsers/base.py
class BaseMarkdownParser(ABC):
    @abstractmethod
    def parse(self, content: str, metadata: dict[str, Any]) -> str:
        """Parse Markdown content into HTML."""
        pass

    @abstractmethod
    def parse_with_toc(self, content: str, metadata: dict[str, Any]) -> tuple[str, str]:
        """Parse Markdown and extract TOC."""
        pass
```

**Current Implementations:**
- `MistuneParser` - Fast, GFM-compatible, custom directives (default)
- `PythonMarkdownParser` - Full-featured, slower (legacy)

**Parser Selection:**
```toml
# bengal.toml
[markdown]
parser = "mistune"  # or "python-markdown"
```

**Factory Pattern:**
```python
# bengal/rendering/parsers/__init__.py
def create_markdown_parser(engine: str | None = None) -> BaseMarkdownParser:
    engine = (engine or "mistune").lower()

    if engine == "mistune":
        return MistuneParser()
    elif engine in ("python-markdown", "python_markdown", "markdown"):
        return PythonMarkdownParser()
    else:
        raise ValueError(f"Unsupported markdown engine: {engine}")
```

**Pipeline Integration:**
```python
# bengal/rendering/pipeline.py - RenderingPipeline.__init__()
markdown_config = site.config.get("markdown", {})
markdown_engine = markdown_config.get("parser", "mistune")
self.parser = _get_thread_parser(markdown_engine)  # Thread-local caching
```

### Thread-Local Parser Caching

Bengal uses **thread-local caching** for parser instances to avoid re-initialization overhead in parallel builds:

```python
# _get_thread_parser() creates ONE parser per worker thread
# With max_workers=10 and 200 pages:
# - 10 threads → 10 parser instances
# - Each processes ~20 pages
# - Creation cost: 10ms × 10 = 100ms one-time
# - Reuse savings: 9.9 seconds (avoiding 190 × 10ms)
```

**Implication for MyST:** Must ensure MyST parser instances are thread-safe or use same pattern.

---

## MyST Parser Overview

### What is MyST?

**MyST (Markedly Structured Text)** is an extended Markdown specification designed for technical documentation.

**Key Characteristics:**
- **Superset of CommonMark** - All valid Markdown is valid MyST
- **Directives & Roles** - RST/Sphinx-style extension points
- **Multiple Implementations** - Python (via `myst-parser`) and JavaScript (via `mystmd`)
- **Well-Specified** - Formal spec at https://mystmd.org/spec
- **Sphinx-Compatible** - Designed for Sphinx ecosystem

### Python MyST Parser

**Package:** `myst-parser` (https://myst-parser.readthedocs.io/)

**Architecture:**
- Built on `markdown-it-py` (Python port of markdown-it)
- Integrates with **Docutils** (RST/Sphinx document model)
- Outputs **Docutils doctree** (not HTML directly)
- Sphinx renders doctree → HTML

**Key Features (Built-in):**
- ✅ **Directives:** `:::{directive}` syntax (admonitions, figures, tables, etc.)
- ✅ **Roles:** `` {role}`content` `` syntax (cross-refs, citations, inline markup)
- ✅ **Math:** LaTeX equations with `$...$` and `$$...$$`
- ✅ **Footnotes:** `[^1]` syntax
- ✅ **Definition Lists:** Term/definition pairs
- ✅ **Attributes:** `{#id .class key=val}` on blocks
- ✅ **Nested Parsing:** Full Markdown support inside directives
- ✅ **Cross-References:** Sphinx-style `` {doc}`path/to/doc` ``
- ✅ **Substitutions:** `{{ variable }}` (via MyST-specific extension)

**Standard Directives (Out-of-Box):**
```markdown
:::{note}
This is a note admonition.
:::

:::{warning}
This is a warning.
:::

:::{figure} path/to/image.png
:width: 500px

Figure caption goes here.
:::

:::{code-block} python
:linenos:
:emphasize-lines: 2,3

def hello():
    print("Hello")
    print("World")
:::

:::{list-table} Title
:header-rows: 1

* - Column 1
  - Column 2
* - Data
  - More data
:::
```

**Standard Roles:**
```markdown
{ref}`target`         - Cross-reference to heading/label
{doc}`path/to/doc`    - Link to another document
{term}`glossary-term` - Glossary reference
{math}`E=mc^2`        - Inline math
{code}`python code`   - Inline code with language
{abbr}`NASA (National Aeronautics and Space Administration)` - Abbreviation
```

### Comparison: MyST vs Bengal's Current Directives

| Feature | Bengal (Mistune) | MyST (Out-of-Box) | Winner |
|---------|------------------|-------------------|--------|
| **Admonitions** | 9 types (custom plugin) | 15+ types (built-in) | MyST |
| **Tabs** | Custom plugin (~200 lines) | Not built-in | Bengal |
| **Dropdowns** | Custom plugin | `dropdown` directive | Tie |
| **Code Tabs** | Partial support | Not built-in | Neutral |
| **Cards/Grid** | Custom plugin | Sphinx-Design compat | MyST |
| **List Tables** | Custom plugin | Built-in `list-table` | MyST |
| **Data Tables** | Custom plugin (CSV/JSON) | Not built-in | Bengal |
| **Math** | Via Pygments | Native LaTeX support | MyST |
| **Cross-refs** | `[[link]]` (custom) | Sphinx-style roles | Both |
| **Variable Sub** | `{{ var }}` (custom) | Jinja2 extension | Tie |
| **Figures** | Markdown images | `figure` directive | MyST |
| **Glossary** | Not built-in | `glossary`/`term` | MyST |
| **Citations** | Not built-in | `cite`/`footcite` | MyST |

**Verdict:** MyST provides **significantly more directives** out-of-box, reducing custom code.

---

## Level of Effort Assessment

### LoE: **LOW-to-MEDIUM** (2-4 weeks, 1 developer)

### Phase 1: Basic Integration (1 week)

**Goal:** Get MyST parsing working with existing Bengal pipeline.

**Tasks:**
1. ✅ Add `myst-parser` dependency to `pyproject.toml`
2. ✅ Create `MystParser` class implementing `BaseMarkdownParser`
3. ✅ Handle Docutils doctree → HTML conversion
4. ✅ Update `create_markdown_parser()` factory
5. ✅ Add basic tests

**Key Challenge:** **Docutils Integration**

MyST outputs a **Docutils doctree**, not HTML strings. Need adapter:

```python
# Conceptual implementation
class MystParser(BaseMarkdownParser):
    def __init__(self):
        from myst_parser.main import to_docutils
        from docutils.core import publish_string
        self.to_docutils = to_docutils
        self.publish = publish_string

    def parse(self, content: str, metadata: dict[str, Any]) -> str:
        # Parse MyST → Docutils doctree
        doc = self.to_docutils(content)

        # Render doctree → HTML
        html = self.publish(
            doc.asdom().toprettyxml(),
            writer_name='html5',
            settings_overrides={'initial_header_level': 2}
        )

        return html.decode('utf-8')
```

**Estimate:** 3-5 days (including Docutils learning curve)

### Phase 2: TOC Extraction (2-3 days)

**Goal:** Implement `parse_with_toc()` for TOC sidebar.

**Challenge:** Extract TOC from Docutils doctree, not HTML.

**Approach 1: Docutils Visitor Pattern**
```python
def parse_with_toc(self, content: str, metadata: dict[str, Any]) -> tuple[str, str]:
    doc = self.to_docutils(content)

    # Extract TOC using Docutils node visitor
    toc_builder = TOCVisitor(doc)
    doc.walk(toc_builder)
    toc_html = toc_builder.get_toc_html()

    # Render HTML
    html = self.publish(doc, writer_name='html5')

    return html, toc_html
```

**Approach 2: Parse HTML Output (Simpler)**
```python
def parse_with_toc(self, content: str, metadata: dict[str, Any]) -> tuple[str, str]:
    html = self.parse(content, metadata)

    # Reuse Bengal's existing TOC extraction (from MistuneParser)
    toc = self._extract_toc(html)

    return html, toc
```

**Estimate:** 2-3 days (Approach 1 is better but harder; Approach 2 is quick fallback)

### Phase 3: Bengal Feature Parity (3-5 days)

**Goal:** Ensure Bengal-specific features work with MyST.

**Required Features:**
1. ✅ **Variable Substitution** - `{{ page.metadata.xxx }}`
2. ✅ **Cross-References** - `[[docs/page]]` syntax
3. ✅ **Custom Directives** - Tabs, data-table, marimo, etc.
4. ✅ **Heading Anchors** - Auto-generated IDs
5. ✅ **Badges** - API doc enhancements (`@async`, `@property`)

**Implementation:**

**1. Variable Substitution:**
```python
def parse_with_context(self, content: str, metadata: dict, context: dict) -> str:
    # Option A: Preprocess before MyST parsing (like Mistune)
    from jinja2 import Template
    preprocessed = Template(content).render(**context)
    return self.parse(preprocessed, metadata)

    # Option B: Use MyST's Jinja2 extension
    # (MyST has built-in support, just needs config)
```

**2. Cross-References:**
```python
# Post-process HTML to convert [[...]] → <a>
def _substitute_xrefs(self, html: str) -> str:
    # Reuse existing CrossReferencePlugin logic
    return self._xref_plugin._substitute_xrefs(html)
```

**3. Custom Directives:**
```python
# Register Bengal's custom directives with MyST
from myst_parser.main import MdParserConfig
from docutils.parsers.rst import directives

# Register custom directives
directives.register_directive('tabs', TabsDirective)
directives.register_directive('data-table', DataTableDirective)
directives.register_directive('marimo', MarimoDirective)
# ... etc
```

**Estimate:** 3-5 days (mostly testing and edge cases)

### Phase 4: Testing & Documentation (2-3 days)

**Goal:** Comprehensive test suite and user documentation.

**Tasks:**
1. ✅ Unit tests for `MystParser` class
2. ✅ Integration tests with example sites
3. ✅ Update documentation (README, ARCHITECTURE.md)
4. ✅ Migration guide for Sphinx users
5. ✅ Performance benchmarking vs Mistune

**Estimate:** 2-3 days

### Total LoE: **2-4 weeks** (single developer)

**Breakdown:**
- Week 1: Basic integration + TOC
- Week 2: Feature parity + custom directives
- Week 3-4: Testing, docs, polish, benchmarking

**Parallelization:** Could reduce to **1-2 weeks** with 2 developers (one on core, one on directives).

---

## Implementation Strategy

### Approach: **Use Existing MyST-Parser (Don't Build from Spec)**

**Recommendation:** Use the official `myst-parser` Python package, NOT build against spec.

**Why?**
1. ✅ **Mature & Battle-Tested** - Used by entire Sphinx/JupyterBook ecosystem
2. ✅ **Rich Feature Set** - 50+ directives/roles out-of-box
3. ✅ **Active Development** - Regularly updated, good support
4. ✅ **Docutils Integration** - Leverages 20 years of RST tooling
5. ✅ **Lower Maintenance** - Don't reinvent parsing logic
6. ⚠️ **Docutils Dependency** - Adds weight (~1.5MB), but worth it

**Alternative (Not Recommended):** Build custom MyST parser from spec
- ❌ **High LoE** - 2-3 months of work
- ❌ **Bug-Prone** - Parsing is hard, spec is complex
- ❌ **Missing Features** - Spec doesn't include all Sphinx directives
- ❌ **Maintenance Burden** - Must keep up with spec changes
- ✅ **Lighter Weight** - No Docutils dependency
- ✅ **Full Control** - Can optimize for SSG use case

**Verdict:** Use `myst-parser` unless weight is critical concern (it's not for most users).

### Architecture Design

#### Option A: Pure MyST Parser (Recommended)

**When to use:** User configures `parser = "myst"`

```toml
# bengal.toml
[markdown]
parser = "myst"  # Uses MyST parser exclusively
```

**Behavior:**
- Use MyST's native directive syntax: `:::{note}`
- Disable Bengal's Mistune plugins
- Register Bengal custom directives as Docutils directives

**Pros:**
- ✅ Clean separation
- ✅ Full MyST spec compliance
- ✅ Better for Sphinx migrations

**Cons:**
- ⚠️ Users must rewrite content if switching from Mistune

#### Option B: Hybrid Parser (Complex, Not Recommended)

**When to use:** Auto-detect syntax, use appropriate parser per-file

```toml
[markdown]
parser = "auto"  # Detect MyST vs GFM syntax
```

**Behavior:**
- Detect `:::{directive}` → use MyST
- Detect ` ```{directive}` → use Mistune
- Mixed syntax in single file? Parse with both?

**Pros:**
- ✅ Gradual migration path

**Cons:**
- ❌ Complex implementation
- ❌ Confusing UX (magic behavior)
- ❌ Ambiguous syntax conflicts
- ❌ Hard to test

**Verdict:** Don't implement Option B. Use explicit `parser` config.

### File Structure

```
bengal/rendering/parsers/
├── __init__.py          # Add "myst" to factory
├── base.py              # No changes needed
├── mistune.py           # Existing
├── python_markdown.py   # Existing
└── myst.py              # NEW - MystParser implementation
```

### Configuration Schema

```toml
[markdown]
parser = "myst"  # New option: "mistune", "python-markdown", "myst"

# MyST-specific configuration (optional)
[markdown.myst]
enable_extensions = [
    "dollarmath",     # $...$ and $$...$$ math
    "amsmath",        # Advanced math environments
    "deflist",        # Definition lists
    "fieldlist",      # Field lists
    "colon_fence",    # ::: fenced directives (in addition to ```)
    "substitution",   # Jinja2 variable substitution
]

# Register custom directives
custom_directives = [
    "tabs",
    "data-table",
    "marimo",
]
```

### Custom Directive Registration

**Strategy:** Convert Bengal's Mistune directives → Docutils directives

**Example:**

```python
# bengal/rendering/parsers/myst_directives.py
from docutils.parsers.rst import Directive, directives
from docutils import nodes

class TabsDirective(Directive):
    """
    Convert Bengal's tabs directive to Docutils.

    Syntax:
        :::{tabs}
        ### Tab: Python
        Python code here

        ### Tab: JavaScript
        JS code here
        :::
    """
    has_content = True
    option_spec = {
        'id': directives.unchanged,
    }

    def run(self):
        # Parse content for tab markers
        content = '\n'.join(self.content)
        tabs = self._parse_tabs(content)

        # Generate HTML node
        html = self._render_tabs_html(tabs)
        raw_node = nodes.raw('', html, format='html')

        return [raw_node]

    def _parse_tabs(self, content):
        # Reuse Bengal's existing tab parsing logic
        from bengal.rendering.plugins.directives.tabs import parse_tab_markers
        return parse_tab_markers(content)

    def _render_tabs_html(self, tabs):
        # Reuse Bengal's existing rendering logic
        from bengal.rendering.plugins.directives.tabs import render_tabs_html
        return render_tabs_html(tabs)

# Register with Docutils
directives.register_directive('tabs', TabsDirective)
```

**Key Insight:** Reuse Bengal's existing directive logic, just wrap in Docutils API.

---

## Strategic Benefits

### 1. **Sphinx Migration Path** ⭐⭐⭐⭐⭐

**Problem:** Organizations want to move from Sphinx to faster SSGs, but rewriting RST → Markdown is painful.

**Solution:** MyST is a **drop-in Markdown replacement for RST**.

**Value Prop:**
> "Bengal supports MyST syntax, so you can migrate from Sphinx with **minimal content rewrites**. Just switch your parser and theme."

**Example Migration:**

**Before (Sphinx RST):**
```rst
.. note::
   This is an important note.

.. code-block:: python
   :linenos:

   def hello():
       pass

.. toctree::
   :maxdepth: 2

   intro
   guide
```

**After (Bengal MyST):**
```markdown
:::{note}
This is an important note.
:::

:::{code-block} python
:linenos:

def hello():
    pass
:::

# No toctree needed - Bengal auto-discovers pages
```

**Conversion Tool Opportunity:**
Could build `bengal migrate sphinx` CLI command to auto-convert:
- RST directives → MyST directives
- `conf.py` → `bengal.toml`
- Sphinx extensions → Bengal plugins

### 2. **Differentiation vs Competitors**

**Competitive Landscape:**
- **Hugo:** GFM + shortcodes (Go templates, not Markdown-native)
- **MkDocs:** Python-Markdown + extensions (fragmented ecosystem)
- **Docusaurus:** MDX (React components, high learning curve)
- **VitePress:** Markdown + Vue components
- **Sphinx:** RST or MyST (slow builds, legacy architecture)

**Bengal's Unique Position:**
> "Bengal is the **only fast SSG** with **native MyST support** and **Sphinx compatibility**."

**Target Audience:**
- 🎯 Sphinx users wanting faster builds (10-100x speedup)
- 🎯 Technical writers wanting RST-level features in Markdown
- 🎯 Open-source projects needing scientific docs (math, citations)
- 🎯 Organizations with existing Sphinx content

### 3. **Reduced Maintenance Burden**

**Current State:** Bengal maintains ~1500 lines of custom directive code
- `directives/admonitions.py` (~150 lines)
- `directives/tabs.py` (~200 lines)
- `directives/dropdown.py` (~100 lines)
- `directives/code_tabs.py` (~150 lines)
- `directives/cards.py` (~200 lines)
- `directives/list_table.py` (~300 lines)
- `directives/data_table.py` (~200 lines)
- `directives/button.py` (~100 lines)
- `directives/rubric.py` (~50 lines)

**With MyST:** Most of these are **built-in** (admonitions, dropdown, list-table, etc.)

**Remaining Custom Directives:**
- `tabs` - Bengal-specific syntax (could keep)
- `data-table` - CSV/JSON data (unique feature)
- `marimo` - Reactive notebooks (unique feature)
- `github-notebook` - GitHub integration (unique feature)

**Maintenance Reduction:** ~60% less custom code to maintain.

### 4. **Ecosystem Compatibility**

**MyST is Supported By:**
- **JupyterBook** - Entire ecosystem uses MyST
- **Sphinx** - Official parser (`myst-parser`)
- **VSCode** - MyST syntax highlighting extension
- **Jupyter** - Native support in JupyterLab
- **GitHub** - Renders MyST directives (basic)

**Network Effects:**
- Content written for Bengal works in JupyterBook
- Sphinx themes can be adapted for Bengal
- VSCode extensions work out-of-box
- Shared learning resources / documentation

### 5. **Technical Documentation Excellence**

**MyST Features Bengal Currently Lacks:**

| Feature | Use Case | Example |
|---------|----------|---------|
| **Math** | Scientific docs | `$E=mc^2$` or `$$\int f(x)dx$$` |
| **Citations** | Academic papers | `{cite}smith2020` → footnote + bibliography |
| **Glossary** | Terminology | `{term}API` → link to definition |
| **Field Lists** | Metadata display | `:Author: John\n:Date: 2024` |
| **Figures** | Publication-quality | `:::{figure} img.png\n:scale: 50%\n:::` |
| **Substitutions** | Reusable snippets | `{{{ company_name }}}` |
| **Line Numbers** | Code tutorials | `:linenos:\n:emphasize-lines: 2,3` |

**Result:** Bengal becomes **best-in-class for technical documentation**.

---

## Risks & Mitigations

### Risk 1: **Docutils Dependency Size**

**Risk:** Docutils adds ~1.5MB to install size + dependencies (Pygments, etc.)

**Impact:** Medium - Some users want minimal installs

**Mitigation:**
```toml
# pyproject.toml
[project.optional-dependencies]
myst = [
    "myst-parser>=2.0.0",
    "docutils>=0.19",
]
```

**Usage:**
```bash
# Minimal install (Mistune only)
pip install bengal

# With MyST support
pip install bengal[myst]
```

**Trade-off:** Acceptable - users who want MyST can install extra deps.

### Risk 2: **Performance Regression**

**Risk:** MyST parser might be slower than Mistune

**Mitigation:**
1. ✅ **Benchmark early** - Measure MyST vs Mistune on real sites
2. ✅ **Thread-local caching** - Reuse parser instances (same as Mistune)
3. ✅ **Lazy loading** - Only import MyST when `parser = "myst"`
4. ✅ **Make it optional** - Default stays `mistune`

**Hypothesis:** MyST built on `markdown-it-py` which is fast (~0.5-1ms per page). Docutils overhead might add ~1-2ms. Acceptable for most use cases.

**Target:** MyST should be within **2x of Mistune** performance.

### Risk 3: **Breaking Changes in Bengal Syntax**

**Risk:** Users with Mistune content can't easily switch to MyST

**Impact:** Medium - Different directive syntax

**Mistune (Bengal current):**
````markdown
```{note} Title
Content here
```
````

**MyST:**
```markdown
:::{note} Title
Content here
:::
```

**Mitigation:**
1. ✅ **Support both syntaxes** - MyST supports ` ```{...}` via `colon_fence=False`
2. ✅ **Migration guide** - Document syntax differences
3. ✅ **Conversion tool** - Build `bengal convert mistune-to-myst` command
4. ✅ **Keep Mistune default** - No breaking change for existing users

**MyST Config for Mistune Compat:**
```python
# myst-parser supports both syntaxes!
myst_enable_extensions = [
    "colon_fence",  # Support both ::: and ```{} syntax
]
```

### Risk 4: **Custom Directive Incompatibility**

**Risk:** Bengal's custom directives (tabs, data-table, marimo) don't work with MyST

**Impact:** High - These are differentiating features

**Mitigation:**
1. ✅ **Docutils Wrapper** - Wrap Bengal directives as Docutils directives (see implementation above)
2. ✅ **Reuse Logic** - Keep existing parsing/rendering code, just change API surface
3. ✅ **Comprehensive Tests** - Ensure feature parity
4. ✅ **Fallback to Mistune** - If directive fails, user can switch back

**Estimate:** 1-2 days per custom directive to wrap.

### Risk 5: **Variable Substitution Conflicts**

**Risk:** Bengal's `{{ page.metadata.xxx }}` syntax conflicts with MyST's Jinja2 extension

**Impact:** Low - Both use same syntax, should be compatible

**Mitigation:**
1. ✅ **Use MyST's substitution extension** - It already does what Bengal needs!
2. ✅ **Test code block isolation** - Ensure ` ``` ` blocks stay literal
3. ✅ **Document escape syntax** - `{{/* literal */}}`

**MyST Config:**
```python
myst_enable_extensions = ["substitution"]
myst_substitutions = {
    "page.title": page.title,
    "site.baseurl": site.config.get("baseurl", ""),
    # ... dynamically populate from page/site context
}
```

### Risk 6: **Learning Curve for Contributors**

**Risk:** Contributors need to learn Docutils API to add/fix directives

**Impact:** Low-Medium - Docutils is less familiar than Mistune

**Mitigation:**
1. ✅ **Document patterns** - Create guide for wrapping directives
2. ✅ **Reuse existing logic** - Most complexity is already in Bengal's directive code
3. ✅ **Keep Mistune path** - Contributors can still work on Mistune directives
4. ✅ **Examples** - Provide template directive as reference

**Trade-off:** Acceptable - benefit of MyST outweighs learning curve.

---

## Recommendations

### Phase 1: **Prototype & Validate** (Week 1)

**Goal:** Prove MyST integration is viable with minimal effort.

**Tasks:**
1. ✅ Create spike branch: `feature/myst-parser-prototype`
2. ✅ Implement basic `MystParser` class (no TOC, no custom directives)
3. ✅ Test with simple example site (5-10 pages)
4. ✅ Benchmark performance vs Mistune
5. ✅ Present findings to team

**Success Criteria:**
- MyST parser renders Markdown correctly
- Performance within 2x of Mistune
- No major architectural blockers

**Decision Point:** Go/no-go on full implementation.

### Phase 2: **Full Implementation** (Week 2-3)

**If prototype succeeds, implement full MyST support:**

1. ✅ Implement `parse_with_toc()`
2. ✅ Add variable substitution support
3. ✅ Wrap custom directives (tabs, data-table, marimo)
4. ✅ Add cross-reference support
5. ✅ Write comprehensive tests
6. ✅ Update documentation

### Phase 3: **Beta Release** (Week 4)

**Goal:** Get community feedback before 1.0 release.

1. ✅ Release Bengal v0.2.0-beta with MyST support
2. ✅ Write migration guide for Sphinx users
3. ✅ Create example sites (scientific docs, API docs)
4. ✅ Gather feedback from early adopters
5. ✅ Fix bugs and iterate

**Marketing:**
- Blog post: "Migrating from Sphinx to Bengal"
- Reddit: r/python, r/opensource
- HN: "Show HN: Fast SSG with MyST support"

### Phase 4: **Stable Release** (Month 2)

**Goal:** Production-ready MyST parser.

1. ✅ Address beta feedback
2. ✅ Performance optimizations
3. ✅ Release Bengal v0.2.0 stable
4. ✅ Case study: Real migration (JupyterBook → Bengal?)

---

## Alternatives Considered

### Alternative 1: **Extend Mistune with MyST-Like Syntax**

**Approach:** Add `:::{directive}` support to Mistune via plugin.

**Pros:**
- ✅ No Docutils dependency
- ✅ Keep existing parser architecture

**Cons:**
- ❌ **Lots of custom code** - Must implement 50+ directives
- ❌ **Not real MyST** - Won't be compatible with JupyterBook/Sphinx
- ❌ **No ecosystem benefits** - Isolated implementation
- ❌ **High maintenance** - Must keep up with MyST spec changes

**Verdict:** ❌ **Not recommended** - Misses strategic value of MyST compatibility.

### Alternative 2: **Support Only Core MyST Syntax**

**Approach:** Implement basic MyST parser from spec, skip advanced directives.

**Pros:**
- ✅ Lighter weight (no Docutils)
- ✅ Full control over implementation

**Cons:**
- ❌ **Partial compatibility** - Not true "MyST support"
- ❌ **Sphinx migrations fail** - Missing critical directives (code-block, figure, etc.)
- ❌ **High LoE** - Still 1-2 months of parsing work
- ❌ **Confusing UX** - "Supports MyST" but missing features

**Verdict:** ❌ **Not recommended** - "Half-MyST" is worse than no MyST.

### Alternative 3: **Wait for MyST JavaScript Parser**

**Approach:** Use `mystmd` (JavaScript MyST parser) via Python bindings.

**Pros:**
- ✅ Official MyST implementation
- ✅ No Docutils dependency

**Cons:**
- ❌ **Immature** - JavaScript parser is beta, less feature-complete than Python
- ❌ **Node.js dependency** - Adds complexity for pure Python tool
- ❌ **Python bindings** - Extra work to integrate
- ❌ **Performance unknown** - Node/Python IPC overhead

**Verdict:** ⚠️ **Maybe in future** - Monitor `mystmd` maturity, revisit in 6-12 months.

---

## Conclusion

### Summary

**MyST parser integration is HIGHLY RECOMMENDED for Bengal.**

**Key Points:**
1. ✅ **Low-Medium LoE** - 2-4 weeks with existing `myst-parser` package
2. ✅ **High Strategic Value** - Unique position for Sphinx migrations
3. ✅ **Reduced Maintenance** - Leverage mature Docutils ecosystem
4. ✅ **Best-in-Class Features** - Math, citations, glossaries, etc.
5. ✅ **Clean Architecture** - Bengal already designed for this
6. ⚠️ **Optional Dependency** - Can make it `pip install bengal[myst]`
7. ⚠️ **Performance Trade-off** - Slight overhead acceptable for feature richness

### Next Steps

1. **Immediate:** Prototype `MystParser` class (1 week spike)
2. **Short-term:** Full implementation if prototype succeeds (2-3 weeks)
3. **Medium-term:** Beta release and community feedback (1 month)
4. **Long-term:** Position Bengal as "Sphinx successor" (3-6 months)

### Impact on Bengal's Vision

**Before MyST:**
> "Bengal is a fast, modern SSG for Python developers."

**After MyST:**
> "Bengal is the **fast Sphinx alternative** - build docs 10-100x faster without rewriting content."

This is a **game-changing value proposition** for the Sphinx/JupyterBook community.

---

## Appendix

### References

- **MyST Specification:** https://mystmd.org/spec
- **MyST Parser (Python):** https://myst-parser.readthedocs.io/
- **MyST JavaScript:** https://mystmd.org/overview/ecosystem
- **Docutils:** https://docutils.sourceforge.io/
- **JupyterBook:** https://jupyterbook.org/ (largest MyST user)
- **Sphinx:** https://www.sphinx-doc.org/

### Related Bengal Docs

- `bengal/rendering/parsers/base.py` - Parser interface
- `bengal/rendering/pipeline.py` - Parser integration
- `bengal/rendering/plugins/README.md` - Custom directive architecture
- `ARCHITECTURE.md` - Overall system design

### Dependencies to Add

```toml
# pyproject.toml
[project.optional-dependencies]
myst = [
    "myst-parser>=2.0.0",  # MyST Markdown parser
    "docutils>=0.19",      # Document processing (required by myst-parser)
]
```

### Configuration Examples

**Minimal MyST:**
```toml
[markdown]
parser = "myst"
```

**Full MyST Config:**
```toml
[markdown]
parser = "myst"

[markdown.myst]
# Enable extensions
enable_extensions = [
    "dollarmath",      # $...$ and $$...$$ math
    "amsmath",         # Advanced math environments
    "deflist",         # Definition lists
    "fieldlist",       # Field lists
    "colon_fence",     # ::: fenced directives
    "substitution",    # {{ variable }} substitution
]

# Substitution variables (accessible in Markdown)
substitutions = {
    company = "Acme Corp",
    version = "2.0.0",
}

# Custom directive registration
custom_directives = [
    "tabs",
    "data-table",
    "marimo",
]

# HTML output settings
html_meta = {
    "description": "Technical documentation",
}
```

### Performance Targets

**Benchmark Goals (per page):**
- Mistune: ~1-2ms (baseline)
- MyST target: ~2-4ms (within 2x)
- MyST acceptable: ~5ms (within 2.5x)

**Full site build (100 pages):**
- Mistune: ~200-300ms (parallel, 10 workers)
- MyST target: ~400-600ms
- MyST acceptable: ~750ms

**Methodology:**
- Benchmark on `examples/showcase/` (50+ pages)
- Test with different content types (code-heavy, text-heavy, math-heavy)
- Compare peak memory usage
- Measure parser initialization overhead

### Success Metrics

**Technical:**
- ✅ Passes all existing tests with MyST parser
- ✅ Renders 50+ standard MyST directives correctly
- ✅ Performance within 2x of Mistune
- ✅ No memory leaks in long-running builds

**Strategic:**
- ✅ 3+ case studies of Sphinx → Bengal migrations
- ✅ 20+ GitHub stars from JupyterBook/Sphinx users
- ✅ Featured on MyST ecosystem page
- ✅ 10+ questions on Stack Overflow tagged `bengal-myst`

**Community:**
- ✅ 5+ community-contributed MyST directives
- ✅ Blog posts from users about Sphinx migration
- ✅ Positive feedback on r/python, HN

---

**Document Status:** ✅ **COMPLETE - Ready for Decision**  
**Recommendation:** ✅ **PROCEED with Phase 1 Prototype**  
**Owner:** TBD  
**Review Date:** TBD after prototype completion
