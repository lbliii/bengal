---
title: Install Bengal
nav_title: Install
description: Install Bengal using pip, uv, or from source
weight: 10
draft: false
lang: en
tags:
- onboarding
- installation
keywords:
- installation
- setup
- python
- pyenv
- uv
category: onboarding
---

# Install Bengal

## Requirements

Bengal requires **Python 3.14 or later**. For best performance, use the free-threaded build (Python 3.14t), which enables true parallel processing.

## Install

:::{tab-set}
:::{tab-item} uv
:icon: rocket
:badge: Recommended

```bash
uv pip install bengal
```

Or for a one-time run without installation:

```bash
uvx bengal --version
```

:::{/tab-item}

:::{tab-item} pip
:icon: package

```bash
pip install bengal
```

:::{/tab-item}

:::{tab-item} pipx
:icon: terminal

```bash
pipx install bengal
```

This installs Bengal in an isolated environment while making the `bengal` command available globally.
:::{/tab-item}

:::{tab-item} From Source
:icon: code
:badge: Development

```bash
git clone https://github.com/lbliii/bengal.git
cd bengal
make setup
make install
```

This installs Bengal in editable mode with development dependencies.
:::{/tab-item}
:::{/tab-set}

## Verify Installation

```bash
bengal --version
```

You should see output like: `Bengal SSG, version 0.1.10`

## Upgrade Bengal

Bengal includes a built-in upgrade command that automatically detects how it was installed:

```bash
# Interactive upgrade (recommended)
bengal upgrade

# Skip confirmation
bengal upgrade -y

# Preview changes without executing
bengal upgrade --dry-run
```

The upgrade command:
- Detects your installer (uv, pip, pipx, conda)
- Checks PyPI for the latest version (cached for 24 hours)
- Shows a confirmation before making changes

:::{tip}
Bengal will show a notification after commands when a new version is available. You can disable this by setting `BENGAL_NO_UPDATE_CHECK=1` in your environment.
:::

## Python Version Setup

:::{tab-set}
:::{tab-item} pyenv
:icon: settings
:badge: Recommended

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

:::{/tab-item}

:::{tab-item} Official Installer
:icon: download

Download Python 3.14 from [python.org/downloads](https://www.python.org/downloads/).

After installation, verify: `python3 --version`
:::{/tab-item}
:::{/tab-set}

## Free-Threaded Python

For best build performance, use the free-threaded Python build (Python 3.14t). This enables true parallel processing for 1.5-2x faster builds on multi-core machines.

```bash
# With pyenv
pyenv install 3.14.0t
pyenv global 3.14.0t

# Verify free-threading is enabled
python -c "import sys; print('Free-threaded!' if sys._is_gil_enabled() == False else 'GIL enabled')"
```

Bengal automatically detects the free-threaded build and enables parallel processing.

## Troubleshooting

:::{dropdown} Command not found
:icon: alert

Ensure Python's bin directory is in your PATH.

If using a virtual environment, activate it:

```bash
source .venv/bin/activate
```

Try reinstalling:

```bash
pip uninstall bengal && pip install bengal
```

:::

:::{dropdown} Python version errors
:icon: alert

Verify your Python version:

```bash
python --version
# or
python3 --version
```

Bengal requires Python 3.14 or later. Install using [pyenv](https://github.com/pyenv/pyenv) or the [official installer](https://www.python.org/downloads/).
:::

:::{dropdown} Permission errors
:icon: alert

Use the `--user` flag:

```bash
pip install --user bengal
```

Or use a virtual environment:

```bash
python -m venv venv && source venv/bin/activate
pip install bengal
```

:::

## Next Steps

- **[[docs/get-started/quickstart-writer|Writer Quickstart]]** — Start creating content
- **[[docs/get-started/quickstart-themer|Themer Quickstart]]** — Customize your site's look
- **[[docs/tutorials|Tutorials]]** — Guided learning journeys
