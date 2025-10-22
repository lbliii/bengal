# Dependency Optimization Plan

**Status**: Draft  
**Created**: 2025-10-20  
**Priority**: High (reduces install size and complexity)

## Executive Summary

Bengal currently has **15 direct dependencies + 5 transitive = 20 total packages** installed on `pip install bengal`. This audit identifies opportunities to reduce this to **~8-10 core dependencies** by making several features optional, eliminating redundant packages, and using stdlib alternatives.

**Estimated Impact:**
- **Install size reduction**: ~35-40% (from ~8 MB to ~5 MB)
- **Install time reduction**: ~30% faster
- **Simpler dependency tree**: Fewer potential conflicts
- **Better user experience**: Core SSG works immediately, opt-in for advanced features

---

## Current State Analysis

### Core Dependencies (Must Keep - 8)
✅ **Essential for basic SSG functionality**

1. **click** (107 KB) - CLI framework, essential
2. **jinja2** (134 KB) - Template engine, essential  
3. **pyyaml** (183 KB) - YAML frontmatter parsing, essential
4. **pygments** (1.2 MB) - Syntax highlighting, essential for docs
5. **python-frontmatter** (9.8 KB) - Frontmatter parsing, essential
6. **rich** (243 KB) - Terminal output, essential for good UX
7. **mistune** (53 KB) - Markdown parser (fast), essential
8. **markdown** (107 KB) - *OPTIONAL* - Alternative parser, can be made optional

### Dependencies to Make Optional (6)

⚠️ **Should be installable via extras**

9. **pillow** (4.7 MB!) - Image processing
   - **Usage**: 2 files (images.py, asset.py)
   - **Feature**: Image dimensions, optimization, data URIs
   - **Recommendation**: Make optional via `pip install bengal[images]`

10. **psutil** (built from source!) - System utilities
    - **Usage**: 2 files (performance_collector.py, pid_manager.py)
    - **Feature**: Memory tracking, process management
    - **Recommendation**: Already has graceful fallback, make fully optional via `pip install bengal[perf]`

11. **csscompressor** (9.5 KB) - CSS minification
    - **Usage**: 1 file (asset.py)
    - **Feature**: CSS minification fallback
    - **Recommendation**: Make optional via `pip install bengal[minify]`

12. **jsmin** (tiny) - JS minification
    - **Usage**: 1 file (asset.py)
    - **Feature**: JS minification
    - **Recommendation**: Make optional via `pip install bengal[minify]`

13. **questionary** (36 KB) - Interactive CLI prompts
    - **Usage**: 1 file (new.py)
    - **Feature**: Pretty site creation wizard
    - **Recommendation**: Already has fallback, make fully optional

14. **watchdog** - File watching (already in server extra!)
    - **Status**: ✅ Already optional in `[project.optional-dependencies]`
    - **Action**: None needed

### Dependencies to Remove (1)

❌ **Can be replaced with stdlib**

15. **toml** (16 KB) - TOML parsing
    - **Usage**: 6 files (file_io.py, template_engine.py, project.py, autodoc/config.py, component_preview.py, theme_resolution.py)
    - **Replacement**: Use `tomllib` (Python 3.11+ stdlib)
    - **Benefit**: One less dependency, no behavior change
    - **Note**: Bengal requires Python 3.14+, so tomllib is always available

### Dual Markdown Parser Situation

🔍 **Investigation Findings:**

**Current State:**
- Both `markdown` (python-markdown) and `mistune` are required dependencies
- Users can choose via `config['markdown_engine']` or `config['markdown']['parser']`
- Default: `mistune` (recommended for speed)

**Usage Analysis:**
- `python-markdown`: 14 files (mostly legacy, validators, API doc enhancer)
- `mistune`: 15 files (plugins, directives, main parser)

**Recommendation:**
1. **Keep mistune as core** (default, faster, feature-complete)
2. **Make python-markdown optional** via `pip install bengal[markdown-alt]`
3. **Graceful degradation**: If user sets `markdown_engine = "python-markdown"` but it's not installed, show error message with install instruction

**Benefits:**
- Removes 107 KB from default install
- Users who need python-markdown can opt-in
- 95% of users will never need it

---

## Proposed New Structure

