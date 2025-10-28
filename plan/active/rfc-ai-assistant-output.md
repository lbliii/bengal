# RFC: AI-Assistant-Friendly Output Formats

**Status:** Draft  
**Created:** 2025-10-28  
**Author:** System  
**Confidence:** TBD (pending validation)

---

## Executive Summary

Add machine-readable output formats to Bengal CLI commands to make AI assistants (like Claude, GitHub Copilot, etc.) more effective when helping users work with Bengal projects. This builds on Bengal's existing "ai" profile and extends structured output (JSON/YAML) across all commands.

**Key Insight:** AI assistants already have access to the codebase and can run commands. By providing structured, context-rich output, we make them dramatically more effective without requiring API integrations or AI model dependencies.

---

## Problem Statement

### Current State

**Evidence from `bengal/cli/commands/project.py:41-49`:**
```python
"ai": {
    "name": "Automation / AI",
    "emoji": "🤖",
    "description": "Machine-readable output, JSON formats, no interactive prompts",
    "output_format": "json",
    "verbosity": "info",
    "show_all_commands": True,
    "default_build_profile": "dev",
}
```

Bengal already recognizes AI/automation as a user persona, but:

1. **Inconsistent structured output**: Only some commands support `--format json` (config, graph)
2. **Human-centric output**: Most commands output pretty tables/text for humans
3. **Missing context APIs**: No easy way for AI to get "what should I do next?" or "what conventions does this project use?"
4. **Limited introspection**: Hard to programmatically understand site structure, dependencies, health status

### User Pain Points

When an AI assistant (like Claude in Cursor) helps with Bengal:

1. **Context gathering is slow**: Must read multiple files to understand project state
2. **Output parsing is fragile**: Scraping pretty tables/colored text is error-prone
3. **No actionable suggestions**: AI must infer next steps rather than get structured recommendations
4. **Convention drift**: AI doesn't know project-specific conventions, generates code that doesn't match style

### Why This Matters

AI-assisted development is growing rapidly. SSGs that make AI assistants more effective will:
- **Improve developer experience** for users already using AI tools
- **Differentiate Bengal** as "AI-native" SSG
- **Enable new workflows** (AI-driven content generation, automated refactoring)
- **Future-proof** as AI capabilities improve

---

## Goals

### Primary Goals

1. **Extend structured output to all commands** using consistent `--format` flag
2. **Add AI-context commands** for introspection and guidance
3. **Make output rich and actionable** with suggestions, not just data dumps
4. **Maintain backward compatibility** with existing human-friendly output

### Non-Goals

1. ❌ Build AI models or agents into Bengal
2. ❌ Require external API calls (OpenAI, Anthropic, etc.)
3. ❌ Replace human-friendly output (both should coexist)
4. ❌ Create new config formats or breaking changes

---

## Design Options

### Option 1: Global `--format` Flag (Recommended)

Add `--format` to all commands via base `BengalCommand` class.

**Pros:**
- ✅ Consistent across all commands
- ✅ Single implementation point
- ✅ Easy to extend to new commands
- ✅ Backward compatible (defaults to 'human')

**Cons:**
- ⚠️ Must implement for each command type
- ⚠️ May not fit all command outputs

**Implementation:**
```python
# bengal/cli/base.py
class BengalCommand(click.Command):
    def __init__(self, *args, **kwargs):
        # Add --format option to all commands
        params = kwargs.get('params', [])
        params.append(
            click.Option(
                ['--format'],
                type=click.Choice(['human', 'json', 'yaml']),
                default='human',
                help='Output format (human, json, yaml)',
                envvar='BENGAL_OUTPUT_FORMAT'
            )
        )
        kwargs['params'] = params
        super().__init__(*args, **kwargs)
```

### Option 2: Separate AI Commands

Create dedicated commands like `bengal ai context`, `bengal ai inspect`.

**Pros:**
- ✅ Clear separation of concerns
- ✅ Can optimize for AI use case
- ✅ No changes to existing commands

**Cons:**
- ❌ Duplicates functionality
- ❌ Harder to maintain
- ❌ Not as discoverable

