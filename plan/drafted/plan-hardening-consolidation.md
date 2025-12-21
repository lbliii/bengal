# Plan: Hardening Phase - Codebase Consolidation

**RFC**: `plan/drafted/rfc-hardening-consolidation.md`  
**Status**: Draft  
**Created**: 2025-12-21  
**Estimated Time**: 8-10 hours (phased, multiple PRs)

---

## Summary

This plan implements the RFC’s phased consolidation work as a series of small, bisectable refactors. Each task is one atomic commit, with validation after each phase.

---

## Evidence checkpoints (verified in code)

- **Duplicate `BengalPaths` classes**: `bengal/cache/paths.py:52`, `bengal/utils/paths.py:59`
- **`format_path_for_display` usage**: `bengal/core/page/__init__.py:409`, `bengal/orchestration/stats/models.py:36`
- **Renderer markdown access inconsistency**:
  - `renderer._md`: `bengal/directives/glossary.py:442`
  - `renderer.md`: `bengal/directives/glossary.py:457`
  - Safeguard pattern: `bengal/directives/steps.py:244`
- **Multiple `escape_html` definitions (not just one)**:
  - `bengal/utils/text.py:306`
  - `bengal/directives/utils.py:20`
  - `bengal/directives/cards/utils.py:390`
  - `bengal/directives/base.py:354` (wrapper method)
  - plus glossary local helper: `bengal/directives/glossary.py:484`
- **Remaining `os.path` usage (8 matches / 4 files)**:
  - `bengal/utils/rich_console.py:141,144`
  - `bengal/server/live_reload.py:305,307,308,318`
  - `bengal/content_layer/sources/rest.py:90`
  - `bengal/server/request_handler.py:373` (comment)
- **Scattered `site.config.get(` calls**: 156 matches across 61 files (repo grep)
- **Instance-level loggers**: 13 matches for `self.logger = get_logger(` (repo grep)
- **`SitePropertiesMixin` location**: `bengal/core/site/properties.py:28`

---

## Tasks

### Phase 1: Paths consolidation (High priority)

#### Task 1.1: Move `format_path_for_display` into `bengal/utils/text.py` and update call sites
- **Files**:
  - `bengal/utils/paths.py`
  - `bengal/utils/text.py`
  - `bengal/core/page/__init__.py`
  - `bengal/orchestration/stats/models.py`
- **Action**:
  - Move `format_path_for_display()` implementation out of `bengal/utils/paths.py` into `bengal/utils/text.py`.
  - Update imports in the two known call sites to import from `bengal.utils.text`.
  - Keep behavior identical (including `None` handling and base path relativity).
- **Commit**: `utils(text): move format_path_for_display out of utils.paths; update call sites`

#### Task 1.2: Switch CLI log/profile path resolution to `bengal.cache.paths.BengalPaths` properties
- **Files**:
  - `bengal/cli/commands/build.py`
  - `bengal/cli/commands/serve.py`
- **Action**:
  - Replace `bengal.utils.paths.BengalPaths.get_build_log_path` with:
    - `paths = bengal.cache.paths.BengalPaths(Path(source))`
    - `paths.ensure_dirs()`
    - `log_path = Path(log_file) if log_file else paths.build_log`
  - Replace `BengalPaths.get_profile_path(...)` with the `paths.profiles_dir / filename` pattern and ensure directories exist.
  - Replace serve log path with `BengalPaths(root_path).serve_log` (and ensure `logs_dir` exists).
- **Commit**: `cli: resolve build/serve log + profile paths via cache.paths.BengalPaths`