### Core Install (8 packages, ~2.1 MB)
```toml
[project.dependencies]
click>=8.1.7
mistune>=3.0.0
jinja2>=3.1.0
pyyaml>=6.0
pygments>=2.18.0
python-frontmatter>=1.0.0
rich>=13.7.0
```

### Optional Features
```toml
[project.optional-dependencies]
# Already exists
server = ["watchdog>=3.0.0"]

# Already exists  
css = ["lightningcss>=0.2.0"]

# NEW: Image processing features
images = ["pillow>=10.0.0"]

# NEW: Asset minification
minify = [
    "csscompressor>=0.9.5",
    "jsmin>=3.0.1",
]

# NEW: Performance monitoring
perf = ["psutil>=5.9.0"]

# NEW: Interactive CLI wizard
wizard = ["questionary>=2.0.0"]

# NEW: Alternative markdown parser
markdown-alt = ["markdown>=3.5.0"]

# NEW: All optional features
full = [
    "watchdog>=3.0.0",
    "lightningcss>=0.2.0",
    "pillow>=10.0.0",
    "csscompressor>=0.9.5",
    "jsmin>=3.0.1",
    "psutil>=5.9.0",
    "questionary>=2.0.0",
    "markdown>=3.5.0",
]
```

### Installation Examples
```bash
# Minimal install (docs site, blog, etc.)
pip install bengal

# With development server
pip install bengal[server]

# With image optimization
pip install bengal[images]

# Full featured
pip install bengal[full]

# Custom combo
pip install bengal[server,images,minify]
```

---

## Implementation Plan

### Phase 1: Low-Hanging Fruit (15 min)
**Target: Remove toml dependency**

1. ✅ Update `bengal/utils/file_io.py`:
   ```python
   # Replace:
   import toml
   data = toml.loads(content)

   # With:
   import tomllib
   data = tomllib.loads(content)
   ```

2. ✅ Update all other files (5 files total):
   - `bengal/rendering/template_engine.py`
   - `bengal/cli/commands/project.py`
   - `bengal/autodoc/config.py`
   - `bengal/server/component_preview.py`
   - `bengal/utils/theme_resolution.py`

3. ✅ Remove from `pyproject.toml`:
   ```diff
   - "toml>=0.10.0",
   ```

4. ✅ Test: Run full test suite to ensure no breakage

**Outcome**: 1 less dependency, no behavior change

---

### Phase 2: Make python-markdown Optional (30 min)
**Target: Make alternative parser opt-in**

1. ✅ Move `markdown>=3.5.0` to optional dependencies
2. ✅ Update `bengal/rendering/parsers/__init__.py`:
   ```python
   def create_markdown_parser(engine: str | None = None) -> BaseMarkdownParser:
       """Create markdown parser based on engine name."""
       engine = engine or "mistune"

       if engine == "python-markdown":
           try:
               from bengal.rendering.parsers.python_markdown import PythonMarkdownParser
               return PythonMarkdownParser()
           except ImportError:
               raise ImportError(
                   "python-markdown parser not installed. "
                   "Install with: pip install bengal[markdown-alt]"
               )

       # Default to mistune
       from bengal.rendering.parsers.mistune import MistuneParser
       return MistuneParser()
   ```

3. ✅ Update config validation to warn about missing parser
4. ✅ Update documentation to explain parser options
5. ✅ Test both paths (with and without python-markdown)

**Outcome**: 107 KB saved, graceful degradation

---

### Phase 3: Make Image Features Optional (45 min)
**Target: Make pillow optional**

1. ✅ Move `pillow>=10.0.0` to `[images]` extra
2. ✅ Update `bengal/rendering/template_functions/images.py`:
   - Already has graceful fallback for `image_dimensions()`
   - Already has graceful fallback for `image_data_uri()`
   - No changes needed! ✨

3. ✅ Update `bengal/core/asset.py`:
   ```python
   def _optimize_image(self) -> None:
       """Optimize image assets."""
       try:
           from PIL import Image
           # ... existing code ...
       except ImportError:
           logger.debug(
               "pillow_not_installed",
               suggestion="Install with: pip install bengal[images]"
           )
           self.optimized = True  # Skip optimization
           return
   ```

