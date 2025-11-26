# Health Check System: Long-Term Strategic Plan

**Status**: Draft  
**Date**: 2025-01-XX  
**Goal**: Design a health check system that serves writers, theme developers, and full-stack developers with progressive disclosure, performance, and extensibility.

---

## Current State Analysis

### Strengths
- ✅ 15+ validators covering major build aspects (organized in 5 phases)
- ✅ Profile-based enable/disable (WRITER, THEME_DEV, DEVELOPER) with config overrides
- ✅ Progressive disclosure (problems first, passed collapsed) - recently implemented
- ✅ Clear error messages with actionable recommendations
- ✅ Integrated into build process (automatic validation after builds)
- ✅ File hash tracking infrastructure exists (`BuildCache.hash_file()` uses SHA256)
- ✅ Incremental build infrastructure exists (`IncrementalOrchestrator`, `BuildCache.is_changed()`)
- ✅ Dependency tracking exists (`DependencyTracker` tracks page→template dependencies)
- ✅ Dev server file watching (`BuildHandler` watches for changes, triggers incremental rebuilds)

### Gaps
- ❌ **No validation result caching**: Health checks re-validate everything on every build
- ❌ **No context-aware validation**: Can't validate single file (`bengal validate --file page.md`)
- ❌ **No standalone validate command**: Only `bengal health linkcheck` exists, no general `bengal validate`
- ❌ **No incremental validation**: Always validates entire site, even if only 1 file changed
- ❌ **No auto-fix capabilities**: Only reports problems, doesn't fix them
- ❌ **Performance overhead**: All enabled validators run sequentially, even for unchanged files
- ❌ **No IDE/editor integration**: Only CLI output, no LSP or editor plugins
- ❌ **Limited extensibility**: No plugin system for custom validators (must modify code)
- ❌ **No watch mode**: Can't run `bengal validate --watch` for continuous validation
- ❌ **No validation profiles**: Can't create custom profiles per project (only 3 built-in)

---

## User Persona Needs

### 1. Writers (Content Creators)
**Primary Goal**: Fast feedback on content errors

**Needs**:
- ✅ Markdown syntax errors (directives, links, formatting)
- ✅ Content quality (orphans, broken links, missing metadata)
- ✅ Fast feedback (< 2s for typical site)
- ✅ Clear, actionable error messages
- ✅ Focus on content, not technical details

**Don't Need**:
- ❌ Template rendering details
- ❌ Performance metrics
- ❌ Cache integrity
- ❌ Navigation structure analysis

**Current**: ✅ Well served by WRITER profile

---

### 2. Theme Developers
**Primary Goal**: Debug template and rendering issues

**Needs**:
- ✅ Template rendering errors (Jinja2, unrendered blocks)
- ✅ Navigation/menu structure issues
- ✅ Asset pipeline problems
- ✅ Rendering performance (slow pages)
- ✅ Template function validation
- ✅ HTML structure validation

**Don't Need**:
- ❌ Content quality checks (orphans, connectivity)
- ❌ RSS/sitemap validation (unless testing production)
- ❌ Cache integrity (unless debugging incremental builds)

**Current**: ⚠️ Partially served by THEME_DEV profile, but missing some checks

---

### 3. Developers (Full Stack)
**Primary Goal**: Complete observability and optimization

**Needs**:
- ✅ Everything (all validators)
- ✅ Performance profiling (build time, memory, throughput)
- ✅ Cache integrity and optimization
- ✅ Deep diagnostics (why is X slow?)
- ✅ Regression detection (build time trends)
- ✅ Production readiness (RSS, sitemap, SEO)

**Current**: ✅ Well served by DEVELOPER profile

---

## Strategic Vision: 3-Phase Evolution

### Phase 1: Incremental & Context-Aware Validation (3-6 months)
**Goal**: Leverage existing infrastructure to validate only what changed

