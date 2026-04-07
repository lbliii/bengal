"""
Integration tests for error recovery and resilience scenarios.

Tests the system's ability to handle and recover from various error conditions:
- Invalid configuration
"""

import pytest

from bengal.core.site import Site
from bengal.utils.io.file_io import write_text_file


class TestInvalidConfigurationRecovery:
    """Tests for handling invalid configuration."""

    def test_invalid_toml_syntax(self, tmp_path):
        """Test handling of invalid TOML syntax."""
        config_file = tmp_path / "bengal.toml"
        write_text_file(
            str(config_file),
            """
[site
title = "Broken TOML"
""",
        )

        # Should raise appropriate error (message mentions toml or config)
        with pytest.raises(Exception, match=r"(?i)toml|config"):
            Site.from_config(tmp_path, config_path=config_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
