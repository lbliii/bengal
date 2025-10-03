---
title: "Deployment Best Practices"
date: 2025-10-03
tags: ["deployment", "hosting", "production"]
categories: ["Guides", "Production"]
type: "guide"
description: "Best practices for deploying your Bengal site to production"
author: "Bengal Documentation Team"
---

# Deployment Best Practices

Learn how to deploy your Bengal site to production with confidence, following industry best practices.

## Pre-Deployment Checklist

Before deploying, ensure:

- [ ] All content is proofread and reviewed
- [ ] Links are validated (`validate_links = true`)
- [ ] Images are optimized
- [ ] Site builds without errors
- [ ] Configuration is production-ready
- [ ] baseurl is set correctly
- [ ] 404 page exists
- [ ] Sitemap and RSS are generated

## Production Build

### Clean Build

Always start with a clean build for production:

```bash
# Remove previous build
bengal clean

# Build for production
bengal build --parallel

# Verify output
ls public/
```

### Production Configuration

Use production-optimized settings in `bengal.toml`:

```toml
[site]
title = "My Site"
baseurl = "https://example.com"  # ✅ Full production URL

[build]
parallel = true
incremental = false  # ❌ No cache for production
pretty_urls = true

[assets]
minify = true        # ✅ Minify CSS/JS
optimize = true      # ✅ Optimize images
fingerprint = true   # ✅ Cache busting

[features]
generate_sitemap = true
generate_rss = true
validate_links = true

[dev]
strict_mode = true   # ✅ Fail on errors
validate_build = true
```

## Deployment Platforms

### Netlify

**Recommended for**: Ease of use, automatic deployments

#### Manual Deployment

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Build
bengal build

# Deploy
netlify deploy --prod --dir=public
```

#### Automatic Deployment

Create `netlify.toml`:

```toml
[build]
  command = "bengal build"
  publish = "public"

[build.environment]
  PYTHON_VERSION = "3.11"

[[redirects]]
  from = "/*"
  to = "/404.html"
  status = 404
```

Connect your Git repository and push to deploy automatically!

### Vercel

**Recommended for**: Global CDN, serverless functions

#### Configuration

Create `vercel.json`:

```json
{
  "buildCommand": "pip install bengal-ssg && bengal build",
  "outputDirectory": "public",
  "installCommand": "pip install -r requirements.txt"
}
```

Create `requirements.txt`:

```
bengal-ssg>=0.1.0
```

### GitHub Pages

**Recommended for**: Free hosting, GitHub integration

#### GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Bengal
        run: |
          pip install bengal-ssg
      
      - name: Build site
        run: |
          bengal build
      
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v2
        with:
          path: public
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v2
```

Update `bengal.toml`:

```toml
[site]
baseurl = "https://username.github.io/repository"
```

### Cloudflare Pages

**Recommended for**: Global performance, security features

#### Configuration

1. Connect your Git repository
2. Configure build:
   - **Build command**: `pip install bengal-ssg && bengal build`
   - **Build output**: `public`
   - **Root directory**: `/`

3. Add environment variables:
   - `PYTHON_VERSION`: `3.11`

### AWS S3 + CloudFront

**Recommended for**: Full control, enterprise deployments

#### Upload to S3

```bash
# Install AWS CLI
pip install awscli

# Build
bengal build

# Sync to S3
aws s3 sync public/ s3://your-bucket-name/ \
  --delete \
  --cache-control "public, max-age=31536000"

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id YOUR_DIST_ID \
  --paths "/*"
```

