Title: Implementation Plan — Config System v2
Status: Active
RFC: rfc-config-ergonomics-v2-clean.md
Owner: Bengal Core
Created: 2025-10-25
Target: 4-5 weeks

## Overview

Implement directory-based, environment-aware, profile-native config system.

**Goal**: Best-in-class config DX that beats Sphinx, MkDocs, and Hugo.

## Timeline

- **Week 1**: Core loader + merge engine (Foundation)
- **Week 2**: Introspection commands (show/doctor/diff/init)
- **Week 3**: Integration with Site/CLI (Wire it up)
- **Week 4**: Examples + docs (Polish)
- **Week 5**: Testing + performance (Ship)

---

## Week 1: Core Loader (Foundation)

### 1.1 Create Config Module Structure

**Files to create**:
```
bengal/config/
├── __init__.py
├── loader.py              # ConfigLoader (keep for single-file)
├── directory_loader.py    # NEW: ConfigDirectoryLoader
├── merge.py               # NEW: Deep merge logic
├── feature_mappings.py    # NEW: Feature → detailed config
├── environment.py         # NEW: Environment detection
├── validators.py          # Keep, enhance
└── origin_tracker.py      # NEW: Origin tracking for introspection
```

**Tasks**:
- [ ] 1.1.1 Create `bengal/config/directory_loader.py`
  - ConfigDirectoryLoader class
  - `load()` method with precedence (defaults → env → profile)
  - `_load_directory()` for multi-file YAML
  - `_load_yaml()` with error handling

- [ ] 1.1.2 Create `bengal/config/merge.py`
  - `deep_merge(base, override)` function
  - Handle dicts, lists, primitives
  - Test with nested structures

- [ ] 1.1.3 Create `bengal/config/feature_mappings.py`
  - `FEATURE_MAPPINGS` dict
  - Map: rss, sitemap, search, json, llm_txt, validate_links, minify_html, minify_assets
  - `expand_features(config)` function
  - `set_if_missing(config, key_path, value)` helper

- [ ] 1.1.4 Create `bengal/config/environment.py`
  - `detect_environment()` function
  - Check: BENGAL_ENV, NETLIFY, VERCEL, GITHUB_ACTIONS
  - Return: local, preview, production

- [ ] 1.1.5 Create `bengal/config/origin_tracker.py`
  - `ConfigWithOrigin` class
  - Track which file contributed each key
  - `merge(other, origin)` method
  - `show_with_origin()` formatter

**Tests**:
- [ ] 1.1.6 `tests/unit/config/test_directory_loader.py`
  - Test loading from config/_default/
  - Test environment overrides
  - Test profile overrides
  - Test precedence order (default < env < profile)

- [ ] 1.1.7 `tests/unit/config/test_merge.py`
  - Test deep merge with nested dicts
  - Test list handling (replace vs extend)
  - Test primitive overrides

- [ ] 1.1.8 `tests/unit/config/test_feature_mappings.py`
  - Test each feature expansion
  - Test combination of features
  - Test detailed config overrides expanded features

- [ ] 1.1.9 `tests/unit/config/test_environment.py`
  - Test BENGAL_ENV explicit
  - Test Netlify detection (production vs preview)
  - Test Vercel detection
  - Test GitHub Actions detection
  - Test default to "local"

- [ ] 1.1.10 `tests/unit/config/test_origin_tracker.py`
  - Test origin tracking through merges
  - Test format output with origins

**Acceptance Criteria**:
- ✅ ConfigDirectoryLoader can load multi-file configs
- ✅ Merge precedence works: defaults < env < profile
- ✅ All 8 feature mappings expand correctly
- ✅ Environment auto-detection works for all platforms
- ✅ Origin tracking accurate through merge chain
- ✅ Test coverage ≥ 90%

---

## Week 2: Introspection Commands

### 2.1 Config Show Command

**Files to create/modify**:
```
bengal/cli/commands/config.py  # NEW command group
```

**Tasks**:
- [ ] 2.1.1 Create `bengal/cli/commands/config.py`
  - Click group: `@click.group("config")`
  - Subcommand: `show`
  - Options: `--environment`, `--profile`, `--origin`, `--section`

