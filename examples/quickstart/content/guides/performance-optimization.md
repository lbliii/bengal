---
title: "Performance Optimization Guide"
date: 2025-10-03
tags: ["performance", "optimization", "speed"]
categories: ["Guides", "Performance"]
type: "guide"
description: "Maximize your Bengal site's speed with these optimization techniques"
author: "Bengal Documentation Team"
---

# Performance Optimization Guide

Maximize your Bengal site's speed and deliver the best possible user experience with these optimization techniques.

## Build Performance

### Enable Incremental Builds

For development, use incremental builds for 18-42x faster rebuilds:

```toml
[build]
incremental = true
```

```bash
bengal build --incremental --verbose
```

**Impact**: Single-file changes build in ~0.012s vs 0.223s (18x faster).

See: [Incremental Builds Guide](/docs/incremental-builds/)

### Enable Parallel Processing

Use all CPU cores for 2-4x faster builds:

```toml
[build]
parallel = true
max_workers = 0  # Auto-detect cores
```

**Impact**: 100-page sites build in 1.66s vs 2.45s (1.5x faster).

See: [Parallel Processing Guide](/docs/parallel-processing/)

### Optimize Asset Pipeline

```toml
[assets]
minify = true        # Reduce CSS/JS file sizes
optimize = true      # Compress images
fingerprint = true   # Enable cache busting
```

**Impact**:
- CSS minification: 30-50% size reduction
- JS minification: 20-40% size reduction
- Image optimization: 20-60% size reduction

## Content Optimization

### Optimize Images

#### Before Upload

Use tools to compress images:

```bash
# Install ImageMagick
brew install imagemagick  # macOS
apt install imagemagick   # Linux

# Optimize JPEG (quality 85)
convert input.jpg -quality 85 output.jpg

# Optimize PNG
pngquant input.png --output output.png

# Convert to WebP
cwebp -q 85 input.jpg -o output.webp
```

#### Image Sizing

Use appropriate image dimensions:

| Use Case | Max Width | Quality |
|----------|-----------|---------|
| Hero images | 1920px | 85% |
| Content images | 1200px | 85% |
| Thumbnails | 400px | 80% |
| Icons | 200px | 90% |

#### Responsive Images

Use picture elements for art direction:

```html
<picture>
  <source media="(max-width: 768px)" srcset="/images/mobile.jpg">
  <source media="(max-width: 1200px)" srcset="/images/tablet.jpg">
  <img src="/images/desktop.jpg" alt="Description">
</picture>
```

### Minimize Content

#### Reduce Page Weight

- Keep pages under 1MB total
- Limit images per page
- Use SVG for icons and logos
- Lazy-load below-fold images

#### Lazy Loading

```html
<img src="/images/photo.jpg" loading="lazy" alt="Description">
```

### Optimize Fonts

#### System Fonts

Use system font stack (no downloads):

```css
font-family: -apple-system, BlinkMacSystemFont, 
  "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
```

#### Web Fonts

If using web fonts:

1. **Subset fonts** to only needed characters
2. **Use WOFF2** format (best compression)
3. **Preload critical fonts**:

```html
<link rel="preload" href="/fonts/font.woff2" as="font" type="font/woff2" crossorigin>
```

4. **Use font-display**:

```css
@font-face {
  font-family: 'MyFont';
  src: url('/fonts/font.woff2') format('woff2');
  font-display: swap;  /* Show fallback while loading */
}
```

## CSS Optimization

### Minification

Enable automatic minification:

```toml
[assets]
minify = true
```

### Critical CSS

Inline critical CSS for above-the-fold content:

```html
<style>
  /* Critical styles for initial render */
  .header { ... }
  .hero { ... }
</style>
```

Load non-critical CSS asynchronously:

```html
<link rel="preload" href="/css/non-critical.css" as="style" onload="this.onload=null;this.rel='stylesheet'">
```

### Remove Unused CSS

Use PurgeCSS to remove unused styles:

```bash
npm install -g purgecss

purgecss --css public/assets/css/*.css \
  --content public/**/*.html \
  --output public/assets/css/
```

### CSS Performance Tips

- Avoid expensive selectors (deep nesting)
- Use CSS containment for isolated components
- Minimize use of shadows and gradients
- Use transform and opacity for animations (GPU-accelerated)

## JavaScript Optimization

### Minification

Bengal automatically minifies JavaScript when enabled:

```toml
[assets]
minify = true
```

### Defer Non-Critical Scripts

```html
<!-- Defer parsing -->
<script defer src="/js/non-critical.js"></script>

<!-- Load asynchronously -->
<script async src="/js/analytics.js"></script>
```

### Code Splitting

Split large scripts into smaller chunks:

```
js/
├── main.js          # Core functionality
├── blog.js          # Blog-specific code
└── docs.js          # Docs-specific code
```

Load only what's needed per page.

### Reduce JavaScript Dependencies

- Use vanilla JS instead of jQuery when possible
- Avoid heavy frameworks for static sites
- Remove unused libraries

## Caching Strategy

### Cache Headers

Configure appropriate cache durations:

```
# _headers (Netlify/Cloudflare Pages)
/
  Cache-Control: public, max-age=3600, must-revalidate

/assets/*
  Cache-Control: public, max-age=31536000, immutable

/*.html
  Cache-Control: public, max-age=0, must-revalidate
```

### Service Workers

Implement offline support and advanced caching:

```javascript
// sw.js
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('v1').then((cache) => {
      return cache.addAll([
        '/',
        '/css/styles.css',
        '/js/app.js',
      ]);
    })
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
```

Register in HTML:

```html
<script>
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js');
  }
</script>
```

## CDN Configuration

### Use a CDN

Serve assets from a CDN for global performance:

