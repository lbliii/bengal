# Plan: Unified URL Model

**RFC**: `rfc-unified-url-model.md`  
**Status**: Draft  
**Created**: 2024-12-21  
**Estimated Time**: 3-4 days

---

## Summary

Replace Bengal's confusing URL properties (`url`, `relative_url`, `site_path`, `permalink`) with a clear two-property model: `href` (for templates, includes baseurl) and `_path` (for internals, no baseurl). This eliminates deployment bugs on GitHub Pages and provides AI-native guardrails via underscore naming.

---

## Tasks

### Phase 0: Codemod Development

Build a CLI tool to automate migration across themes and user sites.

#### Task 0.1: Add codemod CLI command scaffold
- **Files**: `bengal/cli/commands/codemod.py`
- **Action**: Create new CLI command `bengal codemod-urls` with click decorators, help text, and basic argument parsing (`--path`, `--dry-run`, `--diff`)
- **Commit**: `cli(codemod): add codemod-urls command scaffold with dry-run and diff modes`

#### Task 0.2: Implement URL replacement logic
- **Files**: `bengal/cli/commands/codemod.py`
- **Action**: Add regex-based replacement logic:
  - `\.url\b` → `.href` (but NOT `source_url`, `canonical_url`, etc.)
  - `\.relative_url\b` → `._path`
  - `\.site_path\b` → `._path`
  - `\.permalink\b` → `.href`
- **Depends on**: Task 0.1
- **Commit**: `cli(codemod): implement url property replacement with smart boundary detection`

#### Task 0.3: Add file type filtering and preview
- **Files**: `bengal/cli/commands/codemod.py`
- **Action**: Filter to `.html`, `.py`, `.jinja2`, `.j2` files; implement unified diff output for `--diff` mode; add file count summary
- **Depends on**: Task 0.2
- **Commit**: `cli(codemod): add file type filtering, diff preview, and summary output`

#### Task 0.4: Register codemod command
- **Files**: `bengal/cli/commands/__init__.py`, `bengal/cli/base.py`
- **Action**: Import and register `codemod` command group
- **Depends on**: Task 0.3
- **Commit**: `cli: register codemod-urls command`

#### Task 0.5: Add codemod tests
- **Files**: `tests/unit/cli/test_codemod.py`
- **Action**: Test edge cases: `.url` vs `source_url`, underscore preservation, dry-run behavior, diff output format
- **Depends on**: Task 0.4
- **Commit**: `tests(cli): add codemod-urls unit tests with edge case coverage`

---

### Phase 1: Core Model Changes (Non-Breaking)

Add new `href` and `_path` properties alongside existing ones. No deprecation warnings yet.

#### Task 1.1: Add `href` and `_path` to NavNode dataclass
- **Files**: `bengal/core/nav_tree.py`
- **Action**:
  - Rename internal `url` field to `_path` in `NavNode` dataclass
  - Add property aliases for backward compatibility: `@property def url(self) -> str: return self._path`
- **Commit**: `core(nav_tree): rename NavNode.url to ._path; add backward-compatible alias`

#### Task 1.2: Add `href` and `_path` to NavNodeProxy
- **Files**: `bengal/core/nav_tree.py`
- **Action**:
  - Add `href` property that returns URL with baseurl (current `url` logic)
  - Add `_path` property that returns raw path without baseurl
  - Keep `url` as non-deprecated alias for `href` (deprecation comes in Phase 2)
- **Depends on**: Task 1.1
- **Commit**: `core(nav_tree): add NavNodeProxy.href and ._path properties`

#### Task 1.3: Add `href` and `_path` to Page metadata
- **Files**: `bengal/core/page/metadata.py`
- **Action**:
  - Add `href` property (same as current `url`)
  - Add `_path` property (same as current `relative_url`)
  - Keep existing properties as aliases (no deprecation yet)
- **Commit**: `core(page): add Page.href and ._path properties alongside existing aliases`

#### Task 1.4: Add `href` and `_path` to PageProxy
- **Files**: `bengal/core/page/proxy.py`
- **Action**: Add `href` and `_path` properties that delegate to underlying page
- **Depends on**: Task 1.3
- **Commit**: `core(page): add PageProxy.href and ._path delegation`

#### Task 1.5: Add `href` and `_path` to Section
- **Files**: `bengal/core/section.py`
- **Action**:
  - Add `href` cached_property (same as current `url`)
  - Add `_path` cached_property (same as current `relative_url`)
- **Commit**: `core(section): add Section.href and ._path properties`

#### Task 1.6: Add `href` and `_path` to Asset
- **Files**: `bengal/assets/asset.py` or relevant asset file
- **Action**: Add `href` property (calls existing `_site._asset_url()` logic) and `_path` for logical path
- **Commit**: `assets: add Asset.href and ._path properties`

