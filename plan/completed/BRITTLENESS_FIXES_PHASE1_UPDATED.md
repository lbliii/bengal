# Phase 1 Critical Brittleness Fixes - Implementation Plan (Updated)

**Date:** October 3, 2025  
**Priority:** 🔴 CRITICAL  
**Estimated Time:** 2-3 days  
**Status:** Ready to implement  
**Architecture:** ✅ Aligned with minimal dependencies & single-responsibility principles

## Overview

This document provides detailed implementation specifications for the 5 critical brittleness issues identified in the analysis. Each fix includes:
- Exact code changes needed
- Test cases to write
- Edge cases to handle
- Migration notes (if any)

**Important:** All fixes maintain Bengal's architectural principles:
- ✅ No god objects
- ✅ Single responsibility
- ✅ Minimal dependencies (no Pydantic - using lightweight validation)
- ✅ Modular design

---

## Fix #1: Robust URL Generation

### Current Issue
`Page.url` property uses hardcoded output directory names and fragile path parsing.

### Implementation

**File:** `bengal/core/page.py`

```python
@property
def url(self) -> str:
    """
    Get the URL path for the page.
    
    Generates clean URLs from output paths, handling:
    - Pretty URLs (about/index.html -> /about/)
    - Index pages (docs/index.html -> /docs/)
    - Root index (index.html -> /)
    - Edge cases (missing site reference, invalid paths)
    
    Returns:
        URL path with leading and trailing slashes
    """
    # Fallback if no output path set
    if not self.output_path:
        return self._fallback_url()
    
    # Need site reference to compute relative path
    if not self._site:
        return self._fallback_url()
    
    try:
        # Compute relative path from actual output directory
        rel_path = self.output_path.relative_to(self._site.output_dir)
    except ValueError:
        # output_path not under output_dir - should never happen
        # but handle gracefully with warning
        print(f"⚠️  Warning: Page output path {self.output_path} "
              f"is not under output directory {self._site.output_dir}")
        return self._fallback_url()
    
    # Convert Path to URL components
    url_parts = list(rel_path.parts)
    
    # Remove 'index.html' from end (it's implicit in URLs)
    if url_parts and url_parts[-1] == 'index.html':
        url_parts = url_parts[:-1]
    elif url_parts and url_parts[-1].endswith('.html'):
        # For non-index pages, remove .html extension
        # e.g., about.html -> about
        url_parts[-1] = url_parts[-1][:-5]
    
    # Construct URL with leading and trailing slashes
    if not url_parts:
        # Root index page
        return '/'
    
    url = '/' + '/'.join(url_parts)
    
    # Ensure trailing slash for directory-like URLs
    if not url.endswith('/'):
        url += '/'
    
    return url

def _fallback_url(self) -> str:
    """
    Generate fallback URL when output_path or site not available.
    
    Used during page construction before output_path is determined.
    
    Returns:
        URL based on slug
    """
    return f"/{self.slug}/"
```

### Test Cases
*(See original plan for full test suite)*

---

## Fix #2: Configuration Validation (Lightweight Approach)

### Current Issue
No validation of loaded configuration, leading to type errors at runtime.

### Implementation

**New File:** `bengal/config/validators.py`

