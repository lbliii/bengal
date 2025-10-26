Title: RFC — Config System v2: Directory-Based, Environment-Aware, Profile-Native
Status: Draft
Owners: Bengal Core
Created: 2025-10-25
Supersedes: rfc-config-ergonomics-profiles-env-introspection.md

## Executive Summary

**No users = no compromises. Go straight to excellence.**

Adopt Hugo's proven config directory pattern. Make environments and profiles first-class filesystem concepts. Use YAML for power, support TOML for simplicity. Clean, composable, grep-able.

## 1) Problem Statement

Current config system has accumulated cruft:
- Flat keys mixed with nested sections (confusing discovery)
- Profiles are CLI-only, not declarative
- No environment-aware configuration
- Single-file gets unwieldy for complex sites
- No clear separation of concerns

We have no users yet. We can fix this RIGHT NOW before anyone depends on it.

## 2) Goals

1. **Directory-first**: `config/` pattern like Hugo, Rails, Kubernetes
2. **Environment-native**: `production/`, `staging/`, `local/` as directories
3. **Profile-native**: Build profiles as config files, not runtime logic
4. **Composable**: YAML anchors for DRY, filesystem for precedence
5. **Introspectable**: Clear origin (filename), easy to debug
6. **Scalable**: Simple sites stay simple, complex sites have structure

## 3) Design

### Directory Structure

```
config/
├── _default/              # Base config (always loaded)
│   ├── site.yaml          # Core: title, baseurl, description
│   ├── build.yaml         # Build: parallel, incremental, cache
│   ├── features.yaml      # Toggles: rss, sitemap, search, json
│   ├── theme.yaml         # Theme config and appearance
│   ├── markdown.yaml      # Markdown parser settings
│   ├── assets.yaml        # Asset pipeline config
│   ├── fonts.yaml         # Font configuration
│   ├── health.yaml        # Health checks and validation
│   └── menus.yaml         # Menu definitions
│
├── environments/          # Environment-specific overrides
│   ├── local.yaml         # Local dev (debug, verbose)
│   ├── preview.yaml       # Deploy previews (Netlify/Vercel)
│   └── production.yaml    # Production (strict, optimized)
│
└── profiles/              # Build profiles
    ├── writer.yaml        # Content-focused (fast, quiet)
    ├── theme-dev.yaml     # Template-focused (timing, rendering checks)
    └── dev.yaml           # Full observability (all metrics, all checks)
```

### Merge Order (Clear Precedence)

```
1. config/_default/*.yaml       [Base layer]
2. config/environments/<env>.yaml  [Environment overrides]
3. config/profiles/<profile>.yaml  [Profile settings]
4. Environment variables           [Runtime overrides]
5. CLI flags                       [Highest priority]
```

### Activation

```bash
# Environment via flag (explicit)
bengal build --environment production

# Environment via env var (CI/CD)
export BENGAL_ENV=production
bengal build

# Auto-detect environment (smart defaults)
# - Netlify: detect from NETLIFY=true → "preview" or "production"
# - Vercel: detect from VERCEL=1 → "preview" or "production"
# - GitHub Actions: detect from GITHUB_ACTIONS → "production"
# - Local: default to "local"

# Profile selection (orthogonal to environment)
bengal build --profile dev
bengal build --environment production --profile theme-dev
```

### Fallback for Simple Sites

**Single-file configs still work:**

```yaml
# bengal.yaml (root directory)
site:
  title: My Simple Blog
  baseurl: https://example.com

features:
  rss: true
  sitemap: true
  search: true

build:
  parallel: true
  incremental: true
```

**Precedence**: `config/` directory takes priority over root `bengal.yaml` or `bengal.toml`

### Example Configs

#### `config/_default/site.yaml`
```yaml
title: Bengal Documentation
description: Modern static site generator
language: en
timezone: UTC

# Default appearance (overridden by theme.yaml if present)
appearance: system  # light | dark | system
```