- **Cloudflare**: Free tier available
- **AWS CloudFront**: Pay-per-use
- **Netlify/Vercel**: Built-in CDN

### Edge Caching

Configure edge caching for maximum performance:

```
Cache-Control: public, max-age=31536000, immutable, s-maxage=31536000
```

## HTML Optimization

### Semantic HTML

Use semantic elements for better parsing:

```html
<header>, <nav>, <main>, <article>, <aside>, <footer>
```

### Minimize DOM Depth

Keep DOM tree shallow (< 32 nodes deep, < 60 children per parent).

### Avoid Inline Styles

Use classes instead of inline styles for better cacheability.

### Preconnect to External Domains

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="dns-prefetch" href="https://analytics.example.com">
```

## Performance Monitoring

### Lighthouse

Audit your site:

```bash
npm install -g lighthouse
lighthouse https://example.com --view
```

Target scores:
- Performance: > 90
- Accessibility: > 90
- Best Practices: 100
- SEO: 100

### Web Vitals

Monitor Core Web Vitals:

| Metric | Target | Description |
|--------|--------|-------------|
| LCP | < 2.5s | Largest Contentful Paint |
| FID | < 100ms | First Input Delay |
| CLS | < 0.1 | Cumulative Layout Shift |

### Performance API

Track real user metrics:

```javascript
// Track page load time
window.addEventListener('load', () => {
  const perfData = window.performance.timing;
  const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
  console.log('Page load time:', pageLoadTime, 'ms');
});

// Track Largest Contentful Paint
new PerformanceObserver((list) => {
  const entries = list.getEntries();
  const lastEntry = entries[entries.length - 1];
  console.log('LCP:', lastEntry.renderTime || lastEntry.loadTime);
}).observe({ entryTypes: ['largest-contentful-paint'] });
```

## Build-Time Optimizations

### Template Optimization

- Keep templates simple
- Avoid complex logic in templates
- Use partials for reusable components
- Minimize nested includes

### Content Organization

- Use sections for better organization
- Limit posts per page (pagination)
- Break large pages into smaller pages

### Configuration Tuning

```toml
[build]
parallel = true
max_workers = 0  # Auto-detect (usually optimal)

[pagination]
items_per_page = 10  # Balance page count vs page size
```

## Network Optimization

### HTTP/2 or HTTP/3

Ensure your hosting supports HTTP/2 or HTTP/3:
- Multiplexing (multiple requests in one connection)
- Server push (proactive resource sending)
- Header compression

### Compress Responses

Enable compression (automatic on most platforms):
- Gzip (widely supported)
- Brotli (better compression, modern browsers)

### Reduce Requests

- Combine CSS files
- Combine JS files
- Use CSS sprites for icons (or SVG sprites)
- Inline critical resources

## Mobile Optimization

### Responsive Design

Use mobile-first approach:

```css
/* Mobile first */
.container {
  padding: 1rem;
}

/* Tablet and up */
@media (min-width: 768px) {
  .container {
    padding: 2rem;
  }
}

/* Desktop */
@media (min-width: 1024px) {
  .container {
    padding: 3rem;
  }
}
```

### Touch Targets

Ensure touch targets are at least 44×44 pixels:

```css
button, a {
  min-width: 44px;
  min-height: 44px;
  padding: 0.75rem 1.5rem;
}
```

### Viewport Meta Tag

```html
<meta name="viewport" content="width=device-width, initial-scale=1">
```

## SEO Performance

### Sitemaps

Enable automatic sitemap generation:

```toml
[features]
generate_sitemap = true
```

Submit to search engines:
- Google Search Console
- Bing Webmaster Tools

### Structured Data

Add JSON-LD structured data:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "{{ '{{ page.title }}' }}",
  "datePublished": "{{ '{{ page.date | dateformat' }}('%Y-%m-%d') }}",
  "author": {
    "@type": "Person",
    "name": "{{ '{{ page.metadata.author }}' }}"
  }
}
</script>
```

## Performance Checklist

### Pre-Launch

- [ ] Enable minification
- [ ] Optimize all images
- [ ] Configure cache headers
- [ ] Test on slow connections
- [ ] Run Lighthouse audit
- [ ] Verify mobile performance
- [ ] Check Core Web Vitals

### Post-Launch

- [ ] Monitor real user metrics
- [ ] Track Core Web Vitals
- [ ] Review analytics
- [ ] Optimize slow pages
- [ ] Update cache strategy

## Tools and Resources

### Testing Tools

- **Lighthouse**: Chrome DevTools
- **PageSpeed Insights**: https://pagespeed.web.dev/
- **WebPageTest**: https://www.webpagetest.org/
- **GTmetrix**: https://gtmetrix.com/

### Image Optimization

- **Squoosh**: https://squoosh.app/
- **TinyPNG**: https://tinypng.com/
- **ImageOptim**: https://imageoptim.com/ (macOS)

### Performance Monitoring

- **Google Analytics**: Real user monitoring
- **New Relic**: Detailed performance metrics
- **Cloudflare Analytics**: CDN-level insights

## Quick Wins

### Immediate Improvements

1. **Enable asset optimization** (`minify = true, optimize = true`)
2. **Add lazy loading** to images
3. **Use system fonts** or optimize web fonts
4. **Enable compression** (usually automatic)
5. **Set proper cache headers**

**Expected impact**: 20-40% improvement in load time

## Learn More

- [Incremental Builds](/docs/incremental-builds/) - Build faster
- [Parallel Processing](/docs/parallel-processing/) - Use all cores
- [Deployment Best Practices](/guides/deployment-best-practices/) - Deploy optimally
- [Web.dev Performance](https://web.dev/performance/) - Google's guide

---

**Start optimizing today!** Even small improvements compound to significant performance gains. 🚀

