# file_io

```{warning}
Template Variable Error: python/module.md.jinja2
Undefined variable: 'config' is undefined
```

## Basic Information

**Type:** module
**Source:** bengal/utils/file_io.py

File I/O utilities with robust error handling.

Provides standardized file reading/writing operations with consistent error handling,
logging, and encoding fallback. Consolidates duplicate file I/O patterns found
throughout the codebase.

Example:
    from bengal.utils.file_io import read_text_file, load_json, load_yaml

    # Read text file with encoding fallback
    content = read_text_file(path, fallback_encoding='latin-1')

    # Load JSON with error handling
    data = load_json(path, on_error='return_empty')

    # Auto-detect and load data file
    data = load_data_file(path)  # Works for .json, .yaml, .toml

*Note: Template has undefined variables. This is fallback content.*