```python
"""
Configuration validation without external dependencies.

Provides type-safe configuration validation with helpful error messages,
following Bengal's minimal dependencies and single-responsibility principles.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path


class ConfigValidationError(ValueError):
    """Raised when configuration validation fails."""
    pass


class ConfigValidator:
    """
    Validates configuration with helpful error messages.
    
    Single-responsibility validator class that checks:
    - Type correctness (bool, int, str)
    - Value ranges (min/max)
    - Required fields
    - Type coercion where sensible
    """
    
    # Define expected types for known fields
    BOOLEAN_FIELDS = {
        'parallel', 'incremental', 'pretty_urls', 
        'minify', 'optimize', 'fingerprint',
        'minify_assets', 'optimize_assets', 'fingerprint_assets',
        'generate_sitemap', 'generate_rss', 'validate_links',
        'strict_mode', 'debug', 'validate_build'
    }
    
    INTEGER_FIELDS = {
        'max_workers', 'min_page_size', 'port'
    }
    
    STRING_FIELDS = {
        'title', 'baseurl', 'description', 'author', 'language', 'theme',
        'output_dir', 'content_dir', 'assets_dir', 'templates_dir', 'host'
    }
    
    def validate(self, config: Dict[str, Any], source_file: Optional[Path] = None) -> Dict[str, Any]:
        """
        Validate configuration and return normalized version.
        
        Args:
            config: Raw configuration dictionary
            source_file: Optional source file for error context
            
        Returns:
            Validated and normalized configuration
            
        Raises:
            ConfigValidationError: If validation fails
        """
        errors = []
        
        # Flatten nested config if present (support both flat and nested)
        flat_config = self._flatten_config(config)
        
        # Validate and coerce types
        errors.extend(self._validate_types(flat_config))
        
        # Validate ranges
        errors.extend(self._validate_ranges(flat_config))
        
        # Validate dependencies
        errors.extend(self._validate_dependencies(flat_config))
        
        if errors:
            self._print_errors(errors, source_file)
            raise ConfigValidationError(f"{len(errors)} validation error(s)")
        
        return flat_config
    
    def _flatten_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten nested configuration for validation.
        
        Supports both:
        - Flat: {parallel: true, title: "Site"}
        - Nested: {build: {parallel: true}, site: {title: "Site"}}
        """
        flat = {}
        
        for key, value in config.items():
            if key in ('site', 'build', 'assets', 'features', 'dev') and isinstance(value, dict):
                # Nested section - merge to root
                flat.update(value)
            else:
                # Already flat or special key (menu, etc)
                flat[key] = value
        
        # Handle special asset fields (assets.minify -> minify_assets)
        if 'assets' in config and isinstance(config['assets'], dict):
            for k, v in config['assets'].items():
                flat[f"{k}_assets"] = v
        
        # Handle pagination
        if 'pagination' in config and isinstance(config['pagination'], dict):
            flat['pagination'] = config['pagination']
        
        return flat
    
    def _validate_types(self, config: Dict[str, Any]) -> List[str]:
        """Validate and coerce config value types."""
        errors = []
        
        # Boolean fields
        for key in self.BOOLEAN_FIELDS:
            if key in config:
                value = config[key]
                
                if isinstance(value, bool):
                    continue  # Already correct
                elif isinstance(value, str):
                    # Coerce string to boolean
                    lower_val = value.lower()
                    if lower_val in ('true', 'yes', '1', 'on'):
                        config[key] = True
                    elif lower_val in ('false', 'no', '0', 'off'):
                        config[key] = False
                    else:
                        errors.append(
                            f"'{key}': expected boolean or 'true'/'false', got '{value}'"
                        )
                elif isinstance(value, int):
                    # Coerce int to boolean (0=False, non-zero=True)
                    config[key] = bool(value)
                else:
                    errors.append(
                        f"'{key}': expected boolean, got {type(value).__name__}"
                    )
        
        # Integer fields
        for key in self.INTEGER_FIELDS:
            if key in config:
                value = config[key]
                
                if isinstance(value, int):
                    continue  # Already correct
                elif isinstance(value, str):
                    # Try to coerce string to int
                    try:
                        config[key] = int(value)
                    except ValueError:
                        errors.append(
                            f"'{key}': expected integer, got non-numeric string '{value}'"
                        )
                else:
                    errors.append(
                        f"'{key}': expected integer, got {type(value).__name__}"
                    )
        
        # String fields (mostly for type checking, less coercion needed)
        for key in self.STRING_FIELDS:
            if key in config:
                value = config[key]
                if not isinstance(value, str):
                    # Coerce to string if not already
                    config[key] = str(value)
        
        return errors
    
    def _validate_ranges(self, config: Dict[str, Any]) -> List[str]:
        """Validate numeric ranges."""
        errors = []
        
        # max_workers: must be >= 0
        max_workers = config.get('max_workers')
        if max_workers is not None and isinstance(max_workers, int):
            if max_workers < 0:
                errors.append("'max_workers': must be >= 0 (0 = auto-detect)")
            elif max_workers > 100:
                errors.append("'max_workers': value > 100 seems excessive, is this intentional?")
        
        # min_page_size: must be >= 0
        min_page_size = config.get('min_page_size')
        if min_page_size is not None and isinstance(min_page_size, int):
            if min_page_size < 0:
                errors.append("'min_page_size': must be >= 0")
        
        # Pagination per_page
        pagination = config.get('pagination', {})
        if isinstance(pagination, dict):
            per_page = pagination.get('per_page')
            if per_page is not None:
                if not isinstance(per_page, int):
                    errors.append("'pagination.per_page': must be integer")
                elif per_page < 1:
                    errors.append("'pagination.per_page': must be >= 1")
                elif per_page > 1000:
                    errors.append("'pagination.per_page': value > 1000 seems excessive")
        
        # Port number
        port = config.get('port')
        if port is not None and isinstance(port, int):
            if port < 1 or port > 65535:
                errors.append("'port': must be between 1 and 65535")
        
        return errors
    
    def _validate_dependencies(self, config: Dict[str, Any]) -> List[str]:
        """Validate field dependencies and logical consistency."""
        errors = []
        
        # Future: Add dependency validation here
        # Example: if incremental, ensure cache location is valid
        
        return errors
    
    def _print_errors(self, errors: List[str], source_file: Optional[Path] = None) -> None:
        """Print formatted validation errors."""
        source_info = f" in {source_file}" if source_file else ""
        print(f"\n❌ Configuration validation failed{source_info}:")
        print()
        
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
        
        print()
        print("Please fix the configuration errors and try again.")
        print("See documentation for valid configuration options.")
        print()
```

