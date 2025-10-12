# Installable Themes (uv/pip) - Design & Rollout Plan

Date: 2025-10-12
Status: Proposal
Owner: Site/Rendering/CLI

---

## Goals

- Enable installing and using third-party themes via uv/pip without copying files into a repo.
- Support a clear branding/naming convention for discoverability and safety.
- Maintain seamless compatibility with existing project-local and bundled themes.
- Provide CLI ergonomics for discovery, install, info, and selective override (swizzle).

## Non-Goals

- Building a centralized theme registry beyond PyPI (out of scope).
- Implementing complex three-way merge in swizzle updates (future work).

## User Stories

1. As a site author, I can `uv pip install bengal-theme-acme` and set `theme = "acme"` in config, and it works.
2. As a site author, I can list all available themes (project-local, installed, bundled) and see their source and version.
3. As a site author, I get a gentle warning if I reference a non-branded theme name and a suggestion for the canonical name.
4. As a site author, I can discover partials and swizzle them even when the theme is installed via pip.

## Naming & Branding Policy

- Canonical package name prefix: `bengal-theme-<slug>` (preferred).
- Accepted but discouraged: `<slug>-bengal-theme` (warn with remediation).
- CLI install will warn on non-conforming names and suggest the canonical one; `--force` bypasses.
- Official listings/galleries show only canonical names by default.

## Theme Package Layout (for PyPI)

```
project root
├── pyproject.toml
└── bengal_themes/
    └── <slug>/
        ├── __init__.py
        ├── templates/               # Jinja2 templates
        ├── assets/                  # CSS/JS/images
        └── theme.toml               # optional: { name, extends }
```

pyproject.toml (entry points):

```toml
[project]
name = "bengal-theme-acme"

[project.entry-points."bengal.themes"]
acme = "bengal_themes.acme"
```

## Discovery & Resolution

Resolution order (unchanged conceptually; new source added):
1. Project overrides: `templates/`
2. Project themes chain: `themes/<theme>/templates`
3. Installed themes (entry points): `bengal.themes` → `bengal_themes/<slug>/templates`
4. Bundled themes inside Bengal package
5. Fallback to `default`

Implementation details:
- Use `importlib.metadata.entry_points(group="bengal.themes")` to gather installed themes.
- Map site `[site].theme` slug to the matching entry point name.
- For each theme in the inheritance chain, add template dirs via `importlib.resources.files(pkg) / "templates"` and asset dirs via `... / "assets"` when they exist.
- Continue honoring `theme.toml` `extends` in installed themes (read via resources).
- Cache resolved directories per process; invalidate on dev server reload.

## CLI UX

- `bengal theme list`
  - Output: theme slug, source (project | installed | bundled), version (if installed), and path.

- `bengal theme install <name-or-slug> [--force]`
  - If `<slug>` without prefix, warn and suggest `bengal-theme-<slug>`; proceed or require `--force` for non-canonical names.
  - Execute `uv pip install <resolved-package>` (non-interactive) and re-list themes.

- `bengal theme info <slug>`
  - Show source, package metadata (if installed), resolved dirs, `extends`, available templates summary.

- `bengal theme discover [--partials|--templates]`
  - List swizzlable templates in the active theme chain with relative include paths.

- `bengal theme pull <slug> [--all|--templates|--assets]` (optional)
  - Copy all files into `themes/<slug>/` for advanced customization; clearly documented as optional.

## Config Changes

- No breaking changes. Continue to use:

```toml
[site]
theme = "acme"
```

- Optional (future): `theme_paths = ["/extra/themes/"]` for custom on-disk repositories.

## Rendering Integration

- Extend `TemplateEngine._resolve_theme_chain` to support `extends` from installed themes (`theme.toml` via package resources).
- Extend `TemplateEngine._create_environment` to include resource-backed template dirs from installed themes.
- Ensure `Site._get_theme_assets_chain` also resolves assets from installed themes.

## Swizzle Integration

- `SwizzleManager._find_theme_template` updated to search installed theme resource paths.
- Provenance records include `theme_source = installed|project|bundled` and `package_name`/`version` for installed.

## Dev Server & Component Preview

- Component discovery reads manifests from installed themes (`themes/<theme>/dev/components/*.yaml` under package resources) in addition to project/bundled.
- Keep live reload for project/local; installed packages typically static unless reinstalled.

## Warnings & Strict Mode

- Warn once per process if `[site].theme` references a non-canonical package name when resolved via installed theme.
- CLI `theme install` enforces naming unless `--force`.
- Add `--strict` flag (or use `--theme-dev`) to convert warnings into errors in CI.

## Security Considerations

- Do not execute theme code; only read package resources.
- Avoid arbitrary code import beyond discovering entry points and reading files.
- Validate `extends` to prevent infinite loops and depth > 5.

## Performance

- Cache entry point discovery (process-level singleton with TTL in dev server).
- Avoid repeated `importlib.resources` calls by memoizing resolved Paths.

## Testing Strategy

- Unit tests:
  - Entry point discovery, naming validation, extends chain, resolution ordering.
  - Swizzle source selection priority and provenance metadata.
  - CLI commands (`list`, `info`, name warnings) using Click runner.

- Integration tests:
  - Build a minimal wheel for a fixture theme (`bengal-theme-fixture`), install into venv, assert rendering and asset resolution.
  - Swizzle a template from installed theme and ensure overrides work.

- E2E (optional):
  - Run `examples/showcase` with an installed theme variant and confirm page output.

## Documentation Updates

- README/GETTING_STARTED: add uv/pip theme installation instructions and naming convention.
- Default theme README: link to discover/list commands.
- New guide: "Creating a Bengal Theme" with entry points and package layout.

## Rollout Plan

1. Phase 1: Discovery-only (no install) — list/info/discover and engine resolution for installed themes.
2. Phase 2: CLI install with naming warnings.
3. Phase 3: Optional pull command and strict-mode policies.

## Acceptance Criteria

- Given `uv pip install bengal-theme-acme` and `theme = "acme"`, templates and assets load from the package.
- `bengal theme list` shows `acme` as installed with version and paths.
- `bengal theme discover` lists partials including those from installed themes.
- Non-canonical names warn in `theme install` and at runtime; `--force` bypasses.
- All tests pass; docs updated.

## Work Breakdown (High-level)

- Rendering/Engine (discovery, resolves, extends): 1–2 days
- CLI (`list`, `info`, `install`, `discover`): 1–2 days
- Swizzle updates (resource search, provenance): 0.5–1 day
- Tests (unit/integration), example theme package: 1–2 days
- Docs and examples: 0.5–1 day
