"""Shared post-render pipeline benchmark harness.

The harness intentionally measures the work after rendering because that is the
tail authors feel after the "Track assets" phase completes.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions
from bengal.orchestration.stats.models import BuildStats, ReloadHint
from bengal.utils.observability.profile import BuildProfile

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class StoreSizes:
    """Measured byte sizes for persistent build state stores."""

    state_total_bytes: int
    main_cache_bytes: int
    page_artifact_bytes: int
    effects_bytes: int
    generated_page_cache_bytes: int
    page_artifact_file_count: int


@dataclass(frozen=True)
class PostRenderMetrics:
    """Metrics for one build in the post-render pipeline harness."""

    scenario: str
    timestamp: str
    wall_time_ms: float
    build_time_ms: float
    total_pages: int
    pages_rendered: int
    changed_output_count: int
    reload_hint: str | None
    rendering_time_ms: float
    assets_time_ms: float
    postprocess_time_ms: float
    health_check_time_ms: float
    postprocess_task_timings_ms: dict[str, float] = field(default_factory=dict)
    postprocess_output_timings_ms: dict[str, float] = field(default_factory=dict)
    post_render_timings_ms: dict[str, float] = field(default_factory=dict)
    store_sizes: StoreSizes | None = None

    @property
    def tail_time_ms(self) -> float:
        """Measured post-render tail from tracked phase timings."""
        post_render_total = sum(self.post_render_timings_ms.values())
        return self.postprocess_time_ms + self.health_check_time_ms + post_render_total

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["tail_time_ms"] = round(self.tail_time_ms, 1)
        return data


def create_post_render_site(root: Path, *, page_count: int = 100) -> Path:
    """Create a deterministic docs-like fixture for post-render timing."""
    site_root = root / "post-render-site"
    content_dir = site_root / "content"
    assets_dir = site_root / "assets" / "css"
    content_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    (site_root / "bengal.toml").write_text(
        """
[site]
title = "Post Render Benchmark"
baseurl = "/"

[build]
output_dir = "public"
incremental = true
parallel = true

[output_formats]
enabled = true
per_page = ["json", "llm_txt"]
site_wide = ["index_json", "llms_txt", "agent_manifest"]

[health_check]
enabled = true
""",
        encoding="utf-8",
    )

    (assets_dir / "site.css").write_text(
        """
:root { color-scheme: light; }
body { font-family: system-ui, sans-serif; margin: 0; }
.doc { max-width: 72ch; margin: 0 auto; padding: 2rem; }
""",
        encoding="utf-8",
    )

    (content_dir / "index.md").write_text(
        "---\ntitle: Home\n---\n# Home\n\nWelcome to the post-render benchmark.\n",
        encoding="utf-8",
    )
    for section_idx in range(max(1, page_count // 25)):
        section_dir = content_dir / f"section-{section_idx + 1:02d}"
        section_dir.mkdir(exist_ok=True)
        (section_dir / "_index.md").write_text(
            f"---\ntitle: Section {section_idx + 1}\n---\n# Section {section_idx + 1}\n",
            encoding="utf-8",
        )

    for idx in range(page_count):
        section_dir = content_dir / f"section-{idx // 25 + 1:02d}"
        section_dir.mkdir(exist_ok=True)
        (section_dir / f"page-{idx + 1:04d}.md").write_text(
            f"""---
title: "Page {idx + 1}"
date: 2026-01-{idx % 28 + 1:02d}
tags: ["bench", "tag-{idx % 7}"]
---

# Page {idx + 1}

This page exists to exercise post-render artifacts.

## Details

