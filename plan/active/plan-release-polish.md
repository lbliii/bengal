# Release Plan: 0.1.5/0.1.6 Polish & Hardening

**Status**: Active  
**Goal**: Finalize robustness and developer experience polish post-hardening.  
**Focus**: Validation of implemented features, UI/UX polish for tracks, and closing security gaps.

---

## Executive Summary

While researching the "Next Batch" of work, we discovered that several high-impact features (Hugo-like template functions, Graph Analysis logic) are **already implemented** in the codebase but lack documentation or CLI exposure.

This plan pivots from "New Feature Implementation" to **"Verification, Polish, and Exposure"**. We will focus on validating existing code, fixing visible UI/UX bugs in the Tracks system, and closing the remaining security audit findings.

**Key Deliverables**:
1.  Verified & Documented Template Functions (Hugo parity)
2.  Polished Tracks System (UI/UX fixes)
3.  Security Hardening (Input validation)
4.  Graph Analysis CLI Integration (Insights exposure)

---

## Phase 1: Verification & Documentation (Template Functions)
**Status**: Code exists (`bengal/rendering/template_functions/collections.py`), needs verification.

- [ ] **Audit Tests**: Review `tests/unit/template_functions/test_collections.py` to ensure coverage for:
    - [ ] `where` with operators (`gt`, `lt`, `in`, `not_in`)
    - [ ] `union`, `intersect`, `complement`
    - [ ] `first`, `last`, `reverse`
- [ ] **Add Missing Tests**: If coverage is low, add `tests/unit/template_functions/test_hugo_parity.py`.
- [ ] **Update Documentation**:
    - [ ] Update `content/docs/reference/template-functions.md` with examples of new operators.
    - [ ] Add a "Hugo Migration Guide" section showing equivalent Bengal syntax.

## Phase 2: Tracks System Polish (UI/UX)
**Status**: Critical bugs and missing styles.

- [ ] **Fix Formatting Bug**: Repair malformed comment in `bengal/themes/default/templates/partials/track_nav.html` (lines 10-11).
- [ ] **Improve Navigation Logic**: Update `tracks/list.html` to link to the Track Overview page (`/tracks/{slug}`) instead of the first lesson, or make it configurable.
- [ ] **Create Track Styles**:
    - [ ] Create `bengal/themes/default/assets/css/components/tracks.css`.
    - [ ] Implement visual hierarchy for Track Overview (Syllabus, Progress).
    - [ ] Improve "Next/Prev" navigation buttons in `track_nav.html`.
- [ ] **Semantic HTML**: Refactor `tracks/single.html` to use `<article>`, `<nav>`, and proper ARIA labels.

## Phase 3: Security Hardening
**Status**: Closing P2/P3 audit findings.

- [ ] **Theme Install Validation**:
    - [ ] Update `bengal/cli/commands/theme.py` to validate `name` argument against a safe regex (prevent malicious package names).
- [ ] **Variable Substitution Sandboxing**:
    - [ ] Update `bengal/rendering/plugins/variable_substitution.py` to block access to attributes starting with `_` or `__` (e.g., `__class__`).

## Phase 4: Graph Analysis Exposure
**Status**: Logic exists, CLI integration missing.

- [ ] **CLI Output**: Update `bengal/cli/commands/graph/__main__.py` to call `graph.get_actionable_recommendations()` and print them to the console during `analyze`.
- [ ] **HTML Report**: Update `bengal/analysis/graph_visualizer.py` to include these insights in the generated HTML dashboard.

---

## Archived Plans
The following plans are superseded by this document and the current codebase state:
- `plan/active/hugo-like-template-enhancements.md` (Implemented)
- `plan/active/graph-analysis-enhancements.md` (Partially Implemented/Integrated here)
- `plan/active/track-templates-improvement.md` (Integrated here)

## Next Steps
1.  Execute Phase 1 (Tests & Docs).
2.  Execute Phase 2 (Tracks UI).
3.  Execute Phase 3 (Security).
4.  Execute Phase 4 (Graph CLI).

