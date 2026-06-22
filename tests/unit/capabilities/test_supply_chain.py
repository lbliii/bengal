"""Tests for capability supply-chain controls (#573)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class TestComputeSri:
    def test_known_payload(self) -> None:
        from bengal.capabilities.supply_chain import compute_sri, verify_sri

        data = b"hello world"
        integrity = compute_sri(data)
        assert integrity.startswith("sha384-")
        assert verify_sri(data, integrity)


class TestResolveVendorAsset:
    def test_cdn_default_with_pin_substitution(self, tmp_path: Path) -> None:
        from bengal.capabilities.supply_chain import resolve_vendor_asset

        resolved = resolve_vendor_asset(
            {"capabilities": {"mermaid": True}},
            "mermaid",
            "mermaid.min.js",
            "https://cdn.jsdelivr.net/npm/mermaid@{pin}/dist/mermaid.min.js",
            site_root=tmp_path,
        )
        assert resolved.source_mode == "cdn"
        assert resolved.url is not None
        assert "@10/" in resolved.url

    def test_pin_override(self, tmp_path: Path) -> None:
        from bengal.capabilities.supply_chain import resolve_vendor_asset

        config = {
            "capabilities": {
                "mermaid": True,
                "sources": {"mermaid": {"pin": "9.4.3"}},
            }
        }
        resolved = resolve_vendor_asset(
            config,
            "mermaid",
            "mermaid.min.js",
            "https://cdn.jsdelivr.net/npm/mermaid@{pin}/dist/mermaid.min.js",
            site_root=tmp_path,
        )
        assert "@9.4.3/" in (resolved.url or "")

    def test_local_source_requires_path(self, tmp_path: Path) -> None:
        import pytest

        from bengal.capabilities.supply_chain import resolve_vendor_asset

        config = {
            "capabilities": {
                "mermaid": True,
                "sources": {"mermaid": {"source": "local"}},
            }
        }
        with pytest.raises(ValueError, match="path required"):
            resolve_vendor_asset(
                config,
                "mermaid",
                "mermaid.min.js",
                "https://cdn.jsdelivr.net/npm/mermaid@{pin}/dist/mermaid.min.js",
                site_root=tmp_path,
            )


class TestCapabilityVendorHelperLocalSource:
    def test_provisions_from_local_path(self, tmp_path: Path) -> None:
        from bengal.capabilities.supply_chain import compute_sri
        from bengal.capabilities.vendors import CapabilityVendorHelper, load_vendor_integrity

        site_root = tmp_path / "site"
        site_root.mkdir()
        local_js = site_root / "vendor" / "mermaid.min.js"
        local_js.parent.mkdir(parents=True)
        payload = b"local mermaid payload"
        local_js.write_bytes(payload)

        config = {
            "capabilities": {
                "mermaid": True,
                "sources": {
                    "mermaid": {
                        "source": "local",
                        "path": "vendor/mermaid.min.js",
                        "require_sri": False,
                    }
                },
            }
        }

        helper = CapabilityVendorHelper(config, site_root)
        result = helper.process()

        dest = site_root / "assets" / "vendor" / "mermaid.min.js"
        assert dest.is_file()
        assert dest.read_bytes() == payload
        assert "mermaid.min.js" in result.downloaded
        assert load_vendor_integrity(dest.parent)["mermaid.min.js"] == compute_sri(payload)

    def test_sri_mismatch_raises(self, tmp_path: Path) -> None:
        import pytest

        from bengal.capabilities.supply_chain import compute_sri, record_vendor_integrity

        data = b"payload"
        wrong = compute_sri(b"other")
        with pytest.raises(ValueError, match="SRI mismatch"):
            record_vendor_integrity({}, "x.js", data, expected_sri=wrong, require_sri=True)
