---
title: Build Hooks
description: Run external tools before and after Bengal builds
weight: 10
---

Build hooks let you run shell commands before and after Bengal builds. Use them to integrate CSS preprocessors, JavaScript bundlers, icon generators, or custom validation scripts.

## Configuration

Add hooks to your `bengal.toml` under the `[dev_server]` section:

```toml
[dev_server]
pre_build = [
    "npm run build:icons",
    "npx tailwindcss -i src/input.css -o assets/style.css"
]
post_build = [
    "echo 'Build complete!'",
    "node scripts/validate-output.js"
]
```

## How Hooks Work

Hooks execute sequentially in the order defined:

1. **Pre-build hooks** run before the build starts
2. Bengal processes and renders your site
3. **Post-build hooks** run after all pages are written

If a **pre-build hook fails** (non-zero exit code), the build stops immediately and reports the error. If a **post-build hook fails**, a warning is logged but the build is considered complete.

## Common Use Cases

### CSS Preprocessing with Tailwind

```toml
[dev_server]
pre_build = [
    "npx tailwindcss -i src/input.css -o assets/css/tailwind.css --minify"
]
```

### JavaScript Bundling with esbuild

```toml
[dev_server]
pre_build = [
    "npx esbuild src/main.ts --bundle --outfile=assets/js/bundle.js --minify"
]
```

### Icon Sprite Generation

```toml
[dev_server]
pre_build = [
    "npx svg-sprite --symbol --dest assets/icons src/icons/*.svg"
]
```

### Post-Build Validation

```toml
[dev_server]
post_build = [
    "python scripts/check-links.py public/",
    "npx html-validate public/**/*.html"
]
```

### Multi-Step Asset Pipeline

```toml
[dev_server]
pre_build = [
    "npm run build:icons",
    "npm run build:css",
    "npm run build:js"
]
```

## Environment and Working Directory

Hooks run in your project's root directory with access to your shell environment. This means:

- `npm`, `npx`, and other tools in your PATH work as expected
- Environment variables from your shell are available
- Relative paths resolve from the project root

## Error Handling

When a **pre-build hook** fails:

1. The command's stderr is logged (truncated to 500 characters)
2. The build stops immediately
3. An error message shows which hook failed

Example error output:

```text
Pre-build hook failed - skipping build
```

When a **post-build hook** fails:

1. The command's stderr is logged
2. A warning is logged, but the build is considered successful
3. Your site output is still available

Successful hook output (stdout) is logged at debug level. Run `bengal serve --debug` to see full command output during development.

## Limitations

- Hooks run synchronously (one at a time)
- Each command has a 60-second timeout
- No shell features like pipes (`|`) or redirects (`>`) — commands are parsed as argument lists, not passed to a shell interpreter
- Hooks run for every build, including incremental rebuilds in dev server mode

## Tips

### Use npm Scripts for Complex Commands

Instead of long inline commands:

```toml
# ❌ Hard to read
pre_build = [
    "npx tailwindcss -i src/input.css -o assets/style.css --config tailwind.config.js --minify"
]
```

Define an npm script:

```json
// package.json
{
  "scripts": {
    "build:css": "tailwindcss -i src/input.css -o assets/style.css --config tailwind.config.js --minify"
  }
}
```

Then use it in your hooks:

```toml
# ✅ Clean and maintainable
pre_build = ["npm run build:css"]
```

### Skip Hooks in CI

If your CI pipeline handles asset building separately, you can use environment variables:

```toml
# Only run hooks if BENGAL_HOOKS is set
pre_build = []  # Override in local config
```

Or use a local config override file that's not committed to version control.

## Related

- [Configuration](/docs/building/configuration/) for all `bengal.toml` options
- [Build Pipeline](/docs/reference/architecture/core/pipeline/) for understanding when hooks run
