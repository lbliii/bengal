# RFC: Deployment Profiles

## Problem

Bengal users encounter deployment failures despite successful local builds:

1. **Baseurl misconfiguration** - Project sites on GitHub Pages require `/repo-name` baseurl, which users forget or misconfigure
2. **No pre-deploy validation** - Build succeeds but links break in production
3. **Platform-specific requirements unclear** - GitHub Pages needs `.nojekyll`, Netlify uses `_redirects`, etc.
4. **Poor discoverability** - Users don't know what Bengal auto-detects vs. what they must configure

## Prior Art

Bengal already has runtime platform detection in `bengal/config/env_overrides.py`:

```python
# Existing: Auto-detection via CI environment variables
# Priority: BENGAL_BASEURL > Netlify > Vercel > GitHub Pages

if os.environ.get("GITHUB_ACTIONS") == "true":
    # Auto-sets baseurl to /{repo-name} for project sites
    # Detects user/org sites ({owner}.github.io) and uses empty baseurl

if os.environ.get("NETLIFY") == "true":
    # Uses URL or DEPLOY_PRIME_URL

if os.environ.get("VERCEL") in ("1", "true"):
    # Uses VERCEL_URL with https:// prefix
```

**What works today**:
- ✅ CI environment auto-detection (GitHub Actions, Netlify, Vercel)
- ✅ Baseurl auto-configuration in CI
- ✅ Explicit override via `BENGAL_BASEURL` env var
- ✅ User/org vs project site detection for GitHub Pages

**What's missing** (this RFC):
- ❌ Local development platform awareness (no CI env vars)
- ❌ Pre-build validation
- ❌ Platform-specific file generation (`.nojekyll`)
- ❌ CLI for inspecting detected configuration
- ❌ Cloudflare Pages detection

## Proposal

Extend the existing auto-detection with:
1. **Explicit `deploy` config** - Optional declaration for local awareness
2. **Validation layer** - Catch misconfigurations before build
3. **Platform files** - Auto-generate `.nojekyll`, `_redirects`, etc.
4. **CLI commands** - Inspect and validate deployment configuration

## Configuration

The `deploy` section is **optional**. When present, it provides explicit platform targeting and enables local validation. When absent, runtime detection from `env_overrides.py` continues to work.

```yaml
# config/environments/production.yaml

deploy:
  # Explicit platform (optional - enables local validation)
  platform: github-pages  # github-pages | netlify | cloudflare | vercel | s3 | static

  # Platform-specific options (all optional)
  github_pages:
    repo: owner/repo      # Auto-detected from git remote
    type: project         # project | user-org (auto-detected)
    custom_domain: docs.example.com  # Optional: disables baseurl requirement

  netlify:
    # No baseurl needed - Netlify serves from root
    generate_redirects: true  # Create _redirects for SPA routing

  cloudflare:
    # No baseurl needed - Cloudflare Pages serves from root

  vercel:
    # No baseurl needed - Vercel serves from root
```

### Config vs Runtime Detection

| Scenario | Config `deploy:` | Runtime Detection | Result |
|----------|------------------|-------------------|--------|
| CI build, no config | absent | active | Runtime sets baseurl |
| CI build, explicit config | present | skipped | Config values used |
| Local build, no config | absent | inactive | No platform awareness |
| Local build, explicit config | present | n/a | Validation enabled |

**Key principle**: Explicit config always wins. Runtime detection is the fallback for zero-config CI deployments.

## Validation Rules

### GitHub Pages

```python
class GitHubPagesValidator:
    def validate(self, config: dict, site: Site) -> list[Issue]:
        issues = []

        # 1. Baseurl check (unless custom domain)
        if not config.get("custom_domain"):
            repo = detect_repo_name()
            expected = f"/{repo}" if is_project_site(repo) else ""
            actual = config.get("baseurl", "")
            if actual != expected:
                issues.append(Issue(
                    level="error",
                    message=f"Baseurl mismatch: expected '{expected}', got '{actual}'",
                    fix=f"Set site.baseurl: \"{expected}\" in production.yaml"
                ))

        # 2. Check for hardcoded absolute paths in templates
        for template in site.templates:
            if has_absolute_asset_paths(template):
                issues.append(Issue(
                    level="warning",
                    message=f"Absolute asset path in {template.path}",
                    fix="Use {{ asset_url('...') }} instead of /assets/..."
                ))

        return issues
```

### All Platforms

| Check | Level | Description |
|-------|-------|-------------|
| Baseurl consistency | error | Config matches detected platform requirements |
| No localhost URLs | error | Hardcoded `localhost` or `127.0.0.1` in output |
| Asset paths | warning | Absolute paths that bypass baseurl |
| Internal links | warning | Links to non-existent pages |
| Canonical URLs | info | Verify `<link rel="canonical">` uses correct base |

## Platform Files

Auto-generated in output directory when platform is detected/configured:

| Platform | File | Purpose |
|----------|------|---------|
| GitHub Pages | `.nojekyll` | Disable Jekyll processing |
| GitHub Pages | `CNAME` | Custom domain (if configured) |
| Netlify | `_redirects` | SPA routing / redirects |
| Netlify | `_headers` | Security headers (if configured) |
| Cloudflare | `_routes.json` | Functions routing (if applicable) |

