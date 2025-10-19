Title: Testing Strategy - Visual Summary

---

## The Problem You Identified

```
Your Experience:
┌─────────────────────────────────────────────────────────────┐
│ Test Progress                                               │
│ ████████████████████████████████████████░░░ 95%             │
│ Fast! ↑                                                     │
│                                                             │
│ ░ 95-100%                                                   │
│ Slow... waiting... still waiting... ↑                       │
│ (2-5 minutes of frustration)                                │
└─────────────────────────────────────────────────────────────┘
```

## Root Cause (What We Found)

```
Worker Distribution with pytest -n auto:

Time →
Worker 1: [fast][fast][fast][fast]................ IDLE (waiting)
Worker 2: [fast][fast][fast].................. IDLE (waiting)
Worker 3: [fast][SHOWCASE×11]████████████████████████ (3-4 min)
Worker 4: [fast][STATEFUL]███████████████ (1-3 min)
          ↑                                          ↑
       20 seconds                             Last 5% = pain

Problem: test_output_quality.py rebuilds 292-page showcase 11 TIMES
         (function-scoped fixture for read-only tests)
```

## Phase 0 Quick Wins (30 minutes of work)

```
┌─────────────────────────────────────────────────────────────┐
│ Fix #1: Change fixture scope (5 minutes)                   │
│                                                             │
│ Before:                          After:                     │
│ @pytest.fixture                  @pytest.fixture            │
│ def built_site(tmp_path):        def built_site(          │
│                                      tmp_path_factory):     │
│                                      scope="class"          │
│                                                             │
│ Result: 11 builds → 1 build                                │
│ Impact: SAVES 1.5-4 MINUTES ⚡                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Fix #2: Add @pytest.mark.slow (2 minutes)                  │
│                                                             │
│ @pytest.mark.slow                                           │
│ class TestOutputQuality:                                    │
│     ...                                                     │
│                                                             │
│ Enables: pytest -m "not slow"                               │
│ Impact: 20-second feedback loop for devs ⚡                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Fix #3: Tune Hypothesis (5 minutes)                        │
│                                                             │
│ settings.register_profile("ci", max_examples=100)           │
│ settings.register_profile("dev", max_examples=20)           │
│                                                             │
│ Result: 100 examples → 20 in dev                            │
│ Impact: SAVES 30-90 SECONDS ⚡                              │
└─────────────────────────────────────────────────────────────┘
```

## Results

```
╔═══════════════════════════════════════════════════════════╗
║ BEFORE Phase 0                                            ║
╠═══════════════════════════════════════════════════════════╣
║ Full suite:     5-6 minutes  ████████████████████████████ ║
║ - Fast tests:   20 seconds   ████                         ║
║ - Long tail:    3-5 minutes  ████████████████████████     ║
║                              ↑ YOU ARE HERE (frustrated)  ║
╚═══════════════════════════════════════════════════════════╝

                        ⬇ APPLY PHASE 0 FIXES ⬇

╔═══════════════════════════════════════════════════════════╗
║ AFTER Phase 0 (30 min work)                              ║
╠═══════════════════════════════════════════════════════════╣
║ Dev mode:       ~20 seconds  ████ ✨                      ║
║ (skip slow)                                               ║
║                                                           ║
║ Full suite:     ~1 minute    ████████ ✨                  ║
║ - Fast tests:   20 seconds   ████                         ║
║ - Long tail:    30-60 sec    ████                         ║
║                              ↑ MUCH BETTER!               ║
╚═══════════════════════════════════════════════════════════╝

                    ⬇ IMPLEMENT FULL RFC (Phases 1-3) ⬇

╔═══════════════════════════════════════════════════════════╗
║ AFTER Full RFC (2-3 weeks implementation)                ║
╠═══════════════════════════════════════════════════════════╣
║ Dev mode:       ~15 seconds  ███ 🚀                       ║
║ Full suite:     ~40 seconds  ███████ 🚀                   ║
║                                                           ║
║ Bonus: New tests are 10 lines instead of 50-100          ║
╚═══════════════════════════════════════════════════════════╝
```

