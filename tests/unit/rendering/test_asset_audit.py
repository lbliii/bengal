from __future__ import annotations

from bengal.rendering.asset_audit import find_missing_local_asset_references


def test_finds_missing_local_css_reference(tmp_path) -> None:
    output = tmp_path / "public"
    (output / "docs").mkdir(parents=True)
    (output / "docs" / "index.html").write_text(
        '<link rel="stylesheet" href="/assets/missing.css">',
        encoding="utf-8",
    )

    missing = find_missing_local_asset_references(output)

    assert len(missing) == 1
    assert missing[0].url == "/assets/missing.css"
    assert missing[0].expected_path == output / "assets" / "missing.css"


def test_accepts_existing_baseurl_and_relative_asset_references(tmp_path) -> None:
    output = tmp_path / "public"
    (output / "assets").mkdir(parents=True)
    (output / "docs").mkdir(parents=True)
    (output / "assets" / "app.css").write_text(".app{}", encoding="utf-8")
    (output / "docs" / "local.js").write_text("window.local=true", encoding="utf-8")
    (output / "docs" / "index.html").write_text(
        "\n".join(
            [
                '<link rel="stylesheet" href="/preview/assets/app.css">',
                '<script src="local.js"></script>',
                '<script src="https://cdn.example.com/app.js"></script>',
            ]
        ),
        encoding="utf-8",
    )

    missing = find_missing_local_asset_references(output, baseurl="/preview")

    assert missing == []
