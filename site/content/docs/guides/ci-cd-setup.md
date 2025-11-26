---
title: Set Up CI/CD
description: Set up automated builds, testing, and deployments using GitHub Actions, GitLab CI, and other platforms
weight: 40
draft: false
lang: en
tags: [ci-cd, deployment, automation, github-actions, gitlab-ci]
keywords: [ci-cd, continuous integration, deployment, github actions, gitlab ci, automation]
category: guide
---

# Set Up CI/CD

Set up continuous integration and deployment (CI/CD) for your Bengal site. Automate builds, run tests, and deploy to production with GitHub Actions, GitLab CI, or other platforms.

## When to Use This Guide

- You want automated builds on every commit
- You need to run tests before deployment
- You want to deploy to production automatically
- You're setting up preview deployments for pull requests
- You need to validate content and links before publishing

## Prerequisites

- [Bengal installed](/docs/getting-started/installation/)
- A Git repository (GitHub, GitLab, etc.)
- A hosting provider account (Netlify, Vercel, GitHub Pages, etc.)
- Basic knowledge of YAML and CI/CD concepts

## Step 1: GitHub Actions Setup

### Basic Build Workflow

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
        run: bengal site build --environment production --strict

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: site
          path: public/
          retention-days: 1
```

### Production Deployment

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
        run: bengal site build --environment production --strict --clean

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

### Preview Deployments

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
        run: bengal site build --environment preview --build-drafts

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

## Step 2: GitLab CI Setup

### Basic Pipeline

Create `.gitlab-ci.yml`:

```yaml
image: python:3.14

stages:
  - build
  - test
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip

build:
  stage: build
  script:
    - pip install bengal
    - bengal site build --environment production --strict
  artifacts:
    paths:
      - public/
    expire_in: 1 hour

test:
  stage: test
  script:
    - pip install bengal
    - bengal health check
    - bengal site build --strict
  only:
    - merge_requests
    - main

deploy:
  stage: deploy
  script:
    - echo "Deploy to production"
    # Add your deployment commands here
  only:
    - main
  when: manual
```

### GitLab Pages Deployment

```yaml
pages:
  stage: deploy
  script:
    - pip install bengal
    - bengal site build --environment production --strict
  artifacts:
    paths:
      - public
  only:
    - main
```

## Step 3: Netlify Setup

### Netlify Configuration

Create `netlify.toml`:

```toml
[build]
  publish = "public"
  command = "pip install bengal && bengal site build --environment production --strict"

[build.environment]
  PYTHON_VERSION = "3.14"

[[plugins]]
  package = "@netlify/plugin-lighthouse"

[context.production.environment]
  NODE_ENV = "production"

[context.deploy-preview.environment]
  NODE_ENV = "preview"
```

### Build Settings in Netlify Dashboard

1. Go to Site settings → Build & deploy
2. Set build command: `pip install bengal && bengal site build --environment production`
3. Set publish directory: `public`
4. Set Python version: `3.14`

## Step 4: Vercel Setup

### Vercel Configuration

Create `vercel.json`:

```json
{
  "buildCommand": "pip install bengal && bengal site build --environment production",
  "outputDirectory": "public",
  "installCommand": "pip install bengal",
  "framework": null,
  "env": {
    "PYTHON_VERSION": "3.14"
  }
}
```

### Vercel Build Settings

1. Go to Project Settings → General
2. Set Framework Preset: Other
3. Set Build Command: `pip install bengal && bengal site build --environment production`
4. Set Output Directory: `public`
5. Set Install Command: `pip install bengal`

## Step 5: Add Testing and Validation

### Health Checks

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
        run: bengal config validate

      - name: Check for broken links
        run: bengal health check

      - name: Build with strict mode
        run: bengal site build --strict --verbose
```

### Content Validation

```yaml
- name: Validate content
  run: |
    # Check for missing frontmatter
    python scripts/validate-content.py

    # Check for broken internal links
    bengal health check --check-links
```