4. ✅ Update documentation about image features
5. ✅ Test without pillow installed

**Outcome**: 4.7 MB saved! (biggest win)

---

### Phase 4: Make Minification Optional (30 min)
**Target: Make csscompressor + jsmin optional**

1. ✅ Move both to `[minify]` extra
2. ✅ Update `bengal/core/asset.py`:
   - `_minify_css()` already has fallback
   - `_minify_js()` already has fallback
   - Just improve error messages with install instructions

3. ✅ Update config to add `minify` option:
   ```toml
   [assets]
   minify = true  # Will warn if minifiers not installed
   ```

4. ✅ Add check at build start:
   ```python
   if config.get("assets", {}).get("minify") and not has_minifiers():
       logger.warning(
           "minification_disabled",
           reason="Minifiers not installed",
           install_command="pip install bengal[minify]"
       )
   ```

**Outcome**: Tiny (~10 KB) but cleaner dependency tree

---

### Phase 5: Make Performance Tools Optional (20 min)
**Target: Make psutil optional**

1. ✅ Move `psutil>=5.9.0` to `[perf]` extra
2. ✅ Already has graceful fallback in both files!
   - `performance_collector.py`: `HAS_PSUTIL = False` path works
   - `pid_manager.py`: Falls back to `os.kill()` checks

3. ✅ Update CLI to show install tip when memory stats unavailable:
   ```python
   if not HAS_PSUTIL:
       logger.info(
           "enhanced_metrics_unavailable",
           tip="Install psutil for memory tracking: pip install bengal[perf]"
       )
   ```

**Outcome**: Removes compiled dependency (psutil builds from source)

---

### Phase 6: Make Wizard Optional (15 min)
**Target: Make questionary optional**

1. ✅ Move `questionary>=2.0.0` to `[wizard]` extra
2. ✅ Already has fallback in `cli/commands/new.py`!
   ```python
   try:
       import questionary
   except ImportError:
       cli.warning("Install questionary for interactive prompts: pip install questionary")
       return None  # Falls back to basic mode
   ```

3. ✅ Just update the message:
   ```python
   cli.warning("Install questionary for interactive prompts: pip install bengal[wizard]")
   ```

**Outcome**: 36 KB + better prompts saved

---

## Testing Strategy

### Automated Tests
1. **Test matrix**: Run full test suite with different combinations:
   - Core only (no optional deps)
   - Core + server
   - Core + images
   - Core + full

2. **Import tests**: Verify graceful degradation
   ```python
   def test_missing_pillow_graceful():
       """Verify image functions work without pillow"""
       # Mock missing pillow
       with patch.dict('sys.modules', {'PIL': None}):
           result = image_dimensions('test.jpg', site.root_path)
           assert result is None  # Graceful return
   ```

3. **Build tests**: Run example builds with minimal deps

### Manual Testing
1. Fresh virtualenv with `pip install .`
2. Build example site without optional deps
3. Add optional deps one by one, verify features work

---

## Documentation Updates

### README.md
```markdown
## Installation

### Basic Installation
```bash
pip install bengal
```

### Optional Features

Install extra features as needed:

- **Development server with hot reload**: `pip install bengal[server]`
- **Image optimization**: `pip install bengal[images]`
- **CSS/JS minification**: `pip install bengal[minify]`
- **Performance monitoring**: `pip install bengal[perf]`
- **Interactive CLI wizard**: `pip install bengal[wizard]`
- **Alternative markdown parser**: `pip install bengal[markdown-alt]`
- **Everything**: `pip install bengal[full]`

### Feature Comparison

| Feature | Core | Extra Required |
|---------|------|----------------|
| Build static sites | ✅ | - |
| Markdown parsing (mistune) | ✅ | - |
| Jinja2 templates | ✅ | - |
| Syntax highlighting | ✅ | - |
| Development server | ❌ | `[server]` |
| Image optimization | ❌ | `[images]` |
| Asset minification | ❌ | `[minify]` |
| Memory profiling | ❌ | `[perf]` |
| Site creation wizard | ❌ | `[wizard]` |
```

### Getting Started Guide
- Add section explaining when you need which extras
- Example: "Building a docs site? Core is enough. Building a photography portfolio? Add `[images]`."

