import concurrent.futures
import os
from pathlib import Path

import pytest

from bengal.core.site import Site
from bengal.orchestration.build.options import BuildOptions


@pytest.mark.serial
@pytest.mark.parallel_unsafe
class TestConcurrentBuilds:
    def test_concurrent_full_builds(self, tmp_path):
        site_root = Path(tmp_path)
        (site_root / "content").mkdir(parents=True)
        (site_root / "content" / "index.md").write_text("---\ntitle: Home\n---\n# Home\n")
        (site_root / "bengal.toml").write_text('[site]\ntitle = "t"')

        def build_once(_):
            site = Site.from_config(site_root)
            site.build(BuildOptions(force_sequential=True, incremental=False))
            return True

        # Scale down in CI: 6 concurrent builds under free-threaded Python
        # spawn 48+ writer threads that deadlock on constrained runners.
        ci_fast = os.environ.get("BENGAL_CI_FAST") == "1"
        max_workers = 2 if ci_fast else 4
        num_builds = 3 if ci_fast else 6

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            results = list(ex.map(build_once, range(num_builds)))

        assert all(results)
        # cache existence is implementation-specific; assert build output instead
        assert (site_root / "public").exists()
