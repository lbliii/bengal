# Bengal SSG - Strategic Plan (Honest Edition)

**Date:** October 5, 2025  
**Purpose:** Clear direction without hyperbole

---

## What Bengal Is

A **Python static site generator** focused on **simplicity and good developer experience**.

**Target audience:**
- Personal bloggers
- Small project documentation
- Portfolio sites
- Small business sites

**Target size:**
- 10-500 pages (sweet spot: 50-200)

**Not for:**
- Enterprise documentation portals
- Sites with 1000+ pages
- News sites with huge archives
- Multi-language mega-sites

---

## Core Strengths

1. **Simple workflow** - Markdown + TOML
2. **Good defaults** - Auto-discovery, sensible config
3. **Python ecosystem** - Familiar tools, easy to hack
4. **Solid architecture** - Clean code, testable
5. **Dev experience** - Hot reload, helpful errors

---

## Actual Performance (Benchmarked)

- **Small sites (10-100 pages):** 0.1-0.3s ⚡
- **Medium sites (100-500 pages):** 0.3-2.0s ⚡
- **Large sites (500-1,000 pages):** 2-5s ⚡
- **Very large sites (1K+ pages):** ~3.5s ⚡

**Bengal is the 2nd fastest SSG (only Hugo is faster!)**
- ✅ Faster than Eleventy, Jekyll, Gatsby
- ✅ Fastest Python SSG by far
- ✅ Sub-linear scaling (excellent architecture)

---

## What We're NOT Trying to Be

### Not Hugo
- Hugo is 10x-100x faster
- Written in Go with 10+ years of optimization
- We won't beat it on speed
- **That's okay**

### Not Sphinx
- Sphinx has 15+ years of Python autodoc
- Built for API documentation
- Massive feature set for technical docs
- **We're not going there**

### Not for massive sites
- Other tools are better for 1K+ pages
- **We're okay with that**

---

## Strategic Direction: Focus & Polish

### Core Strategy
**Be excellent at one thing: Simple static sites with great DX**

### Not Strategy
- Chasing performance numbers
- Feature parity with everything
- Trying to replace established tools

---

## Roadmap (Priority-Based, Not Time-Based)

### Phase 1: Document & Polish

**Focus:** Make what we have discoverable and smooth

**High Priority:**
- Complete documentation (getting started, config, templates)
- **Document autodoc** - it's a killer feature, needs visibility
- Better error messages and UX polish
- Fix known bugs
- Create 2-3 showcase sites (including autodoc example)

**Why:** Features don't matter if nobody knows they exist. First impression matters.

**Goal:** Bengal is solid, documented, and ready to show

---

### Phase 2: Validate & Iterate

**Focus:** Real users, real feedback

**High Priority:**
- Soft launch (Python community, Show HN, etc.)
- Get 5-10 real users
- Watch them use it, fix friction
- Build real sites (deployed)
- Deployment guides

**Why:** Theory vs practice. Real usage reveals real needs.

**Goal:** 5-10 real users building real sites successfully

---

### Phase 3: Grow Sustainably

**Focus:** Respond to actual needs, not speculation

**High Priority:**
- Fix pain points from real users
- Add small features users actually request
- Theme variants if needed
- Keep it simple

**Why:** Let users guide development. Don't build what nobody asked for.

**Goal:** Sustainable project with happy users

---

## Success Metrics (Realistic)

### 3 Months
- ✅ Complete documentation
- ✅ 5 real users
- ✅ 20+ GitHub stars
- ✅ 2-3 example sites deployed

### 6 Months
- ✅ 10-20 real users
- ✅ 50+ GitHub stars
- ✅ Active issues/discussions
- ✅ Known for good DX

### 12 Months
- ✅ 50+ real users
- ✅ 200+ GitHub stars
- ✅ Small helpful community
- ✅ Sustainable maintenance

---

## What We're NOT Measuring

- ❌ Competing with Hugo/Jekyll on speed
- ❌ Thousands of users
- ❌ Enterprise adoption
- ❌ Conference talks
- ❌ Venture funding
- ❌ Huge GitHub star count

---

## Decision Framework

**When considering new features/work:**

Ask:
1. Does it help our target audience (small sites)?
2. Can we implement it well in < 1 week?
3. Will it make Bengal simpler or more complex?
4. Did a real user ask for it?

If 3+ yes: Consider it  
If < 3 yes: Probably skip it

---

## Things We Won't Do

### ❌ Python autodoc system
- Months of work
- Complex edge cases  
- Not our strength
- Sphinx does it better

### ❌ Rust integration
- Adds complexity
- Marginal gains
- Wrong direction

### ❌ Plugin architecture
- Premature
- Adds complexity
- No users asking

### ❌ Advanced optimization
- Diminishing returns
- Current speed is fine
- Better uses of time

### ❌ Versioned docs
- Complex feature
- Small audience
- Not essential

---

## Marketing Position

### ✅ Say:
- "Simple Python static site generator"
- "Good for personal blogs and small sites"
- "Clean Markdown + TOML workflow"
- "Solid defaults, good developer experience"
- "Fast enough for small-medium sites"
- "Easy to understand and customize"

### ❌ Don't say:
- "Blazing fast" - we're not
- "Production-ready at scale" - nope
- "Sphinx alternative" - we're not
- "Hugo speed with Python flexibility" - false
- "50-900x faster" - unvalidated claim
- "Enterprise-ready" - we're not

---

## Risk Mitigation

### Risk: No users
**Mitigation:** That's okay, still useful for personal projects

### Risk: Slow builds discourage users
**Mitigation:** Set clear expectations about target site sizes

### Risk: Python ecosystem moves on
**Mitigation:** Keep dependencies minimal and up to date

### Risk: Burnout
**Mitigation:** Sustainable pace, don't over-commit

---

## Resource Allocation

**Time available:** ~10 hours/week (assumption)

**Allocation:**
- 40% Documentation
- 30% Bug fixes / stability
- 20% UX improvements
- 10% New features (small only)

**Not allocating time to:**
- Big new features
- Performance optimization
- Competing with other tools
- Marketing beyond basics

---

## Principles Going Forward

1. **Honesty** - Don't overpromise capabilities
2. **Focus** - Do a few things well
3. **Simplicity** - Resist feature creep
4. **Iteration** - Small improvements, frequently
5. **Users** - Listen to real feedback
6. **Acceptance** - We're not Hugo, that's fine
7. **Sustainability** - Maintainable pace
8. **Strategic over tactical** - With AI, building is fast. The question isn't "can we?" but "should we?"

---

## The Big Picture

**Bengal aims to be:**
- The simplest Python SSG
- Best DX in the Python SSG space
- Reliable and well-documented
- Good for 80% of small site use cases

**Bengal doesn't aim to be:**
- The fastest SSG
- The most feature-rich
- An everything-to-everyone tool
- The industry standard

---

## Next Actions

1. ✅ Archive over-ambitious plans
2. ✅ Update README with honest positioning
3. ⏳ Write documentation (Week 1-2)
4. ⏳ Polish UX (Week 3-4)
5. ⏳ Create examples (Week 5-6)
6. ⏳ Test and iterate (Week 7-8)

---

## Bottom Line

**Focus on being excellent at what we are, not trying to be what we're not.**

Build a simple, solid, well-documented SSG for people who want a Python-based tool for small sites.

That's enough. That's valuable. That's achievable.

---

**Stop planning. Start shipping.**
