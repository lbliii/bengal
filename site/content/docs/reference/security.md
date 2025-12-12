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
:::

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
:::

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
:::

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
:::

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
:::

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

### Exclude Sensitive Files

Ensure sensitive files don't end up in your output:

```toml
# bengal.toml
[build]
exclude = [
  "*.env",
  "*.local",
  ".env*",
  "secrets/",
  ".git/",
  "*.key",
  "*.pem",
  "node_modules/",
  "__pycache__/",
]
```

### Verify Before Deploy

Run validation before deploying:

```bash
# Validate content
bengal validate --strict

# Check for broken links
bengal health linkcheck

# Verify no drafts in production
grep -r "draft: true" public/ && echo "DRAFTS FOUND" || echo "No drafts"
```

### CI/CD Validation

Add security checks to your CI pipeline:

```yaml
# GitHub Actions example
- name: Security checks
  run: |
    # Validate no sensitive patterns
    ! grep -r "API_KEY\|SECRET\|PASSWORD" public/

    # Validate no drafts
    ! grep -r "draft-banner\|class=\"draft\"" public/

    # Run Bengal validation
    bengal validate --strict
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
[assets]
fingerprint = true  # style.css → style.a1b2c3.css
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

All embed IDs and paths are validated:

| Directive | Validation |
|-----------|------------|
| `{youtube}` | 11-character alphanumeric ID only |
| `{vimeo}` | Numeric ID only |
| `{gist}` | `username/hash` format only |
| `{figure}` | Safe paths, no `../` traversal |
| `{video}` / `{audio}` | Extension whitelist |

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

Drafts are excluded from production by default. Verify this works:

### Check Configuration

```toml
# bengal.toml
[build]
include_drafts = false  # Default, but explicit is good
```

### Verify Output

```bash
# Build for production
bengal build

# Search for draft indicators
grep -r "draft" public/  # Should return nothing
grep -r "draft-banner" public/  # Should return nothing
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
- [ ] Sensitive files excluded from build
- [ ] No API keys or secrets in content
- [ ] Drafts excluded from production
- [ ] Validation passes (`bengal validate --strict`)
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
