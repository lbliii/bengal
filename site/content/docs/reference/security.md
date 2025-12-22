---
title: Security Hardening
nav_title: Security
description: Best practices for deploying Bengal sites securely
weight: 50
type: doc
tags: [security, production, hardening]
---

# Security Hardening

Best practices for deploying Bengal sites securely. Since Bengal generates static files, most security concerns relate to HTTP headers, content policies, and build hygiene.

---

## Security Headers

Configure your hosting platform to send security headers with every response.

### Recommended Headers

| Header | Purpose |
|--------|---------|
| `Content-Security-Policy` | Prevents XSS and injection attacks |
| `X-Frame-Options` | Prevents clickjacking |
| `X-Content-Type-Options` | Prevents MIME-type sniffing |
| `Referrer-Policy` | Controls referrer information |
| `Permissions-Policy` | Restricts browser features |
| `Strict-Transport-Security` | Enforces HTTPS |

### Platform Configuration

:::{tab-set}

:::{tab-item} Netlify

Create `netlify.toml` in your project root:

```toml
[[headers]]
  for = "/*"
  [headers.values]
    # Prevent XSS attacks
    Content-Security-Policy = """
      default-src 'self';
      script-src 'self' 'unsafe-inline';
      style-src 'self' 'unsafe-inline';
      img-src 'self' data: https:;
      font-src 'self';
      connect-src 'self';
      frame-ancestors 'none';
    """

    # Prevent clickjacking
    X-Frame-Options = "DENY"

    # Prevent MIME sniffing
    X-Content-Type-Options = "nosniff"

    # Control referrer
    Referrer-Policy = "strict-origin-when-cross-origin"

    # Restrict browser features
    Permissions-Policy = "camera=(), microphone=(), geolocation=()"
```
:::{/tab-item}

:::{tab-item} Vercel

Create `vercel.json` in your project root:

```json
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Content-Security-Policy",
          "value": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';"
        },
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "Referrer-Policy",
          "value": "strict-origin-when-cross-origin"
        },
        {
          "key": "Permissions-Policy",
          "value": "camera=(), microphone=(), geolocation=()"
        }
      ]
    }
  ]
}
```
:::{/tab-item}

:::{tab-item} Cloudflare Pages

Create `_headers` in your output directory (or configure via `public/_headers`):

```text
/*
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
```
:::{/tab-item}

:::{tab-item} Nginx

Add to your server block:

```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

# HSTS (only if using HTTPS)
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```
:::{/tab-item}

:::{tab-item} Apache

Add to `.htaccess` or server config:

```apache
<IfModule mod_headers.c>
  Header always set Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';"
  Header always set X-Frame-Options "DENY"
  Header always set X-Content-Type-Options "nosniff"
  Header always set Referrer-Policy "strict-origin-when-cross-origin"
  Header always set Permissions-Policy "camera=(), microphone=(), geolocation=()"
</IfModule>
```
:::{/tab-item}

:::{/tab-set}

---

## Content Security Policy (CSP)

The Content-Security-Policy header is your primary defense against XSS attacks.

### Base Policy

Start with a restrictive policy and add exceptions as needed:

```text
default-src 'self';
script-src 'self';
style-src 'self';
img-src 'self';
font-src 'self';
connect-src 'self';
frame-ancestors 'none';
```

### Common Additions

| Need | Add to CSP |
|------|------------|
| Inline styles | `style-src 'self' 'unsafe-inline'` |
| Inline scripts | `script-src 'self' 'unsafe-inline'` (avoid if possible) |
| Google Fonts | `font-src 'self' fonts.gstatic.com; style-src 'self' fonts.googleapis.com` |
| Google Analytics | `script-src 'self' www.googletagmanager.com; connect-src www.google-analytics.com` |
| Plausible | `script-src 'self' plausible.io; connect-src plausible.io` |
| External images | `img-src 'self' data: https:` |
| YouTube embeds | `frame-src www.youtube-nocookie.com www.youtube.com` |
| Vimeo embeds | `frame-src player.vimeo.com` |
| CodePen embeds | `frame-src codepen.io` |
| CodeSandbox embeds | `frame-src codesandbox.io` |
| StackBlitz embeds | `frame-src stackblitz.com` |
| GitHub Gist | `script-src 'self' gist.github.com` |
| Asciinema | `script-src 'self' asciinema.org` |

