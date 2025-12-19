# Competitive Analysis: Bengal vs. Major SSGs

**Status:** Draft  
**Date:** December 2025  
**Purpose:** Evaluate Bengal's default features and theme against leading static site generators

---

## Executive Summary

Bengal occupies a unique position as a **Python-native documentation SSG** with batteries-included features. This analysis compares Bengal against:

1. **MkDocs Material** - Direct Python ecosystem competitor
2. **Hugo** - Performance benchmark leader
3. **Docusaurus** - React-based documentation leader
4. **Sphinx** - Traditional Python documentation
5. **Eleventy** - Minimalist JavaScript SSG
6. **Jekyll** - Legacy Ruby-based SSG

**Key Finding:** Bengal's differentiators are AST-based autodoc, query indexes for O(1) lookups, and a comprehensive default theme—but it faces gaps in versioning, i18n, and community ecosystem size.

---

## Feature Comparison Matrix

### Core Build Features

| Feature | Bengal | MkDocs Material | Hugo | Docusaurus | Sphinx | Eleventy |
|---------|--------|----------------|------|------------|--------|----------|
| **Language** | Python 3.14+ | Python 3.8+ | Go | React/Node | Python 3.9+ | JavaScript |
| **Template Engine** | Jinja2 | Jinja2 | Go Templates | React/MDX | Jinja2/RST | Multiple |
| **Build Speed** | ~200 pages/s | ~100 pages/s | ~10,000 pages/s | ~50 pages/s | ~30 pages/s | ~500 pages/s |
| **Incremental Builds** | ✅ Yes (18-42x faster) | ❌ No | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes |
| **Parallel Builds** | ✅ Yes (free-threading) | ❌ No | ✅ Yes | ✅ Yes | ❌ Limited | ❌ No |
| **Cache System** | ✅ Zstd compressed | ❌ No | ✅ Yes | ✅ Yes | ✅ Pickle | ❌ No |
| **Streaming/Large Sites** | ✅ Yes (5K+ pages) | ⚠️ Memory issues | ✅ Yes | ⚠️ Memory issues | ⚠️ Memory issues | ✅ Yes |

**Bengal Advantage:** Python-native with true incremental builds and Zstd cache compression (12-14x smaller).  
**Bengal Gap:** Hugo is 50x faster in raw build speed.

---

### Content Authoring

| Feature | Bengal | MkDocs Material | Hugo | Docusaurus | Sphinx | Eleventy |
|---------|--------|----------------|------|------------|--------|----------|
| **Markdown Flavor** | MyST-compatible | Python-Markdown | Goldmark | MDX | reStructuredText/MyST | Multiple |
| **Frontmatter** | YAML/TOML | YAML | YAML/TOML/JSON | YAML | ❌ (docinfo) | YAML/JSON |
| **Admonitions** | ✅ 8 types | ✅ 12+ types | ⚠️ Shortcodes | ✅ MDX | ✅ Directives | ❌ Plugin |
| **Tabs** | ✅ Native | ✅ Native | ⚠️ Shortcode | ✅ Native | ✅ Plugin | ❌ Plugin |
| **Code Blocks** | ✅ Pygments + copy | ✅ Pygments + copy | ✅ Chroma + copy | ✅ Prism + copy | ✅ Pygments | ⚠️ Plugin |
| **Code Annotations** | ❌ Not yet | ✅ Yes | ❌ No | ❌ No | ❌ No | ❌ No |
| **Dropdowns** | ✅ Native | ✅ Native | ⚠️ Shortcode | ✅ Native | ✅ Plugin | ❌ Plugin |
| **Cards/Grids** | ✅ Native | ✅ Native | ⚠️ Shortcode | ✅ Native | ⚠️ Plugin | ❌ Plugin |
| **Steps/Procedures** | ✅ Native | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |
| **List Tables** | ✅ Native | ❌ No | ❌ No | ❌ No | ✅ Native | ❌ No |
| **Math (LaTeX)** | ✅ Native | ✅ Plugin | ✅ Plugin | ✅ Plugin | ✅ Native | ❌ Plugin |
| **Mermaid Diagrams** | ✅ Native | ✅ Plugin | ❌ Plugin | ✅ Plugin | ❌ Plugin | ❌ Plugin |
| **Task Lists** | ✅ Native | ✅ Native | ✅ Native | ✅ Native | ❌ No | ✅ Native |
| **Footnotes** | ✅ Native | ✅ Native | ✅ Native | ❌ Plugin | ✅ Native | ⚠️ Plugin |
| **Definition Lists** | ✅ Native | ✅ Plugin | ⚠️ No | ❌ No | ✅ Native | ❌ No |
| **Glossary Terms** | ✅ Native | ❌ Plugin | ❌ No | ❌ No | ✅ Native | ❌ No |
| **Variable Substitution** | ✅ `{{ var }}` | ⚠️ Plugin | ✅ Params | ❌ No | ✅ `|var|` | ⚠️ Data files |
| **Cross-References** | ✅ `[[link]]` | ⚠️ Plugin | ⚠️ Relref | ⚠️ Manual | ✅ `:ref:` | ❌ No |

