"""Clean command — remove generated files and stale processes."""

from __future__ import annotations

from pathlib import Path
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
    from bengal.cli.utils import load_site_from_cli
    from bengal.output import get_cli_output

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

    action = "Clean output and cache" if clean_cache else "Clean output"
    state_dir = site.config_service.paths.state_dir
    targets = [
        _clean_target("Output", _display_path(site.output_dir, site.root_path), mode="remove"),
        _clean_target(
            "Cache",
            _display_path(state_dir, site.root_path) if clean_cache else "preserved",
            mode="remove" if clean_cache else "keep",
        ),
    ]

    cli.render_write(
        "clean_plan.kida",
        brand_mark="ᓚᘏᗢ",
        title=action,
        targets=targets,
        targets_text="\n".join(target["line"] for target in targets),
        cold_build=clean_cache,
    )

    if not force and not cli.confirm("Proceed", default=False):
        cli.render_write(
            "clean_result.kida",
            status="skipped",
            message="Clean cancelled",
            detail="No files were removed.",
        )
        return {"status": "skipped", "message": "Clean cancelled by user"}

    site.clean()

    removed = [str(site.output_dir)]
    if clean_cache and state_dir.exists():
        from bengal.utils.io.file_io import rmtree_robust

        rmtree_robust(state_dir, max_retries=3, caller="cli.clean")
        removed.append(str(state_dir))

    cli.render_write(
        "clean_result.kida",
        status="success",
        message="Clean complete",
        detail="Next build will be cold."
        if clean_cache
        else "Cache preserved for incremental builds.",
    )

    return {
        "status": "ok",
        "message": "Done — cold build next time" if clean_cache else "Done — cache preserved",
        "removed": removed,
        "cache_cleared": clean_cache,
    }


def _clean_target(label: str, value: str, *, mode: str) -> dict[str, str]:
    """Build a template-friendly clean target row."""
    return {
        "label": label,
        "value": value,
        "mode": mode,
        "padding": " " * max(10 - len(label), 1),
        "line": f"  {label}{' ' * max(10 - len(label), 1)}{value}"
        + (" [kept]" if mode == "keep" else ""),
    }


def _display_path(path: Path | str, root: Path) -> str:
    """Return a concise command-facing path relative to the site root when possible."""
    path = Path(path)
    try:
        display = path.relative_to(root)
    except ValueError:
        display = path
    text = str(display)
    return f"{text}/" if path.suffix == "" and not text.endswith("/") else text


def _cleanup_stale_server(force: bool, source: str) -> None:
    """Clean up stale Bengal server processes."""
    from pathlib import Path

    from bengal.output import get_cli_output
    from bengal.server.pid_manager import PIDManager

    cli = get_cli_output()
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
