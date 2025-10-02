# Bengal SSG - Git Setup & Repository Management Plan

**Date:** October 2, 2025  
**Status:** Planning

---

## Overview

This document outlines the git repository setup, branching strategy, commit conventions, and release workflow for Bengal SSG.

---

## 🎯 Repository Setup

### 1. Initialize Repository

```bash
cd /Users/llane/Documents/github/python/bengal
git init
git branch -M main
```

### 2. Review & Update .gitignore

Current `.gitignore` is good but let's verify it covers everything:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/
.venv/

# IDE
.vscode/
.idea/
*.swp
.swn
*.swo
*~
.cursor/  # Add this for Cursor IDE

# Bengal SSG
public/  # Build output (examples)
.bengal/  # Cache/temp files

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.mypy_cache/
.ruff_cache/

# OS
.DS_Store
Thumbs.db

# Documentation builds
docs/_build/
site/  # MkDocs output if we use it

# Temporary files
*.log
*.bak
*.tmp
.env  # Environment variables
```

### 3. Initial Commit Structure

**Commit 1:** Core implementation
```bash
git add bengal/ pyproject.toml requirements.txt setup.py
git add README.md LICENSE CONTRIBUTING.md
git commit -m "feat: initial Bengal SSG implementation

- Core object model (Site, Page, Section, Asset)
- Rendering pipeline with Jinja2
- Markdown parser
- CLI interface
- Development server with hot reload
- Configuration system (TOML/YAML)
- Post-processing (sitemap, RSS)
"
```

**Commit 2:** Documentation
```bash
git add *.md ARCHITECTURE.md
git commit -m "docs: add comprehensive documentation

- Architecture documentation
- Getting started guide
- Quick reference
- Contributing guidelines
"
```

**Commit 3:** Default theme
```bash
git add bengal/themes/
git commit -m "feat: add production-ready default theme

- Responsive design with dark/light mode
- Pagination system
- Breadcrumb navigation
- Template partials
- SEO optimization
"
```

**Commit 4:** Examples
```bash
git add examples/
git commit -m "docs: add quickstart example site"
```

---

## 📝 Commit Conventions

Use **Conventional Commits** format for clear history:

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring (no feature/fix)
- `perf`: Performance improvement
- `test`: Adding or updating tests
- `build`: Build system or dependencies
- `ci`: CI/CD changes
- `chore`: Maintenance tasks

### Examples

```bash
feat(pagination): add pagination utility class

Implemented generic Paginator class with:
- Configurable items per page
- Page range calculation
- Template context generation

Closes #42

---

fix(url): generate clean URLs without index.html

Updated url_for() to use page.url property instead of
constructing from output_path directly.

Fixes #45

---

docs(readme): update installation instructions

Added pip install instructions and quick start example.

---

refactor(site): extract taxonomy collection to separate method

Moved taxonomy logic from build() to collect_taxonomies()
for better separation of concerns.

---

test(paginator): add comprehensive pagination tests

Added tests for:
- Basic pagination
- Edge cases (empty lists, single item)
- Page range calculation
- Context generation

Coverage: 95%
```

---

## 🌿 Branching Strategy

### Main Branches

**`main`**
- Production-ready code
- Always stable
- Protected branch (no direct commits)
- Deploys to PyPI on tag

**`develop`** (optional, for larger team)
- Integration branch
- Latest development changes
- Used if team > 2 people

### Supporting Branches

**Feature branches** (`feature/<name>`)
```bash
git checkout -b feature/search-functionality
# Work on feature
git commit -m "feat(search): implement client-side search"
git push origin feature/search-functionality
# Create PR to main
```

**Bugfix branches** (`fix/<name>`)
```bash
git checkout -b fix/url-generation
# Fix bug
git commit -m "fix(url): handle None output_path"
git push origin fix/url-generation
# Create PR to main
```

**Hotfix branches** (`hotfix/<version>`)
```bash
git checkout -b hotfix/0.1.1 main
# Critical fix
git commit -m "fix: critical security patch"
# Merge to main and tag immediately
```

**Release branches** (`release/<version>`)
```bash
git checkout -b release/1.0.0
# Prepare release (update version, changelog)
git commit -m "chore: prepare v1.0.0 release"
# Merge to main and tag
```

### Branch Naming

- Use lowercase
- Use hyphens, not underscores
- Be descriptive but concise

**Good:**
- `feature/pagination-system`
- `fix/broken-links`
- `docs/api-reference`

**Bad:**
- `feature/stuff`
- `fix_something`
- `FEATURE/PAGINATION`

---

## 🏷️ Versioning & Releases

### Semantic Versioning

Follow **SemVer** (MAJOR.MINOR.PATCH):

- `MAJOR`: Breaking changes (e.g., 1.0.0 → 2.0.0)
- `MINOR`: New features, backward compatible (e.g., 1.0.0 → 1.1.0)
- `PATCH`: Bug fixes, backward compatible (e.g., 1.0.0 → 1.0.1)

### Pre-release Versions

- `0.1.0-alpha.1`: Early testing
- `0.1.0-beta.1`: Feature complete, testing
- `0.1.0-rc.1`: Release candidate

### Version Numbering Strategy

**Current:** `0.1.0` (MVP complete, not production tested)

**Path to 1.0.0:**
- `0.1.0`: Current state (Phase 2B complete)
- `0.2.0`: Performance optimization (incremental builds)
- `0.3.0`: Plugin system
- `0.4.0`: Comprehensive documentation
- `0.5.0-beta.1`: Beta testing
- `1.0.0`: First stable release

### Creating Releases

```bash
# 1. Update version in pyproject.toml
# 2. Update CHANGELOG.md
# 3. Commit changes
git commit -m "chore: bump version to 1.0.0"