#### Task 1.7: Add `absolute_href` property
- **Files**: `bengal/core/page/metadata.py`, `bengal/core/section.py`, `bengal/core/nav_tree.py`
- **Action**: Add `absolute_href` property per RFC design (returns href if baseurl is absolute, else returns href as-is)
- **Depends on**: Tasks 1.3, 1.5, 1.2
- **Commit**: `core: add absolute_href property to Page, Section, NavNodeProxy`

#### Task 1.8: Add `href` Jinja filter
- **Files**: `bengal/rendering/template_engine/url_helpers.py`, `bengal/rendering/template_engine/filters.py`
- **Action**: Add `href` filter for manual paths: `{{ '/about/' | href }}`
- **Commit**: `rendering: add href Jinja filter for manual path baseurl application`

#### Task 1.9: Update url_helpers.py to prefer href
- **Files**: `bengal/rendering/template_engine/url_helpers.py`
- **Action**: Add `href_for()` helper function; update docstrings to recommend `href`
- **Depends on**: Task 1.8
- **Commit**: `rendering(url_helpers): add href_for helper; update docs to recommend href`

---

### Phase 1b: Tests for New Properties

#### Task 1.10: Add unit tests for href/path properties
- **Files**: `tests/unit/core/test_href_property.py`
- **Action**: Test all scenarios:
  - `href` includes baseurl (empty, path-only `/bengal`, absolute `https://`)
  - `_path` excludes baseurl in all cases
  - `absolute_href` behavior
  - NavNode, NavNodeProxy, Page, Section, Asset
- **Commit**: `tests(core): add comprehensive href/_path property tests`

#### Task 1.11: Add integration tests for template rendering
- **Files**: `tests/integration/test_href_templates.py`
- **Action**: Test templates using `href` produce correct output for GitHub Pages deployment scenarios
- **Depends on**: Task 1.10
- **Commit**: `tests(integration): add href template rendering tests for deployment scenarios`

---

### Phase 1c: Theme Migration

#### Task 1.12: Migrate default theme templates to href
- **Files**: `bengal/themes/default/templates/**/*.html` (56 files, ~154 occurrences)
- **Action**: Run `bengal codemod-urls --path bengal/themes/default/` then review changes
- **Depends on**: Tasks 0.5, 1.2, 1.3, 1.5
- **Commit**: `themes(default): migrate templates from .url to .href`

#### Task 1.13: Migrate default theme JavaScript to href
- **Files**: `bengal/themes/default/assets/js/**/*.js`
- **Action**: Update JS files that access `.url` property (search.js, graph-*.js, build-badge.js)
- **Depends on**: Task 1.12
- **Commit**: `themes(default): migrate JavaScript from .url to .href`

---

### Phase 1d: Internal Code Migration

#### Task 1.14: Migrate cache subsystem to _path
- **Files**: `bengal/cache/*.py`
- **Action**: Update cache key generation and lookups to use `_path` for consistency
- **Commit**: `cache: migrate internal lookups from .url to ._path`

#### Task 1.15: Migrate health validators to _path
- **Files**: `bengal/health/*.py`
- **Action**: Update link validators and consistency checks to use `_path`
- **Depends on**: Task 1.14
- **Commit**: `health: migrate validators from relative_url to ._path`

#### Task 1.16: Migrate rendering subsystem
- **Files**: `bengal/rendering/**/*.py`
- **Action**: Update link_transformer.py and related to use `_path` for lookup, `href` for output
- **Commit**: `rendering: migrate to _path for lookup, href for output`

#### Task 1.17: Migrate orchestration subsystem
- **Files**: `bengal/orchestration/*.py`
- **Action**: Update any URL comparisons to use `_path`
- **Commit**: `orchestration: migrate url comparisons to ._path`

#### Task 1.18: Migrate postprocess subsystem
- **Files**: `bengal/postprocess/*.py`
- **Action**: Update sitemap generation to use appropriate properties
- **Commit**: `postprocess: migrate sitemap/RSS generators to href/absolute_href`

---

### Phase 2: Deprecation Warnings

#### Task 2.1: Add deprecation warnings to Page
- **Files**: `bengal/core/page/metadata.py`
- **Action**: Add `warnings.warn()` to `url`, `relative_url`, `site_path`, `permalink` properties
- **Commit**: `core(page): add deprecation warnings to url, relative_url, site_path, permalink`

#### Task 2.2: Add deprecation warnings to Section
- **Files**: `bengal/core/section.py`
- **Action**: Add deprecation warnings to `url`, `relative_url`, `site_path` properties
- **Depends on**: Task 2.1
- **Commit**: `core(section): add deprecation warnings to legacy url properties`

