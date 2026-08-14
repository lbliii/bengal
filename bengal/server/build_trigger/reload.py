"""Reload, overlay, and post-build presentation for the rebuild loop.

Turns a finished (or failed) rebuild into stats, browser-overlay messages,
and a typed reload decision.
"""

from typing import TYPE_CHECKING, Any

from bengal.errors import ErrorCode
from bengal.orchestration.stats import ReloadHint, display_build_stats
from bengal.server.build_executor import BuildResult
from bengal.server.build_state import build_state
from bengal.server.reload_controller import ReloadDecision
from bengal.utils.observability.logger import get_logger
from bengal.utils.stats_minimal import MinimalStats

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bengal.server.reload_types import BuildReloadInfo

logger = get_logger("bengal.server.build_trigger")


def _make_build_result(trigger: Any, stats: Any, build_duration: float) -> BuildResult:
    """Adapt warm-build ``stats`` into the module-level :class:`BuildResult`.

    Mirrors the subprocess :class:`BuildResult` so ``_display_stats`` and the
    reload path see the same type whether the build ran warm or out-of-process.
    """
    from bengal.server.reload_types import SerializedOutputRecord

    changed_outputs: tuple[SerializedOutputRecord, ...] = (
        tuple(
            SerializedOutputRecord(
                path=str(r.path),
                type_value=r.output_type.value,
                phase=r.phase,
            )
            for r in stats.changed_outputs
        )
        if hasattr(stats, "changed_outputs")
        else ()
    )
    return BuildResult(
        success=True,
        pages_built=stats.total_pages,
        build_time_ms=build_duration * 1000,
        error_message=None,
        changed_outputs=changed_outputs,
        reload_hint=stats.reload_hint,
        completion_policy=trigger.completion_policy,
    )


def _display_stats(trigger: Any, result: BuildResult, incremental: bool) -> None:
    """Display build statistics using MinimalStats adapter."""
    stats = MinimalStats.from_build_result(result, incremental=incremental)
    display_build_stats(stats, show_art=False, output_dir=str(trigger.site.output_dir))


def _handle_overlay_messages(
    trigger: Any, template_errors: list[Any], build_duration: float
) -> bool:
    """Push browser-overlay control messages over SSE.

    Returns ``True`` when the overlay messages take ownership of the
    client-notification slot for this build, signalling the caller to
    skip the regular reload path. Returns ``False`` when the build is
    clean and was preceded by another clean build (no overlay state).
    """
    from bengal.errors.overlay import build_error_payload, build_ok_payload
    from bengal.server.live_reload.notification import (
        send_build_error_payload,
        send_build_ok_payload,
    )

    if template_errors:
        try:
            payload = build_error_payload(template_errors)
            send_build_error_payload(payload)
        except Exception as exc:
            logger.warning(
                "build_error_overlay_send_failed",
                error_code=ErrorCode.S003.name,
                error=str(exc),
            )
            # Fall through to normal reload — the per-page overlay
            # HTML written to disk still gives the developer a useful
            # page even without the live overlay.
            return False
        trigger._had_template_errors_last_build = True
        return True

    if trigger._had_template_errors_last_build:
        try:
            payload = build_ok_payload(build_ms=int(build_duration * 1000))
            send_build_ok_payload(payload)
        except Exception as exc:
            logger.warning(
                "build_ok_overlay_send_failed",
                error_code=ErrorCode.S003.name,
                error=str(exc),
            )
            # Fall through to normal reload so the user still gets a
            # refresh; the overlay JS treats a plain `reload` as a
            # dismiss as well.
            trigger._had_template_errors_last_build = False
            return False
        trigger._had_template_errors_last_build = False
        return True

    return False


