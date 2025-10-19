# AI-Synthesized MyST Parser Proposal for Bengal

**Author:** Grok 4 Fast AI Assistant  
**Date:** October 19, 2025  
**Status:** Proposal - Ready for Review  
**Strategic Priority:** High - Enables Sphinx/MyST Ecosystem Integration  

## Executive Summary

After analyzing the two engineer drafts and examining Bengal's codebase, I **strongly recommend proceeding with Option A from the first draft (Python `myst-parser` + Docutils integration)** as the primary path for MyST support. This aligns closely with the second draft's detailed recommendation and leverages Bengal's existing pluggable parser architecture.

**Key Findings:**
- **Viability:** High. Bengal's `BaseMarkdownParser` ABC and factory pattern (`create_markdown_parser`) make integration straightforward.
- **LoE:** Medium (3-5 weeks for MVP, including custom directive wrapping). Lower than extending mistune for full MyST parity.
- **Strategic Value:** Transformative. Positions Bengal as the "fast Sphinx alternative" for technical docs, enabling seamless migrations without content rewrites.
- **Risks:** Manageable (Docutils dependency, performance overhead ~2x mistune, syntax differences). Mitigated by optional extras and keeping mistune as default.
- **Recommendation:** Start with a 1-week prototype of basic `MystParser` to validate performance and doctree-to-HTML flow, then full implementation.

This approach provides native Python integration (no Node.js), broad MyST spec compliance, and reduced maintenance by reusing Docutils for standard directives (admonitions, figures, math, etc.). Custom Bengal features (tabs, data-tables) can be wrapped as Docutils directives.

## Analysis of Engineer Drafts

### Draft 1: `myst-parser-viability-and-loe.md`
- **Focus:** High-level options assessment with emphasis on migration from Sphinx.
- **Options Evaluated:**
  - **A (Python myst-parser + Docutils):** Parse to AST, render via Docutils HTML writer. LoE: 2-3 days baseline +1-2 weeks for Sphinx directives. Risks: Coverage gaps, differing HTML semantics.
  - **B (JS mystmd CLI):** Shell-out to Node CLI per page. LoE: 1-2 days MVP. Risks: Node dep, per-page overhead.
  - **C (Extend mistune):** Add MyST syntax as plugins. LoE: 3-6 days core. Risks: Spec divergence, maintenance.
- **Recommendation:** Tiered - Start with B (quick, broad coverage), enhance C for performance, optional A later.
- **Strengths:** Pragmatic, low-risk MVP via CLI. Highlights existing partial MyST support (colon fences).
- **Weaknesses:** JS CLI adds deps/overhead; doesn't leverage Python ecosystem.

### Draft 2: `myst-parser-integration-analysis.md`
- **Focus:** Deep dive into Python myst-parser integration, with code sketches and strategic rationale.
- **Key Insights:**
  - Detailed architecture: Wrap `myst-parser`'s Docutils output in `BaseMarkdownParser`.
  - LoE: 2-4 weeks (Phase 1: Basic, Phase 2: TOC, Phase 3: Parity, Phase 4: Tests/Docs).
  - Strategic: Sphinx migration path, reduced custom code (~60% less maintenance), ecosystem compatibility (JupyterBook, VSCode).
  - Risks/Mitigations: Optional deps (`bengal[myst]`), benchmarks, syntax compat via extensions.
  - Recommendation: Pure MyST parser, explicit config (`parser = "myst"`), reuse Bengal logic for customs.
- **Strengths:** Comprehensive, code-ready sketches, performance targets, success metrics.
- **Weaknesses:** Assumes Docutils weight is acceptable; no CLI fallback.

