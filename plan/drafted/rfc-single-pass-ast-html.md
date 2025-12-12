---
status: Draft
---

## RFC: Single-pass AST + HTML generation for Mistune content parsing

### Summary
Bengal currently **parses Markdown twice per page** (HTML + AST) in the common Mistune “preprocess enabled” path, but the build pipeline does not consume the cached AST yet. This RFC proposes a phased change to **enable a single-pass AST-first pipeline** (AST → HTML/TOC) with strict output-equivalence validation gates.

### Problem statement
In cold builds (and in any build where pages are fully parsed), Bengal’s `RenderingPipeline` parses Markdown to HTML and then separately parses the same Markdown to AST tokens for caching:

- **HTML parse**: `bengal/rendering/pipeline/core.py:368-403`
- **AST parse (second parse)**: `bengal/rendering/pipeline/core.py:404-418`

The AST is stored on the `Page` and in the parsed-content cache (via `_ast_cache`), but the main rendering pipeline continues to render templates from the legacy HTML field (`page.parsed_ast`), not from AST-derived HTML:

- `page.parsed_ast` is set and used for downstream rendering: `bengal/rendering/pipeline/core.py:420-421`
- The pipeline still post-processes `page.parsed_ast` (escape + internal-link transforms): `bengal/rendering/pipeline/core.py:346-353`

Meanwhile, the Mistune parser already documents per-page parsing costs and provides AST APIs:

- Parser perf note (**~1–5 ms per page**): `bengal/rendering/parsers/mistune.py:84-88`
- `parse_to_ast()` cost “similar to parse()”: `bengal/rendering/parsers/mistune.py:705-708`
- `parse_with_ast()` exists but does not currently use the same plugin/renderer configuration as the HTML path: `bengal/rendering/parsers/mistune.py:781-830`

### Goals
- **Reduce cold-build render time** by eliminating redundant Markdown parsing work when AST caching is enabled.
- Provide an **output-equivalence proof** (within a defined tolerance) before switching defaults.
- Keep the implementation **thread-safe** and compatible with parallel rendering.

### Non-goals
- Changing template rendering semantics (Jinja).
- Changing Markdown feature behavior (directives, term plugin, variable substitution, xrefs, badges/icons).
- Migrating the entire system to AST-driven rendering in one step.

### Current behavior (evidence)
#### Where the double parse happens
In `_parse_with_mistune()` when `page.metadata.get("preprocess") is not False`, the pipeline:
1. Builds variable context and runs `parse_with_toc_and_context` / `parse_with_context` (HTML output) `bengal/rendering/pipeline/core.py:378-393`.
2. Separately calls `parse_to_ast()` and stores `_ast_cache` `bengal/rendering/pipeline/core.py:404-418`.

#### AST is present but not used for rendering today
`PageContentMixin` exposes AST-driven helpers (`html`, `_extract_links_from_ast`, etc.), but these are not used by the main render pipeline:
- `PageContentMixin.html` prefers AST if present, otherwise falls back to `parsed_ast`: `bengal/core/page/content.py:86-114`
- Render pipeline uses `page.parsed_ast` and assigns it directly: `bengal/rendering/pipeline/core.py:420-421`

### Proposed design
#### Phase 0 (safety gate): stop paying for AST unless it is used
Introduce a config flag that controls AST extraction:

- `markdown.ast_cache.enabled` (default **False** initially)

Behavior:
- When disabled, skip the `parse_to_ast()` step in `RenderingPipeline` (remove the second parse).
- When enabled, proceed with the Phase 1/2 path below.

Rationale: today AST is stored but not consumed by the pipeline; gating immediately prevents paying the redundant parse cost on cold builds while we harden AST-first rendering.

#### Phase 1 (correctness-first): make AST generation semantically equivalent
Modify Mistune AST parsing to use the **same plugin set and shared renderer assumptions** as the HTML path:

Evidence for current HTML parser configuration:
- Plugins list includes documentation directives and TermPlugin: `bengal/rendering/parsers/mistune.py:113-124`
- HTML renderer is shared (`HTMLRenderer(escape=False)`): `bengal/rendering/parsers/mistune.py:130-153`

Issue with current `parse_with_ast()` implementation:
- AST parser is created via `create_markdown(renderer=None)` without passing the same plugins: `bengal/rendering/parsers/mistune.py:727-734`
- AST → HTML uses a fresh `HTMLRenderer()` (not shared renderer): `bengal/rendering/parsers/mistune.py:765-773`

Design changes:
- Provide a new API on `MistuneParser` that supports the same per-page context behavior as today:
  - `parse_with_ast_and_context(content, metadata, context) -> (ast, html, toc)`
  - Must incorporate the existing variable substitution preprocessing (see variable-substitution path described in `MistuneParser.parse_with_toc_and_context` docstring, which states variable preprocessing is ~0.5 ms/page): `bengal/rendering/parsers/mistune.py:451-456`
- Ensure AST tokens are compatible with the existing `PageContentMixin` expectations (`list[dict[str, Any]]`).

#### Phase 2 (pipeline adoption): use AST-first path behind a flag
In `RenderingPipeline._parse_with_mistune()`:
- When `markdown.ast_cache.enabled` is True, run the AST-first path and set:
  - `page._ast_cache = ast`
  - `page.parsed_ast = html` (for backward compatibility)
  - `page.toc = toc`

### Validation strategy (must-have gates)
1. **Output equivalence tests (golden tests)**:
   - For a representative set of test roots and content features (directives, term plugin, variable substitution, xrefs, code fences):
     - Compare old-path `page.parsed_ast` vs new-path output under normalization.
2. **Template rendering equivalence**:
   - Full build outputs must remain identical for a fixed fixture (or match under existing normalization helpers).
3. **Performance test**:
   - Add a benchmark to quantify cold-build time reduction when `markdown.ast_cache.enabled=True` on a site with N pages.

### Payoff estimate (grounded)
Based on in-code performance notes:
- Mistune per-page parsing: **~1–5 ms/page** `bengal/rendering/parsers/mistune.py:84-88`
- `parse_to_ast()` cost similar to parse: `bengal/rendering/parsers/mistune.py:705-708`

If we eliminate the second parse on pages where AST caching is currently performed, expected cold-build savings:

\[
\text{time_saved} \approx N_{\text{pages}} \times (1\text{–}5)\text{ ms}
\]

Examples:
- 1,000 pages: **~1–5 seconds**
- 5,000 pages: **~5–25 seconds**

### Risks
- **Semantic drift** between AST-derived HTML and current HTML parser output (plugins/directives/renderer state).
- **Increased complexity** in Mistune parser codepaths (two output modes).
- **Unclear downstream consumers**: current pipeline still uses `page.parsed_ast`; AST-first is primarily a performance enabling step until AST is used broadly.

### Rollout plan
1. Phase 0: introduce config gate to stop unconditional AST parsing.
2. Phase 1: implement `parse_with_ast_and_context` and add golden equivalence tests.
3. Phase 2: enable AST-first path behind flag; keep default off until confidence is high.
4. Flip default only after:
   - golden tests stable
   - performance regression tests show improvement
   - no drift in integration fixtures

### Confidence
**70% (moderate)** — evidence strongly supports the existence of redundant parsing and the size of the per-page parsing cost, but output equivalence risk is material because the current AST path does not share the same plugin/renderer behavior as the HTML path.
