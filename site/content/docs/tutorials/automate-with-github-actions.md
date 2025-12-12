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
Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

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
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'

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
:::{/step}

:::{step} Preview Deployments
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

      - name: Install Bengal
        run: pip install bengal

      - name: Build site
        run: bengal build --environment preview --build-drafts

      - name: Comment PR with preview
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '✅ Preview build successful! Artifacts available in workflow run.'
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
Add caching to speed up workflows:

```yaml
- name: Cache pip packages
  uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-

- name: Cache Bengal build cache
  uses: actions/cache@v4
  with:
    path: .bengal-cache
    key: ${{ runner.os }}-bengal-${{ github.sha }}
    restore-keys: |
      ${{ runner.os }}-bengal-
```
:::{/step}

:::{step} Environment-Specific Builds
**Create Environment Configs**

**`config/environments/production.yaml`:**
```yaml
site:
  baseurl: "https://example.com"

params:
  analytics_id: "{{ env.GA_ID }}"
```

**`config/environments/preview.yaml`:**
```yaml
site:
  baseurl: "https://preview.example.com"

params:
  analytics_id: ""  # Disable analytics in preview
```

**Use Environment Variables**

```yaml
env:
  GA_ID: ${{ secrets.GA_ID }}
  API_KEY: ${{ secrets.API_KEY }}
```
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

**Issue:** Build fails with "Command not found: bengal"

**Solutions:**
- Ensure Python 3.14+ is installed
- Check `pip install bengal` runs before build
- Verify Python path in CI environment

**Issue:** Build fails with strict mode errors

**Solutions:**
- Fix broken links: `bengal health check`
- Fix template errors
- Remove `--strict` flag temporarily to identify issues
:::

:::{dropdown} Deployment Issues
:icon: alert

**Issue:** Files not deploying

**Solutions:**
- Verify output directory: `public/`
- Check build artifacts are uploaded
- Verify deployment permissions
:::

## Next Steps

- **[Deployment Options](/docs/building/deployment/)** - Explore other hosting platforms
- **[Configuration](/docs/building/configuration/)** - Environment-specific settings
- **[Validation](/docs/extending/validation/)** - Set up health checks