- [ ] 2.1.2 Implement `config show`
  - Load config with specified env/profile
  - Pretty-print with Rich (if available)
  - Show origin annotations if `--origin` flag
  - Filter to section if `--section` flag

- [ ] 2.1.3 Format output beautifully
  - Use Rich syntax highlighting for YAML
  - Origin as comments: `# _default/site.yaml`
  - Color-code by source (default=white, env=blue, profile=green)

**Tests**:
- [ ] 2.1.4 `tests/unit/cli/commands/test_config_show.py`
  - Test show without flags (merged config)
  - Test show with --origin (annotations)
  - Test show with --section (filtered)
  - Test show with --environment
  - Test show with --profile

---

### 2.2 Config Doctor Command

**Tasks**:
- [ ] 2.2.1 Implement `config doctor` in `config.py`
  - YAML syntax validation
  - Type checking (use existing validator)
  - Typo detection with suggestions (use difflib)
  - Required fields check (title, baseurl for production)
  - Value range validation (max_workers ≥ 0)

- [ ] 2.2.2 Add unknown key detection
  - Define KNOWN_KEYS per section
  - Suggest corrections for typos (< 3 char diff)
  - Warn about unused files in config/

- [ ] 2.2.3 Format doctor output
  - ✅ Success: green
  - ⚠️  Warning: yellow
  - ❌ Error: red
  - Summary line: "2 errors, 1 warning"

**Tests**:
- [ ] 2.2.4 `tests/unit/cli/commands/test_config_doctor.py`
  - Test valid config (all green)
  - Test YAML syntax errors
  - Test type mismatches
  - Test typo detection
  - Test required field missing
  - Test value range violations

---

### 2.3 Config Diff Command

**Tasks**:
- [ ] 2.3.1 Implement `config diff` in `config.py`
  - Options: `--environment`, `--profile`, `--against`
  - Load two configs (current vs target)
  - Deep diff algorithm

- [ ] 2.3.2 Format diff output
  - Use `+`/`-` prefixes like git diff
  - Color: red for removed, green for added
  - Show nested path: `site.baseurl`
  - Annotate with source: `[local] → [production]`

**Tests**:
- [ ] 2.3.3 `tests/unit/cli/commands/test_config_diff.py`
  - Test diff between environments
  - Test diff between profiles
  - Test diff against defaults
  - Test no changes (identical configs)

---

### 2.4 Config Init Command

**Tasks**:
- [ ] 2.4.1 Implement `config init` in `config.py`
  - Option: `--type` (directory, file)
  - Option: `--template` (docs, blog, minimal)

- [ ] 2.4.2 Create directory scaffold
  - Create `config/_default/` structure
  - Create `config/environments/` (local, production)
  - Create `config/profiles/` (writer, dev)
  - Populate with template content

- [ ] 2.4.3 Create file scaffold
  - Generate single `bengal.yaml`
  - Populate with template content

- [ ] 2.4.4 Add templates
  - `templates/config/docs.yaml` (docs site)
  - `templates/config/blog.yaml` (blog site)
  - `templates/config/minimal.yaml` (bare minimum)