---

## Migration Guide (for existing users)

**Breaking Change Alert**: None for default users!

### If You Use Default Settings
No action needed! Your existing `pip install bengal` will continue to work.

### If You Use These Features

**Image optimization in templates:**
```bash
pip install bengal[images]
```

**Asset minification:**
```bash
pip install bengal[minify]
```

**Performance monitoring:**
```bash
pip install bengal[perf]
```

**Alternative markdown parser:**
```toml
# In bengal.toml
[markdown]
parser = "python-markdown"  # Instead of "mistune"
```
```bash
pip install bengal[markdown-alt]
```

---

## Rollout Strategy

### Version 0.2.0 (Next Release)
1. Mark as **minor version bump** (breaking for some)
2. Add **migration section** to changelog
3. Update **all documentation** before release
4. Add **deprecation warnings** in 0.1.x if possible

### Changelog Entry
```markdown
## [0.2.0] - 2025-XX-XX

### Changed - Dependency Optimization 📦
**Bengal is now 35% smaller and faster to install!**

We've reorganized dependencies to give you a leaner core installation.
Core SSG features work out of the box, advanced features are opt-in.

**Breaking Changes:**
- `pillow` is now optional (`pip install bengal[images]`)
- `psutil` is now optional (`pip install bengal[perf]`)
- `csscompressor` and `jsmin` are now optional (`pip install bengal[minify]`)
- `questionary` is now optional (`pip install bengal[wizard]`)
- `markdown` (python-markdown) is now optional (`pip install bengal[markdown-alt]`)
- `toml` removed (using stdlib `tomllib`)

**Migration:**
- Most users: No action needed
- If you use image optimization: `pip install bengal[images]`
- If you use asset minification: `pip install bengal[minify]`
- If you use python-markdown parser: `pip install bengal[markdown-alt]`
- For all features: `pip install bengal[full]`

**Benefits:**
- 35% smaller install size (~5 MB vs ~8 MB)
- 30% faster installation
- Fewer dependency conflicts
- Cleaner dependency tree
```

---

## Success Metrics

### Before (Current)
- Total packages: 20
- Total size: ~8 MB
- Install time: ~10s
- Dependencies with compilation: 1 (psutil)

### After (Target)
- Total packages: ~13 (core + transitive)
- Total size: ~5 MB
- Install time: ~7s
- Dependencies with compilation: 0

### Validation
- [ ] All tests pass with core-only install
- [ ] Example sites build successfully with core-only
- [ ] Optional features work when installed
- [ ] Error messages guide users to correct extras
- [ ] Documentation is comprehensive

---

## Risk Assessment

### Low Risk
- **toml → tomllib**: Direct replacement, Python 3.14+ guaranteed
- **Making questionary optional**: Already has fallback

### Medium Risk
- **Making pillow optional**: Used in 2 files, but both have fallbacks
- **Making python-markdown optional**: Changes default behavior for some users

### Mitigation
1. Comprehensive testing with all combinations
2. Clear migration guide in changelog
3. Helpful error messages with install instructions
4. Update documentation before release

---

## Alternative Considered

### Do Nothing
**Pros**: No work, no risk  
**Cons**: 20 dependencies is above average for SSGs, slower installs

### Make Everything Optional
**Pros**: Minimal core  
**Cons**: Bad UX, users confused about what to install

### Use Plugin System
**Pros**: Most flexible  
**Cons**: Way more complexity, not worth it for this scale

---

## Recommendation

**Proceed with phased approach** outlined above. Start with Phase 1 (toml removal) immediately as it's zero-risk. Then tackle Phase 2-6 for next release.

**Expected user reaction**: Positive! Faster installs, clearer features, modern Python usage.

**Timeline**:
- Phase 1: Today (15 min)
- Phase 2-6: Over 1-2 days
- Testing: 1 day
- Documentation: Half day
- **Total**: ~3-4 days of work

---

## Next Actions

1. Get approval for this plan
2. Start with Phase 1 (toml → tomllib)
3. Create feature branch: `feature/dependency-optimization`
4. Implement phases 2-6
5. Update all documentation
6. Run full test suite
7. Create PR with migration guide
8. Release as v0.2.0
