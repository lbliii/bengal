"""Execute a classified rebuild: reactive path and warm build.

Called after debounce decides this batch should run. Coordinates hooks
and the rebuild strategies; overlay/reload live in ``reload.py``.
"""

import time
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.errors import ErrorCode, create_dev_error, get_dev_server_state
from bengal.orchestration.stats import show_building_indicator, show_error
from bengal.output import get_cli_output
from bengal.server.build_hooks import run_post_build_hooks, run_pre_build_hooks
from bengal.server.build_trigger.rebuild_plan import _DoubleBuffer
from bengal.server.reload_types import BuildReloadInfo
from bengal.server.utils import get_timestamp
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from bengal.server.build_executor import BuildResult

logger = get_logger("bengal.server.build_trigger")


def _execute_build(
    trigger: Any,
    changed_paths: set[Path],
    event_types: set[str],
) -> None:
    """
    Execute the build (internal, called with lock held).
    """
    # Signal build in progress to the request handler via build_state.
    trigger._set_build_in_progress(True)

    try:
        changed_files = [str(p) for p in changed_paths]
        file_count = len(changed_files)

        # Determine file name for display
        if file_count == 1:
            file_name = Path(changed_files[0]).name
        else:
            first_file = Path(changed_files[0]).name
            file_name = f"{first_file} (+{file_count - 1} more)"

        # Determine build strategy
        needs_full_rebuild = trigger._needs_full_rebuild(changed_paths, event_types)
        nav_changed_files = trigger._detect_nav_changes(changed_paths, needs_full_rebuild)
        structural_changed = bool({"created", "deleted", "moved"} & event_types)

        logger.info(
            "rebuild_triggered",
            changed_file_count=file_count,
            changed_files=changed_files[:10],
            build_strategy="full" if needs_full_rebuild else "incremental",
            structural_changed=structural_changed,
        )

        # Display building indicator
        timestamp = get_timestamp()
        cli = get_cli_output()
        cli.file_change_notice(file_name=file_name, timestamp=timestamp)
        show_building_indicator("Rebuilding")

        # RFC: Output Cache Architecture - Capture content hash baseline BEFORE build
        # This enables accurate change detection vs regeneration noise
        if trigger._should_capture_content_hash_baseline(changed_files):
            trigger._reload_controller.capture_content_hash_baseline(trigger.site.output_dir)

        # Run pre-build hooks
        config = trigger.site.config or {}
        # run_pre_build_hooks expects a dict, use .raw for serialization
        raw = getattr(config, "raw", config)
        config_dict: dict[str, Any] = raw if isinstance(raw, dict) else {}

        # Strategy 1: fast asset hot-reload (no rebuild needed)
        if not needs_full_rebuild and trigger._try_fast_asset_reload(
            changed_paths, event_types, config_dict
        ):
            return

        if not run_pre_build_hooks(config_dict, trigger.site.root_path):
            show_error("Pre-build hook failed - skipping build", show_art=False)
            cli.request_log_header()
            logger.error("rebuild_skipped", reason="pre_build_hook_failed")
            return

        # Strategy 2: reactive content path (content-only edit skips full build)
        if not needs_full_rebuild and trigger._run_reactive_build(
            changed_paths, event_types, changed_files, config_dict
        ):
            return

        # Strategy 3: warm incremental/full build on the existing site
        use_incremental = not needs_full_rebuild
        outcome = trigger._run_warm_build(
            changed_paths=changed_paths,
            changed_files=changed_files,
            nav_changed_files=nav_changed_files,
            structural_changed=structural_changed,
            use_incremental=use_incremental,
            cli=cli,
        )
        if outcome is None:
            # Warm build failed; it logged + recovered the site already.
            return
        result, stats, build_duration = outcome

        # Display build stats
        trigger._display_stats(result, use_incremental)

        # Run post-build hooks
        if not run_post_build_hooks(config_dict, trigger.site.root_path):
            logger.warning("post_build_hook_failed", action="continuing")

        # Show server URL
        cli.server_url_inline(host=trigger.host, port=trigger.port)
        cli.request_log_header()

        # Record success for session tracking
        trigger._last_successful_build = datetime.now()
        get_dev_server_state().record_success()

        logger.info(
            "rebuild_complete",
            duration_seconds=round(build_duration, 2),
            pages_built=result.pages_built,
            incremental=use_incremental,
        )

        # Browser-overlay control: if any pages failed to render, push a
        # `build_error` envelope so the SSE client renders the overlay in
        # place. If a previous build had errors and this one is clean,
        # push `build_ok` (which the client treats as both dismiss AND
        # cache-bust reload). Skip the regular reload path in those
        # cases — the overlay messages are the reload signal.
        template_errors = list(getattr(stats, "template_errors", None) or [])
        overlay_handled = trigger._handle_overlay_messages(template_errors, build_duration)

        if overlay_handled:
            trigger._clear_html_cache()
            return

        # Handle reload decision
        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=tuple(changed_files),
                changed_outputs=result.changed_outputs,
                reload_hint=result.reload_hint,
            )
        )

        # Clear HTML cache
        trigger._clear_html_cache()

    except Exception as e:
        # Create dev server error context for rich debugging
        # Use next(iter(...)) instead of pop() to avoid mutating the set
        context = create_dev_error(
            e,
            changed_files=[str(p) for p in changed_paths],
            trigger_file=str(next(iter(changed_paths))) if changed_paths else None,
            last_successful_build=trigger._last_successful_build,
        )

        # Record failure for pattern detection
        error_sig = f"{type(e).__name__}:{str(e)[:50]}"
        is_new = get_dev_server_state().record_failure(error_sig)
        if not is_new:
            logger.warning(
                "recurring_error_detected",
                error_code=ErrorCode.S003.name,
                signature=error_sig,
            )

        logger.error(
            "rebuild_error",
            error_code=ErrorCode.S003.name,
            error=str(e),
            error_type=type(e).__name__,
            likely_cause=context.get_likely_cause(),
            quick_actions=context.quick_actions[:3],
            auto_fixable=context.auto_fixable,
            is_recurring=not is_new,
        )

        # Show auto-fix suggestion if available
        if context.auto_fix_command:
            show_error(f"Build failed: {e}\n\nTry: {context.auto_fix_command}", show_art=False)
    finally:
        trigger._set_build_in_progress(False)


