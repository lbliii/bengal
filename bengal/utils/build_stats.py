"""
Build statistics display with colorful output and ASCII art.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import time
import click


# Bengal tiger ASCII art variations
BENGAL_ART = r"""
    /\_/\  
   ( o.o ) 
    > ^ <   Bengal SSG
"""

BENGAL_SUCCESS = r"""
    /\_/\  
   ( ^.^ ) 
    > ^ <
"""

BENGAL_ERROR = r"""
    /\_/\  
   ( x.x ) 
    > ^ <
"""

BENGAL_BUILDING = r"""
    /\_/\  
   ( -.o ) 
    > ^ <   Building...
"""


@dataclass
class BuildStats:
    """Container for build statistics."""
    
    total_pages: int = 0
    regular_pages: int = 0
    generated_pages: int = 0
    total_assets: int = 0
    total_sections: int = 0
    taxonomies_count: int = 0
    build_time_ms: float = 0
    parallel: bool = True
    incremental: bool = False
    skipped: bool = False
    
    # Phase timings
    discovery_time_ms: float = 0
    taxonomy_time_ms: float = 0
    rendering_time_ms: float = 0
    assets_time_ms: float = 0
    postprocess_time_ms: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            'total_pages': self.total_pages,
            'regular_pages': self.regular_pages,
            'generated_pages': self.generated_pages,
            'total_assets': self.total_assets,
            'total_sections': self.total_sections,
            'taxonomies_count': self.taxonomies_count,
            'build_time_ms': self.build_time_ms,
            'parallel': self.parallel,
            'incremental': self.incremental,
            'skipped': self.skipped,
            'discovery_time_ms': self.discovery_time_ms,
            'taxonomy_time_ms': self.taxonomy_time_ms,
            'rendering_time_ms': self.rendering_time_ms,
            'assets_time_ms': self.assets_time_ms,
            'postprocess_time_ms': self.postprocess_time_ms,
        }


def format_time(ms: float) -> str:
    """Format milliseconds for display."""
    if ms < 1:
        return f"{ms:.2f} ms"
    elif ms < 1000:
        return f"{int(ms)} ms"
    else:
        seconds = ms / 1000
        return f"{seconds:.2f} s"


def display_build_stats(stats: BuildStats, show_art: bool = True) -> None:
    """
    Display build statistics in a colorful table.
    
    Args:
        stats: Build statistics to display
        show_art: Whether to show ASCII art
    """
    if stats.skipped:
        click.echo(click.style("\n✨ No changes detected - build skipped!", fg='cyan', bold=True))
        return
    
    # Display ASCII art
    if show_art:
        click.echo(click.style(BENGAL_SUCCESS, fg='yellow'))
    
    # Header
    click.echo(click.style("\n┌─────────────────────────────────────────────────────┐", fg='cyan'))
    click.echo(click.style("│", fg='cyan') + click.style("              🎉 BUILD COMPLETE 🎉                 ", fg='green', bold=True) + click.style("│", fg='cyan'))
    click.echo(click.style("└─────────────────────────────────────────────────────┘", fg='cyan'))
    
    # Content stats
    click.echo(click.style("\n📊 Content Statistics:", fg='cyan', bold=True))
    click.echo(click.style("   ├─ ", fg='cyan') + f"Pages:       {click.style(str(stats.total_pages), fg='green', bold=True)}" + 
               f" ({stats.regular_pages} regular + {stats.generated_pages} generated)")
    click.echo(click.style("   ├─ ", fg='cyan') + f"Sections:    {click.style(str(stats.total_sections), fg='green', bold=True)}")
    click.echo(click.style("   ├─ ", fg='cyan') + f"Assets:      {click.style(str(stats.total_assets), fg='green', bold=True)}")
    click.echo(click.style("   └─ ", fg='cyan') + f"Taxonomies:  {click.style(str(stats.taxonomies_count), fg='green', bold=True)}")
    
    # Build info
    click.echo(click.style("\n⚙️  Build Configuration:", fg='cyan', bold=True))
    mode_parts = []
    if stats.incremental:
        mode_parts.append(click.style("incremental", fg='yellow'))
    if stats.parallel:
        mode_parts.append(click.style("parallel", fg='yellow'))
    if not mode_parts:
        mode_parts.append(click.style("sequential", fg='yellow'))
    
    mode_text = " + ".join(mode_parts)
    click.echo(click.style("   └─ ", fg='cyan') + f"Mode:        {mode_text}")
    
    # Performance stats
    click.echo(click.style("\n⏱️  Performance:", fg='cyan', bold=True))
    
    # Total time with color coding
    total_time_str = format_time(stats.build_time_ms)
    if stats.build_time_ms < 100:
        time_color = 'green'
        emoji = "🚀"
    elif stats.build_time_ms < 1000:
        time_color = 'yellow'
        emoji = "⚡"
    else:
        time_color = 'red'
        emoji = "🐌"
    
    click.echo(click.style("   ├─ ", fg='cyan') + f"Total:       {click.style(total_time_str, fg=time_color, bold=True)} {emoji}")
    
    # Phase breakdown (only if we have phase data)
    if stats.discovery_time_ms > 0:
        click.echo(click.style("   ├─ ", fg='cyan') + f"Discovery:   {click.style(format_time(stats.discovery_time_ms), fg='white')}")
    if stats.taxonomy_time_ms > 0:
        click.echo(click.style("   ├─ ", fg='cyan') + f"Taxonomies:  {click.style(format_time(stats.taxonomy_time_ms), fg='white')}")
    if stats.rendering_time_ms > 0:
        click.echo(click.style("   ├─ ", fg='cyan') + f"Rendering:   {click.style(format_time(stats.rendering_time_ms), fg='white')}")
    if stats.assets_time_ms > 0:
        click.echo(click.style("   ├─ ", fg='cyan') + f"Assets:      {click.style(format_time(stats.assets_time_ms), fg='white')}")
    if stats.postprocess_time_ms > 0:
        click.echo(click.style("   └─ ", fg='cyan') + f"Postprocess: {click.style(format_time(stats.postprocess_time_ms), fg='white')}")
    
    # Fun stats
    if stats.build_time_ms > 0:
        pages_per_sec = (stats.total_pages / stats.build_time_ms) * 1000 if stats.build_time_ms > 0 else 0
        if pages_per_sec > 0:
            click.echo(click.style("\n📈 Throughput:", fg='cyan', bold=True))
            click.echo(click.style("   └─ ", fg='cyan') + 
                      f"{click.style(f'{pages_per_sec:.1f}', fg='magenta', bold=True)} pages/second")
    
    click.echo(click.style("\n─────────────────────────────────────────────────────\n", fg='cyan'))


def show_building_indicator(text: str = "Building") -> None:
    """Show a building indicator."""
    click.echo(click.style(BENGAL_BUILDING, fg='yellow'))
    click.echo(click.style(f"🔨 {text}...\n", fg='cyan', bold=True))


def show_error(message: str, show_art: bool = True) -> None:
    """Show an error message with art."""
    if show_art:
        click.echo(click.style(BENGAL_ERROR, fg='red'))
    click.echo(click.style(f"❌ {message}", fg='red', bold=True))


def show_welcome() -> None:
    """Show welcome banner."""
    banner = r"""
    ╔══════════════════════════════════════════════════════╗
    ║                                                      ║
    ║        /\_/\      BENGAL SSG                        ║
    ║       ( ^.^ )     Fast & Fierce Static Sites        ║
    ║        > ^ <                                         ║
    ║                                                      ║
    ╚══════════════════════════════════════════════════════╝
    """
    click.echo(click.style(banner, fg='yellow', bold=True))


def show_clean_success(output_dir: str) -> None:
    """Show clean success message."""
    click.echo(click.style("\n🧹 Cleaning output directory...", fg='cyan'))
    click.echo(click.style("   ├─ ", fg='cyan') + f"Directory: {click.style(output_dir, fg='white')}")
    click.echo(click.style("   └─ ", fg='cyan') + click.style("✓ Clean complete!", fg='green', bold=True))
    click.echo()

