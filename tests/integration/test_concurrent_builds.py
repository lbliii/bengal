import concurrent.futures
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

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            results = list(ex.map(build_once, range(6)))

        assert all(results)
        # cache existence is implementation-specific; assert build output instead
        assert (site_root / "public").exists()
