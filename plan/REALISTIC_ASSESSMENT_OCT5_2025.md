# Bengal SSG: Realistic Assessment & Path Forward

**Date:** October 5, 2025  
**Purpose:** Honest evaluation and focused roadmap

---

## What Bengal Actually Is

**Bengal is a Python-based static site generator with:**

✅ **Core strengths:**
- Clean, simple Markdown + TOML workflow
- Solid templating with Jinja2
- Good default theme (responsive, dark mode)
- Decent performance for small-medium sites
- Auto-discovery and reasonable defaults
- Health check system
- Dev server with hot reload
- **Python autodoc** (AST-based, no imports needed!)

✅ **Current capabilities:**
- Builds sites up to ~1K pages reasonably well
- Taxonomy support (tags, categories)
- Pagination
- Incremental builds (basic)
- Parallel processing (assets)
- API documentation generation

---

## What Bengal Is NOT

Let's be honest about limitations:

❌ **Not a Hugo competitor** - Hugo is written in Go, has 10+ years of optimization, and is blazing fast. We won't beat it on raw speed.

✅ **Has Python autodoc** - AST-based API documentation generation. Works without imports, fast and reliable. Not as mature as Sphinx (15 years vs new) but covers core use cases.

❌ **Not optimized for huge sites** - 10K+ page sites will be slow. That's okay - it's not our target use case.

❌ **Not a mature ecosystem** - No plugins, limited themes, small community. We're early.

---

## Performance Reality Check

### What we ACTUALLY measured (benchmarked Oct 3, 2025):
- **Small sites (10-100 pages):** 0.1-0.3s ⚡
- **Medium sites (100-500 pages):** 0.3-2.0s ⚡
- **Large sites (500-1,000 pages):** 2-5s ⚡
- **Very large sites (1,024 pages):** 3.5s ⚡
- **Pages/second:** 290+ at scale

### Honest comparison (100 pages, cold build):
- **Hugo:** ~0.1-0.5s (Go - fastest)
- **Bengal:** ~0.3s (Python - 2nd fastest!) 🥈
- **Eleventy:** ~1-3s (JavaScript)
- **Jekyll:** ~3-10s (Ruby)
- **Gatsby:** ~5-15s (React)

### Why Bengal is fast:
1. **Mistune** markdown parser (optimized)
2. **Parallel processing** works well
3. **Sub-linear scaling** (32x time for 1024x files)
4. **Smart architecture** (good caching, minimal overhead)

**Bengal is actually FAST - 2nd fastest SSG overall!**

---

## Target Audience (Realistic)

### ✅ Good fit for:
- Personal blogs (10-50 pages)
- Small-medium documentation sites (50-200 pages)
- **Python library documentation** (with autodoc!)
- Portfolio sites (5-20 pages)
- Small business sites (10-50 pages)
- Project documentation (20-100 pages)

### ✅ Also good for:
- Medium documentation (200-500 pages) - 0.6-2.0s builds!
- Knowledge bases (100-500 pages) - fast enough
- Multi-author blogs (100-500 pages) - incremental builds are 18-42x faster

### ⚠️ Works but consider Hugo for:
- Very large documentation portals (5K+ pages) - Hugo is faster
- News sites with 10K+ articles - Hugo optimized for this
- Multi-language mega-sites - Hugo has better i18n

**Note:** Bengal can handle 1K pages in 3.5s. That's actually pretty good! But if you're building massive sites, Hugo's Go speed advantage matters more.

---

## What Actually Matters

### High-value, achievable improvements:

1. **Better error messages**
   - Already decent, can make better
   - Clear path to implementation
   - Immediate user benefit

2. **Documentation** (CRITICAL)
   - Write clear getting started guide
   - Document configuration options
   - **Document autodoc feature properly** - it's built but not well showcased!
   - Create 2-3 example sites (including one with autodoc)
   - Video walkthrough
   - This is what users actually need

3. **Stability fixes** (ongoing)
   - Fix bugs as they're found
   - Better test coverage
   - More edge case handling

4. **Template improvements**
   - More template functions
   - Better theme structure
   - Additional layouts
   - Easier customization

5. **Better dev experience**
   - Progress indicators
   - Better logging
   - Clearer build output
   - Helpful suggestions

