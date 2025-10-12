# Tests Needed - Quick Checklist

This is a quick reference for what test files need to be created.

## Priority 1: Critical User-Facing Features

### Rendering Features
- [ ] `tests/unit/rendering/test_data_table_directive.py`
  - Test YAML parsing
  - Test CSV parsing
  - Test error handling
  - Test option parsing
  - Test HTML rendering

- [ ] `tests/unit/template_functions/test_tables.py`
  - Test data_table() function
  - Test integration with directive
  - Test error messages

- [ ] `tests/integration/test_data_table_workflow.py`
  - End-to-end data table rendering
  - Test with real files

### CLI Commands
- [ ] `tests/unit/cli/test_init_command.py`
  - Test section creation
  - Test slugify function
  - Test dry-run mode
  - Test sample content generation
  - Test date staggering

- [ ] `tests/unit/cli/test_new_command.py`
  - Test site creation
  - Test preset system
  - Test wizard flow
  - Test template selection

- [ ] `tests/unit/cli/test_template_registry.py`
  - Test template discovery
  - Test get_template()
  - Test list_templates()
  - Test registration

- [ ] `tests/integration/test_init_wizard.py`
  - Full init workflow
  - Multiple sections
  - Config generation

### Swizzle System
- [ ] `tests/unit/utils/test_swizzle.py`
  - Test swizzle()
  - Test provenance tracking
  - Test checksum calculation
  - Test modification detection
  - Test list_swizzled()
  - Test update logic

- [ ] `tests/integration/test_swizzle_workflow.py`
  - Full swizzle workflow
  - Update scenarios

## Priority 2: Core Infrastructure

### Utilities
- [ ] `tests/unit/utils/test_dotdict.py`
  - Test dot notation access
  - Test bracket notation
  - Test nested wrapping
  - Test caching
  - Test method name collisions
  - Test from_dict()
  - Test wrap_data()

- [ ] `tests/unit/rendering/test_jinja_utils.py`
  - Test is_undefined()
  - Test safe_get()
  - Test has_value()
  - Test safe_get_attr()
  - Test ensure_defined()

- [ ] `tests/unit/rendering/test_template_tests.py`
  - Test test_draft()
  - Test test_featured()
  - Test test_outdated()
  - Test test_section()
  - Test test_translated()
  - Test registration with Jinja2

- [ ] `tests/unit/utils/test_cli_output.py`
  - Test CLIOutput class
  - Test message levels
  - Test profile awareness
  - Test rich/plain fallback
  - Test formatting functions

- [ ] `tests/unit/utils/test_build_summary.py`
  - Test timing breakdown table
  - Test performance panel
  - Test suggestions panel
  - Test cache stats panel
  - Test content stats table

- [ ] `tests/unit/utils/test_paths.py`
  - Test get_profile_dir()
  - Test get_log_dir()
  - Test get_build_log_path()
  - Test get_cache_path()
  - Test get_template_cache_dir()

- [ ] `tests/unit/utils/test_live_progress.py`
  - Test progress bar creation
  - Test task tracking
  - Test context manager

## Summary

**Total new test files needed:** 17
**Estimated effort:** ~83 hours
**Critical path items:** 10 test files

## Commands to Run

```bash
# After creating tests, check coverage
pytest tests/unit/rendering/test_data_table_directive.py --cov=bengal.rendering.plugins.directives.data_table --cov-report=term-missing

# Run all new tests
pytest tests/unit/cli/ tests/unit/utils/test_dotdict.py tests/unit/rendering/test_jinja_utils.py -v

# Check overall coverage
pytest --cov=bengal --cov-report=html
```

## Priority Order for Implementation

1. `test_dotdict.py` - Quick win, core functionality
2. `test_jinja_utils.py` - Core template safety
3. `test_data_table_directive.py` - Major feature
4. `test_tables.py` - Completes data table feature
5. `test_init_command.py` - User experience
6. `test_new_command.py` - User experience
7. `test_template_registry.py` - CLI infrastructure
8. `test_template_tests.py` - Template features
9. `test_swizzle.py` - Theme customization
10. `test_cli_output.py` - Nice to have
11. Rest as time permits