#### `config/_default/build.yaml`
```yaml
# Build defaults (DRY via anchors)
defaults: &defaults
  parallel: true
  incremental: true
  minify_html: true
  cache_templates: true

output:
  dir: public
  clean: true

# Apply defaults
<<: *defaults
```

#### `config/_default/features.yaml`
```yaml
# Simple on/off toggles for common features
# Maps to detailed config sections automatically

rss: true              # → generate_rss + output_formats
sitemap: true          # → generate_sitemap
search: true           # → search page + preload strategy
json: true             # → output_formats.per_page: [json]
llm_txt: true          # → output_formats.per_page: [llm_txt]
minify_assets: true    # → assets.minify
validate_links: true   # → health.linkcheck.enabled
```

#### `config/environments/production.yaml`
```yaml
site:
  baseurl: https://docs.bengal.dev

build:
  strict_mode: true    # Fail on errors
  validate_build: true # Full health checks
  debug: false

features:
  validate_links: true
  minify_assets: true
  minify_html: true

health:
  linkcheck:
    external: true
    timeout: 10
    retries: 3
```

#### `config/environments/local.yaml`
```yaml
build:
  debug: true
  strict_mode: false
  fast_mode: true

dev:
  traceback:
    style: compact
    show_locals: false
    max_frames: 10
```

#### `config/profiles/writer.yaml`
```yaml
# Content writer profile: fast, quiet, minimal checks
observability:
  show_phase_timing: false
  track_memory: false
  verbose_build_stats: false

health_checks:
  enabled:
    - config
    - output
    - links
  # Disable expensive checks
  disabled:
    - performance
    - cache
    - directives
    - rendering
    - navigation
```

#### `config/profiles/dev.yaml`
```yaml
# Developer profile: full observability
observability:
  show_phase_timing: true
  track_memory: true
  verbose_build_stats: true
  collect_metrics: true
  enable_debug_output: true

health_checks:
  enabled: all  # Run everything

live_progress:
  enabled: true
  show_recent_items: true
  show_metrics: true
  max_recent: 5
```

### YAML Anchors for DRY

```yaml
# config/_default/build.yaml
strict_settings: &strict
  strict_mode: true
  validate_build: true
  fail_on_warnings: true

relaxed_settings: &relaxed
  strict_mode: false
  validate_build: false
  fail_on_warnings: false

# Default to relaxed
<<: *relaxed

# config/environments/production.yaml
# Override with strict
<<: *strict
```

### Feature Groups (Ergonomic → Detailed Mapping)

**Implementation**: `features.yaml` keys expand to detailed config

```python
FEATURE_MAPPINGS = {
    "rss": {
        "generate_rss": True,
        "output_formats.site_wide": ["rss"],
    },
    "sitemap": {
        "generate_sitemap": True,
    },
    "search": {
        "search.enabled": True,
        "search.preload": "smart",
    },
    "json": {
        "output_formats.per_page": ["json"],
    },
    "llm_txt": {
        "output_formats.per_page": ["llm_txt"],
    },
    "validate_links": {
        "validate_links": True,
        "health.linkcheck.enabled": True,
    },
    "minify_assets": {
        "assets.minify": True,
    },
    "minify_html": {
        "minify_html": True,
        "html_output.mode": "minify",
    },
}
```

**Loader expands features FIRST**, then detailed config can override:

```yaml
# config/_default/features.yaml
json: true  # Expands to output_formats.per_page: [json]

# config/_default/output_formats.yaml (if needed, overrides expansion)
per_page:
  - json
  - llm_txt
site_wide:
  - index_json
  - llm_full
options:
  json_indent: 0
  include_full_content_in_index: false
```

## 4) Introspection Commands

### `bengal config show`

**Show effective merged config**

```bash
# Show merged config for default environment
bengal config show

# Show merged config for specific environment
bengal config show --environment production

# Show merged config with profile
bengal config show --environment production --profile dev

# Show with origin (which file contributed each key)
bengal config show --origin

# Show specific section
bengal config show site
bengal config show build.output
```

