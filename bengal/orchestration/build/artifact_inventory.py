"""Build artifact inventory helpers.

The hot-reload output collector records files changed during a build. Health
checks need a different inventory: generated artifacts that exist after
postprocess, even if unchanged. This module keeps that inventory explicit so
validators do not have to infer generated URLs from scattered config.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal, cast

from bengal.core.output import OutputType
from bengal.postprocess.output_formats import OutputFormatsGenerator
from bengal.postprocess.output_formats.utils import (
    get_i18n_output_path,
    get_page_json_path,
    get_page_md_path,
    get_page_txt_path,
)

if TYPE_CHECKING:
    from pathlib import Path

    from bengal.protocols import OutputCollector

_SITE_WIDE_OUTPUTS = {
    "index_json": "index.json",
    "llm_full": "llm-full.txt",
    "llms_txt": "llms.txt",
    "changelog": "changelog.json",
    "agent_manifest": "agent.json",
}


def populate_artifact_inventory(site: Any, build_context: Any | None) -> None:
    """Populate build_context.artifact_collector with existing generated outputs."""
    if build_context is None or build_context.artifact_collector is None:
        return

    collector = build_context.artifact_collector
    seen: set[Path] = set()

    changed_collector = getattr(build_context, "output_collector", None)
    if changed_collector is not None:
        for record in changed_collector.get_outputs():
            _record_existing(collector, site, record.path, record.output_type, record.phase, seen)

    for page in getattr(site, "pages", []):
        output_path = getattr(page, "output_path", None)
        if output_path:
            _record_existing(collector, site, output_path, OutputType.HTML, "render", seen)

    output_config: dict[str, Any] = OutputFormatsGenerator(
        site,
        getattr(site, "config", {}).get("output_formats", {}),
    ).config
    if output_config.get("enabled", True):
        _record_output_format_artifacts(site, collector, output_config, seen)

    output_dir = site.output_dir
    _record_existing(
        collector, site, output_dir / "sitemap.xml", OutputType.XML, "postprocess", seen
    )
    _record_existing(
        collector, site, output_dir / "robots.txt", OutputType.ASSET, "postprocess", seen
    )
    _record_existing(
        collector,
        site,
        output_dir / ".well-known" / "content-signals.json",
        OutputType.JSON,
        "postprocess",
        seen,
    )

    for path in _rss_output_paths(site):
        _record_existing(collector, site, path, OutputType.XML, "postprocess", seen)


def _record_output_format_artifacts(
    site: Any,
    collector: OutputCollector,
    output_config: dict[str, Any],
    seen: set[Path],
) -> None:
    """Record existing per-page and site-wide output-format artifacts."""
    per_page = set(output_config.get("per_page", []))
    for page in getattr(site, "pages", []):
        if "json" in per_page:
            _record_existing(
                collector, site, get_page_json_path(page), OutputType.JSON, "postprocess", seen
            )
        if "llm_txt" in per_page:
            _record_existing(
                collector, site, get_page_txt_path(page), OutputType.ASSET, "postprocess", seen
            )
        if "markdown" in per_page:
            _record_existing(
                collector, site, get_page_md_path(page), OutputType.ASSET, "postprocess", seen
            )

    for output_format in output_config.get("site_wide", []):
        filename = _SITE_WIDE_OUTPUTS.get(str(output_format))
        if filename:
            _record_existing(
                collector,
                site,
                get_i18n_output_path(site, filename),
                _output_type_for_filename(filename),
                "postprocess",
                seen,
            )


def _record_existing(
    collector: OutputCollector,
    site: Any,
    path: Path | None,
    output_type: OutputType,
    phase: Literal["render", "asset", "postprocess"],
    seen: set[Path],
) -> None:
    """Record path if it exists, normalizing to an absolute output path."""
    if path is None:
        return
    output_dir = site.output_dir
    output_path = path if path.is_absolute() else output_dir / path
    if output_path in seen or not output_path.exists():
        return
    seen.add(output_path)
    collector.record(output_path, output_type, phase=phase)


def _output_type_for_filename(filename: str) -> OutputType:
    """Return an output type for a generated filename."""
    return OutputType.JSON if filename.endswith(".json") else OutputType.ASSET


def _rss_output_paths(site: Any) -> list[Path]:
    """Return possible RSS output paths for the site's i18n configuration."""
    config = getattr(site, "config", {})
    if not config.get("generate_rss", True):
        return []

    output_dir = site.output_dir
    i18n = config.get("i18n", {}) or {}
    languages = i18n.get("languages") or [i18n.get("default_language", "en")]
    default_lang = i18n.get("default_language", "en")
    default_in_subdir = bool(i18n.get("default_in_subdir", False))
    strategy = i18n.get("strategy")

    paths: list[Path] = []
    for lang in languages:
        code = _language_code(lang)
        if not code:
            continue
        if strategy == "prefix" and (default_in_subdir or code != default_lang):
            paths.append(output_dir / code / "rss.xml")
        elif code == default_lang:
            paths.append(output_dir / "rss.xml")
        else:
            paths.append(output_dir / code / "rss.xml")
    return paths


def _language_code(lang: object) -> str:
    """Return a normalized i18n language code from string or mapping config."""
    if isinstance(lang, str):
        return lang
    if isinstance(lang, Mapping):
        language = cast("Mapping[str, object]", lang)
        code = language.get("code") or language.get("language") or language.get("id")
        return str(code) if code else ""
    return str(lang)