#### Task 2.3: Add deprecation warnings to NavNodeProxy
- **Files**: `bengal/core/nav_tree.py`
- **Action**: Add deprecation warnings to `url`, `relative_url` properties
- **Depends on**: Task 2.2
- **Commit**: `core(nav_tree): add deprecation warnings to NavNodeProxy legacy properties`

#### Task 2.4: Add deprecation warnings to PageProxy
- **Files**: `bengal/core/page/proxy.py`
- **Action**: Add deprecation warnings to `url`, `relative_url` properties
- **Depends on**: Task 2.3
- **Commit**: `core(page): add deprecation warnings to PageProxy legacy properties`

#### Task 2.5: Add deprecation tests
- **Files**: `tests/unit/core/test_deprecation_warnings.py`
- **Action**: Test that deprecated properties emit DeprecationWarning with correct message
- **Depends on**: Task 2.4
- **Commit**: `tests(core): add deprecation warning verification tests`

#### Task 2.6: Update documentation
- **Files**: `architecture/object-model.md`, `README.md`, `QUICKSTART.md`
- **Action**: Document new `href`/`_path` convention; add migration guide
- **Depends on**: Task 2.5
- **Commit**: `docs: document href/_path convention and migration guide`

---

### Phase 3: Validation & Cleanup

#### Task 3.1: Run full test suite
- **Files**: N/A
- **Action**: `uv run pytest tests/ -v`
- **Validation**: All tests pass

#### Task 3.2: Run linter
- **Files**: N/A
- **Action**: `uv run ruff check bengal/ --fix`
- **Validation**: No errors

#### Task 3.3: Run health validators
- **Files**: N/A
- **Action**: `bengal health site/`
- **Validation**: No broken links

#### Task 3.4: Test GitHub Pages deployment
- **Files**: N/A
- **Action**: Build with `baseurl: /bengal` and verify all links work
- **Validation**: Links include baseurl prefix

---

## Validation Checklist

- [ ] Unit tests pass (`uv run pytest tests/unit/ -v`)
- [ ] Integration tests pass (`uv run pytest tests/integration/ -v`)
- [ ] Linter passes (`uv run ruff check bengal/`)
- [ ] Type checker passes (`uv run mypy bengal/`)
- [ ] Health validators pass (`bengal health site/`)
- [ ] GitHub Pages deployment works (manual test)
- [ ] Deprecation warnings fire correctly

---

## Changelog Entry

```markdown
### Changed

- **URL Model Overhaul**: Introduced `href` and `_path` properties across Page, Section, NavNodeProxy, and Asset classes for clearer URL handling (#unified-url-model)
  - `href`: Use in templates for links (includes `baseurl` automatically)
  - `_path`: Use internally for lookups and comparisons (no `baseurl`)
  - `absolute_href`: Fully-qualified URL for meta tags and sitemaps
- **AI-Native Guardrails**: Underscore prefix on `_path` signals "internal only" to prevent template misuse
- Added `bengal codemod-urls` CLI command for automated migration of themes and user sites
- Added `href` Jinja filter for manual path baseurl application

### Deprecated

- `page.url` → Use `page.href` instead
- `page.relative_url` → Use `page._path` instead
- `page.site_path` → Use `page._path` instead
- `page.permalink` → Use `page.href` instead
- Same deprecations apply to Section, NavNodeProxy, and PageProxy

### Migration

Run `bengal codemod-urls --path your-theme/` to automatically migrate templates.
```

---

## Task Summary

| Phase | Tasks | Est. Time |
|-------|-------|-----------|
| Phase 0: Codemod | 5 tasks | 3-4 hours |
| Phase 1: Core | 9 tasks | 4-5 hours |
| Phase 1b: Tests | 2 tasks | 2 hours |
| Phase 1c: Themes | 2 tasks | 1-2 hours |
| Phase 1d: Internal | 5 tasks | 3-4 hours |
| Phase 2: Deprecation | 6 tasks | 2-3 hours |
| Phase 3: Validation | 4 tasks | 1-2 hours |
| **Total** | **33 tasks** | **~20 hours** |

---

## Dependencies Graph

```
Phase 0 (Codemod)
  0.1 → 0.2 → 0.3 → 0.4 → 0.5

Phase 1 (Core) - can run parallel to Phase 0
  1.1 → 1.2 ─┬→ 1.7
  1.3 → 1.4 ─┤
  1.5 ───────┘
  1.6 (independent)
  1.8 → 1.9

Phase 1b (Tests) - after Phase 1 core
  1.10 → 1.11

Phase 1c (Themes) - after Phase 0 + Phase 1
  1.12 → 1.13

Phase 1d (Internal) - after Phase 1
  1.14 → 1.15
  1.16 (independent)
  1.17 (independent)
  1.18 (independent)

Phase 2 (Deprecation) - after Phase 1c, 1d
  2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6

Phase 3 (Validation) - after all
  3.1 → 3.2 → 3.3 → 3.4
```