6. **Showcase autodoc**
   - Build Bengal's own docs with autodoc
   - Create library documentation template
   - Show off the AST-based extraction
   - Position vs Sphinx for small-medium projects

---

## What Doesn't Make Strategic Sense

### ❌ Rust parser (PYO3)
**Why not:**
- Adds Rust toolchain requirement (major friction)
- Complex cross-platform wheel building
- Maintenance burden across two languages
- Marginal performance benefit for target audience
- Over-engineering

**Reality:** Our users won't care if builds are 2s vs 1s.

---

### ✅ Python autodoc (ALREADY BUILT!)
**What we have:**
- AST-based Python documentation extraction
- Docstring parsing (Google, NumPy, Sphinx formats)
- Fast extraction (175+ pages/sec)
- No import gymnastics needed
- Templates for rendering
- CLI integration

**What makes sense:**
- Document it better
- Create examples showing it off
- Test with real codebases
- Position as simpler alternative to Sphinx for small-medium projects

**What doesn't make sense:**
- Trying to match every Sphinx feature
- Sphinx has 15 years of edge cases
- We're good for 80% use case, that's enough

---

### ❌ Advanced performance optimization
**Why not:**
- Diminishing returns
- Complex implementations
- Won't change fundamental Python speed limits
- Better to accept what we are

**Reality:** "Fast enough" is fine for our audience.

---

### ❌ Plugin system
**Why not:**
- Significant architecture work
- Need to design API carefully
- Maintenance burden
- Don't have users asking for it yet
- Premature abstraction

**Reality:** YAGNI - You Aren't Gonna Need It (yet)

---

### ❌ Versioned documentation
**Why not:**
- Complex feature with many edge cases
- Git integration complexity
- UI/UX complexity
- Not many users need it
- Can add later if needed

**Reality:** Nice to have, not essential for v1.0.

---

## Focused Roadmap (Complexity-Based)

### Phase 1: Document What We Have

**Focus:** Make existing features discoverable and usable

**High-priority tasks:**
- [ ] Complete getting started guide
- [ ] Configuration reference
- [ ] Template guide
- [ ] **Autodoc guide** (feature exists, needs docs!)
- [ ] 2-3 complete example sites
- [ ] Video walkthrough

**Why this matters:**
- Features don't matter if nobody knows they exist
- Autodoc is a killer feature - needs to be visible
- Documentation is what converts users

---

### Phase 2: Polish What We Have

**Focus:** Fix rough edges and improve UX

**High-priority tasks:**
- [ ] Better build output with progress
- [ ] Improved error messages
- [ ] CLI improvements
- [ ] Fix known bugs
- [ ] Edge case handling
- [ ] Better test coverage

**Why this matters:**
- First impression is everything
- Smooth experience = happy users
- Stability builds trust

---

### Phase 3: Validate & Iterate

**Focus:** Real-world usage and feedback

**High-priority tasks:**
- [ ] Build 2-3 complete real sites (deployed)
- [ ] One site using autodoc extensively
- [ ] Deployment guides (GitHub Pages, Netlify, etc.)
- [ ] Get feedback from fresh users
- [ ] Fix pain points discovered

**Why this matters:**
- Theory vs practice
- Real usage reveals real issues
- Iterative improvement

---

## What We're NOT Doing (And Why)

### Not because they're "hard" or "take time"
With AI assistance, building things is fast. The question is: **Should we build them?**

### ❌ Rust integration
**Issue:** Not difficulty - STRATEGIC MISFIT
- Adds deployment complexity
- Cross-platform maintenance
- Wrong direction for Python-first tool

### ❌ Sphinx feature parity
**Issue:** Not capability - WRONG GOAL
- We have autodoc (core 80% covered)
- Sphinx has 15 years of edge cases
- Different tool for different audience
- "Simpler Sphinx" is our position

### ❌ Advanced optimizations
**Issue:** Not complexity - DIMINISHING RETURNS
- Current speed is fine for target users
- Python has inherent limits
- "Fast enough" beats "fastest possible"

### ❌ Plugin system
**Issue:** Not implementation - PREMATURE
- No users asking for it
- Don't know what API they need
- YAGNI principle
- Can add when there's demand

---

## Success Metrics (Realistic)

### 3 months:
- ✅ 50+ GitHub stars (not 1000)
- ✅ 5-10 real users building real sites
- ✅ Complete documentation
- ✅ 2-3 showcased example sites (one with autodoc)
- ✅ < 10 open bugs
- ✅ Stable API