**Bengal Advantage:** Steps directive, list-table, glossary terms, and cross-references are all native.  
**Bengal Gap:** Code annotations (MkDocs Material's killer feature).

---

### Auto-Generated Documentation

| Feature | Bengal | MkDocs Material | Hugo | Docusaurus | Sphinx | Eleventy |
|---------|--------|----------------|------|------------|--------|----------|
| **Python API Docs** | ✅ AST-based (no imports) | ⚠️ mkdocstrings (imports) | ❌ No | ❌ No | ✅ autodoc (imports) | ❌ No |
| **CLI Reference** | ✅ Click/Typer/argparse | ⚠️ mkdocs-click (Click only) | ❌ No | ❌ No | ⚠️ sphinx-click | ❌ No |
| **OpenAPI/Swagger** | ✅ Native rendering | ⚠️ Plugin | ⚠️ Plugin | ⚠️ Plugin | ⚠️ Plugin | ❌ No |
| **TypeScript Docs** | ❌ No | ❌ No | ❌ No | ✅ TypeDoc | ❌ No | ❌ No |
| **Safe Execution** | ✅ No code execution | ❌ Imports modules | N/A | N/A | ❌ Imports modules | N/A |

**Bengal Advantage:** AST-based autodoc is **unique**—generates API docs without importing code, making it safe for any Python project.  
**Bengal Gap:** No TypeScript/JavaScript API docs.

---

### Navigation & Structure

| Feature | Bengal | MkDocs Material | Hugo | Docusaurus | Sphinx | Eleventy |
|---------|--------|----------------|------|------------|--------|----------|
| **Hierarchical Sections** | ✅ Auto from dirs | ✅ nav.yml | ✅ _index.md | ✅ sidebar.js | ✅ toctree | ❌ Manual |
| **Sidebar Navigation** | ✅ Auto-generated | ✅ Auto + manual | ⚠️ Theme-dependent | ✅ Auto + manual | ✅ toctree | ❌ Manual |
| **Breadcrumbs** | ✅ Native | ✅ Native | ⚠️ Theme | ✅ Native | ✅ Plugin | ❌ Manual |
| **TOC (In-Page)** | ✅ Sticky + scroll spy | ✅ Sticky + scroll spy | ⚠️ Theme | ✅ Native | ✅ Native | ❌ Manual |
| **Prev/Next Links** | ✅ Native | ✅ Native | ⚠️ Theme | ✅ Native | ✅ Native | ❌ Manual |
| **Related Posts** | ✅ Tag-based | ❌ No | ⚠️ Theme | ❌ No | ❌ No | ❌ No |
| **Back to Top** | ✅ Native | ✅ Native | ⚠️ Theme | ✅ Native | ❌ No | ❌ No |
| **Menus** | ✅ Flexible nesting | ⚠️ nav.yml only | ✅ Menus API | ✅ Navbar | ❌ Manual | ❌ Manual |

**Bengal Advantage:** Fully automatic navigation from directory structure, no configuration required.  
**Bengal Gap:** No versioned documentation support (Docusaurus/MkDocs excel here).

---

### Search & Discovery

| Feature | Bengal | MkDocs Material | Hugo | Docusaurus | Sphinx | Eleventy |
|---------|--------|----------------|------|------------|--------|----------|
| **Built-in Search** | ✅ Lunr.js | ✅ Lunr.js + custom | ⚠️ Theme | ✅ Algolia + local | ❌ Plugin | ❌ No |
| **Search Highlighting** | ✅ Yes | ✅ Yes | ⚠️ Theme | ✅ Yes | ⚠️ Plugin | ❌ No |
| **Search Suggestions** | ✅ Yes | ✅ Yes | ⚠️ Theme | ✅ Yes | ❌ No | ❌ No |
| **Algolia DocSearch** | ❌ Not yet | ✅ Native | ⚠️ Theme | ✅ Native | ⚠️ Plugin | ❌ No |
| **LLM-Friendly Output** | ✅ llm.txt generation | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |

**Bengal Advantage:** LLM-friendly text output (`llm.txt`) is unique.  
**Bengal Gap:** No Algolia DocSearch integration.

---

### Theme & Appearance

| Feature | Bengal | MkDocs Material | Hugo | Docusaurus | Sphinx | Eleventy |
|---------|--------|----------------|------|------------|--------|----------|
| **Default Theme** | ✅ Modern, complete | ✅ Material Design | ❌ None (pick theme) | ✅ Modern | ⚠️ Basic (alabaster) | ❌ None |
| **Dark Mode** | ✅ System + toggle | ✅ System + toggle | ⚠️ Theme | ✅ System + toggle | ⚠️ Theme | ❌ No |
| **Design Tokens** | ✅ ~200 CSS vars | ✅ Extensive | ⚠️ Theme | ✅ CSS vars | ⚠️ Theme | ❌ No |
| **Responsive Design** | ✅ Mobile-first | ✅ Mobile-first | ⚠️ Theme | ✅ Mobile-first | ⚠️ Theme | ❌ No |
| **WCAG Compliance** | ✅ AA | ✅ AA | ⚠️ Theme | ✅ AA | ⚠️ Theme | ❌ No |
| **Print Styles** | ✅ Optimized | ✅ Optimized | ⚠️ Theme | ⚠️ Basic | ⚠️ Theme | ❌ No |
| **Icon Library** | ✅ Phosphor (100+) | ✅ Material Icons | ⚠️ Theme | ✅ FontAwesome | ❌ No | ❌ No |
| **Theme Customization** | ✅ Swizzle templates | ✅ Override blocks | ✅ Theme inheritance | ✅ Swizzle | ✅ Override | ✅ Full control |
| **Component Library** | ✅ 14 partials + preview | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |
| **Palettes/Brands** | ✅ Multiple brand colors | ✅ Primary/accent | ⚠️ Theme | ✅ Custom CSS | ⚠️ Theme | ❌ No |

**Bengal Advantage:** Component library with live preview system, template swizzle with provenance tracking.  
**Bengal Gap:** MkDocs Material has more mature color/palette system.

---

### Performance Features

| Feature | Bengal | MkDocs Material | Hugo | Docusaurus | Sphinx | Eleventy |
|---------|--------|----------------|------|------------|--------|----------|
| **Query Indexes** | ✅ O(1) section/author/date | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |
| **Asset Fingerprinting** | ✅ Hash-based | ⚠️ Plugin | ✅ Native | ✅ Native | ❌ No | ⚠️ Plugin |
| **Lazy Loading** | ✅ Images | ✅ Images | ⚠️ Theme | ✅ Native | ❌ No | ❌ No |
| **Code Splitting** | ❌ No | ❌ No | ❌ No | ✅ Native | ❌ No | ❌ No |
| **Image Optimization** | ⚠️ Basic | ⚠️ Plugin | ✅ Native | ✅ Native | ❌ No | ⚠️ Plugin |

**Bengal Advantage:** Query indexes provide 10,000x speedup for common template lookups on large sites.  
**Bengal Gap:** No image optimization pipeline.

---

### Developer Experience

| Feature | Bengal | MkDocs Material | Hugo | Docusaurus | Sphinx | Eleventy |
|---------|--------|----------------|------|------------|--------|----------|
| **Dev Server** | ✅ Hot reload | ✅ Hot reload | ✅ Hot reload | ✅ Hot reload | ✅ Hot reload | ✅ Hot reload |
| **Health Checks** | ✅ Native validation | ❌ No | ❌ No | ❌ No | ✅ linkcheck | ❌ No |
| **Link Checking** | ✅ Built-in | ⚠️ Plugin | ⚠️ Plugin | ⚠️ Plugin | ✅ Built-in | ❌ Plugin |
| **Graph Analysis** | ✅ Orphan detection | ❌ No | ❌ No | ⚠️ Plugin | ❌ No | ❌ No |
| **Auto-Fix Issues** | ✅ `bengal fix` | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |
| **Scaffolding** | ✅ `bengal new` | ✅ `mkdocs new` | ✅ `hugo new` | ✅ `create-docusaurus` | ✅ `sphinx-quickstart` | ⚠️ Manual |
| **Type Hints** | ✅ Fully typed | ⚠️ Partial | N/A (Go) | ✅ TypeScript | ⚠️ Partial | ⚠️ Partial |

**Bengal Advantage:** Comprehensive health validation system with auto-fix capability.  
**Bengal Gap:** None significant.

---

### Content Delivery

| Feature | Bengal | MkDocs Material | Hugo | Docusaurus | Sphinx | Eleventy |
|---------|--------|----------------|------|------------|--------|----------|
| **Sitemap** | ✅ Auto | ✅ Plugin | ✅ Native | ✅ Native | ⚠️ Plugin | ⚠️ Plugin |
| **RSS Feed** | ✅ Auto | ⚠️ Plugin | ✅ Native | ✅ Plugin | ❌ No | ⚠️ Plugin |
| **JSON Feed** | ✅ Per-page | ❌ No | ✅ Native | ❌ No | ❌ No | ❌ No |
| **404 Page** | ✅ Template | ✅ Template | ✅ Template | ✅ Template | ❌ Manual | ❌ Manual |
| **Redirects** | ⚠️ Config-based | ✅ Plugin | ✅ Aliases | ✅ Plugin | ❌ Manual | ⚠️ Plugin |

**Bengal Advantage:** Per-page JSON output for headless CMS integration.  
**Bengal Gap:** None significant.

---

### Ecosystem & Extensibility

| Feature | Bengal | MkDocs Material | Hugo | Docusaurus | Sphinx | Eleventy |
|---------|--------|----------------|------|------------|--------|----------|
| **Themes Available** | 1 (default) | 1 (Material) | 300+ | 10+ | 50+ | 100+ |
| **Plugin Ecosystem** | ⚠️ Emerging | ✅ 50+ plugins | ✅ Built-in | ✅ 100+ plugins | ✅ 1000+ extensions | ✅ 100+ plugins |
| **Remote Content** | ✅ GitHub/Notion/REST | ⚠️ Plugin | ⚠️ Modules | ⚠️ Plugin | ❌ No | ⚠️ Data files |
| **Custom Directives** | ✅ Python API | ⚠️ Plugin | ✅ Shortcodes | ✅ MDX/React | ✅ Sphinx API | ✅ Filters |
| **i18n/Multilingual** | ❌ Not yet | ✅ Native | ✅ Native | ✅ Native | ✅ Native | ⚠️ Manual |
| **Versioning** | ❌ Not yet | ✅ mike | ⚠️ Manual | ✅ Native | ✅ Native | ❌ No |

**Bengal Advantage:** Remote content sources (GitHub, Notion, REST APIs) are first-class.  
**Bengal Gap:** **Critical gaps in i18n and versioning.** Only 1 theme.

---

## Detailed Competitor Analysis

### MkDocs Material — Primary Python Competitor

**Strengths:**
- Most polished documentation theme in the Python ecosystem
- Code annotations are a killer feature (inline explanations)
- Excellent search with custom tokenizers
- Versioning via mike
- Huge community adoption (FastAPI, Pydantic, etc.)

**Weaknesses:**
- No incremental builds (rebuild entire site)
- Plugin-dependent for many features
- mkdocstrings imports code (unsafe for some projects)
- No streaming for large sites

**Bengal's Competitive Position:**
- ✅ Beat them on: Incremental builds, AST-based autodoc safety, query indexes, streaming
- ❌ Behind on: Code annotations, versioning, community size, polish

**Strategic Recommendation:** Add code annotations as high-priority feature.

---

### Hugo — Performance Benchmark

**Strengths:**
- 50x faster build times
- Massive theme ecosystem (300+)
- Mature, battle-tested
- Excellent multilingual support

**Weaknesses:**
- Go templates have steep learning curve
- No default theme (must choose one)
- Documentation-specific features require themes/shortcodes
- No Python API docs

**Bengal's Competitive Position:**
- ✅ Beat them on: Default theme quality, Python autodoc, directives out-of-box
- ❌ Behind on: Raw speed, theme ecosystem, i18n, community

**Strategic Recommendation:** Position as "Hugo for Python developers who want batteries-included."

---

### Docusaurus — React Documentation Leader

**Strengths:**
- Excellent versioning system
- MDX allows React components in docs
- Strong TypeScript support
- Algolia DocSearch integration

**Weaknesses:**
- Requires Node.js ecosystem
- React knowledge needed for customization
- No Python API docs
- Memory-heavy for large sites

**Bengal's Competitive Position:**
- ✅ Beat them on: Python-native, no Node.js, AST autodoc, query indexes
- ❌ Behind on: Versioning, MDX flexibility, Algolia integration

**Strategic Recommendation:** Implement versioning as high-priority feature.

---

### Sphinx — Traditional Python Docs

**Strengths:**
- Industry standard for Python library docs
- Massive extension ecosystem
- Cross-reference system is unmatched
- ReadTheDocs integration

**Weaknesses:**
- reStructuredText learning curve
- Slow builds
- Dated default theme (alabaster)
- Complex configuration

**Bengal's Competitive Position:**
- ✅ Beat them on: Modern theme, Markdown-first, speed, UX
- ❌ Behind on: Extension ecosystem, ReadTheDocs integration, cross-references

**Strategic Recommendation:** Position as "modern Sphinx alternative for new projects."

---

## Summary: Bengal's Competitive Position

### 🟢 Clear Advantages (Unique or Best-in-Class)

| Feature | Why It Matters |
|---------|---------------|
| **AST-Based Autodoc** | No code execution = safe for any Python project |
| **Query Indexes** | O(1) lookups = 10,000x faster templates on large sites |
| **Component Library + Preview** | Storybook-like development for theme components |
| **Steps Directive** | Native step-by-step procedures (no one else has this) |
| **LLM-Friendly Output** | `llm.txt` for AI training/consumption |
| **Health Validation + Fix** | Built-in quality checks with auto-remediation |
| **Remote Content Sources** | GitHub/Notion/REST APIs as first-class sources |
| **Incremental Builds** | 18-42x faster rebuilds with dependency tracking |

### 🟡 Competitive Parity

| Feature | Notes |
|---------|-------|
| **Default Theme** | On par with MkDocs Material, ahead of Hugo/Sphinx |
| **Directives** | Comprehensive, matches or exceeds most competitors |
| **Search** | Solid Lunr.js implementation |
| **Dev Server** | Hot reload works well |

### 🔴 Critical Gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| **Versioning** | Blocks enterprise adoption | 🔥 High |
| **i18n/Multilingual** | Blocks international projects | 🔥 High |
| **Code Annotations** | MkDocs Material's killer feature | 🔥 High |
| **Algolia DocSearch** | Expected for large doc sites | Medium |
| **Theme Ecosystem** | Only 1 theme limits adoption | Medium |
| **Image Optimization** | Expected in 2025 | Medium |
| **Raw Build Speed** | 50x slower than Hugo | Low (acceptable) |

---

## Recommended Roadmap Priorities

### Phase 1: Close Critical Gaps
1. **Versioned Documentation** — Multiple versions in single site
2. **Code Annotations** — Inline explanations for code blocks
3. **i18n Framework** — Multilingual content support

### Phase 2: Ecosystem Growth
4. **Algolia DocSearch** — Enterprise search integration
5. **ReadTheDocs Integration** — Hosting platform support
6. **Plugin API** — Formalize extension points

### Phase 3: Performance & Polish
7. **Image Optimization Pipeline** — WebP conversion, responsive images
8. **Additional Themes** — 2-3 alternative themes
9. **Build Speed Improvements** — Target 500+ pages/s

---

## Appendix: Market Positioning Statement

> **Bengal** is a Python-native static site generator for developers who want Hugo-level features without leaving the Python ecosystem. It's the only SSG with safe, AST-based Python autodoc, O(1) query indexes for large sites, and a modern batteries-included theme—making it ideal for technical documentation, blogs, and mixed-content sites.

**Target Audience:**
- Python developers documenting libraries
- Teams using FastAPI/Django who want Python-native tooling
- Projects that need autodoc without code execution risks
- Large documentation sites (1000+ pages) needing performance

**Not For:**
- Projects requiring versioned docs (until implemented)
- Multilingual sites (until implemented)
- Users wanting maximum theme choice (Hugo/Jekyll better)
- Teams already invested in React/MDX (Docusaurus better)
