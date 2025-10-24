---
description: Extract verifiable, evidence-backed claims from source code and tests with confidence scoring
globs: ["bengal/**/*.py", "tests/**/*.py", "architecture/**/*.md"]
alwaysApply: false
---

# Bengal Research & Evidence Extraction

**Purpose**: Extract verifiable claims from source code and tests for features or changes.

**Shortcut**: `::research`

**Principle**: NEVER invent facts. Only make claims backed by code references (`file:line`).

---

## Overview

Evidence-first research from the Bengal codebase. Produces structured claims with code references, criticality ratings, and confidence scores.

---

## Procedure

### Step 1: Scope Definition

Identify target modules/subsystems from context or user query.

**Example**: "Research rendering pipeline" → `bengal/rendering/`, `architecture/rendering.md`

### Step 2: Evidence Collection

**Sources** (in priority order):
1. **Source Code**: `bengal/` modules (primary truth)
2. **Tests**: `tests/unit/`, `tests/integration/` (behavior verification)
3. **Architecture Docs**: `architecture/*.md` (design intent)
4. **Config**: `bengal.toml` schema, defaults in code

**Tools**:
- `codebase_search`: Semantic search for concepts
- `grep`: Exact symbol/function searches
- `read_file`: Read identified files

**Process**:
1. Start broad: semantic search for main concepts
2. Narrow down: grep for specific classes/functions
3. Read code: extract signatures, docstrings, logic
4. Cross-reference: verify in tests
5. Check config: find defaults and schema

### Step 3: Claim Extraction

For each finding, produce a **structured claim**:

```yaml
claim:
  description: "[What the code does/provides]"
  evidence:
    - source: "bengal/module/file.py:45-52"
      type: "code"
      excerpt: "[brief code snippet or signature]"
    - source: "tests/unit/test_module.py:120"
      type: "test"
      excerpt: "[test name or assertion]"
  criticality: [HIGH | MEDIUM | LOW]
  confidence: [0-100%]
  reasoning: "[Why this claim is justified]"
```

**Criticality Levels**:
- **HIGH**: API contracts, core behavior, user-facing features
- **MEDIUM**: Internal implementation, performance characteristics
- **LOW**: Code style, optional features

### Step 4: Cross-Validation

For **HIGH** criticality claims, apply **self-consistency** (3 paths):
- **Path A**: Source code evidence
- **Path B**: Test evidence (does test verify the claim?)
- **Path C**: Config/schema evidence (is it configurable?)

Agreement across 2+ paths → high confidence.

---

## Output Format

```markdown
## 📚 Research: [Topic/Module]

### Executive Summary
[2-3 sentences: what was researched, key findings, confidence level]

### Evidence Summary
- **Claims Extracted**: [N]
- **High Criticality**: [N]
- **Medium Criticality**: [N]
- **Low Criticality**: [N]
- **Average Confidence**: [N]%

---

### 🔴 High Criticality Claims

#### Claim 1: [Description]
**Evidence**:
- ✅ **Source**: `bengal/core/site.py:145-150`
  ```python
  def build(self, incremental: bool = False):
      """Build the site with optional incremental mode."""
  ```
- ✅ **Test**: `tests/unit/test_site.py:89`
  - Test: `test_incremental_build_only_rebuilds_changed_pages`
- ✅ **Config**: `bengal.toml` schema allows `build.incremental = true`

**Confidence**: 95% 🟢
**Reasoning**: All three paths agree; API is stable and tested.

---

#### Claim 2: [Description]
[Similar structure]

---

### 🟡 Medium Criticality Claims
[Similar structure, may skip 3-path validation]

---

### 🟢 Low Criticality Claims
[Brief list format]

---

### 📋 Next Steps
- [ ] Use findings for RFC (run `::rfc`)
- [ ] Identify gaps requiring SME input
- [ ] Update architecture docs if drift detected
```

---

## Prompting Techniques

- **ReAct**: Reason → search → read → refine loop
- **Chain-of-Thought**: Explicit reasoning per claim
- **Self-Consistency**: 3-path validation for HIGH criticality
- **Example-guided**: Use claim schema template

---

## Bengal Integration

### Key Evidence Sources

**Core**:
- `bengal/core/site.py` - Site orchestrator
- `bengal/core/page/*.py` - Page model
- `bengal/core/theme.py` - Theme resolution
- `bengal/core/asset.py` - Asset handling

**Orchestration**:
- `bengal/orchestration/render_orchestrator.py` - Render pipeline
- `bengal/orchestration/build_orchestrator.py` - Build coordination
- `bengal/orchestration/incremental_builder.py` - Incremental builds

**Rendering**:
- `bengal/rendering/jinja_env.py` - Jinja setup
- `bengal/rendering/markdown/*.py` - Markdown processing
- `bengal/rendering/shortcodes/*.py` - Shortcodes

**Cache**:
- `bengal/cache/build_cache.py` - Build cache
- `bengal/cache/indexes/*.py` - Query indexes
- `bengal/cache/dependency_tracker.py` - Dependencies

**Health**:
- `bengal/health/validators/*.py` - Validators
- `bengal/health/checks/*.py` - Health checks

**CLI**:
- `bengal/cli/commands/*.py` - CLI commands

**Tests**:
- `tests/unit/` - Unit tests
- `tests/integration/` - Integration tests
- `tests/performance/` - Performance benchmarks
