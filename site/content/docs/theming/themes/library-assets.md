---
title: Theme Library Assets
description: Package reusable Kida components with CSS and JavaScript for Bengal themes
weight: 25
category: guide
icon: package
card_color: green
---
# Theme Library Assets

Theme libraries let a Python package provide Kida templates, CSS, JavaScript,
and runtime metadata to any Bengal theme. A theme opts in with `libraries` in
`theme.toml`; the package exposes a small Python contract; Bengal handles
fingerprinting, dev URLs, static output, and missing asset diagnostics.

Use this for component libraries such as `chirp_ui`, not for one-off site
styles. Site and theme-owned files should still use `asset_url()`.

## Theme Setup

Declare the package in the theme manifest:

```toml
name = "vendor-theme"
libraries = ["vendor_ui"]
```

Then render provider-owned tags from the base template:

```html
{{ library_asset_tags() }}
<link rel="stylesheet" href="{{ asset_url('css/style.css') }}">
```

`library_asset_tags()` renders only assets declared by the package contract.
Your theme can still include its own bridge stylesheet or script with
`asset_url()`.

## Package Contract

In the library package, expose `get_library_contract()`:

```python
from pathlib import Path

from kida import PackageLoader


def static_path() -> Path:
    return Path(__file__).parent / "static"


def get_loader():
    return PackageLoader("vendor_ui", "templates")


def get_library_contract():
    return {
        "asset_root": static_path(),
        "assets": [
            {"path": "vendor.css", "mode": "bundle", "type": "css"},
            {
                "path": "transitions.css",
                "mode": "bundle",
                "type": "css",
                "output": "vendor.css",
            },
            {
                "path": "vendor.js",
                "mode": "link",
                "type": "javascript",
                "defer": True,
                "module": True,
            },
            {"path": "tokens.css", "mode": "none", "type": "css"},
        ],
        "runtime": ["vendor-ui"],
    }
```

The contract is intentionally plain Python. Paths are relative to `asset_root`
unless you return an absolute source path. Output paths must be relative and
cannot contain `..`; Bengal namespaces them under the package name, such as
`/assets/vendor_ui/vendor.css`.

## Asset Modes

| Mode | Build behavior | Tag behavior | Use when |
|------|----------------|--------------|----------|
| `link` | Emits the file through the normal asset pipeline. | Renders one tag for the emitted asset. | The file should stay separate. |
| `bundle` | Concatenates assets with the same `output`, then fingerprints the bundle. | Renders one tag for the bundle. | A package splits CSS/JS internally but themes should load one file. |
| `none` | Does not emit the file. | Renders no tag. | The asset is metadata-only or consumed by another package process. |

CSS and JavaScript emitted through `link` or `bundle` use the normal Bengal
asset manifest. In development, URLs stay stable. In static builds, URLs are
fingerprinted.

## Manifest Provenance

Provider-managed assets add optional provenance to `asset-manifest.json`:

```json
{
  "assets": {
    "vendor_ui/vendor.css": {
      "output_path": "assets/vendor_ui/vendor.350f9b04.css",
      "fingerprint": "350f9b04",
      "size_bytes": 12345,
      "provenance": {
        "kind": "theme_library",
        "package": "vendor_ui",
        "mode": "bundle",
        "sources": ["vendor.css", "transitions.css"]
      }
    }
  }
}
```

`sources` contains contract-relative paths only. Bengal does not write absolute
local filesystem paths into the manifest.

## Tag Attributes

Use `attributes` or the common shorthands to control the generated HTML tag:

```python
{
    "path": "vendor.js",
    "type": "javascript",
    "mode": "link",
    "defer": True,
    "attributes": {"crossorigin": "anonymous"},
}
```

Boolean attributes render without a value. String attributes are escaped.
Bengal owns `href` and `src`; declaring either as an attribute is rejected so
fingerprinted URLs cannot drift.

## Runtime Metadata

`runtime` is a string or list of strings:

```python
{"runtime": ["vendor-ui", "alpine"]}
```

Templates can read the deduplicated runtime list with:

```html
{% if "vendor-ui" in library_runtime() %}
  ...
{% end %}
```

Use this for conditional template behavior. Do not use it to bypass asset
declarations.

## Diagnostics

Bengal validates the contract while resolving the theme library:

- `assets` entries need a non-empty path.
- `mode` must be `bundle`, `link`, or `none`.
- Runtime entries must be strings.
- Output paths must be relative and stay inside the library namespace.
- Tag attributes must be strings or booleans and cannot set `href` or `src`.

During build, Bengal also checks rendered HTML for local CSS/JS references that
were not emitted. In normal builds this is a warning with the first missing URL.
In strict builds it is a `BengalAssetError`.

```bash
bengal build --strict
```

Run strict builds in CI for vendor themes. A browser console 404 should not be
the first signal that a theme library asset is missing.
