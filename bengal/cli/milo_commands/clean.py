"""Clean command — remove generated files and stale processes."""

from __future__ import annotations

from typing import Annotated

from milo import Description


def clean(
    source: Annotated[str, Description("Source directory path")] = ".",
    force: Annotated[bool, Description("Skip confirmation prompt")] = False,
    cache: Annotated[bool, Description("Also remove build cache (.bengal/ directory)")] = False,
    all: Annotated[bool, Description("Remove everything (output + cache)")] = False,
    stale_server: Annotated[bool, Description("Clean up stale 'bengal serve' processes")] = False,
    config: Annotated[str, Description("Path to config file (default: bengal.toml)")] = "",
) -> dict:
    """Clean generated files and stale processes.

    By default, removes only the output directory (public/).
    Use --cache to also remove the build cache, or --all for both.
    """
    from bengal.cli.utils import get_cli_output, load_site_from_cli

    cli = get_cli_output()

    source = source or "."
    config_path = config or None
    site = load_site_from_cli(
        source=source, config=config_path, environment=None, profile=None, cli=cli
    )

    clean_cache = cache or all

    if stale_server:
        _cleanup_stale_server(force, source)
        return {"status": "ok", "message": "Stale server cleanup complete"}

    action = "Clean output + cache" if clean_cache else "Clean output"
    items = [{"label": "Output", "value": str(site.output_dir)}]
    if clean_cache:
        items.append({"label": "Cache", "value": str(site.root_path / ".bengal")})
    else:
        items.append({"label": "Cache", "value": "preserved"})

    cli.render_write("kv_detail.kida", title=action, items=items)

    if not force:
        if clean_cache:
            cli.warning("This forces a complete rebuild next time")
        if not cli.confirm("Proceed", default=False):
            cli.warning("Cancelled")
            return {"status": "skipped", "message": "Clean cancelled by user"}

    site.clean()

    removed = [str(site.output_dir)]
    if clean_cache and site.config_service.paths.state_dir.exists():
        from bengal.utils.io.file_io import rmtree_robust

        rmtree_robust(site.config_service.paths.state_dir, max_retries=3, caller="cli.clean")
        removed.append(str(site.config_service.paths.state_dir))

    cli.blank()
    if clean_cache:
        cli.success("Done — cold build next time")
    else:
        cli.success("Done — cache preserved")

    return {
        "status": "ok",
        "message": "Done — cold build next time" if clean_cache else "Done — cache preserved",
        "removed": removed,
        "cache_cleared": clean_cache,
    }


def _cleanup_stale_server(force: bool, source: str) -> None:
    """Clean up stale Bengal server processes."""
    from pathlib import Path

    from bengal.output import CLIOutput
    from bengal.server.pid_manager import PIDManager

    cli = CLIOutput()
    root_path = Path(source).resolve()
    pid_file = PIDManager.get_pid_file(root_path)

    stale_pid = PIDManager.check_stale_pid(pid_file)

    if not stale_pid:
        cli.success("No stale processes found")
        return

    cli.warning("Found stale Bengal server process")
    cli.info(f"   PID: {stale_pid}")

    if not force and not cli.confirm("Kill this process", default=False):
        cli.info("Cancelled")
        return

    if PIDManager.kill_stale_process(stale_pid):
        cli.success("Stale process terminated successfully")
    else:
        cli.error("Failed to terminate process")
        cli.info(f"   Try manually: kill {stale_pid}")
        raise SystemExit(1)
