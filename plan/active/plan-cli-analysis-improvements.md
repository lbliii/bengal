# Plan: CLI Analysis Improvements & Semantic Link Model

```yaml
RFC: plan/active/rfc-cli-analysis-improvements.md
Created: 2025-12-10
Status: Ready to Execute
Estimated Time: 9-12 days
Phases: 6
Tasks: 22
```

---

## Overview

Convert RFC into atomic implementation tasks. Each task includes:
- Clear deliverable
- Affected files
- Pre-drafted commit message
- Dependencies

---

## Phase 1: CLI Commands (1-2 days)

**Goal**: Immediate usability wins—promote `graph` to top-level, add convenience commands.

### Task 1.1: Promote `graph` to top-level CLI

**Description**: Add `graph_cli` as a top-level command in addition to `utils graph`.

**Files**:
- `bengal/cli/__init__.py`

**Changes**:
```python
# Add import
from bengal.cli.commands.graph import graph_cli

# Add after other top-level commands (~line 135)
main.add_command(graph_cli, name="graph")
```

**Commit**: `cli: promote graph to top-level; keep utils graph for backward compat`

**Verification**:
```bash
bengal graph --help  # Should show graph subcommands
bengal utils graph --help  # Should still work
```

---

### Task 1.2: Add `bengal analyze` alias

**Description**: Add `analyze` as top-level alias for `bengal graph report`.

