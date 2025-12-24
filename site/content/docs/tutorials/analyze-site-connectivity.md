---
title: Analyze and Improve Site Connectivity
nav_title: Analyze Site
description: Learn to discover, interpret, and act on site structure insights using Bengal's graph analysis tools
weight: 50
draft: false
lang: en
tags:
- tutorial
- analysis
- graph
- seo
- connectivity
keywords:
- graph analysis tutorial
- site connectivity
- internal linking
- orphan pages
- seo optimization
category: tutorial
---

# Analyze and Improve Site Connectivity

In this tutorial, you'll learn to use Bengal's graph analysis tools to discover connectivity issues, interpret the results, and take action to improve your site's internal linking structure.

**What you'll learn:**
- Run a connectivity analysis on your site
- Interpret the output and understand what it means
- Prioritize which pages need attention
- Fix connectivity issues
- Set up CI gates to prevent regression

**Time:** 15-20 minutes

**Prerequisites:**
- A Bengal site with content
- Basic familiarity with the command line

---

## Steps

:::{steps}

:::{step} Run Your First Analysis

Start by getting an overview of your site's connectivity:

```bash
bengal graph report
```

:::{example-label} Output
:::

```
================================================================================
📊 Site Analysis Report
================================================================================

📈 Overview
   Total pages:        124
   Total links:        316
   Avg links/page:     2.5
   Avg conn. score:    1.46

🔗 Connectivity Distribution
   🟢 Well-Connected:      39 pages (31.5%)
   🟡 Adequately:          38 pages (30.6%)
   🟠 Lightly Linked:      26 pages (21.0%)
   🔴 Isolated:            21 pages (16.9%) ⚠️

🔴 Isolated Pages (need attention)
      • content/_index.md
      • content/docs/_index.md
      ... and 19 more

💡 Recommendations
   • Add explicit cross-references to isolated pages
   • Add internal links to lightly-linked pages
================================================================================
```

**What this tells you:**
- **124 pages** are being analyzed (autodoc pages excluded by default)
- **Avg conn. score: 1.46** — This is good (≥1.0 is healthy)
- **31.5% well-connected** — About a third of your pages have strong linking
- **16.9% isolated** — These pages have almost no incoming links

:::{/step}

:::{step} Understand the Connectivity Levels

Bengal uses a **weighted scoring system** based on link types:

| Link Type | Weight | What It Means |
|-----------|--------|---------------|
| Explicit | 1.0 | You wrote `[link text](url)` in markdown |
| Menu | 10.0 | Page appears in navigation menu |
| Taxonomy | 1.0 | Shares tags/categories with other pages |
| Related | 0.75 | Algorithm computed "related posts" |
| Topical | 0.5 | Parent `_index.md` links to children |
| Sequential | 0.25 | Next/prev navigation in section |

**The score determines the level:**

| Level | Score | What It Means |
|-------|-------|---------------|
| 🟢 Well-Connected | ≥ 2.0 | Multiple link types pointing here |
| 🟡 Adequately | 1.0 - 2.0 | Has some connections |
| 🟠 Lightly Linked | 0.25 - 1.0 | Only structural links (parent/nav) |
| 🔴 Isolated | < 0.25 | Almost no incoming links |

:::{/step}

:::{step} Investigate Isolated Pages

Let's look at what's actually isolated:

```bash
bengal graph orphans --level isolated
```

:::{example-label} Output
:::

```
📊 Connectivity Distribution
==========================================================================================
  🟢 Well-Connected (≥2.0):      39 pages (31.5%)
  🟡 Adequately Linked (1-2):    38 pages (30.6%)
  🟠 Lightly Linked (0.25-1):    26 pages (21.0%)
  🔴 Isolated (<0.25):           21 pages (16.9%)
==========================================================================================

🔴 Isolated Pages (21 total)
==========================================================================================
#    Score    Path                                          Title
------------------------------------------------------------------------------------------
1    0.00     content/_index.md                             Home
2    0.00     content/docs/_index.md                        Documentation
3    0.00     content/docs/about/_index.md                  About
...
```

