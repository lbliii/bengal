from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.bengal(testroot="test-assets")
def test_build_twice_keeps_single_fingerprint(site, build_site):
    """Only the latest fingerprinted CSS should remain and be manifest-tracked after consecutive builds."""
    site_css_dir = site.root_path / "assets" / "css"
    site_css_dir.mkdir(parents=True, exist_ok=True)
    source_css = site_css_dir / "style.css"
    source_css.write_text(
        ":root { --color-primary: var(--blue-500); }\n",
        encoding="utf-8",
    )

    build_site()
    output_dir = Path(site.output_dir)
    css_dir = output_dir / "assets" / "css"
    manifest_path = output_dir / "asset-manifest.json"
    assert manifest_path.exists()

    manifest_snapshot = manifest_path.read_text(encoding="utf-8")
    assert "css/style.css" in manifest_snapshot

    first_hashes = sorted(css_dir.glob("style.*.css"))
    assert len(first_hashes) == 1

    # Modify source to force a different hash on rebuild
    source_css.write_text(
        ":root { --color-primary: var(--blue-500); --color-secondary: var(--green-500); }\n",
        encoding="utf-8",
    )

    build_site()
    second_hashes = sorted(css_dir.glob("style.*.css"))
    assert len(second_hashes) == 1
    assert second_hashes[0] != first_hashes[0]

    manifest_data_after = manifest_path.read_text(encoding="utf-8")
    assert second_hashes[0].name in manifest_data_after
