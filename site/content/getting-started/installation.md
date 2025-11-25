---
title: Installation
description: How to install bengal
weight: 20
type: doc
draft: false
lang: en
tags: [onboarding, installation]
keywords: [installation, setup, python, pyenv, uv]
category: onboarding
---

## Before You Start

Bengal is built with Python 3.14+ free-threaded features in mind. We recommend Python 3.14+ (3.14t free-threaded build recommended for best performance).

::::{tab-set}
:::{tab-item} pyenv

```bash
# Install pyenv (see https://github.com/pyenv/pyenv for full instructions)
brew install pyenv  # On macOS with Homebrew
# or: curl https://pyenv.run | bash

pyenv install 3.14.0
pyenv global 3.14.0

# Initialize pyenv in your shell profile (add these lines to ~/.zshrc or ~/.bash_profile):
# export PYENV_ROOT="$HOME/.pyenv"
# export PATH="$PYENV_ROOT/bin:$PATH"
# eval "$(pyenv init --path)"
# eval "$(pyenv init -)"
# eval "$(pyenv virtualenv-init -)"
#
# Then reload your shell:
# source ~/.zshrc  # or source ~/.bash_profile
#
# Verify with: python --version (should show 3.14.0)
```

:::

:::{tab-item} Official Installer

Download from [python.org/downloads](python.org/downloads).

:::

::::

## Install

::::{tab-set}

:::{tab-item} UV

```bash
uv pip install bengal
```

:::

:::{tab-item} PyPi

```bash
pip install bengal
```

:::

:::{tab-item} Development Version

```bash
git clone https://github.com/lbliii/bengal.git
cd bengal
```

:::

::::

## Verify Installation

After installing, verify Bengal is working:

```bash
bengal --version
```

You should see output like: `Bengal SSG, version X.X.X`

If you see an error, check:
- Python version: `python --version` (should be 3.14+)
- Virtual environment is activated (if using one)
- Installation completed without errors

## Troubleshooting

### Installation Issues

**"Command not found" after installation:**
- Ensure Python's bin directory is in your PATH
- If using a virtual environment, activate it: `source .venv/bin/activate`
- Try reinstalling: `pip uninstall bengal && pip install bengal`

**Python version errors:**
- Verify Python version: `python --version` or `python3 --version`
- Install Python 3.14+ using pyenv or official installer
- Ensure you're using the correct Python executable

**Permission errors:**
- Use `--user` flag: `pip install --user bengal`
- Or use a virtual environment: `python -m venv venv && source venv/bin/activate`

**UV installation issues:**
- Install UV: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Verify UV: `uv --version`
- Try with explicit Python: `uv pip install --python 3.14 bengal`
