---
description: Deep context analysis of code, tests, git history, and architecture before rule execution
globs: ["bengal/**/*.py", "tests/**/*.py", "architecture/**/*.md"]
alwaysApply: false
---

# Bengal Context Analyzer

**Purpose**: Deep context understanding before rule execution.

**Shortcut**: `::analyze`

---

## Overview

Analyzes code, tests, git, and architecture context to provide comprehensive understanding of the current state. Used automatically by the orchestrator and can be invoked explicitly.

---

## Analysis Dimensions

### 1. Code Context

- **Changed Files**: Git status/diff, uncommitted changes
- **Imports**: What modules import the changed code
- **Dependents**: What code depends on changed modules
- **Module Type**: Core / Orchestration / Rendering / Cache / Health / CLI
- **Complexity**: Lines changed, cyclomatic complexity

### 2. Test Context

- **Existing Tests**: Related test files in `tests/unit/`, `tests/integration/`
- **Coverage**: Current test coverage for changed modules
- **Recent Test Runs**: Pass/fail status, recent failures
- **Missing Tests**: Areas without coverage

### 3. Git Context

- **Branch**: Current branch name and type (feature/fix/refactor)
- **Recent Commits**: Last 5 commits in this area
- **Uncommitted Changes**: Staged vs unstaged
- **Merge Base**: Commits since divergence from main

### 4. Architecture Context

- **Subsystems Affected**: Which Bengal components touched
  - Core (Site, Page, Section, Asset, Theme)
  - Orchestration (render, build, incremental)
  - Rendering (Jinja, Markdown, shortcodes, filters)
  - Cache (discovery, dependency, indexes, query)
  - Health (validators, checks, reporting)
  - CLI (commands, helpers, templates)
- **Integration Points**: How subsystems interact
- **Performance Considerations**: Cache invalidation, incremental builds

### 5. Document Context (if applicable)

- **Open Files**: Currently open/visible in IDE
- **File Type**: Python module, test, config, docs
- **File Age**: Last modified date
- **File Size**: Lines of code, complexity

---

## Procedure

### Step 1: Gather Data

- Run `git status`, `git diff`, `git log`
- Scan imports with `grep -r "from bengal.X import"` or `grep -r "import bengal.X"`
- Check test files: `tests/unit/test_{module}.py`, `tests/integration/test_{feature}.py`
- Read `architecture/{subsystem}.md` for context

### Step 2: Analyze Patterns

- Identify primary subsystem(s)
- Detect cross-cutting concerns (cache invalidation, error handling)
- Flag high-risk areas (core.site, orchestration pipeline)

### Step 3: Assess Complexity

- **Simple**: Single module, < 50 lines, isolated
- **Moderate**: Multiple files, < 200 lines, some dependencies
- **Complex**: Cross-subsystem, > 200 lines, many dependents

---

## Output Format

```markdown
## 🔍 Context Analysis

### Summary
[2-3 sentence overview of context]

### Code Context
- **Changed Files**: [list with line counts]
- **Primary Subsystem**: [Core/Orchestration/Rendering/Cache/Health/CLI]
- **Imports**: [N] modules import this code
- **Dependents**: [list of dependent modules]

### Test Context
- **Existing Tests**: [list of test files]
- **Coverage**: [percentage or "unknown"]
- **Gaps**: [areas without tests]

### Git Context
- **Branch**: `[branch name]` (type: [feature/fix/refactor])
- **Recent Commits**: [last 3-5 relevant commits]
- **Uncommitted**: [N] staged, [N] unstaged files

### Architecture Context
- **Subsystems**: [list with brief descriptions]
- **Integration Points**: [how they connect]
- **Performance Notes**: [cache implications, build impact]

### Complexity Assessment
**Level**: [Simple/Moderate/Complex]
**Reasoning**: [why this complexity level]

### 💡 Recommendations
- [Recommendation 1 based on context]
- [Recommendation 2]
```

---

## Integration with Orchestrator

Context Analyzer runs **automatically** before routing in Orchestrator when:
- User query is complex or ambiguous
- Multiple subsystems potentially affected
- Git status shows many changes

Can also be invoked explicitly via `::analyze`.

---

## Prompting Techniques

- **ReAct**: Reason → search → read → analyze cycle
- **RAG**: Pull from `architecture/` docs and git history