### Synthesis
Both drafts agree on high viability and Sphinx value. Draft 1's CLI option is quick but suboptimal (Node dep, overhead). Draft 2's Python path is superior for native integration and long-term maintenance. My proposal merges: Python primary (per Draft 2), with CLI as future experimental option (per Draft 1's Phase 3). LoE averaged to 3-5 weeks, emphasizing prototype validation.

## Codebase Examination

Bengal's rendering system is well-architected for parser extensibility, confirming low integration friction.

### Parser Architecture (`bengal/rendering/parsers/`)
- **BaseMarkdownParser (base.py):** Clean ABC with `parse()` → HTML str and `parse_with_toc()` → (HTML, TOC HTML). No changes needed.
- **Factory (__init__.py):** `create_markdown_parser(engine)` supports "mistune" (default) and "python-markdown". Easy to add "myst" case.
- **MistuneParser (mistune.py):** ~700 lines, feature-rich:
  - Plugins: Tables, footnotes, custom directives (admonitions, tabs via `create_documentation_directives()`).
  - Variable sub: Preprocess with `VariableSubstitutionPlugin` for `{{ var }}`.
  - TOC: Regex-based extraction from anchored headings (fast, excludes blockquotes).
  - Post-process: Badges (`BadgePlugin`), xrefs (`CrossReferencePlugin`).
  - Thread-local: Designed for parallel reuse (critical for perf).
  - Perf: ~1-5ms/page, highlighting via cached Pygments.
- **PythonMarkdownParser (python_markdown.py):** ~70 lines, simple extensions (extra, codehilite, toc). Legacy/slower baseline.
- **Integration (pipeline.py, inferred):** Thread-cached via `_get_thread_parser()`, config-driven (`[markdown].parser`).

### Existing MyST Mentions
- No implementations: Grep confirms no `MystParser` or myst-parse classes/functions.
- Partial support: Draft 1 notes colon-fence directives work in tests (via mistune plugins).
- Opportunities: Reuse mistune's post-process (badges, xrefs, anchors) on MyST HTML output. Wrap custom directives as Docutils nodes.

### Gaps/Insights
- **Strength:** Pluggable design ideal for MyST. TOC/anchors can reuse mistune's regex (apply post-HTML).
- **Perf Consideration:** Mistune is optimized (regex > BS4); MyST's Docutils may add 1-2ms/page. Benchmark essential.
- **Customs:** Directives in `plugins/directives/` (~1500 lines total) need Docutils wrappers, but logic reusable.
- **No Breaking Changes:** Keep mistune default; MyST opt-in via config/extras.

## My Recommendation: Python MyST-Parser Integration (Primary), CLI Experimental

**Primary Path:** Implement `MystParser` using `myst-parser` + Docutils:
- **Why Python over JS CLI?** Native, no Node dep, better perf (no shell-out), aligns with Bengal's Python-first ethos. Leverages mature ecosystem (Sphinx/Jupyter).
- **Why over mistune extension?** Full spec compliance, less custom code (built-in directives), true MyST compatibility for migrations.
- **Tiered Rollout:** MVP with core MyST (admonitions, figures, math). Add customs (tabs) in v1. Follow with CLI as "experimental" for edge cases.

**Config Example:**
```toml
[markdown]
parser = "myst"  # or "mistune" default

[project.optional-dependencies]
myst = ["myst-parser>=2.0.0", "docutils>=0.19"]
```
Usage: `pip install bengal[myst]`

**MVP Scope (3 weeks):**
- Basic parse/toc.
- Variable sub (preprocess or MyST extension).
- Standard MyST features (no customs yet).
- Tests on showcase site.

**Full Scope (5 weeks):** Wrap 4-5 key customs (tabs, data-table, marimo, dropdowns).

## Implementation Plan

### Phase 1: Prototype (1 Week)
- Create `bengal/rendering/parsers/myst.py`: Implement `BaseMarkdownParser`.
  - Use `myst_parser.main.to_docutils()` → doctree.
  - Render via `docutils.core.publish_string(writer_name='html')`.
  - Reuse mistune's `_inject_heading_anchors` and `_extract_toc` (post-HTML).
- Add to factory: `if engine == "myst": return MystParser()`.
- Basic tests: Parse sample MyST, compare HTML to mistune.
- Benchmark: Time 50 pages from `examples/showcase/`.
- Decision: Proceed if perf <3x mistune.

### Phase 2: Core Features (1-2 Weeks)
- **Variable Sub:** Preprocess content with Jinja2 (reuse `VariableSubstitutionPlugin` logic) before MyST.
- **XRefs/Badges:** Apply mistune's post-process plugins to MyST HTML.
- **TOC/Anchors:** Reuse regex methods.
- Config: `[markdown.myst]` for extensions (dollarmath, substitution).
- Integration: Update pipeline to handle myst engine.

### Phase 3: Custom Directives (1 Week)
- Wrap key mistune directives as Docutils:
  - `TabsDirective`: Reuse `parse_tab_markers`/`render_tabs_html`.
  - `DataTableDirective`: Reuse CSV/JSON logic.
  - Others: Admonitions (leverage MyST built-ins where possible).
- Register via `directives.register_directive()` in MystParser init.

### Phase 4: Testing & Polish (0.5-1 Week)
- Unit: Parser methods.
- Integration: Build test sites with MyST syntax.
- Docs: Update README, add migration guide (`bengal migrate sphinx` stub).
- Optional: CLI fallback if Docutils issues arise.

**File Changes:**
- New: `parsers/myst.py` (~300 lines).
- Update: `__init__.py` (+5 lines), `pyproject.toml` (extras).
- Reuse: Plugins from mistune (post-process).

**Perf Targets:** <3ms/page (100-page site: <500ms total).

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Docutils dep (~2MB) | Medium | Optional `[myst]` extras; minimal install unchanged. |
| Perf overhead (2-3x) | Medium | Prototype benchmark; opt-in only; cache doctree if possible. |
| Syntax shift (```` vs :::) | Low | MyST `colon_fence` extension supports both; migration tool. |
| Custom directive wrapping | Medium | Reuse 80% logic; start with 4 key ones; fallback to mistune. |
| Doctree-HTML diffs | Low | Post-process with mistune regex; CSS compat layer if needed. |
| Maintenance (Docutils changes) | Low | Monitor via tests; community handles most (Sphinx). |

## Strategic Benefits & Next Steps

- **Benefits:** Sphinx migration (minimal rewrites), reduced custom code, MyST ecosystem (VSCode, Jupyter), differentiation ("Fast SSG with native MyST").
- **Metrics:** 10x faster than Sphinx; 20% maintenance reduction; 5+ migration case studies.
- **Next Steps:**
  1. Approve prototype (1 week).
  2. Assign dev for Phase 1.
  3. Review prototype; greenlight full impl.
  4. Beta in v0.2.0; gather feedback.
  5. Stable in v1.0 with changelog entry.

This proposal positions Bengal as a leader in technical docs SSGs. Let's prototype!

## Appendix: Code Sketches

### MystParser Skeleton
```python
from typing import Any
from abc import abstractmethod
import docutils.core
from myst_parser.main import to_docutils
from bengal.rendering.parsers.base import BaseMarkdownParser
from bengal.rendering.parsers.mistune import MistuneParser  # For reuse

class MystParser(BaseMarkdownParser):
    def __init__(self):
        self.publish = docutils.core.publish_string
        # Register custom directives
        from docutils.parsers.rst import directives
        directives.register_directive('tabs', TabsDirective)
        # ...

    def parse(self, content: str, metadata: dict[str, Any]) -> str:
        doc = to_docutils(content)
        html = self.publish(doc.asdom().toxml(), writer_name='html')
        # Post-process (reuse mistune)
        html = MistuneParser._inject_heading_anchors(html)  # Static method?
        return html

    def parse_with_toc(self, content: str, metadata: dict[str, Any]) -> tuple[str, str]:
        html = self.parse(content, metadata)
        toc = MistuneParser._extract_toc(html)
        return html, toc
```

### Dependency Update
```toml
[project.optional-dependencies]
myst = [
    'myst-parser >= 2.0.0',
    'docutils >= 0.19',
]
```