# 4. Create tag
git tag -a v1.0.0 -m "Release v1.0.0

- Feature 1
- Feature 2
- Bug fix 3
"

# 5. Push tag
git push origin v1.0.0

# 6. Create GitHub release from tag
```

---

## 📋 CHANGELOG.md Format

Use **Keep a Changelog** format:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New features in development

### Changed
- Changes to existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security fixes

## [1.0.0] - 2025-11-01

### Added
- Plugin system with hook architecture
- Incremental build support
- Comprehensive documentation site

### Changed
- Improved rendering performance (3x faster)
- Better error messages

### Fixed
- URL generation for nested sections
- Memory leak in dev server

## [0.1.0] - 2025-10-02

### Added
- Initial release
- Core SSG functionality
- Default theme with pagination
- CLI tools
- Development server

[unreleased]: https://github.com/user/bengal/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/user/bengal/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/user/bengal/releases/tag/v0.1.0
```

---

## 🔒 GitHub Repository Settings

### Branch Protection (main)

- ✅ Require pull request reviews (1 approver)
- ✅ Require status checks (tests, linting)
- ✅ Require branches to be up to date
- ✅ Require signed commits (optional)
- ✅ No direct commits allowed
- ✅ No force push
- ✅ No branch deletion

### Issue Templates

Create `.github/ISSUE_TEMPLATE/`:

**bug_report.md:**
```markdown
---
name: Bug Report
about: Report a bug in Bengal SSG
title: '[BUG] '
labels: bug
---

**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce:
1. Create site with '...'
2. Run `bengal build`
3. See error

**Expected behavior**
What you expected to happen.

**Environment:**
- OS: [e.g., macOS 14.0]
- Python version: [e.g., 3.11]
- Bengal version: [e.g., 0.1.0]

**Additional context**
Any other context about the problem.
```

**feature_request.md:**
```markdown
---
name: Feature Request
about: Suggest a feature for Bengal SSG
title: '[FEATURE] '
labels: enhancement
---

**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
What you want to happen.

**Describe alternatives you've considered**
Other approaches you've thought about.

**Additional context**
Any other context or screenshots.
```

### Pull Request Template

Create `.github/pull_request_template.md`:

```markdown
## Description

Brief description of the changes.

## Type of Change

- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change
- [ ] Documentation update

## Checklist

- [ ] My code follows the style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code where necessary
- [ ] I have updated the documentation
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing tests pass locally
- [ ] I have updated the CHANGELOG.md

## Testing

How has this been tested?

## Related Issues

Closes #(issue number)
```

---

## 🤖 GitHub Actions (CI/CD)

Create `.github/workflows/`:

### test.yml

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.10', '3.11', '3.12']
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -e ".[dev]"
    
    - name: Run linters
      run: |
        ruff check .
        mypy bengal
    
    - name: Run tests
      run: |
        pytest --cov=bengal --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### publish.yml

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install build twine
    
    - name: Build package
      run: python -m build
    
    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
      run: twine upload dist/*
```

---

## 📦 Initial Setup Steps

### 1. Clean Up Before Committing

```bash
# Remove plan documents (move to completed)
mv plan/*.md plan/completed/ 2>/dev/null || true

# Remove duplicate/outdated docs at root
# Keep: README, ARCHITECTURE, LICENSE, CONTRIBUTING, QUICKSTART
# Consider consolidating others into docs/

# Remove example build outputs
rm -rf examples/quickstart/public

# Remove any Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### 2. Create Missing Files

```bash
# CHANGELOG.md
touch CHANGELOG.md

# .github files
mkdir -p .github/workflows
mkdir -p .github/ISSUE_TEMPLATE
```

### 3. Initialize Git

```bash
git init
git branch -M main
git add .
git commit -m "feat: initial Bengal SSG implementation

Complete static site generator with:
- Modular architecture (Site, Page, Section, Asset)
- Rendering pipeline with Jinja2
- Markdown parsing with extensions
- CLI interface (build, serve, clean, new)
- Development server with hot reload
- Configuration system (TOML/YAML)
- Post-processing (sitemap, RSS)
- Production-ready default theme
- Pagination system
- Taxonomy support (tags, categories)
- Comprehensive documentation

Version: 0.1.0
"
```

### 4. Create GitHub Repository

```bash
# On GitHub, create repository: bengal-ssg/bengal

git remote add origin https://github.com/bengal-ssg/bengal.git
git push -u origin main

# Create tag for v0.1.0
git tag -a v0.1.0 -m "Initial release - MVP complete"
git push origin v0.1.0
```

---

## 🔄 Ongoing Workflow

### Daily Development

```bash
# 1. Create feature branch
git checkout -b feature/incremental-builds

# 2. Work on feature, commit often
git add bengal/core/incremental.py
git commit -m "feat(build): add file change tracking"

git add tests/test_incremental.py
git commit -m "test(build): add incremental build tests"

# 3. Push branch
git push origin feature/incremental-builds

# 4. Create Pull Request on GitHub
# 5. Review and merge
```

### Before Each Commit

```bash
# Run linting
ruff check .

# Run tests
pytest

# Run type checking
mypy bengal

# If all pass, commit
git commit
```

### Release Process

```bash
# 1. Update version in pyproject.toml
# 2. Update CHANGELOG.md
# 3. Commit and tag
git commit -m "chore: release v0.2.0"
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin main --tags

# 4. Create GitHub release
# 5. PyPI publish happens automatically via GitHub Action
```

---

## 🎯 Git Best Practices

### Do's ✅

- Write clear, descriptive commit messages
- Commit often, push at least daily
- Keep commits atomic (one logical change per commit)
- Use branches for features/fixes
- Review your own diff before pushing
- Keep main branch always deployable
- Tag releases
- Update CHANGELOG

### Don'ts ❌

- Don't commit large binary files
- Don't commit secrets/credentials
- Don't commit generated files (public/, __pycache__)
- Don't force push to main
- Don't commit commented-out code
- Don't commit "TODO" or "WIP" to main
- Don't commit without testing

---

## 📊 Repository Health Metrics

Track these in README badges:

- Build status (GitHub Actions)
- Test coverage (Codecov)
- PyPI version
- Python version support
- License
- Downloads
- Contributors

```markdown
[![Tests](https://github.com/bengal-ssg/bengal/workflows/Tests/badge.svg)](https://github.com/bengal-ssg/bengal/actions)
[![Coverage](https://codecov.io/gh/bengal-ssg/bengal/branch/main/graph/badge.svg)](https://codecov.io/gh/bengal-ssg/bengal)
[![PyPI](https://img.shields.io/pypi/v/bengal-ssg.svg)](https://pypi.org/project/bengal-ssg/)
[![Python](https://img.shields.io/pypi/pyversions/bengal-ssg.svg)](https://pypi.org/project/bengal-ssg/)
[![License](https://img.shields.io/github/license/bengal-ssg/bengal.svg)](LICENSE)
```

---

## ✅ Checklist

Before initializing git:
- [ ] Review .gitignore is complete
- [ ] Remove build outputs (public/, __pycache__)
- [ ] Create CHANGELOG.md
- [ ] Create .github templates
- [ ] Update README with badges
- [ ] Consolidate documentation
- [ ] Set version to 0.1.0 in pyproject.toml

After initializing:
- [ ] Create GitHub repository
- [ ] Set up branch protection
- [ ] Add issue/PR templates
- [ ] Set up GitHub Actions
- [ ] Create initial release (v0.1.0)
- [ ] Consider setting up Codecov

---

**Ready to initialize? See TEST_STRATEGY.md for test planning first!**