**Foundation Already Exists**:
- ✅ `BuildCache.hash_file()` - SHA256 file hashing
- ✅ `BuildCache.is_changed()` - Change detection
- ✅ `DependencyTracker` - Tracks page→template dependencies
- ✅ `IncrementalOrchestrator` - Determines what needs rebuilding

**Features**:
1. **Validation Result Caching**
   - Store validation results per file in `BuildCache` (new field: `validation_results`)
   - Key: `(file_path, validator_name, file_hash)` → `CheckResult[]`
   - Only re-validate if file hash changed
   - **Implementation**: Extend `BuildCache` with validation cache, reuse existing hash infrastructure

2. **Incremental Validation**
   - `HealthCheck.run(incremental=True)` → Only validate changed files
   - Use `BuildCache.is_changed()` to determine what to validate
   - Use `DependencyTracker` to find dependent files (e.g., template changes affect pages)
   - **Implementation**: Add `incremental` parameter to `HealthCheck.run()`, integrate with `BuildCache`

3. **Context-Aware Checks**
   - `bengal validate` → New standalone command (full validation)
   - `bengal validate --file content/page.md` → Only check that file + dependencies
   - `bengal validate --changed` → Only check git-modified files (use `BuildCache.is_changed()`)
   - `bengal validate --watch` → Watch mode, validate on save (reuse `BuildHandler` infrastructure)
   - **Implementation**: New CLI command `bengal/cli/commands/validate.py`, reuse file watching from dev server

4. **Smart Integration**
   - Dev server: Only validate changed files on rebuild (use incremental=True)
   - Build: Full validation (current behavior, but cached)
   - Pre-commit: Only changed files + critical checks (new hook)

**Implementation Details**:
```python
# Extend BuildCache
@dataclass
class BuildCache:
    # ... existing fields ...
    validation_results: dict[str, dict[str, list[CheckResult]]] = field(default_factory=dict)
    # Key: file_path → validator_name → [CheckResult]

# New HealthCheck API
health_check.run(
    profile=BuildProfile.WRITER,
    incremental=True,  # Use BuildCache.is_changed()
    context=["content/page.md"],  # Specific files/paths
    cache_results=True,  # Store in BuildCache.validation_results
)

# New CLI command
@click.command("validate")
@click.option("--file", multiple=True, help="Validate specific files")
@click.option("--changed", is_flag=True, help="Only validate changed files")
@click.option("--watch", is_flag=True, help="Watch mode")
def validate_cmd(file, changed, watch):
    # Implementation
```

**Benefits**:
- Writers get instant feedback (< 500ms for single file)
- Theme devs can validate specific templates
- Developers can validate incrementally (10x faster)
- Reuses existing infrastructure (no new systems needed)

---

### Phase 2: Interactive Fixes & IDE Integration (12-18 months)
**Goal**: Not just report problems, help fix them

**Features**:
1. **Auto-Fix Suggestions**
   - `bengal fix directives` → Auto-fix common directive errors
   - `bengal fix links` → Suggest link fixes (with confirmation)
   - `bengal fix --all` → Batch fix safe issues

2. **IDE Integration**
   - LSP server for real-time validation
   - Inline error markers in editor
   - Quick-fix actions (VS Code, Cursor, etc.)
   - Hover tooltips with explanations

3. **Progressive Severity**
   - **Errors**: Block builds, must fix
   - **Warnings**: Don't block, but should fix
   - **Suggestions**: Quality improvements (collapsed by default)
   - **Info**: Contextual information (hidden unless verbose)

**Implementation**:
```python
# New CheckResult levels
CheckResult.error(...)      # Blocks build
CheckResult.warning(...)    # Shows in normal mode
CheckResult.suggestion(...)  # Hidden unless --suggestions
CheckResult.info(...)       # Hidden unless verbose

# Auto-fix API
fixer = AutoFixer(report)
fixes = fixer.suggest_fixes()  # Returns fix actions
fixer.apply_safe_fixes()       # Apply fixes that are safe
```

