# MyST parser: viability and LoE

### Goal

Assess the level of effort (LoE) and viability of adding a "MyST" Markdown parser option to Bengal as an alternative to the existing `mistune` engine, with a focus on migration paths from Sphinx and alignment with the MyST specification.

References: [MyST Ecosystem Overview](https://mystmd.org/overview/ecosystem), [MyST Specification](https://mystmd.org/spec)

### Current State (Bengal)

- Parser switching is already supported via `bengal.rendering.parsers.create_markdown_parser(engine)` with `mistune` as default and `python-markdown` as an alternative.
- Bengal’s custom directive suite (admonitions, tabs, dropdown, code-tabs, badges, etc.) is implemented as `mistune` plugins. We already support MyST-style colon-fenced directives and options parsing in tests, so a subset of MyST syntax works today.
- Cross-references, heading anchors, TOC extraction, and variable substitution are handled post-parse or via Bengal plugins, independent of the underlying markdown engine.

### What “MyST support” could mean

MyST has two major tracks:

1) Python track (ExecutableBooks)
   - `myst-parser` integrates with `docutils`/Sphinx, producing a `docutils` AST; Sphinx extensions provide commonly used directives/roles in JupyterBook ecosystems.
   - Outside Sphinx, we can still parse with `docutils` + extensions, then render to HTML via the `docutils` HTML writer, but coverage of popular Sphinx directives (e.g., sphinx-design tabs/cards) would require either running Sphinx or re-implementing those directives/transforms.

2) JavaScript track (`mystmd`)
   - CLI parses MyST to HTML/LaTeX/Word and follows the MyST Spec/AST. Viable to shell out and ingest HTML. Easier to get broad syntax, but adds Node dependency and potential performance overhead per page.

There’s also a third pragmatic path we already started: extend `mistune` to accept MyST syntax (colon fences, options lines, common directives) without full spec compliance.

### Options

- Option A: Python myst-parser + `docutils` HTML writer (no Sphinx runtime)
  - Scope: Parse MyST into a `docutils` AST; render HTML with `docutils`; rely on myst-parser’s directive/role support.
  - Coverage: Core MyST + a subset of directives; many Sphinx-provided directives (e.g., sphinx-design tabs/cards) would be missing unless we port them.
  - Integrations: Keep Bengal’s post-processing (anchors, TOC, xrefs, variable substitution) as-is; or adapt around `docutils` output.
  - LoE: 2–3 days for baseline Parse→HTML path, wiring into `BaseMarkdownParser` and thread-local caching; +1–2 weeks if we aim to replicate popular Sphinx-only directives without Sphinx.
  - Risks: Directive/role coverage gaps vs. JupyterBook expectations; `docutils` HTML output semantics and CSS classes may differ from our themes; maintenance against myst-parser and `docutils` changes.

- Option B: JS `mystmd` CLI (shell-out)
  - Scope: Add a `myst` engine that calls `myst` CLI for each page, returns HTML.
  - Coverage: Broad MyST syntax by spec; potentially better alignment with MyST AST and future features.
  - Integrations: Keep Bengal post-processing (anchors, TOC, xrefs, variables). Variables would need to run pre-CLI, or we rely on MyST features instead; ensure we don’t double-handle anchors/TOC.
  - LoE: 1–2 days for a functional prototype (engine wrapper, error surfacing, caching, thread model, fallback when CLI missing); +1–2 days to optimize caching and configure a project-level toggle.
  - Risks: Adds Node dependency; per-page process cost; CLI version drift; mapping generated HTML classes to Bengal themes.

- Option C: Continue `mistune`-based MyST compatibility (status quo++)
  - Scope: We already support colon fences and some MyST-style options. Expand inline roles (e.g., ref, numref, abbrev), figure/table numbering, citations, and other commonly used MyST features as Mistune plugins.
  - Coverage: Target the 80/20 most-used MyST features for Sphinx migrations where full Sphinx extension parity isn’t required.
  - LoE: 3–6 days for core roles and options (design, implement, test, docs); more for advanced cross-referencing and numbering semantics.
  - Risks: Divergence from the canonical MyST AST/spec; ongoing maintenance for feature parity; but keeps Python-only, fast path, and our existing plugin model.

### Viability and Recommendation

- As an alternative to `mistune`: Yes, we can add a `myst` parser engine. The cleanest product story is a tiered approach:
  - Phase 1: Option B (`mystmd`) CLI as an “experimental” optional engine. Minimal LoE, wide syntax coverage, good for teams migrating from Sphinx and familiar with MyST. Keep `mistune` the default for speed.
  - Phase 2: Option C enhancements to `mistune` to cover the most-requested MyST features inline, preserving performance and Python-only dependency.
  - Phase 3 (optional): Option A if customers demand a Python-native MyST path without Node, accepting narrower directive coverage unless we port Sphinx directives.

This leverages Bengal’s engine-pluggability without forcing a global runtime shift. Projects migrating from Sphinx get a quick on-ramp (Option B), and we continue to deliver a fast path (Mistune) for mainstream static docs.

### Design Sketch (Option B)

- Add `bengal/rendering/parsers/myst.py` implementing `BaseMarkdownParser`:
  - Resolve `myst` CLI path at init; feature-detect version.
  - `parse()`: run CLI once per page (`stdin` content → `stdout` HTML), surface `stderr` as warnings; maintain thread-local instances holding CLI options.
  - `parse_with_toc()`: if CLI’s TOC differs from Bengal’s, prefer Bengal’s fast anchor+TOC extractor for consistency; otherwise honor CLI output and skip our TOC pass.
  - `parse_with_context()`: run Bengal variable substitution pre-CLI (to keep content semantics consistent across engines), then CLI, then Bengal’s usual post-processing (badges, xrefs).
  - Caching: Respect existing parsed-content cache by incorporating a `mystmd-<version>` parser version string.
  - Configuration:

```toml
[markdown]
parser = "myst"

[markdown.myst]
cli_path = "myst" # override if needed
args = ["--format", "html"]
```

### Estimated LoE

- Option B (`mystmd` CLI): 1–2 days to land MVP, 0.5–1 day hardening and docs.
- Option C (`mistune` + MyST features): 3–6 days for core roles and numbering; additional phases for citations/advanced semantics.
- Option A (Python myst-parser + `docutils`): 2–3 days for HTML baseline; +1–2 weeks if porting popular Sphinx-only directives.

### Risks and mitigation

- Directive parity: Set expectations—“experimental MyST engine” initially focuses on content fidelity, not full Sphinx extension parity. Document unsupported directives.
- Theming/class names: Provide a small compatibility CSS layer for myst-generated HTML where needed.
- Performance: Add an opt-in build flag to bypass myst CLI for unchanged pages via existing parsed-content cache. Consider batching or worker reuse if CLI overhead is noticeable.
- Supply chain: Pin CLI version in project docs; surface version in build logs to aid debugging.

### Decision

- Proceed with Option B as an optional engine (`parser = "myst"`), keeping `mistune` as default.
- In parallel, continue Option C improvements to close the 80/20 gap for MyST syntax directly in Mistune.

This provides an immediate migration story for Sphinx/MyST users with low engineering risk, while preserving Bengal’s performance and Python-first defaults.
