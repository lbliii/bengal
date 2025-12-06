# Bengal Marketing Positioning & Brand Strategy

**Status**: Draft  
**Created**: 2025-01-XX  
**Purpose**: Define Bengal's positioning, value proposition, brand voice, and messaging framework

---

## Executive Summary

Bengal needs a clear, differentiated positioning that goes beyond feature comparisons. This document establishes:

1. **Core Positioning**: Where Bengal sits in the market
2. **Value Proposition**: The unique value we deliver
3. **Brand Voice & Tone**: How we communicate
4. **Point of View**: Our perspective on the industry
5. **Messaging Framework**: How to talk about Bengal consistently
6. **Content Strategy**: How to apply this to site content

---

## 1. Market Positioning

### Current State (What We Say Now)
- "A pythonic static site generator with incremental builds, parallel processing, and auto-generated API docs"
- Feature-focused, technical, reactive (defined by what we're not)

### Proposed Positioning

**Bengal is the static site generator for Python teams who want to ship fast without fighting their tools.**

**Positioning Statement** (for internal use):
> For Python developers and technical teams building documentation, blogs, and mixed-content sites, Bengal is the static site generator that combines Python-native developer experience with production-grade performance. Unlike Hugo (Go templates) or Jekyll (Ruby ecosystem), Bengal lets you extend and customize everything in Python—the language you already know. Unlike MkDocs (docs-only) or Pelican (dated), Bengal is modern, fast, and built for mixed content from day one.

**Key Differentiators**:
1. **Python-native**: Everything is Python—no context switching to Go/Ruby/JS
2. **Developer experience first**: Fast iteration, great defaults, helpful errors
3. **Modern performance**: Incremental builds + free-threading = fast enough for most
4. **Mixed content**: Not just docs, not just blogs—everything in one tool

---

## 2. Value Proposition

### Primary Value Proposition

**"Build static sites in Python, without the compromises."**

### Value Pillars

#### 1. **Zero Context Switching**
- **What it means**: Everything you need is Python—templates, plugins, extensions, config
- **Why it matters**: Developers stay in their flow state, use familiar tools, leverage existing Python knowledge
- **Proof points**: Jinja2 (Python ecosystem), Python classes for plugins, Python config files

#### 2. **Fast Enough, Built Right**
- **What it means**: We optimize for developer experience and iteration speed, not just raw build times
- **Why it matters**: High-performance parallel builds mean you spend less time waiting, more time building
- **Proof points**: Parallel processing, free-threading support, dependency tracking

#### 3. **Modern by Default**
- **What it means**: Built for Python 3.14+, free-threading, modern CLI, great defaults
- **Why it matters**: No legacy baggage, leverages latest Python features, future-proof
- **Proof points**: Python 3.14+ requirement, free-threading support, interactive CLI wizards

#### 4. **Flexible Content Strategy**
- **What it means**: Not locked into "docs only" or "blog only"—build mixed content sites
- **Why it matters**: Real sites mix docs, blogs, landing pages, portfolios—Bengal handles it all
- **Proof points**: Flexible content types, hierarchical sections, taxonomies

---

## 3. Brand Voice & Tone

### Brand Personality

**Bengal is:**
- **Confident but not arrogant**: We know what we're good at, honest about what we're not
- **Helpful and practical**: We solve real problems, provide real solutions
- **Technical but accessible**: We speak to developers without condescending
- **Opinionated but flexible**: We have strong defaults, but you can override everything
- **Honest and transparent**: We tell you when to use something else

### Voice Characteristics

| Characteristic | What It Means | Examples |
|----------------|---------------|----------|
| **Direct** | Get to the point, no fluff | "Bengal is fast enough for most sites. If you have 50,000 pages, use Hugo." |
| **Practical** | Focus on what works, not theory | "Incremental builds mean you rebuild in seconds, not minutes." |
| **Respectful** | Acknowledge other tools, don't trash them | "MkDocs is fantastic for docs. Bengal is for mixed content." |
| **Empowering** | Help users succeed, not gatekeep | "Choose your path: Writer, Themer, or Contributor." |
| **Transparent** | Honest about limitations | "We want you to be happy, even if it means using another tool." |

### Tone Guidelines

**Do:**
- ✅ Use "you" (second person) for actions
- ✅ Be specific with numbers and examples
- ✅ Acknowledge tradeoffs honestly
- ✅ Show, don't just tell (code examples, benchmarks)
- ✅ Use active voice
- ✅ Be conversational but professional

**Don't:**
- ❌ Use marketing fluff ("powerful", "revolutionary", "game-changing")
- ❌ Make claims without evidence
- ❌ Trash competitors
- ❌ Use passive voice unnecessarily
- ❌ Be condescending or gatekeepy
- ❌ Hide limitations

### Tone Examples

**Homepage Hero** (Confident, Clear):
> Build static sites in Python, without the compromises. Bengal combines Python-native developer experience with production-grade performance for documentation, blogs, and mixed-content sites.

**Feature Description** (Practical, Specific):
> Parallel processing and free-threading ensure builds are fast. A 1,000-page site builds in seconds, not minutes.

**Comparison** (Respectful, Honest):
> Hugo is the speed king for 50,000+ page sites. Bengal is fast enough for most sites and gives you Python-native extensibility Hugo can't match.

**Limitations** (Transparent, Helpful):
> Bengal isn't for React/Vue SPAs—use Next.js or Nuxt for that. Bengal is for Multi-Page Apps (MPA) where static generation makes sense.

---

## 4. Point of View (POV)

### Core Beliefs

1. **Developer experience matters more than raw speed** (for most use cases)
   - Fast iteration > fast builds
   - Good defaults > infinite configurability
   - Helpful errors > silent failures

2. **Python deserves a modern SSG**
   - Python is the #1 language for many developers
   - They shouldn't have to learn Go/Ruby/JS just to build a site
   - Python's ecosystem is rich—use it

3. **Mixed content is the norm, not the exception**
   - Real sites mix docs, blogs, landing pages, portfolios
   - Tools that force you into one content type create friction
   - Flexibility shouldn't mean complexity

4. **Incremental builds are the future**
   - Full rebuilds are wasteful
   - Dependency tracking enables smart rebuilds
   - Fast iteration unlocks better developer experience

5. **Honesty builds trust**
   - Tell users when to use something else
   - Acknowledge limitations upfront
   - Set realistic expectations

### Industry Perspective

**The Problem with Current SSGs:**
- **Hugo**: Fast but Go templates are hard to debug, ecosystem is Go-focused
- **Jekyll**: Ruby ecosystem, GitHub Pages lock-in, slow builds
- **MkDocs**: Docs-only, can't easily mix content types
- **Pelican**: Dated, shows its age, missing modern features
- **Next.js/Astro**: Overkill for static sites, React/Vue required

**Bengal's Approach:**
- Python-native (no context switching)
- Modern (Python 3.14+, free-threading, great defaults)
- Fast enough (incremental builds, parallel processing)
- Flexible (mixed content, extensible architecture)
- Honest (we'll tell you when to use something else)

---

## 5. Messaging Framework

### Elevator Pitch (30 seconds)

"Bengal is a static site generator built in Python. If you know Python, you know Bengal—no Go templates or Ruby gems to learn. It's fast enough for most sites with incremental builds, and it handles mixed content—docs, blogs, portfolios—all in one tool."

### Core Message (1 minute)

"Bengal is the static site generator for Python teams. We combine Python-native developer experience with production-grade performance. Everything is Python—templates, plugins, config. Incremental builds make iteration fast, and our flexible content system handles docs, blogs, and mixed sites. We're honest about limitations—if you have 50,000 pages, use Hugo. But for most sites, Bengal gives you the best developer experience without compromising on performance."

### Key Messages by Audience

#### Python Developers
- **Message**: "Build sites in Python, not Go or Ruby"
- **Proof**: Jinja2 templates, Python plugins, Python config
- **Benefit**: Stay in your flow state, use familiar tools

#### Technical Writers
- **Message**: "Documentation that doesn't fight you"
- **Proof**: Auto-generated API docs, flexible content types, great defaults
- **Benefit**: Focus on writing, not tooling

#### Team Leads
- **Message**: "Fast iteration, reliable builds, Python-native"
- **Proof**: Incremental builds, health checks, Python ecosystem
- **Benefit**: Faster shipping, easier onboarding, maintainable codebase

#### Content Creators
- **Message**: "One tool for docs, blogs, portfolios"
- **Proof**: Mixed content support, flexible taxonomies, theme system
- **Benefit**: No need to learn multiple tools

---

## 6. Competitive Positioning

### Positioning Map

```
                    Fast Builds
                         ↑
                         |
        Hugo ────────────┼─────────── (Raw Speed)
                         |
                         |
        Bengal ──────────┼─────────── (DX + Speed)
                         |
                         |
        Jekyll ──────────┼─────────── (Ecosystem)
                         |
                         ↓
                  Developer Experience
```

### Competitive Messaging

**vs. Hugo**:
- "Hugo is faster, but Bengal is fast enough—and everything is Python"
- "If you have 50,000+ pages, use Hugo. For most sites, Bengal's Python-native experience wins."

**vs. Jekyll**:
- "Jekyll is great for GitHub Pages. Bengal is great for everything else—and it's faster."
- "No Ruby ecosystem to learn—just Python, which you already know."

**vs. MkDocs**:
- "MkDocs is fantastic for docs-only sites. Bengal handles docs, blogs, portfolios, and more."
- "Need to mix content types? Bengal is built for that from day one."

**vs. Pelican**:
- "Pelican is the grandfather of Python SSGs. Bengal is the modern reimplementation."
- "Built for Python 3.14+, with incremental builds and a modern CLI."

**vs. Next.js/Astro**:
- "Next.js and Astro are for React/Vue SPAs. Bengal is for Multi-Page Apps (MPA)."
- "If you need SSR or client-side routing, use Next.js. If you need static sites, Bengal is simpler."

---

## 7. Content Strategy Recommendations

### Homepage Messaging

**Current**: Feature list, technical specs
**Proposed**: Value-first messaging

**Hero Section**:
```
Build static sites in Python, without the compromises.

Bengal combines Python-native developer experience with production-grade performance.
Everything is Python—templates, plugins, config. Fast incremental builds.
Flexible content system. Modern by default.

[Get Started] [View Docs]
```

**Value Props** (3-column):
1. **Zero Context Switching**: Everything is Python—no Go templates or Ruby gems
2. **Fast Enough, Built Right**: High-performance parallel builds, free-threading support
3. **Modern by Default**: Python 3.14+, free-threading, great defaults

**Social Proof**:
- "Used by Python teams building docs, blogs, and mixed-content sites"
- Benchmarks: "200+ pages/sec build speed (parallel processing)"

### Documentation Tone

**Current**: Technical, reference-focused
**Proposed**: Practical, outcome-focused

**Examples**:

**Before** (Technical):
> Bengal supports incremental builds with dependency tracking. The build cache stores page metadata and dependencies.

**After** (Practical):
> Fast builds mean you wait seconds, not minutes. Edit a blog post and see changes instantly. Your 1,000-page site stays fast.

**Before** (Feature-focused):
> Bengal includes an asset pipeline with fingerprinting and minification.

**After** (Outcome-focused):
> Built-in asset pipeline handles optimization automatically. No need to configure Webpack or Rollup—just add your assets and Bengal handles the rest.

### Comparison Page

**Current**: Feature matrix, technical comparison
**Proposed**: Decision framework, honest guidance

**Structure**:
1. **Quick Decision Guide**: "Choose Bengal if... Choose Hugo if... Choose MkDocs if..."
2. **Honest Comparison**: Acknowledge strengths of competitors
3. **When NOT to Use Bengal**: Clear guidance on alternatives

**Example**:
> **Choose Bengal if:**
> - You're a Python developer (or team)
> - You want to build mixed-content sites (docs + blog + landing pages)
> - You value developer experience over raw speed
> - You need incremental builds for fast iteration
>
> **Choose Hugo if:**
> - You have 50,000+ pages (Bengal will feel slow)
> - You're comfortable with Go templates
> - Raw build speed is your #1 priority
>
> **Choose MkDocs if:**
> - You're building docs-only (no blog, no landing pages)
> - You want Material theme out of the box
> - You don't need custom templates

### Feature Pages

**Current**: "Bengal has X feature"
**Proposed**: "X feature helps you Y"

**Examples**:

**Incremental Builds**:
- **Before**: "Bengal supports incremental builds"
- **After**: "Intelligent caching and parallel processing mean you rebuild in seconds, not minutes. Your 1,000-page site stays fast."

**Auto-generated API Docs**:
- **Before**: "Bengal generates API documentation from Python source"
- **After**: "Document your Python APIs automatically. Write docstrings, get beautiful docs—no manual maintenance."

**Python-native**:
- **Before**: "Bengal is built in Python"
- **After**: "Everything is Python—templates, plugins, config. No context switching to Go or Ruby. Use the language you already know."

---

## 8. Brand Voice Examples

### Homepage Hero

**Current**:
> A pythonic static site generator with incremental builds, parallel processing, and auto-generated API docs.

**Proposed**:
> Build static sites in Python, without the compromises.  
> Bengal combines Python-native developer experience with production-grade performance.

### Feature Description

**Current**:
> Incremental builds with dependency tracking (18-42x faster than full builds)

**Proposed**:
> High-performance build pipeline using parallel processing and free-threading. Rebuilds take seconds, not minutes.

### Comparison

**Current**:
> Hugo is the speed king. If you have 50,000 pages, use Hugo.

**Proposed**:
> Hugo is the speed king for massive sites (50,000+ pages). Bengal is fast enough for most sites and gives you Python-native extensibility Hugo can't match.

### Limitations

**Current**:
> Extremely Large Sites (>10,000 pages): You will feel the Python GIL. Use Hugo.

**Proposed**:
> Sites with 10,000+ pages will feel the Python GIL. For massive sites, Hugo's raw speed wins. For most sites, Bengal's developer experience wins.

---

## 9. Implementation Checklist

### Immediate Actions

- [ ] Rewrite homepage hero with value-first messaging
- [ ] Update comparison page with decision framework
- [ ] Revise feature descriptions to be outcome-focused
- [ ] Add "When NOT to use Bengal" section
- [ ] Update README with new positioning

### Content Updates

- [ ] Homepage: Value props, not feature list
- [ ] Getting Started: Outcome-focused, not technical
- [ ] Comparison: Decision framework, honest guidance
- [ ] Features: "Helps you X" not "Has X feature"
- [ ] About: Philosophy and POV, not just features

### Messaging Consistency

- [ ] Audit all site content for voice/tone
- [ ] Update all "Bengal is..." statements
- [ ] Ensure all comparisons are respectful
- [ ] Add outcome-focused language throughout
- [ ] Remove marketing fluff

---

## 10. Success Metrics

### Brand Awareness
- Search volume for "Bengal static site generator"
- Mentions in Python/SSG communities
- GitHub stars and forks

### Messaging Effectiveness
- Time to value (how quickly users understand Bengal)
- Conversion rate (visitors → users)
- User feedback on clarity

### Positioning Clarity
- User surveys: "What is Bengal?" (should align with positioning)
- Comparison page engagement
- "When NOT to use Bengal" page views (shows honesty resonates)

---

## Appendix: Voice & Tone Quick Reference

### Do's ✅
- Be direct and practical
- Use "you" for actions
- Show outcomes, not just features
- Acknowledge tradeoffs honestly
- Respect competitors
- Use specific numbers and examples

### Don'ts ❌
- Marketing fluff ("powerful", "revolutionary")
- Passive voice unnecessarily
- Trash competitors
- Hide limitations
- Be condescending
- Make claims without evidence

### Tone Examples

**Confident**: "Bengal is fast enough for most sites"
**Practical**: "Incremental builds mean you rebuild in seconds"
**Respectful**: "Hugo is the speed king for massive sites"
**Transparent**: "We want you to be happy, even if it means using another tool"
**Empowering**: "Choose your path: Writer, Themer, or Contributor"

---

**Next Steps**: Review with team, refine based on feedback, implement in site content.
