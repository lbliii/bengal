from pathlib import Path

import pytest

from bengal.content.discovery.content_discovery import ContentDiscovery


class TestFrontmatterBOM:
    def test_utf8_bom_frontmatter(self, tmp_path):
        content_dir = Path(tmp_path) / "content"
        content_dir.mkdir()
        file = content_dir / "bom.md"
        file.write_bytes(b"\xef\xbb\xbf---\ntitle: Test\n---\nContent")

        discovery = ContentDiscovery(content_dir)
        _sections, pages = discovery.discover()

        assert len(pages) == 1
        assert pages[0].metadata.get("title") == "Test"


class TestConfigFuzzing:
    # Determine hypothesis availability at import time
    try:
        import hypothesis

        _HYPOTHESIS_AVAILABLE = True
    except Exception:  # pragma: no cover - environment dependent
        _HYPOTHESIS_AVAILABLE = False

    @pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
    def test_config_validator_fuzz(self):
        from hypothesis import HealthCheck, given, settings
        from hypothesis import strategies as st

        from bengal.config.validators import ConfigValidator

        @given(
            st.dictionaries(
                keys=st.text(min_size=1, max_size=20),
                values=st.one_of(st.booleans(), st.integers(), st.text(), st.none()),
                max_size=20,
            )
        )
        @settings(suppress_health_check=[HealthCheck.too_slow])
        def run_fuzz(config):
            validator = ConfigValidator()
            try:
                validator.validate(config)
            except Exception as e:  # Validation errors are expected; but no crashes
                # Allow ConfigValidationError; fail on unexpected exceptions
                if e.__class__.__name__ != "ConfigValidationError":
                    pytest.fail(f"Unexpected error: {e}")

        run_fuzz()
