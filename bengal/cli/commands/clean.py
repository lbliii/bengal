"""Clean commands for removing generated files."""

from pathlib import Path

import click

from bengal.core.site import Site
from bengal.utils.build_stats import show_error


@click.command()
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.option("--cache", is_flag=True, help="Also remove build cache (.bengal/ directory)")
@click.option("--all", "clean_all", is_flag=True, help="Remove everything (output + cache)")
@click.option(
    "--config", type=click.Path(exists=True), help="Path to config file (default: bengal.toml)"
)
@click.argument("source", type=click.Path(exists=True), default=".")
def clean(force: bool, cache: bool, clean_all: bool, config: str, source: str) -> None:
    """
    🧹 Clean generated files.

    By default, removes only the output directory (public/).

    Options:
      --cache    Also remove build cache (for cold build testing)
      --all      Remove both output and cache (complete reset)

    Examples:
      bengal clean              # Clean output only (preserves cache)
      bengal clean --cache      # Clean output AND cache
      bengal clean --all        # Same as --cache
    """
    try:
        root_path = Path(source).resolve()
        config_path = Path(config).resolve() if config else None

        # Create site
        site = Site.from_config(root_path, config_path)

        # Determine what to clean
        clean_cache = cache or clean_all

        # Show header (consistent with all other commands)
        from bengal.utils.cli_output import CLIOutput

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

        # Confirm before cleaning unless --force
        if not force:
            # Interactive mode: ask for confirmation (with warning icon for destructive operation)
            try:
                from rich.prompt import Confirm

                from bengal.utils.rich_console import get_console, should_use_rich

                if should_use_rich():
                    console = get_console()
                    if clean_cache:
                        console.print("[yellow bold]⚠️  Delete output AND cache?[/yellow bold]")
                        console.print(
                            "[dim]   This will force a complete rebuild on next build[/dim]"
                        )
                    else:
                        console.print("[yellow bold]⚠️  Delete output files?[/yellow bold]")
                        console.print(
                            "[dim]   Cache will be preserved for incremental builds[/dim]"
                        )
                    if not Confirm.ask("Proceed", console=console, default=False):
                        console.print("[yellow]Cancelled[/yellow]")
                        return
                else:
                    # Fallback to click
                    prompt = click.style("⚠️  Delete files?", fg="yellow", bold=True)
                    if not click.confirm(prompt, default=False):
                        click.echo(click.style("Cancelled", fg="yellow"))
                        return
            except ImportError:
                # Rich not available, use click
                prompt = click.style("⚠️  Delete files?", fg="yellow", bold=True)
                if not click.confirm(prompt, default=False):
                    click.echo(click.style("Cancelled", fg="yellow"))
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
            cli.info("   Run 'bengal clean --cache' for cold build testing")
        cli.blank()

    except Exception as e:
        show_error(f"Clean failed: {e}", show_art=False)
        raise click.Abort() from e


@click.command()
@click.option("--force", "-f", is_flag=True, help="Kill process without confirmation")
@click.option("--port", "-p", type=int, help="Also check if process is using this port")
@click.argument("source", type=click.Path(exists=True), default=".")
def cleanup(force: bool, port: int, source: str) -> None:
    """
    🔧 Clean up stale Bengal server processes.

    Finds and terminates any stale 'bengal serve' processes that may be
    holding ports or preventing new servers from starting.

    This is useful if a previous server didn't shut down cleanly.
    """
    try:
        from bengal.server.pid_manager import PIDManager

        root_path = Path(source).resolve()
        pid_file = PIDManager.get_pid_file(root_path)

        # Check for stale process
        stale_pid = PIDManager.check_stale_pid(pid_file)

        if not stale_pid:
            click.echo(click.style("✅ No stale processes found", fg="green"))

            # If port specified, check if something else is using it
            if port:
                port_pid = PIDManager.get_process_on_port(port)
                if port_pid:
                    click.echo(
                        click.style(
                            f"\n⚠️  However, port {port} is in use by PID {port_pid}", fg="yellow"
                        )
                    )
                    if PIDManager.is_bengal_process(port_pid):
                        click.echo("   This appears to be a Bengal process not tracked by PID file")
                        if not force and not click.confirm(f"  Kill process {port_pid}?"):
                            click.echo("Cancelled")
                            return
                        if PIDManager.kill_stale_process(port_pid):
                            click.echo(click.style(f"✅ Process {port_pid} terminated", fg="green"))
                        else:
                            click.echo(
                                click.style(f"❌ Failed to kill process {port_pid}", fg="red")
                            )
                            raise click.Abort()
                    else:
                        click.echo("   This is not a Bengal process")
                        click.echo(f"   Try manually: kill {port_pid}")
            return

        # Found stale process
        click.echo(click.style("⚠️  Found stale Bengal server process", fg="yellow"))
        click.echo(f"   PID: {stale_pid}")

        # Check if it's holding a port
        if port:
            port_pid = PIDManager.get_process_on_port(port)
            if port_pid == stale_pid:
                click.echo(f"   Holding port: {port}")

        # Confirm unless --force
        if not force:
            try:
                from rich.prompt import Confirm

                from bengal.utils.rich_console import get_console, should_use_rich

                if should_use_rich():
                    console = get_console()
                    if not Confirm.ask("  Kill this process", console=console, default=False):
                        console.print("Cancelled")
                        return
                elif not click.confirm("  Kill this process?"):
                    click.echo("Cancelled")
                    return
            except ImportError:
                if not click.confirm("  Kill this process?"):
                    click.echo("Cancelled")
                    return

        # Kill the process
        if PIDManager.kill_stale_process(stale_pid):
            click.echo(click.style("✅ Stale process terminated successfully", fg="green"))
        else:
            click.echo(click.style("❌ Failed to terminate process", fg="red"))
            click.echo(f"   Try manually: kill {stale_pid}")
            raise click.Abort()

    except ImportError:
        show_error("Cleanup command requires server dependencies", show_art=False)
        raise click.Abort() from None
    except Exception as e:
        show_error(f"Cleanup failed: {e}", show_art=False)
        raise click.Abort() from e
