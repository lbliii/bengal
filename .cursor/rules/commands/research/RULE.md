---
description: Extract verifiable, evidence-backed claims from Bengal codebase with confidence scoring
alwaysApply: false
globs: ["bengal/**/*.py", "tests/**/*.py"]
---

# Research

Extract verifiable claims from source code and tests. Every claim must have a `file:line` reference.

**Shortcut**: `::research`

**Works with**: `modules/evidence-handling`, `modules/output-format`

---

## Principle

> **NEVER invent facts. Only make claims backed by code references.**

---

## Procedure

### Step 1: Scope Definition

Identify target from context or query:

```yaml
examples:
  "How does PageCore work?" → bengal/core/page/page_core.py
  "Where is incremental build?" → bengal/orchestration/incremental_builder.py
  "How do directives validate?" → bengal/directives/contracts.py, validator.py
```

### Step 2: Evidence Collection

**Priority order**:
1. **Source Code** (`bengal/`) - Primary truth
2. **Tests** (`tests/`) - Behavior verification
3. **Architecture Docs** (`architecture/`) - Design intent
4. **Config** (`pyproject.toml`, `bengal.toml`) - Settings

**Search strategy**:
```yaml
1. Semantic search: Broad concept discovery
   tool: codebase_search
   query: "How does [concept] work?"

2. Symbol search: Find exact definitions
   tool: grep
   pattern: "def function_name\\(|class ClassName"

3. Read code: Extract with context
   tool: read_file
   target: identified file

4. Cross-reference: Find tests
   tool: grep
   pattern: "test.*function_name"
   path: tests/
```

### Step 3: Claim Extraction

For each finding, produce a structured claim:

```yaml
claim:
  description: "PageCore is a frozen dataclass for cacheable metadata"
  evidence:
    - source: "bengal/core/page/page_core.py:25-35"
      type: "code"
      excerpt: "@dataclass(frozen=True)\nclass PageCore:"
    - source: "tests/unit/core/test_page_core.py:45"
      type: "test"
      excerpt: "def test_page_core_is_immutable():"
  criticality: HIGH  # API contract
  confidence: 95%
  reasoning: "Direct code evidence + test verification"
```

**Criticality levels**:
- **HIGH**: API contracts, core behavior, user-facing
- **MEDIUM**: Internal implementation, performance
- **LOW**: Code style, optional features

### Step 4: Cross-Validation (HIGH criticality)

For HIGH criticality, apply 3-path validation:

```yaml
path_a_source:
  location: "bengal/core/page/page_core.py:25"
  finding: "@dataclass(frozen=True)"

path_b_tests:
  location: "tests/unit/core/test_page_core.py:45"
  finding: "test_page_core_is_immutable"

path_c_config:
  location: "N/A - no config for this"

agreement: 2/3 → MODERATE confidence (test + code agree)
```

---

## Output Format

```markdown
## 📚 Research: [Topic]

### Executive Summary
[2-3 sentences: what was researched, key findings, confidence]

### Evidence Summary
- **Claims Extracted**: [N]
- **High Criticality**: [N]
- **Average Confidence**: [N]%

---

### 🔴 High Criticality Claims

#### Claim 1: [Description]
**Criticality**: HIGH
**Confidence**: 95% 🟢

**Evidence**:
- ✅ **Source**: `bengal/core/page/page_core.py:25-35`
  ```python
  @dataclass(frozen=True)
  class PageCore:
      """Immutable, cacheable page metadata."""
  ```
- ✅ **Test**: `tests/unit/core/test_page_core.py:45`
  - `test_page_core_is_immutable` - Verifies frozen behavior

**3-Path Validation**:
- Source: ✅ Verified
- Tests: ✅ Verified  
- Config: N/A

---

### 🟡 Medium Criticality Claims
[Similar format]

---

### 🟢 Low Criticality Claims
[Brief list format]

---

### 📋 Next Steps
- [ ] Use findings for RFC (`::rfc`)
- [ ] Identify gaps requiring SME input
- [ ] Update architecture docs if drift detected
```

---

## Bengal-Specific Sources

### Core Models
- `bengal/core/site.py` - Site container
- `bengal/core/page/__init__.py` - Page model
- `bengal/core/page/page_core.py` - PageCore contract
- `bengal/core/section.py` - Section model

### Orchestration
- `bengal/orchestration/build_orchestrator.py`
- `bengal/orchestration/render_orchestrator.py`
- `bengal/orchestration/incremental_builder.py`

### Rendering
- `bengal/rendering/template_engine/` - Jinja setup
- `bengal/rendering/markdown/` - Markdown parsing
- `bengal/directives/` - MyST directives

### Cache
- `bengal/cache/build_cache/` - Build cache
- `bengal/cache/indexes/` - Query indexes
- `bengal/cache/dependency_tracker.py`

### Tests
- `tests/unit/` - Fast, isolated tests
- `tests/integration/` - Full workflow tests
- `tests/roots/` - Test site fixtures

---

## Related

- `modules/evidence-handling` - Reference format
- `commands/rfc` - Use research for RFC
- `commands/validate` - Validation with confidence