### Option 3: Hybrid Approach (Recommended)

Combine both: Add `--format` flag globally + new AI-specific commands.

**Rationale:**
- Existing commands get structured output for automation
- New commands provide AI-specific workflows (context, suggestions)
- Best of both worlds

---

## Recommended Design

### 1. Global `--format` Flag

**Evidence: Existing pattern in `bengal/cli/commands/config.py:60-64`:**
```python
@click.option(
    "--format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="Output format",
)
```

**Extend to all commands:**

```python
# All commands support:
bengal site build --format json
bengal health linkcheck --format json
bengal graph analyze --format json
bengal config show --format yaml
```

### 2. New AI Context Commands

Add `bengal context` command group for AI-specific workflows:

```bash
# Get project context
bengal context inspect [--format json]

# Get project conventions
bengal context conventions [--format yaml]

# Get suggested next steps
bengal context next [--format json]

# Explain dependency graph
bengal context explain FILE [--format json]

# Get current status
bengal context status [--format json]
```

### 3. Enhanced Output Schemas

#### `bengal context inspect --format json`

```json
{
  "project": {
    "root": "/Users/llane/Documents/github/python/bengal",
    "type": "bengal_site",
    "config_file": "bengal.toml"
  },
  "site_structure": {
    "content_dir": "content",
    "output_dir": "public",
    "theme": "default",
    "sections": ["blog", "docs", "about"]
  },
  "subsystems": {
    "core": {
      "files": ["bengal/core/site.py", "bengal/core/page/", "..."],
      "purpose": "Passive data models"
    },
    "orchestration": {
      "files": ["bengal/orchestration/build_orchestrator.py", "..."],
      "purpose": "Build coordination and operations"
    }
  },
  "git": {
    "branch": "enh/autodoc-url-grouping",
    "uncommitted_changes": 23,
    "untracked_files": ["plan/active/plan-autodoc-url-grouping.md"]
  },
  "health": {
    "linter_errors": 0,
    "test_status": "passed",
    "coverage": 94.2,
    "broken_links": 0
  },
  "recent_activity": {
    "modified_files": [
      {
        "path": "bengal/autodoc/generator.py",
        "modified": "2h ago",
        "subsystem": "autodoc"
      }
    ],
    "last_build": "2025-10-28T14:23:00Z",
    "last_test_run": "2025-10-28T14:20:00Z"
  }
}
```

#### `bengal context conventions --format yaml`

```yaml
# Auto-learned from codebase
file_naming:
  pattern: snake_case
  test_pattern: test_*.py
  examples:
    - build_orchestrator.py
    - test_build_orchestrator.py

commit_messages:
  format: "<subsystem>: <description>"
  subsystems:
    - core
    - orchestration
    - rendering
    - cache
    - cli
    - tests
    - docs
  examples:
    - "core: decouple theme chain/assets resolution from TemplateEngine"
    - "autodoc: add URL grouping for API reference pages"
    - "tests: add integration tests for incremental builds"

code_style:
  python_version: "3.14+"
  docstring_format: google
  type_hints: required
  line_length: 100
  imports_order:
    - stdlib
    - third_party
    - bengal
    - relative

testing:
  test_dirs:
    - tests/unit/
    - tests/integration/
  coverage_minimum: 90
  run_command: pytest
  patterns:
    - "Test functions start with test_"
    - "Use fixtures from tests/_testing/"

documentation:
  location: architecture/
  format: markdown
  update_when:
    - API changes
    - architectural changes
  cross_reference: true
```

#### `bengal context next --format json`

