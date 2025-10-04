# Bengal SSG - Comprehensive Example Site Rewrite Plan

**Date:** October 4, 2025  
**Status:** Planning Phase  
**Goal:** Create a world-class example site that showcases ALL Bengal features comprehensively

---

## 📊 Current State Analysis

### What the Example Site Currently Has

**Structure:**
```
examples/quickstart/content/
├── index.md                    # Basic homepage
├── about.md                    # Simple about page
├── contact.md                  # Simple contact page
├── docs/                       # 10 documentation pages
├── posts/                      # 13 blog posts
├── tutorials/                  # 3 tutorials
├── guides/                     # 3 guides
├── products/                   # 3 product pages
└── api/                        # 4 API documentation pages
```

**Documentation Coverage:**
- ✅ Incremental builds
- ✅ Parallel processing
- ✅ Template system basics
- ✅ Cascading frontmatter
- ✅ Content organization
- ✅ Configuration reference
- ✅ Advanced markdown
- ✅ Cross-references
- ✅ Mistune features

**What's Missing or Inadequate:**
- ❌ No comprehensive template function reference (0 of 75 functions documented)
- ❌ No examples of Mistune directives (tabs, dropdown, code-tabs, admonitions)
- ❌ No health check system showcase
- ❌ No output formats demonstration (JSON, LLM-txt)
- ❌ Limited navigation/menu system examples
- ❌ No variable substitution examples
- ❌ Minimal cross-reference usage
- ❌ No theming guide
- ❌ No plugin development guide
- ❌ Posts don't showcase advanced features
- ❌ No interactive examples
- ❌ No "kitchen sink" demo page
- ❌ No comparison with other SSGs
- ❌ No migration guides

---

## 🎯 Product Features vs Example Coverage

### Core Performance Features

| Feature | Implemented | Example Coverage | Gap |
|---------|-------------|------------------|-----|
| Incremental builds (18-42x) | ✅ | ✅ Good | Minor improvements |
| Parallel processing (2-4x) | ✅ | ✅ Good | Minor improvements |
| Multiple markdown engines | ✅ | ⚠️ Partial | Need comparison |
| Build stats/metrics | ✅ | ❌ None | Missing |

### Content & Templates

| Feature | Implemented | Example Coverage | Gap |
|---------|-------------|------------------|-----|
| 75 Template functions | ✅ | ❌ None | **MAJOR GAP** |
| Navigation system | ✅ | ⚠️ Partial | Need showcase |
| Menu system | ✅ | ✅ Good | Minor improvements |
| Cascade system | ✅ | ✅ Good | Examples needed |
| Taxonomy system | ✅ | ⚠️ Partial | Examples needed |
| Table of contents | ✅ | ⚠️ Partial | Showcase needed |

### Markdown & Plugins

| Feature | Implemented | Example Coverage | Gap |
|---------|-------------|------------------|-----|
| Variable substitution | ✅ | ❌ None | **MAJOR GAP** |
| Cross-references [[link]] | ✅ | ❌ Minimal | **MAJOR GAP** |
| Admonitions (9 types) | ✅ | ❌ None | **MAJOR GAP** |
| Tabs directive | ✅ | ❌ None | **MAJOR GAP** |
| Dropdown directive | ✅ | ❌ None | **MAJOR GAP** |
| Code-tabs directive | ✅ | ❌ None | **MAJOR GAP** |
| GFM tables, footnotes | ✅ | ⚠️ Minimal | Need more examples |

### Development & Quality

| Feature | Implemented | Example Coverage | Gap |
|---------|-------------|------------------|-----|
| Health checks (9 validators) | ✅ | ❌ None | **MAJOR GAP** |
| Dev server with hot reload | ✅ | ⚠️ Mentioned | Need guide |
| Link validation | ✅ | ❌ None | Missing |
| Build profiling | ✅ | ❌ None | Missing |

### Output & SEO

| Feature | Implemented | Example Coverage | Gap |
|---------|-------------|------------------|-----|
| Sitemap generation | ✅ | ✅ Good | OK |
| RSS feeds | ✅ | ✅ Good | OK |
| Output formats (JSON, LLM) | ✅ | ❌ None | **MAJOR GAP** |
| SEO meta tags | ✅ | ⚠️ Partial | Need guide |

