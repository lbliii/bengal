Title: RFC — Config Ergonomics Overhaul: Profiles, Env Overrides, Introspection, Feature Groups, Canonicalization, Plugins, Versioning
Status: Draft
Owners: Bengal Core
Created: 2025-10-25

## 1) Problem Statement

Bengal’s configuration is powerful but scattered across flat keys, nested tables, and CLI flags. Users moving from Sphinx/MkDocs want:
- Simple, obvious starting config
- Predictable overrides (local vs CI vs preview)
- Profile-based ergonomics (writer vs theme-dev vs developer)
- First-class introspection and migration tooling

Pain points today:
- Flags and config are mixed (e.g., debug/strict/profile/fast_mode)
- Some canonical sections coexist with flat aliases (confusing discovery)
- No built-in env/profile layering
- Limited “effective config” introspection

## 2) Goals and Non-Goals

Goals:
- Introduce first-class Profiles and Env overrides with deterministic merge order
- Provide feature groups for simple on/off while retaining advanced knobs
- Canonicalize names and nesting while supporting backward-compatible aliases
- Add introspection tools: show/doctor/diff
- Prepare for plugins and safe evolution via config_version

Non-Goals:
- Redesign of content model or themes
- Breaking existing user configs (must be backward compatible)

## 3) Current State (Evidence)

Known config sections recognized by loader:
```65:81:/Users/llane/Documents/github/python/bengal/bengal/config/loader.py
    # Known valid section names
    KNOWN_SECTIONS = {
        "site",
        "build",
        "markdown",
        "features",
        "taxonomies",
        "menu",
        "params",
        "assets",
        "pagination",
        "dev",
        "output_formats",
        "health_check",
        "fonts",
        "theme",
    }
```

Profile logic exists in code, but not first-class in config files:
```27:40:/Users/llane/Documents/github/python/bengal/bengal/utils/profile.py
class BuildProfile(Enum):
    """
    Build profiles for different user personas.
    """

    WRITER = "writer"
    THEME_DEV = "theme-dev"
    DEVELOPER = "dev"
```
```137:151:/Users/llane/Documents/github/python/bengal/bengal/utils/profile.py
    def get_config(self) -> dict[str, Any]:
        """
        Get configuration dictionary for this profile.
        """
        if self == BuildProfile.WRITER:
            return {
                "show_phase_timing": False,
                "track_memory": False,
                "enable_debug_output": False,
                "collect_metrics": False,
                "health_checks": {
                    # Only run critical checks
                    "enabled": ["config", "output", "links"],
```

HTML bootstrap toggle is flat and lightly surfaced:
```117:126:/Users/llane/Documents/github/python/bengal/bengal/themes/default/templates/base.html
    {# Optional JSON bootstrap for client-side scripts #}
    {% if config.get('expose_metadata_json') %}
    <script id="bengal-bootstrap" type="application/json">{{ bengal | jsonify }}</script>
    <script>
        (function () {
            var el = document.getElementById('bengal-bootstrap');
            if (el) { window.__BENGAL__ = JSON.parse(el.textContent || '{}'); }
        })();
    </script>
    {% endif %}
```

Output formats already normalize “simple vs advanced” config:
```90:123:/Users/llane/Documents/github/python/bengal/bengal/postprocess/output_formats.py
        if is_advanced:
            # Advanced format - merge with defaults
            normalized.update(config)
        else:
            # Simple format - convert to advanced format
            per_page = []
            site_wide = []
            # Map simple format keys to advanced format
            if config.get("json", False):
                per_page.append("json")
            if config.get("llm_txt", False):
                per_page.append("llm_txt")
            if config.get("site_json", False):
                site_wide.append("index_json")
            if config.get("site_llm", False):
                site_wide.append("llm_full")
```

I18n options used widely by URL strategy:
```54:60:/Users/llane/Documents/github/python/bengal/bengal/utils/url_strategy.py
pretty_urls = site.config.get("pretty_urls", True)
i18n = site.config.get("i18n", {}) or {}
strategy = i18n.get("strategy", "none")
default_lang = i18n.get("default_language", "en")
default_in_subdir = bool(i18n.get("default_in_subdir", False))
```

Connectivity thresholds read from config:
```151:154:/Users/llane/Documents/github/python/bengal/bengal/health/validators/connectivity.py
orphan_threshold = site.config.get("health_check", {}).get("orphan_threshold", 5)
```
```188:191:/Users/llane/Documents/github/python/bengal/bengal/health/validators/connectivity.py
super_hub_threshold = site.config.get("health_check", {}).get(
    "super_hub_threshold", 50
)
```

Assets pipeline options under `[assets]`:
```256:271:/Users/llane/Documents/github/python/bengal/bengal/assets/pipeline.py
def from_site(site: Site) -> NodePipeline:
    assets_cfg = (
        site.config.get("assets", {}) if isinstance(site.config.get("assets"), dict) else {}
    )
    pc = PipelineConfig(
        root_path=site.root_path,
        theme_name=site.theme,
        enabled=bool(assets_cfg.get("pipeline", False)),
        scss=bool(assets_cfg.get("scss", True)),
        postcss=bool(assets_cfg.get("postcss", True)),
        postcss_config=assets_cfg.get("postcss_config"),
        bundle_js=bool(assets_cfg.get("bundle_js", True)),
        esbuild_target=str(assets_cfg.get("esbuild_target", "es2018")),
        sourcemaps=bool(assets_cfg.get("sourcemaps", True)),
    )
```

## 4) Proposal

4.1 Profiles as first-class config
- Root key `profile = "writer|theme-dev|dev"` selects active profile
- New section `[profiles.<name>]` with nested overrides merged when selected
- CLI `--profile` simply chooses the block. No special-case behavior in code.

