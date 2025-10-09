"""
Configuration validation without external dependencies.

Provides type-safe configuration validation with helpful error messages,
following Bengal's minimal dependencies and single-responsibility principles.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

from bengal.utils.logger import get_logger

logger = get_logger(__name__)


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
        
        # Log for observability
        logger.error("config_validation_failed",
                    error_count=len(errors),
                    source_file=str(source_file) if source_file else None,
                    errors=errors)
        
        # Print for user visibility (part of CLI UX)
        print(f"\n❌ Configuration validation failed{source_info}:")
        print()
        
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
        
        print()
        print("Please fix the configuration errors and try again.")
        print("See documentation for valid configuration options.")
        print()