```json
{
  "context": {
    "branch": "enh/autodoc-url-grouping",
    "uncommitted_changes": true,
    "tests_passing": true,
    "linter_passing": true,
    "current_work": "Implementing autodoc URL grouping feature"
  },
  "suggestions": [
    {
      "priority": 1,
      "action": "Add tests for URL grouping logic",
      "reason": "New code in generator.py:145-167 has no test coverage",
      "commands": [
        "# Create test file",
        "# Add test cases for URL grouping"
      ],
      "files_to_modify": [
        "tests/unit/test_autodoc.py"
      ],
      "estimated_effort": "10-15 minutes",
      "confidence": 0.95
    },
    {
      "priority": 2,
      "action": "Update autodoc documentation",
      "reason": "New URL grouping feature not documented in README",
      "files_to_modify": [
        "bengal/autodoc/README.md"
      ],
      "estimated_effort": "5 minutes",
      "confidence": 0.90
    },
    {
      "priority": 3,
      "action": "Commit changes with atomic message",
      "reason": "Feature complete with tests and docs",
      "suggested_commit": "autodoc: add URL grouping for cleaner API reference organization",
      "blockers": [
        "Complete priority 1 and 2 first"
      ],
      "confidence": 0.85
    }
  ],
  "quality_gates": {
    "tests_passing": true,
    "linter_passing": true,
    "coverage_above_minimum": false,
    "documentation_updated": false,
    "ready_to_commit": false
  }
}
```

#### `bengal context explain FILE --format json`

```json
{
  "file": "bengal/core/site.py",
  "subsystem": "core",
  "purpose": "Central site orchestrator and container",
  "dependencies": {
    "imports": [
      {
        "module": "bengal.cache.build_cache",
        "usage": "Build state persistence"
      },
      {
        "module": "bengal.orchestration.render_orchestrator",
        "usage": "Page rendering coordination"
      }
    ],
    "imported_by": [
      {
        "file": "bengal/cli/commands/build.py",
        "usage": "CLI build command"
      },
      {
        "file": "tests/unit/test_site.py",
        "usage": "Unit tests"
      }
    ]
  },
  "impact_analysis": {
    "affects_if_changed": [
      "bengal/orchestration/*.py",
      "tests/unit/test_site.py",
      "tests/integration/test_build.py"
    ],
    "critical": true,
    "test_coverage": {
      "lines": 247,
      "covered": 234,
      "percentage": 94.7
    }
  },
  "recent_changes": [
    {
      "date": "2025-10-20",
      "commit": "a3f2b1c",
      "message": "core: add incremental build state tracking"
    }
  ]
}
```

#### `bengal context status --format json`

```json
{
  "git": {
    "branch": "enh/autodoc-url-grouping",
    "status": "ahead 3 commits",
    "uncommitted": {
      "modified": [
        {
          "file": "bengal/autodoc/generator.py",
          "lines_changed": 23,
          "subsystem": "autodoc",
          "summary": "Added URL grouping logic"
        }
      ],
      "untracked": [
        "plan/active/plan-autodoc-url-grouping.md"
      ]
    }
  },
  "build": {
    "last_run": "2025-10-28T14:23:00Z",
    "status": "success",
    "duration_ms": 1234,
    "pages_built": 47
  },
  "tests": {
    "last_run": "2025-10-28T14:20:00Z",
    "status": "passed",
    "total": 847,
    "passed": 847,
    "failed": 0,
    "coverage": 94.2
  },
  "health": {
    "linter_errors": 0,
    "broken_links": 0,
    "validation_warnings": 1
  },
  "recommendations": [
    {
      "type": "coverage",
      "message": "New code in generator.py:145-167 lacks test coverage",
      "action": "Add tests for URL grouping logic",
      "priority": "high"
    }
  ]
}
```

### 4. Enhanced Existing Command Output

#### `bengal site build --format json`

```json
{
  "status": "success",
  "timing": {
    "total_ms": 1234,
    "phases": {
      "discovery": 123,
      "rendering": 890,
      "postprocess": 221
    }
  },
  "output": {
    "pages_built": 47,
    "assets_processed": 23,
    "output_dir": "public",
    "size_bytes": 12458900
  },
  "cache": {
    "hits": 12,
    "misses": 35,
    "hit_rate": 0.26
  },
  "warnings": [],
  "errors": []
}
```

#### `bengal health linkcheck --format json`

**Evidence: Schema already defined in `plan/active/viability-analysis-link-checker-async.md:550-571`:**

