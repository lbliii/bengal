"""Serve-ability smoke check for the dev server (#398).

Bengal's build-time checks (``bengal.health``, ``inspect_asset_outputs``) verify
that output *bytes exist on disk* — they never verify those outputs are actually
*reachable over HTTP* from the running dev server. The hidden-buffer bug (#392,
upstream lbliii/pounce#74) is the canonical failure: the CSS was on disk in both
buffers, the build was perfect, yet ~half of asset requests 404'd because the
active buffer (``.bengal/staging``) could not be served. Nothing caught it until
a user saw an unstyled page.

This module shifts that check left: once the server is listening, request a known
asset (chosen from ``asset-manifest.json``, falling back to ``index.html``) against
the *real* serving setup and assert it returns 200. On failure we fail startup
loudly with the buffer path, the serving directory, and the reason — instead of
letting users discover it as silent 404s.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bengal.assets.manifest import select_smoke_probe_asset
from bengal.utils.observability.logger import get_logger

if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)

# Fallback probe target when no manifest asset can be resolved. ``index.html`` is
# always present once a build has produced servable output.
_FALLBACK_PROBE_PATH = "/"


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Outcome of a serve-ability smoke probe."""

    ok: bool
    url: str
    probe_path: str
    status: int | None
    reason: str | None = None


def choose_probe_path(serving_dir: Path) -> str:
    """Return the URL path to probe for serve-ability.

    Prefers a known asset from the manifest (the #392 symptom was asset 404s);
    falls back to ``"/"`` (``index.html``) when the manifest is empty or none of
    its entries resolve to an on-disk file.
    """
    asset_path = select_smoke_probe_asset(serving_dir)
    return asset_path if asset_path else _FALLBACK_PROBE_PATH


def probe_serve_ability(
    host: str,
    port: int,
    serving_dir: Path,
    *,
    timeout: float = 5.0,
    attempts: int = 20,
    retry_interval: float = 0.15,
) -> ProbeResult:
    """Issue an HTTP GET for a known asset and verify it returns 200.

    Coordinates with backend readiness by retrying connection errors (the server
    thread may still be binding) up to ``attempts`` times; a non-200 *response*
    is treated as a hard failure immediately — that is a serve-path bug, not a
    not-yet-listening race.

    Args:
        host: Server bind host.
        port: Server port.
        serving_dir: The active buffer the ASGI app serves from. Used to choose
            the probe target and reported in diagnostics.
        timeout: Per-request timeout in seconds.
        attempts: Max connection attempts while the server comes up.
        retry_interval: Seconds to sleep between connection retries.

    Returns:
        A :class:`ProbeResult`. ``ok`` is True only when the probe got a 200/304.
    """
    probe_path = choose_probe_path(serving_dir)
    probe_host = "localhost" if host in {"", "0.0.0.0", "::", "::1"} else host  # noqa: S104
    url = f"http://{probe_host}:{port}{probe_path}"

    last_reason: str | None = None
    for _attempt in range(max(1, attempts)):
        try:
            with urlopen(Request(url, method="GET"), timeout=timeout) as resp:
                status = resp.status
                if status in (200, 304):
                    logger.debug("serve_probe_ok", url=url, status=status)
                    return ProbeResult(ok=True, url=url, probe_path=probe_path, status=status)
                return ProbeResult(
                    ok=False,
                    url=url,
                    probe_path=probe_path,
                    status=status,
                    reason=f"server returned HTTP {status} for a known asset",
                )
        except HTTPError as exc:
            # An HTTP error status (e.g. 404) is a definitive serve-path failure —
            # the canonical #392 symptom is a 404 for a file present on disk.
            return ProbeResult(
                ok=False,
                url=url,
                probe_path=probe_path,
                status=exc.code,
                reason=f"server returned HTTP {exc.code} for a known asset",
            )
        except (URLError, OSError) as exc:
            # Connection refused / reset: server may still be binding. Retry.
            last_reason = str(getattr(exc, "reason", exc) or exc)
            time.sleep(retry_interval)

    return ProbeResult(
        ok=False,
        url=url,
        probe_path=probe_path,
        status=None,
        reason=f"could not connect to server: {last_reason}",
    )


def format_probe_failure(result: ProbeResult, *, serving_dir: Path, staging_dir: Path) -> str:
    """Build a loud, actionable failure message for a failed serve probe.

    References #392 / pounce#74, the canonical serve-path failure where assets
    are present on disk but 404 because the active buffer lives under a hidden
    (dot-prefixed) directory that Pounce's static handler rejects.
    """
    return (
        "Dev server serve-ability smoke check FAILED.\n"
        f"  probe URL:    {result.url}\n"
        f"  HTTP status:  {result.status if result.status is not None else 'no response'}\n"
        f"  reason:       {result.reason}\n"
        f"  serving dir:  {serving_dir}\n"
        f"  staging dir:  {staging_dir}\n"
        "The build wrote output to disk but it is not reachable over HTTP. This is the "
        "serve-path failure class from #392 (upstream lbliii/pounce#74): assets can be "
        "present on disk yet 404 when the active buffer lives under a hidden (dot-prefixed) "
        "directory the static handler rejects."
    )