def _run_reactive_build(
    trigger: Any,
    changed_paths: set[Path],
    event_types: set[str],
    changed_files: list[str],
    config_dict: dict[str, Any],
) -> bool:
    """Reactive content path: re-render a single content edit without a build.

    Returns ``True`` when the change was fully handled (the caller should
    return), ``False`` when the reactive path is not applicable or failed
    and the caller should fall through to a warm build. This path has its
    own ``try/except`` and never touches the double-buffer state.
    """
    if not trigger._can_use_reactive_path(changed_paths, event_types):
        return False

    path = next(iter(changed_paths))
    from bengal.core.output import OutputType
    from bengal.server.reactive import ReactiveContentHandler
    from bengal.server.reload_types import SerializedOutputRecord

    handler = ReactiveContentHandler(trigger.site, trigger.site.output_dir)
    try:
        result = handler.handle_content_change(path)
        if result is not None:
            output_path = result.output_path
            # Use path relative to output_dir (matches full build)
            rel_path = output_path
            if output_path.is_absolute() and trigger.site.output_dir:
                with suppress(ValueError):
                    rel_path = output_path.relative_to(trigger.site.output_dir)
            changed_outputs = (
                SerializedOutputRecord(
                    path=str(rel_path),
                    type_value=OutputType.HTML.value,
                    phase="render",
                ),
            )

            # Fragment path: extract #main-content from in-memory
            # rendered HTML (zero-disk — no read-back from disk)
            dev_config = config_dict.get("dev", {}) or {}
            content_selector = dev_config.get("content_selector", "#main-content")
            from bengal.server.live_reload.fragment import extract_main_content
            from bengal.server.live_reload.notification import send_fragment_payload
            from bengal.utils.paths.url_strategy import URLStrategy

            fragment = extract_main_content(result.rendered_html, content_selector)
            if fragment:
                permalink = URLStrategy.url_from_output_path(output_path, trigger.site)
                send_fragment_payload(content_selector, fragment, permalink)
            else:
                trigger._handle_reload(
                    BuildReloadInfo(
                        changed_files=tuple(changed_files),
                        changed_outputs=changed_outputs,
                        reload_hint=None,
                    )
                )
            trigger._clear_html_cache()
            return True
    except Exception as e:
        logger.warning(
            "reactive_path_failed",
            error=str(e),
            fallback="full_build",
        )
    return False