```json
{
  "status": "passed|failed",
  "summary": {
    "checked": 123,
    "broken": 4,
    "ignored": 7,
    "duration_ms": 842
  },
  "results": [
    {
      "url": "https://example.com/a",
      "kind": "external",
      "status": 404,
      "reason": "Not Found",
      "first_ref": "/docs/page.md",
      "ref_count": 3,
      "ignored": false
    }
  ]
}
```

#### `bengal graph analyze --format json`

```json
{
  "stats": {
    "total_pages": 47,
    "total_links": 234,
    "avg_links_per_page": 4.98,
    "isolated_pages": 2,
    "max_depth": 4
  },
  "graph": {
    "nodes": [
      {
        "id": "/docs/intro/",
        "title": "Introduction",
        "section": "docs",
        "incoming_links": 12,
        "outgoing_links": 8,
        "pagerank": 0.042
      }
    ],
    "edges": [
      {
        "source": "/docs/intro/",
        "target": "/docs/quickstart/",
        "weight": 1
      }
    ]
  },
  "recommendations": [
    {
      "type": "orphaned_page",
      "page": "/old-post/",
      "suggestion": "No incoming links - consider linking from index or removing"
    }
  ]
}
```

---

## Architecture Impact

### Affected Subsystems

1. **CLI (`bengal/cli/`)** ⭐ PRIMARY
   - Extend `BengalCommand` base class
   - Add new `context` command group
   - Update all commands to support structured output

2. **Utils (`bengal/utils/`)** ⭐ MODERATE
   - Add `conventions_analyzer.py` to auto-learn project conventions
   - Add `context_provider.py` for project introspection
   - Extend `cli_output.py` to support JSON/YAML formatters

3. **Config (`bengal/config/`)** ⭐ LOW
   - No changes needed (already supports `--format`)

4. **Core (`bengal/core/`)** ⭐ NONE
   - No changes needed (passive data models)

### New Files

```
bengal/
├── cli/
│   └── commands/
│       └── context.py          # New: AI context commands
├── utils/
│   ├── conventions_analyzer.py # New: Auto-learn conventions
│   ├── context_provider.py     # New: Project introspection
│   └── output_formatter.py     # New: Structured output helper
└── config/
    └── ai_profile.py           # New: AI profile defaults
```

### Dependencies

**New dependencies:** None (use stdlib `json`, `yaml` via existing `pyyaml`)

**Evidence from `pyproject.toml`:**
- Already has `pyyaml>=6.0` (for YAML output)
- Already has `click>=8.0` (for CLI)
- Already has `rich>=13.0` (for human output)

### Backward Compatibility

✅ **Fully backward compatible:**
- Default `--format` is `human` (existing behavior)
- All existing commands work unchanged
- New commands are additive (opt-in)
- AI profile is optional

---

## Implementation Plan

### Phase 1: Foundation (1 week)

**Goal:** Establish patterns and infrastructure

1. **Extend `BengalCommand` base class** with `--format` flag
   - Update `bengal/cli/base.py`
   - Add `OutputFormatter` utility class
   - Test on 2-3 existing commands

2. **Create `bengal/utils/output_formatter.py`**
   ```python
   class OutputFormatter:
       """Format command output in human/json/yaml."""

       @staticmethod
       def format(data: dict, format: str = 'human') -> str:
           if format == 'json':
               return json.dumps(data, indent=2)
           elif format == 'yaml':
               return yaml.dump(data, default_flow_style=False)
           else:
               return format_human(data)  # Rich output
   ```

3. **Update 3 pilot commands** with structured output:
   - `bengal config show` (already has `--format`, extend)
   - `bengal site build` (add structured output)
   - `bengal health linkcheck` (use RFC schema)

**Deliverable:** Working `--format` flag on 3 commands

### Phase 2: Context Commands (1.5 weeks)

**Goal:** Add AI-specific introspection commands

1. **Create `bengal context inspect`**
   - Scan project structure
   - Git status integration
   - Health summary
   - Return JSON schema as designed

