# Bengal SSG - Next Steps & Roadmap

**Date:** October 2, 2025  
**Current Status:** Phase 2B Complete - Core SSG + Default Theme Functional

---

## 🎯 Current State

### ✅ What's Complete

**Core SSG (Phase 1 - Original Implementation)**
- ✅ Modular architecture (Site, Page, Section, Asset objects)
- ✅ Content discovery and parsing (Markdown → HTML)
- ✅ Jinja2 template engine integration
- ✅ Asset pipeline (copy static files)
- ✅ Rendering pipeline
- ✅ Configuration system (bengal.toml)
- ✅ Section support
- ✅ Post-processing (sitemap, RSS feed)
- ✅ Development server with hot reload
- ✅ CLI (`bengal build`, `bengal serve`, `bengal new`)

**Default Theme - Phase 1: Foundation**
- ✅ Modern CSS architecture (variables, reset, typography, utilities)
- ✅ Responsive grid system
- ✅ Header and footer layouts
- ✅ Component library (buttons, cards, tags, code blocks)
- ✅ Dark/light mode toggle
- ✅ Mobile navigation
- ✅ Base templates (base, page, post, index)
- ✅ SEO meta tags (Open Graph, Twitter Cards)
- ✅ Accessibility features (ARIA labels, skip links, semantic HTML)

**Default Theme - Phase 2A: Content Discovery**
- ✅ Template partials (article-card, tag-list, pagination scaffold)
- ✅ Taxonomy system (tags, categories)
- ✅ Archive pages for sections
- ✅ Tag index page (all tags)
- ✅ Individual tag pages
- ✅ Dynamic page generation

**Default Theme - Phase 2B: Pagination & Polish**
- ✅ Full pagination system (Paginator utility)
- ✅ Paginated archive pages
- ✅ Paginated tag pages
- ✅ Breadcrumb navigation (auto-generated)
- ✅ 404 error page
- ✅ Page URL property
- ✅ Pagination CSS and controls

---

## 🚀 What's Working Right Now

You can build a full-featured static site with:

1. **Content Types**
   - Pages (static content)
   - Blog posts (with dates, tags, authors)
   - Multiple sections

2. **Organization**
   - Sections (e.g., blog, docs, tutorials)
   - Tags and categories
   - Archive pages (paginated)
   - Tag pages (paginated)

3. **Templates**
   - Homepage with recent posts
   - Individual post pages
   - Individual page templates
   - Section archives
   - Tag listings
   - 404 error page

4. **Features**
   - Dark/light mode
   - Mobile-responsive
   - SEO optimized
   - RSS feed
   - Sitemap
   - Breadcrumbs
   - Pagination
   - Syntax highlighting

5. **Developer Experience**
   - Hot reload dev server
   - Clear CLI
   - Extensible theme system
   - Configuration file

---

## 📋 Potential Next Phases

### Phase 2C: Advanced Features (Optional Polish)

**Estimated Effort:** 4-6 hours

1. **Table of Contents**
   - Auto-generate TOC from headings
   - Sticky TOC on scroll
   - Highlight current section

2. **Related Posts**
   - Find related posts by tags
   - Display at end of posts
   - Configurable algorithm

3. **Search**
   - Client-side search index
   - Search page template
   - Search results display

4. **Reading Progress**
   - Progress bar for posts
   - Scroll indicator
   - Estimated reading time enhancement

5. **Social Sharing**
   - Share buttons component
   - Copy link functionality
   - Platform-specific sharing

**Priority:** Medium (nice-to-have polish features)

---

### Phase 3: Plugin System

**Estimated Effort:** 8-12 hours

1. **Plugin Architecture**
   - Plugin discovery and loading
   - Hook system (pre-build, post-build, pre-render, post-render)
   - Plugin configuration
   - Plugin API documentation

