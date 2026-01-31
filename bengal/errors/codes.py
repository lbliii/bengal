"""
Unique error codes for Bengal errors.

Error codes enable quick identification, searchability, and documentation linking.
Each code follows the format ``[Category][Number]`` where the category is a single
letter prefix indicating the error domain.

Category Prefixes
=================

====  ================  =================================
Code  Category          Description
====  ================  =================================
C     Config            Configuration loading and validation
N     Content           Frontmatter, markdown, taxonomy
R     Rendering         Template rendering and output
D     Discovery         Content and section discovery
A     Cache             Build cache operations
S     Server            Development server
T     Template          Template functions, shortcodes, directives
P     Parsing           YAML, JSON, TOML, markdown parsing
X     Asset             Static asset processing
G     Graph             Graph analysis and algorithms
O     Autodoc           Autodoc extraction and generation
V     Validator         Health check and validation operations
====  ================  =================================

Usage
=====

Raise an error with a code::

    from bengal.errors import ErrorCode, BengalRenderingError

    raise BengalRenderingError(
        "Template not found",
        code=ErrorCode.R001,
        file_path=template_path,
    )

Look up a code by name::

    from bengal.errors import get_error_code_by_name

    code = get_error_code_by_name("R001")  # By code name
    code = get_error_code_by_name("template_not_found")  # By value

Get all codes in a category::

    from bengal.errors import get_codes_by_category

    rendering_codes = get_codes_by_category("rendering")

See Also
========

- Each code maps to documentation at ``/docs/reference/errors/#{code}``
- ``bengal/errors/exceptions.py`` - Exception classes using these codes
"""

from __future__ import annotations

from enum import Enum


