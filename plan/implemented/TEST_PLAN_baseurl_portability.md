# Baseurl Portability and Search Index Test Plan

## Goals
- Ensure Bengal output works at domain root and arbitrary subpaths across hosts.
- Prevent regressions in env-based baseurl overrides, URL generation, and search index loading.

## Scope
- Config overrides (env and explicit config)
- Asset URLs and fingerprint lookup
- Template internal links and meta exposure
- Search index generation and client loading
- Integration builds with baseurl variations

## Test Matrix
- baseurl: "" (root), "/bengal" (path-only), "https://example.com/sub" (absolute)
- env: none, BENGAL_BASEURL set, Netlify (URL/DEPLOY_PRIME_URL), Vercel (VERCEL_URL), GitHub Actions (GITHUB_REPOSITORY)

## Unit Tests
1) ConfigLoader env overrides
- Given no config baseurl and BENGAL_BASEURL set → config.baseurl == env
- Given no config baseurl and NETLIFY URL/DEPLOY_PRIME_URL set → picks those
- Given VERCEL_URL hostname → prefixes https:// when absent
- Given GITHUB_ACTIONS with owner/repo → computes https://owner.github.io/repo
- Given explicit baseurl in config → env does not override

2) TemplateEngine._asset_url
- No baseurl → "/assets/css/style.css"
- baseurl "/bengal" → "/bengal/assets/css/style.css"
- baseurl "https://x/y" → "https://x/y/assets/css/style.css"
- Fingerprinted file exists in output_dir/assets/css/style.<hash>.css → returns that path with baseurl

3) Template rendering (default theme)
- Render sample page with baseurl set; assert:
  - meta name="bengal:baseurl" present with correct value
  - nav/footer/breadcrumb anchors use | absolute_url prefix

4) OutputFormats index.json
- After build, index.json exists at output root
- JSON includes site.baseurl and pages with uri and url

## Integration Tests
5) Build with baseurl path-only
- baseurl="/bengal"; build test site
- Assert all generated HTML link href/src start with "/bengal/" for internal resources
- assets exist and match URLs (fingerprinted)

6) Build with absolute baseurl
- baseurl="https://example.com/sub"; build
- Assert internal links are absolute to that origin

7) Search client baseurl resolution
- Open built search HTML and parse script/meta
- Simulate window.document meta and verify constructed fetch URL equals `${baseurl}/index.json`

## Optional E2E (if infra available)
- Serve built site under a subpath and verify network request to `<baseurl>/index.json` returns 200 and search results render

## Implementation Notes
- Place unit tests in tests/unit/... matching modules
- Place integration tests in tests/integration/... using existing build helpers
- Keep tests fast: small sample content and minimal theme usage
- Use temporary directories for output; clean up after

## Exit Criteria
- All new tests pass locally and in CI
- Fails if any baseurl permutations break links/assets/search