---

## 🚀 Comprehensive Rewrite Plan

### Philosophy

The new example site should be:
1. **Self-documenting** - Showcases every feature by using it
2. **Educational** - Teaches best practices through examples
3. **Beautiful** - Demonstrates Bengal's aesthetic capabilities
4. **Comprehensive** - Covers ALL 75+ features
5. **Practical** - Real-world patterns, not toy examples
6. **Interactive** - Uses directives, tabs, dropdowns effectively
7. **Discoverable** - Good navigation, search-ready content

### Target Audience

1. **New users** - Getting started quickly
2. **Migrators** - Coming from Hugo/Jekyll/11ty/MkDocs
3. **Advanced users** - Deep dives into features
4. **Contributors** - Understanding architecture
5. **AI/LLM systems** - Machine-readable content via output formats

---

## 📁 Proposed New Structure

```
examples/showcase/  (new comprehensive example)
├── bengal.toml                 # Fully configured with all features
├── content/
│   ├── index.md                # Homepage: Feature overview
│   │
│   ├── docs/                   # COMPREHENSIVE DOCUMENTATION
│   │   ├── _index.md           # Docs hub
│   │   │
│   │   ├── getting-started/    # 🟢 Onboarding
│   │   │   ├── _index.md
│   │   │   ├── installation.md
│   │   │   ├── quick-start.md
│   │   │   ├── first-site.md
│   │   │   ├── project-structure.md
│   │   │   └── next-steps.md
│   │   │
│   │   ├── core-concepts/      # 🔵 Understanding Bengal
│   │   │   ├── _index.md
│   │   │   ├── architecture.md
│   │   │   ├── pages-and-sections.md
│   │   │   ├── frontmatter.md
│   │   │   ├── content-types.md
│   │   │   └── build-process.md
│   │   │
│   │   ├── markdown/           # 📝 Content Authoring
│   │   │   ├── _index.md
│   │   │   ├── basic-syntax.md
│   │   │   ├── gfm-features.md
│   │   │   ├── variable-substitution.md      # 🆕 {{ page.var }}
│   │   │   ├── cross-references.md           # 🆕 [[link]]
│   │   │   ├── admonitions.md                # 🆕 ```{note}
│   │   │   ├── tabs-and-dropdowns.md         # 🆕 ```{tabs}
│   │   │   ├── code-examples.md              # 🆕 ```{code-tabs}
│   │   │   └── kitchen-sink.md               # 🆕 ALL features in one page!
│   │   │
│   │   ├── templates/          # 🎨 Templating
│   │   │   ├── _index.md
│   │   │   ├── template-basics.md
│   │   │   ├── template-inheritance.md
│   │   │   ├── partials-and-includes.md
│   │   │   ├── custom-templates.md
│   │   │   └── function-reference/          # 🆕 75 FUNCTIONS DOCUMENTED!
│   │   │       ├── _index.md
│   │   │       ├── strings.md               # 11 functions
│   │   │       ├── collections.md           # 8 functions
│   │   │       ├── math.md                  # 6 functions
│   │   │       ├── dates.md                 # 3 functions
│   │   │       ├── urls.md                  # 3 functions
│   │   │       ├── content.md               # 6 functions
│   │   │       ├── data.md                  # 8 functions
│   │   │       ├── files.md                 # 3 functions
│   │   │       ├── images.md                # 6 functions
│   │   │       ├── seo.md                   # 4 functions
│   │   │       ├── debug.md                 # 3 functions
│   │   │       ├── taxonomies.md            # 4 functions
│   │   │       ├── pagination.md            # 3 functions
│   │   │       ├── crossref.md              # 5 functions
│   │   │       └── advanced-strings.md      # 3 functions
│   │   │
│   │   ├── navigation/         # 🧭 Site Navigation
│   │   │   ├── _index.md
│   │   │   ├── menus.md
│   │   │   ├── breadcrumbs.md
│   │   │   ├── next-prev-links.md
│   │   │   ├── table-of-contents.md
│   │   │   └── site-hierarchy.md
│   │   │
│   │   ├── organization/       # 📂 Content Management
│   │   │   ├── _index.md
│   │   │   ├── sections.md
│   │   │   ├── taxonomies.md
│   │   │   ├── cascading-frontmatter.md
│   │   │   ├── content-types.md
│   │   │   └── url-structure.md
│   │   │
│   │   ├── performance/        # ⚡ Speed & Optimization
│   │   │   ├── _index.md
│   │   │   ├── incremental-builds.md
│   │   │   ├── parallel-processing.md
│   │   │   ├── caching-strategy.md
│   │   │   ├── build-stats.md           # 🆕 Performance metrics
│   │   │   ├── benchmarks.md            # 🆕 vs other SSGs
│   │   │   └── optimization-tips.md
│   │   │
│   │   ├── theming/            # 🎨 Themes & Design
│   │   │   ├── _index.md
│   │   │   ├── default-theme.md
│   │   │   ├── creating-themes.md       # 🆕 Theme development
│   │   │   ├── customizing-themes.md
│   │   │   ├── theme-structure.md
│   │   │   └── design-system.md         # 🆕 CSS architecture
│   │   │
│   │   ├── assets/             # 📦 Static Assets
│   │   │   ├── _index.md
│   │   │   ├── asset-pipeline.md
│   │   │   ├── images.md
│   │   │   ├── css-and-js.md
│   │   │   └── optimization.md
│   │   │
│   │   ├── output/             # 📤 Build Output
│   │   │   ├── _index.md
│   │   │   ├── output-formats.md        # 🆕 JSON, LLM-txt
│   │   │   ├── sitemap-and-rss.md
│   │   │   ├── seo-optimization.md
│   │   │   └── structured-data.md
│   │   │
│   │   ├── quality/            # ✅ Quality Assurance
│   │   │   ├── _index.md
│   │   │   ├── health-checks.md         # 🆕 9 validators!
│   │   │   ├── link-validation.md
│   │   │   ├── error-handling.md
│   │   │   └── strict-mode.md
│   │   │
│   │   ├── development/        # 🛠️ Dev Workflow
│   │   │   ├── _index.md
│   │   │   ├── dev-server.md
│   │   │   ├── hot-reload.md
│   │   │   ├── debugging.md
│   │   │   └── troubleshooting.md
│   │   │
│   │   ├── deployment/         # 🚀 Production
│   │   │   ├── _index.md
│   │   │   ├── build-strategies.md
│   │   │   ├── hosting-options.md
│   │   │   ├── ci-cd.md
│   │   │   └── best-practices.md
│   │   │
│   │   ├── configuration/      # ⚙️ Config Reference
│   │   │   ├── _index.md
│   │   │   ├── site-settings.md
│   │   │   ├── build-options.md
│   │   │   ├── features.md
│   │   │   └── full-reference.md
│   │   │
│   │   └── advanced/           # 🔬 Advanced Topics
│   │       ├── _index.md
│   │       ├── plugin-development.md   # 🆕 Creating plugins
│   │       ├── extending-bengal.md
│   │       ├── custom-parsers.md
│   │       ├── architecture-deep-dive.md
│   │       └── performance-profiling.md
│   │
│   ├── tutorials/              # 📚 STEP-BY-STEP GUIDES
│   │   ├── _index.md
│   │   ├── build-a-blog/
│   │   │   ├── _index.md
│   │   │   ├── 01-setup.md
│   │   │   ├── 02-first-post.md
│   │   │   ├── 03-navigation.md
│   │   │   ├── 04-styling.md
│   │   │   └── 05-deployment.md
│   │   │
│   │   ├── documentation-site/
│   │   │   ├── _index.md
│   │   │   ├── 01-structure.md
│   │   │   ├── 02-navigation.md
│   │   │   ├── 03-search.md
│   │   │   └── 04-versioning.md
│   │   │
│   │   ├── portfolio/
│   │   │   ├── _index.md
│   │   │   ├── 01-homepage.md
│   │   │   ├── 02-projects.md
│   │   │   ├── 03-gallery.md
│   │   │   └── 04-contact.md
│   │   │
│   │   ├── custom-theme/
│   │   │   ├── _index.md
│   │   │   ├── 01-setup.md
│   │   │   ├── 02-templates.md
│   │   │   ├── 03-styles.md
│   │   │   └── 04-distribution.md
│   │   │
│   │   └── migration/          # 🆕 MIGRATION GUIDES
│   │       ├── _index.md
│   │       ├── from-hugo.md
│   │       ├── from-jekyll.md
│   │       ├── from-eleventy.md
│   │       └── from-mkdocs.md
│   │
│   ├── examples/               # 💡 REAL-WORLD EXAMPLES
│   │   ├── _index.md
│   │   ├── blog-layouts/
│   │   │   ├── _index.md
│   │   │   ├── classic-blog.md
│   │   │   ├── magazine-layout.md
│   │   │   └── minimal-blog.md
│   │   │
│   │   ├── documentation-patterns/
│   │   │   ├── _index.md
│   │   │   ├── api-docs.md
│   │   │   ├── user-guides.md
│   │   │   └── technical-specs.md
│   │   │
│   │   ├── landing-pages/
│   │   │   ├── _index.md
│   │   │   ├── product-launch.md
│   │   │   ├── saas-homepage.md
│   │   │   └── portfolio-showcase.md
│   │   │
│   │   └── special-features/
│   │       ├── _index.md
│   │       ├── search-integration.md
│   │       ├── commenting-systems.md
│   │       ├── analytics.md
│   │       └── social-sharing.md
│   │
│   ├── blog/                   # 📝 FEATURE-RICH BLOG
│   │   ├── _index.md
│   │   ├── 2025/
│   │   │   └── 10/
│   │   │       ├── introducing-bengal.md
│   │   │       ├── performance-benchmarks.md    # Uses charts/data
│   │   │       ├── template-functions-guide.md  # Showcases functions
│   │   │       ├── markdown-power-features.md   # All directives
│   │   │       ├── theming-best-practices.md    # Design patterns
│   │   │       ├── output-formats-explained.md  # JSON/LLM features
│   │   │       ├── health-checks-deep-dive.md   # Quality tools
│   │   │       └── incremental-builds-magic.md  # Performance
│   │   │
│   │   └── series/             # Blog series
│   │       ├── bengal-basics/
│   │       ├── advanced-techniques/
│   │       └── case-studies/
│   │
│   ├── showcase/               # 🎨 VISUAL DEMOS
│   │   ├── _index.md
│   │   ├── component-library.md        # All UI components
│   │   ├── directive-playground.md     # Interactive directive demos
│   │   ├── template-gallery.md         # Template examples
│   │   └── theme-preview.md            # Theme showcase
│   │
│   ├── comparison/             # ⚖️ VS OTHER SSGs
│   │   ├── _index.md
│   │   ├── bengal-vs-hugo.md
│   │   ├── bengal-vs-jekyll.md
│   │   ├── bengal-vs-eleventy.md
│   │   ├── bengal-vs-mkdocs.md
│   │   └── feature-matrix.md
│   │
│   ├── api/                    # 📖 API DOCUMENTATION
│   │   ├── _index.md
│   │   ├── python-api/
│   │   │   ├── site.md
│   │   │   ├── page.md
│   │   │   ├── section.md
│   │   │   └── asset.md
│   │   │
│   │   └── cli/
│   │       ├── build.md
│   │       ├── serve.md
│   │       ├── new.md
│   │       └── clean.md
│   │
│   ├── about.md                # About Bengal
│   ├── contact.md              # Contact/community
│   ├── contributing.md         # Contribution guide
│   └── changelog.md            # Release notes
│
├── templates/                  # CUSTOM TEMPLATES
│   ├── custom-post.html        # Example custom template
│   ├── api-doc.html            # API documentation template
│   └── showcase.html           # Showcase template
│
└── data/                       # DATA FILES
    ├── features.yaml           # Feature list
    ├── benchmarks.yaml         # Performance data
    └── testimonials.yaml       # User quotes
