"""Development server command."""

from pathlib import Path
import click

from bengal.core.site import Site
from bengal.utils.build_stats import show_error


@click.command()
@click.option('--host', default='localhost', help='Server host address')
@click.option('--port', '-p', default=5173, type=int, help='Server port number')
@click.option('--watch/--no-watch', default=True, help='Watch for file changes and rebuild (default: enabled)')
@click.option('--auto-port/--no-auto-port', default=True, help='Find available port if specified port is taken (default: enabled)')
@click.option('--open', '-o', 'open_browser', is_flag=True, help='Open browser automatically after server starts')
@click.option('--config', type=click.Path(exists=True), help='Path to config file (default: bengal.toml)')
@click.argument('source', type=click.Path(exists=True), default='.')
def serve(host: str, port: int, watch: bool, auto_port: bool, open_browser: bool, config: str, source: str) -> None:
    """
    🚀 Start development server with hot reload.
    
    Watches for changes in content, assets, and templates,
    automatically rebuilding the site when files are modified.
    """
    try:
        # Welcome banner removed for consistency with build command
        # The "Building your site..." header is sufficient
        
        root_path = Path(source).resolve()
        config_path = Path(config).resolve() if config else None
        
        # Create site
        site = Site.from_config(root_path, config_path)
        
        # Enable strict mode in development (fail fast on errors)
        site.config["strict_mode"] = True
        
        # Start server (this blocks)
        site.serve(host=host, port=port, watch=watch, auto_port=auto_port, open_browser=open_browser)
        
    except Exception as e:
        show_error(f"Server failed: {e}", show_art=True)
        raise click.Abort()