**Files**:
- `bengal/cli/__init__.py`
- `bengal/cli/commands/graph/__main__.py` (if report doesn't exist)

**Changes**:
```python
# In __init__.py
from bengal.cli.commands.graph import report as analyze_cmd
main.add_command(analyze_cmd, name="analyze")
```

**Commit**: `cli: add 'bengal analyze' as alias for 'bengal graph report'`

**Depends on**: Task 1.3 (report command must exist)

---

### Task 1.3: Add unified `report` command

**Description**: Create `bengal graph report` that combines analyze, suggest, bridges, communities.

**Files**:
- `bengal/cli/commands/graph/report.py` (NEW)
- `bengal/cli/commands/graph/__main__.py` (register command)

**Key Features**:
- `--brief` flag for compact output
- `--format` (console, json, markdown)
- Combines all graph analysis into single output

**Commit**: `cli(graph): add unified 'report' command combining all analyses`

---

### Task 1.4: Add `orphans` subcommand

**Description**: Create `bengal graph orphans` for quick orphan listing.

**Files**:
- `bengal/cli/commands/graph/orphans.py` (NEW)
- `bengal/cli/commands/graph/__main__.py` (register command)

**Key Features**:
- `--format` (table, json, paths)
- `--limit` to cap results
- `--level` filter (isolated, lightly, adequately, well) [Phase 3]

**Commit**: `cli(graph): add 'orphans' subcommand for quick orphan listing`

---

## Phase 2: Semantic Link Model (2-3 days)

**Goal**: Eliminate false orphan reports by tracking structural relationships.

### Task 2.1: Add `LinkType` enum

**Description**: Define semantic link types with weights.

**Files**:
- `bengal/analysis/link_types.py` (NEW)

**Contents**:
```python
from enum import Enum

class LinkType(Enum):
    """Semantic relationship types between pages."""
    EXPLICIT = "explicit"       # Weight: 1.0
    MENU = "menu"               # Weight: 10.0
    TAXONOMY = "taxonomy"       # Weight: 1.0
    RELATED = "related"         # Weight: 0.75
    TOPICAL = "topical"         # Weight: 0.5 (NEW)
    SEQUENTIAL = "sequential"   # Weight: 0.25 (NEW)

DEFAULT_WEIGHTS = {
    LinkType.EXPLICIT: 1.0,
    LinkType.MENU: 10.0,
    LinkType.TAXONOMY: 1.0,
    LinkType.RELATED: 0.75,
    LinkType.TOPICAL: 0.5,
    LinkType.SEQUENTIAL: 0.25,
}
```

**Commit**: `analysis: add LinkType enum with semantic relationship types and weights`

---

### Task 2.2: Add `LinkMetrics` dataclass

**Description**: Track detailed link breakdown per page.

**Files**:
- `bengal/analysis/link_types.py` (extend)

**Contents**:
```python
@dataclass
class LinkMetrics:
    """Detailed link breakdown for a page."""
    explicit: int = 0
    menu: int = 0
    taxonomy: int = 0
    related: int = 0
    topical: int = 0
    sequential: int = 0
    
    def connectivity_score(self, weights: dict | None = None) -> float:
        """Weighted connectivity score."""
        w = weights or DEFAULT_WEIGHTS
        return (
            self.explicit * w[LinkType.EXPLICIT] +
            self.menu * w[LinkType.MENU] +
            self.taxonomy * w[LinkType.TAXONOMY] +
            self.related * w[LinkType.RELATED] +
            self.topical * w[LinkType.TOPICAL] +
            self.sequential * w[LinkType.SEQUENTIAL]
        )
```

**Commit**: `analysis: add LinkMetrics dataclass with connectivity scoring`

**Depends on**: Task 2.1

---

### Task 2.3: Implement `_analyze_section_hierarchy()`

**Description**: Track parent `_index.md` → child page relationships.

**Files**:
- `bengal/analysis/knowledge_graph.py`

**Changes**:
1. Add `link_types: dict[tuple[Page, Page], LinkType]` to class
2. Add `link_metrics: dict[Page, LinkMetrics]` to class
3. Implement `_analyze_section_hierarchy()` method
4. Call from `build()` method

**Commit**: `analysis(knowledge_graph): add section hierarchy analysis for topical links`

**Depends on**: Task 2.1, 2.2

---

### Task 2.4: Implement `_analyze_navigation_links()`

**Description**: Track next/prev sequential relationships.

**Files**:
- `bengal/analysis/knowledge_graph.py`

**Changes**:
1. Implement `_analyze_navigation_links()` method
2. Use `page.next_in_section` and `page.prev_in_section`
3. Call from `build()` method

**Commit**: `analysis(knowledge_graph): add sequential navigation link analysis`

**Depends on**: Task 2.3

---

### Task 2.5: Update `build()` to call new analysis methods

**Description**: Wire up new analysis methods in the build pipeline.

**Files**:
- `bengal/analysis/knowledge_graph.py`

**Changes**:
```python
def build(self) -> None:
    # ... existing code ...
    self._analyze_cross_references()
    self._analyze_taxonomies()
    self._analyze_related_posts()
    self._analyze_menus()
    self._analyze_section_hierarchy()  # NEW
    self._analyze_navigation_links()   # NEW
    # ... rest of build ...
```

**Commit**: `analysis(knowledge_graph): integrate semantic link analysis into build pipeline`

**Depends on**: Task 2.3, 2.4

---

### Task 2.6: Validate Phase 2 on Bengal site

**Description**: Run analysis on site/ to verify false positives are eliminated.

**Verification**:
```bash
cd site/
bengal graph analyze --verbose
# Expected: releases/*.md pages should NOT appear as orphans
```

**Commit**: N/A (validation only)

**Depends on**: Task 2.5

---

## Phase 3: Connectivity Levels (1-2 days)

**Goal**: Replace binary orphan/not with nuanced connectivity levels.

### Task 3.1: Add `ConnectivityLevel` enum

**Description**: Define threshold-based connectivity classification.

**Files**:
- `bengal/analysis/link_types.py` (extend)

**Contents**:
```python
class ConnectivityLevel(Enum):
    WELL_CONNECTED = "well_connected"     # Score >= 2.0
    ADEQUATELY_LINKED = "adequately"      # Score 1.0-2.0
    LIGHTLY_LINKED = "lightly"            # Score 0.25-1.0
    ISOLATED = "isolated"                 # Score < 0.25
    
    @classmethod
    def from_score(cls, score: float, thresholds: dict | None = None) -> "ConnectivityLevel":
        t = thresholds or DEFAULT_THRESHOLDS
        if score >= t["well_connected"]:
            return cls.WELL_CONNECTED
        elif score >= t["adequately_linked"]:
            return cls.ADEQUATELY_LINKED
        elif score >= t["lightly_linked"]:
            return cls.LIGHTLY_LINKED
        else:
            return cls.ISOLATED

DEFAULT_THRESHOLDS = {
    "well_connected": 2.0,
    "adequately_linked": 1.0,
    "lightly_linked": 0.25,
}
```

**Commit**: `analysis: add ConnectivityLevel enum with threshold-based classification`

**Depends on**: Task 2.2

---

### Task 3.2: Add `get_connectivity_report()` to KnowledgeGraph

**Description**: Return pages grouped by connectivity level.

**Files**:
- `bengal/analysis/knowledge_graph.py`

**Returns**:
```python
{
    "isolated": [Page, ...],
    "lightly_linked": [Page, ...],
    "adequately_linked": [Page, ...],
    "well_connected": [Page, ...],
    "distribution": {
        "isolated": 5,
        "lightly_linked": 10,
        "adequately_linked": 28,
        "well_connected": 81,
    }
}
```

**Commit**: `analysis(knowledge_graph): add get_connectivity_report() with level grouping`

**Depends on**: Task 3.1

---

### Task 3.3: Update CLI output to show connectivity distribution

**Description**: Enhance `graph analyze` and `graph report` to show distribution.

**Files**:
- `bengal/cli/commands/graph/analyze.py`
- `bengal/cli/commands/graph/report.py`

**Output**:
```
📊 Connectivity Analysis: 124 pages

Distribution:
  🟢 Well-Connected (≥2.0):    81 pages (65%)
  🟡 Adequately Linked (1-2):  28 pages (23%)
  🟠 Lightly Linked (0.25-1):  10 pages (8%)
  🔴 Isolated (<0.25):          5 pages (4%)
```

**Commit**: `cli(graph): update analyze/report output with connectivity distribution`

**Depends on**: Task 3.2

---

### Task 3.4: Add `--level` filter to orphans command

**Description**: Allow filtering by connectivity level.

**Files**:
- `bengal/cli/commands/graph/orphans.py`

**Usage**:
```bash
bengal graph orphans --level isolated     # Only truly isolated
bengal graph orphans --level lightly      # Lightly linked
bengal graph orphans                      # All (default: isolated + lightly)
```

**Commit**: `cli(graph): add --level filter to orphans command`

**Depends on**: Task 3.2

---

## Phase 4: CI Integration (1 day)

**Goal**: Enable CI pipelines to fail builds on connectivity thresholds.

### Task 4.1: Add `--ci` and `--threshold-*` flags to report

**Description**: Support CI mode with configurable thresholds.

**Files**:
- `bengal/cli/commands/graph/report.py`

**Flags**:
```python
@click.option("--ci", is_flag=True, help="Exit 1 if thresholds exceeded")
@click.option("--threshold-isolated", type=int, default=5, help="Max isolated pages")
@click.option("--threshold-lightly", type=int, default=20, help="Max lightly linked pages")
```

**Commit**: `cli(graph): add --ci mode with threshold flags for CI pipelines`

---

### Task 4.2: Add exit code logic

**Description**: Return non-zero exit code when thresholds exceeded.

**Files**:
- `bengal/cli/commands/graph/report.py`

**Logic**:
```python
if ci_mode:
    if len(isolated) > threshold_isolated:
        click.echo(f"❌ CI FAILED: {len(isolated)} isolated pages > {threshold_isolated}")
        sys.exit(1)
```

**Commit**: `cli(graph): implement exit code logic for CI threshold violations`

**Depends on**: Task 4.1

---

## Phase 5: Health Integration (1 day)

**Goal**: Enhance existing ConnectivityValidator with semantic awareness.

### Task 5.1: Enhance ConnectivityValidator with connectivity levels

**Description**: Modify existing validator to use connectivity levels instead of binary.

**Files**:
- `bengal/health/validators/connectivity.py`

**Changes**:
1. Import `ConnectivityLevel`, `LinkMetrics` from `bengal.analysis.link_types`
2. Use `graph.get_connectivity_report()` instead of `graph.get_orphans()`
3. Report isolated vs lightly linked separately
4. Add `lightly_linked_threshold` config option

**Commit**: `health(connectivity): enhance validator with semantic link awareness and connectivity levels`

**Depends on**: Task 3.2

---

### Task 5.2: Add configuration schema for weights and thresholds

**Description**: Allow per-site configuration of link weights and thresholds.

**Files**:
- `bengal/config/schema.py` (or equivalent)
- Documentation

**Config Schema**:
```toml
[analysis.link_weights]
explicit = 1.0
menu = 10.0
taxonomy = 1.0
related = 0.75
topical = 0.5
sequential = 0.25

[analysis.connectivity_thresholds]
well_connected = 2.0
adequately_linked = 1.0
lightly_linked = 0.25

[health.connectivity]
orphan_threshold = 5
lightly_linked_threshold = 20
```

**Commit**: `config: add schema for link weights and connectivity thresholds`

---

## Phase 6: Documentation (1 day)

**Goal**: Update docs to reflect new commands and features.

### Task 6.1: Update CLI reference docs

**Description**: Document new commands in site/content/docs/reference.

**Files**:
- `site/content/docs/reference/architecture/tooling/cli.md`

**Sections to add**:
- `bengal graph` commands
- `bengal analyze` command
- CI integration with thresholds

**Commit**: `docs(cli): document graph commands and analyze alias`

---

### Task 6.2: Add "Site Analysis" how-to guide

**Description**: Create how-to guide for analyzing site structure.

**Files**:
- `site/content/docs/how-to/analyze-site-structure.md` (NEW)

**Contents**:
- How to run analysis
- Understanding connectivity levels
- Fixing orphaned pages
- CI integration

**Commit**: `docs: add how-to guide for site structure analysis`

---

### Task 6.3: Document semantic link model

**Description**: Document link types, weights, and scoring.

**Files**:
- `site/content/docs/reference/semantic-links.md` (NEW)

**Contents**:
- Link types and their meaning
- Weight rationale
- Connectivity levels
- Configuration options

**Commit**: `docs: document semantic link model and connectivity scoring`

---

## Task Dependencies Graph

```
Phase 1 (CLI)
├── 1.1 Promote graph ─────────────────────────────────┐
├── 1.3 Add report command ───────────────────────────┼─→ 1.2 Add analyze alias
└── 1.4 Add orphans command ──────────────────────────┘

Phase 2 (Semantic Links)
├── 2.1 LinkType enum ───────┐
├── 2.2 LinkMetrics ─────────┼──→ 2.3 Section hierarchy ──┐
│                            │                             ├──→ 2.5 Wire up build() → 2.6 Validate
│                            └──→ 2.4 Navigation links ───┘

Phase 3 (Connectivity Levels)
├── 3.1 ConnectivityLevel ───→ 3.2 get_connectivity_report() ──┬──→ 3.3 Update CLI output
│                                                               └──→ 3.4 Add --level filter

Phase 4 (CI)
├── 4.1 Add --ci flags ───→ 4.2 Exit code logic

Phase 5 (Health)
├── 3.2 ───→ 5.1 Enhance ConnectivityValidator
└── 5.2 Add config schema (parallel)

Phase 6 (Docs)
├── 6.1 CLI reference
├── 6.2 How-to guide
└── 6.3 Semantic link docs
```

---

## Execution Checklist

### Phase 1: CLI Commands
- [ ] 1.1: Promote graph to top-level
- [ ] 1.3: Add report command
- [ ] 1.4: Add orphans command
- [ ] 1.2: Add analyze alias (after 1.3)

### Phase 2: Semantic Link Model
- [ ] 2.1: Add LinkType enum
- [ ] 2.2: Add LinkMetrics dataclass
- [ ] 2.3: Implement _analyze_section_hierarchy()
- [ ] 2.4: Implement _analyze_navigation_links()
- [ ] 2.5: Update build() to call new methods
- [ ] 2.6: Validate on Bengal site

### Phase 3: Connectivity Levels
- [ ] 3.1: Add ConnectivityLevel enum
- [ ] 3.2: Add get_connectivity_report()
- [ ] 3.3: Update CLI output
- [ ] 3.4: Add --level filter

### Phase 4: CI Integration
- [ ] 4.1: Add --ci and threshold flags
- [ ] 4.2: Add exit code logic

### Phase 5: Health Integration
- [ ] 5.1: Enhance ConnectivityValidator
- [ ] 5.2: Add config schema

### Phase 6: Documentation
- [ ] 6.1: Update CLI reference
- [ ] 6.2: Add how-to guide
- [ ] 6.3: Document semantic links

---

## Validation Criteria

After implementation, verify:

1. **CLI Discoverability**
   ```bash
   bengal graph --help  # Works
   bengal analyze --help  # Works
   bengal graph orphans  # Works
   ```

2. **False Positives Eliminated**
   ```bash
   cd site/
   bengal graph analyze
   # releases/*.md should NOT appear as orphans
   ```

3. **Connectivity Levels**
   ```bash
   bengal graph report --brief
   # Shows distribution: 🟢 🟡 🟠 🔴
   ```

4. **CI Integration**
   ```bash
   bengal graph report --ci --threshold-isolated 5
   # Exit 0 if ≤5 isolated, exit 1 if >5
   ```

5. **Health Validator**
   ```bash
   bengal check
   # Shows connectivity levels, not just binary orphan count
   ```

---

## Commit Message Templates

```bash
# Phase 1
git commit -m "cli: promote graph to top-level; keep utils graph for backward compat"
git commit -m "cli(graph): add unified 'report' command combining all analyses"
git commit -m "cli(graph): add 'orphans' subcommand for quick orphan listing"
git commit -m "cli: add 'bengal analyze' as alias for 'bengal graph report'"

# Phase 2
git commit -m "analysis: add LinkType enum with semantic relationship types and weights"
git commit -m "analysis: add LinkMetrics dataclass with connectivity scoring"
git commit -m "analysis(knowledge_graph): add section hierarchy analysis for topical links"
git commit -m "analysis(knowledge_graph): add sequential navigation link analysis"
git commit -m "analysis(knowledge_graph): integrate semantic link analysis into build pipeline"

# Phase 3
git commit -m "analysis: add ConnectivityLevel enum with threshold-based classification"
git commit -m "analysis(knowledge_graph): add get_connectivity_report() with level grouping"
git commit -m "cli(graph): update analyze/report output with connectivity distribution"
git commit -m "cli(graph): add --level filter to orphans command"

# Phase 4
git commit -m "cli(graph): add --ci mode with threshold flags for CI pipelines"
git commit -m "cli(graph): implement exit code logic for CI threshold violations"

# Phase 5
git commit -m "health(connectivity): enhance validator with semantic link awareness and connectivity levels"
git commit -m "config: add schema for link weights and connectivity thresholds"

# Phase 6
git commit -m "docs(cli): document graph commands and analyze alias"
git commit -m "docs: add how-to guide for site structure analysis"
git commit -m "docs: document semantic link model and connectivity scoring"
```