**Output with origin**:
```yaml
site:
  title: Bengal Docs                    # _default/site.yaml
  baseurl: https://docs.bengal.dev      # environments/production.yaml
  description: Modern SSG               # _default/site.yaml

build:
  parallel: true                        # _default/build.yaml
  strict_mode: true                     # environments/production.yaml
  debug: false                          # environments/production.yaml
```

### `bengal config doctor`

**Lint and validate config**

```bash
bengal config doctor

# Check specific environment
bengal config doctor --environment production
```

**Checks**:
- ✅ Valid YAML syntax in all files
- ✅ No unknown keys (typo detection with suggestions)
- ✅ Type checking (bool, int, str validation)
- ✅ Required fields present (title, baseurl for production)
- ✅ Value ranges (max_workers >= 0, port 1-65535)
- ✅ Deprecated keys (suggest modern equivalents)
- ⚠️ Warnings for common mistakes
- 🔍 Orphaned files (config files not loaded)

**Example output**:
```
🩺 Config Health Check

✅ Syntax: All YAML files valid
✅ Required: title, baseurl present
⚠️  Warning: config/environments/preview.yaml not used (did you mean 'preview' environment?)
❌ Error: Unknown key 'strict_moode' in production.yaml (did you mean 'strict_mode'?)
❌ Error: build.max_workers must be >= 0, got -1

📊 Summary: 2 errors, 1 warning
```

### `bengal config diff`

**Compare configurations**

```bash
# Compare environments
bengal config diff --environment local --against production

# Compare profiles
bengal config diff --profile writer --against dev

# Compare against defaults
bengal config diff --environment production --against defaults
```

**Output**:
```diff
# local → production
site:
  - baseurl: ""                        [local]
  + baseurl: "https://docs.bengal.dev" [production]

build:
  - strict_mode: false                 [local]
  + strict_mode: true                  [production]

  - debug: true                        [local]
  + debug: false                       [production]
```

### `bengal config init`

**Scaffold config directory**

```bash
# Create config/ structure with examples
bengal config init --type directory

# Create simple single-file config
bengal config init --type file

# Create with specific template
bengal config init --template docs   # Documentation site
bengal config init --template blog   # Blog site
bengal config init --template minimal # Minimal config
```

**Creates**:
```
✨ Created config structure:
   config/_default/site.yaml       (core settings)
   config/_default/features.yaml   (feature toggles)
   config/environments/local.yaml  (local dev)
   config/environments/production.yaml (production)
   config/profiles/writer.yaml     (content writer profile)

💡 Next steps:
   1. Edit config/_default/site.yaml (add title, baseurl)
   2. Run: bengal config doctor
   3. Build: bengal build --environment local
```

### `bengal config validate`

**Strict validation (CI/CD)**

```bash
# Validate all environments
bengal config validate --all

# Validate specific environment
bengal config validate --environment production

# Exit code 0 = valid, 1 = invalid (CI-friendly)
```

## 5) Migration from Current System

### Phase 1: Support Both (1-2 weeks)

**Keep existing single-file support**, add config directory support:

```python
def load_config(root_path: Path) -> dict:
    # Priority 1: config/ directory
    if (config_dir := root_path / "config").exists():
        return load_config_directory(config_dir)

    # Priority 2: bengal.yaml (single file)
    if (yaml_file := root_path / "bengal.yaml").exists():
        return load_yaml_file(yaml_file)

    # Priority 3: bengal.toml (legacy)
    if (toml_file := root_path / "bengal.toml").exists():
        return load_toml_file(toml_file)

    # Default
    return default_config()
```

### Phase 2: Update Examples and Docs (1 week)

- Update `bengal.toml.example` → `config/_default/*.yaml` examples
- Update CLI docs to show config directory usage
- Update Getting Started guide
- Add migration guide for internal test sites

### Phase 3: Deprecate Single-File (Future)

- After 6 months, recommend config directory for new projects
- Keep single-file for simple sites (no breaking change)