**Tests**:
- [ ] 2.4.5 `tests/unit/cli/commands/test_config_init.py`
  - Test directory scaffold creation
  - Test file scaffold creation
  - Test template application
  - Test overwrite protection (don't clobber existing)

**Acceptance Criteria**:
- ✅ `bengal config show` displays merged config beautifully
- ✅ `bengal config show --origin` shows file sources
- ✅ `bengal config doctor` catches 95%+ common errors
- ✅ `bengal config diff` shows clear differences
- ✅ `bengal config init` scaffolds structure in < 1 second
- ✅ All commands have help text and examples

---

## Week 3: Integration with Site/CLI

### 3.1 Update Site.from_config()

**Files to modify**:
```
bengal/core/site.py
```

**Tasks**:
- [ ] 3.1.1 Update `Site.from_config()` class method
  - Detect config source (directory vs file)
  - If `config/` exists, use ConfigDirectoryLoader
  - Pass environment and profile to loader
  - Fallback to old loader for single files

- [ ] 3.1.2 Add environment/profile parameters
  - `Site.from_config(root_path, config_path=None, environment=None, profile=None)`
  - Default environment: auto-detect
  - Default profile: None (or from config if specified)

**Tests**:
- [ ] 3.1.3 `tests/unit/core/test_site_config_loading.py`
  - Test loading from config/ directory
  - Test loading from bengal.yaml
  - Test loading from bengal.toml (legacy)
  - Test environment parameter
  - Test profile parameter
  - Test auto-detection

---

### 3.2 Update Build Command

**Files to modify**:
```
bengal/cli/commands/build.py
```

**Tasks**:
- [ ] 3.2.1 Add `--environment` flag
  - Type: Choice[local, preview, production] or string
  - Help: "Environment to build for (auto-detected if not specified)"

- [ ] 3.2.2 Update profile handling
  - Keep existing `--profile`, `--dev`, `--theme-dev` flags
  - Load profile from config file if not specified via CLI
  - CLI flags override config file

- [ ] 3.2.3 Pass environment/profile to Site
  - `site = Site.from_config(root_path, config_path, environment=env, profile=profile_str)`

- [ ] 3.2.4 Show effective config in verbose mode
  - If `--verbose`, print: "Environment: production, Profile: dev"
  - If `--debug`, show config snapshot

**Tests**:
- [ ] 3.2.5 `tests/integration/test_build_with_environment.py`
  - Test build with explicit environment
  - Test build with auto-detected environment
  - Test build with profile
  - Test build with environment + profile
  - Test CLI overrides config

---

### 3.3 Update Profile System

**Files to modify**:
```
bengal/utils/profile.py
```

**Tasks**:
- [ ] 3.3.1 Load profile from config if present
  - Check for `config/profiles/{profile}.yaml`
  - Merge profile config into runtime settings
  - CLI args still override everything

- [ ] 3.3.2 Keep backward compat
  - If no profile config file, use hardcoded defaults
  - Existing `BuildProfile.get_config()` still works

**Tests**:
- [ ] 3.3.3 `tests/unit/utils/test_profile_config.py`
  - Test loading profile from config file
  - Test fallback to hardcoded defaults
  - Test CLI override of profile settings

---

### 3.4 Update Serve Command

**Files to modify**:
```
bengal/cli/commands/serve.py
```

**Tasks**:
- [ ] 3.4.1 Add `--environment` flag
  - Default: "local"
  - Pass to Site.from_config()

- [ ] 3.4.2 Add `--profile` flag
  - Default: None (use config or auto-detect)
  - Pass to Site.from_config()

**Tests**:
- [ ] 3.4.3 `tests/integration/test_serve_with_config.py`
  - Test serve with environment
  - Test serve with profile
  - Test hot reload updates config

**Acceptance Criteria**:
- ✅ Site loads from config/ directory when present
- ✅ Environment auto-detection works in build/serve
- ✅ Profile config files override hardcoded defaults
- ✅ CLI flags override everything (highest priority)
- ✅ Backward compat: single-file configs still work
- ✅ All integration tests pass

---

## Week 4: Examples and Documentation

### 4.1 Create Example Configs

**Files to create**:
```
examples/config-directory/
├── config/
│   ├── _default/
│   │   ├── site.yaml
│   │   ├── build.yaml
│   │   ├── features.yaml
│   │   ├── theme.yaml
│   │   └── menus.yaml
│   ├── environments/
│   │   ├── local.yaml
│   │   ├── preview.yaml
│   │   └── production.yaml
│   └── profiles/
│       ├── writer.yaml
│       ├── theme-dev.yaml
│       └── dev.yaml
└── README.md

examples/config-simple/
├── bengal.yaml
└── README.md
```

**Tasks**:
- [ ] 4.1.1 Create directory structure example
  - Annotated YAML files with comments
  - Show YAML anchors for DRY
  - README explaining structure

- [ ] 4.1.2 Create simple single-file example
  - Minimal bengal.yaml
  - README explaining when to use

---

### 4.2 Update Main Example Site

**Files to modify**:
```
site/bengal.toml  →  site/config/
```

**Tasks**:
- [ ] 4.2.1 Migrate site/bengal.toml to config/
  - Split sections into separate files
  - Add environment overrides
  - Add profile configs

- [ ] 4.2.2 Document the migration
  - Add comment in old location pointing to new
  - Update site/README.md

---

### 4.3 Update Documentation

**Files to create/modify**:
```
site/content/docs/configuration/
├── overview.md           # NEW/UPDATE
├── directory-structure.md  # NEW
├── environments.md        # NEW
├── profiles.md            # NEW
├── feature-groups.md      # NEW
├── introspection.md       # NEW
└── migration-guide.md     # NEW
```

**Tasks**:
- [ ] 4.3.1 Write configuration overview
  - Explain directory vs single-file
  - When to use which approach
  - Link to detailed guides

- [ ] 4.3.2 Write directory structure guide
  - Explain config/_default/
  - Explain environments/
  - Explain profiles/
  - Show merge precedence diagram

- [ ] 4.3.3 Write environments guide
  - Explain local/preview/production
  - Show auto-detection examples
  - Explain manual override
  - Platform-specific tips (Netlify, Vercel, GitHub)

- [ ] 4.3.4 Write profiles guide
  - Explain writer/theme-dev/dev personas
  - Show profile config files
  - Explain when to create custom profiles

- [ ] 4.3.5 Write feature groups guide
  - List all features and their mappings
  - Explain expansion behavior
  - Show how to override expanded config

- [ ] 4.3.6 Write introspection guide
  - Document `config show` with examples
  - Document `config doctor` with examples
  - Document `config diff` with examples
  - Document `config init` with examples

- [ ] 4.3.7 Write migration guide
  - How to migrate from TOML to YAML directory
  - Step-by-step process
  - Common patterns
  - Automated migration tool (future)

---

### 4.4 Update bengal.toml.example

**Files to modify**:
```
bengal.toml.example  →  Keep for reference
```

**Files to create**:
```
config.example/     # NEW directory example
└── (structure as above)
```

**Tasks**:
- [ ] 4.4.1 Create config.example/ directory
  - Full annotated example
  - Show all options
  - Include comments explaining each section

- [ ] 4.4.2 Update bengal.toml.example header
  - Add note: "Prefer config/ directory for new projects"
  - Link to config.example/
  - Keep file for single-file preference

---

### 4.5 Update CLI Help Text

**Tasks**:
- [ ] 4.5.1 Update `bengal build --help`
  - Document --environment flag
  - Document --profile behavior
  - Add examples section

- [ ] 4.5.2 Update `bengal --help`
  - Add `config` command group to main help

- [ ] 4.5.3 Add examples to config commands
  - `bengal config show --help` with examples
  - `bengal config doctor --help` with examples
  - `bengal config diff --help` with examples
  - `bengal config init --help` with examples

**Acceptance Criteria**:
- ✅ Working examples in examples/ directory
- ✅ Main example site (site/) uses new system
- ✅ Complete documentation for all features
- ✅ Migration guide for existing users
- ✅ CLI help text updated with examples
- ✅ config.example/ shows best practices

---

## Week 5: Testing, Performance, Polish

### 5.1 Performance Testing

**Tasks**:
- [ ] 5.1.1 Benchmark config loading
  - Simple config (1 file): < 5ms
  - Complex config (10+ files): < 50ms
  - Profile if needed

- [ ] 5.1.2 Optimize if needed
  - Cache parsed YAML in memory
  - Lazy load environment-specific files
  - Optimize deep merge algorithm

- [ ] 5.1.3 Add performance tests
  - `tests/performance/test_config_loading.py`
  - Assert loading time < thresholds
  - Test with various config sizes

---

### 5.2 Integration Testing

**Tasks**:
- [ ] 5.2.1 Test full build pipeline
  - Build with directory config
  - Build with single-file config
  - Build with environment overrides
  - Build with profiles
  - Build with all combinations

- [ ] 5.2.2 Test error handling
  - Invalid YAML syntax
  - Missing required files
  - Type errors
  - Unknown keys
  - Circular dependencies (if we add imports later)

- [ ] 5.2.3 Test edge cases
  - Empty config directory
  - Missing _default/
  - Environment file without defaults
  - Profile conflicts with environment
  - Very deep nesting

---

### 5.3 Error Message Polish

**Tasks**:
- [ ] 5.3.1 Review all error messages
  - Make them actionable
  - Include suggestions
  - Show file paths clearly

- [ ] 5.3.2 Add helpful context
  - "Did you mean...?" for typos
  - "Try running: bengal config doctor"
  - Link to docs for complex errors

- [ ] 5.3.3 Test error messages
  - Verify they're helpful
  - Check formatting (colors, indentation)

---

### 5.4 Code Review and Cleanup

**Tasks**:
- [ ] 5.4.1 Code review
  - Check for edge cases
  - Verify error handling
  - Review test coverage

- [ ] 5.4.2 Cleanup TODOs and comments
  - Remove debug prints
  - Update docstrings
  - Add type hints where missing

- [ ] 5.4.3 Update type stubs
  - Ensure mypy passes
  - Add missing type annotations

---

### 5.5 Final Testing

**Tasks**:
- [ ] 5.5.1 Run full test suite
  - All unit tests pass
  - All integration tests pass
  - All performance tests pass

- [ ] 5.5.2 Test on real projects
  - Build Bengal docs site
  - Build example sites
  - Test on various environments (local, Netlify, Vercel)

- [ ] 5.5.3 Browser testing
  - Verify built sites work
  - Check asset loading
  - Test search functionality

**Acceptance Criteria**:
- ✅ Config loading < 50ms for complex configs
- ✅ All integration tests pass
- ✅ Error messages are helpful and actionable
- ✅ Code review complete
- ✅ Test coverage ≥ 90%
- ✅ Real projects build successfully
- ✅ Documentation complete and accurate

---

## Success Metrics

**Performance**:
- [ ] Config loading < 50ms (complex)
- [ ] Config loading < 5ms (simple)
- [ ] `bengal config doctor` < 1 second

**Quality**:
- [ ] Test coverage ≥ 90%
- [ ] Zero regressions in existing builds
- [ ] All error paths tested

**User Experience**:
- [ ] `config doctor` catches 95%+ typos
- [ ] `config show --origin` accurate
- [ ] `config init` scaffolds in < 1 second
- [ ] Documentation clear and complete

**Adoption**:
- [ ] Example sites migrated
- [ ] Bengal docs use new system
- [ ] Migration guide complete

---

## Rollout Plan

### Phase 1: Soft Launch (Week 5)
- ✅ Code complete and tested
- ✅ Documentation published
- ✅ Example sites updated
- 📣 Announce in commit messages
- 📣 Update README with new features

### Phase 2: Feedback (Week 6-7)
- 👂 Monitor for issues
- 🐛 Fix bugs if found
- 📝 Update docs based on feedback

### Phase 3: Promote (Week 8+)
- 📣 Blog post highlighting features
- 📣 Update marketing site
- 📣 Social media posts
- 📣 Comparison docs (vs Hugo, MkDocs, Sphinx)

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| **Breaking changes** | Keep single-file support, add config/ as optional |
| **Performance regression** | Benchmark and profile, optimize critical paths |
| **Complex edge cases** | Extensive integration testing, real-world testing |
| **Documentation gaps** | Write docs alongside code, review for completeness |
| **User confusion** | Clear examples, migration guide, helpful errors |

---

## Definition of Done

- [ ] All tasks completed (checkboxes above)
- [ ] Test coverage ≥ 90%
- [ ] Performance targets met
- [ ] Documentation complete
- [ ] Examples working
- [ ] Code reviewed
- [ ] No known bugs
- [ ] Ready to announce

---

## Next Steps

1. **Review this plan** - Any additions/changes?
2. **Start Week 1** - Create directory_loader.py
3. **Daily standup** - Track progress, adjust as needed
4. **Ship it!** 🚀

---

**Let's build the best config system in the SSG space.** 🔥
