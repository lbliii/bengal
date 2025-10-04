"""
Configuration loader supporting TOML and YAML formats.
"""

from pathlib import Path
from typing import Any, Dict, Optional, List
import difflib
import toml
import yaml


class ConfigLoader:
    """
    Loads site configuration from bengal.toml or bengal.yaml.
    """
    
    # Section aliases for ergonomic config (accept common variations)
    SECTION_ALIASES = {
        'menus': 'menu',        # Plural → singular
        'plugin': 'plugins',    # Singular → plural (if we add plugins)
    }
    
    # Known valid section names
    KNOWN_SECTIONS = {
        'site', 'build', 'markdown', 'features', 'taxonomies',
        'menu', 'params', 'assets', 'pagination', 'dev', 
        'output_formats', 'health_check'
    }
    
    def __init__(self, root_path: Path) -> None:
        """
        Initialize the config loader.
        
        Args:
            root_path: Root directory to look for config files
        """
        self.root_path = root_path
        self.warnings: List[str] = []
    
    def load(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Args:
            config_path: Optional explicit path to config file
            
        Returns:
            Configuration dictionary
        """
        if config_path:
            return self._load_file(config_path)
        
        # Try to find config file automatically
        for filename in ['bengal.toml', 'bengal.yaml', 'bengal.yml']:
            config_file = self.root_path / filename
            if config_file.exists():
                return self._load_file(config_file)
        
        # Return default config if no file found
        print("Warning: No configuration file found, using defaults")
        return self._default_config()
    
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
        from bengal.config.validators import ConfigValidator, ConfigValidationError
        
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
            validator = ConfigValidator()
            validated_config = validator.validate(raw_config, source_file=config_path)
            
            return validated_config
            
        except ConfigValidationError:
            # Validation error already printed nice errors
            raise
        except Exception as e:
            print(f"❌ Error loading config from {config_path}: {e}")
            return self._default_config()
    
    def _load_toml(self, config_path: Path) -> Dict[str, Any]:
        """
        Load TOML configuration file.
        
        Args:
            config_path: Path to TOML file
            
        Returns:
            Configuration dictionary
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = toml.load(f)
        
        return self._flatten_config(config)
    
    def _load_yaml(self, config_path: Path) -> Dict[str, Any]:
        """
        Load YAML configuration file.
        
        Args:
            config_path: Path to YAML file
            
        Returns:
            Configuration dictionary
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return self._flatten_config(config or {})
    
    def _flatten_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten nested config structure for easier access.
        
        Args:
            config: Nested configuration dictionary
            
        Returns:
            Flattened configuration (sections are preserved but accessible at top level too)
        """
        # First, normalize section names (accept aliases)
        normalized = self._normalize_sections(config)
        
        # Keep the original structure but also flatten for convenience
        flat = dict(normalized)
        
        # Extract common sections to top level
        if 'site' in normalized:
            for key, value in normalized['site'].items():
                if key not in flat:
                    flat[key] = value
        
        if 'build' in normalized:
            for key, value in normalized['build'].items():
                if key not in flat:
                    flat[key] = value
        
        # Preserve menu configuration (it's already in the right structure)
        # [[menu.main]] in TOML becomes {'menu': {'main': [...]}}
        if 'menu' not in flat and 'menu' in normalized:
            flat['menu'] = normalized['menu']
        
        return flat
    
    def _normalize_sections(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize config section names using aliases.
        
        Accepts common variations like [menus] → [menu].
        Warns about unknown sections.
        
        Args:
            config: Raw configuration dictionary
            
        Returns:
            Normalized configuration with canonical section names
        """
        normalized = {}
        
        for key, value in config.items():
            # Check if this is an alias
            canonical = self.SECTION_ALIASES.get(key)
            
            if canonical:
                # Using an alias - normalize it
                if canonical in normalized:
                    # Both forms present - merge if possible
                    if isinstance(value, dict) and isinstance(normalized[canonical], dict):
                        normalized[canonical].update(value)
                        self.warnings.append(
                            f"⚠️  Both [{key}] and [{canonical}] defined. Merging into [{canonical}]."
                        )
                    else:
                        self.warnings.append(
                            f"⚠️  Both [{key}] and [{canonical}] defined. Using [{canonical}]."
                        )
                else:
                    normalized[canonical] = value
                    self.warnings.append(
                        f"💡 Config note: [{key}] works, but [{canonical}] is preferred for consistency"
                    )
            elif key not in self.KNOWN_SECTIONS:
                # Unknown section - check for typos
                suggestions = difflib.get_close_matches(key, self.KNOWN_SECTIONS, n=1, cutoff=0.6)
                if suggestions:
                    self.warnings.append(
                        f"⚠️  Unknown section [{key}]. Did you mean [{suggestions[0]}]?"
                    )
                # Still include it (might be user-defined)
                normalized[key] = value
            else:
                # Known canonical section
                normalized[key] = value
        
        return normalized
    
    def get_warnings(self) -> List[str]:
        """Get configuration warnings (aliases used, unknown sections, etc)."""
        return self.warnings
    
    def print_warnings(self, verbose: bool = False) -> None:
        """Print configuration warnings if verbose mode is enabled."""
        if verbose and self.warnings:
            for warning in self.warnings:
                print(warning)
    
    def _default_config(self) -> Dict[str, Any]:
        """
        Get default configuration.
        
        Returns:
            Default configuration dictionary
        """
        return {
            'title': 'Bengal Site',
            'baseurl': '',
            'theme': 'default',
            'output_dir': 'public',
            'content_dir': 'content',
            'assets_dir': 'assets',
            'templates_dir': 'templates',
            'parallel': True,
            'incremental': False,
            'max_workers': 4,
            'pretty_urls': True,
            'minify_assets': True,
            'optimize_assets': True,
            'fingerprint_assets': True,
            'generate_sitemap': True,
            'generate_rss': True,
            'validate_links': True,
            # Debug and validation options
            'strict_mode': False,       # Fail on template errors instead of fallback
            'debug': False,             # Show verbose debug output and tracebacks
            'validate_build': True,     # Run post-build health checks
            'min_page_size': 1000,      # Minimum expected page size in bytes
        }