2. **Create `bengal context conventions`**
   - Auto-analyze commit messages (last 50 commits)
   - Detect file naming patterns
   - Parse `architecture/*.md` for conventions
   - Return YAML schema as designed

3. **Create `bengal context next`**
   - Detect uncommitted changes
   - Check test coverage gaps
   - Validate against quality gates
   - Return prioritized suggestions

4. **Create `bengal context explain FILE`**
   - Dependency analysis (imports, imported_by)
   - Impact analysis (what breaks if changed)
   - Test coverage for file
   - Recent change history

5. **Create `bengal context status`**
   - Combine git, build, test, health status
   - Return unified JSON view

**Deliverable:** Full `bengal context` command group

### Phase 3: Rollout (1.5 weeks)

**Goal:** Add structured output to all remaining commands

1. **Update all `bengal site` commands**
   - `site build` ✅ (done in Phase 1)
   - `site serve` (add structured output for server status)
   - `site clean` (add structured output for cleanup report)

2. **Update all `bengal health` commands**
   - `health linkcheck` ✅ (done in Phase 1)
   - `health report` (add structured output)
   - `health run` (add structured output)

3. **Update all `bengal graph` commands**
   - `graph analyze` (extend existing format)
   - `graph pagerank` (extend existing format)
   - `graph communities` (extend existing format)
   - `graph suggest` (extend existing format)

4. **Update all `bengal new` commands**
   - `new site` (add structured output for created files)
   - `new page` (add structured output)
   - `new layout` (add structured output)
   - `new partial` (add structured output)
   - `new theme` (add structured output)

5. **Update remaining commands**
   - `autodoc` (add structured output)
   - `perf` (add structured output)
   - `clean` (add structured output)

**Deliverable:** All commands support `--format json|yaml|human`

### Phase 4: Documentation & Polish (0.5 weeks)

**Goal:** Document and refine

1. **Add documentation**
   - `architecture/ai-output-formats.md`
   - Update `GETTING_STARTED.md` with AI profile
   - Add examples to `README.md`

2. **Add tests**
   - Unit tests for `OutputFormatter`
   - Integration tests for context commands
   - Test all commands with `--format json`

3. **Polish output schemas**
   - Validate JSON schemas
   - Ensure consistency across commands
   - Add helpful error messages

**Deliverable:** Production-ready feature

### Total Effort: ~4.5 weeks

---

## Alternatives Considered

### Alternative 1: Environment Variable Only

Use `BENGAL_OUTPUT_FORMAT=json` instead of `--format` flag.

**Rejected because:**
- Less discoverable
- Harder to override per-command
- Doesn't work well with AI assistants (they run one-off commands)

### Alternative 2: Separate `bengal-ai` Binary

Create a separate CLI binary for AI use cases.

**Rejected because:**
- Increases maintenance burden
- Duplicates functionality
- Not discoverable from main CLI
- Doesn't benefit human users who want automation

### Alternative 3: Plugin System

Make AI output a plugin that extends commands.

**Rejected because:**
- Over-engineered for this use case
- Adds complexity
- No clear benefit over built-in support

---

## Risks & Mitigations

### Risk 1: Schema Stability

**Risk:** AI assistants depend on stable JSON schemas. Breaking changes cause issues.

**Mitigation:**
- Version schemas in output: `{"schema_version": "1.0", ...}`
- Document schemas in `architecture/schemas/`
- Use semantic versioning for schema changes
- Maintain backward compatibility for 2 major versions

### Risk 2: Maintenance Burden

**Risk:** Every command needs JSON output maintained.

**Mitigation:**
- Use `OutputFormatter` utility for consistency
- Validate schemas in tests
- Document schema conventions in `architecture/`
- Make human output the source of truth (JSON is derived)

### Risk 3: Performance Overhead

**Risk:** Structured output generation slows down commands.

**Mitigation:**
- Only compute when `--format` is not 'human'
- Lazy evaluation where possible
- Benchmark critical commands (build, serve)
- Acceptable trade-off: AI workflows are less latency-sensitive