The content is deterministic so benchmark output can be compared over time.
""",
            encoding="utf-8",
        )

    return site_root


def collect_store_sizes(site: Site) -> StoreSizes:
    """Measure the durable build-state stores used by the benchmark."""
    state_dir = site.config_service.paths.state_dir
    page_artifacts_dir = state_dir / "page-artifacts"

    def file_size(path: Path) -> int:
        return path.stat().st_size if path.exists() and path.is_file() else 0

    def tree_size(path: Path) -> int:
        if not path.exists():
            return 0
        return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())

    page_artifact_files = (
        sum(1 for item in page_artifacts_dir.rglob("*") if item.is_file())
        if page_artifacts_dir.exists()
        else 0
    )
    return StoreSizes(
        state_total_bytes=tree_size(state_dir),
        main_cache_bytes=file_size(state_dir / "cache.json.zst"),
        page_artifact_bytes=tree_size(page_artifacts_dir),
        effects_bytes=file_size(state_dir / "effects.json"),
        generated_page_cache_bytes=file_size(state_dir / "generated_page_cache.json"),
        page_artifact_file_count=page_artifact_files,
    )


def run_build(site: Site, scenario: str, options: BuildOptions) -> PostRenderMetrics:
    """Run one build and collect post-render metrics."""
    start = time.perf_counter()
    stats = site.build(options)
    wall_time_ms = (time.perf_counter() - start) * 1000
    return metrics_from_stats(site, scenario, stats, wall_time_ms)


def metrics_from_stats(
    site: Site,
    scenario: str,
    stats: BuildStats,
    wall_time_ms: float,
) -> PostRenderMetrics:
    """Convert BuildStats to stable benchmark metrics."""
    reload_hint = stats.reload_hint.value if isinstance(stats.reload_hint, ReloadHint) else None
    return PostRenderMetrics(
        scenario=scenario,
        timestamp=datetime.now(UTC).isoformat(),
        wall_time_ms=round(wall_time_ms, 1),
        build_time_ms=round(stats.build_time_ms, 1),
        total_pages=stats.total_pages,
        pages_rendered=stats.pages_rendered,
        changed_output_count=len(stats.changed_outputs),
        reload_hint=reload_hint,
        rendering_time_ms=round(stats.rendering_time_ms, 1),
        assets_time_ms=round(stats.assets_time_ms, 1),
        postprocess_time_ms=round(stats.postprocess_time_ms, 1),
        health_check_time_ms=round(stats.health_check_time_ms, 1),
        postprocess_task_timings_ms=dict(stats.postprocess_task_timings_ms),
        postprocess_output_timings_ms=dict(stats.postprocess_output_timings_ms),
        post_render_timings_ms=dict(stats.post_render_timings_ms),
        store_sizes=collect_store_sizes(site),
    )


def run_post_render_scenarios(site_root: Path) -> list[PostRenderMetrics]:
    """Run the canonical post-render scenarios for a site root."""
    site = Site.from_config(site_root)
    content_dir = site_root / "content"
    page = sorted(content_dir.glob("section-*/page-*.md"))[0]
    section_index = sorted(content_dir.glob("section-*/_index.md"))[0]
    css = site_root / "assets" / "css" / "site.css"

    metrics: list[PostRenderMetrics] = []
    metrics.append(
        run_build(site, "cold", BuildOptions(incremental=False, profile=BuildProfile.WRITER))
    )

    site.prepare_for_rebuild()
    metrics.append(
        run_build(
            site,
            "warm_noop",
            BuildOptions(incremental=True, profile=BuildProfile.WRITER, changed_sources=set()),
        )
    )

    _touch(page, "\n\n<!-- single-page-edit -->\n")
    site.prepare_for_rebuild()
    metrics.append(
        run_build(
            site,
            "single_page_edit",
            BuildOptions(
                incremental=True,
                profile=BuildProfile.WRITER,
                changed_sources={page},
            ),
        )
    )

    _touch(section_index, "\n\n<!-- section-index-edit -->\n")
    site.prepare_for_rebuild()
    metrics.append(
        run_build(
            site,
            "section_index_edit",
            BuildOptions(
                incremental=True,
                profile=BuildProfile.WRITER,
                changed_sources={section_index},
            ),
        )
    )

    _touch(css, "\n/* css edit */\n")
    site.prepare_for_rebuild()
    metrics.append(
        run_build(
            site,
            "css_only_edit",
            BuildOptions(
                incremental=True,
                profile=BuildProfile.WRITER,
                changed_sources={css},
            ),
        )
    )

    return metrics


def write_metrics(path: Path, metrics: list[PostRenderMetrics]) -> None:
    """Persist metrics in the same JSON shape used by benchmark scripts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([metric.to_dict() for metric in metrics], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _touch(path: Path, suffix: str) -> None:
    path.write_text(path.read_text(encoding="utf-8") + suffix, encoding="utf-8")
