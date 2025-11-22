# pipeline

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/assets/pipeline.py

Optional Node-based asset pipeline integration for Bengal SSG.

Provides SCSS → CSS, PostCSS transforms, and JS/TS bundling via esbuild.

Behavior:
- Only runs when enabled via config (`[assets].pipeline = true`).
- Detects required CLIs on PATH and produces clear, actionable errors.
- Compiles into a temporary pipeline output directory for subsequent
  Bengal fingerprinting and copying.

This module does not change the public API of asset processing; it returns
compiled output files to be treated as regular assets by AssetOrchestrator.

*Note: Template has undefined variables. This is fallback content.*