## The RFC Strategy (Simplified)

```
┌────────────────────────────────────────────────────────────┐
│ Phase 0: Quick Wins (30 minutes) ← START HERE             │
│ - Fix fixture scope for test_output_quality.py            │
│ - Add slow markers                                         │
│ - Tune Hypothesis                                          │
│ IMPACT: 70-80% long-tail reduction                         │
└────────────────────────────────────────────────────────────┘
                            ⬇
┌────────────────────────────────────────────────────────────┐
│ Phase 1: Infrastructure (2-3 days)                         │
│ - Create tests/roots/ with 5 minimal sites                 │
│ - Implement @pytest.mark.bengal marker                     │
│ - Build supporting utilities (cli runner, normalize, etc)  │
│ GOAL: Make new tests easy to write                         │
└────────────────────────────────────────────────────────────┘
                            ⬇
┌────────────────────────────────────────────────────────────┐
│ Phase 2: Pilot (2-3 days)                                  │
│ - Migrate 5-8 high-duplication tests                       │
│ - Validate ergonomics                                      │
│ DECISION: Does it feel good? Proceed or adjust             │
└────────────────────────────────────────────────────────────┘
                            ⬇
┌────────────────────────────────────────────────────────────┐
│ Phase 3: Selective Migration (3-4 days)                    │
│ - Migrate 30-40 tests total (1.5% of suite)                │
│ - Focus on high-duplication integration tests              │
│ - Leave unit tests alone (they're fine)                    │
│ RESULT: Pattern established for future tests               │
└────────────────────────────────────────────────────────────┘
```

## Example: Before vs After RFC

```python
# BEFORE (current style) - 30 lines, lots of duplication
def test_build_with_path_baseurl(tmp_path: Path):
    site_dir = tmp_path / "site"
    (site_dir / "content").mkdir(parents=True)
    (site_dir / "public").mkdir(parents=True)

    cfg = site_dir / "bengal.toml"
    cfg.write_text(f"""
[site]
title = "Test"
baseurl = "/bengal"

[build]
output_dir = "public"
    """, encoding="utf-8")

    (site_dir / "content" / "index.md").write_text(
        """---\ntitle: Home\n---\n# Home\n""",
        encoding="utf-8"
    )

    site = Site.from_config(site_dir)
    orchestrator = BuildOrchestrator(site)
    orchestrator.build()

    assert (site_dir / "public" / "assets").exists()
    html = (site_dir / "public" / "index.html").read_text()
    assert 'href="/bengal/assets/css/style' in html

# AFTER RFC - 8 lines, clear intent, reusable
@pytest.mark.bengal(
    testroot="test-baseurl",
    confoverrides={"site.baseurl": "/bengal"}
)
def test_build_with_path_baseurl(site, build_site):
    build_site()

    assert (site.output_dir / "assets").exists()
    html = (site.output_dir / "index.html").read_text()
    assert 'href="/bengal/assets/css/style' in html
```

## Test Roots Structure

```
tests/
├── roots/                          ← NEW: Reusable minimal sites
│   ├── README.md                   "Purpose of each root"
│   ├── test-basic/                 1 page, default theme
│   │   ├── bengal.toml
│   │   └── content/
│   │       └── index.md
│   ├── test-baseurl/               2 pages, baseurl testing
│   │   ├── bengal.toml            (baseurl = "/site")
│   │   └── content/
│   │       ├── index.md
│   │       └── about.md
│   ├── test-taxonomy/              3 pages, 2 tags
│   ├── test-templates/             Template examples
│   └── test-assets/                Custom + theme assets
│
├── _testing/                       ← NEW: Shared utilities
│   ├── __init__.py
│   ├── fixtures.py                 rootdir, site_factory
│   ├── markers.py                  @pytest.mark.bengal
│   ├── cli.py                      run_cli() wrapper
│   ├── normalize.py                HTML/JSON normalization
│   └── README.md
│
├── integration/                    Some tests use roots
├── unit/                           Left alone (already fast)
└── conftest.py                     Loads _testing plugin
```

