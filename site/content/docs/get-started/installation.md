---
title: Install Bengal
description: Install Bengal using pip, uv, or from source
weight: 10
type: doc
draft: false
lang: en
tags: [onboarding, installation]
keywords: [installation, setup, python, pyenv, uv]
category: onboarding
aliases:
  - /docs/getting-started/installation/
---

# Install Bengal

## Requirements

Bengal requires **Python 3.12 or later**. We recommend Python 3.14+ (3.14t free-threaded build for best performance).

## Install

::::{tab-set}

:::{tab-item} pip
```bash
pip install bengal
```
:::

:::{tab-item} uv
```bash
uv pip install bengal
```

Or for a one-time run:

```bash
uvx bengal --version
```
:::

:::{tab-item} pipx
```bash
pipx install bengal
```

This installs Bengal in an isolated environment while making the `bengal` command available globally.
:::

:::{tab-item} From Source
```bash
git clone https://github.com/lbliii/bengal.git
cd bengal
pip install -e ".[dev]"
```

This installs Bengal in development mode.
:::

::::

## Verify Installation

```bash
bengal --version
```

You should see output like: `Bengal SSG, version X.X.X`

## Python Version Setup

::::{tab-set}

:::{tab-item} pyenv (Recommended)

pyenv lets you install and switch between multiple Python versions:

```bash
# macOS (with Homebrew)
brew install pyenv

# Install Python 3.14
pyenv install 3.14.0

# Set as default
pyenv global 3.14.0

# Verify
python --version
```
:::

:::{tab-item} Official Installer

Download Python 3.14 from [python.org/downloads](https://www.python.org/downloads/).

After installation, verify: `python3 --version`
:::

::::

## Free-Threaded Python (Optional)

For best performance, use the free-threaded build (Python 3.14t):

```bash
# With pyenv
pyenv install 3.14.0t
pyenv global 3.14.0t

# Verify free-threading is enabled
python -c "import sys; print('Free-threaded!' if sys._is_gil_enabled() == False else 'GIL enabled')"
```

**Why?** The free-threaded build enables true parallel processing for 1.8-2x faster builds.

## Troubleshooting

### "Command not found"

- Ensure Python's bin directory is in your PATH
- If using a virtual environment, activate it: `source .venv/bin/activate`
- Try reinstalling: `pip uninstall bengal && pip install bengal`

### Python version errors

- Verify: `python --version` or `python3 --version`
- Install Python 3.12+ using pyenv or official installer

### Permission errors

- Use `--user` flag: `pip install --user bengal`
- Or use a virtual environment: `python -m venv venv && source venv/bin/activate`

## Next Steps

- **[Writer Quickstart](/docs/get-started/quickstart-writer/)** — Start creating content
- **[Themer Quickstart](/docs/get-started/quickstart-themer/)** — Customize your site's look
- **[Tutorials](/docs/tutorials/)** — Guided learning journeys
