"""
Unified utilities for the autodoc documentation extraction system.

This package consolidates all autodoc utilities into focused modules:

- text: Text processing (sanitize_text, truncate_text, slugify)
- paths: Path/URL resolution (resolve_cli_url_path, format_source_file_for_display)
- grouping: Module grouping (auto_detect_prefix_map, apply_grouping)
- config: Config normalization (normalize_autodoc_config)
- metadata: Typed metadata accessors (get_python_*, get_cli_*, get_openapi_*)

All functions are re-exported here for backward compatibility with:
    from bengal.autodoc.utils import sanitize_text

"""

from __future__ import annotations

# Config normalization
from bengal.autodoc.utils.config import normalize_autodoc_config

# Module grouping
from bengal.autodoc.utils.grouping import (
    apply_grouping,
    auto_detect_prefix_map,
)

# Typed metadata accessors
from bengal.autodoc.utils.metadata import (
    get_cli_command_callback,
    get_cli_command_option_count,
    get_cli_group_command_count,
    get_function_parameters,
    get_function_return_info,
    get_openapi_method,
    get_openapi_operation_id,
    get_openapi_path,
    get_openapi_tags,
    get_python_class_bases,
    get_python_class_decorators,
    get_python_class_is_dataclass,
    get_python_function_decorators,
    get_python_function_is_property,
    get_python_function_return_type,
    get_python_function_signature,
    get_python_module_all_exports,
)

# Path/URL resolution
from bengal.autodoc.utils.paths import (
    format_source_file_for_display,
    get_template_dir_for_type,
    resolve_cli_url_path,
)

# Text processing
from bengal.autodoc.utils.text import (
    sanitize_text,
    slugify,
    truncate_text,
)

__all__ = [
    "apply_grouping",
    "auto_detect_prefix_map",
    "format_source_file_for_display",
    "get_cli_command_callback",
    "get_cli_command_option_count",
    "get_cli_group_command_count",
    "get_function_parameters",
    "get_function_return_info",
    "get_openapi_method",
    "get_openapi_operation_id",
    "get_openapi_path",
    "get_openapi_tags",
    "get_python_class_bases",
    "get_python_class_decorators",
    "get_python_class_is_dataclass",
    "get_python_function_decorators",
    "get_python_function_is_property",
    "get_python_function_return_type",
    "get_python_function_signature",
    "get_python_module_all_exports",
    "get_template_dir_for_type",
    "normalize_autodoc_config",
    "resolve_cli_url_path",
    "sanitize_text",
    "slugify",
    "truncate_text",
]
