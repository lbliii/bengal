"""Task: render_pages_targeted -- lean render path for targeted outputs."""

from __future__ import annotations

from bengal.orchestration.pipeline.task import BuildTask
from bengal.orchestration.tasks.rendering import _execute, _skip


TASK = BuildTask(
    name="render_pages_targeted",
    requires=frozenset({
        "parsed_pages",
        "menu_tree",
        "taxonomy_pages",
        "asset_manifest",
        "font_css",
    }),
    produces=frozenset({"rendered_pages_fast"}),
    execute=_execute,
    skip_if=_skip,
)
