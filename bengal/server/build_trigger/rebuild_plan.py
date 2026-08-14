"""Rebuild plan helpers: double-buffering and direct asset copies.

Owns the staging/swap/resync invariant and the fast asset hot-reload
path that copies static/asset edits straight to served output.
"""

from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from bengal.orchestration.stats import ReloadHint
from bengal.server.reload_types import BuildReloadInfo
from bengal.utils.observability.logger import get_logger

logger = get_logger("bengal.server.build_trigger")

if TYPE_CHECKING:
    from bengal.protocols import SiteLike
    from bengal.server.buffer_manager import BufferManager


class _DoubleBuffer:
    """Centralizes the dev-server double-buffer prepare/swap/resync invariant.

    The dev server writes each rebuild into a *staging* buffer so the ASGI app
    keeps serving the previous, complete snapshot. On success the build calls
    :meth:`swap` to make staging the active buffer; on failure the context
    manager resyncs ``site.output_dir`` so it always points at the buffer that
    is actually being served:

    - If :meth:`swap` already ran, ``output_dir`` follows the new active buffer.
    - If it has not, ``output_dir`` reverts to the pre-build directory.

    With no :class:`BufferManager` configured this is a no-op shim that simply
    leaves ``site.output_dir`` untouched.
    """

    def __init__(
        self,
        site: SiteLike,
        buffer_manager: BufferManager | None,
        *,
        use_incremental: bool,
        last_delta_paths: tuple[Path, ...] | None,
    ) -> None:
        self._site = site
        self._buffer_manager = buffer_manager
        self._use_incremental = use_incremental
        self._last_delta_paths = last_delta_paths
        self._original_output_dir = site.output_dir
        self.swapped = False

    def __enter__(self) -> _DoubleBuffer:
        """Redirect ``site.output_dir`` to the prepared staging buffer."""
        if self._buffer_manager is None:
            return self

        if self._use_incremental and self._last_delta_paths is not None:
            # asset-manifest.json describes the currently-served buffer and is
            # not rewritten on content-only rebuilds, so it never lands in the
            # delta paths — sync it from active every time so the staging buffer
            # (and thus the next active buffer) never serves a stale/divergent
            # manifest that blinds the asset output-integrity check (#315).
            staging = self._buffer_manager.prepare_delta_staging(
                self._last_delta_paths,
                always_sync=("asset-manifest.json",),
            )
        else:
            staging = self._buffer_manager.prepare_staging()
        self._site.output_dir = staging
        logger.debug(
            "build_to_staging",
            staging=str(staging),
            active=str(self._buffer_manager.active_dir),
        )
        return self

    def swap(self) -> None:
        """Swap staging to active now the build wrote a consistent snapshot."""
        if self._buffer_manager is None:
            return
        self._buffer_manager.swap()
        self.swapped = True
        self._site.output_dir = self._buffer_manager.active_dir
        logger.debug(
            "buffer_swapped",
            active=str(self._buffer_manager.active_dir),
            generation=self._buffer_manager.generation,
        )

    def resync_after_failure(self) -> None:
        """Point ``output_dir`` at the buffer that is actually being served.

        Call this when the build failed but the exception was handled inside
        the ``with`` block (so it never reaches :meth:`__exit__`). If
        :meth:`swap` already ran the new active buffer is being served;
        otherwise serving never moved off the pre-build directory.
        """
        if self._buffer_manager is None:
            return
        if self.swapped:
            self._site.output_dir = self._buffer_manager.active_dir
        else:
            self._site.output_dir = self._original_output_dir

    def __exit__(self, exc_type: object, exc: object, tb: object) -> Literal[False]:
        """Backstop: resync if an exception propagates out of the ``with``.

        The warm-build path normally handles its own failure inside the block
        and calls :meth:`resync_after_failure` directly, so this only fires for
        an unexpected escape. Never suppresses the exception.
        """
        if exc_type is not None:
            self.resync_after_failure()
        return False


def _try_fast_asset_reload(
    trigger: Any,
    changed_paths: set[Path],
    event_types: set[str],
    config: dict[str, Any],
) -> bool:
    """Copy direct asset/static edits to output without running a warm build."""
    mapped = trigger._direct_asset_output_mappings(changed_paths, event_types, config)
    if mapped is None:
        return False

    from bengal.core.output import OutputRecord, OutputType
    from bengal.server.reload_types import SerializedOutputRecord
    from bengal.utils.io.atomic_write import atomic_write_bytes

    changed_outputs: list[SerializedOutputRecord] = []
    written = 0

    try:
        for source, rel_output, phase in mapped:
            source_mode = source.stat().st_mode & 0o777
            content = source.read_bytes()
            for output_root in trigger._served_output_roots():
                atomic_write_bytes(output_root / rel_output, content, mode=source_mode)
                written += 1

            record = OutputRecord.from_path(rel_output, phase=phase)
            changed_outputs.append(
                SerializedOutputRecord(
                    path=str(rel_output),
                    type_value=record.output_type.value,
                    phase=record.phase,
                )
            )

        reload_hint = (
            ReloadHint.CSS_ONLY
            if changed_outputs
            and all(record.type_value == OutputType.CSS.value for record in changed_outputs)
            else ReloadHint.FULL
        )
        trigger._handle_reload(
            BuildReloadInfo(
                changed_files=tuple(str(path) for path in changed_paths),
                changed_outputs=tuple(changed_outputs),
                reload_hint=reload_hint,
            )
        )
        trigger._clear_html_cache()
        logger.info(
            "fast_asset_reload_complete",
            changed_files=len(changed_paths),
            outputs=len(changed_outputs),
            writes=written,
            reload_hint=reload_hint.value,
        )
        return True
    except OSError as exc:
        logger.warning(
            "fast_asset_reload_failed",
            error=str(exc),
            fallback="warm_build",
        )
        return False


