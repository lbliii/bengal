# Test Coverage Audit Report
**Date:** October 12, 2025  
**Auditor:** AI Assistant  
**Context:** Tests were accidentally deleted in commit `7c00402` and restored in `0fa1d2d`

## Executive Summary

During the period when tests were missing (commits `7c00402` through `0fa1d2d`), **15 major features** were added to the codebase without accompanying tests. This audit identifies all untested functionality and provides a prioritized test implementation plan.

**Key Findings:**
- ✅ **Analysis modules**: All have tests (community_detection, page_rank, path_analysis, etc.)
- ❌ **Rendering features**: Data table directive and template functions lack tests
- ❌ **Utility modules**: 7 new utility modules without tests
- ❌ **CLI system**: Complete CLI scaffolding system lacks tests
- ❌ **Template system**: Jinja2 utilities and custom tests lack coverage

---

## Priority 1: Critical User-Facing Features

These features are directly used by end users and need comprehensive testing.

### 1.1 Data Table Directive & Template Function
**Files:**
- `bengal/rendering/plugins/directives/data_table.py` (390 lines)
- `bengal/rendering/template_functions/tables.py` (152 lines)

**Functionality:**
- Interactive data tables from YAML/CSV
- Filtering, sorting, searching
- Pagination control
- Error handling for missing files
- Column visibility configuration

**Test Requirements:**
- [ ] Parse YAML data files correctly
- [ ] Parse CSV data files correctly
- [ ] Handle missing files gracefully
- [ ] Generate correct table IDs
- [ ] Apply search/filter/sort options
- [ ] Render HTML with correct structure
- [ ] Handle file size limits (5MB)
- [ ] Parse pagination options (int or false)
- [ ] Filter columns correctly
- [ ] Template function integration
- [ ] Error messages display correctly

**Priority:** CRITICAL - Used in documentation and technical sites

---

### 1.2 CLI Scaffolding System
**Files:**
- `bengal/cli/commands/init.py` (529 lines)
- `bengal/cli/commands/new.py` (389 lines)
- `bengal/cli/templates/registry.py` (74 lines)
- `bengal/cli/templates/*/template.py` (7 template modules)

**Functionality:**
- `bengal init` - Initialize site structure with sections
- `bengal new` - Create new sites from templates
- Template discovery and registration
- Preset system (blog, docs, portfolio, etc.)
- Smart slugification
- Date staggering for blog posts
- Dry-run mode

**Test Requirements:**
- [ ] Template registry discovers all templates
- [ ] Template files are created correctly
- [ ] Slugify function handles edge cases
- [ ] Init wizard creates proper structure
- [ ] Preset configurations work correctly
- [ ] Date staggering for posts
- [ ] Weight calculations
- [ ] Dry-run mode doesn't write files
- [ ] Error handling for existing sites
- [ ] Config file generation
- [ ] Index page creation
- [ ] Multi-section initialization
- [ ] Sample content generation

**Priority:** CRITICAL - First experience for new users

---

### 1.3 Swizzle Manager
**Files:**
- `bengal/utils/swizzle.py` (289 lines)

**Functionality:**
- Copy theme templates to project for customization
- Track provenance in `.bengal/themes/sources.json`
- List swizzled files
- Detect modifications
- Auto-update unchanged files

**Test Requirements:**
- [ ] Copy template preserving relative path
- [ ] Create provenance records
- [ ] Calculate checksums correctly
- [ ] Detect local modifications
- [ ] List swizzled files
- [ ] Update unchanged files
- [ ] Handle missing source files
- [ ] JSON serialization/deserialization
- [ ] File system operations

**Priority:** HIGH - Important for theme customization

---

## Priority 2: Core Infrastructure

Essential utility modules that support multiple features.

### 2.1 DotDict Utility
**Files:**
- `bengal/utils/dotdict.py` (254 lines)

**Functionality:**
- Dictionary with dot notation access
- Solves Jinja2 method name collision issue
- Recursive wrapping with caching
- Dict-like interface without inheritance

