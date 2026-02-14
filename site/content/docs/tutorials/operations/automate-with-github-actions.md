---
title: Automate with GitHub Actions
nav_title: GitHub Actions
description: Set up automated builds, testing, and deployments using GitHub Actions
weight: 30
draft: false
lang: en
tags:
- tutorial
- ci-cd
- automation
- github-actions
keywords:
- ci-cd
- continuous integration
- deployment
- github actions
- automation
category: tutorial
---

# Automate with GitHub Actions

Set up continuous integration and deployment (CI/CD) for your Bengal site. Automate builds, run tests, and deploy to production with GitHub Actions.

## When to Use This Guide

- You want automated builds on every commit
- You need to run tests before deployment
- You want to deploy to production automatically
- You're setting up preview deployments for pull requests
- You need to validate content and links before publishing

## Prerequisites

- [Bengal installed](/docs/get-started/installation/)
- A Git repository on GitHub
- A hosting provider account (GitHub Pages, Netlify, Vercel, etc.)
- Basic knowledge of YAML

:::tip Performance Tip
For faster CI builds, use Python 3.14t (free-threading build) instead of 3.14. This enables true parallel processing and can reduce build times by 1.5-2x on multi-core runners. Update `python-version: '3.14t'` in your workflows.
:::

## Steps

:::{steps}
:::{step} Basic Build Workflow
Create `.github/workflows/build.yml`:

```yaml
name: Build Site

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Install Bengal
        run: pip install bengal

      - name: Build site
        run: bengal build --environment production --strict

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: site
          path: public/
          retention-days: 1
```

:::{/step}

:::{step} Deploy to GitHub Pages

Automatically deploys to GitHub Pages when you push to `main`. Requires GitHub Pages enabled in repository settings.

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

# Required permissions for GitHub Pages deployment
permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'
          cache: 'pip'

      - name: Install Bengal
        run: pip install bengal

      - name: Build site
        run: bengal build --environment production --strict --clean-output

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v4
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

**Note:** Enable GitHub Pages in your repository settings: **Settings** > **Pages** > **Source**: GitHub Actions.
:::{/step}

:::{step} Preview Deployments

Builds preview versions for pull requests. Comments on PRs when build succeeds. Artifacts available in workflow run.

Create `.github/workflows/preview.yml`:

```yaml
name: Preview Deployment

on:
  pull_request:
    branches: [main]

jobs:
  preview:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'
          cache: 'pip'

      - name: Install Bengal
        run: pip install bengal

      - name: Build site
        run: bengal build --environment preview

      - name: Upload preview artifacts
        uses: actions/upload-artifact@v4
        with:
          name: preview-site
          path: public/
          retention-days: 7

      - name: Comment PR with preview
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '✅ Preview build successful! Download artifacts from workflow run.'
            })
```

:::{/step}

:::{step} Add Validation and Testing
Add health checks to your CI pipeline:

```yaml
# .github/workflows/test.yml
name: Test and Validate

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Install Bengal
        run: pip install bengal

      - name: Validate configuration
        run: bengal config doctor

      - name: Check for broken links
        run: bengal health linkcheck

      - name: Build with strict mode
        run: bengal build --strict --verbose
```

:::{/step}

:::{step} Caching for Faster Builds

Cache dependencies and build artifacts to reduce workflow time. Add these steps after Python setup:

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.14'
    cache: 'pip'  # Automatically caches pip packages

- name: Cache Bengal build cache
  uses: actions/cache@v4
  with:
    path: .bengal-cache
    key: ${{ runner.os }}-bengal-${{ github.sha }}
    restore-keys: |
      ${{ runner.os }}-bengal-
```

**Note:** Python setup with `cache: 'pip'` automatically caches pip packages. Only add Bengal cache if you use incremental builds.
:::{/step}

:::{step} Environment-Specific Builds

Use different configurations for production and preview builds. Store secrets in GitHub repository settings.

**1. Create environment configs:**

`config/environments/production.yaml`:

```yaml
site:
  baseurl: "https://example.com"

