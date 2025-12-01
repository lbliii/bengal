---
title: Install Bengal
description: Install Bengal using pip, uv, or from source
weight: 20
type: doc
draft: false
lang: en
tags: [onboarding, installation]
keywords: [installation, setup, python, pyenv, uv]
category: onboarding
---

## Before You Start

Bengal requires **Python 3.14 or later**. We recommend Python 3.14+ (3.14t free-threaded build recommended for best performance).

**Why Python 3.14?** Bengal leverages modern Python features including:
- **Free-threaded execution** - Enables true parallel processing for faster builds
- **Enhanced type hinting** - Better code quality and IDE support
- **Performance improvements** - Faster standard library operations

:::{admonition} What is Python 3.14t?
:class: info

The `t` suffix indicates the **free-threaded build**, which disables Python's Global Interpreter Lock (GIL). With [PEP 779](https://peps.python.org/pep-0779/), free-threaded Python is now officially supported.

**Why it matters for Bengal:**
- **1.8-2x faster builds** through true parallel processing
- Standard Python 3.14 works fine, but 3.14t unlocks Bengal's full performance

**Install the free-threaded build:**
```bash
# With pyenv
pyenv install 3.14.0t
pyenv global 3.14.0t

# Verify free-threading is enabled
python -c "import sys; print('Free-threaded!' if sys._is_gil_enabled() == False else 'GIL enabled')"
```
:::

:::::{tab-set}
::::{tab-item} pyenv (Recommended)

pyenv is a Python version manager that lets you install and switch between multiple Python versions. It's the easiest way to manage Python 3.14 alongside other versions.

**Installation Steps:**

1. **Install pyenv:**
   ```bash
   # macOS (with Homebrew)
   brew install pyenv

   # Linux/Unix (or macOS without Homebrew)
   curl https://pyenv.run | bash
   ```

2. **Configure your shell** (add to `~/.zshrc` or `~/.bash_profile`):
   ```bash
   export PYENV_ROOT="$HOME/.pyenv"
   export PATH="$PYENV_ROOT/bin:$PATH"
   eval "$(pyenv init --path)"
   eval "$(pyenv init -)"
   eval "$(pyenv virtualenv-init -)"
   ```

3. **Reload your shell:**
   ```bash
   source ~/.zshrc  # or source ~/.bash_profile
   ```

4. **Install Python 3.14:**
   ```bash
   # Standard build (works great)
   pyenv install 3.14.0
   
   # Free-threaded build (recommended for best performance)
   pyenv install 3.14.0t
   
   # Set as default
   pyenv global 3.14.0t  # or 3.14.0
   ```

5. **Verify installation:**
   ```bash
   python --version  # Should show Python 3.14.0
   ```

:::{tip}
**Troubleshooting pyenv:** If `pyenv install` fails, you may need to install build dependencies. See [pyenv's installation guide](https://github.com/pyenv/pyenv#installation) for your platform.
:::

::::

::::{tab-item} Official Installer

Download Python 3.14 from [python.org/downloads](https://www.python.org/downloads/release/python-3140/).

**After installation:**
- Verify: `python3 --version` (should show 3.14.0)
- Use `python3` command instead of `python` if your system has multiple versions

:::{note}
**macOS users:** The official installer may conflict with system Python. Consider using pyenv instead for easier version management.
:::

::::

:::::

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
pip install -e ".[dev]"
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
