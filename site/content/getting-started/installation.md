---
title: Installation
description: How to install bengal
weight: 20
---

## Before You Start

Bengal is built with Python 3.14t free-threaded features in mind. We recommend creating an environment that is 3.14t+.

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