params:
  analytics_id: "{{ env.GA_ID }}"
```

`config/environments/preview.yaml`:

```yaml
site:
  baseurl: "https://preview.example.com"

params:
  analytics_id: ""  # Disable analytics in preview
```

**2. Add environment variables to workflow:**

```yaml
env:
  GA_ID: ${{ secrets.GA_ID }}
  API_KEY: ${{ secrets.API_KEY }}

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      # ... other steps ...
      - name: Build site
        run: bengal build --environment production
```

**3. Set secrets in GitHub:** **Settings** > **Secrets and variables** > **Actions** > **New repository secret**
:::{/step}

:::{step} Multi-Variant Builds (OSS vs Enterprise)

Build separate doc sites from one repo. Use `params.edition` and page frontmatter `edition` to filter content.

```yaml
jobs:
  build:
    strategy:
      matrix:
        edition: [oss, enterprise]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'
          cache: 'pip'

      - name: Install Bengal
        run: pip install bengal

      - name: Build ${{ matrix.edition }} site
        run: bengal build --environment ${{ matrix.edition }} --strict --clean-output

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: site-${{ matrix.edition }}
          path: public/
```

Ensure `config/environments/oss.yaml` and `config/environments/enterprise.yaml` set `params.edition` accordingly. See [Multi-Variant Builds](/docs/building/configuration/variants) for full setup.
:::{/step}
:::{/steps}

## Alternative Platforms

### GitLab CI

Create `.gitlab-ci.yml`:

```yaml
image: python:3.14

stages:
  - build
  - deploy

build:
  stage: build
  script:
    - pip install bengal
    - bengal build --environment production --strict
  artifacts:
    paths:
      - public/

pages:
  stage: deploy
  script:
    - pip install bengal
    - bengal build --environment production --strict
  artifacts:
    paths:
      - public
  only:
    - main
```

### Netlify

Create `netlify.toml`:

```toml
[build]
  publish = "public"
  command = "pip install bengal && bengal build --environment production --strict"

[build.environment]
  PYTHON_VERSION = "3.14"
```

### Vercel

Create `vercel.json`:

```json
{
  "buildCommand": "pip install bengal && bengal build --environment production",
  "outputDirectory": "public",
  "installCommand": "pip install bengal"
}
```

## Troubleshooting

:::{dropdown} Build Failures
:icon: alert

**Issue:** `Command not found: bengal`

**Solutions:**

- Verify Python 3.14+ is installed: `python-version: '3.14'`
- Ensure `pip install bengal` runs before build step
- Check Python path: Add `which python` step for debugging

**Issue:** Build fails with strict mode errors

**Solutions:**

- Check configuration: `bengal config doctor`
- Fix broken links: `bengal health linkcheck`
- Fix template errors: Check build logs for specific errors
- Temporarily remove `--strict` to identify issues: `bengal build --verbose`

**Issue:** Build succeeds locally but fails in CI

**Solutions:**

- Check environment variables are set in GitHub secrets
- Verify file paths match CI working directory
- Review build logs for missing dependencies
:::

:::{dropdown} Deployment Issues
:icon: alert

**Issue:** Files not deploying to GitHub Pages

**Solutions:**

- Verify output directory: `path: './public'` matches your build output
- Check build artifacts uploaded: View workflow run artifacts
- Verify permissions: Ensure `pages: write` permission is set
- Enable GitHub Pages: **Settings** > **Pages** > **Source**: GitHub Actions

**Issue:** Preview builds not working

**Solutions:**

- Check PR comments for errors
- Verify `actions/github-script@v7` has write permissions
- Review workflow logs for authentication errors
:::

## Next Steps

- **[Deployment Options](/docs/building/deployment/)** — Explore other hosting platforms
- **[Configuration](/docs/building/configuration/)** — Environment-specific settings
- **[Health Checks](/docs/content/validation/)** — Set up content validation
- **[Graph Analysis](/docs/tutorials/operations/analyze-site-connectivity/)** — Add connectivity checks to CI
