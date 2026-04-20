"""
Reload notification: send_reload_payload, notify_clients_reload, set_reload_action.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from bengal.errors import ErrorCode
from bengal.utils.observability.logger import get_logger

from .sse import _reload_events_disabled, _state

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = get_logger(__name__)


class LiveReloadNotifier:
    """ReloadNotifier implementation that sends events via SSE."""

    def send(
        self,
        action: str,
        reason: str,
        changed_paths: Sequence[str],
    ) -> None:
        """Delegate to send_reload_payload."""
        send_reload_payload(action, reason, changed_paths)


def send_reload_payload(action: str, reason: str, changed_paths: Sequence[str]) -> None:
    """Send a structured JSON reload event to all connected SSE clients."""
    if _reload_events_disabled():
        logger.info(
            "reload_notification_suppressed",
            reason="env_BENGAL_DISABLE_RELOAD_EVENTS",
            action=action,
        )
        return
    with _state.condition:
        _state.generation += 1
        next_gen = _state.generation
        try:
            payload = json.dumps(
                {
                    "action": action,
                    "reason": reason,
                    "changedPaths": changed_paths,
                    "generation": next_gen,
                }
            )
        except Exception as e:
            logger.warning(
                "reload_payload_serialization_failed",
                error_code=ErrorCode.S003.name,
                action=action,
                reason=reason,
                error=str(e),
            )
            payload = action
        _state.last_action = payload
        _state.sent_count += 1
        _state.condition.notify_all()

    logger.info(
        "reload_notification_sent_structured",
        action=action,
        reason=reason,
        changed=min(len(changed_paths), 5),
        changed_paths=changed_paths[:5],
        generation=_state.generation,
        sent_count=_state.sent_count,
    )
    if os.environ.get("BENGAL_DEBUG_RELOAD"):
        print(f"[Bengal] Reload sent: action={action!r} reason={reason!r}", flush=True)


def notify_clients_reload() -> None:
    """Notify all connected SSE clients to trigger a full page reload."""
    if _reload_events_disabled():
        logger.info("reload_notification_suppressed", reason="env_BENGAL_DISABLE_RELOAD_EVENTS")
        return
    with _state.condition:
        _state.last_action = "reload"
        _state.generation += 1
        _state.condition.notify_all()
    logger.info("reload_notification_sent", generation=_state.generation)


def set_reload_action(action: str) -> None:
    """Set the next reload action type for SSE clients."""
    if action not in ("reload", "reload-css", "reload-page"):
        action = "reload"
    with _state.condition:
        _state.last_action = action
    logger.debug("reload_action_set", action=action)


def send_build_error_payload(payload: dict) -> None:
    """Push a ``build_error`` envelope to all connected SSE clients.

    The payload must already conform to the A0.2 wire schema (see
    :mod:`bengal.errors.overlay.transport`). The notifier only adds
    transport concerns: JSON-encoding, generation bump, condition signal.
    """
    if _reload_events_disabled():
        logger.info(
            "reload_notification_suppressed",
            reason="env_BENGAL_DISABLE_RELOAD_EVENTS",
            action="build_error",
        )
        return
    try:
        encoded = json.dumps(payload)
    except Exception as e:
        logger.warning(
            "build_error_payload_serialization_failed",
            error_code=ErrorCode.S003.name,
            error=str(e),
        )
        return

    with _state.condition:
        _state.last_action = encoded
        _state.generation += 1
        _state.sent_count += 1
        _state.condition.notify_all()

    error_count = len(payload.get("errors", []))
    first_code = ""
    if error_count:
        first_code = payload["errors"][0].get("code") or ""
    logger.info(
        "build_error_notification_sent",
        error_count=error_count,
        first_code=first_code,
        generation=_state.generation,
        sent_count=_state.sent_count,
    )
    if os.environ.get("BENGAL_DEBUG_RELOAD"):
        print(
            f"[Bengal] build_error sent: errors={error_count} first={first_code!r}",
            flush=True,
        )


def send_build_ok_payload(payload: dict) -> None:
    """Push a ``build_ok`` envelope to all connected SSE clients.

    Sent after a successful rebuild that follows a failed build, so the
    overlay can dismiss itself.
    """
    if _reload_events_disabled():
        logger.info(
            "reload_notification_suppressed",
            reason="env_BENGAL_DISABLE_RELOAD_EVENTS",
            action="build_ok",
        )
        return
    try:
        encoded = json.dumps(payload)
    except Exception as e:
        logger.warning(
            "build_ok_payload_serialization_failed",
            error_code=ErrorCode.S003.name,
            error=str(e),
        )
        return

    with _state.condition:
        _state.last_action = encoded
        _state.generation += 1
        _state.sent_count += 1
        _state.condition.notify_all()

    logger.info(
        "build_ok_notification_sent",
        build_ms=payload.get("build_ms"),
        generation=_state.generation,
        sent_count=_state.sent_count,
    )
    if os.environ.get("BENGAL_DEBUG_RELOAD"):
        print(
            f"[Bengal] build_ok sent: build_ms={payload.get('build_ms')!r}",
            flush=True,
        )


def send_fragment_payload(
    selector: str,
    html: str,
    permalink: str,
    *,
    reason: str = "single-page-content",
) -> None:
    """Send a fragment event for instant DOM swap instead of full reload.

    Clients on the matching page will swap innerHTML of the selector;
    others ignore or fall back to full reload.

    Args:
        selector: CSS selector for the target element (e.g. #main-content)
        html: Inner HTML to inject
        permalink: URL path of the page (e.g. /docs/foo/) for client matching
        reason: Optional reason string for logging
    """
    if _reload_events_disabled():
        logger.info(
            "reload_notification_suppressed",
            reason="env_BENGAL_DISABLE_RELOAD_EVENTS",
            action="fragment",
        )
        return
    try:
        payload = json.dumps(
            {
                "action": "fragment",
                "selector": selector,
                "html": html,
                "permalink": permalink,
                "reason": reason,
            }
        )
    except Exception as e:
        logger.warning(
            "fragment_payload_serialization_failed",
            error_code=ErrorCode.S003.name,
            error=str(e),
        )
        return

    with _state.condition:
        _state.last_action = payload
        _state.generation += 1
        _state.sent_count += 1
        _state.condition.notify_all()

    logger.info(
        "fragment_notification_sent",
        selector=selector,
        permalink=permalink,
        html_len=len(html),
        generation=_state.generation,
    )
    if os.environ.get("BENGAL_DEBUG_RELOAD"):
        print(
            f"[Bengal] Fragment sent: selector={selector!r} permalink={permalink!r}",
            flush=True,
        )