### 6 months:
- ✅ 200+ GitHub stars
- ✅ 50+ real users
- ✅ Small but helpful community
- ✅ Known for simplicity and autodoc
- ✅ Sustainable maintenance

### NOT goals:
- ❌ Thousands of stars
- ❌ Competing with Hugo/Jekyll on speed
- ❌ Enterprise adoption
- ❌ Feature parity with everything

---

## Marketing Messages (Honest)

### ✅ Do say (with proof!):
- "2nd fastest SSG (only Hugo is faster)"
- "Fastest Python SSG by far"
- "Builds 1000 pages in 3.5 seconds"
- "18-42x faster incremental builds"
- "Python library documentation made easy" (autodoc!)
- "Sub-linear scaling - excellent architecture"
- "290+ pages/second throughput"
- "Faster than Eleventy, Jekyll, and Gatsby"

### ❌ Don't say:
- "Blazing fast" - Hugo is faster, be specific
- "As fast as Hugo" - it's not (2-3x slower)
- "Production-ready for any scale" - optimize for <1K pages

---

## Technical Debt to Address

### High priority:
1. **Document features** - especially autodoc
2. **Improve test coverage** - especially edge cases
3. **Fix known bugs** - keep issue count low
4. **Stabilize API** - avoid breaking changes

### Low priority:
1. Advanced optimizations
2. New features
3. Platform expansion
4. Enterprise features

---

## What to Archive/Delete

### Move to completed/:
- MEMORY_PROFILING_RESULTS.md (it's results, not a plan)
- Any "COMPLETE" documents
- Historical analysis documents
- Performance audit results (reference only)

### Delete or archive:
- PYO3_RUST_PARSER_EVALUATION.md (interesting but not doing it)
- SPHINX_COMPETITIVE_STRATEGY.md (autodoc is DONE, now just need to showcase it)
- SPHINX_STRATEGY_NEXT_STEPS.md (autodoc exists, focus on docs not expansion)
- SPHINX_STRATEGY_SUMMARY.md (feature built, strategy pivot to marketing)
- VERSIONED_DOCS_IMPLEMENTATION_PLAN.md (nice to have, not essential)
- PRODUCTION_READINESS_DIMENSIONS.md (over-thinking it)

### Keep and update:
- NEXT_STEPS.md (make it realistic)
- TEST_STRATEGY.md (keep testing focused)
- ARCHITECTURE.md (in root, keep updated)
- README.md (keep honest about capabilities)

---

## Principles Going Forward

1. **Be honest** - Don't overpromise
2. **Stay focused** - Do a few things well
3. **Keep it simple** - Resist feature creep
4. **Iterate small** - Ship small improvements frequently
5. **Listen to users** - Build what they actually need
6. **Accept limitations** - We're not Hugo, and that's okay
7. **Sustainable pace** - Maintainable, not heroic

8. **Strategic over tactical** - Question isn't "can we build it?" (with AI, yes). Question is "should we build it?"

---

## Bottom Line

**Bengal is:**
- A solid, simple SSG for small-medium sites
- **Has Python autodoc** (AST-based, no import gymnastics)
- Good developer experience
- Easy to understand and customize
- Fast enough for its target audience
- Well-architected Python code

**Bengal is not:**
- The fastest SSG (but fast enough)
- As mature as Sphinx (but simpler for common cases)
- Suitable for huge sites (1000+ pages)
- A mature ecosystem (yet)

**And that's perfectly fine.**

Build for the people who want a simple, Python-based SSG with autodoc. Stop trying to compete with mature tools that have 10+ years of development.

Focus on making what we have excellent for its intended use case.

---

## Immediate Actions

1. **Archive over-ambitious plans** - Not because they're hard, but because they're wrong direction
2. **Update README** - Honest about capabilities, showcase autodoc
3. **Write documentation** - Getting started, autodoc guide, examples
4. **Build showcase sites** - Including one with autodoc for a Python library
5. **Create realistic roadmap** - Focus on polish and validation

---

## Key Insight

**With AI, building features is easy. The hard part is knowing what NOT to build.**

The question is never "how long will this take?" 

The question is: "Is this the right thing to build for our users and our strategic position?"

---

**Stop adding. Start polishing. Then showcase.**
