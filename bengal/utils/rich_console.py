"""
Rich console wrapper with profile-aware output.

Provides a singleton console instance that respects:
- Build profiles (Writer/Theme-Dev/Developer)
- Terminal capabilities
- CI/CD environments
"""

import os

from rich.console import Console
from rich.theme import Theme

# Bengal theme
bengal_theme = Theme({
    'info': 'cyan',
    'success': 'green',
    'warning': 'yellow',
    'error': 'red bold',
    'highlight': 'magenta bold',
    'dim': 'dim',
    'bengal': 'yellow bold',  # For the cat mascot
})

_console: Console | None = None


def get_console() -> Console:
    """
    Get singleton rich console instance.
    
    Returns:
        Configured Console instance
    """
    global _console
    
    if _console is None:
        # Detect environment
        force_terminal = None
        no_color = os.getenv('NO_COLOR') is not None
        ci_mode = os.getenv('CI') is not None
        
        if ci_mode:
            # In CI, force simple output
            force_terminal = False
        
        _console = Console(
            theme=bengal_theme,
            force_terminal=force_terminal,
            no_color=no_color,
            highlight=True,
            emoji=True,  # Support emoji on all platforms
        )
    
    return _console


def should_use_rich() -> bool:
    """
    Determine if we should use rich features.
    
    Returns:
        True if rich features should be enabled
    """
    console = get_console()
    
    # Disable in CI environments
    if os.getenv('CI'):
        return False
    
    # Disable if no terminal
    if not console.is_terminal:
        return False
    
    # Allow if terminal exists, even if TERM=dumb
    # Rich handles this gracefully with simpler output
    return True


def detect_environment() -> dict:
    """
    Detect terminal and environment capabilities.
    
    Returns:
        Dictionary with environment info
    """
    env = {}
    
    # Terminal info
    console = get_console()
    env['is_terminal'] = console.is_terminal
    env['color_system'] = console.color_system
    env['width'] = console.width
    env['height'] = console.height
    
    # CI detection
    env['is_ci'] = any([
        os.getenv('CI'),
        os.getenv('CONTINUOUS_INTEGRATION'),
        os.getenv('GITHUB_ACTIONS'),
        os.getenv('GITLAB_CI'),
        os.getenv('CIRCLECI'),
        os.getenv('TRAVIS'),
    ])
    
    # Docker detection
    env['is_docker'] = (
        os.path.exists('/.dockerenv') or
        os.path.exists('/run/.containerenv')
    )
    
    # Git detection
    env['is_git_repo'] = os.path.exists('.git')
    
    # CPU cores (for parallel suggestions)
    import multiprocessing
    env['cpu_count'] = multiprocessing.cpu_count()
    
    # Terminal emulator detection
    term_program = os.getenv('TERM_PROGRAM', '')
    env['terminal_app'] = term_program or 'unknown'
    
    return env


def reset_console():
    """Reset the console singleton (mainly for testing)."""
    global _console
    _console = None