**Test Requirements:**
- [ ] Basic dot notation access
- [ ] Bracket notation access
- [ ] Nested dict wrapping
- [ ] Cache performance for repeated access
- [ ] Method name collision handling (items, keys, values)
- [ ] Dict interface methods work correctly
- [ ] from_dict() recursive wrapping
- [ ] wrap_data() handles lists and dicts
- [ ] None handling in Jinja2 context
- [ ] AttributeError for missing keys
- [ ] Assignment and deletion operations

**Priority:** HIGH - Used in templates throughout the system

---

### 2.2 Jinja2 Utilities
**Files:**
- `bengal/rendering/jinja_utils.py` (153 lines)
- `bengal/rendering/template_tests.py` (149 lines)

**Functionality:**
- Safe attribute access with Undefined handling
- Custom Jinja2 tests (draft, featured, outdated, section, translated)
- Nested attribute retrieval
- Value checking utilities

**Test Requirements:**
- [ ] is_undefined() detects Undefined objects
- [ ] safe_get() handles missing attributes
- [ ] safe_get() handles Undefined values
- [ ] has_value() checks for truthy values
- [ ] safe_get_attr() traverses nested attributes
- [ ] ensure_defined() provides defaults
- [ ] test_draft() checks metadata
- [ ] test_featured() checks tags
- [ ] test_outdated() calculates date age
- [ ] test_section() type checking
- [ ] test_translated() checks translations

**Priority:** HIGH - Core template functionality

---

### 2.3 CLI Output System
**Files:**
- `bengal/utils/cli_output.py` (393 lines)
- `bengal/utils/build_summary.py` (434 lines)

**Functionality:**
- Profile-aware CLI output (Writer/Theme-Dev/Developer)
- Rich formatting with fallbacks
- Build phase reporting
- Performance dashboards
- Timing breakdowns
- Smart suggestions display

**Test Requirements:**
- [ ] Profile detection and configuration
- [ ] TTY detection
- [ ] Rich/plain fallback switching
- [ ] Message level filtering (quiet, verbose)
- [ ] Header formatting
- [ ] Phase line formatting with padding
- [ ] Success/error/warning styling
- [ ] Table rendering
- [ ] Path formatting based on profile
- [ ] Timing breakdown calculations
- [ ] Performance grade display
- [ ] Suggestions panel creation
- [ ] Cache statistics display

**Priority:** MEDIUM - Quality of life, but not blocking

---

### 2.4 Paths Utility
**Files:**
- `bengal/utils/paths.py` (123 lines)

**Functionality:**
- Consistent path management
- Profile directory creation
- Log directory management
- Cache path resolution
- Template cache directories

**Test Requirements:**
- [ ] get_profile_dir() creates directories
- [ ] get_log_dir() creates directories
- [ ] get_build_log_path() handles custom paths
- [ ] get_profile_path() with defaults
- [ ] get_cache_path() returns correct location
- [ ] get_template_cache_dir() creates structure

**Priority:** MEDIUM - Infrastructure support

---

### 2.5 Live Progress Utility
**Files:**
- `bengal/utils/live_progress.py` (size not checked)

**Functionality:**
- Real-time progress bars
- Status updates during builds
- Rich integration

**Test Requirements:**
- [ ] Progress bar creation
- [ ] Task tracking
- [ ] Live updates
- [ ] Completion handling
- [ ] Error display
- [ ] Context manager usage

**Priority:** LOW - Visual enhancement only

---

## Priority 3: Extended Features

Additional functionality that enhances the system but isn't critical.

### 3.1 Additional CLI Commands
**Files:**
- `bengal/cli/commands/assets.py`
- `bengal/cli/commands/graph.py`
- `bengal/cli/commands/perf.py`

**Note:** These were refactored during the period. Verify existing tests still cover all functionality.

**Test Requirements:**
- [ ] Verify asset command coverage
- [ ] Verify graph command coverage
- [ ] Verify perf command coverage

**Priority:** LOW - Verify only; likely already tested

---

## Testing Strategy

### Phase 1: Critical Path (Week 1)
1. Data table directive and template functions
2. CLI init command
3. CLI new command and template system
4. DotDict utility
5. Jinja2 utilities

