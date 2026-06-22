# Reference capability package

Minimal third-party capability that demonstrates the full flow:

1. Declare a `CapabilitySpec` with assets, detectors, fence render hook, and init contract
2. Register via `[project.entry-points."bengal.capabilities"]`
3. Enable in site config and author ` ```demo ` fences in content

## Install (editable)

```bash
cd examples/capability-demo
pip install -e .
```

## Sample site

See `sample-site/` for a minimal Bengal project using `demo_viz`.

## Inspect

```bash
bengal capability list
bengal capability info demo_viz
```
