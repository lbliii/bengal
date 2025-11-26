---
title: Deploy Your Site
description: Build and deploy your Bengal site to production
weight: 40
draft: false
lang: en
tags: [deployment, production, hosting]
keywords: [deployment, production, hosting, netlify, vercel, github pages]
category: guide
---

Bengal generates static HTML, CSS, and JavaScript files. This means you can host your site anywhere that serves static files (e.g., GitHub Pages, Netlify, Vercel, AWS S3, Nginx).

## 1. The Production Build

When you are ready to ship, run the build command.

```bash
bengal build --environment production
```

This command:

:::{checklist}
- Loads configuration from `config/environments/production.yaml` (if it exists)
- Minifies assets (if enabled)
:::
- Generates the `public/` directory with your complete site
```

### Common Build Flags

| Flag | Description | Use Case |
| :--- | :--- | :--- |
| `--environment production` | Loads production config overrides. | **Always use for shipping.** |
| `--strict` | Fails the build on warnings (e.g., broken links). | **Highly Recommended for CI/CD.** |
| `--clean` | Cleans the `public/` directory before building. | Recommended to avoid stale files. |
| `--verbose` | Shows detailed logs. | Useful for debugging CI failures. |

Example full command for CI:
```bash
bengal build --environment production --strict --clean
```

## 2. Hosting Providers

### GitHub Pages

You can deploy using GitHub Actions. Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Install Bengal
        run: pip install bengal

      - name: Build Site
        run: bengal build --environment production --strict

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: './public'

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

### Netlify

Create a `netlify.toml` in your repository root:

```toml
[build]
  publish = "public"
  command = "bengal build --environment production"

[build.environment]
  PYTHON_VERSION = "3.14"
```

### Vercel

1.  **Build Command**: `bengal build --environment production`
2.  **Output Directory**: `public`
3.  Ensure your `requirements.txt` includes `bengal`.

## 3. Environment Variables

Bengal allows you to inject environment variables into your configuration using `{{ env.VAR_NAME }}` syntax in your YAML/TOML config files.

**config/environments/production.yaml**:
```yaml
params:
  api_key: "{{ env.API_KEY }}"
  analytics_id: "{{ env.ANALYTICS_ID }}"
```

Then set `API_KEY` and `ANALYTICS_ID` in your hosting provider's dashboard.

## 4. Pre-Deployment Checklist

Before you merge to main or deploy:

1.  **Run `bengal doctor`**: Checks for common configuration issues.
2.  **Run `bengal build --strict` locally**: Ensures no broken links or missing templates.
3.  **Check `config/environments/production.yaml`**: Ensure your `baseurl` is set to your production domain (e.g., `https://mysite.com`).

```yaml
# config/environments/production.yaml
site:
  baseurl: "https://example.com"
```