**Update File:** `bengal/config/loader.py`

Add validation call in `_load_file` method:

```python
def _load_file(self, config_path: Path) -> Dict[str, Any]:
    """
    Load a specific config file with validation.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Validated configuration dictionary
        
    Raises:
        ConfigValidationError: If validation fails
    """
    suffix = config_path.suffix.lower()
    
    try:
        # Load raw config
        if suffix == '.toml':
            raw_config = self._load_toml(config_path)
        elif suffix in ('.yaml', '.yml'):
            raw_config = self._load_yaml(config_path)
        else:
            raise ValueError(f"Unsupported config format: {suffix}")
        
        # Validate with lightweight validator
        from bengal.config.validators import ConfigValidator
        validator = ConfigValidator()
        validated_config = validator.validate(raw_config, source_file=config_path)
        
        return validated_config
        
    except Exception as e:
        # ConfigValidationError already printed errors
        if not isinstance(e, ConfigValidationError):
            print(f"❌ Error loading config from {config_path}: {e}")
        raise
```

### Test Cases

**File:** `tests/unit/config/test_config_validation.py`

```python
import pytest
from pathlib import Path
from bengal.config.validators import ConfigValidator, ConfigValidationError


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_valid_config(self):
        """Test valid configuration passes."""
        validator = ConfigValidator()
        config = {
            'title': 'Test Site',
            'parallel': True,
            'max_workers': 4
        }
        result = validator.validate(config)
        assert result['title'] == 'Test Site'
        assert result['parallel'] == True
        assert result['max_workers'] == 4
    
    def test_boolean_coercion_string(self):
        """Test string to boolean coercion."""
        validator = ConfigValidator()
        config = {'parallel': 'true', 'debug': 'false'}
        result = validator.validate(config)
        assert result['parallel'] is True
        assert result['debug'] is False
    
    def test_boolean_coercion_int(self):
        """Test int to boolean coercion."""
        validator = ConfigValidator()
        config = {'parallel': 1, 'debug': 0}
        result = validator.validate(config)
        assert result['parallel'] is True
        assert result['debug'] is False
    
    def test_integer_coercion_string(self):
        """Test string to integer coercion."""
        validator = ConfigValidator()
        config = {'max_workers': '8'}
        result = validator.validate(config)
        assert result['max_workers'] == 8
        assert isinstance(result['max_workers'], int)
    
    def test_invalid_boolean_string(self):
        """Test invalid boolean string is rejected."""
        validator = ConfigValidator()
        config = {'parallel': 'maybe'}
        with pytest.raises(ConfigValidationError):
            validator.validate(config)
    
    def test_invalid_integer_string(self):
        """Test invalid integer string is rejected."""
        validator = ConfigValidator()
        config = {'max_workers': 'many'}
        with pytest.raises(ConfigValidationError):
            validator.validate(config)
    
    def test_negative_max_workers(self):
        """Test negative max_workers is rejected."""
        validator = ConfigValidator()
        config = {'max_workers': -1}
        with pytest.raises(ConfigValidationError):
            validator.validate(config)
    
    def test_invalid_port_range(self):
        """Test invalid port range is rejected."""
        validator = ConfigValidator()
        config = {'port': 99999}
        with pytest.raises(ConfigValidationError):
            validator.validate(config)
    
    def test_nested_config_flattening(self):
        """Test nested config is flattened correctly."""
        validator = ConfigValidator()
        config = {
            'site': {'title': 'Test'},
            'build': {'parallel': True}
        }
        result = validator.validate(config)
        assert result['title'] == 'Test'
        assert result['parallel'] is True
```

---

## Fix #3: Improved Frontmatter Parsing

*(Implementation same as in original plan - no dependencies, pure Python)*

---

## Fix #4: Menu Building Validation

*(Implementation same as in original plan - validation within MenuBuilder)*

---

## Fix #5: Generated Page Virtual Paths

*(Implementation same as in original plan - namespace isolation)*

---

## Architectural Alignment

### ✅ Single Responsibility
- `ConfigValidator`: Only validates configuration
- `Page.url`: Only computes URLs
- `ContentDiscovery._parse_content_file`: Only parses files
- `MenuBuilder._has_cycle`: Only detects cycles

### ✅ No God Objects
- Each validator is focused and modular
- No single class tries to do everything
- Clear separation of concerns

### ✅ Minimal Dependencies
- No Pydantic required
- No external validation libraries
- Pure Python implementation
- Uses only stdlib (typing, pathlib)

### ✅ Composition Over Inheritance
- Validators used via composition
- No complex inheritance hierarchies
- Clear interfaces

---

## Success Criteria

Phase 1 is complete when:

- [ ] All 5 critical fixes implemented
- [ ] All test cases written and passing
- [ ] No regressions in existing tests
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] No new dependencies added ✅

## Next Steps

After Phase 1 completion:
1. Review metrics - did error rates decrease?
2. Gather feedback from test builds
3. Proceed to Phase 2 hardening