2. **Built-in Plugins**
   - Image optimization
   - Asset minification (CSS, JS)
   - Syntax highlighting themes
   - Analytics integration
   - Comments integration (Disqus, utterances)

3. **Plugin Examples**
   - Create 2-3 example plugins
   - Plugin template/boilerplate
   - Plugin development guide

**Priority:** High (makes Bengal extensible and future-proof)

---

### Phase 4: Advanced Content Features

**Estimated Effort:** 6-10 hours

1. **Content Versioning**
   - Multiple versions of documentation
   - Version switcher UI
   - Version-specific content

2. **Multi-language Support**
   - i18n/l10n system
   - Language switcher
   - Translated content routing

3. **Custom Content Types**
   - Define custom content types (projects, team members, etc.)
   - Custom templates per type
   - Custom metadata schemas

4. **Content Collections**
   - Group related content
   - Collection pages
   - Cross-collection references

**Priority:** Medium (needed for docs/portfolio sites)

---

### Phase 5: Performance & Optimization

**Estimated Effort:** 4-6 hours

1. **Incremental Builds**
   - Dependency tracking
   - Only rebuild changed files
   - Smart cache invalidation

2. **Parallel Processing**
   - Multi-threaded rendering
   - Parallel asset processing
   - Worker pool for large sites

3. **Build Optimization**
   - Minify HTML output
   - Optimize image sizes
   - Bundle and minify CSS/JS
   - Generate WebP/AVIF variants

4. **Benchmarking**
   - Build time tracking
   - Performance tests
   - Comparison with Hugo, Sphinx, MkDocs

**Priority:** High (core value proposition)

---

### Phase 6: Documentation & Community

**Estimated Effort:** 8-12 hours

1. **Documentation Site**
   - Build docs site with Bengal itself
   - Comprehensive guides
   - API reference
   - Theme development guide
   - Plugin development guide

2. **Examples**
   - Blog template
   - Documentation template
   - Portfolio template
   - Marketing site template

3. **Community**
   - Contributing guide (already exists)
   - Code of conduct
   - Issue templates
   - PR templates
   - Theme showcase

**Priority:** High (needed for adoption)

---

### Phase 7: Advanced Themes

**Estimated Effort:** 10-15 hours

1. **Additional Themes**
   - Documentation theme (like Read the Docs)
   - Portfolio theme
   - Marketing/landing page theme
   - Minimal blog theme

2. **Theme Marketplace**
   - Theme registry
   - Theme installation CLI
   - Theme customization guide

3. **Theme Inheritance**
   - Inherit from existing themes
   - Override specific components
   - Theme composition

