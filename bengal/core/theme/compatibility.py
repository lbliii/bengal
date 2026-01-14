"""
Theme compatibility checking for template engine portability.

Provides feature matrix and compatibility checker to ensure themes work
correctly with different template engines (Jinja2, Kida, etc.).

Usage:
    from bengal.core.theme.compatibility import check_theme_compatibility

    missing = check_theme_compatibility(theme, "kida")
    if missing:
        print(f"Theme requires unsupported features: {missing}")

Theme Configuration (theme.yaml):
    engine:
      minimum: "jinja2-compatible"
      features_used:
        - namespace_mutation
        - loop_controls
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bengal.themes.config import ThemeConfig

# Comprehensive feature matrix for template engine constructs
# True = feature is supported, False = not supported
FEATURE_SUPPORT: dict[str, dict[str, bool]] = {
    "jinja": {
        # Scoping & Variables
        "namespace_mutation": True,  # {% set ns.value = x %}
        "scoped_blocks": True,  # {% block x scoped %}
        # Control Flow
        "loop_controls": True,  # {% break %}, {% continue %}
        "recursive_loops": True,  # {% for x in y recursive %}
        # Macros & Imports
        "macro_with_context": True,  # {% from x import y with context %}
        "macro_caller": True,  # {{ caller() }}
        "import_with_context": True,  # {% import x with context %}
        # Expressions
        "expression_statement": True,  # {% do list.append(x) %}
        "inline_if": True,  # {{ x if y else z }}
        "walrus_operator": False,  # := not in Jinja2
        # Extensions
        "i18n_extension": True,  # {% trans %}...{% endtrans %}
        "loop_controls_ext": True,  # Requires extension
        "debug_extension": True,  # {% debug %}
    },
    "kida": {
        # Scoping & Variables
        "namespace_mutation": False,  # Not implemented
        "scoped_blocks": True,
        # Control Flow
        "loop_controls": True,  # Native support
        "recursive_loops": True,
        # Macros & Imports
        "macro_with_context": True,
        "macro_caller": True,
        "import_with_context": True,
        # Expressions
        "expression_statement": True,  # {% do %}
        "inline_if": True,
        "walrus_operator": True,  # Native Python 3.8+
        # Extensions
        "i18n_extension": False,  # Use t() function instead
        "loop_controls_ext": True,  # Native, no extension needed
        "debug_extension": False,
    },
    "generic": {
        # Minimal baseline for unknown engines
        "namespace_mutation": False,
        "scoped_blocks": False,
        "loop_controls": False,
        "recursive_loops": False,
        "macro_with_context": False,
        "macro_caller": False,
        "import_with_context": False,
        "expression_statement": False,
        "inline_if": True,  # Most engines support this
        "walrus_operator": False,
        "i18n_extension": False,
        "loop_controls_ext": False,
        "debug_extension": False,
    },
}

# Feature categories for documentation and grouping
FEATURE_CATEGORIES = {
    "scoping": ["namespace_mutation", "scoped_blocks"],
    "control_flow": ["loop_controls", "recursive_loops"],
    "macros": ["macro_with_context", "macro_caller", "import_with_context"],
    "expressions": ["expression_statement", "inline_if", "walrus_operator"],
    "extensions": ["i18n_extension", "loop_controls_ext", "debug_extension"],
}

# Portable alternatives for non-portable features
PORTABLE_ALTERNATIVES: dict[str, str] = {
    "namespace_mutation": "Use groupby filter or pre-compute values in Python",
    "i18n_extension": "Use t() function: {{ t('key', {'param': value}) }}",
    "expression_statement": "Build lists/dicts in Python, pass to template",
    "import_with_context": "Pass required variables explicitly to macros",
}


def check_theme_compatibility(theme: ThemeConfig | dict[str, Any], engine: str) -> list[str]:
    """Check if theme is compatible with engine, return missing features.
    
    Args:
        theme: Theme configuration (ThemeConfig object or dict)
        engine: Engine type ("jinja", "kida", "generic")
    
    Returns:
        List of feature names that theme requires but engine doesn't support.
        Empty list means theme is fully compatible.
    
    Example:
            >>> missing = check_theme_compatibility(theme, "kida")
            >>> if missing:
            ...     print(f"Incompatible features: {missing}")
        
    """
    # Extract engine config from theme
    if hasattr(theme, "get"):
        # dict-like
        engine_config = theme.get("engine", {}) or {}
    elif hasattr(theme, "engine"):
        # ThemeConfig object
        engine_config = theme.engine or {}
    else:
        engine_config = {}

    # Get features used by theme
    required_features = engine_config.get("features_used", [])
    if not required_features:
        return []

    # Get engine capabilities
    supported = FEATURE_SUPPORT.get(engine, FEATURE_SUPPORT["generic"])

    # Find missing features
    missing = [f for f in required_features if not supported.get(f, False)]
    return missing


def get_engine_capabilities(engine: str) -> dict[str, bool]:
    """Get full capability matrix for an engine.
    
    Args:
        engine: Engine type ("jinja", "kida", "generic")
    
    Returns:
        Dict mapping feature name -> bool (supported)
    
    Example:
            >>> caps = get_engine_capabilities("kida")
            >>> caps["namespace_mutation"]
        False
        
    """
    return dict(FEATURE_SUPPORT.get(engine, FEATURE_SUPPORT["generic"]))


def get_portable_alternative(feature: str) -> str | None:
    """Get portable alternative for a non-portable feature.
    
    Args:
        feature: Feature name
    
    Returns:
        String describing portable alternative, or None if none available
        
    """
    return PORTABLE_ALTERNATIVES.get(feature)


def validate_theme_portability(
    theme: ThemeConfig | dict[str, Any],
) -> dict[str, list[str]]:
    """Validate theme portability across all engines.
    
    Args:
        theme: Theme configuration
    
    Returns:
        Dict mapping engine -> list of unsupported features
        Empty dict for each engine means fully portable
    
    Example:
            >>> issues = validate_theme_portability(theme)
            >>> for engine, missing in issues.items():
            ...     if missing:
            ...         print(f"{engine}: missing {missing}")
        
    """
    issues: dict[str, list[str]] = {}
    for engine in FEATURE_SUPPORT:
        missing = check_theme_compatibility(theme, engine)
        if missing:
            issues[engine] = missing
    return issues


def get_minimum_engine_level(theme: ThemeConfig | dict[str, Any]) -> str:
    """Determine minimum engine compatibility level for theme.
    
    Args:
        theme: Theme configuration
    
    Returns:
        Minimum compatibility level:
        - "portable": Works with all engines
        - "jinja2-compatible": Requires Jinja2-compatible features
        - "jinja2-only": Requires Jinja2-specific features
        
    """
    # Extract engine config from theme
    if hasattr(theme, "get"):
        engine_config = theme.get("engine", {}) or {}
    elif hasattr(theme, "engine"):
        engine_config = theme.engine or {}
    else:
        engine_config = {}

    # Check if explicit minimum is set
    explicit_minimum = engine_config.get("minimum")
    if explicit_minimum:
        return str(explicit_minimum)

    # Auto-detect based on features used
    required_features = engine_config.get("features_used", [])
    if not required_features:
        return "portable"

    # Check against Kida capabilities
    kida_supported = FEATURE_SUPPORT["kida"]
    kida_missing = [f for f in required_features if not kida_supported.get(f, False)]

    if not kida_missing:
        # Works with Kida = jinja2-compatible
        return "jinja2-compatible"

    # Requires features only Jinja2 has
    return "jinja2-only"


def format_compatibility_warning(missing_features: list[str], engine: str) -> str:
    """Format a user-friendly warning message for incompatible features.
    
    Args:
        missing_features: List of unsupported feature names
        engine: Target engine name
    
    Returns:
        Formatted warning message with alternatives
        
    """
    if not missing_features:
        return ""

    lines = [
        f"⚠️  Theme uses features not supported by '{engine}' engine:",
        "",
    ]

    for feature in missing_features:
        alt = PORTABLE_ALTERNATIVES.get(feature)
        if alt:
            lines.append(f"  • {feature}")
            lines.append(f"    💡 Alternative: {alt}")
        else:
            lines.append(f"  • {feature}")

    lines.append("")
    lines.append("Consider using a portable alternative or switching to a compatible engine.")

    return "\n".join(lines)


__all__ = [
    "FEATURE_SUPPORT",
    "FEATURE_CATEGORIES",
    "PORTABLE_ALTERNATIVES",
    "check_theme_compatibility",
    "get_engine_capabilities",
    "get_portable_alternative",
    "validate_theme_portability",
    "get_minimum_engine_level",
    "format_compatibility_warning",
]
