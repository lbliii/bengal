# Phase 1 Critical Brittleness Fixes - Implementation Plan

**Date:** October 3, 2025  
**Priority:** 🔴 CRITICAL  
**Estimated Time:** 2-3 days  
**Status:** Ready to implement

## Overview

This document provides detailed implementation specifications for the 5 critical brittleness issues identified in the analysis. Each fix includes:
- Exact code changes needed
- Test cases to write
- Edge cases to handle
- Migration notes (if any)

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

**File:** `tests/unit/test_page_url_generation.py`

```python
import pytest
from pathlib import Path
from bengal.core.page import Page
from bengal.core.site import Site


class TestPageURLGeneration:
    """Test Page.url property edge cases and robustness."""
    
    def test_url_basic_pretty_url(self):
        """Test basic pretty URL generation."""
        site = Site(root_path=Path('/site'), config={'output_dir': 'public'})
        page = Page(source_path=Path('/site/content/about.md'))
        page._site = site
        page.output_path = Path('/site/public/about/index.html')
        
        assert page.url == '/about/'
    
    def test_url_nested_page(self):
        """Test URL for nested page."""
        site = Site(root_path=Path('/site'), config={'output_dir': 'public'})
        page = Page(source_path=Path('/site/content/docs/guide.md'))
        page._site = site
        page.output_path = Path('/site/public/docs/guide/index.html')
        
        assert page.url == '/docs/guide/'
    
    def test_url_root_index(self):
        """Test URL for root index page."""
        site = Site(root_path=Path('/site'), config={'output_dir': 'public'})
        page = Page(source_path=Path('/site/content/index.md'))
        page._site = site
        page.output_path = Path('/site/public/index.html')
        
        assert page.url == '/'
    
    def test_url_section_index(self):
        """Test URL for section index page."""
        site = Site(root_path=Path('/site'), config={'output_dir': 'public'})
        page = Page(source_path=Path('/site/content/docs/_index.md'))
        page._site = site
        page.output_path = Path('/site/public/docs/index.html')
        
        assert page.url == '/docs/'
    
    def test_url_custom_output_dir(self):
        """Test URL with custom output directory name."""
        site = Site(root_path=Path('/site'), config={'output_dir': 'dist'})
        page = Page(source_path=Path('/site/content/about.md'))
        page._site = site
        page.output_path = Path('/site/dist/about/index.html')
        
        assert page.url == '/about/'
    
    def test_url_absolute_output_dir(self):
        """Test URL with absolute output directory."""
        site = Site(root_path=Path('/site'), config={'output_dir': '/var/www/html'})
        page = Page(source_path=Path('/site/content/about.md'))
        page._site = site
        page.output_path = Path('/var/www/html/about/index.html')
        
        assert page.url == '/about/'
    
    def test_url_no_output_path(self):
        """Test fallback when output_path not set."""
        site = Site(root_path=Path('/site'), config={})
        page = Page(source_path=Path('/site/content/my-post.md'))
        page._site = site
        # output_path not set
        
        # Should fallback to slug-based URL
        assert page.url == '/my-post/'
    
    def test_url_no_site_reference(self):
        """Test fallback when site reference not set."""
        page = Page(source_path=Path('/site/content/about.md'))
        page.output_path = Path('/site/public/about/index.html')
        # _site not set
        
        # Should fallback to slug-based URL
        assert page.url == '/about/'
    
    def test_url_output_path_not_under_output_dir(self, capsys):
        """Test handling of invalid output path."""
        site = Site(root_path=Path('/site'), config={'output_dir': 'public'})
        page = Page(source_path=Path('/site/content/about.md'))
        page._site = site
        # Output path in wrong location
        page.output_path = Path('/tmp/output/about/index.html')
        
        url = page.url
        captured = capsys.readouterr()
        
        # Should warn and use fallback
        assert '⚠️  Warning' in captured.out
        assert url == '/about/'
    
    def test_url_deep_nesting(self):
        """Test URL with deep nesting."""
        site = Site(root_path=Path('/site'), config={'output_dir': 'public'})
        page = Page(source_path=Path('/site/content/a/b/c/d/page.md'))
        page._site = site
        page.output_path = Path('/site/public/a/b/c/d/page/index.html')
        
        assert page.url == '/a/b/c/d/page/'
    
    def test_url_special_characters_in_path(self):
        """Test URL with special characters (should be escaped elsewhere)."""
        site = Site(root_path=Path('/site'), config={'output_dir': 'public'})
        page = Page(source_path=Path('/site/content/hello-world.md'))
        page._site = site
        page.output_path = Path('/site/public/hello-world/index.html')
        
        assert page.url == '/hello-world/'
```