def _direct_asset_output_mappings(
    trigger: Any,
    changed_paths: set[Path],
    event_types: set[str],
    config: dict[str, Any],
) -> tuple[tuple[Path, Path, Literal["asset"]], ...] | None:
    """Return source-to-output mappings when a direct asset copy is safe."""
    if not changed_paths or event_types != {"modified"}:
        return None
    if trigger._has_configured_build_hooks(config):
        return None

    mappings: list[tuple[Path, Path, Literal["asset"]]] = []
    static_root = trigger._static_source_root(config)
    asset_root = trigger.site.root_path / "assets"

    for changed_path in changed_paths:
        source = changed_path
        if not source.is_file():
            return None

        static_rel = trigger._relative_to(source, static_root)
        if static_rel is not None:
            if not trigger._active_output_exists(static_rel):
                return None
            mappings.append((source, static_rel, "asset"))
            continue

        asset_rel = trigger._relative_to(source, asset_root)
        if asset_rel is None:
            return None
        if not trigger._can_copy_site_asset_directly(source):
            return None

        output_rel = Path("assets") / asset_rel
        if not trigger._active_output_exists(output_rel):
            return None
        mappings.append((source, output_rel, "asset"))

    return tuple(mappings)


def _has_configured_build_hooks(trigger: Any, config: dict[str, Any]) -> bool:
    """Return True when external hooks must participate in rebuilds."""
    dev_server = config.get("dev_server", {})
    if not isinstance(dev_server, dict):
        return False
    return bool(dev_server.get("pre_build") or dev_server.get("post_build"))


def _static_source_root(trigger: Any, config: dict[str, Any]) -> Path:
    """Return configured static source root."""
    static_config = config.get("static", {})
    if not isinstance(static_config, dict):
        static_config = {}
    static_dir_name = static_config.get("dir", "static")
    return trigger.site.root_path / str(static_dir_name)


def _can_copy_site_asset_directly(trigger: Any, source: Path) -> bool:
    """Return True when the asset pipeline would preserve this file verbatim."""
    config = trigger.site.config or {}
    if config.get("fingerprint_assets", True):
        return False

    suffix = source.suffix.lower()
    if suffix in {".css", ".js", ".mjs"} and config.get("minify_assets", True):
        return False
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico"} and config.get(
        "optimize_assets", True
    ):
        return False

    asset = trigger._site_asset_for_source(source)
    if asset is None:
        return False
    if suffix == ".css" and (
        asset.is_css_entry_point() or (asset.is_css_module() and not asset.standalone)
    ):
        return False

    assets_config = getattr(getattr(trigger.site, "config_service", None), "assets_config", {})
    if isinstance(assets_config, dict) and assets_config.get("bundle_js", False):
        with suppress(AttributeError):
            if asset.is_js_module():
                return False

    return True


def _site_asset_for_source(trigger: Any, source: Path) -> Any | None:
    """Find the discovered site asset for a source path."""
    try:
        resolved = source.resolve()
    except OSError:
        resolved = source

    for asset in getattr(trigger.site, "assets", []):
        asset_source = getattr(asset, "source_path", None)
        if asset_source is None:
            continue
        try:
            if Path(asset_source).resolve() == resolved:
                return asset
        except OSError, TypeError, ValueError:
            continue
    return None


def _served_output_roots(trigger: Any) -> tuple[Path, ...]:
    """Return output roots that should stay current for direct asset edits."""
    if trigger._buffer_manager is None:
        return (trigger.site.output_dir,)

    roots: list[Path] = []
    for root in (trigger._buffer_manager.active_dir, trigger._buffer_manager.staging_dir):
        if root not in roots:
            roots.append(root)
    return tuple(roots)


def _buffer_delta_paths(
    trigger: Any,
    changed_outputs: tuple[Any, ...],
) -> tuple[Path, ...] | None:
    """Normalize changed output records for the next buffered rebuild."""
    paths: list[Path] = []
    seen: set[Path] = set()
    active_root = (
        trigger._buffer_manager.active_dir
        if trigger._buffer_manager is not None
        else trigger.site.output_dir
    )

    for output in changed_outputs:
        raw_path = Path(getattr(output, "path", ""))
        if raw_path == Path("."):
            continue
        if raw_path.is_absolute():
            try:
                raw_path = raw_path.resolve().relative_to(active_root.resolve())
            except OSError, ValueError:
                return None
        if any(part == ".." for part in raw_path.parts):
            return None
        if raw_path not in seen:
            seen.add(raw_path)
            paths.append(raw_path)

    return tuple(paths)


def _active_output_exists(trigger: Any, rel_output: Path) -> bool:
    """Return True when the currently served output already exists."""
    output_root = (
        trigger._buffer_manager.active_dir
        if trigger._buffer_manager is not None
        else trigger.site.output_dir
    )
    return (output_root / rel_output).is_file()


def _relative_to(trigger: Any, path: Path, root: Path) -> Path | None:
    """Return path relative to root, resolving symlinks where possible."""
    try:
        return path.resolve().relative_to(root.resolve())
    except OSError, ValueError:
        return None
