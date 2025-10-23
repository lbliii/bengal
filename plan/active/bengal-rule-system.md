# Bengal Rule System – Planning (v2 Enhanced)

## Goals

- Define an AI-assisted rule framework specialized for Bengal's workflows: research → RFC → plan → implementation → validation.
- Integrate advanced prompting techniques from `Prompting Techniques` (zero-shot, example-guided prompting, Chain-of-Thought, Self-Consistency, ReAct, self-critique, RAG) to improve reliability and speed.
- Align with Bengal architecture (Site, Orchestrators, Rendering, Cache, Health) and CLI.
- Match sophistication of `example-framework/` with context analysis, reflexion loops, workflow chains, and natural language support.

## Constraints & Considerations

- Must not invent facts—verify against code/tests (`bengal/` and `tests/`).
- Produce scannable outputs using the communication style framework and NVIDIA style guide.
- Save artifacts to `plan/` and use atomic commits.
- Support both shortcuts (::b-*) and natural language queries.

## Outputs

- `rules/bengal/index.md` with:
  - Bengal Orchestrator (auto-routing for tasks with NL support)
  - **Context Analyzer** (deep context understanding)
  - Research & Evidence Extraction rule (code-first claims)
  - RFC Drafting rule (evidence-backed structure)
  - Planning & Breakdown rule (tasks → to-dos → owners)
  - Implementation Driver rule (guided code edits, tests, lints)
  - Validation & Confidence rule (self-consistency scoring with formula)
  - Retrospective & Changelog rule
  - **Reflexion Loop** (iterative improvement)
  - **Help System** (context-aware assistance)
  - **Workflow Templates** (pre-built chains)
  - **Confidence Scoring** (explicit algorithm)
  - **Communication Style** (Bengal-adapted output format)
- Shortcut commands: `::b-auto`, `::b-research`, `::b-rfc`, `::b-plan`, `::b-impl`, `::b-validate`, `::b-retro`, `::b-improve`, `::b?`, `::bh`
- Workflow shortcuts: `::b-feature`, `::b-fix`, `::b-ship`, `::b-full`

## Prompting Techniques Mapping

- Zero-shot and example-guided prompting: template-based RFC and plan skeletons with minimal examples.
- Chain-of-Thought: explicit reasoning steps in audits and design tradeoffs.
- Self-Consistency: 3-path validation for critical claims (code, tests, configuration).
- ReAct: interleave reasoning with tool use (search, read, grep) during research and implementation.
- RAG: fetch architecture docs and source references.
- Self-critique: post-pass analysis to raise confidence.

## Bengal-Specific Integration Points

- Evidence sources: `bengal/core/site.py`, orchestrators, rendering pipeline, health validation modules, CLI commands under `bengal/cli/`.
- Performance/Cache: ensure plans consider incremental builds and indexes.
- Themes/Templates: verify changes across `themes/` when relevant.

## Quality Gates

- Confidence ≥ 85% for RFCs and plans; ≥ 90% for implementation changes to core.
- All critical claims validated by self-consistency (3-path verification).
- Confidence scoring formula: Evidence (40) + Consistency (30) + Recency (15) + Tests (15) = 0-100%

## Enhanced Features (from example-framework/)

### 1. Context Analyzer
- Code context: changed files, imports, dependents
- Test context: coverage, related test files
- Git context: recent commits, branch history
- Architecture context: which subsystems affected

### 2. Natural Language Routing
- Research triggers: `investigate`, `explore`, `how does`, `understand`
- RFC triggers: `should we`, `design`, `architecture`, `options`
- Plan triggers: `break down`, `tasks`, `steps`, `checklist`
- Implement triggers: `add`, `fix`, `implement`, `change`, `build`
- Validate triggers: `verify`, `check`, `test`, `validate`, `confidence`

### 3. Workflow Chains
- `::b-feature`: research → RFC → plan (full design)
- `::b-fix`: research → plan → implement (quick fix)
- `::b-ship`: validate → retro → changelog (pre-release)
- `::b-full`: complete cycle

### 4. Reflexion Loop
- Validation → identify gaps → regenerate → revalidate
- Self-improvement iteration for low-confidence outputs

### 5. Help System
- `::b?`: context-aware suggestions ("what should I do here?")
- `::bh`: full command reference

## Next Steps

1. ✅ Update `plan/active/bengal-rule-system.md` with v2 enhancements
2. Create comprehensive `rules/bengal/index.md` as markdown (convert to .mdc manually)
3. Wire outputs to planning/implementation artifacts in `plan/` and `CHANGELOG.md`
4. Test with first use case (e.g., cache optimization RFC)
5. Iterate to refine thresholds, templates, and confidence scoring