### Phase 2: Infrastructure (Week 2)
1. Template tests (custom Jinja2 tests)
2. Swizzle manager
3. CLI output system
4. Paths utility

### Phase 3: Polish (Week 3)
1. Build summary dashboard
2. Live progress
3. Verify refactored commands

---

## Test Implementation Guidelines

### General Principles
1. **Unit tests first**: Test each function/method in isolation
2. **Integration tests**: Test feature workflows end-to-end
3. **Edge cases**: Invalid input, missing files, permission errors
4. **Fixtures**: Create reusable test data (YAML, CSV files)
5. **Mocking**: Mock file I/O, subprocess calls, external dependencies
6. **Parametrize**: Use pytest.mark.parametrize for similar test cases

### Coverage Goals
- **Unit tests**: 90%+ line coverage
- **Integration tests**: Cover all happy paths and major error paths
- **Edge cases**: At least 3 edge cases per function

### File Organization
```
tests/unit/
  ├── rendering/
  │   ├── test_data_table_directive.py  (NEW)
  │   └── test_jinja_utils.py           (NEW)
  ├── template_functions/
  │   └── test_tables.py                (NEW)
  ├── cli/
  │   ├── test_init_command.py          (NEW)
  │   ├── test_new_command.py           (NEW)
  │   └── test_template_registry.py     (NEW)
  └── utils/
      ├── test_dotdict.py               (NEW)
      ├── test_swizzle.py               (NEW)
      ├── test_cli_output.py            (NEW)
      ├── test_build_summary.py         (NEW)
      ├── test_paths.py                 (NEW)
      ├── test_live_progress.py         (NEW)
      └── test_template_tests.py        (NEW)

tests/integration/
  ├── test_data_table_full_workflow.py  (NEW)
  ├── test_init_wizard.py               (NEW)
  └── test_swizzle_workflow.py          (NEW)
```

---

## Estimated Effort

| Component | Test Files | Estimated Hours |
|-----------|-----------|----------------|
| Data table system | 3 | 16 |
| CLI scaffolding | 4 | 20 |
| DotDict | 1 | 4 |
| Jinja2 utilities | 2 | 8 |
| Swizzle manager | 2 | 12 |
| CLI output system | 2 | 10 |
| Paths utility | 1 | 3 |
| Live progress | 1 | 4 |
| Build summary | 1 | 6 |
| **TOTAL** | **17** | **83 hours** |

---

## Risk Assessment

### High Risk (No Tests)
- **Data table directive**: Used in production docs, complex parsing
- **CLI init/new**: First user experience, file system operations
- **DotDict**: Core template functionality, subtle bugs possible

### Medium Risk
- **Swizzle manager**: File operations, checksum tracking
- **Jinja2 utilities**: Template safety, undefined handling

### Low Risk
- **CLI output**: Cosmetic issues mainly
- **Paths utility**: Simple path management
- **Build summary**: Display only

---

## Next Steps

1. **Review this audit** with the team
2. **Prioritize** which features need tests first
3. **Create tracking issues** for each test file
4. **Assign ownership** to team members
5. **Set milestones** for completion
6. **Run coverage reports** after each phase

---

## Appendix: Commands to Verify Status

```bash
# Check test coverage
pytest --cov=bengal --cov-report=term-missing

# Run only new tests (when created)
pytest tests/unit/rendering/test_data_table_directive.py -v

# Check if modules are importable
python -c "from bengal.rendering.plugins.directives.data_table import DataTableDirective"

# Find all test files
find tests -name "test_*.py" -type f | sort

# Count lines needing tests
find bengal -name "*.py" -type f -exec wc -l {} + | sort -n
```

---

## Notes

- All analysis modules (community_detection, page_rank, etc.) already have good test coverage ✅
- The assets pipeline has tests ✅
- Theme registry has tests ✅
- Rich console has tests ✅
- Most changes were during major refactoring to support rich CLI output and component-based templates
- The commit `7c00402` introduced "macro components" which reorganized template partials