#### Task 1.3: Replace internal `bengal.utils.paths.BengalPaths` usage with `bengal.cache.paths.BengalPaths` (keep compatibility shim)
- **Files** (from repo grep for `bengal.utils.paths` / `bengal.cache.paths`, 24 matches / 18 files):
  - `bengal/core/page/__init__.py`
  - `bengal/cli/commands/build.py`
  - `bengal/cli/commands/validate.py`
  - `bengal/cli/commands/serve.py`
  - `bengal/debug/delta_analyzer.py`
  - `bengal/assets/pipeline.py`
  - `bengal/rendering/template_engine/environment.py`
  - `bengal/orchestration/stats/models.py`
  - `bengal/cli/helpers/site_loader.py`
  - `bengal/cli/commands/sources.py`
  - `bengal/cli/commands/perf.py`
  - `bengal/utils/__init__.py`
  - `bengal/utils/paths.py`
  - `bengal/server/pid_manager.py`
  - `bengal/cache/utils.py`
  - `bengal/cache/__init__.py`
  - `bengal/cache/paths.py`
  - `bengal/core/site/properties.py`
- **Action**:
  - Make `bengal/cache/paths.py` the single internal source of `BengalPaths` and `STATE_DIR_NAME`.
  - Convert `bengal/utils/paths.py` into a small compatibility module that re-exports:
    - `BengalPaths` from `bengal.cache.paths`
    - `STATE_DIR_NAME` from `bengal.cache.paths`
    - `format_path_for_display` from `bengal.utils.text`
  - Update internal imports to prefer `bengal.cache.paths` (leaving `bengal.utils.paths` supported for external callers).
- **Commit**: `cache(paths): make cache.paths the canonical BengalPaths import; keep utils.paths as compat shim`

---

### Phase 2: Directive renderer access pattern (High priority)

#### Task 2.1: Add `get_markdown_instance()` helper and use it in directives
- **Files**:
  - `bengal/directives/utils.py`
  - `bengal/directives/glossary.py`
  - (optional) `bengal/directives/steps.py` (already uses safeguard pattern)
- **Action**:
  - Add `get_markdown_instance(renderer: Any) -> Any | None` that returns `getattr(renderer, "_md", None) or getattr(renderer, "md", None)`.
  - Update glossary inline parsing to use the helper rather than branching on `hasattr(renderer, "_md")` vs `hasattr(renderer, "md")`.
- **Commit**: `directives: add get_markdown_instance helper; adopt in glossary inline parsing`

---

### Phase 3: HTML escaping consolidation (Medium priority)

#### Task 3.1: Decide canonical escaping semantics, then align `bengal.utils.text.escape_html`
- **Files**:
  - `bengal/utils/text.py`
- **Action**:
  - Decide whether `escape_html()` must escape apostrophes (`'`) as `&#x27;` (current behavior in `directives/utils.py` and `directives/cards/utils.py`) or whether stdlib `html.escape(..., quote=True)` behavior is sufficient.
  - Update `bengal.utils.text.escape_html()` to match the chosen semantics.
- **Commit**: `utils(text): align escape_html semantics for attribute-safe escaping`

#### Task 3.2: Remove duplicate `escape_html` implementations by delegating to `bengal.utils.text.escape_html`
- **Files**:
  - `bengal/directives/utils.py`
  - `bengal/directives/cards/utils.py`
  - `bengal/directives/glossary.py`
  - `bengal/directives/base.py` (wrapper should continue to call a single function)
- **Action**:
  - Replace custom implementations in directives with calls/imports from `bengal.utils.text.escape_html`.
  - Replace glossary’s `_escape_html()` helper with `bengal.utils.text.escape_html` (keeping XSS intent explicit).
- **Commit**: `directives: consolidate escape_html to utils.text; remove directive-local implementations`

#### Task 3.3 (Optional): Standardize `import html as ...` aliases to one convention
- **Files** (8 alias sites verified by grep):
  - `bengal/rendering/parsers/mistune/toc.py`
  - `bengal/rendering/template_functions/content.py`
  - `bengal/rendering/parsers/mistune/highlighting.py`
  - `bengal/rendering/pipeline/toc.py`
  - `bengal/utils/text.py`
  - `bengal/directives/code_tabs.py`
  - `bengal/directives/list_table.py`
- **Action**:
  - Pick one import style (e.g., `import html as html_module`) and apply consistently.
  - Only do this if it does not create noisy diffs that complicate review.
