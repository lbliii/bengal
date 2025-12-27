# RFC: Deployment Profiles

## Problem

Currently Bengal requires manual configuration for deployment:
- User must know to set `baseurl` for GitHub Pages project sites
- No validation that config is correct for target platform
- "Works locally, breaks in prod" is too common
- Different platforms have different requirements (GitHub Pages, Netlify, Cloudflare, Vercel, S3, etc.)

## Proposal

Add first-class deployment profile support that:
1. Auto-detects platform when possible
2. Validates configuration for the target
3. Provides sensible defaults per platform
4. Warns about common misconfigurations at build time

## Configuration

```yaml
# config/environments/production.yaml

deploy:
  # Explicit platform specification
  platform: github-pages  # github-pages | netlify | cloudflare | vercel | s3 | static

  # Platform-specific options
  github_pages:
    # Auto-detect from git remote, or specify explicitly
    repo: lane-neuro/bengal  # optional, auto-detected from git
    type: project  # project | user-org (auto-detected from repo name)
    # baseurl is AUTO-SET based on repo name for project sites

  # OR for other platforms
  netlify:
    site_id: my-site  # optional

  cloudflare:
    project_name: my-docs
```

## Auto-Detection Logic

### GitHub Pages
```python
def detect_github_pages_config():
    # 1. Check git remote for github.com
    remote = get_git_remote_url()
    if 'github.com' not in remote:
        return None

    # 2. Parse owner/repo
    owner, repo = parse_github_remote(remote)

    # 3. Determine site type
    if repo == f"{owner}.github.io":
        # User/org site - no baseurl needed
        return {"type": "user-org", "baseurl": ""}
    else:
        # Project site - baseurl = /repo
        return {"type": "project", "baseurl": f"/{repo}"}
```

### Environment Variables (CI Detection)
```python
# Auto-detect platform from CI environment
def detect_platform():
    if os.environ.get("GITHUB_ACTIONS"):
        return "github-pages"
    if os.environ.get("NETLIFY"):
        return "netlify"
    if os.environ.get("CF_PAGES"):
        return "cloudflare"
    if os.environ.get("VERCEL"):
        return "vercel"
    return "static"  # fallback
```

## Build-Time Validation

When building for production, Bengal validates:

### GitHub Pages
- [ ] baseurl matches repo name (for project sites)
- [ ] .nojekyll will be created
- [ ] Asset paths use baseurl correctly
- [ ] No absolute paths that bypass baseurl

### All Platforms
- [ ] All internal links are valid
- [ ] All asset references resolve
- [ ] No hardcoded localhost URLs
- [ ] Canonical URLs are correct

## Warning Examples

```
⚠️  GitHub Pages project site detected: lane-neuro/bengal
    Expected baseurl: /bengal
    Configured baseurl: (empty)

    Fix: Set `site.baseurl: "/bengal"` in production.yaml
    Or: Use `deploy.platform: github-pages` for auto-configuration

⚠️  Found 3 absolute asset paths that bypass baseurl:
    - templates/base.html:45: href="/assets/style.css"
    Should be: href="{{ asset_url('style.css') }}"
```

## New CLI Commands

```bash
# Show detected deployment info
bengal deploy info
# Output:
#   Platform: github-pages (auto-detected)
#   Site type: project
#   Repo: lane-neuro/bengal  
#   Baseurl: /bengal
#   Build command: bengal build -e production

# Validate deployment config
bengal deploy validate
# Output:
#   ✓ Platform detected: github-pages
#   ✓ Baseurl correctly set to /bengal
#   ✓ Asset URLs use asset_url() function
#   ⚠️ 2 internal links not verified (pages don't exist yet)

# Build with deployment validation
bengal build -e production --validate-deploy
```

## Implementation Phases

### Phase 1: Detection & Validation
- Add `deploy` config section
- Implement platform auto-detection
- Add build-time baseurl validation
- Warn on common misconfigurations

### Phase 2: Auto-Configuration
- Auto-set baseurl for GitHub Pages
- Generate platform-specific files (.nojekyll, _redirects, etc.)
- Platform-specific asset handling

### Phase 3: Deploy Command
- `bengal deploy` command for common platforms
- Direct deployment without separate CI
- Preview URL generation

## Benefits

1. **Fewer "works locally, breaks in prod"** - Validation catches issues before deploy
2. **Less configuration** - Auto-detection handles common cases
3. **Better DX** - Clear errors with actionable fixes
4. **Platform flexibility** - Easy to switch between hosting providers

## Open Questions

1. Should auto-detection be opt-in or opt-out?
2. How to handle custom domains on GitHub Pages?
3. Should we support direct deployment (like `hugo deploy`)?