4.2 Environment-aware overrides
- New section `[env.<name>]` with common names: `local`, `preview`, `production`
- Precedence detection: `--env`, `BENGAL_ENV`, Netlify/Vercel/GitHub inferred
- Deterministic merge order (see Design)

4.3 Introspection commands
- `bengal config show [--profile dev] [--env production] [--origin]`
  - Prints effective merged config; `--origin` shows per-key origin chain
- `bengal config doctor`
  - Lints config, flags deprecated keys, suggests canonical names, shows typos
- `bengal config diff --against defaults|path/to/other.toml`
  - Highlights what your config actually changes

4.4 Feature groups
- Introduce `[features]` booleans for the most common toggles:
  - `rss`, `sitemap`, `search`, `json`, `llm_txt`, `minify_html`, `validate_links`
- Loader maps `[features]` to detailed sections (`[output_formats]`, `[postprocess]`, `[health.linkcheck]`) via normalization

4.5 Canonical naming and nesting
- Canonicalize booleans under `[build]` where appropriate
- Keep flat keys as read-only aliases; emit warnings via `config doctor`
- Prefer one verb convention going forward (e.g., `generate_*`), preserve `enable_*` as aliases

4.6 Plugin-ready structure
- `[plugins]` namespace with `[[plugins]] name = "xyz"` and `plugins.xyz.*` sections
- Validator enforces shape; unknown plugin names get friendly guidance

4.7 Safe evolution with versioning
- `config_version = 1` at top-level
- When increasing to 2+, the validator includes deprecation maps and automatic suggestions
- `bengal config migrate` writes a proposed updated config with comments

4.8 Presets
- `site.kind = "docs|blog|marketing"` to set bundles of defaults (pagination, search preload, output formats)
- `autodoc.presets = "api-minimal|api-full"` to tune inherited/alias behavior quickly

## 5) Detailed Design

5.1 Merge precedence and origin tracking
Order (lowest → highest):
1. Bengal defaults (code)
2. User config file
3. Env block: `[env.<active>]`
4. Profile block: `[profiles.<selected>]`
5. CLI flags

Each key carries `{value, origin}`; `origin` is a small struct: `{"source": "default|file|env|profile|cli", "path": "..."}` used by `config show --origin`.

5.2 Loader/Validator updates
- Extend `ConfigLoader` to merge env/profile blocks in the defined precedence
- `ConfigValidator` gains:
  - Canonical name mapping table (aliases → canonical)
  - Deprecation registry keyed by `config_version`
  - Optional “autofix” mode for `doctor`/`migrate`

5.3 CLI
- `bengal site build --profile dev --env production` (selection only)
- New `bengal config` subcommands as above

5.4 Compatibility
- All existing keys remain accepted via aliases; warnings explain canonical form
- `[build.output_formats]` (simple) continues to normalize into `[output_formats]` (advanced)

## 6) Alternatives Considered

1) Keep flags as the primary override surface
- Cons: drifts from single-source-of-truth, harder to diff/inspect

2) Only env-based layering (no profiles)
- Cons: profiles encode intent and are discoverable in config and docs

3) Hard switch to canonical names (no aliases)
- Cons: breaks existing users; unnecessary friction

## 7) Migration Plan

Phase 1 (Additive, default off):
- Implement merge engine, origin tracking, and `config show`
- Add warnings (off by default) for deprecated/aliased keys
- Land `profile` and `[profiles.*]` blocks without changing defaults

Phase 2 (Developer preview):
- Add `doctor` and `diff` commands
- Add `[env.*]` layering; example config and docs

Phase 3 (Default on, still compatible):
- Enable warnings by default; provide `BENGAL_NO_CONFIG_WARN=1` escape hatch
- Publish migration guide and `config migrate`

Phase 4 (Future major):
- Consider raising `config_version` and making canonical names primary in docs

## 8) Risks and Mitigations

- Risk: Confusion around precedence
  - Mitigation: `config show --origin`, clear docs, single diagram of merge order

- Risk: Plugin config collisions
  - Mitigation: reserved `plugins.<name>` namespace, validation of shapes

- Risk: Hidden behavior changes
  - Mitigation: soft-launch with explicit warnings and doctor reports

## 9) Testing & Validation Plan

- Unit tests for merge precedence (defaults/file/env/profile/CLI)
- Golden tests for `config show --origin` output
- Property tests for alias → canonical normalization
- Integration tests: build with per-profile/env matrices; verify toggles (e.g., `minify_html`, `validate_links`, `[output_formats]`)

Key behavior exercised by tests (examples from code):
```151:154:/Users/llane/Documents/github/python/bengal/bengal/health/validators/connectivity.py
orphan_threshold = site.config.get("health_check", {}).get("orphan_threshold", 5)
```
```54:60:/Users/llane/Documents/github/python/bengal/bengal/utils/url_strategy.py
i18n = site.config.get("i18n", {}) or {}
strategy = i18n.get("strategy", "none")
```

## 10) Documentation & Example Updates

- Example `bengal.toml.example` gains:
  - `profile = "writer"` (top)
  - `[profiles.dev]` quick-start overrides
  - `[env.production]` and `[env.preview]` stubs
  - `[features]` one-liners mapping to advanced sections
  - Clear note that `[output_formats]` supersedes `[build.output_formats]`

## 11) Impact Assessment

- Developer UX: Big improvement (discoverability, predictability, introspection)
- Back-compat: Maintained with alias normalization + warnings
- Future-proofing: Versioning and plugin namespace reduce churn cost

## 12) Confidence & Rationale

Evidence weight: strong (existing normalizers, profile logic, section aliases)
Consistency: high (clear precedence, origin tracking)
Recency: current codebase analysis
Tests: proposed suite covers critical flows

Confidence: 88% (Ready to implement behind warnings; review recommended)
