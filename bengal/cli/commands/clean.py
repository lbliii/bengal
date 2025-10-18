"""Clean commands for removing generated files."""

from pathlib import Path

import click

from bengal.cli.base import BengalCommand
from bengal.core.site import Site
from bengal.utils.build_stats import show_error
from bengal.utils.cli_output import CLIOutput


@click.command(cls=BengalCommand)
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.option("--cache", is_flag=True, help="Also remove build cache (.bengal/ directory)")
@click.option("--all", "clean_all", is_flag=True, help="Remove everything (output + cache)")
@click.option("--stale-server", is_flag=True, help="Clean up stale 'bengal serve' processes")
@click.option(
    "--config", type=click.Path(exists=True), help="Path to config file (default: bengal.toml)"
)
@click.argument("source", type=click.Path(exists=True), default=".")
def clean(
    force: bool, cache: bool, clean_all: bool, stale_server: bool, config: str, source: str
) -> None:
    """
    🧹 Clean generated files and stale processes.

    By default, removes only the output directory (public/).

    Options:
      --cache         Also remove build cache
      --all           Remove both output and cache
      --stale-server  Clean up stale 'bengal serve' processes

    Examples:
      bengal clean                  # Clean output only
      bengal clean --cache          # Clean output and cache
      bengal clean --stale-server   # Clean up stale server processes
    """
    try:
        root_path = Path(source).resolve()
        config_path = Path(config).resolve() if config else None

        # Create site
        site = Site.from_config(root_path, config_path)

        # Determine what to clean
        clean_cache = cache or clean_all

        # Show header (consistent with all other commands)
        cli = CLIOutput()
        cli.blank()

        if clean_cache:
            cli.header("Cleaning output directory and cache...")
            cli.info(f"   Output: {site.output_dir}")
            cli.info(f"   Cache:  {site.root_path / '.bengal'}")
        else:
            cli.header("Cleaning output directory...")
            cli.info(f"   ↪ {site.output_dir}")
            cli.info(f"   ℹ Cache preserved at {site.root_path / '.bengal'}")
        cli.blank()

        if stale_server:
            cleanup(force, None, source)
            return

        # Confirm before cleaning unless --force
        if not force:
            # Interactive mode: ask for confirmation (with warning icon for destructive operation)
            if clean_cache:
                cli.warning("Delete output AND cache?")
                if cli.use_rich:
                    cli.detail("This will force a complete rebuild on next build", indent=1)
            else:
                cli.warning("Delete output files?")
                if cli.use_rich:
                    cli.detail("Cache will be preserved for incremental builds", indent=1)

            if not cli.confirm("Proceed", default=False):
                cli.warning("Cancelled")
                return

        # Clean output directory
        site.clean()

        # Clean cache if requested
        if clean_cache:
            cache_dir = site.root_path / ".bengal"
            if cache_dir.exists():
                import shutil

                shutil.rmtree(cache_dir)
                cli.info("   ✓ Removed cache directory")

        # Show success
        cli.blank()
        if clean_cache:
            cli.success("Clean complete! (output + cache)", icon="✓")
            cli.info("   Next build will be a cold build (no cache)")
        else:
            cli.success("Clean complete! (cache preserved)", icon="✓")
            cli.tip("Run 'bengal clean --cache' for cold build testing")
        cli.blank()

    except Exception as e:
        show_error(f"Clean failed: {e}", show_art=False)
        raise click.Abort() from e


def cleanup(force: bool, port: int, source: str) -> None:
    """Clean up stale Bengal server processes."""
    try:
        from bengal.server.pid_manager import PIDManager
        from bengal.utils.cli_output import CLIOutput

        cli = CLIOutput()
        root_path = Path(source).resolve()
        pid_file = PIDManager.get_pid_file(root_path)

        # Check for stale process
        stale_pid = PIDManager.check_stale_pid(pid_file)

        if not stale_pid:
            cli.success("No stale processes found")

            # If port specified, check if something else is using it
            if port:
                port_pid = PIDManager.get_process_on_port(port)
                if port_pid:
                    cli.blank()
                    cli.warning(f"However, port {port} is in use by PID {port_pid}")
                    if PIDManager.is_bengal_process(port_pid):
                        cli.info("   This appears to be a Bengal process not tracked by PID file")
                        if not force and not click.confirm(f"  Kill process {port_pid}?"):
                            cli.info("Cancelled")
                            return
                        if PIDManager.kill_stale_process(port_pid):
                            cli.success(f"Process {port_pid} terminated")
                        else:
                            cli.error(f"Failed to kill process {port_pid}")
                            raise click.Abort()
                    else:
                        cli.info("   This is not a Bengal process")
                        cli.info(f"   Try manually: kill {port_pid}")
            return

        # Found stale process
        cli.warning("Found stale Bengal server process")
        cli.info(f"   PID: {stale_pid}")

        # Check if it's holding a port
        if port:
            port_pid = PIDManager.get_process_on_port(port)
            if port_pid == stale_pid:
                cli.info(f"   Holding port: {port}")

        # Confirm unless --force
        if not force:
            try:
                from rich.prompt import Confirm

                from bengal.utils.rich_console import get_console, should_use_rich

                if should_use_rich():
                    console = get_console()
                    if not Confirm.ask("  Kill this process", console=console, default=False):
                        cli.info("Cancelled")
                        return
                elif not click.confirm("  Kill this process?"):
                    cli.info("Cancelled")
                    return
            except ImportError:
                if not click.confirm("  Kill this process?"):
                    cli.info("Cancelled")
                    return

        # Kill the process
        if PIDManager.kill_stale_process(stale_pid):
            cli.success("Stale process terminated successfully")
        else:
            cli.error("Failed to terminate process")
            cli.info(f"   Try manually: kill {stale_pid}")
            raise click.Abort()

    except ImportError:
        show_error("Cleanup command requires server dependencies", show_art=False)
        raise click.Abort() from None
    except Exception as e:
        show_error(f"Cleanup failed: {e}", show_art=False)
        raise click.Abort() from e
