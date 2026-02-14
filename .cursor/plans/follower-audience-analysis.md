# GitHub Follower Audience Analysis

**Source:** [lbliii Followers](https://github.com/lbliii?tab=followers)  
**Date:** 2026-02-14  
**Purpose:** Inform Bengal ecosystem feature priorities and test coverage based on follower interests in AI, quantum, and crypto spaces.

---

## Executive Summary

Your 23 followers skew toward **AI/ML**, **quantum computing**, **crypto**, **technical documentation**, and **DevOps**. Several are high-reach (7K–24K followers). One follower (**sailorfe**) is an active contributor to Bengal and Patitas. The analysis suggests prioritizing: **math/LaTeX support**, **Rosettes language coverage** (Python, Solidity, C# already in place), **documentation tooling**, and **performance/parallelism** — all of which align with your current roadmap.

---

## Profile Breakdown by Domain

### AI / Machine Learning (6 profiles)

| Handle | Bio / Focus | Notable Projects | Reach |
|--------|-------------|------------------|-------|
| **seehiong** | PyTorch, TensorFlow, LangChain, MLflow, KubeFlow, Neural Networks, Kubernetes | multi-model-chat (GPT/Claude/Mistral/Ollama), md-editor-pro (Markdown + LaTeX), hdb-price-predictor (XGBoost), text-forge | 7,577 |
| **BEPb** | Neural networks, Python | Python-100-days, image_to_ascii | 24,601 |
| **riyad899** | Software Engineering Student, AI ML Enthusiast | crypto-genius, crypto-live-tracker | 104 |
| **JSv4** | Fullstack Legal Engineer, NLP | Delphic (LlamaIndex, Langchain, OpenAI), AtticusClassifier (BERT, Word2Vec, SPACY) | 546 |
| **standardgalactic** | Xanadu (quantum company) | 3D-MOOD (object detection), agent-world-model, Awesome-LLM-Reasoning-Failures | 18,238 |
| **Shackless** | CTO ShipBit, Svelte, UX | wingman-ai, pocket-tts (TTS) | 14 |

**Themes:** Python-heavy, LLM tooling, Markdown editors with LaTeX, multi-model comparison, NLP/legal AI.

---

### Quantum Computing (2 profiles)

| Handle | Bio / Focus | Notable Projects | Reach |
|--------|-------------|------------------|-------|
| **standardgalactic** | Xanadu (quantum computing company) | alphabet (research, cognition, physics), Snowflake-Labs/agent-world-model | 18,238 |
| **rasidi3112** | AI & Quantum Computing, Python, Flutter | — | — |

**Themes:** Quantum + AI crossover, research-heavy content, academic writing (LaTeX, PDFs).

---

### Crypto / Web3 (1 profile)

| Handle | Bio / Focus | Notable Projects | Reach |
|--------|-------------|------------------|-------|
| **riyad899** | AI ML Enthusiast, Web Developer | crypto-genius (CoinGecko API), crypto-live-tracker | 104 |

**Themes:** Solidity, real-time crypto data, React/JS frontends.

---

### Technical Writing / Documentation (2 profiles)

| Handle | Bio / Focus | Notable Projects | Reach |
|--------|-------------|------------------|-------|
| **sailorfe** | technical writer / python dev | **lbliii/bengal**, **lbliii/patitas**, pysweph, ephem, dita-ot/docs | 4 |
| **JSv4** | Fullstack Legal Engineer | Python-Redlines, Docxodus, OpenContracts | 546 |

**Themes:** Docs tooling, Markdown, DITA, Python. **sailorfe is a direct Bengal/Patitas contributor.**

---

### DevOps / Platform (2 profiles)

| Handle | Bio / Focus | Notable Projects | Reach |
|--------|-------------|------------------|-------|
| **nholuongut** | DevOps Engineer Lead, Vietnam | 90-Days-of-DevOps, android-ci, all-roadmaps | 7,042 |
| **esin** | Linux Admin, DevOps, Go | — | — |

**Themes:** CI/CD, Kubernetes, automation, performance.

---

### Web / Mobile (2 profiles)

| Handle | Bio / Focus | Notable Projects | Reach |
|--------|-------------|------------------|-------|
| **iamapuneet** | Flutter, mobile/web apps | Fire-Noti, flutter_ex_kit, dotted_line_flutter | 8,816 |
| **Shackless** | Svelte, C#/.NET | sveltesociety.dev, pocket-tts | 14 |

---

## Cross-Cutting Themes

| Theme | Count | Relevance to Bengal |
|-------|-------|---------------------|
| **Python** | 8+ | Core stack language; autodoc, Patitas, Kida |
| **Markdown / docs** | 6+ | Patitas, content authoring |
| **Code blocks / syntax** | 6+ | Rosettes, highlight caching |
| **LaTeX / math** | 2 (seehiong, standardgalactic) | Not in Bengal today; differentiator |
| **AI/LLM content** | 5+ | Docs for AI projects, API reference |
| **Performance** | 3+ | Parallel builds, incremental, free-threading |

---

## Stack Alignment Check

| Bengal Component | Follower Need | Current State |
|------------------|---------------|---------------|
| **Patitas** (Markdown) | Docs, AI content, tech blogs | ✅ Strong; sailorfe contributes |
| **Rosettes** (syntax) | Python, Solidity, C#, quantum DSLs? | ✅ Python, C#, Solidity in 0.2.0 |
| **Kida** (templates) | Custom layouts, API docs | ✅ In place |
| **Autodoc** | Python API reference | ✅ In place |
| **Math / LaTeX** | Papers, equations, quantum notation | ❌ Not supported |
| **Highlight cache** | Large code-heavy sites | 🔄 In 0.2.0 plan |
| **Pounce / dev server** | Fast iteration | 🔄 In 0.2.0 plan |

---

## Prioritization Matrix

### High Priority (Strong follower overlap + roadmap fit)

1. **Rosettes: Solidity & C# test coverage**
   - Rosettes 0.2.0 adds both; crypto (riyad899) and legal (JSv4) audiences use them.
   - **Action:** Ensure `test_solidity_sm.py` and `test_csharp_sm.py` have broad coverage; document in Rosettes languages reference.

2. **Highlight caching (0.2.0)**
   - AI/ML and quantum docs often have many code blocks; cache reduces build time.
   - **Action:** Ship block-level cache; consider persisted cache for large sites.

3. **Documentation experience**
   - sailorfe contributes; JSv4, seehiong, standardgalactic all produce docs.
   - **Action:** Keep docs-first workflow smooth; consider DITA/structured docs if demand appears.

### Medium Priority (Differentiation or future demand)

4. **Math / LaTeX support**
   - seehiong (md-editor-pro), standardgalactic (academic content) need equations.
   - **Action:** RFC for Patitas math directive or MyST-style `$...$` / `$$...$$`; evaluate KaTeX vs MathJax.

5. **Quantum / niche language lexers**
   - standardgalactic (Xanadu) may use PennyLane, Qiskit, or custom DSLs.
   - **Action:** Track demand; add PennyLane/Python quantum snippets if requested; low effort if Python lexer suffices.

6. **Performance observability**
   - nholuongut (DevOps) cares about build speed and CI.
   - **Action:** `--explain`, `--dry-run` already in place; document incremental build behavior for large sites.

### Lower Priority (Nice to have)

7. **Svelte / React integration**
   - Shackless (Svelte), seehiong (React) build SPAs; Bengal is static-first.
   - **Action:** Ensure static export and asset handling work well; no SPA framework needed.

8. **Flutter / mobile**
   - iamapuneet (Flutter) — minimal overlap with static site gen.
   - **Action:** None unless docs-for-mobile-SDK use case emerges.

---

## Test Coverage Recommendations

| Area | Rationale | Suggested Focus |
|------|------------|-----------------|
| **Rosettes: Solidity** | Crypto audience | Contract keywords, modifiers, events, inheritance |
| **Rosettes: C#** | Legal/enterprise (JSv4) | Async/await, LINQ, attributes |
| **Rosettes: Python** | Universal | Type hints, match, async, 3.14 syntax |
| **Patitas: Math** (if added) | AI/quantum papers | Inline `$x^2$`, block `$$\sum$$`, escaping |
| **Highlight cache** | Large code-heavy sites | Cache hit/miss, key stability, thread safety |
| **Incremental build** | DevOps, large sites | Taxonomy, autodoc, content-hash invalidation |

---

## Summary: What to Prioritize

| Priority | Feature / Area | Follower Signal |
|----------|----------------|-----------------|
| **P0** | Rosettes 0.2.0 (Solidity, C#, highlight cache) | Crypto, legal, AI code blocks |
| **P0** | Documentation DX (sailorfe, JSv4) | Active contributor + legal docs |
| **P1** | Math/LaTeX RFC | seehiong, standardgalactic |
| **P1** | Performance docs for large sites | nholuongut, AI/quantum content |
| **P2** | Quantum-specific lexers | standardgalactic (Xanadu) — monitor |

---

## Data Sources

- [lbliii Followers](https://github.com/lbliii?tab=followers)
- Individual profile pages (seehiong, BEPb, riyad899, JSv4, standardgalactic, sailorfe, iamapuneet, nholuongut, Shackless)
- Bengal ecosystem: `site/content/docs/about/ecosystem.md`
- Rosettes languages: `rosettes/site/content/docs/reference/languages.md`
- Bengal 0.2.0 plan: `.cursor/plans/bengal-0.2.0.plan.md`
