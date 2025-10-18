# Bengal Docs Scale Roadmap: Eating Sphinx's Lunch (5K+ Page Sites)

## Overview
Bengal's goal is to become the modern, fast alternative to Sphinx for large documentation sites (5K+ pages). Sphinx is slow, outdated, and Python-centric; Bengal will excel with incremental builds (18-42x faster), AI-native features, interactive UX, and broad language support.

**Key Differentiators**:
- **Speed**: Parallel/incremental builds, memory-optimized for massive sites.
- **Modern UX**: Interactive components, LLM exports, beautiful themes.
- **Ease**: Markdown-first, auto-doc for Python/CLI/OpenAPI, simple config.
- **Scale**: Handle 10K+ pages without config bloat; versioning, multi-lang.

This roadmap builds on `feature-solidification-plan.md`, focusing on docs presets. Track progress in CHANGELOG.md and benchmarks in `performance/`.

## 1. Assess & Benchmark (Immediate: 1-2 Weeks)
Measure current capabilities and Sphinx gaps to guide priorities.

- **Create Benchmarks** (Effort: 1 day)
  - Synthetic 5K-page docs site (e.g., auto-gen from Sphinx/NumPy docs).
  - Metrics: Build time (full/incremental), memory, output size, search speed.
  - Compare: Bengal vs Sphinx, Hugo, MkDocs.
  - Extend `performance/benchmark_template_complexity.py` for docs loads (cross-refs, TOCs).
  - Target: <5min full build, <1s incremental for 5K pages.
  - Output: `plan/active/docs-benchmark.md` with results; add to CI.

- **Audit Large Docs Pain Points** (Effort: 1 week)
  - Survey Sphinx users (Reddit/HN): Slow apidoc, navigation issues.
  - Convert mid-size Sphinx project (e.g., Click docs) via `bengal new --from-sphinx`.
  - Test real sites: Identify bottlenecks (e.g., autodoc on large repos).

**Milestone**: PR with benchmarks + audit. CHANGELOG: "Benchmarked for 5K+ scalability."

## 2. Short-Term: Stabilize & Scale Basics (0.2.0 - 1 Month)
Fix brittleness (e.g., renderer context hacks), ensure 1K-5K page reliability.

- **Performance Hardening** (Effort: 1-2 weeks)
  - Streaming Builds: Enhance `orchestration/streaming.py` with knowledge graph (hub-first rendering). Goal: 80-90% memory reduction.
  - Parallel Autodoc: Multi-thread module scanning (`concurrent.futures` for I/O).
  - Cache Docs-Deps: `cache/dependency_tracker.py` for autodoc hashes; incremental apidoc.
  - Test: 5K-page site <2min build.

- **Docs-Specific Polish** (Effort: 2 weeks)
  - Autodoc Depth: Type hints (`inspect`), private members (opt-in), cross-refs (`@see`).
  - CLI: `bengal autodoc --sphinx-compat`.
  - Navigation: Virtual root section to generalize renderer context (fix doc/list.html brittleness).
  - Search: Lunr.js + Whoosh fallback for 10K+ pages.
  - Presets: Sphinx-like index gen, cascade for versions.
  - Test: Migrate 1K-page Sphinx site (e.g., Requests).

**Milestone**: 0.2.0 "Sphinx Slayer." GETTING_STARTED.md: "From Sphinx to Bengal" guide.

## 3. Medium-Term: Docs-First Features (0.3.0 - 3 Months)
Differentiate: AI/modern web features for enterprise docs.

- **Advanced Autodoc & Integration** (Effort: Medium)
  - Sphinx Parity: reST bridge (`docutils`), diagrams (Mermaid), interactive code (Marimo).
  - Versioning: Multi-version support (`/v1.0/api/`), Git-tag auto-versioning, redirects.
  - Cross-Refs: Enhance `template_functions/crossref.py` for `:ref:`, inter-repo links (GitHub API).
  - OpenAPI/CLI: Swagger embeds, subcommand examples.
  - Test: FastAPI migration.

- **UX & Scalability** (Effort: 1-2 months)
  - Interactive: API explorers (Tabulator), collapsible sections, Q&A search (embeddings).
  - Multi-Lang: Prefix + auto-translation (DeepL hooks).
  - Health: Validators for broken refs, outdated APIs (`health/` expansion).
  - Memory: Graph-based partial builds (changed subtrees).
  - Test: Kubernetes docs migration (5K+ pages).

**Milestone**: 0.3.0 "Enterprise Docs Ready." Blog: "Bengal vs Sphinx: 10x Faster for 5K Pages."

## 4. Long-Term: Ecosystem & Domination (1.0+ - 6-12 Months)
Build the full platform.

- **Plugins/Extensibility**: Renderers for Sphinx extensions; themes marketplace.
- **Integrations**: GitHub Actions "Bengal Docs CI"; VS Code live preview.
- **AI-Powered**: LLM summaries, suggest sections, advanced search.
- **Deployment**: Vercel/Netlify one-click; edge caching.
- **Community**: Sphinx migration docs, PyCon talks, 100+ stars goal.
- **Monetization**: Free core; pro for unlimited pages/premium themes.

**Milestone**: 1.0 "Docs Platform." 10+ migrated projects.

## Risks & Mitigation
- **Perf Regressions**: CI benchmarks on 5K synthetic site.
- **Complexity**: Optional `bengal[docs]` extra; keep core lean.
- **Adoption**: Python-first (autodoc wins), then JS/Rust; free migration tools.
- **Competition**: Beat Hugo/MkDocs on autodoc, Docusaurus on speed.

## Next Steps
- Week 1: Run benchmarks, file PR for `docs-benchmark.md`.
- Prioritize: Autodoc depth or virtual root section?
- Track: Use todo_write for tasks; update `feature-solidification-plan.md`.

*Last Updated: Oct 14, 2025*