## Conservative Approach Highlights

```
✅ DOING:
- Quick wins first (validate approach)
- Selective migration (30-40 tests, not all 2,297)
- Clear, explicit assertions (readable)
- Subprocess-based CLI tests (true e2e)
- Class-scoped fixtures for read-only tests

❌ NOT DOING (lessons from review):
- Snapshot everything (brittle, deferred to Phase 5+)
- Migrate all tests (unit tests are fine)
- Over-abstract (keep tests readable)
- Mock everything (prefer black-box)
- Commit to patterns before validating
```

## What Makes This Worthwhile

```
┌──────────────────────────────────────────────────────────┐
│ IMMEDIATE PAIN RELIEF (Phase 0)                          │
│ Your 95% long-tail problem: FIXED                        │
│ Time investment: 30 minutes                              │
│ Time savings: 2-4 min per test run                       │
│ ROI: Pays back after ~10 test runs (same day!)           │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ LONG-TERM BENEFITS (Full RFC)                            │
│ ✨ New tests: 10 lines vs 50-100                         │
│ ✨ Fast feedback: 15-20s dev loop                        │
│ ✨ Less duplication: DRY test setup                      │
│ ✨ Better isolation: Consistent cleanup                  │
│ ✨ Easier reviews: Clear intent, less noise              │
└──────────────────────────────────────────────────────────┘
```

## Validation (How We Know It Works)

```bash
# Before Phase 0
$ time pytest tests/integration/test_output_quality.py -v
...
real    4m23s  ← SLOW 🐌

# Apply Phase 0 fixes (30 minutes work)

# After Phase 0
$ time pytest tests/integration/test_output_quality.py -v
...
real    0m18s  ← FAST ⚡ (14x speedup!)

# Dev workflow
$ time pytest -m "not slow" -n auto
...
real    0m20s  ← FAST FEEDBACK ⚡

# Full suite
$ time pytest -n auto
...
real    1m05s  ← ACCEPTABLE ✅ (vs 5-6 min before)
```

## Decision Tree

```
                    START
                      │
                      ▼
        ┌─────────────────────────┐
        │ Execute Phase 0?        │
        │ (30 min, high impact)   │
        └────────┬────────────────┘
                 │
          ┌──────┴──────┐
          │             │
         YES            NO
          │             │
          ▼             ▼
    ┌─────────┐   ┌──────────┐
    │ Apply   │   │ Review   │
    │ fixes   │   │ RFC only │
    └────┬────┘   └──────────┘
         │
         ▼
    ┌─────────────────────┐
    │ Long tail fixed?    │
    │ (measure impact)    │
    └────────┬────────────┘
             │
      ┌──────┴──────┐
      │             │
     YES            NO
      │             │
      ▼             ▼
┌──────────┐   ┌────────────┐
│ Proceed  │   │ Investigate│
│ to RFC   │   │ (unlikely) │
│ Phase 1  │   └────────────┘
└──────────┘
      │
      ▼
┌──────────────────────┐
│ Implement Phase 1-3  │
│ (2-3 weeks total)    │
└──────────────────────┘
      │
      ▼
┌──────────────────────┐
│ Fast, ergonomic      │
│ test suite! 🎉       │
└──────────────────────┘
```

## Summary

**Your pain point is real and fixable.**

- **30 minutes of work** (Phase 0) → 70-80% improvement in long tail
- **2-3 weeks of work** (Full RFC) → Systematic, long-term solution

**Start with Phase 0, validate, then decide on full RFC.**

The quick wins validate the strategy, and the full RFC builds on what works.