**`scripts/validate-content.py`:**
```python
#!/usr/bin/env python3
"""Validate content files."""

import sys
from pathlib import Path
import frontmatter

errors = []

for md_file in Path("content").rglob("*.md"):
    try:
        post = frontmatter.load(md_file)

        # Check required fields
        if not post.get("title"):
            errors.append(f"{md_file}: Missing 'title' field")

        # Validate date format
        if post.get("date"):
            from datetime import datetime
            date = post["date"]
            if isinstance(date, str):
                try:
                    datetime.fromisoformat(date.replace("Z", "+00:00"))
                except ValueError:
                    errors.append(f"{md_file}: Invalid date format")

    except Exception as e:
        errors.append(f"{md_file}: {e}")

if errors:
    print("\n".join(errors))
    sys.exit(1)

print("✅ All content files valid")
```

## Step 6: Environment-Specific Builds

### Environment Configuration

Create environment-specific configs:

**`config/environments/production.yaml`:**
```yaml
site:
  baseurl: "https://example.com"

params:
  analytics_id: "{{ env.GA_ID }}"
  api_key: "{{ env.API_KEY }}"
```

**`config/environments/preview.yaml`:**
```yaml
site:
  baseurl: "https://preview.example.com"

params:
  analytics_id: ""  # Disable analytics in preview
```

### CI/CD Environment Variables

Set in your CI/CD platform:

**GitHub Actions:**
```yaml
env:
  GA_ID: ${{ secrets.GA_ID }}
  API_KEY: ${{ secrets.API_KEY }}
```

**GitLab CI:**
```yaml
variables:
  GA_ID: $GA_ID
  API_KEY: $API_KEY
```

**Netlify:**
- Go to Site settings → Environment variables
- Add `GA_ID` and `API_KEY`

## Step 7: Caching for Faster Builds

### GitHub Actions Caching

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

### GitLab CI Caching

```yaml
cache:
  paths:
    - .cache/pip
    - .bengal-cache
  key: ${CI_COMMIT_REF_SLUG}
```

## Step 8: Deployment Strategies

### Manual Deployment

Deploy only when manually triggered:

```yaml
deploy:
  runs-on: ubuntu-latest
  needs: build
  steps:
    - name: Deploy
      run: |
        # Your deployment commands
  environment:
    name: production
  if: github.event_name == 'workflow_dispatch'
```

### Automatic Deployment

Deploy on push to main:

```yaml
deploy:
  runs-on: ubuntu-latest
  needs: build
  steps:
    - name: Deploy
      run: |
        # Your deployment commands
  if: github.ref == 'refs/heads/main'
```

### Staged Deployment

Deploy to staging, then production:

```yaml
deploy-staging:
  # Deploy to staging
  if: github.ref == 'refs/heads/develop'

deploy-production:
  # Deploy to production
  if: github.ref == 'refs/heads/main'
  needs: [build, deploy-staging]
```

## Step 9: Notification and Monitoring

### Slack Notifications

```yaml
- name: Notify Slack
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK }}
    payload: |
      {
        "text": "Build failed: ${{ github.workflow }}",
        "blocks": [{
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": "Build failed: <${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|View workflow>"
          }
        }]
      }
```

### Email Notifications

Most CI/CD platforms send email notifications by default for failed builds.

## Troubleshooting

### Build Failures

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

### Deployment Issues

**Issue:** Files not deploying

**Solutions:**
- Verify output directory: `public/`
- Check build artifacts are uploaded
- Verify deployment permissions

**Issue:** Environment variables not working

**Solutions:**
- Check variable names match config
- Verify secrets are set in CI/CD platform
- Check environment variable syntax: `{{ env.VAR_NAME }}`

## Next Steps

- **[Deployment Guide](/docs/guides/deployment/)** - Learn deployment options
- **[Content Workflow](/docs/guides/content-workflow/)** - Set up content publishing workflow
- **[Multi-Environment Setup](/docs/guides/multi-environment/)** - Manage dev/staging/production
