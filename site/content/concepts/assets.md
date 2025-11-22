---
title: Assets
description: Asset pipeline, optimization, and Node.js integration
weight: 20
---

Bengal includes a powerful asset pipeline that handles discovery, optimization, and delivery of static assets like CSS, JavaScript, images, and fonts.

## Default Python Pipeline

By default, Bengal uses a pure Python pipeline that requires no external dependencies (like Node.js).

### Features

- **Discovery**: Automatically finds assets in `assets/` and theme directories.
- **Minification**: Minifies CSS and JS using `lightningcss` and `rjsmin`.
- **Image Optimization**: Compresses and converts images (WebP support) using Pillow.
- **Fingerprinting**: Adds SHA256 hashes to filenames for cache busting (`style.abc123.css`).
- **Incremental Builds**: Only reprocesses changed assets.

### Usage

Place assets in your `assets/` directory:

```text
assets/
├── css/
│   └── style.css
├── js/
│   └── main.js
└── images/
    └── photo.jpg
```

Reference them in templates using the `asset_url` helper:

```html
<link rel="stylesheet" href="{{ asset_url('css/style.css') }}">
<script src="{{ asset_url('js/main.js') }}"></script>
<img src="{{ asset_url('images/photo.jpg') }}" alt="Photo">
```

When `fingerprint = true` is enabled, `asset_url` automatically resolves to the hashed filename (e.g., `/assets/css/style.a1b2c3.css`).

## Optional Node.js Pipeline

For modern frontend tooling (SCSS, PostCSS, Tailwind, TypeScript bundling), you can opt-in to the Node-based pipeline.

### Prerequisites

-   Node.js v22 LTS
-   `npm` or `yarn` or `pnpm`

### Setup

1.  Install dependencies in your project root:

    ```json
    {
      "devDependencies": {
        "sass": "^1.77.0",
        "postcss": "^8.4.35",
        "postcss-cli": "^11.0.0",
        "autoprefixer": "^10.4.19",
        "esbuild": "^0.23.0"
      }
    }
    ```

2.  Enable the pipeline in `bengal.toml`:

    ```toml
    [assets]
    pipeline = true          # Enable Node-based pipeline
    scss = true              # Compile SCSS → CSS
    postcss = true           # Run PostCSS
    postcss_config = "postcss.config.cjs"
    bundle_js = true         # Bundle JS/TS with esbuild
    sourcemaps = true        # Emit source maps
    ```

### Conventions

- **SCSS**: Place files in `assets/scss/`. Output goes to `public/assets/scss/`.
- **JS/TS**: Place entry files in `assets/js/`. Bundled output goes to `public/assets/js/`.

## Configuration

Configure the asset pipeline in `bengal.toml`:

```toml
[assets]
minify = true
optimize = true
fingerprint = true

# Image optimization settings
[assets.images]
quality = 85
strip_metadata = true
formats = ["webp"]
```

