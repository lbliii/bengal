"""Serve command — development server with hot reload."""

from __future__ import annotations

from typing import Annotated

from milo import Description


def serve(
    source: Annotated[str, Description("Source directory path")] = "",
    host: Annotated[str, Description("Server host address")] = "localhost",
    port: Annotated[int, Description("Server port number")] = 5173,
    watch: Annotated[bool, Description("Watch for file changes and rebuild")] = True,
    no_watch: Annotated[bool, Description("Disable file watching")] = False,
    auto_port: Annotated[
        bool, Description("Find available port if specified port is taken")
    ] = True,
    no_auto_port: Annotated[bool, Description("Don't auto-find available port")] = False,
    open_browser: Annotated[bool, Description("Open browser after server starts")] = True,
    no_open: Annotated[bool, Description("Don't open browser")] = False,
    environment: Annotated[str, Description("Environment: local, preview, production")] = "",
    profile: Annotated[str, Description("Config profile: writer, theme-dev, dev")] = "",
    version_scope: Annotated[str, Description("Focus on single version (e.g., v2, latest)")] = "",
    all_versions: Annotated[bool, Description("Build all versions (default behavior)")] = False,
    dashboard: Annotated[bool, Description("Launch interactive Textual dashboard")] = False,
    verbose: Annotated[bool, Description("Show detailed server activity")] = False,
    debug: Annotated[bool, Description("Show debug output and full tracebacks")] = False,
    traceback: Annotated[
        str, Description("Traceback verbosity: full | compact | minimal | off")
    ] = "",
    config: Annotated[str, Description("Path to config file (default: bengal.toml)")] = "",
) -> dict:
    """Start development server with hot reload.

    Watches for changes in content, assets, and templates,
    automatically rebuilding the site when files are modified.
    """
    from bengal.cli.utils import configure_cli_logging, configure_traceback, load_site_from_cli

    source = source or "."
    config_path = config or None
    traceback_val = traceback or None
    version_scope_val = version_scope or None

    # Resolve tri-state flags
    watch_enabled = not no_watch and watch
    auto_port_enabled = not no_auto_port and auto_port
    open_browser_enabled = not no_open and open_browser

    if verbose and debug:
        raise SystemExit("Error: --verbose and --debug cannot be used together")

    if version_scope_val and all_versions:
        raise SystemExit("Error: --version-scope and --all-versions cannot be used together")

    configure_cli_logging(
        source=source,
        debug=debug,
        verbose=verbose,
        log_type="serve",
    )
    configure_traceback(debug=debug, traceback=traceback_val)

    dev_environment = environment or "local"

    site = load_site_from_cli(
        source=source,
        config=config_path,
        environment=dev_environment,
        profile=profile or None,
    )

    configure_traceback(debug=debug, traceback=traceback_val, site=site)

    cfg = site.config
    if "build" not in cfg:
        cfg["build"] = {}
    cfg["build"]["strict_mode"] = True
    if debug:
        cfg["build"]["debug"] = True

    if dashboard:
        from bengal.cli.dashboard.serve import run_serve_dashboard

        run_serve_dashboard(
            site=site,
            host=host,
            port=port,
            watch=watch_enabled,
            open_browser=open_browser_enabled,
        )
        return None

    site.serve(
        host=host,
        port=port,
        watch=watch_enabled,
        auto_port=auto_port_enabled,
        open_browser=open_browser_enabled,
        version_scope=version_scope_val,
    )

    return None