## CLI Commands

### `bengal deploy info`

Show detected/configured deployment information:

```bash
$ bengal deploy info

Platform: github-pages
  Source: config (deploy.platform in production.yaml)

Repository: lane-neuro/bengal
  Source: git remote origin

Site Type: project
  Baseurl: /bengal (required)

Configuration Status:
  ✓ site.baseurl matches expected value
  ✓ .nojekyll will be generated

Build Command:
  bengal build -e production
```

### `bengal deploy validate`

Pre-build validation:

```bash
$ bengal deploy validate

Validating deployment configuration...

Platform: github-pages (project site)

Checks:
  ✓ Baseurl correctly set to /bengal
  ✓ No hardcoded localhost URLs
  ✓ Asset URLs use asset_url() or relative paths
  ⚠ 2 templates use absolute paths (non-blocking)
    - templates/custom.html:23
    - templates/widget.html:45

Result: PASS (2 warnings)
```

### `bengal build --validate-deploy`

Build with deployment validation:

```bash
$ bengal build -e production --validate-deploy

Validating deployment configuration... OK
Building site...
  ✓ 42 pages rendered
  ✓ Assets processed
  ✓ .nojekyll generated

Build complete: public/
```

## Implementation Phases

### Phase 1: Validation & CLI (This RFC)

**Scope**: High-value gaps only

- [ ] Add `deploy` config section parsing
- [ ] Implement `bengal deploy info` command
- [ ] Implement `bengal deploy validate` command
- [ ] Add `--validate-deploy` flag to build command
- [ ] Generate `.nojekyll` for GitHub Pages
- [ ] Add Cloudflare Pages detection to `env_overrides.py`

**Files affected**:
- `bengal/config/deploy.py` (new)
- `bengal/cli/commands/deploy.py` (new)
- `bengal/cli/commands/build.py` (add flag)
- `bengal/config/env_overrides.py` (add Cloudflare)
- `bengal/orchestration/build/finalization.py` (add .nojekyll)

**Estimated effort**: 2-3 days

### Phase 2: Extended Platform Support

- [ ] Generate `_redirects` for Netlify
- [ ] CNAME file generation for custom domains
- [ ] S3/static bucket configuration
- [ ] Platform-specific headers generation

### Phase 3: Direct Deployment (Future)

- [ ] `bengal deploy` command (direct push to platforms)
- [ ] Preview URL generation
- [ ] Deployment status checking

**Note**: Phase 3 is explicitly deferred. Most users have CI/CD pipelines; direct deployment is nice-to-have.

## Error Handling

Detection failures should never break builds:

```python
def get_deploy_config(config: dict) -> DeployConfig:
    """Get deployment configuration with graceful fallback."""
    try:
        explicit = config.get("deploy", {})
        if explicit.get("platform"):
            return DeployConfig.from_explicit(explicit)

        detected = detect_platform_from_env()
        if detected:
            return DeployConfig.from_detected(detected)

    except Exception as e:
        logger.warning("deploy_detection_failed", error=str(e))

    return DeployConfig.static()  # Safe fallback
```

## Custom Domains

Custom domains change baseurl requirements:

```yaml
# With custom domain, baseurl is typically empty
deploy:
  platform: github-pages
  github_pages:
    custom_domain: docs.example.com

site:
  baseurl: ""  # Correct for custom domain
```

Detection logic:
1. Check for `CNAME` file in content root
2. Check `deploy.github_pages.custom_domain` config
3. If either present, skip baseurl validation

## Migration Path

**No breaking changes**. This RFC is purely additive:

1. Existing `site.baseurl` config continues to work
2. Existing `BENGAL_BASEURL` env var continues to work
3. Existing `env_overrides.py` runtime detection unchanged
4. New `deploy:` section is optional

Users can adopt incrementally:
- Start with `bengal deploy info` to see what Bengal detects
- Add `deploy:` config if they want local validation
- Use `--validate-deploy` in CI for pre-merge checks

## Design Decisions

### Q: Auto-detection opt-in or opt-out?

**Answer**: Opt-out (current behavior preserved).

Runtime detection via `env_overrides.py` remains active by default. Users who want to disable it can set explicit empty values:

```yaml
site:
  baseurl: ""  # Explicit empty = no auto-detection
```

### Q: How to handle custom domains on GitHub Pages?

**Answer**: CNAME detection + explicit config.

If `CNAME` file exists or `deploy.github_pages.custom_domain` is set, baseurl validation is skipped (custom domains serve from root).

### Q: Should we support direct deployment?

**Answer**: Defer to Phase 3.

Focus on validation first. Direct deployment is complex (auth, error handling, rollback) and most users have CI/CD.

## Success Metrics

1. **Reduced support issues** - Fewer "works locally, breaks on GitHub Pages" reports
2. **Faster debugging** - `bengal deploy info` provides instant clarity
3. **CI integration** - `--validate-deploy` catches issues before merge

## References

- Existing implementation: `bengal/config/env_overrides.py`
- Baseurl tests: `tests/integration/test_baseurl_builds.py`
- Hugo's approach: `hugo deploy` command (Phase 3 reference)
- Astro's approach: Adapter-based deployment configuration