def _run_warm_build(
    trigger: Any,
    *,
    changed_paths: set[Path],
    changed_files: list[str],
    nav_changed_files: set[Path] | None,
    structural_changed: bool,
    use_incremental: bool,
    cli: Any,
) -> tuple[BuildResult, Any, float] | None:
    """Warm incremental/full build that reuses the existing site object.

    Builds into the double-buffer staging directory (when configured),
    swaps on success, and resyncs ``output_dir`` on failure via
    :class:`_DoubleBuffer`. Returns ``(result, stats, build_duration)`` on
    success or ``None`` on failure (after logging + recovering the site).
    """
    # Warm build: reuse the existing site object instead of creating a new
    # one. This eliminates Site.from_config() overhead (~250ms per rebuild).
    from bengal.orchestration.build.options import BuildOptions
    from bengal.utils.observability.profile import BuildProfile

    # Reset all per-build mutable state in one call.
    # Site.prepare_for_rebuild() is the single source of truth for what
    # must be reset between warm builds — including cascade snapshot,
    # content registry, page caches, and URL registry.
    trigger.site.prepare_for_rebuild()

    build_opts = BuildOptions(
        force_sequential=False,  # Auto-detect based on page count
        incremental=use_incremental,
        profile=BuildProfile.WRITER,
        completion_policy=trigger.completion_policy,
        changed_sources={Path(p) for p in changed_files} if changed_files else None,
        nav_changed_sources=nav_changed_files,
        structural_changed=structural_changed,
    )

    # Apply version scope if set
    if trigger.version_scope:
        trigger.site.config["_version_scope"] = trigger.version_scope

    # Double-buffer: redirect output to staging directory so the ASGI
    # app continues serving from the active buffer during the build.
    build_start = time.time()
    with _DoubleBuffer(
        trigger.site,
        trigger._buffer_manager,
        use_incremental=use_incremental,
        last_delta_paths=trigger._last_buffer_delta_paths,
    ) as buffer:
        try:
            stats = trigger.site.build(options=build_opts)
            build_duration = time.time() - build_start

            # Double-buffer: swap staging to active now that the build
            # wrote a complete, consistent snapshot.
            buffer.swap()

            result = trigger._make_build_result(stats, build_duration)
            if trigger._buffer_manager is not None:
                trigger._last_buffer_delta_paths = (
                    trigger._buffer_delta_paths(result.changed_outputs) if use_incremental else None
                )

            # Seed content hash cache so first edit can use reactive path
            trigger.seed_content_hash_cache(list(trigger.site.pages))

        except Exception as e:
            # Resync output_dir with the buffer being served (active if the
            # swap ran, else the pre-build original) before recovering.
            buffer.resync_after_failure()
            if trigger._buffer_manager is not None:
                trigger._last_buffer_delta_paths = None

            # Build crashed - log error and reinitialize site for next build
            build_duration = time.time() - build_start
            error_msg = str(e)

            show_error(f"Build failed: {error_msg}", show_art=False)
            cli.request_log_header()

            # Record failure for pattern detection
            error_sig = f"build_failed:{error_msg[:50] if error_msg else 'unknown'}"
            is_new = get_dev_server_state().record_failure(error_sig)
            if not is_new:
                logger.warning(
                    "recurring_error_detected",
                    error_code=ErrorCode.S003.name,
                    signature=error_sig,
                )

            logger.error(
                "rebuild_failed",
                error_code=ErrorCode.S003.name,
                duration_seconds=round(build_duration, 2),
                error=error_msg,
                changed_files=[str(p) for p in changed_paths][:5],
                is_recurring=not is_new,
            )

            # Reinitialize site from scratch to recover from corrupted
            # state. This ensures the next build starts clean.
            try:
                from bengal.core.site import Site

                logger.info("warm_build_recovery", action="reinitializing_site")
                trigger.site = Site.from_config(trigger.site.root_path)
                trigger.site.dev_mode = True
            except Exception as reinit_error:
                logger.error(
                    "warm_build_recovery_failed",
                    error=str(reinit_error),
                )
            return None

    return result, stats, build_duration