def _handle_reload(trigger: Any, info: BuildReloadInfo) -> None:
    """Handle reload decision and notification.

    Decision flow:
    1. reload_hint=NONE + typed outputs → suppress (build knows no reload needed)
    2. Typed outputs available → use ReloadController for CSS vs full
    3. No outputs but changed_files → full reload (fallback when output collector empty)
    4. Neither → suppress

    Args:
        info: BuildReloadInfo from build (changed_files, changed_outputs, reload_hint)
    """
    changed_files = list(info.changed_files)
    changed_outputs = info.changed_outputs
    reload_hint = info.reload_hint

    # Trust reload_hint=NONE only when we have typed outputs (build can confirm)
    if reload_hint is ReloadHint.NONE and changed_outputs:
        logger.info("reload_suppressed", reason="reload-hint-none")
        return

    decision: ReloadDecision | None = None
    decision_source = "none"

    # Primary: typed outputs from build
    if changed_outputs:
        from bengal.core.output import OutputType

        records = []
        for rec in changed_outputs:
            try:
                if rec.phase in ("render", "asset", "postprocess"):
                    records.append(rec.to_output_record())
            except ValueError, TypeError:
                logger.debug("invalid_output_type", path=rec.path, type_val=rec.type_value)

        if records:
            decision = trigger._reload_controller.decide_from_outputs(
                records, reload_hint=reload_hint
            )
            decision_source = "typed-outputs"
            logger.debug(
                "reload_from_typed_outputs",
                output_count=len(records),
                css_count=sum(1 for r in records if r.output_type == OutputType.CSS),
            )
        else:
            # Fallback: Path-based decision (when type reconstruction fails)
            paths = [rec.path for rec in changed_outputs]
            decision = trigger._reload_controller.decide_from_changed_paths(paths)
            decision_source = "fallback-paths"
            logger.debug(
                "reload_decision_fallback",
                reason="typed_output_reconstruction_failed",
                output_count=len(changed_outputs),
            )

    # Fallback: If sources changed but no typed outputs were recorded, trigger full reload
    # This handles cases where the output collector didn't receive records (e.g., subprocess
    # serialization issues, early exit paths, or collector not being passed through).
    if decision is None:
        if changed_files:
            # Sources changed, but no typed outputs - fall back to full reload
            decision = ReloadDecision(
                action="reload", reason="source-change-no-outputs", changed_paths=()
            )
            decision_source = "fallback-source-change"
            logger.debug(
                "reload_fallback_no_outputs",
                changed_files_count=len(changed_files),
                changed_files=changed_files[:5],
            )
        else:
            # No sources changed and no outputs - suppress reload
            decision = ReloadDecision(action="none", reason="no-changes", changed_paths=())
            decision_source = "no-changes"
            logger.debug("reload_suppressed_no_changes")

    # Content-hash filter: aggregate-only (sitemap, feeds) → no reload.
    # Skip when: (1) fallback-source-change, or (2) user edited source files.
    # If changed_files is non-empty, user triggered a build—don't suppress reload.
    if (
        decision.action == "reload"
        and decision_source != "fallback-source-change"
        and not changed_files
        and trigger._reload_controller._use_content_hashes
        and hasattr(trigger._reload_controller, "_baseline_content_hashes")
        and trigger._reload_controller._baseline_content_hashes
    ):
        enhanced = trigger._reload_controller.decide_with_content_hashes(trigger.site.output_dir)
        if enhanced.meaningful_change_count == 0:
            # All changes are aggregate-only (sitemap, feeds, search index)
            decision = ReloadDecision(
                action="none",
                reason="aggregate-only",
                changed_paths=(),
            )
            decision_source = "content-hash-filtered"
            logger.info(
                "reload_filtered_aggregate_only",
                total_changes=len(enhanced.aggregate_changes),
            )
        else:
            # Update with accurate change count
            decision_source = f"{decision_source}+content-hash"
            logger.debug(
                "content_hash_breakdown",
                content_changes=len(enhanced.content_changes),
                aggregate_changes=len(enhanced.aggregate_changes),
                asset_changes=len(enhanced.asset_changes),
            )

    # Log decision source for observability
    logger.debug(
        "reload_decision_source",
        source=decision_source,
        action=decision.action,
        reason=decision.reason,
    )

    # Send reload notification
    if decision.action == "none":
        logger.info("reload_suppressed", reason=decision.reason)
        # Safety: user changed files but decision is none (e.g. throttled).
        # Send reload unless we trust aggregate-only (sitemap/feeds only).
        if changed_files and decision.reason != "aggregate-only":
            logger.info(
                "reload_bypass_source_changes",
                reason="changed_files_nonempty_decision_none",
                changed_count=len(changed_files),
            )
            trigger._reload_notifier.send("reload", "source-changes-bypass", ())
        return

    logger.info(
        "reload_decision",
        action=decision.action,
        reason=decision.reason,
        source=decision_source,
    )
    trigger._reload_notifier.send(decision.action, decision.reason, decision.changed_paths)


def _should_capture_content_hash_baseline(trigger: Any, changed_files: Sequence[str]) -> bool:
    """Return whether this build still needs pre-build output hash scanning."""
    return trigger._reload_controller._use_content_hashes and not changed_files


def _set_build_in_progress(trigger: Any, building: bool) -> None:
    """Signal build state to shared registry (handler and ASGI app read from it)."""
    try:
        build_state.set_build_in_progress(building)
    except Exception as e:
        logger.debug("build_state_signal_failed", error=str(e))


def _clear_html_cache(trigger: Any) -> None:
    """Clear HTML injection cache after rebuild."""
    try:
        from bengal.server.live_reload import LiveReloadMixin

        with LiveReloadMixin._html_cache_lock:
            cache_size = len(LiveReloadMixin._html_cache)
            LiveReloadMixin._html_cache.clear()

        if cache_size > 0:
            logger.debug("html_cache_cleared", entries=cache_size)
    except Exception as e:
        logger.debug("html_cache_clear_failed", error=str(e))