- **Commit**: `refactor: standardize html import aliasing`

---

### Phase 4: `os.path` → `pathlib.Path` migration (Medium priority)

#### Task 4.1: Replace remaining `os.path.*` usages with `Path`
- **Files**:
  - `bengal/utils/rich_console.py`
  - `bengal/server/live_reload.py`
  - `bengal/content_layer/sources/rest.py`
  - `bengal/server/request_handler.py` (comment only)
- **Action**:
  - Replace `os.path.exists`, `os.path.isdir`, `os.path.join`, `os.path.getmtime` with `Path(...).exists()`, `Path(...).is_dir()`, `Path(...) / ...`, `Path(...).stat().st_mtime` (or `Path(...).stat().st_mtime_ns` where appropriate).
  - Keep behavior identical (including relative path semantics in live reload).
- **Commit**: `refactor: replace remaining os.path usage with pathlib.Path`

---

### Phase 5: Config accessor properties (Lower priority)

#### Task 5.1: Add section accessors to `SitePropertiesMixin`
- **Files**:
  - `bengal/core/site/properties.py`
- **Action**:
  - Add properties like `assets_config`, `build_config`, `i18n_config`, `menu_config` returning `dict[str, Any]` with safe dict coercion.
- **Commit**: `core(site): add config section accessors on SitePropertiesMixin`

#### Task 5.2: Migrate high-touch modules to use new accessors (small, targeted sweep)
- **Files** (starting points from grep top offenders):
  - `bengal/orchestration/asset.py`
  - `bengal/orchestration/menu.py`
  - `bengal/cli/commands/build.py` (when touching anyway)
- **Action**:
  - Replace repeated `site.config.get("assets", {})` and similar patterns with `site.assets_config`, `site.build_config`, etc.
- **Commit**: `orchestration: adopt SitePropertiesMixin config accessors in assets/menu`

#### Task 5.3 (Optional): Gradual sweep of remaining `site.config.get(` calls by subsystem
- **Files**: Remaining matches (156 total across 61 files)
- **Action**:
  - Break the migration into several commits by subsystem (rendering, postprocess, health, server, cli), each with a tight diff.
- **Commit**: `refactor(config): migrate <subsystem> to SitePropertiesMixin config accessors`

---

### Phase 6: Logger pattern standardization (Lower priority)

#### Task 6.1: Convert straightforward instance-level loggers to module-level loggers
- **Files** (from grep for `self.logger = get_logger(`):
  - `bengal/discovery/content_discovery.py`
  - `bengal/orchestration/asset.py`
  - `bengal/postprocess/sitemap.py`
  - `bengal/postprocess/redirects.py`
  - `bengal/postprocess/rss.py`
  - `bengal/orchestration/build/__init__.py`
  - `bengal/orchestration/static.py`
  - `bengal/orchestration/content.py`
  - `bengal/orchestration/incremental/orchestrator.py`
  - `bengal/discovery/version_resolver.py`
  - `bengal/config/loader.py`
  - `bengal/cache/dependency_tracker.py`
- **Action**:
  - Replace `self.logger = get_logger(__name__)` with module-level `logger = get_logger(__name__)`.
  - Update call sites in methods to use `logger`.
- **Commit**: `refactor(logging): replace instance loggers with module-level logger`

#### Task 6.2: Decide what to do with `bengal/directives/base.py` logger naming
- **Files**:
  - `bengal/directives/base.py`
- **Action**:
  - `base.py` uses `get_logger(self.__class__.__module__)` to attribute logs to the directive’s concrete module.
  - Decide whether to keep this exception (document it) or adopt a module-level logger while preserving the previous log “name” in structured fields.
- **Commit**: `directives(logging): document or refactor directive logger naming`

---

## Validation (after each task)

- [ ] `ruff` / formatting passes
- [ ] `pytest` passes
- [ ] `mypy` (if part of existing workflow) passes

---

## Changelog Entry (draft)

- `refactor: consolidate duplicated path/escape helpers; standardize directive markdown access; complete os.path→pathlib migration`
