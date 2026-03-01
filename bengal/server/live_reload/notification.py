"""
Reload notification: send_reload_payload, notify_clients_reload, set_reload_action.
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence

from bengal.errors import ErrorCode
from bengal.utils.observability.logger import get_logger

from .sse import _reload_events_disabled, _state

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
    try:
        payload = json.dumps(
            {
                "action": action,
                "reason": reason,
                "changedPaths": changed_paths,
                "generation": _state.generation + 1,
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

    with _state.condition:
        _state.last_action = payload
        _state.generation += 1
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
