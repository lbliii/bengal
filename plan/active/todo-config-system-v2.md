## Config System v2 - Quick TODO Tracker

**Status**: 🟡 In Progress
**Target**: 4-5 weeks
**Started**: 2025-10-25

---

## 🏃 Week 1: Core Loader (Current)

### Files
- [ ] `bengal/config/directory_loader.py` - ConfigDirectoryLoader
- [ ] `bengal/config/merge.py` - Deep merge logic
- [ ] `bengal/config/feature_mappings.py` - Feature → detailed config
- [ ] `bengal/config/environment.py` - Environment detection
- [ ] `bengal/config/origin_tracker.py` - Origin tracking

### Tests
- [ ] `tests/unit/config/test_directory_loader.py`
- [ ] `tests/unit/config/test_merge.py`
- [ ] `tests/unit/config/test_feature_mappings.py`
- [ ] `tests/unit/config/test_environment.py`
- [ ] `tests/unit/config/test_origin_tracker.py`

### Acceptance
- [ ] ConfigDirectoryLoader loads multi-file configs
- [ ] Merge precedence: defaults < env < profile
- [ ] All 8 feature mappings expand correctly
- [ ] Environment auto-detection works
- [ ] Test coverage ≥ 90%

---

## 📊 Week 2: Introspection

### Commands
- [ ] `bengal config show` - Display merged config
- [ ] `bengal config show --origin` - Show file sources
- [ ] `bengal config doctor` - Validate and lint
- [ ] `bengal config diff` - Compare configs
- [ ] `bengal config init` - Scaffold structure

### Tests
- [ ] `tests/unit/cli/commands/test_config_show.py`
- [ ] `tests/unit/cli/commands/test_config_doctor.py`
- [ ] `tests/unit/cli/commands/test_config_diff.py`
- [ ] `tests/unit/cli/commands/test_config_init.py`

### Acceptance
- [ ] All commands work and look beautiful
- [ ] Help text clear with examples
- [ ] Error messages actionable

---

## 🔌 Week 3: Integration

### Core
- [ ] Update `Site.from_config()` for directory loading
- [ ] Update `bengal/cli/commands/build.py` with `--environment`
- [ ] Update `bengal/utils/profile.py` to load from config files
- [ ] Update `bengal/cli/commands/serve.py` with env/profile flags

### Tests
- [ ] `tests/unit/core/test_site_config_loading.py`
- [ ] `tests/integration/test_build_with_environment.py`
- [ ] `tests/unit/utils/test_profile_config.py`
- [ ] `tests/integration/test_serve_with_config.py`

### Acceptance
- [ ] Site loads from config/ when present
- [ ] Environment auto-detection works
- [ ] Profile config files work
- [ ] Backward compat maintained

---

## 📚 Week 4: Examples & Docs

### Examples
- [ ] `examples/config-directory/` - Full structure example
- [ ] `examples/config-simple/` - Single file example
- [ ] Migrate `site/` to use config/ directory

### Documentation
- [ ] `docs/configuration/overview.md`
- [ ] `docs/configuration/directory-structure.md`
- [ ] `docs/configuration/environments.md`
- [ ] `docs/configuration/profiles.md`
- [ ] `docs/configuration/feature-groups.md`
- [ ] `docs/configuration/introspection.md`
- [ ] `docs/configuration/migration-guide.md`

### Reference
- [ ] Create `config.example/` annotated directory
- [ ] Update CLI help text
- [ ] Update README

### Acceptance
- [ ] All features documented
- [ ] Migration guide complete
- [ ] Examples work

---

## 🚀 Week 5: Polish & Ship

### Performance
- [ ] Benchmark config loading (< 50ms)
- [ ] Optimize if needed
- [ ] Add performance tests

### Testing
- [ ] Full integration testing
- [ ] Error handling tests
- [ ] Edge case tests
- [ ] Real project testing (Bengal docs)

### Polish
- [ ] Review all error messages
- [ ] Code cleanup
- [ ] Type hints complete
- [ ] Documentation review

### Ship
- [ ] All tests pass
- [ ] Coverage ≥ 90%
- [ ] Performance targets met
- [ ] Ready to announce

---

## 📈 Progress

**Week 1**: ░░░░░░░░░░ 0%
**Week 2**: ░░░░░░░░░░ 0%
**Week 3**: ░░░░░░░░░░ 0%
**Week 4**: ░░░░░░░░░░ 0%
**Week 5**: ░░░░░░░░░░ 0%

**Overall**: ░░░░░░░░░░ 0%

---

## 🎯 Next Actions

1. [ ] Create `bengal/config/directory_loader.py`
2. [ ] Create `bengal/config/merge.py`
3. [ ] Create `bengal/config/feature_mappings.py`

**Focus**: Get Week 1 done, then iterate.

---

## 📝 Notes

- Keep single-file configs working (backward compat)
- Prioritize user experience (helpful errors, beautiful output)
- Test on real projects early and often
- Document as you go, not at the end

---

**Updated**: 2025-10-25