**Benefits**:
- Writers can fix issues without understanding technical details
- Theme devs get quick fixes for common template errors
- Developers can automate fixes in CI/CD

---

### Phase 3: Extensibility & Intelligence (18-24 months)
**Goal**: Platform for custom validation and intelligent insights

**Features**:
1. **Plugin System**
   - Custom validators via `bengal.toml` plugins
   - Community validators (SEO, accessibility, etc.)
   - Project-specific validators

2. **Intelligent Insights**
   - Pattern detection ("You have 20 orphan pages, consider adding navigation")
   - Performance optimization suggestions ("Page X is slow, consider splitting")
   - Content quality scoring ("Your content has good connectivity: 85%")

3. **Validation Profiles**
   - Custom profiles per project
   - Team-specific profiles (content team vs dev team)
   - CI/CD profiles (strict mode, fast mode)

**Implementation**:
```python
# Plugin API
@validator_plugin("seo")
class SEOValidator(BaseValidator):
    name = "SEO"
    ...

# Custom profiles
[health_check.profiles.content_team]
enabled = ["directives", "links", "content-quality"]
disabled = ["performance", "cache"]

[health_check.profiles.ci]
enabled = ["all"]
strict_mode = true  # Fail build on warnings
```

**Benefits**:
- Teams can customize validation for their needs
- Community can contribute validators
- Intelligent insights help improve site quality over time

---

## Implementation Roadmap

### Q1 2025: Foundation (Leverage Existing Infrastructure)
- [ ] **Validation result caching** (extend `BuildCache` with `validation_results` field)
- [ ] **Incremental validation** (use `BuildCache.is_changed()` in `HealthCheck.run()`)
- [ ] **Standalone validate command** (`bengal validate` CLI command)
- [ ] **Context-aware API** (`--file`, `--changed` options)
- [ ] **Performance optimization** (parallel validation where possible)
- [ ] **Dev server integration** (use incremental validation in dev server rebuilds)

### Q2 2025: User Experience
- [ ] Progressive severity (errors/warnings/suggestions/info)
- [ ] Better error messages (swarm feedback addressed)
- [ ] Auto-fix framework (safe fixes only)
- [ ] Watch mode (`bengal validate --watch`)

### Q3 2025: Integration
- [ ] LSP server for IDE integration
- [ ] Pre-commit hooks integration
- [ ] CI/CD profiles (strict mode)
- [ ] Validation report formats (JSON, HTML)

### Q4 2025: Extensibility
- [ ] Plugin system for custom validators
- [ ] Custom profiles per project
- [ ] Community validator registry
- [ ] Intelligent insights (pattern detection)

---

## Design Principles

### 1. Progressive Disclosure
- **Layer 1**: Critical errors (always visible)
- **Layer 2**: Warnings (visible in normal mode)
- **Layer 3**: Suggestions (collapsed, expandable)
- **Layer 4**: Info (hidden unless verbose)

### 2. Performance First
- Incremental validation by default
- Cache results aggressively
- Parallel validation where possible
- Skip expensive checks unless needed

### 3. Persona-Aware Defaults
- **Writers**: Fast, content-focused, actionable
- **Theme Devs**: Template-focused, rendering details
- **Developers**: Complete observability, deep diagnostics

### 4. Extensibility
- Plugin system for custom validators
- Config-driven profiles
- Community contributions welcome

### 5. Actionable Intelligence
- Not just "what's wrong" but "how to fix"
- Auto-fix where safe
- Pattern detection and suggestions
- Quality scoring and trends

---

## Success Metrics

### Performance
- ✅ Writers: < 500ms validation for typical site
- ✅ Theme devs: < 2s validation for template changes
- ✅ Developers: < 5s full validation for large sites