## 6) Detailed Design: Loader Implementation

### Config Directory Loader

```python
from pathlib import Path
from typing import Any
import yaml

class ConfigDirectoryLoader:
    """Load and merge config from directory structure."""

    def load(
        self,
        config_dir: Path,
        environment: str = "local",
        profile: str | None = None,
    ) -> dict[str, Any]:
        """
        Load config with precedence:
        1. _default/*.yaml (base)
        2. environments/<env>.yaml (env overrides)
        3. profiles/<profile>.yaml (profile settings)
        """
        config = {}

        # Layer 1: Base defaults
        defaults_dir = config_dir / "_default"
        if defaults_dir.exists():
            config = self._load_directory(defaults_dir)

        # Layer 2: Environment overrides
        env_file = config_dir / "environments" / f"{environment}.yaml"
        if env_file.exists():
            env_config = self._load_yaml(env_file)
            config = self._deep_merge(config, env_config)

        # Layer 3: Profile settings
        if profile:
            profile_file = config_dir / "profiles" / f"{profile}.yaml"
            if profile_file.exists():
                profile_config = self._load_yaml(profile_file)
                config = self._deep_merge(config, profile_config)

        # Layer 4: Expand feature groups
        config = self._expand_features(config)

        return config

    def _load_directory(self, directory: Path) -> dict[str, Any]:
        """Load all YAML files in directory and merge."""
        config = {}
        for yaml_file in sorted(directory.glob("*.yaml")):
            section_config = self._load_yaml(yaml_file)
            config = self._deep_merge(config, section_config)
        return config

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        """Load single YAML file with error handling."""
        try:
            with path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in {path}: {e}")

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge override into base (override wins)."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _expand_features(self, config: dict) -> dict:
        """Expand features.* toggles to detailed config."""
        if "features" not in config:
            return config

        features = config.pop("features")
        for feature_name, enabled in features.items():
            if enabled and feature_name in FEATURE_MAPPINGS:
                mapping = FEATURE_MAPPINGS[feature_name]
                for key_path, value in mapping.items():
                    # Apply mapping if not already explicitly set
                    self._set_if_missing(config, key_path, value)

        return config

    def _set_if_missing(self, config: dict, key_path: str, value: Any) -> None:
        """Set nested key if not already present."""
        keys = key_path.split(".")
        current = config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        final_key = keys[-1]
        if final_key not in current:
            current[final_key] = value
```

### Origin Tracking (for `config show --origin`)

```python
class ConfigWithOrigin:
    """Track which file contributed each config key."""

    def __init__(self):
        self.config: dict[str, Any] = {}
        self.origins: dict[str, str] = {}  # key_path → file_path

    def merge(self, other: dict, origin: str) -> None:
        """Merge config and track origin."""
        self._merge_recursive(self.config, other, origin, [])

    def _merge_recursive(
        self,
        base: dict,
        override: dict,
        origin: str,
        path: list[str],
    ) -> None:
        """Recursively merge and track origins."""
        for key, value in override.items():
            key_path = ".".join(path + [key])

            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._merge_recursive(base[key], value, origin, path + [key])
            else:
                base[key] = value
                self.origins[key_path] = origin

    def show_with_origin(self) -> str:
        """Format config with origin annotations."""
        lines = []
        self._format_recursive(self.config, lines, [], indent=0)
        return "\n".join(lines)

    def _format_recursive(
        self,
        config: dict,
        lines: list[str],
        path: list[str],
        indent: int,
    ) -> None:
        """Format config with origins as comments."""
        for key, value in config.items():
            key_path = ".".join(path + [key])
            origin = self.origins.get(key_path, "unknown")

            if isinstance(value, dict):
                lines.append(f"{'  ' * indent}{key}:")
                self._format_recursive(value, lines, path + [key], indent + 1)
            else:
                lines.append(f"{'  ' * indent}{key}: {value}  # {origin}")
```

## 7) Environment Detection (Smart Defaults)

