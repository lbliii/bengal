---
title: "debug config-inspect"
type: "cli-reference"
css_class: "api-content"
source_file: "bengal/cli/commands/debug.py"
description: "🔬 Advanced configuration inspection with origin tracking and impact analysis."
weight: 60
---

# debug config-inspect

**Type:** Command  
**Source:** [View source](https://github.com/lbliii/bengal/blob/main/bengal/cli/commands/debug.py)

:::{badge} Command
:class: badge-secondary
:::

**Command:** `bengal debug config-inspect`

🔬 Advanced configuration inspection and comparison.

Goes beyond `bengal config diff` with origin tracking, impact analysis, and key-level value resolution explanations. Useful for understanding how configuration values are resolved through the layered config system.

## Usage

```bash
bengal debug config-inspect [OPTIONS]
```

## Options

### `--compare-to SOURCE`

Compare current configuration to another source. Source can be:
- Environment name: `production`, `local`, `preview`
- Environment prefix: `env:production`
- Profile prefix: `profile:dev`

### `--explain-key KEY_PATH`

Explain how a specific configuration key got its effective value. Shows the resolution chain through defaults → environment → profile layers.

Key path uses dot notation: `site.title`, `build.parallel`, `features.rss`

### `--list-sources`

List all available configuration sources (environments and profiles).

### `--find-issues`

Find potential configuration issues including:
- Deprecated keys
- Invalid values
- Common misconfigurations

### `--format [console|json]`

Output format. Default is `console`.

## Examples

### List available config sources

```bash
bengal debug config-inspect --list-sources
```

Output:
```
🔬 Config Inspector

Available configuration sources:
   • env:local
   • env:preview
   • env:production
   • profile:dev
   • profile:writer
```

### Compare to production

```bash
bengal debug config-inspect --compare-to production
```

Output:
```
🔬 Config Inspector

Comparing: local → production
  Added: 1
  Removed: 1
  Changed: 2

Added:
  + site.analytics_id: GA-123456 (from environments/production.yaml)

Removed:
  - build.debug: True (was from environments/local.yaml)

Changed:
  site.baseurl:
    - / (_default/site.yaml)
    + https://example.com (environments/production.yaml)
    ⚠️  Changes output URLs and may break links
```

### Explain a specific key

```bash
bengal debug config-inspect --explain-key site.baseurl
```

Output:
```
🔬 Config Inspector

site.baseurl: https://example.com
  Source: environments/production.yaml
  Resolution chain:
    ○ _default/site.yaml: /
    → environments/production.yaml: https://example.com
```

### Find configuration issues

```bash
bengal debug config-inspect --find-issues
```

Output:
```
🔬 Config Inspector

Found 2 potential issue(s):
   ⚠️ baseurl ends with trailing slash
      💡 Consider removing trailing slash for consistency
   ⚠️ Deprecated key: old.key
      💡 Use new.key instead
```

### JSON output for scripting

```bash
bengal debug config-inspect --compare-to production --format json
```

## Comparison Features

### Origin Tracking

Shows which config file contributed each value:

```
site.title:
  - My Site (_default/site.yaml)
  + Production Site (environments/production.yaml)
```

### Impact Analysis

Identifies potentially breaking changes:

| Key Pattern | Impact Warning |
|-------------|----------------|
| `baseurl` | "Changes output URLs and may break links" |
| `theme` | "Changes site appearance and available templates" |
| `parallel` | "Affects build performance" |
| `incremental` | "Affects build performance and caching behavior" |
| `strict_mode` | "Affects error handling during builds" |

### Resolution Chain

For `--explain-key`, shows how value was determined through layers:

```
Resolution chain:
  ○ _default/site.yaml: /            # Base value
  → environments/production.yaml: https://example.com  # Final value (→)
```

The `→` marker indicates the layer that provided the final value.

## Use Cases

### Pre-Deployment Check

Before deploying to production, verify config differences:

```bash
bengal debug config-inspect --compare-to production
```

### Debugging Config Issues

When a value isn't what you expected:

```bash
bengal debug config-inspect --explain-key build.parallel
```

### CI/CD Validation

Check for configuration issues in CI:

```bash
bengal debug config-inspect --find-issues --format json | jq -e '.findings | length == 0'
```

### Documenting Config

Export config comparison for documentation:

```bash
bengal debug config-inspect --compare-to production --format json > config-diff.json
```

## Configuration Layers

Bengal resolves configuration through these layers (in order):

1. **Defaults** (`config/_default/*.yaml`) - Base configuration
2. **Environment** (`config/environments/<env>.yaml`) - Environment overrides
3. **Profile** (`config/profiles/<profile>.yaml`) - Profile settings

Later layers override earlier ones. The inspector shows which layer contributed each value.

## Related Commands

- [`bengal config show`](/cli/config/show/) - Display merged configuration
- [`bengal config diff`](/cli/config/diff/) - Basic config comparison
- [`bengal config doctor`](/cli/config/doctor/) - Validate configuration

## See Also

- [Configuration Guide](/docs/about/concepts/configuration/) - Configuration system overview
- [Environment Overrides](/docs/about/concepts/configuration/environments/) - Environment-specific config
- [Profiles](/docs/about/concepts/configuration/profiles/) - Profile-based configuration

