---
title: "Optional Asset Pipeline"
description: "Enable SCSS, PostCSS, and JS/TS bundling with Node v22 LTS"
weight: 65
toc: true
---

# Optional Asset Pipeline

By default, Bengal uses a lightweight Python-only asset flow. If you want modern CSS/JS tools, enable the optional Node-based pipeline.

## Prerequisites

- Node.js v22 LTS
- Add devDependencies:

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

Create `postcss.config.cjs` if using PostCSS:

```js
module.exports = {
  plugins: [require('autoprefixer')]
};
```

## Configuration

```toml
[assets]
pipeline = true
scss = true
postcss = true
postcss_config = "postcss.config.cjs"
bundle_js = true
esbuild_target = "es2018"
sourcemaps = true
```

You can also toggle at build time:

```bash
bengal build --assets-pipeline
bengal build --no-assets-pipeline
```

## Project Layout

```text
assets/
  scss/
    main.scss      # -> public/assets/scss/main.<hash>.css
  js/
    main.ts       # -> public/assets/js/main.<hash>.js
```

In templates:

```html
<link rel="stylesheet" href="{{ asset_url('scss/main.css') }}">
<script src="{{ asset_url('js/main.js') }}" defer></script>
```

`asset_url` resolves the fingerprinted filenames automatically.