### Risk 4: Security/Privacy

**Risk:** Structured output might leak sensitive information.

**Mitigation:**
- Don't include file contents by default
- Redact sensitive paths (home directories)
- Add `--safe` flag to filter sensitive data
- Document what's included in each command's output

---

## Success Criteria

### Minimum Viable Product (MVP)

✅ **Phase 1 Complete:**
- 3 commands support `--format json|yaml|human`
- `OutputFormatter` utility working
- No regressions in existing output

✅ **Phase 2 Complete:**
- `bengal context` command group working
- All 5 subcommands return useful structured data
- AI assistants can use output effectively

### Full Success

✅ **All Phases Complete:**
- All 40+ commands support structured output
- Schemas documented and versioned
- Tests passing (95%+ coverage for new code)
- Documentation complete

### Adoption Metrics (3 months post-launch)

- 🎯 **10%+ users enable AI profile** (via `bengal project profile ai`)
- 🎯 **100+ GitHub stars** with "AI-friendly" mentioned in reviews
- 🎯 **3+ blog posts/videos** featuring AI-assisted Bengal workflows
- 🎯 **Zero breaking changes** to schemas (stability)

---

## Open Questions

1. **Q:** Should we include file contents in `bengal context explain`?
   **A:** No by default. Add `--include-content` flag if needed.

2. **Q:** How do we handle very large JSON outputs (100+ pages)?
   **A:** Add pagination via `--limit` and `--offset` flags.

3. **Q:** Should we support XML/CSV formats?
   **A:** Not initially. Can add later if demand exists.

4. **Q:** Should conventions auto-update based on new commits?
   **A:** Yes, but cache for 24h to avoid slowdowns.

5. **Q:** How do we test AI effectiveness?
   **A:** User studies + dogfooding (use Bengal OS with new formats).

---

## References

### Codebase Evidence

1. **Existing AI profile:** `bengal/cli/commands/project.py:41-49`
2. **Existing `--format` flag:** `bengal/cli/commands/config.py:60-64`
3. **Existing JSON generation:** `bengal/postprocess/output_formats.py`
4. **Link check JSON schema:** `plan/active/viability-analysis-link-checker-async.md:550-571`
5. **CLI base classes:** `bengal/cli/base.py:1-243`

### External References

- [Click Documentation: Options](https://click.palletsprojects.com/en/8.1.x/options/)
- [Rich JSON Export](https://rich.readthedocs.io/en/stable/console.html#export)
- [YAML Specification](https://yaml.org/spec/1.2.2/)

### Related Documents

- `architecture/cli.md` - CLI architecture overview
- `GETTING_STARTED.md:444-572` - Output formats documentation
- `plan/active/viability-analysis-link-checker-async.md` - Link check JSON schema

---

## Appendix: Example AI Assistant Workflow

**Scenario:** User asks AI to "add caching to taxonomy system"

**Without this RFC:**
```bash
# AI must:
1. Read multiple files manually to understand context
2. Parse human-friendly output (fragile)
3. Infer conventions from reading code
4. Guess at next steps
5. Generate code that may not match style
```

**With this RFC:**
```bash
# AI runs these commands behind the scenes:

# 1. Get project context
$ bengal context inspect --format json
# Returns: structure, subsystems, health, git status

# 2. Understand dependencies
$ bengal context explain bengal/cache/taxonomy_index.py --format json
# Returns: imports, imported_by, impact analysis, tests

# 3. Learn conventions
$ bengal context conventions --format yaml
# Returns: commit format, code style, testing patterns

# 4. Check current status
$ bengal context status --format json
# Returns: git status, build status, test status

# Now AI has everything needed to:
# - Make changes that fit project style
# - Update the right test files
# - Suggest the right commit message
# - Know what else needs updating
```

**Result:** AI generates perfect implementation on first try, no back-and-forth needed.

---

**Next Steps:**
1. Validate this RFC via `::validate`
2. Create implementation plan via `::plan`
3. Implement in phases
4. Dogfood with Bengal OS (meta!)

---

**Status:** Ready for review and validation
