# Assets Steward

Assets protect the files readers actually download: copied static files,
fingerprinted theme assets, manifests, CSS/JS bundling, and references embedded
in rendered pages.

Related docs:
- root `../../AGENTS.md`
- `../../site/content/docs/reference/architecture/rendering/assets-pipeline.md`
- `../../site/content/docs/theming/assets/`
- `../../bengal/themes/default/assets/css/README.md`

## Point Of View

Assets represent browser correctness and deployment reliability. Every copied,
fingerprinted, bundled, or referenced file must exist where rendered HTML says
it exists.

## Protect

- Asset discovery, deduplication, manifest generation, and baseurl handling.
- Fingerprint stability and invalidation when asset content changes.
- CSS/JS bundling without adding npm or Node to the build path.
- Atomic output writes and generated artifact references.

## Contract Checklist

- Tests under `tests/unit/assets/`, theme asset tests, rendering asset URL
  tests, and integration asset manifest tests.
- Assets pipeline docs, theming assets docs, and default-theme asset READMEs.
- Cache/incremental collateral when asset changes affect rebuild decisions.
- Health/audit collateral for broken asset references.
- Changelog for user-visible asset output or URL behavior changes.

## Advocate

- Manifest entries that can explain source, output path, hash, and owner.
- Small fixtures for baseurl, installed theme assets, and duplicate asset names.
- CSS/JS optimizations that preserve reader behavior and accessibility.

## Serve Peers

- Give rendering and default theme stable asset URLs.
- Give postprocess, health, and audit complete output artifact data.
- Give docs truthful theming asset examples.

## Do Not

- Add an npm, Node, or external JS build step.
- Write assets outside atomic output helpers.
- Change fingerprint or manifest semantics without invalidation tests.
- Ignore missing asset references because the page still renders.

## Own

- `bengal/assets/`
- `site/content/docs/reference/architecture/rendering/assets-pipeline.md`
- `site/content/docs/theming/assets/`
- Tests: `tests/unit/assets/`, asset rendering/integration tests
- Checks: `uv run pytest tests/unit/assets tests/integration/test_assets_manifest.py tests/integration/test_installed_theme_asset_build.py -q`
- Checks: `uv run ruff check bengal/assets tests/unit/assets`
