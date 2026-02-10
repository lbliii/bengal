"""
Integration contracts for incremental coherence on real warm builds.
"""

from __future__ import annotations

from tests.integration.warm_build.conftest import WarmBuildTestSite, warm_build_site

# Re-export fixture for pytest discovery in this module.
_ = warm_build_site


class TestIncrementalCoherenceContracts:
    """Cross-layer coherence checks using full -> incremental build sequences."""

    def test_targeted_rebuild_for_single_content_change(
        self, warm_build_site: WarmBuildTestSite
    ) -> None:
        """
        A single markdown edit should trigger a targeted incremental rebuild.
        """
        warm_build_site.create_file(
            "content/page-a.md",
            """---
title: Page A
---

Original A content.
""",
        )
        warm_build_site.create_file(
            "content/page-b.md",
            """---
title: Page B
---

Original B content.
""",
        )

        full_stats = warm_build_site.full_build()
        assert full_stats.pages_built >= 3  # home + 2 content pages

        warm_build_site.modify_file(
            "content/page-a.md",
            """---
title: Page A
---

UPDATED A content.
""",
        )
        warm_build_site.wait_for_fs()

        incremental_stats = warm_build_site.incremental_build()

        # Targeted contract: at least one page rebuilt, but not a full rebuild.
        assert incremental_stats.cache_misses >= 1
        assert incremental_stats.cache_misses < full_stats.pages_built

        warm_build_site.assert_output_contains("page-a/index.html", "UPDATED A content")
        warm_build_site.assert_output_contains("page-b/index.html", "Original B content")

    def test_no_change_incremental_reuses_cache_after_targeted_rebuild(
        self, warm_build_site: WarmBuildTestSite
    ) -> None:
        """
        After a targeted incremental rebuild, the next no-change build should skip or hit cache.
        """
        warm_build_site.create_file(
            "content/page-a.md",
            """---
title: Page A
---

Initial content.
""",
        )

        warm_build_site.full_build()
        warm_build_site.modify_file(
            "content/page-a.md",
            """---
title: Page A
---

Updated content.
""",
        )
        warm_build_site.wait_for_fs()
        warm_build_site.incremental_build()

        no_change_stats = warm_build_site.incremental_build()
        assert no_change_stats.skipped or no_change_stats.cache_misses == 0

    def test_missing_output_is_regenerated_by_incremental(
        self, warm_build_site: WarmBuildTestSite
    ) -> None:
        """
        If output is missing while source is unchanged, incremental should regenerate it.
        """
        warm_build_site.create_file(
            "content/page-a.md",
            """---
title: Page A
---

Stable content.
""",
        )

        warm_build_site.full_build()
        output_rel = "page-a/index.html"
        output_path = warm_build_site.output_dir / output_rel
        assert output_path.exists()
        output_path.unlink()
        assert not output_path.exists()

        incremental_stats = warm_build_site.incremental_build()

        warm_build_site.assert_output_exists(output_rel)
        assert not incremental_stats.skipped
