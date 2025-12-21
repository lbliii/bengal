"""
Unique error codes for Bengal errors.

Error codes enable quick identification, searchability, and documentation linking.
Each code is prefixed by category:
- C: Config errors
- N: Content errors
- R: Rendering errors
- D: Discovery errors
- A: Cache errors
- S: Server errors
- T: Template errors
- P: Parsing errors
- X: Asset errors

Usage:
    from bengal.errors import ErrorCode, BengalRenderingError

    raise BengalRenderingError(
        "Template not found",
        code=ErrorCode.R001,
        file_path=template_path,
    )
"""

from __future__ import annotations

from enum import Enum


class ErrorCode(Enum):
    """
    Unique error codes for Bengal errors.

    Format: [Category][Number]
    - Category: Single letter indicating error domain
    - Number: 3-digit sequential number

    Each code maps to documentation at /docs/errors/{code}/
    """

    # ============================================================
    # Config errors (C001-C099)
    # ============================================================
    C001 = "config_yaml_parse_error"
    C002 = "config_key_missing"
    C003 = "config_invalid_value"
    C004 = "config_type_mismatch"
    C005 = "config_defaults_missing"
    C006 = "config_environment_unknown"
    C007 = "config_circular_reference"
    C008 = "config_deprecated_key"

    # ============================================================
    # Content errors (N001-N099)
    # ============================================================
    N001 = "frontmatter_invalid"
    N002 = "frontmatter_date_invalid"
    N003 = "content_file_encoding"
    N004 = "content_file_not_found"
    N005 = "content_markdown_error"
    N006 = "content_shortcode_error"
    N007 = "content_toc_extraction_error"
    N008 = "content_taxonomy_invalid"
    N009 = "content_weight_invalid"
    N010 = "content_slug_invalid"

    # ============================================================
    # Rendering errors (R001-R099)
    # ============================================================
    R001 = "template_not_found"
    R002 = "template_syntax_error"
    R003 = "template_undefined_variable"
    R004 = "template_filter_error"
    R005 = "template_include_error"
    R006 = "template_macro_error"
    R007 = "template_block_error"
    R008 = "template_context_error"
    R009 = "template_inheritance_error"
    R010 = "render_output_error"

    # ============================================================
    # Discovery errors (D001-D099)
    # ============================================================
    D001 = "content_dir_not_found"
    D002 = "invalid_content_path"
    D003 = "section_index_missing"
    D004 = "circular_section_reference"
    D005 = "duplicate_page_path"
    D006 = "invalid_file_pattern"
    D007 = "permission_denied"

    # ============================================================
    # Cache errors (A001-A099)
    # ============================================================
    A001 = "cache_corruption"
    A002 = "cache_version_mismatch"
    A003 = "cache_read_error"
    A004 = "cache_write_error"
    A005 = "cache_invalidation_error"
    A006 = "cache_lock_timeout"

    # ============================================================
    # Server errors (S001-S099)
    # ============================================================
    S001 = "server_port_in_use"
    S002 = "server_bind_error"
    S003 = "server_reload_error"
    S004 = "server_websocket_error"
    S005 = "server_static_file_error"

    # ============================================================
    # Template function errors (T001-T099)
    # ============================================================
    T001 = "shortcode_not_found"
    T002 = "shortcode_argument_error"
    T003 = "shortcode_render_error"
    T004 = "directive_not_found"
    T005 = "directive_argument_error"
    T006 = "directive_since_empty"
    T007 = "directive_deprecated_empty"
    T008 = "directive_changed_empty"
    T009 = "directive_include_not_found"

    # ============================================================
    # Parsing errors (P001-P099)
    # ============================================================
    P001 = "yaml_parse_error"
    P002 = "json_parse_error"
    P003 = "toml_parse_error"
    P004 = "markdown_parse_error"
    P005 = "frontmatter_delimiter_missing"
    P006 = "glossary_parse_error"

    # ============================================================
    # Asset errors (X001-X099)
    # ============================================================
    X001 = "asset_not_found"
    X002 = "asset_invalid_path"
    X003 = "asset_processing_failed"
    X004 = "asset_copy_error"
    X005 = "asset_fingerprint_error"
    X006 = "asset_minify_error"

    @property
    def docs_url(self) -> str:
        """Get documentation URL for this error code."""
        return f"/docs/errors/{self.name.lower()}/"

    @property
    def category(self) -> str:
        """Get error category from code prefix."""
        categories = {
            "C": "config",
            "N": "content",
            "R": "rendering",
            "D": "discovery",
            "A": "cache",
            "S": "server",
            "T": "template_function",
            "P": "parsing",
            "X": "asset",
        }
        prefix = self.name[0]
        return categories.get(prefix, "unknown")

    @property
    def subsystem(self) -> str:
        """Get Bengal subsystem for this error."""
        subsystem_map = {
            "C": "config",
            "N": "core",
            "R": "rendering",
            "D": "discovery",
            "A": "cache",
            "S": "server",
            "T": "rendering",
            "P": "core",
            "X": "assets",
        }
        prefix = self.name[0]
        return subsystem_map.get(prefix, "unknown")

    def __str__(self) -> str:
        """Return code name for display."""
        return self.name


def get_error_code_by_name(name: str) -> ErrorCode | None:
    """
    Look up error code by name.

    Args:
        name: Error code name (e.g., "R001" or "template_not_found")

    Returns:
        ErrorCode if found, None otherwise
    """
    # Try direct name match
    try:
        return ErrorCode[name.upper()]
    except KeyError:
        pass

    # Try value match
    for code in ErrorCode:
        if code.value == name.lower():
            return code

    return None


def get_codes_by_category(category: str) -> list[ErrorCode]:
    """
    Get all error codes in a category.

    Args:
        category: Category name (e.g., "rendering", "config")

    Returns:
        List of ErrorCode instances in that category
    """
    return [code for code in ErrorCode if code.category == category]