**Key insight:** Notice that most isolated pages are `_index.md` files!

:::{tip} Why Are Index Pages Isolated?

This is **expected behavior**, not a bug:

1. **Topical links flow downward** — Parent `_index.md` links TO children, not the reverse
2. **Index pages sit at hierarchy tops** — No parent above them to link down
3. **They depend on navigation** — Menus, breadcrumbs, URLs — not content links

**Should you "fix" these?** It depends:
- If the index is in your main menu → It gets menu links (weight 10.0), won't be isolated
- If it's a deep section index → Consider adding explicit links FROM child pages
:::

:::{/step}

:::{step} Find Pages That Need Real Attention

The **lightly linked** pages are often more actionable than isolated ones:

```bash
bengal graph orphans --level lightly
```

:::{example-label} Output
:::

```
🟠 Lightly Linked Pages (26 total)
==========================================================================================
#    Score    Path                                          Title
------------------------------------------------------------------------------------------
1    0.50     content/authors/lbliii.md                     Lawrence Lane
2    0.50     content/docs/content/analysis/graph.md        Graph Analysis
3    0.50     content/docs/content/component-model.md       The Component Model
4    0.75     content/docs/about/glossary.md                Glossary
5    0.75     content/docs/reference/cheatsheet.md          Cheatsheet
...
```

**These pages have a score of 0.5-0.75**, meaning they only have topical links from their parent section. They're discoverable via navigation but **no other content links to them**.

**Action:** Add explicit cross-references to these pages from related content.

:::{/step}

:::{step} Get Detailed Metrics

For deeper analysis, export to JSON:

```bash
bengal graph orphans --level lightly --format json
```

:::{example-label} JSON Output
:::

```json
{
  "level_filter": "lightly",
  "distribution": {
    "isolated": 21,
    "lightly_linked": 26,
    "adequately_linked": 38,
    "well_connected": 39
  },
  "pages": [
    {
      "path": "content/docs/about/glossary.md",
      "title": "Glossary",
      "score": 0.75,
      "metrics": {
        "explicit": 0,
        "menu": 0,
        "taxonomy": 0,
        "related": 0,
        "topical": 1,
        "sequential": 1
      }
    }
  ]
}
```

**Reading the metrics:**
- `explicit: 0` — No markdown links point here
- `topical: 1` — Parent `_index.md` links here (0.5 × 1 = 0.5)
- `sequential: 1` — Has next/prev nav (0.25 × 1 = 0.25)
- **Total: 0.75** — Only structural links, no human cross-references

:::{/step}

:::{step} Find Important Pages to Prioritize

Not all under-linked pages are equally important. Use PageRank:

```bash
bengal graph pagerank --top-n 10
```

:::{example-label} Output
:::

```
🏆 Top 10 Pages by PageRank
====================================================================================================
Rank   Title                                         Score        In    Out
----------------------------------------------------------------------------------------------------
1      Template Functions Reference                  0.04669      7.5   2
2      Templating                                    0.03515      6     1
3      Analysis System                               0.02980      2.0   2
4      Health Check System                           0.02592      3.0   2
5      Theme Variables Reference                     0.02559      5.5   2
```

**Cross-reference with under-linked pages:**
- Is "Glossary" in the top PageRank? If yes, prioritize linking to it
- Low PageRank + lightly linked = low priority
- High PageRank + lightly linked = **fix this first**

:::{/step}

:::{step} Fix a Connectivity Issue

Let's improve the Glossary page (score: 0.75).

**Current state:** Only has topical + sequential links

**Goal:** Add explicit cross-references from related content

### Find Related Content

Look for pages that mention glossary terms:

```bash
grep -r "see glossary" content/docs/ --include="*.md"
grep -r "defined in" content/docs/ --include="*.md"
```

### Add Cross-References

In related pages, add links:

