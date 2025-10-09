"""
Centralized CLI output system for Bengal.

Provides a unified interface for all CLI messaging with:
- Profile-aware formatting (Writer, Theme-Dev, Developer)
- Consistent indentation and spacing
- Automatic TTY detection
- Rich/fallback rendering
"""

from typing import Optional, Dict, Any, List
from enum import Enum
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
import click


class MessageLevel(Enum):
    """Message importance levels."""
    DEBUG = 0      # Only in --verbose
    INFO = 1       # Normal operations
    SUCCESS = 2    # Successful operations
    WARNING = 3    # Non-critical issues
    ERROR = 4      # Errors
    CRITICAL = 5   # Fatal errors


class OutputStyle(Enum):
    """Visual styles for messages."""
    PLAIN = "plain"
    HEADER = "header"
    PHASE = "phase"
    DETAIL = "detail"
    METRIC = "metric"
    PATH = "path"
    SUMMARY = "summary"


class CLIOutput:
    """
    Centralized CLI output manager.
    
    Handles all terminal output with profile-aware formatting,
    consistent spacing, and automatic TTY detection.
    
    Example:
        cli = CLIOutput(profile=BuildProfile.WRITER)
        
        cli.header("Building your site...")
        cli.phase_start("Discovery")
        cli.detail("Found 245 pages", indent=1)
        cli.phase_complete("Discovery", duration_ms=61)
        cli.success("Built 245 pages in 0.8s")
    """
    
    def __init__(
        self,
        profile: Optional[Any] = None,
        quiet: bool = False,
        verbose: bool = False,
        use_rich: Optional[bool] = None
    ):
        """
        Initialize CLI output manager.
        
        Args:
            profile: Build profile (Writer, Theme-Dev, Developer)
            quiet: Suppress non-critical output
            verbose: Show detailed output
            use_rich: Force rich/plain output (None = auto-detect)
        """
        self.profile = profile
        self.quiet = quiet
        self.verbose = verbose
        
        # Auto-detect rich support
        if use_rich is None:
            from bengal.utils.rich_console import should_use_rich
            use_rich = should_use_rich()
        
        self.use_rich = use_rich
        self.console = Console() if use_rich else None
        
        # Get profile config
        self.profile_config = profile.get_config() if profile else {}
        
        # Spacing and indentation rules
        self.indent_char = " "
        self.indent_size = 2
        
    def should_show(self, level: MessageLevel) -> bool:
        """Determine if message should be shown based on level and settings."""
        if self.quiet and level.value < MessageLevel.WARNING.value:
            return False
        if not self.verbose and level == MessageLevel.DEBUG:
            return False
        return True
    
    # === High-level message types ===
    
    def header(self, text: str, mascot: bool = True) -> None:
        """
        Print a header message.
        
        Example: "ᓚᘏᗢ  Building your site..."
        """
        if not self.should_show(MessageLevel.INFO):
            return
        
        if self.use_rich:
            mascot_str = "[bengal]ᓚᘏᗢ[/bengal]  " if mascot else ""
            self.console.print()
            self.console.print(f"    {mascot_str}[bold cyan]{text}[/bold cyan]")
            self.console.print()
        else:
            mascot_str = "ᓚᘏᗢ  " if mascot else ""
            click.echo(f"\n    {mascot_str}{text}\n", color=True)
    
    def phase(
        self,
        name: str,
        status: str = "Done",
        duration_ms: Optional[float] = None,
        details: Optional[str] = None,
        icon: str = "✓"
    ) -> None:
        """
        Print a phase status line.
        
        Examples:
            ✓ Discovery     Done
            ✓ Rendering     501ms (245 pages)
            ✓ Assets        Done
        """
        if not self.should_show(MessageLevel.SUCCESS):
            return
        
        # Format based on profile
        parts = [icon, name]
        
        # Add timing if available and profile shows it
        if duration_ms is not None and self._show_timing():
            parts.append(f"{int(duration_ms)}ms")
        
        # Add details if provided and profile shows them
        if details and self._show_details():
            parts.append(f"({details})")
        
        # Render
        line = self._format_phase_line(parts)
        
        if self.use_rich:
            self.console.print(line)
        else:
            click.echo(click.style(line, fg='green'))
    
    def detail(
        self,
        text: str,
        indent: int = 1,
        icon: Optional[str] = None
    ) -> None:
        """
        Print a detail/sub-item.
        
        Example:
            ├─ RSS feed ✓
            └─ Sitemap ✓
        """
        if not self.should_show(MessageLevel.INFO):
            return
        
        indent_str = self.indent_char * (self.indent_size * indent)
        icon_str = f"{icon} " if icon else ""
        line = f"{indent_str}{icon_str}{text}"
        
        if self.use_rich:
            self.console.print(line)
        else:
            click.echo(line)
    
    def success(self, text: str, icon: str = "✨") -> None:
        """
        Print a success message.
        
        Example: "✨ Built 245 pages in 0.8s"
        """
        if not self.should_show(MessageLevel.SUCCESS):
            return
        
        if self.use_rich:
            self.console.print()
            self.console.print(f"{icon} [bold green]{text}[/bold green]")
            self.console.print()
        else:
            click.echo(f"\n{icon} {text}\n", color=True)
    
    def info(self, text: str, icon: Optional[str] = None) -> None:
        """Print an info message."""
        if not self.should_show(MessageLevel.INFO):
            return
        
        icon_str = f"{icon} " if icon else ""
        
        if self.use_rich:
            self.console.print(f"{icon_str}{text}")
        else:
            click.echo(f"{icon_str}{text}")
    
    def warning(self, text: str, icon: str = "⚠️") -> None:
        """Print a warning message."""
        if not self.should_show(MessageLevel.WARNING):
            return
        
        if self.use_rich:
            self.console.print(f"{icon}  [yellow]{text}[/yellow]")
        else:
            click.echo(click.style(f"{icon}  {text}", fg='yellow'))
    
    def error(self, text: str, icon: str = "❌") -> None:
        """Print an error message."""
        if not self.should_show(MessageLevel.ERROR):
            return
        
        if self.use_rich:
            self.console.print(f"{icon} [bold red]{text}[/bold red]")
        else:
            click.echo(click.style(f"{icon} {text}", fg='red', bold=True))
    
    def path(self, path: str, icon: str = "📂", label: str = "Output") -> None:
        """
        Print a path.
        
        Example:
            📂 Output:
               ↪ /Users/.../public
        """
        if not self.should_show(MessageLevel.INFO):
            return
        
        # Shorten path based on profile
        display_path = self._format_path(path)
        
        if self.use_rich:
            self.console.print(f"{icon} {label}:")
            self.console.print(f"   ↪ [cyan]{display_path}[/cyan]")
        else:
            click.echo(f"{icon} {label}:")
            click.echo(click.style(f"   ↪ {display_path}", fg='cyan'))
    
    def metric(
        self,
        label: str,
        value: Any,
        unit: Optional[str] = None,
        indent: int = 0
    ) -> None:
        """
        Print a metric.
        
        Example:
            ⏱️  Performance:
               ├─ Total: 834ms
               └─ Throughput: 293.7 pages/sec
        """
        if not self.should_show(MessageLevel.INFO):
            return
        
        indent_str = self.indent_char * (self.indent_size * indent)
        unit_str = f" {unit}" if unit else ""
        line = f"{indent_str}{label}: {value}{unit_str}"
        
        if self.use_rich:
            self.console.print(line)
        else:
            click.echo(line)
    
    def table(self, data: List[Dict[str, str]], headers: List[str]) -> None:
        """Print a table (rich only, falls back to simple list)."""
        if not self.should_show(MessageLevel.INFO):
            return
        
        if self.use_rich:
            table = Table(show_header=True, header_style="bold")
            for header in headers:
                table.add_column(header)
            
            for row in data:
                table.add_row(*[row.get(h, "") for h in headers])
            
            self.console.print(table)
        else:
            # Fallback to simple list
            for row in data:
                values = [f"{k}: {v}" for k, v in row.items()]
                click.echo(" | ".join(values))
    
    def blank(self, count: int = 1) -> None:
        """Print blank lines."""
        for _ in range(count):
            if self.use_rich:
                self.console.print()
            else:
                click.echo()
    
    # === Internal helpers ===
    
    def _show_timing(self) -> bool:
        """Should we show timing info based on profile?"""
        if not self.profile:
            return False
        
        profile_name = self.profile.__class__.__name__ if hasattr(self.profile, '__class__') else str(self.profile)
        
        # Writer: no timing, Theme-Dev: yes, Developer: yes
        return 'WRITER' not in profile_name
    
    def _show_details(self) -> bool:
        """Should we show detailed info based on profile?"""
        if not self.profile:
            return True
        
        # All profiles can show details (but format may differ)
        return True
    
    def _format_phase_line(self, parts: List[str]) -> str:
        """
        Format a phase line with consistent spacing.
        
        Examples:
            ✓ Discovery     Done
            ✓ Rendering     501ms (245 pages)
        """
        if len(parts) < 2:
            return " ".join(parts)
        
        icon = parts[0]
        name = parts[1]
        rest = parts[2:] if len(parts) > 2 else []
        
        # Calculate padding for alignment
        # Phase names are typically 10-12 chars, pad to 12
        name_width = 12
        name_padded = name.ljust(name_width)
        
        if rest:
            return f"{icon} {name_padded} {' '.join(rest)}"
        else:
            return f"{icon} {name_padded} Done"
    
    def _format_path(self, path: str) -> str:
        """Format path based on profile (shorten for Writer, full for Developer)."""
        if not self.profile:
            return path
        
        profile_name = self.profile.__class__.__name__ if hasattr(self.profile, '__class__') else str(self.profile)
        
        # Writer: just show "public/" or last segment
        if 'WRITER' in profile_name:
            from pathlib import Path
            return Path(path).name or path
        
        # Theme-Dev: abbreviate middle
        if 'THEME' in profile_name:
            if len(path) > 60:
                parts = path.split('/')
                if len(parts) > 3:
                    return f"{parts[0]}/.../{'/'.join(parts[-2:])}"
        
        # Developer: full path
        return path


# === Global instance ===

_cli_output: Optional[CLIOutput] = None


def get_cli_output() -> CLIOutput:
    """Get the global CLI output instance."""
    global _cli_output
    if _cli_output is None:
        _cli_output = CLIOutput()
    return _cli_output


def init_cli_output(profile: Optional[Any] = None, quiet: bool = False, verbose: bool = False) -> CLIOutput:
    """Initialize the global CLI output instance with settings."""
    global _cli_output
    _cli_output = CLIOutput(profile=profile, quiet=quiet, verbose=verbose)
    return _cli_output

