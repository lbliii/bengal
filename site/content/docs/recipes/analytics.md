---
title: Add Analytics
description: Add privacy-friendly analytics to your Bengal site
weight: 20
type: doc
tags: [recipe, analytics, tracking]
---

# Add Analytics

Add visitor analytics to your site in 5 minutes. Choose from Google Analytics, Plausible, or Fathom.

## Goal

After this recipe, you'll have:

- Visitor tracking on all pages
- Page view and traffic source data
- Privacy-compliant implementation

## Prerequisites

- A working Bengal site
- An analytics account (Google Analytics, Plausible, or Fathom)

## Choose Your Provider

::::{tab-set}

:::{tab-item} Plausible (Recommended)
**Privacy-friendly, no cookies, GDPR compliant out of the box.**

### 1. Get Your Script

Sign up at [plausible.io](https://plausible.io) and get your tracking script.

### 2. Create Analytics Partial

Create `templates/partials/analytics.html`:

```html
{% if site.config.analytics.plausible %}
<script
  defer
  data-domain="{{ site.config.analytics.plausible }}"
  src="https://plausible.io/js/script.js">
</script>
{% endif %}
```

### 3. Add to Base Template

In `templates/base.html`, add before `</head>`:

```jinja2
{% include "partials/analytics.html" %}
```

### 4. Configure

In `bengal.toml`:

```toml
[analytics]
plausible = "yourdomain.com"
```
:::

:::{tab-item} Fathom
**Privacy-focused, simple analytics.**

### 1. Get Your Site ID

Sign up at [usefathom.com](https://usefathom.com) and get your site ID.

### 2. Create Analytics Partial

Create `templates/partials/analytics.html`:

```html
{% if site.config.analytics.fathom %}
<script
  src="https://cdn.usefathom.com/script.js"
  data-site="{{ site.config.analytics.fathom }}"
  defer>
</script>
{% endif %}
```

### 3. Add to Base Template

In `templates/base.html`, add before `</head>`:

```jinja2
{% include "partials/analytics.html" %}
```

### 4. Configure

In `bengal.toml`:

```toml
[analytics]
fathom = "ABCDEFGH"  # Your Fathom site ID
```
:::

:::{tab-item} Google Analytics
**Full-featured, free, requires cookie consent for GDPR.**

### 1. Get Your Measurement ID

Go to [Google Analytics](https://analytics.google.com) and create a GA4 property. Copy the Measurement ID (starts with `G-`).

### 2. Create Analytics Partial

Create `templates/partials/analytics.html`:

```html
{% if site.config.analytics.google %}
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={{ site.config.analytics.google }}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', '{{ site.config.analytics.google }}');
</script>
{% endif %}
```

### 3. Add to Base Template

In `templates/base.html`, add before `</head>`:

```jinja2
{% include "partials/analytics.html" %}
```

### 4. Configure

In `bengal.toml`:

```toml
[analytics]
google = "G-XXXXXXXXXX"  # Your GA4 Measurement ID
```

:::{warning}
Google Analytics requires cookie consent in the EU. Consider using a cookie consent banner or switching to Plausible/Fathom for simpler compliance.
:::
:::

::::

## Done

Build and deploy your site. Visit a few pages, then check your analytics dashboard. Data typically appears within a few minutes.

## Environment-Specific Analytics

To disable analytics in development:

### Option 1: Check Environment

```html
{% if site.config.analytics.plausible and site.config.environment == 'production' %}
<script defer data-domain="{{ site.config.analytics.plausible }}" src="https://plausible.io/js/script.js"></script>
{% endif %}
```

### Option 2: Use Environment Config

Create `config/environments/local.yaml`:

```yaml
analytics:
  plausible: null  # Disabled locally
```

And `config/environments/production.yaml`:

```yaml
analytics:
  plausible: "yourdomain.com"
```

## Verifying Installation

### Plausible/Fathom
- Open browser DevTools → Network tab
- Look for requests to `plausible.io` or `usefathom.com`
- Check your dashboard for real-time visitors

### Google Analytics
- Use [Google Tag Assistant](https://tagassistant.google.com/)
- Or check DevTools for `gtag` function and `googletagmanager.com` requests

## See Also

- [Plausible Documentation](https://plausible.io/docs)
- [Fathom Documentation](https://usefathom.com/docs)
- [Google Analytics Setup](https://support.google.com/analytics/answer/9304153)
- [Configuration Reference](/docs/reference/architecture/tooling/config/)