```markdown
<!-- In content/docs/about/concepts/configuration.md -->
For definitions of these terms, see the [Glossary](/docs/about/glossary/).
```

```markdown
<!-- In content/docs/get-started/quickstart-writer.md -->
New to Bengal? Check the [Glossary](/docs/about/glossary/) for key terms.
```

### Verify Improvement

Run the analysis again:

```bash
bengal graph orphans --format json | grep -A 10 "glossary"
```

**After adding 2 explicit links:**
```json
{
  "path": "content/docs/about/glossary.md",
  "score": 2.75,
  "metrics": {
    "explicit": 2,
    "topical": 1,
    "sequential": 1
  }
}
```

**Score improved from 0.75 → 2.75** (now 🟢 Well-Connected!)

:::{/step}

:::{step} Set Up CI Gates

Prevent connectivity regression with CI checks:

```bash
# Fail if more than 25 isolated pages
bengal graph report --ci --threshold-isolated 25

# Brief output for CI logs
bengal graph report --brief --ci --threshold-isolated 25
```

:::{example-label} CI Output (passing)
:::

```
📊 Site Analysis: 124 pages
   Isolated: 21 (16.9%) ✅
   Lightly linked: 26 (21.0%)
   Avg score: 1.46 (good)
✅ CI PASSED: 21 isolated pages within threshold (25)
```

:::{example-label} CI Output (failing)
:::

```
📊 Site Analysis: 124 pages
   Isolated: 30 (24.2%) ⚠️
❌ CI FAILED: 30 isolated pages exceeds threshold (25)
```

### GitHub Actions Example

```yaml
name: Content Quality
on: [push, pull_request]

jobs:
  connectivity:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Bengal
        run: pip install bengal

      - name: Check connectivity
        run: bengal graph report --ci --threshold-isolated 25

      - name: Save report artifact
        if: always()
        run: bengal graph report --format json > connectivity-report.json

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: connectivity-report
          path: connectivity-report.json
```

:::{/step}

:::{step} Track Progress Over Time

Save reports periodically to track improvement:

```bash
# Weekly connectivity snapshot
bengal graph report --format json > reports/connectivity-$(date +%Y-%m-%d).json

# Export under-linked pages
bengal graph orphans --level all --format json > reports/under-linked-$(date +%Y-%m-%d).json
```

**Compare over time:**

```bash
# Week 1
{"isolated": 21, "lightly_linked": 26, "avg_score": 1.46}

# Week 4 (after improvements)
{"isolated": 15, "lightly_linked": 18, "avg_score": 1.82}
```

:::{/step}

:::{/steps}

---

## Summary

You've learned to:

:::{checklist}
- [x] **Run analysis** with `bengal graph report`
- [x] **Interpret levels** — Isolated vs. lightly linked vs. adequate
- [x] **Understand why** — Index pages being isolated is expected
- [x] **Prioritize** — Use PageRank to focus on important pages
- [x] **Fix issues** — Add explicit cross-references
- [x] **Verify improvement** — Re-run analysis to confirm
- [x] **Prevent regression** — Set up CI gates
:::

## Quick Reference

| Task | Command |
|------|---------|
| Full report | `bengal graph report` |
| List isolated | `bengal graph orphans --level isolated` |
| List under-linked | `bengal graph orphans --level all` |
| Page importance | `bengal graph pagerank --top-n 20` |
| Link suggestions | `bengal graph suggest --min-score 0.5` |
| CI check | `bengal graph report --ci --threshold-isolated N` |
| Export JSON | `bengal graph report --format json` |

## Next Steps

- [Graph Analysis Reference](/docs/content/analysis/graph/) — Full command documentation
- [Health Check System](/docs/reference/architecture/subsystems/health/) — Automated validation
- [SEO Best Practices](/docs/building/performance/) — Optimize for search engines

---

**Feedback?** Found this tutorial helpful or confusing? [Open an issue](https://github.com/bengal/bengal/issues) to let us know!