```python
def detect_environment() -> str:
    """Auto-detect environment from platform."""

    # Explicit override
    if env := os.getenv("BENGAL_ENV"):
        return env

    # Netlify
    if os.getenv("NETLIFY") == "true":
        if os.getenv("CONTEXT") == "production":
            return "production"
        return "preview"

    # Vercel
    if os.getenv("VERCEL") == "1":
        if os.getenv("VERCEL_ENV") == "production":
            return "production"
        return "preview"

    # GitHub Actions
    if os.getenv("GITHUB_ACTIONS") == "true":
        # Assume production for CI
        return "production"

    # Default: local development
    return "local"
```

## 8) Validation Schema (Optional Strict Mode)

```python
from pydantic import BaseModel, Field

class SiteConfig(BaseModel):
    """Site configuration schema."""
    title: str = Field(..., min_length=1)
    baseurl: str = Field(default="")
    description: str = Field(default="")
    language: str = Field(default="en")

class BuildConfig(BaseModel):
    """Build configuration schema."""
    parallel: bool = Field(default=True)
    incremental: bool = Field(default=True)
    minify_html: bool = Field(default=True)
    max_workers: int = Field(default=0, ge=0)
    output_dir: str = Field(default="public")

class BengalConfig(BaseModel):
    """Root config schema."""
    site: SiteConfig
    build: BuildConfig
    # ... other sections

# Usage
def validate_config(config: dict) -> None:
    """Validate config against schema."""
    try:
        BengalConfig(**config)
    except ValidationError as e:
        raise ConfigError(f"Config validation failed: {e}")
```

## 9) Testing Strategy

### Unit Tests

```python
def test_config_directory_loading(tmp_path):
    """Test loading from config directory."""
    config_dir = tmp_path / "config"
    defaults = config_dir / "_default"
    defaults.mkdir(parents=True)

    # Create base config
    (defaults / "site.yaml").write_text("title: Test Site\nbaseurl: ''")

    # Create environment override
    envs = config_dir / "environments"
    envs.mkdir()
    (envs / "production.yaml").write_text("site:\n  baseurl: https://example.com")

    # Load config
    loader = ConfigDirectoryLoader()
    config = loader.load(config_dir, environment="production")

    assert config["site"]["title"] == "Test Site"
    assert config["site"]["baseurl"] == "https://example.com"

def test_feature_expansion():
    """Test feature groups expand to detailed config."""
    config = {"features": {"rss": True, "json": True}}
    loader = ConfigDirectoryLoader()
    expanded = loader._expand_features(config)

    assert expanded["generate_rss"] is True
    assert "json" in expanded["output_formats"]["per_page"]

def test_precedence_order():
    """Test merge precedence: default < env < profile."""
    # Test that later layers override earlier layers
    pass

def test_origin_tracking():
    """Test config origin tracking for introspection."""
    pass
```

### Integration Tests

```python
def test_build_with_environment(tmp_path):
    """Test building with different environments."""
    # Setup site with config directory
    # Build with --environment production
    # Assert production settings applied
    pass

def test_profile_observability(tmp_path):
    """Test profile configs affect build behavior."""
    # Build with --profile dev
    # Assert health checks enabled
    # Assert metrics collected
    pass
```

## 10) Documentation Updates

### Quick Start

```markdown
# Quick Start

## Simple Site (Single File)

Create `bengal.yaml`:

```yaml
site:
  title: My Blog
  baseurl: https://myblog.com

features:
  rss: true
  sitemap: true
  search: true
```

Build: `bengal build`

## Complex Site (Directory Structure)

Initialize: `bengal config init --type directory`

Creates:
- `config/_default/` - Base config
- `config/environments/` - Environment overrides
- `config/profiles/` - Build profiles

Edit configs, then build:
```bash
bengal build --environment production --profile writer
```
```

### Config Reference

