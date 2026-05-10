"""Manual/scheduled benchmark for the post-render pipeline tail."""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from tests.performance.post_render_harness import (
    create_post_render_site,
    run_post_render_scenarios,
)


def run_scale(page_count: int) -> list[dict[str, object]]:
    root = Path(tempfile.mkdtemp(prefix="bengal_post_render_"))
    try:
        site_root = create_post_render_site(root, page_count=page_count)
        metrics = run_post_render_scenarios(site_root)
        return [metric.to_dict() | {"page_count": page_count} for metric in metrics]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Bengal post-render tail work")
    parser.add_argument(
        "--scales",
        default="100,1000,5000",
        help="Comma-separated page counts to benchmark",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tests/performance/benchmark_results/post_render_pipeline/latest.json"),
        help="Path for JSON metrics output",
    )
    args = parser.parse_args()

    all_rows: list[dict[str, object]] = []
    for raw_scale in args.scales.split(","):
        scale = int(raw_scale.strip())
        all_rows.extend(run_scale(scale))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Reuse the same writer contract through lightweight metric shims.
    import json

    args.output.write_text(
        json.dumps(all_rows, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