#### S3 Bucket Configuration

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::your-bucket-name/*"
  }]
}
```

### Traditional Web Hosting

**Recommended for**: Existing hosting, full control

```bash
# Build
bengal build

# Upload via FTP/SFTP
# Upload contents of public/ directory to your web root
```

Configure `.htaccess` for pretty URLs:

```apache
# Enable rewrite engine
RewriteEngine On

# Remove .html extension
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^([^\.]+)$ $1.html [NC,L]

# Force HTTPS
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]

# Custom 404 page
ErrorDocument 404 /404.html
```

## Performance Optimization

### Enable Compression

Most platforms enable gzip/brotli automatically. Verify with:

```bash
curl -H "Accept-Encoding: gzip" -I https://example.com
```

### Set Cache Headers

Configure cache control headers:

| File Type | Cache Duration |
|-----------|---------------|
| HTML | No cache or short (1 hour) |
| CSS/JS with fingerprints | 1 year |
| Images | 1 month |
| Fonts | 1 year |

Example Netlify `_headers`:

```
/*
  Cache-Control: public, max-age=3600

/assets/*
  Cache-Control: public, max-age=31536000, immutable

/*.html
  Cache-Control: public, max-age=0, must-revalidate
```

### CDN Configuration

Use a CDN for global performance:

- **Cloudflare**: Automatic CDN
- **AWS CloudFront**: Configure with S3
- **Netlify/Vercel**: Built-in global CDN

## Security Best Practices

### HTTPS

✅ **Always use HTTPS**. Most platforms provide free SSL certificates via Let's Encrypt.

### Security Headers

Add security headers via `_headers` file or server configuration:

```
/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  X-XSS-Protection: 1; mode=block
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: geolocation=(), microphone=(), camera=()
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'
```

### Content Security Policy

Configure CSP for your site:

```
Content-Security-Policy: 
  default-src 'self';
  script-src 'self' 'unsafe-inline';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  font-src 'self';
  connect-src 'self';
  frame-ancestors 'none';
```

## Monitoring and Analytics

### Add Analytics

**Google Analytics**:

Add to `templates/base.html`:

```html
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

**Plausible (Privacy-friendly)**:

```html
<script defer data-domain="example.com" src="https://plausible.io/js/script.js"></script>
```

### Uptime Monitoring

Use services to monitor availability:

- **UptimeRobot**: Free tier available
- **Pingdom**: Comprehensive monitoring
- **Cloudflare**: Built-in analytics

### Error Tracking

Monitor JavaScript errors:

```javascript
window.addEventListener('error', function(e) {
  // Log to error tracking service
  console.error('Error:', e.message);
});
```

## CI/CD Pipeline

### Automated Testing

Add tests before deployment:

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install bengal-ssg
      - run: bengal build
      - run: test -f public/index.html
      - run: test -f public/sitemap.xml
```

### Preview Deployments

Create preview deployments for PRs:

- **Netlify**: Automatic PR previews
- **Vercel**: Automatic PR previews
- **GitHub Pages**: Use separate branch

## Post-Deployment Verification

### Checklist

After deploying, verify:

- [ ] Homepage loads correctly
- [ ] Navigation works
- [ ] All pages are accessible
- [ ] Images load
- [ ] Styles apply correctly
- [ ] Links work
- [ ] Mobile view looks good
- [ ] Sitemap is accessible (`/sitemap.xml`)
- [ ] RSS feed works (`/feed.xml`)
- [ ] 404 page displays

### Testing Tools

**Lighthouse Audit**:
```bash
npm install -g lighthouse
lighthouse https://example.com --view
```

**Link Checker**:
```bash
npx broken-link-checker https://example.com
```

**Mobile-Friendly Test**:
- https://search.google.com/test/mobile-friendly

## Troubleshooting

### 404 Errors on Refresh

**Problem**: Pages work via navigation but fail on direct access.

**Solution**: Configure server for SPA-style routing or ensure pretty URLs are supported.

### Assets Not Loading

**Problem**: CSS/JS/images return 404.

**Solution**: 
- Check `baseurl` in config
- Verify asset_url() usage in templates
- Check file paths are correct

### Slow Build Times

**Problem**: Builds take too long in CI/CD.

**Solution**:
- Enable parallel processing
- Cache dependencies
- Use incremental builds for dev (not production)

## Rollback Strategy

### Keep Previous Builds

```bash
# Tag production builds
git tag v1.0.0
git push origin v1.0.0

# Store build artifacts
mv public public-v1.0.0
```

### Quick Rollback

Most platforms support instant rollback:
- **Netlify**: Deploy previous build from UI
- **Vercel**: Revert to previous deployment
- **GitHub Pages**: Revert commit or force push

## Best Practices Summary

### ✅ Do

- Use clean builds for production
- Enable all optimizations (minify, optimize, fingerprint)
- Set proper cache headers
- Use HTTPS everywhere
- Add security headers
- Monitor uptime and errors
- Test before deploying
- Have a rollback plan

### ❌ Don't

- Deploy with incremental builds
- Skip testing
- Forget to set baseurl
- Use HTTP in production
- Ignore security best practices
- Deploy without backups

## Learn More

- [Performance Optimization](/guides/performance-optimization/)
- [Configuration Reference](/docs/configuration-reference/)
- [SEO Best Practices](/posts/seo-best-practices/)

---

**Ready to deploy?** Choose your platform and follow the steps above. Your site will be live in minutes! 🚀

