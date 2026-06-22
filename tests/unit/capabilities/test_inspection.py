"""Tests for capability CLI inspection (#588)."""

from __future__ import annotations

from bengal.capabilities.inspection import inspect_capabilities, validate_capability_config
from bengal.capabilities.registry import reset_capability_registry


class TestInspectCapabilities:
    def test_lists_builtin_capabilities(self) -> None:
        reset_capability_registry()
        reports = inspect_capabilities()
        names = {report.name for report in reports}
        assert names == {"iconify", "katex", "mermaid"}

    def test_warns_on_unknown_config_capability(self, tmp_path) -> None:
        reset_capability_registry()
        config = {"capabilities": {"not_real": True}}
        issues = validate_capability_config(config, site_root=tmp_path)
        assert any("Unknown capability 'not_real'" in issue["message"] for issue in issues)