```

---

## 🎯 Key Improvements by Category

### 1. Template Functions Documentation (CRITICAL)

**Current:** 0 of 75 functions documented  
**Target:** 100% coverage with examples

**New pages to create:**
- `docs/templates/function-reference/_index.md` - Overview of all 75 functions
- `docs/templates/function-reference/strings.md` - 11 string functions with examples
- `docs/templates/function-reference/collections.md` - 8 collection functions
- `docs/templates/function-reference/math.md` - 6 math functions
- ... (15 pages total, one per module)

**Each function page should include:**
- Function signature
- Parameters and types
- Return value
- Multiple real-world examples
- Edge cases and gotchas
- Related functions
- Performance notes

**Example format:**
```markdown
## truncatewords

Truncate text to a specified number of words.

### Signature
```jinja2
{{ text | truncatewords(count, suffix="...") }}
```

### Parameters
- `text` (str): Text to truncate
- `count` (int): Maximum number of words
- `suffix` (str, optional): Suffix to append. Default: "..."

### Returns
Truncated string with suffix if truncated.

### Examples

#### Basic usage
```jinja2
{{ page.content | truncatewords(50) }}
```

#### Custom suffix
```jinja2
{{ post.description | truncatewords(30, suffix="[Read more]") }}
```

#### In blog preview
```jinja2
<div class="excerpt">
  {{ post.content | strip_html | truncatewords(100) }}
</div>
```