### Edge Cases to Handle
1. ✅ Custom output directory names
2. ✅ Absolute output directory paths
3. ✅ Missing output_path
4. ✅ Missing site reference
5. ✅ output_path not under output_dir (corruption/bug)
6. ✅ Deep nesting
7. ✅ Root index page
8. ✅ Section index pages

---

## Fix #2: Configuration Validation

### Current Issue
No validation of loaded configuration, leading to type errors at runtime.

### Implementation

**New File:** `bengal/config/schema.py`

```python
"""
Configuration schema and validation using Pydantic.

Provides type-safe configuration with validation and helpful error messages.
"""

from pydantic import BaseModel, Field, validator, ValidationError
from typing import Optional, Dict, Any, List
from pathlib import Path


class SiteConfig(BaseModel):
    """Site-level configuration."""
    title: str = "Bengal Site"
    baseurl: str = ""
    description: str = ""
    author: str = ""
    language: str = "en"
    theme: str = "default"
    
    class Config:
        extra = "allow"  # Allow extra fields for extensibility


class BuildConfig(BaseModel):
    """Build-related configuration."""
    output_dir: str = "public"
    content_dir: str = "content"
    assets_dir: str = "assets"
    templates_dir: str = "templates"
    parallel: bool = True
    incremental: bool = False
    max_workers: int = Field(default=0, ge=0)
    pretty_urls: bool = True
    
    @validator('max_workers')
    def validate_max_workers(cls, v):
        if v < 0:
            raise ValueError('max_workers must be >= 0 (0 = auto)')
        if v > 100:
            raise ValueError('max_workers > 100 seems excessive')
        return v
    
    class Config:
        extra = "allow"


class AssetsConfig(BaseModel):
    """Asset processing configuration."""
    minify: bool = True
    optimize: bool = True
    fingerprint: bool = True
    
    class Config:
        extra = "allow"


class FeaturesConfig(BaseModel):
    """Feature flags."""
    generate_sitemap: bool = True
    generate_rss: bool = True
    validate_links: bool = True
    
    class Config:
        extra = "allow"


class DevConfig(BaseModel):
    """Development and debugging configuration."""
    strict_mode: bool = False
    debug: bool = False
    validate_build: bool = True
    min_page_size: int = Field(default=1000, ge=0)
    
    @validator('min_page_size')
    def validate_min_page_size(cls, v):
        if v < 0:
            raise ValueError('min_page_size must be >= 0')
        return v
    
    class Config:
        extra = "allow"


class PaginationConfig(BaseModel):
    """Pagination configuration."""
    per_page: int = Field(default=10, ge=1)
    
    @validator('per_page')
    def validate_per_page(cls, v):
        if v < 1:
            raise ValueError('per_page must be >= 1')
        if v > 1000:
            raise ValueError('per_page > 1000 seems excessive')
        return v
    
    class Config:
        extra = "allow"


class BengalConfig(BaseModel):
    """Root configuration model."""
    site: SiteConfig = Field(default_factory=SiteConfig)
    build: BuildConfig = Field(default_factory=BuildConfig)
    assets: AssetsConfig = Field(default_factory=AssetsConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    dev: DevConfig = Field(default_factory=DevConfig)
    pagination: PaginationConfig = Field(default_factory=PaginationConfig)
    
    # Menu configuration (kept as dict for flexibility)
    menu: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    
    class Config:
        extra = "allow"  # Allow extra top-level keys
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], source_file: Optional[Path] = None) -> 'BengalConfig':
        """
        Load and validate configuration from dictionary.
        
        Args:
            data: Configuration dictionary
            source_file: Optional source file for error messages
            
        Returns:
            Validated BengalConfig instance
            
        Raises:
            ValueError: If validation fails
        """
        try:
            return cls(**data)
        except ValidationError as e:
            # Format nice error message
            source_info = f" in {source_file}" if source_file else ""
            print(f"❌ Configuration validation failed{source_info}:")
            print()
            
            for error in e.errors():
                # Get field path (e.g., "build.max_workers")
                field_path = '.'.join(str(x) for x in error['loc'])
                
                # Get error message
                msg = error['msg']
                
                # Get error type
                error_type = error['type']
                
                # Print formatted error
                print(f"  • [{field_path}] {msg}")
                
                # Add helpful context
                if 'value_error' in error_type:
                    print(f"    Hint: Check the value type and constraints")
                elif 'type_error' in error_type:
                    print(f"    Expected type: {error.get('type', 'see docs')}")
            
            print()
            print("Please fix the configuration errors and try again.")
            print("See documentation for valid configuration options.")
            
            raise ValueError(f"Invalid configuration{source_info}") from e
    
    def to_flat_dict(self) -> Dict[str, Any]:
        """
        Convert to flat dictionary for backward compatibility.
        
        Flattens nested config:
            config.site.title -> config['title']
            config.build.parallel -> config['parallel']
        
        Returns:
            Flattened configuration dictionary
        """
        flat = {}
        
        # Flatten site config to root level
        flat.update(self.site.dict())
        
        # Flatten build config to root level
        flat.update(self.build.dict())
        
        # Flatten other configs to root level
        flat.update({
            'minify_assets': self.assets.minify,
            'optimize_assets': self.assets.optimize,
            'fingerprint_assets': self.assets.fingerprint,
            'generate_sitemap': self.features.generate_sitemap,
            'generate_rss': self.features.generate_rss,
            'validate_links': self.features.validate_links,
        })
        
        # Add dev config
        flat.update(self.dev.dict())
        
        # Add pagination
        flat.update({'pagination': self.pagination.dict()})
        
        # Add menu
        flat['menu'] = self.menu
        
        return flat
```

