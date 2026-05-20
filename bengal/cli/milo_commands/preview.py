"""Preview command - build then serve completed static output."""

from __future__ import annotations

from typing import Annotated

from milo import Description


def preview(
    source: Annotated[str, Description("Source directory path")] = "",
    host: Annotated[str, Description("Server host address")] = "localhost",
    port: Annotated[int, Description("Server port number")] = 5173,
    auto_port: Annotated[
        bool, Description("Find available port if specified port is taken")
    ] = True,
    open_browser: Annotated[bool, Description("Open browser after server starts")] = True,
    environment: Annotated[str, Description("Environment: local, preview, production")] = "preview",
    profile: Annotated[str, Description("Config profile: writer, theme-dev, dev")] = "",
    incremental: Annotated[
        bool, Description("Use incremental build cache before previewing")
    ] = True,
    strict: Annotated[bool, Description("Fail preview build on validation errors")] = True,
    verbose: Annotated[bool, Description("Show detailed build and server activity")] = False,
    debug: Annotated[bool, Description("Show debug output and full tracebacks")] = False,
    style: Annotated[str, Description("Output style: dense, ascii, or ci")] = "dense",
    traceback: Annotated[
        str, Description("Traceback verbosity: full | compact | minimal | off")
    ] = "",
    config: Annotated[str, Description("Path to config file (default: bengal.toml)")] = "",
) -> dict:
    """Build the site completely, then serve the generated output read-only."""
    from bengal.cli.utils import (
        configure_cli_logging,
        configure_traceback,
        get_cli_output,
        load_site_from_cli,
    )

    source = source or "."
    config_path = config or None
    traceback_val = traceback or None

    cli = get_cli_output()

    if verbose and debug:
        cli.error("--verbose and --debug cannot be used together")
        cli.tip("Pick one - --debug implies --verbose and adds traceback output.")
        raise SystemExit(2)

    style_val = (style or "dense").lower()
    if style_val not in {"dense", "ascii", "ci"}:
        cli.error(f"--style must be one of dense, ascii, or ci (got: {style!r})")
        cli.tip("Use --style ci for stable ASCII-safe output in automation logs.")
        raise SystemExit(2)

    with cli.output_mode(style_val):
        configure_cli_logging(
            source=source,
            debug=debug,
            verbose=verbose,
            log_type="serve",
        )
        configure_traceback(debug=debug, traceback=traceback_val)

        preview_environment = environment or "preview"
        site = load_site_from_cli(
            source=source,
            config=config_path,
            environment=preview_environment,
            profile=profile or None,
        )
        configure_traceback(debug=debug, traceback=traceback_val, site=site)

        cfg = site.config
        if "build" not in cfg:
            cfg["build"] = {}
        cfg["build"]["strict_mode"] = strict
        if debug:
            cfg["build"]["debug"] = True

        try:
            from bengal.orchestration.build.options import BuildCompletionPolicy, BuildOptions
            from bengal.orchestration.site_runner import SiteRunner
            from bengal.orchestration.stats import display_build_stats, show_building_indicator
            from bengal.server.preview_server import PreviewServer
            from bengal.utils.observability.profile import BuildProfile

            build_profile = BuildProfile.from_cli_args(profile=profile or None, debug=debug)
            show_building_indicator("Building preview")
            stats = SiteRunner(site).build(
                BuildOptions(
                    profile=build_profile,
                    incremental=incremental,
                    strict=strict,
                    verbose=verbose,
                    completion_policy=BuildCompletionPolicy.COMPLETE,
                )
            )
            display_build_stats(stats, show_art=False, output_dir=str(site.output_dir))

            PreviewServer(
                site,
                host=host,
                port=port,
                auto_port=auto_port,
                open_browser=open_browser,
            ).start()

            return {"status": "ok", "message": "Preview server stopped"}
        except SystemExit, KeyboardInterrupt:
            raise
        except Exception as e:
            from bengal.cli.utils.errors import handle_exception

            handle_exception(e, cli, operation="running preview server")
            raise SystemExit(1) from e