### See Also
- `truncate_chars` - Truncate by character count
- `excerpt` - Extract excerpt with smart paragraph handling
```

### 2. Mistune Directives Showcase (CRITICAL)

**Current:** Zero examples of directives in action  
**Target:** Comprehensive examples of all directives

**New pages:**
- `docs/markdown/admonitions.md` - All 9 admonition types with examples
- `docs/markdown/tabs-and-dropdowns.md` - Interactive content examples
- `docs/markdown/code-examples.md` - Code-tabs directive showcase
- `docs/markdown/kitchen-sink.md` - **EVERYTHING in one page!**

**Kitchen Sink page should demonstrate:**
- All 9 admonition types (note, tip, warning, danger, error, info, example, success, caution)
- Nested tabs
- Collapsible dropdowns
- Multi-language code tabs
- Tables with all GFM features
- Task lists
- Footnotes
- Definition lists
- Variable substitution {{ page.var }}
- Cross-references [[link]]
- Everything else!

### 3. Advanced Features Documentation

**New comprehensive guides:**

#### Output Formats (MAJOR GAP)
- `docs/output/output-formats.md` - JSON and LLM-txt generation
- Show how to use for:
  - Search indexing
  - AI/LLM discovery
  - Programmatic access
  - Mobile apps
  - API endpoints

#### Health Checks (MAJOR GAP)
- `docs/quality/health-checks.md` - All 9 validators explained
- Examples of each validator in action
- How to configure
- CI/CD integration
- Custom validators

#### Variable Substitution (MAJOR GAP)
- `docs/markdown/variable-substitution.md`
- Examples: `{{ page.metadata.version }}`, `{{ site.config.api_url }}`
- Use cases: DRY documentation, dynamic content
- Limitations and best practices

#### Plugin Development (MAJOR GAP)
- `docs/advanced/plugin-development.md`
- How to create custom Mistune plugins
- How to create custom template functions
- API reference
- Complete example plugins

### 4. Migration Guides (NEW)

Help users migrate from other SSGs:
- `tutorials/migration/from-hugo.md` - Hugo → Bengal
- `tutorials/migration/from-jekyll.md` - Jekyll → Bengal
- `tutorials/migration/from-eleventy.md` - 11ty → Bengal
- `tutorials/migration/from-mkdocs.md` - MkDocs → Bengal

**Each guide should cover:**
- Feature comparison matrix
- Content migration (frontmatter differences)
- Template migration (syntax mapping)
- Configuration migration
- Automated migration scripts
- Common gotchas
- What's better in Bengal
- What's different

### 5. Real-World Examples (NEW)

**Blog patterns:**
- Classic chronological blog
- Magazine-style layout
- Minimal/zen blog
- Developer blog with code
- Multi-author blog

**Documentation patterns:**
- API reference docs
- User guides
- Technical specifications
- Tutorials & how-tos

**Landing pages:**
- Product launch page
- SaaS homepage
- Portfolio showcase
- Marketing site

### 6. Comparison Pages (NEW)

Honest, detailed comparisons:
- Bengal vs Hugo (when to use which)
- Bengal vs Jekyll (migration path)
- Bengal vs Eleventy (JavaScript vs Python)
- Bengal vs MkDocs (docs vs general)

### 7. Interactive Showcase (NEW)

**Component library:**
- All UI components from default theme
- Interactive examples
- Copy-paste ready code

**Directive playground:**
- Every directive with live examples
- Side-by-side markdown/output
- Customization options

**Template gallery:**
- Complete template examples
- Different layouts
- Copy-paste ready

---

## 📝 Content Writing Guidelines

### Every Documentation Page Should Have:

1. **Clear title and description**
2. **Table of contents** (auto-generated)
3. **Learning objectives** at the start
4. **Multiple examples** - simple → complex
5. **Code samples** with syntax highlighting
6. **Live demonstrations** using directives
7. **Best practices** section
8. **Common pitfalls** warnings
9. **Related pages** links
10. **Last updated** date

### Use All Bengal Features:

- ✅ **Variable substitution** in content: `{{ page.metadata.version }}`
- ✅ **Cross-references**: `[[docs/templates/strings]]`
- ✅ **Admonitions**: ```{note}, ```{warning}, ```{tip}
- ✅ **Tabs**: ```{tabs} for multi-platform examples
- ✅ **Dropdowns**: ```{dropdown} for long content
- ✅ **Code-tabs**: ```{code-tabs} for multi-language examples
- ✅ **TOC**: Proper heading structure for automatic TOC
- ✅ **Navigation**: next/prev links via template functions
- ✅ **Breadcrumbs**: Auto-generated via cascade
- ✅ **Tags**: Proper taxonomy usage

### Tone and Style:

- **Friendly** but professional
- **Clear** and concise
- **Action-oriented** (do this, try that)
- **Visual** (use tables, lists, diagrams)
- **Example-driven** (show, don't just tell)
- **Encouraging** (celebrate wins, acknowledge challenges)

---

## 🎨 Visual and UX Improvements

### Homepage Redesign

**Current:** Basic feature list  
**New:** Impressive showcase

```markdown
# Bengal SSG