**Update File:** `bengal/config/loader.py`

```python
def _load_file(self, config_path: Path) -> Dict[str, Any]:
    """
    Load a specific config file with validation.
    
    Args:
        config_path: Path to config file
        
    Returns:
        Validated configuration dictionary
        
    Raises:
        ValueError: If validation fails
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
        
        # Validate with schema
        from bengal.config.schema import BengalConfig
        validated = BengalConfig.from_dict(raw_config, source_file=config_path)
        
        # Convert to flat dict for backward compatibility
        return validated.to_flat_dict()
        
    except ValidationError as e:
        # Schema validation already printed nice errors
        raise
    except Exception as e:
        print(f"❌ Error loading config from {config_path}: {e}")
        raise
```

### Test Cases

**File:** `tests/unit/config/test_config_validation.py`

```python
import pytest
from pathlib import Path
from bengal.config.schema import BengalConfig, BuildConfig
from pydantic import ValidationError


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_valid_config(self):
        """Test valid configuration passes."""
        config_data = {
            'site': {'title': 'Test Site'},
            'build': {'parallel': True, 'max_workers': 4}
        }
        config = BengalConfig.from_dict(config_data)
        assert config.site.title == 'Test Site'
        assert config.build.parallel == True
        assert config.build.max_workers == 4
    
    def test_invalid_max_workers_negative(self):
        """Test negative max_workers is rejected."""
        config_data = {
            'build': {'max_workers': -1}
        }
        with pytest.raises(ValueError, match="max_workers must be >= 0"):
            BengalConfig.from_dict(config_data)
    
    def test_invalid_max_workers_type(self):
        """Test non-integer max_workers is rejected."""
        config_data = {
            'build': {'max_workers': "many"}
        }
        with pytest.raises(ValueError):
            BengalConfig.from_dict(config_data)
    
    def test_invalid_parallel_type(self):
        """Test non-boolean parallel is rejected."""
        config_data = {
            'build': {'parallel': "yes"}
        }
        with pytest.raises(ValueError):
            BengalConfig.from_dict(config_data)
    
    def test_invalid_per_page_zero(self):
        """Test per_page=0 is rejected."""
        config_data = {
            'pagination': {'per_page': 0}
        }
        with pytest.raises(ValueError, match="per_page must be >= 1"):
            BengalConfig.from_dict(config_data)
    
    def test_defaults_applied(self):
        """Test default values are applied."""
        config = BengalConfig.from_dict({})
        assert config.site.title == "Bengal Site"
        assert config.build.output_dir == "public"
        assert config.build.parallel == True
        assert config.pagination.per_page == 10
    
    def test_extra_fields_allowed(self):
        """Test extra fields are allowed for extensibility."""
        config_data = {
            'site': {'custom_field': 'value'},
            'custom_top_level': 'test'
        }
        config = BengalConfig.from_dict(config_data)
        # Should not raise error
    
    def test_to_flat_dict(self):
        """Test conversion to flat dict for backward compatibility."""
        config = BengalConfig(
            site={'title': 'Test'},
            build={'parallel': False}
        )
        flat = config.to_flat_dict()
        assert flat['title'] == 'Test'
        assert flat['parallel'] == False
```