### Testing CSP

Use the browser console to identify CSP violations:

1. Open DevTools (F12)
2. Go to the Console tab
3. Look for CSP violation errors
4. Adjust your policy as needed

---

## Build Hygiene

### Exclude Sensitive Files from Output

Bengal provides multiple ways to exclude sensitive files from your build output:

**Output format exclusions** — Exclude pages from JSON, search, and LLM outputs:

```toml
# bengal.toml
[output_formats.options]
exclude_patterns = ["404.html", "search.html", "admin/*"]
exclude_sections = ["internal"]
```

**Content layer exclusions** — Exclude files during content discovery:

```yaml
# config/_default/sources.yaml
sources:
  - type: local
    directory: content
    exclude:
      - "_drafts/*"
      - "*.secret.md"
      - "internal/*"
```

**Dev server exclusions** — Prevent file watching on sensitive paths:

```toml
# bengal.toml
[dev_server]
exclude_patterns = ["*.env", "secrets/*", "*.key"]
```

**Best practice**: Keep sensitive files outside your content directory entirely. Use `.gitignore` to prevent them from being committed.

### Verify Before Deploy

Run validation before deploying:

```bash
# Validate content and health
bengal validate

# Check for broken links
bengal health linkcheck

# Verify no drafts in production
grep -r "draft: true" content/ && echo "DRAFTS FOUND" || echo "No drafts in content"
```

### CI/CD Validation

Add security checks to your CI pipeline:

```yaml
# GitHub Actions example
- name: Security checks
  run: |
    # Validate no sensitive patterns in output
    ! grep -r "API_KEY\|SECRET\|PASSWORD" public/

    # Validate no draft content in output
    ! grep -r "draft-banner\|data-draft" public/

    # Run Bengal validation
    bengal validate
```

---

## Third-Party Scripts

### Subresource Integrity (SRI)

When loading external scripts, use SRI to verify integrity:

```html
<script
  src="https://cdn.example.com/lib.js"
  integrity="sha384-oqVuAfXRKap7fdgcCY5uykM6+R9GqQ8K/uxh..."
  crossorigin="anonymous">
</script>
```

Generate SRI hashes:

```bash
# Using openssl
curl -s https://cdn.example.com/lib.js | openssl dgst -sha384 -binary | openssl base64 -A

# Using srihash.org
# Visit https://www.srihash.org/
```

### Self-Host When Possible

Bengal's asset fingerprinting provides cache-busting without CDN dependencies:

```toml
# bengal.toml
fingerprint_assets = true  # style.css → style.a1b2c3.css
```

Or in the assets section:

```toml
[assets]
fingerprint = true
minify = true
optimize = true
```

Benefits of self-hosting:
- No third-party dependencies
- No tracking via CDN
- Full control over updates
- Works offline

---

## HTTPS Enforcement

### Verify baseurl

Ensure your configuration uses HTTPS:

```toml
[site]
baseurl = "https://example.com"  # ✅ Use https://
# baseurl = "http://example.com"   # ❌ Avoid http://
```

### HSTS Header

Enable HTTP Strict Transport Security:

