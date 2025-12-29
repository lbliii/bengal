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
pre_build_hooks = [
    "npm run build:icons",
    "npx tailwindcss -i src/input.css -o assets/style.css"
]
post_build_hooks = [
    "echo 'Build complete!'",
    "node scripts/validate-output.js"
]
hook_timeout = 60  # seconds per command (default: 60)
```

## How Hooks Work

Hooks execute sequentially in the order defined:

1. **Pre-build hooks** run before content discovery and rendering
2. Bengal processes and renders your site
3. **Post-build hooks** run after all pages are written

If any hook fails (non-zero exit code), the build stops and reports the error.

## Common Use Cases

### CSS Preprocessing with Tailwind

```toml
[dev_server]
pre_build_hooks = [
    "npx tailwindcss -i src/input.css -o assets/css/tailwind.css --minify"
]
```

### JavaScript Bundling with esbuild

```toml
[dev_server]
pre_build_hooks = [
    "npx esbuild src/main.ts --bundle --outfile=assets/js/bundle.js --minify"
]
```

### Icon Sprite Generation

```toml
[dev_server]
pre_build_hooks = [
    "npx svg-sprite --symbol --dest assets/icons src/icons/*.svg"
]
```

### Post-Build Validation

```toml
[dev_server]
post_build_hooks = [
    "python scripts/check-links.py public/",
    "npx html-validate public/**/*.html"
]
```

### Multi-Step Asset Pipeline

```toml
[dev_server]
pre_build_hooks = [
    "npm run build:icons",
    "npm run build:css",
    "npm run build:js"
]
hook_timeout = 120  # Allow more time for complex builds
```

## Environment and Working Directory

Hooks run in your project's root directory with access to your shell environment. This means:

- `npm`, `npx`, and other tools in your PATH work as expected
- Environment variables from your shell are available
- Relative paths resolve from the project root

## Error Handling

When a hook fails:

1. The command's stdout and stderr are logged
2. The build stops immediately
3. An error message shows which hook failed and why

Example error output:

```
Pre-build hook failed: npx tailwindcss -i src/input.css -o assets/style.css
Exit code: 1
Error: Cannot find module 'tailwindcss'
```

## Limitations

- Hooks run synchronously (one at a time)
- No shell features like pipes (`|`) or redirects (`>`) — use a script file for complex commands
- Hooks run for every build, including incremental rebuilds in dev server mode

## Tips

### Use npm Scripts for Complex Commands

Instead of long inline commands:

```toml
# ❌ Hard to read
pre_build_hooks = [
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
pre_build_hooks = ["npm run build:css"]
```

### Skip Hooks in CI

If your CI pipeline handles asset building separately, you can use environment variables:

```toml
# Only run hooks if BENGAL_HOOKS is set
pre_build_hooks = []  # Override in local config
```

Or use a local config override file that's not committed to version control.

## Related

- [Configuration](/docs/building/configuration/) for all `bengal.toml` options
- [Build Pipeline](/docs/reference/architecture/core/pipeline/) for understanding when hooks run