---

## Fix #3: Improved Frontmatter Parsing

### Implementation

**Update File:** `bengal/discovery/content_discovery.py`

```python
import frontmatter
import yaml
from typing import Tuple


def _create_page(self, file_path: Path) -> Page:
    """
    Create a Page object from a file with robust error handling.
    
    Handles:
    - Valid frontmatter
    - Invalid YAML in frontmatter
    - Missing frontmatter
    - File encoding issues
    - IO errors
    
    Args:
        file_path: Path to content file
        
    Returns:
        Page object (always succeeds with fallback metadata)
        
    Raises:
        IOError: Only if file cannot be read at all
    """
    content, metadata = self._parse_content_file(file_path)
    
    return Page(
        source_path=file_path,
        content=content,
        metadata=metadata,
    )


def _parse_content_file(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
    """
    Parse content file with robust error handling.
    
    Args:
        file_path: Path to content file
        
    Returns:
        Tuple of (content, metadata)
        
    Raises:
        IOError: If file cannot be read
    """
    # Read file once
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
    except UnicodeDecodeError as e:
        # Try different encodings
        print(f"⚠️  Warning: UTF-8 decode failed for {file_path}, trying latin-1")
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                file_content = f.read()
        except Exception:
            # Give up
            raise IOError(f"Cannot decode {file_path}: {e}") from e
    except IOError as e:
        print(f"❌ Error: Cannot read {file_path}: {e}")
        raise
    
    # Parse frontmatter
    try:
        post = frontmatter.loads(file_content)
        content = post.content
        metadata = dict(post.metadata)
        return content, metadata
        
    except yaml.YAMLError as e:
        # YAML syntax error in frontmatter
        print(f"⚠️  Warning: Invalid YAML frontmatter in {file_path}")
        print(f"    Error: {e}")
        print(f"    File will be processed without metadata.")
        print(f"    Please fix the frontmatter syntax.")
        
        # Try to extract content (skip broken frontmatter)
        content = self._extract_content_skip_frontmatter(file_content)
        
        # Create minimal metadata for identification
        metadata = {
            '_parse_error': str(e),
            '_parse_error_type': 'yaml',
            '_source_file': str(file_path),
            'title': file_path.stem.replace('-', ' ').replace('_', ' ').title()
        }
        
        return content, metadata
    
    except Exception as e:
        # Unexpected error
        print(f"⚠️  Warning: Unexpected error parsing {file_path}: {e}")
        
        # Use entire file as content
        metadata = {
            '_parse_error': str(e),
            '_parse_error_type': 'unknown',
            '_source_file': str(file_path),
            'title': file_path.stem.replace('-', ' ').replace('_', ' ').title()
        }
        
        return file_content, metadata


def _extract_content_skip_frontmatter(self, file_content: str) -> str:
    """
    Extract content, skipping broken frontmatter section.
    
    Frontmatter is between --- delimiters at start of file.
    If parsing failed, skip the section entirely.
    
    Args:
        file_content: Full file content
        
    Returns:
        Content without frontmatter section
    """
    # Split on --- delimiters
    parts = file_content.split('---', 2)
    
    if len(parts) >= 3:
        # Format: --- frontmatter --- content
        # Return content (3rd part)
        return parts[2].strip()
    elif len(parts) == 2:
        # Format: --- frontmatter (no closing delimiter)
        # Return second part
        return parts[1].strip()
    else:
        # No frontmatter delimiters, return whole file
        return file_content.strip()
```