class ErrorCode(Enum):
    """
    Unique error codes for Bengal errors.

    Each code follows the format ``[Category][Number]`` where:

    - **Category**: Single letter indicating error domain (C, N, R, D, A, S, T, P, X)
    - **Number**: 3-digit sequential number within the category (001-099)

    Codes are organized into ranges by category:

    - ``C001-C099``: Configuration errors
    - ``N001-N099``: Content errors (frontmatter, markdown)
    - ``R001-R099``: Rendering errors (templates, output)
    - ``D001-D099``: Discovery errors (content paths, sections)
    - ``A001-A099``: Cache errors (corruption, versioning)
    - ``S001-S099``: Server errors (dev server, ports)
    - ``T001-T099``: Template function errors (shortcodes, directives)
    - ``P001-P099``: Parsing errors (YAML, JSON, markdown)
    - ``X001-X099``: Asset errors (static files, processing)
    - ``G001-G099``: Graph/analysis errors
    - ``O001-O099``: Autodoc extraction/generation errors
    - ``V001-V099``: Validator/health check errors
    - ``B001-B099``: Build/orchestration errors

    Each code maps to documentation at ``/docs/reference/errors/#{code}``.

    Attributes:
        value: Human-readable identifier (e.g., "template_not_found")
        name: Code identifier (e.g., "R001")

    Example:
            >>> from bengal.errors import ErrorCode
            >>> code = ErrorCode.R001
            >>> code.name
            'R001'
            >>> code.value
            'template_not_found'
            >>> code.category
            'rendering'
            >>> code.docs_url
            '/docs/reference/errors/#r001'

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

    # Collections (N011-N020)
    N011 = "collection_validation_failed"  # Schema validation failure
    N012 = "collection_not_found"  # Unknown collection referenced
    N013 = "collection_schema_invalid"  # Schema class definition error
    N014 = "collection_load_failed"  # collections.py import error
    N015 = "collection_directory_missing"  # Collection directory doesn't exist

    # Content Layer (N016-N020)
    N016 = "content_entry_parse_failed"  # Remote entry parse/conversion error

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

    # Syntax highlighting (R011-R015)
    R011 = "highlighting_language_unknown"  # Unknown/unsupported language
    R012 = "highlighting_backend_error"  # Backend initialization or processing error
    R013 = "highlighting_theme_unknown"  # Unknown syntax theme/palette

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

    # Content Layer (D008-D011)
    D008 = "content_source_fetch_failed"  # Remote source fetch failure
    D009 = "content_source_offline"  # Offline mode with no cache
    D010 = "content_source_auth_failed"  # 401/403 authentication error
    D011 = "content_source_not_found"  # 404 source/repo/database not found

    # Directory Discovery (D012-D014)
    D012 = "symlink_loop_detected"  # Circular symlink in content directory
    D013 = "asset_stat_failed"  # Asset file stat failed
    D014 = "git_ref_fetch_failed"  # Git branch/tag list failed

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
    T010 = "icon_not_found"

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

    # Fonts (X007-X010)
    X007 = "font_download_config_error"  # Missing output_dir or invalid config
    X008 = "font_download_failed"  # Network/API failure downloading font
    X009 = "font_not_found"  # Font family not available from Google Fonts

    # ============================================================
    # Graph/Analysis errors (G001-G099)
    # ============================================================
    G001 = "graph_not_built"
    G002 = "graph_invalid_parameter"
    G003 = "graph_cycle_detected"
    G004 = "graph_disconnected_component"
    G005 = "graph_analysis_failed"

    # ============================================================
    # Autodoc errors (O001-O099)
    # ============================================================
    O001 = "autodoc_extraction_failed"  # General extraction failure (strict mode)
    O002 = "autodoc_syntax_error"  # Python syntax error in source
    O003 = "autodoc_openapi_parse_failed"  # OpenAPI YAML/JSON parse failure
    O004 = "autodoc_cli_load_failed"  # CLI app import/load failure
    O005 = "autodoc_invalid_source"  # Invalid source path/location
    O006 = "autodoc_no_elements_produced"  # Extraction produced no elements

    # ============================================================
    # Validator/Health errors (V001-V099)
    # ============================================================
    V001 = "validator_crashed"  # Validator raised unhandled exception
    V002 = "health_check_failed"  # HealthCheck.run() failed
    V003 = "autofix_failed"  # AutoFixer operation failed
    V004 = "linkcheck_timeout"  # External link check timed out
    V005 = "linkcheck_network_error"  # Network error during link check
    V006 = "health_graph_analysis_failed"  # Connectivity/graph analysis failed in health

    # ============================================================
    # Build/Orchestration errors (B001-B099)
    # ============================================================
    B001 = "build_phase_failed"  # Generic build phase failure
    B002 = "build_parallel_error"  # Parallel processing failure
    B003 = "build_incremental_failed"  # Incremental build detection/cache failure
    B004 = "menu_build_failed"  # Menu building failure
    B005 = "taxonomy_collection_failed"  # Taxonomy collection failure
    B006 = "taxonomy_page_generation_failed"  # Taxonomy page generation failure
    B007 = "asset_processing_failed"  # Asset processing failure
    B008 = "postprocess_task_failed"  # Post-processing task failure
    B009 = "section_finalization_failed"  # Section finalization failure
    B010 = "cache_initialization_failed"  # Cache/tracker initialization failure

    @property
    def docs_url(self) -> str:
        """
        Documentation URL for this error code.

        Returns:
            URL path to error documentation anchor (e.g., "/docs/reference/errors/#r001")
        """
        return f"/docs/reference/errors/#{self.name.lower()}"

    @property
    def category(self) -> str:
        """
        Human-readable error category derived from the code prefix.

        Maps single-letter prefixes to descriptive category names:
        C→config, N→content, R→rendering, D→discovery, A→cache,
        S→server, T→template_function, P→parsing, X→asset, G→graph.

        Returns:
            Category name (e.g., "rendering", "config") or "unknown"
        """
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
            "G": "graph",
            "O": "autodoc",
            "V": "validator",
            "B": "build",
        }
        prefix = self.name[0]
        return categories.get(prefix, "unknown")

    @property
    def subsystem(self) -> str:
        """
        Bengal package subsystem where this error typically originates.

        Maps error codes to the primary Bengal package responsible
        for handling errors of this type. Used for investigation.

        Returns:
            Subsystem name (e.g., "rendering", "core") or "unknown"
        """
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
            "G": "analysis",
            "O": "autodoc",
            "V": "health",
            "B": "orchestration",
        }
        prefix = self.name[0]
        return subsystem_map.get(prefix, "unknown")

    def __str__(self) -> str:
        """
        String representation of the error code.

        Returns:
            The code name (e.g., "R001")
        """
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