### User Experience
- ✅ 90% of errors have actionable fixes
- ✅ 50% of common errors auto-fixable
- ✅ IDE integration reduces context switching

### Quality
- ✅ Validation catches 95% of build issues
- ✅ False positive rate < 5%
- ✅ Coverage: All critical build aspects validated

---

## Open Questions

1. **Validation Timing**: When should validation run?
   - On every build? (current)
   - On file change? (watch mode)
   - Pre-commit only? (CI/CD)
   - On-demand? (`bengal validate`)

2. **Auto-Fix Safety**: How aggressive should auto-fix be?
   - Conservative: Only safe, reversible fixes
   - Moderate: Common fixes with confirmation
   - Aggressive: Fix everything possible (risky)

3. **IDE Integration**: Which editors to prioritize?
   - VS Code (most popular)
   - Cursor (AI-first)
   - Vim/Neovim (power users)
   - All via LSP?

4. **Validation Caching**: How long to cache results?
   - Forever (until file changes)
   - Time-based (5 minutes)
   - Build-based (until next build)

---

## Implementation Roadmap (Updated with Research)

### Immediate (This Week)
- [ ] **Research complete** ✅ - Documented current state
- [ ] Design validation result caching schema (extend `BuildCache`)
- [ ] Design incremental validation API (`HealthCheck.run(incremental=True)`)
- [ ] Design standalone validate command API

### Short-term (This Month)
- [ ] **Phase 1.1**: Extend `BuildCache` with `validation_results` field
  - Add `validation_results: dict[str, dict[str, list[CheckResult]]]` field
  - Implement serialization/deserialization (reuse existing JSON pattern)
  - Add helper methods: `get_cached_results()`, `cache_results()`, `invalidate_results()`

- [ ] **Phase 1.2**: Add incremental validation to `HealthCheck`
  - Add `incremental: bool` parameter to `run()`
  - Add `context: list[Path]` parameter for file-specific validation
  - Integrate with `BuildCache.is_changed()` to skip unchanged files
  - Use `DependencyTracker` to find dependent files

- [ ] **Phase 1.3**: Create standalone `bengal validate` command
  - New file: `bengal/cli/commands/validate.py`
  - Options: `--file`, `--changed`, `--watch`, `--profile`
  - Reuse `load_site_from_cli()` helper
  - Reuse `BuildHandler` for watch mode

### Medium-term (This Quarter)
- [ ] **Phase 1.4**: Integrate incremental validation into dev server
  - Modify `BuildHandler` to use incremental validation on rebuilds
  - Only validate changed files during dev server rebuilds

- [ ] **Phase 2.1**: Progressive severity system
  - Add `CheckResult.suggestion()` level (between warning and info)
  - Update report formatting to collapse suggestions by default
  - Add `--suggestions` flag to show quality improvements

- [ ] **Phase 2.2**: Auto-fix framework
  - Create `AutoFixer` class with `suggest_fixes()` and `apply_safe_fixes()`
  - Start with directive fixes (fence nesting, closing markers)
  - Add confirmation prompts for non-safe fixes

### Long-term (This Year)
- [ ] **Phase 2.3**: Watch mode for validation
  - Standalone `bengal validate --watch` command
  - Real-time validation feedback

- [ ] **Phase 3.1**: LSP server for IDE integration
  - Language Server Protocol implementation
  - Real-time validation in editor
  - Inline error markers and quick fixes

- [ ] **Phase 3.2**: Plugin system for custom validators
  - Validator plugin API
  - Config-driven validator registration
  - Community validator registry

- [ ] **Phase 3.3**: Intelligent insights
  - Pattern detection (orphan pages, connectivity issues)
  - Performance optimization suggestions
  - Content quality scoring

---

## References

- Current validators: `bengal/health/validators/`
- Profile system: `bengal/utils/profile.py`
- Health check orchestrator: `bengal/health/health_check.py`
- Report formatting: `bengal/health/report.py`