```text
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

:::{warning}
Only enable HSTS after confirming HTTPS works correctly. HSTS is cached by browsers and difficult to undo.
:::

---

## Media Embed Security

Bengal's media directives (`{youtube}`, `{vimeo}`, `{gist}`, etc.) include built-in security protections:

### Input Validation

All embed IDs and paths are validated via strict regex patterns:

| Directive | Validation |
|-----------|------------|
| `{youtube}` | Exactly 11 characters: letters, numbers, underscores, hyphens |
| `{vimeo}` | 6-11 digit numeric ID |
| `{gist}` | `username/32-character-hex-id` format |
| `{figure}` | Safe paths starting with `/` or `./`, no `../` traversal |
| `{video}` | Extensions: `.mp4`, `.webm`, `.ogg`, `.mov` |
| `{audio}` | Extensions: `.mp3`, `.ogg`, `.wav`, `.flac`, `.m4a`, `.aac` |

Malicious inputs are rejected with clear error messages:

```markdown
:::{youtube} <script>alert(1)</script>
:title: Test
:::
```

Renders as an error block, not an embed.

### Privacy by Default

External embeds use privacy-respecting modes:

- **YouTube**: Uses `youtube-nocookie.com` by default
- **Vimeo**: Enables Do Not Track (`dnt=1`) by default

### Iframe Sandboxing

External iframes include restricted sandbox attributes to limit capabilities.

### CSP for Media Embeds

If using media embeds, add these frame sources to your CSP:

```text
frame-src 'self' www.youtube-nocookie.com www.youtube.com player.vimeo.com codepen.io codesandbox.io stackblitz.com;
script-src 'self' gist.github.com asciinema.org;
```

Or selectively based on which directives you use.

---

## Dependency Security

### Audit Python Dependencies

```bash
# Using pip-audit
pip install pip-audit
pip-audit

# Using uv
uv pip audit

# Using safety
pip install safety
safety check
```

### Keep Dependencies Updated

```bash
# Check for outdated packages
pip list --outdated

# Update Bengal
pip install --upgrade bengal
```

---

## Draft Protection

Drafts are automatically excluded from listings, sitemap, search index, and RSS feeds.

### How Drafts Work

Mark pages as drafts in frontmatter:

```yaml
---
title: Work in Progress
draft: true
---
```

Draft pages are automatically excluded from:
- `site.pages` queries (listings)
- Sitemap generation
- Search index
- RSS feeds

### Verify Output

```bash
# Build for production
bengal build

# Search for draft indicators in output
grep -r "draft-banner" public/  # Should return nothing
grep -r "data-draft" public/    # Should return nothing

# Verify drafts not in search index
! grep -q '"draft":true' public/index.json
```

### CI Check

```yaml
- name: Verify no drafts
  run: |
    bengal build
    if grep -rq "draft-banner\|data-draft" public/; then
      echo "ERROR: Draft content found in production build"
      exit 1
    fi
```

---

## Security Checklist

Before deploying to production:

### Headers
- [ ] Content-Security-Policy configured
- [ ] X-Frame-Options: DENY
- [ ] X-Content-Type-Options: nosniff
- [ ] Referrer-Policy set
- [ ] HSTS enabled (if HTTPS confirmed working)

### Build
- [ ] Sensitive files excluded from content directory
- [ ] No API keys or secrets in content
- [ ] Drafts marked in frontmatter (auto-excluded from output)
- [ ] Validation passes (`bengal validate`)
- [ ] Links checked (`bengal health linkcheck`)

### Dependencies
- [ ] Dependencies audited for vulnerabilities
- [ ] Bengal and dependencies up to date
- [ ] SRI used for external scripts

### Configuration
- [ ] baseurl uses HTTPS
- [ ] No debug settings in production config
- [ ] Environment-specific configs reviewed

---

## Reporting Security Issues

Found a security vulnerability in Bengal?

**Do NOT open a public GitHub issue.**

Email security concerns to: [security@bengal.dev](mailto:security@bengal.dev)

We'll respond within 48 hours and work with you on a fix before public disclosure.

---

:::{seealso}
- [Deployment Guide](/docs/building/deployment/)
- [CI/CD Setup](/docs/tutorials/automate-with-github-actions/)
- [Configuration Reference](/docs/reference/architecture/tooling/config/)
- [Mozilla Observatory](https://observatory.mozilla.org/) — Test your site's security headers
:::
