"""
Build profile system for persona-based observability.

Provides three profiles optimized for different user workflows:
- Writer: Fast, clean builds for content authors
- Theme Developer: Template-focused debugging for theme builders
- Developer: Full observability for framework contributors

Example:
    from bengal.utils.profile import BuildProfile
    
    profile = BuildProfile.from_cli_args(dev=True)
    config = profile.get_config()
    
    if config['track_memory']:
        # Enable memory tracking
        pass
"""

from enum import Enum
from typing import Dict, Any, List, Optional


class BuildProfile(Enum):
    """
    Build profiles for different user personas.
    
    Each profile optimizes observability features for a specific workflow:
    - WRITER: Content authors who want fast, clean builds
    - THEME_DEV: Theme developers who need template debugging
    - DEVELOPER: Framework contributors who need full observability
    """
    WRITER = "writer"
    THEME_DEV = "theme-dev"
    DEVELOPER = "dev"
    
    @classmethod
    def from_string(cls, value: str) -> 'BuildProfile':
        """
        Parse profile from string.
        
        Args:
            value: Profile name (case-insensitive)
            
        Returns:
            BuildProfile enum value
            
        Example:
            >>> BuildProfile.from_string("theme-dev")
            BuildProfile.THEME_DEV
        """
        if not value:
            return cls.WRITER
        
        mapping = {
            'writer': cls.WRITER,
            'theme-dev': cls.THEME_DEV,
            'theme_dev': cls.THEME_DEV,
            'dev': cls.DEVELOPER,
            'developer': cls.DEVELOPER,
            'debug': cls.DEVELOPER,  # Alias for backward compatibility
        }
        
        normalized = value.lower().strip()
        return mapping.get(normalized, cls.WRITER)
    
    @classmethod
    def from_cli_args(
        cls,
        profile: Optional[str] = None,
        dev: bool = False,
        theme_dev: bool = False,
        verbose: bool = False,
        debug: bool = False
    ) -> 'BuildProfile':
        """
        Determine profile from CLI arguments with proper precedence.
        
        Precedence (highest to lowest):
        1. --dev or --debug flags
        2. --theme-dev flag
        3. --profile option
        4. --verbose flag (legacy)
        5. Default (WRITER)
        
        Args:
            profile: Explicit profile name from --profile
            dev: --dev flag
            theme_dev: --theme-dev flag
            verbose: --verbose flag (legacy)
            debug: --debug flag (legacy)
            
        Returns:
            Determined BuildProfile
            
        Example:
            >>> BuildProfile.from_cli_args(dev=True)
            BuildProfile.DEVELOPER
            
            >>> BuildProfile.from_cli_args(verbose=True)
            BuildProfile.THEME_DEV
        """
        # Priority 1: Explicit dev/debug flags
        if dev or debug:
            return cls.DEVELOPER
        
        # Priority 2: Theme dev flag
        if theme_dev:
            return cls.THEME_DEV
        
        # Priority 3: Explicit profile option
        if profile:
            return cls.from_string(profile)
        
        # Priority 4: Legacy verbose flag
        if verbose:
            return cls.THEME_DEV
        
        # Priority 5: Default
        return cls.WRITER
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get configuration dictionary for this profile.
        
        Returns:
            Configuration with feature toggles for this profile
            
        Configuration keys:
            show_phase_timing: Show build phase timing
            track_memory: Enable memory profiling (tracemalloc + psutil)
            enable_debug_output: Print debug messages to stderr
            collect_metrics: Save metrics to .bengal-metrics/
            health_checks: Dict with enabled/disabled validator lists
            verbose_build_stats: Show detailed build statistics
        """
        if self == BuildProfile.WRITER:
            return {
                'show_phase_timing': False,
                'track_memory': False,
                'enable_debug_output': False,
                'collect_metrics': False,
                'health_checks': {
                    # Only run critical checks
                    'enabled': ['config', 'output', 'links'],
                    'disabled': [
                        'performance', 'cache', 'directives',
                        'rendering', 'navigation', 'menu', 'taxonomy'
                    ]
                },
                'verbose_build_stats': False,
            }
        elif self == BuildProfile.THEME_DEV:
            return {
                'show_phase_timing': True,
                'track_memory': False,
                'enable_debug_output': False,
                'collect_metrics': True,  # Basic timing metrics
                'health_checks': {
                    # Template and theme-focused checks
                    'enabled': [
                        'config', 'output', 'links', 'rendering',
                        'directives', 'navigation', 'menu'
                    ],
                    'disabled': ['performance', 'cache', 'taxonomy']
                },
                'verbose_build_stats': True,
            }
        else:  # DEVELOPER
            return {
                'show_phase_timing': True,
                'track_memory': True,
                'enable_debug_output': True,
                'collect_metrics': True,
                'health_checks': {
                    # Everything
                    'enabled': 'all',
                    'disabled': []
                },
                'verbose_build_stats': True,
            }
    
    def __str__(self) -> str:
        """String representation of profile."""
        return self.value


# Global state for current profile (set during build)
_current_profile: Optional[BuildProfile] = None


def set_current_profile(profile: BuildProfile) -> None:
    """
    Set the current build profile.
    
    This is used by helper functions to determine behavior without
    passing profile through every function call.
    
    Args:
        profile: BuildProfile to set as current
    """
    global _current_profile
    _current_profile = profile


def get_current_profile() -> BuildProfile:
    """
    Get the current build profile.
    
    Returns:
        Current profile, or WRITER if not set
    """
    return _current_profile or BuildProfile.WRITER


def should_show_debug() -> bool:
    """
    Check if debug output should be shown.
    
    This is a helper for conditional debug output without passing
    profile through every function.
    
    Returns:
        True if debug output should be shown
        
    Example:
        if should_show_debug():
            print(f"[Debug] Processing {item}", file=sys.stderr)
    """
    profile = get_current_profile()
    config = profile.get_config()
    return config.get('enable_debug_output', False)


def should_track_memory() -> bool:
    """
    Check if memory tracking should be enabled.
    
    Returns:
        True if memory should be tracked
    """
    profile = get_current_profile()
    config = profile.get_config()
    return config.get('track_memory', False)


def should_collect_metrics() -> bool:
    """
    Check if metrics collection should be enabled.
    
    Returns:
        True if metrics should be collected
    """
    profile = get_current_profile()
    config = profile.get_config()
    return config.get('collect_metrics', False)


def get_enabled_health_checks() -> List[str]:
    """
    Get list of enabled health check validators for current profile.
    
    Returns:
        List of validator names that should run, or 'all' string
        
    Example:
        >>> get_enabled_health_checks()
        ['config', 'output', 'links']
    """
    profile = get_current_profile()
    config = profile.get_config()
    health_config = config.get('health_checks', {})
    enabled = health_config.get('enabled', [])
    
    # Return 'all' as a list with single element for easier checking
    if enabled == 'all':
        return ['all']
    
    return enabled


def is_validator_enabled(validator_name: str) -> bool:
    """
    Check if a specific validator should run.
    
    Args:
        validator_name: Name of validator (e.g., 'config', 'links')
        
    Returns:
        True if validator should run
        
    Example:
        >>> is_validator_enabled('performance')
        False  # In writer mode
    """
    enabled = get_enabled_health_checks()
    
    # If 'all' is in the list, everything is enabled
    if 'all' in enabled:
        return True
    
    # Normalize validator name (handle spaces and case)
    normalized = validator_name.lower().replace(' ', '_')
    enabled_normalized = [v.lower().replace(' ', '_') for v in enabled]
    
    return normalized in enabled_normalized

