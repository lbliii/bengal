# Bengal

[![PyPI version](https://img.shields.io/pypi/v/bengal.svg)](https://pypi.org/project/bengal/)
[![Build Status](https://github.com/lbliii/bengal/actions/workflows/tests.yml/badge.svg)](https://github.com/lbliii/bengal/actions/workflows/tests.yml)
[![Python Version](https://img.shields.io/pypi/pyversions/bengal.svg)](https://pypi.org/project/bengal/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A static site generator written in Python.

## Install

```bash
pip install bengal
```

## Quick Start

```bash
bengal new site mysite
cd mysite
bengal site serve
```

Site runs at `localhost:8000`.

## Features

- Jinja2 templates
- Incremental builds
- Markdown with MyST directives
- Auto-generated API docs from Python source
- Asset fingerprinting and minification
- Dev server with live reload

## Requirements

Python 3.14+. See [installation guide](https://lbliii.github.io/bengal/docs/get-started/installation/).

## Documentation

📚 **[lbliii.github.io/bengal](https://lbliii.github.io/bengal/)**

## Commands

```bash
bengal new site mysite      # Create site
bengal new page my-post     # Create page
bengal site build           # Build
bengal site serve           # Dev server
bengal validate             # Health checks
```

## Configuration

```toml
# bengal.toml
[site]
title = "My Site"
baseurl = "https://example.com"

[theme]
name = "default"
```

## Project Structure

```
mysite/
├── bengal.toml      # Config
├── content/         # Markdown
├── templates/       # Custom templates
├── assets/          # Static files
└── public/          # Output
```

## Development

```bash
git clone https://github.com/lbliii/bengal.git
cd bengal
pip install -e ".[server]"
```

## License

MIT
