"""
Tests for BuildCache robustness when the on-disk cache is malformed or unexpected.
"""

import json
from pathlib import Path

from bengal.cache.build_cache import BuildCache


class TestCacheCorruption:
    def test_load_truncated_json(self, tmp_path):
        cache_file = Path(tmp_path) / ".bengal-cache.json"
        cache_file.write_text('{"version": 1, "file_fingerprints": {"content/page.md"')

        cache = BuildCache.load(cache_file)

        assert isinstance(cache, BuildCache)
        assert cache.version == BuildCache.VERSION
        assert len(cache.file_fingerprints) == 0

    def test_load_invalid_json_characters(self, tmp_path):
        cache_file = Path(tmp_path) / ".bengal-cache.json"
        cache_file.write_bytes(b'{"version": 1, \x00\x01\x02 "invalid": true}')

        cache = BuildCache.load(cache_file)

        assert isinstance(cache, BuildCache)
        assert len(cache.file_fingerprints) == 0

    def test_load_empty_file(self, tmp_path):
        cache_file = Path(tmp_path) / ".bengal-cache.json"
        cache_file.write_text("")

        cache = BuildCache.load(cache_file)

        assert isinstance(cache, BuildCache)
        assert cache.version == BuildCache.VERSION
        assert len(cache.file_fingerprints) == 0

    def test_load_future_version_best_effort(self, tmp_path):
        cache_file = Path(tmp_path) / ".bengal-cache.json"
        future_cache = {
            "version": 99,
            "file_fingerprints": {"content/page.md": {"hash": "abc123", "mtime": 0, "size": 0}},
            # do not include unknown keys to avoid strict dataclass init failure
        }
        cache_file.write_text(json.dumps(future_cache))

        cache = BuildCache.load(cache_file)

        assert isinstance(cache, BuildCache)
        # Known fields preserved
        assert cache.file_fingerprints.get("content/page.md", {}).get("hash") == "abc123"

    def test_load_missing_required_fields(self, tmp_path):
        cache_file = Path(tmp_path) / ".bengal-cache.json"
        cache_file.write_text('{"version": 1}')

        cache = BuildCache.load(cache_file)

        assert isinstance(cache, BuildCache)
        assert len(cache.file_fingerprints) == 0