**Priority:** Medium (expands Bengal's appeal)

---

## 🎓 Recommended Next Steps

### Option A: Production-Ready Core (Recommended)
Focus on making Bengal production-ready for basic use cases:

1. ✅ **Phase 2B Complete** (Pagination & Polish)
2. **Phase 5** (Performance & Optimization)
   - Get incremental builds working
   - Add parallel processing
   - Benchmark against competitors
3. **Phase 6** (Documentation)
   - Create comprehensive docs
   - Add more examples
   - Write tutorials
4. **Phase 3** (Plugin System)
   - Basic plugin architecture
   - 2-3 essential plugins

**Timeline:** 3-4 weeks  
**Result:** Production-ready SSG for blogs and simple sites

---

### Option B: Feature-Complete Bengal
Build out all major features before focusing on performance:

1. ✅ **Phase 2B Complete**
2. **Phase 2C** (Advanced Features)
   - TOC, search, related posts
3. **Phase 4** (Advanced Content)
   - Versioning, i18n
4. **Phase 3** (Plugin System)
5. **Phase 5** (Performance)
6. **Phase 6** (Documentation)

**Timeline:** 6-8 weeks  
**Result:** Feature-rich SSG competing with Hugo/Sphinx

---

### Option C: Community-First Approach
Get Bengal usable quickly and let community drive features:

1. ✅ **Phase 2B Complete**
2. **Phase 6** (Documentation) - *First priority*
3. **Phase 3** (Basic Plugin System)
4. **Phase 5** (Core Performance)
5. Let community contribute themes and plugins

**Timeline:** 4-5 weeks  
**Result:** Well-documented, extensible foundation

---

## 🔍 What Would Make the Biggest Impact?

Based on the original spec ("outperform Hugo, Sphinx, MkDocs"), here's what matters most:

### Critical for Success
1. **Performance** (Phase 5)
   - Incremental builds
   - Parallel processing
   - Speed benchmarks
   
2. **Documentation** (Phase 6)
   - Show how to use it
   - Prove it works
   - Attract contributors

3. **Plugin System** (Phase 3)
   - Allows extensibility without bloat
   - Community can add features
   - Keeps core lean

### Nice to Have
- Advanced theme features (Phase 7)
- Content versioning (Phase 4)
- Additional polish (Phase 2C)

### Can Wait
- Multiple themes (default is solid)
- Marketing/showcase site
- Community infrastructure (until there's a community)

---

## 🎯 My Recommendation

**Go with Option A: Production-Ready Core**

**Reasoning:**
1. Core SSG is already solid ✅
2. Default theme is feature-complete ✅
3. Next bottleneck is **performance** (incremental builds)
4. Then **documentation** (so people can use it)
5. Then **plugins** (so it's extensible)

This gets Bengal to "production-ready for real projects" fastest.

**3-4 Week Roadmap:**

**Week 1: Performance (Phase 5)**
- Implement file dependency tracking
- Add incremental build logic
- Optimize rendering pipeline
- Add parallel processing
- Benchmark vs Hugo/Jekyll/11ty

**Week 2: Plugin System (Phase 3)**
- Design plugin architecture
- Implement hook system
- Create 2-3 essential plugins:
  - Image optimization
  - Syntax highlighting themes
  - Analytics integration
- Write plugin development guide

**Week 3-4: Documentation (Phase 6)**
- Create documentation site (using Bengal!)
- Write comprehensive guides:
  - Getting Started
  - Configuration
  - Themes
  - Plugins
  - Deployment
- Add 3-4 complete examples:
  - Personal blog
  - Documentation site
  - Portfolio
- Write API reference

**Result:** Bengal 1.0 - Production Ready

---

## 🚦 Current Blockers?

None! Bengal is functional and can be used for real projects right now. The next phases are about:
- Making it **faster** (performance)
- Making it **easier** (documentation)
- Making it **extensible** (plugins)

---

## 📝 Quick Wins (Can Do Anytime)

These are small improvements that would be nice but aren't critical:

- [ ] Add `bengal version` command
- [ ] Add `bengal theme install <name>` command
- [ ] Add `bengal plugin install <name>` command
- [ ] Add build time reporting
- [ ] Add verbose/debug mode
- [ ] Add `--watch` flag to build command
- [ ] Add draft posts support
- [ ] Add future post scheduling
- [ ] Add excerpt generation
- [ ] Add image lazy loading enhancement
- [ ] Add print stylesheet improvements
- [ ] Add code copy button enhancement

---

## 🎉 Summary

**Bengal SSG is now:**
- ✅ Functional end-to-end
- ✅ Has a beautiful, feature-complete default theme
- ✅ Supports blogs, pages, sections, tags, pagination
- ✅ Has good developer experience
- ✅ Is ready for real use

**To reach "production-ready 1.0":**
- ⏳ Optimize performance (incremental builds, parallel processing)
- ⏳ Write comprehensive documentation
- ⏳ Add plugin system
- ⏳ Create more examples

**Timeline:** 3-4 weeks of focused work

**Current Status:** Feature-complete for basic use cases, ready for optimization and polish!

---

**What would you like to work on next?**

1. Performance optimizations?
2. Plugin system?
3. Documentation?
4. More theme features?
5. Something else entirely?