```markdown
# Configuration Reference

## Directory Structure

- `config/_default/` - Base configuration (always loaded)
- `config/environments/` - Environment-specific overrides
- `config/profiles/` - Build profile settings

## Merge Order

1. Default config
2. Environment config
3. Profile config
4. Environment variables
5. CLI flags

## Environment Selection

Auto-detected or explicit:

```bash
# Explicit
bengal build --environment production

# Environment variable
export BENGAL_ENV=production

# Auto-detect (Netlify, Vercel, GitHub Actions)
bengal build  # Automatically uses correct environment
```
```

## 11) Implementation Plan

**Total: 4-5 weeks**

### Week 1: Core Loader
- ✅ Implement `ConfigDirectoryLoader`
- ✅ Deep merge logic
- ✅ Environment detection
- ✅ Feature expansion
- ✅ Unit tests (90%+ coverage)

### Week 2: Introspection Commands
- ✅ `bengal config show`
- ✅ `bengal config show --origin`
- ✅ `bengal config doctor`
- ✅ `bengal config diff`
- ✅ `bengal config init`

### Week 3: Integration
- ✅ Update `Site.from_config()` to use new loader
- ✅ Profile integration (load from config files)
- ✅ Environment integration (CLI + auto-detect)
- ✅ Integration tests

### Week 4: Examples and Docs
- ✅ Update example configs
- ✅ Update Getting Started guide
- ✅ Write config reference docs
- ✅ Migration guide for internal test sites

### Week 5: Polish
- ✅ Performance testing
- ✅ Error message polish
- ✅ Edge case handling
- ✅ Final review and merge

## 12) Success Metrics

- ✅ Config loading < 50ms for complex sites (10+ files)
- ✅ `config doctor` catches 95%+ typos
- ✅ `config show` accurately reflects merged config
- ✅ Simple sites need < 10 lines of config
- ✅ Complex sites organized with < 5 files per concern
- ✅ Zero backward incompatibility concerns (no users yet!)

## 13) Advantages Over Previous Design

| Aspect | Old RFC | New RFC (This) |
|--------|---------|----------------|
| **Complexity** | Custom merge + origin tracking + in-file sections | Standard YAML + filesystem precedence |
| **Discoverability** | `[env.production]` inline | `config/environments/production.yaml` visible |
| **Reusability** | Custom normalization | YAML anchors (standard) |
| **Scalability** | Single file gets large | Split concerns across files |
| **Migration** | Backward compat burden | No users = clean slate |
| **Learning curve** | Bengal-specific syntax | Industry pattern (Hugo, Rails) |
| **Introspection** | Complex origin tracking | File path IS the origin |

## 14) Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Too many files** | Overwhelming for simple sites | Keep single-file support for < 20 config lines |
| **Performance** | Loading 10+ YAML files | Cache parsed config, lazy load, benchmark < 50ms |
| **YAML complexity** | Anchors are powerful but can confuse | Provide clear examples, recommend for advanced use |
| **Breaking change** | (None - no users) | Document clearly, provide examples |

## 15) Future Enhancements

### Config Composition (Import)
```yaml
# config/_default/site.yaml
import:
  - ../../shared-config/base.yaml

title: My Site
```

### Environment Variables in Config
```yaml
site:
  baseurl: ${DEPLOY_URL}
  api_key: ${API_KEY}
```

### Remote Config
```yaml
import:
  - https://cdn.example.com/configs/defaults.yaml
```

### Config Encryption
```yaml
secrets:
  api_key: !encrypted |
    AES256:abcd1234...
```

## 16) Conclusion

**This is the RIGHT design for Bengal.**

- ✅ Proven pattern (Hugo, Rails, Kubernetes)
- ✅ Scales from simple to complex
- ✅ Environment-aware by design
- ✅ Profile-native, not bolted on
- ✅ Introspectable with clear origins
- ✅ No backward compat burden
- ✅ Clean implementation (less code than previous RFC)

**Confidence**: 95% 🟢

**Recommendation**: ✅ **Implement immediately**

---

**Let's build this.** 🚀