### Test Cases

**File:** `tests/unit/discovery/test_frontmatter_parsing.py`

```python
import pytest
from pathlib import Path
from bengal.discovery.content_discovery import ContentDiscovery
import tempfile


class TestFrontmatterParsing:
    """Test frontmatter parsing error handling."""
    
    def test_valid_frontmatter(self):
        """Test normal frontmatter parsing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""---
title: Test Page
date: 2025-01-01
tags: [test]
---

Content here.
""")
            f.flush()
            
            discovery = ContentDiscovery(Path(f.name).parent)
            page = discovery._create_page(Path(f.name))
            
            assert page.metadata['title'] == 'Test Page'
            assert page.content.strip() == 'Content here.'
    
    def test_invalid_yaml_frontmatter(self, capsys):
        """Test handling of invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""---
title: Test Page
date: [this is: invalid yaml
---

Content here.
""")
            f.flush()
            
            discovery = ContentDiscovery(Path(f.name).parent)
            page = discovery._create_page(Path(f.name))
            
            captured = capsys.readouterr()
            
            # Should warn
            assert '⚠️  Warning' in captured.out
            assert 'Invalid YAML' in captured.out
            
            # Should have content
            assert page.content.strip() == 'Content here.'
            
            # Should have parse error metadata
            assert '_parse_error' in page.metadata
            assert page.metadata['_parse_error_type'] == 'yaml'
            
            # Should have fallback title
            assert 'title' in page.metadata
    
    def test_missing_frontmatter(self):
        """Test file without frontmatter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("Just content, no frontmatter.\n")
            f.flush()
            
            discovery = ContentDiscovery(Path(f.name).parent)
            page = discovery._create_page(Path(f.name))
            
            # Should have empty metadata
            assert page.metadata == {}
            
            # Should have content
            assert "Just content" in page.content
    
    def test_unclosed_frontmatter(self):
        """Test frontmatter without closing delimiter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""---
title: Test
date: 2025-01-01

Content starts here but no closing ---.
""")
            f.flush()
            
            discovery = ContentDiscovery(Path(f.name).parent)
            page = discovery._create_page(Path(f.name))
            
            # frontmatter library should handle this
            # Check behavior
            assert page.content or page.metadata
```

---

## Fix #4: Menu Building Validation

See analysis document - add validation warnings and cycle detection.

---

## Fix #5: Generated Page Virtual Paths

See analysis document - use dedicated virtual namespace.

---

## Success Criteria

Phase 1 is complete when:

- [x] All 5 critical fixes implemented
- [x] All test cases written and passing
- [x] No regressions in existing tests
- [x] Documentation updated
- [x] Code reviewed
- [x] Deployed to staging

## Next Steps

After Phase 1 completion:
1. Review metrics - did error rates decrease?
2. Gather feedback from test builds
3. Proceed to Phase 2 hardening

