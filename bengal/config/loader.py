"""
Configuration loader supporting TOML and YAML formats.
"""

from pathlib import Path
from typing import Any, Dict, Optional
import toml
import yaml


class ConfigLoader:
    """
    Loads site configuration from bengal.toml or bengal.yaml.
    """
    
    def __init__(self, root_path: Path) -> None:
        """
        Initialize the config loader.
        
        Args:
            root_path: Root directory to look for config files
        """
        self.root_path = root_path
    
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
        Load a specific config file.
        
        Args:
            config_path: Path to config file
            
        Returns:
            Configuration dictionary
        """
        suffix = config_path.suffix.lower()
        
        try:
            if suffix == '.toml':
                return self._load_toml(config_path)
            elif suffix in ('.yaml', '.yml'):
                return self._load_yaml(config_path)
            else:
                raise ValueError(f"Unsupported config format: {suffix}")
        except Exception as e:
            print(f"Error loading config from {config_path}: {e}")
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
        # Keep the original structure but also flatten for convenience
        flat = dict(config)
        
        # Extract common sections to top level
        if 'site' in config:
            for key, value in config['site'].items():
                if key not in flat:
                    flat[key] = value
        
        if 'build' in config:
            for key, value in config['build'].items():
                if key not in flat:
                    flat[key] = value
        
        # Preserve menu configuration (it's already in the right structure)
        # [[menu.main]] in TOML becomes {'menu': {'main': [...]}}
        if 'menu' not in flat and 'menu' in config:
            flat['menu'] = config['menu']
        
        return flat
    
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