A blazingly fast, beautifully modular static site generator for Python.

[Get Started](#) [View Docs](#) [GitHub](#)

## Why Bengal?

### ⚡ Lightning Fast
- **0.3s** to build 100 pages
- **18-42x faster** incremental builds
- **2-4x speedup** with parallel processing

[See Benchmarks](#)

### 🎯 Feature Complete
- **75 template functions** - strings, collections, dates, SEO, and more
- **9 health validators** - catch issues before deployment
- **Advanced markdown** - tabs, admonitions, dropdowns, code-tabs
- **Smart navigation** - automatic next/prev, breadcrumbs, menus

[Explore Features](#)

### 🧩 Beautifully Modular
- Clean architecture with Site, Page, Section, Asset
- No "God objects" - single responsibility principle
- 64% test coverage and growing
- Type-safe with comprehensive docstrings

[Read Architecture](#)

## Quick Start

```bash
pip install bengal-ssg
bengal new my-site
cd my-site
bengal serve
```

[Full Tutorial →](#)
```

### Navigation Improvements

**Add:**
- Sticky TOC sidebar on doc pages
- Next/Prev page links on all docs
- Breadcrumbs on all pages
- Search bar (using output formats JSON)
- "Edit this page" links
- "Was this helpful?" feedback

### Visual Elements

**Add:**
- Performance comparison charts
- Feature matrix tables
- Architecture diagrams
- Screenshot galleries
- Code example carousels
- Dark/light mode toggle (already have!)

---

## 📊 Success Metrics

### Coverage Goals

- ✅ **100%** of 75 template functions documented with examples
- ✅ **100%** of Mistune directives demonstrated
- ✅ **100%** of core features covered in docs
- ✅ **90%+** of pages use advanced features (directives, cross-refs, etc.)

### Quality Goals

- ✅ Every doc page has 3+ code examples
- ✅ Every feature has a "kitchen sink" demo
- ✅ All links validated (link health check passing)
- ✅ All pages have proper metadata for SEO
- ✅ All pages output JSON for search

### UX Goals

- ✅ New user can build first site in < 10 minutes
- ✅ Migrator can find comparison guide in < 2 minutes
- ✅ Advanced user can find any function in < 30 seconds
- ✅ Mobile-friendly responsive design
- ✅ Fast page loads (< 1 second)

---

## 🚀 Implementation Phases

### Phase 1: Template Functions (Week 1) - HIGHEST PRIORITY

**Why first:** This is the BIGGEST gap - 75 functions, 0 documentation!

**Tasks:**
1. Create `docs/templates/function-reference/` structure
2. Document all 15 function modules:
   - strings (11 functions)
   - collections (8 functions)
   - math (6 functions)
   - dates (3 functions)
   - urls (3 functions)
   - content (6 functions)
   - data (8 functions)
   - files (3 functions)
   - advanced_strings (3 functions)
   - advanced_collections (3 functions)
   - images (6 functions)
   - seo (4 functions)
   - debug (3 functions)
   - taxonomies (4 functions)
   - pagination (3 functions)
   - crossref (5 functions)
3. Create master index page with all functions
4. Add search functionality via output formats

**Deliverable:** Complete template function reference

---

### Phase 2: Mistune Directives Showcase (Week 1-2)

**Tasks:**
1. Create `docs/markdown/` section
2. Document each directive type:
   - Admonitions (all 9 types)
   - Tabs
   - Dropdown
   - Code-tabs
3. Create kitchen-sink demo page
4. Add directive playground page

**Deliverable:** Comprehensive directive documentation

---

### Phase 3: Advanced Features (Week 2)

**Tasks:**
1. Output formats guide
2. Health checks guide
3. Variable substitution guide
4. Plugin development guide
5. Performance/benchmarking guide

**Deliverable:** All advanced features documented

---

### Phase 4: Tutorials & Examples (Week 2-3)

**Tasks:**
1. Write 4 comprehensive tutorials:
   - Build a blog
   - Documentation site
   - Portfolio
   - Custom theme
2. Create 4 migration guides:
   - From Hugo
   - From Jekyll
   - From Eleventy
   - From MkDocs
3. Add real-world example patterns

**Deliverable:** Practical learning paths

---

### Phase 5: Comparison & Showcase (Week 3)

**Tasks:**
1. Write comparison pages (vs Hugo, Jekyll, 11ty, MkDocs)
2. Create showcase pages:
   - Component library
   - Directive playground
   - Template gallery
3. Build interactive demos

**Deliverable:** Competitive positioning

---

### Phase 6: Polish & Launch (Week 3-4)

**Tasks:**
1. Redesign homepage
2. Improve navigation (sticky TOC, breadcrumbs)
3. Add search using output formats
4. Create visual assets (diagrams, charts)
5. Full content review and editing
6. Link validation
7. Health check passing
8. Performance optimization
9. Mobile optimization
10. Deploy to production

**Deliverable:** Production-ready example site

---

## 🎯 Quick Wins (Do These First!)

### Day 1: Kitchen Sink Page
Create `docs/markdown/kitchen-sink.md` with EVERY directive and feature in one place. This gives us immediate visual impact.

### Day 2: Template Functions Index
Create the index page listing all 75 functions. Even without details, this shows scope.

### Day 3: Health Checks Demo
Document the health check system - it's unique to Bengal and impressive.

### Day 4: Output Formats Guide
Show off JSON/LLM-txt generation - another unique feature.

### Day 5: Migration Guide (Hugo)
Most users come from Hugo - make this easy and we win conversions.

---

## 📋 Content Inventory Checklist

### Documentation Pages (60+ pages)
- [ ] 15 function reference pages (one per module)
- [ ] 5 getting started pages
- [ ] 6 core concepts pages
- [ ] 9 markdown guide pages (including 4 new directive pages)
- [ ] 6 template pages (including function reference)
- [ ] 6 navigation pages
- [ ] 6 organization pages
- [ ] 7 performance pages
- [ ] 7 theming pages
- [ ] 5 assets pages
- [ ] 5 output pages
- [ ] 5 quality pages
- [ ] 5 development pages
- [ ] 5 deployment pages
- [ ] 5 configuration pages
- [ ] 6 advanced pages

### Tutorials (20+ pages)
- [ ] 5 blog tutorial pages
- [ ] 4 docs site tutorial pages
- [ ] 4 portfolio tutorial pages
- [ ] 4 custom theme tutorial pages
- [ ] 4 migration guide pages

### Examples (15+ pages)
- [ ] 4 blog layout examples
- [ ] 4 documentation pattern examples
- [ ] 4 landing page examples
- [ ] 4 special feature examples

### Blog Posts (8+ posts)
- [ ] Introducing Bengal
- [ ] Performance benchmarks
- [ ] Template functions guide
- [ ] Markdown power features
- [ ] Theming best practices
- [ ] Output formats explained
- [ ] Health checks deep dive
- [ ] Incremental builds magic

### Comparison Pages (5 pages)
- [ ] Bengal vs Hugo
- [ ] Bengal vs Jekyll
- [ ] Bengal vs Eleventy
- [ ] Bengal vs MkDocs
- [ ] Feature matrix

### Showcase Pages (4 pages)
- [ ] Component library
- [ ] Directive playground
- [ ] Template gallery
- [ ] Theme preview

### API Documentation (6+ pages)
- [ ] Site API
- [ ] Page API
- [ ] Section API
- [ ] Asset API
- [ ] CLI reference

**TOTAL:** ~120-130 pages of high-quality, feature-rich content

---

## 🎉 Expected Outcomes

### For New Users
- Clear onboarding path (< 10 minutes to first site)
- Comprehensive learning resources
- Confidence in Bengal's capabilities
- Quick problem resolution

### For Migrators
- Clear comparison to their current SSG
- Step-by-step migration guides
- Feature parity confidence
- Easy transition

### For Advanced Users
- Complete API reference
- Plugin development guide
- Performance tuning docs
- Architecture understanding

### For the Project
- Showcase of ALL features (75+ functions, 9 directives, 9 validators, etc.)
- Dog-fooding (Bengal docs built with Bengal)
- SEO-optimized content
- AI/LLM discoverable (output formats)
- Community-ready documentation
- Production-ready example

### Competitive Advantages Highlighted
- ✅ Faster than Jekyll, competitive with 11ty
- ✅ More modular than Hugo
- ✅ More powerful than MkDocs
- ✅ Python ecosystem (vs Go/Ruby/JS)
- ✅ 75 template functions (more than most SSGs)
- ✅ Health check system (unique feature)
- ✅ Output formats (JSON/LLM-txt - forward-thinking)
- ✅ Clean architecture (no God objects)

---

## 🤔 Open Questions

1. **Should we create multiple example sites or one comprehensive one?**
   - **Recommendation:** One comprehensive "showcase" site with everything
   - Keep `quickstart` for minimal example
   - Add `showcase` for complete example

2. **Should we auto-generate function docs from docstrings?**
   - **Recommendation:** Manual for now (better examples)
   - Consider auto-generation for v2.0

3. **Should we add a search feature?**
   - **Recommendation:** Yes, using output formats JSON
   - Simple client-side search with lunr.js or similar

4. **Should we version the docs?**
   - **Recommendation:** Not yet (v1.0 only)
   - Add versioning in v1.1+

5. **Should we translate docs?**
   - **Recommendation:** English only for v1.0
   - i18n support for v2.0

---

## 🚀 Next Steps

1. **Get approval on this plan**
2. **Start with Phase 1: Template Functions** (biggest gap)
3. **Create content calendar** (which pages each day)
4. **Set up content templates** (for consistency)
5. **Begin writing!**

---

## 📊 Estimated Effort

### Time Investment
- **Phase 1** (Template Functions): 3-4 days
- **Phase 2** (Directives): 2-3 days
- **Phase 3** (Advanced): 2-3 days
- **Phase 4** (Tutorials): 3-4 days
- **Phase 5** (Comparison): 2-3 days
- **Phase 6** (Polish): 3-4 days

**Total: 15-21 days of focused work**

### Content Volume
- **~120-130 pages** of documentation
- **~25,000-30,000 words** of new content
- **100+ code examples**
- **50+ directive demonstrations**

### Success Criteria
- ✅ All 75 template functions documented
- ✅ All Mistune directives showcased
- ✅ All core features covered
- ✅ Health checks passing
- ✅ Link validation passing
- ✅ Beautiful and functional
- ✅ Mobile-responsive
- ✅ Search-enabled
- ✅ Production-ready

---

*This plan transforms the example site from a basic demo into a world-class showcase that demonstrates EVERY Bengal feature through real, practical usage. It positions Bengal as a serious competitor to established SSGs while highlighting its unique advantages.*

