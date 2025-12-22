"""
Origin tracking for configuration introspection.

This module provides utilities to track which configuration file contributed
each key in a merged configuration. This is essential for debugging complex
multi-file configurations and powers the ``bengal config show --origin`` command.

Use Cases:
    - **Debugging**: Identify which file set a particular configuration value.
    - **Introspection**: Understand configuration layering and overrides.
    - **Documentation**: Generate annotated configuration displays.

Classes:
    ConfigWithOrigin: Configuration container that tracks the source of each key.

Example:
    >>> tracker = ConfigWithOrigin()
    >>> tracker.merge({"site": {"title": "Test"}}, "_default/site.yaml")
    >>> tracker.merge({"site": {"baseurl": "/"}}, "environments/prod.yaml")
    >>> tracker.get_origin("site.title")
    '_default/site.yaml'
    >>> tracker.get_origin("site.baseurl")
    'environments/prod.yaml'

See Also:
    - :mod:`bengal.config.directory_loader`: Uses origin tracking during loading.
    - CLI command ``bengal config show --origin``: Displays origin-annotated config.
"""

from __future__ import annotations

from typing import Any


class ConfigWithOrigin:
    """
    Configuration container with origin tracking for each key.

    Tracks which file (or source) contributed each configuration key,
    enabling introspection and debugging of multi-file configurations.
    Later merges override earlier values, and the origin is updated
    to reflect the most recent source.

    Attributes:
        config: The merged configuration dictionary.
        origins: Mapping of dot-separated key paths to their source identifiers.

    Example:
        >>> tracker = ConfigWithOrigin()
        >>> tracker.merge({"site": {"title": "Test"}}, "_default/site.yaml")
        >>> tracker.merge({"site": {"baseurl": "/"}}, "environments/prod.yaml")
        >>> tracker.config
        {'site': {'title': 'Test', 'baseurl': '/'}}
        >>> tracker.origins["site.title"]
        '_default/site.yaml'
        >>> tracker.origins["site.baseurl"]
        'environments/prod.yaml'
    """

    def __init__(self) -> None:
        """Initialize an empty configuration with origin tracking."""
        self.config: dict[str, Any] = {}
        self.origins: dict[str, str] = {}  # key_path → file_path

    def merge(self, other: dict[str, Any], origin: str) -> None:
        """
        Merge configuration and track the origin of each key.

        Recursively merges the provided dictionary into the internal
        configuration, recording the origin for each key that is set or
        updated.

        Args:
            other: Configuration dictionary to merge in.
            origin: Source identifier (e.g., ``"_default/site.yaml"``).
        """
        self._merge_recursive(self.config, other, origin, [])

    def _merge_recursive(
        self,
        base: dict[str, Any],
        override: dict[str, Any],
        origin: str,
        path: list[str],
    ) -> None:
        """
        Recursively merge dictionaries and track origins.

        Internal method that performs the actual merge operation while
        building up the key path for origin tracking.

        Args:
            base: Base dictionary (mutated in place).
            override: Dictionary with values to merge in.
            origin: Source identifier for tracking.
            path: Current key path as a list of keys.
        """
        for key, value in override.items():
            key_path = ".".join(path + [key])

            if isinstance(value, dict):
                if key not in base or not isinstance(base[key], dict):
                    # New dict or type change: track origin and set
                    base[key] = {}
                    self.origins[key_path] = origin
                # Recurse into dict (whether new or existing)
                self._merge_recursive(base[key], value, origin, path + [key])
            else:
                # Primitive or list: override and track
                base[key] = value
                self.origins[key_path] = origin

    def show_with_origin(self, indent: int = 0) -> str:
        """
        Format the configuration with origin annotations.

        Generates a YAML-like string representation of the configuration
        with inline comments indicating the source file for each value.

        Args:
            indent: Starting indentation level (number of two-space indents).

        Returns:
            Formatted string with origins as inline comments.

        Example:
            Output format::

                site:
                  title: Test  # _default/site.yaml
                  baseurl: /  # environments/prod.yaml
        """
        lines: list[str] = []
        self._format_recursive(self.config, lines, [], indent)
        return "\n".join(lines)

    def _format_recursive(
        self,
        config: dict[str, Any],
        lines: list[str],
        path: list[str],
        indent: int,
    ) -> None:
        """
        Recursively format configuration with origin annotations.

        Internal method that traverses the configuration dictionary and
        builds formatted output lines with origin comments.

        Args:
            config: Configuration dictionary to format.
            lines: Output lines list (appended to in place).
            path: Current key path as a list of keys.
            indent: Current indentation level (each level = 2 spaces).
        """
        for key, value in config.items():
            key_path = ".".join(path + [key])
            origin = self.origins.get(key_path, "unknown")
            indent_str = "  " * indent

            if isinstance(value, dict):
                # Nested dict
                lines.append(f"{indent_str}{key}:")
                self._format_recursive(value, lines, path + [key], indent + 1)
            elif isinstance(value, list):
                # List
                lines.append(f"{indent_str}{key}:  # {origin}")
                for item in value:
                    lines.append(f"{indent_str}  - {item}")
            else:
                # Primitive
                lines.append(f"{indent_str}{key}: {value}  # {origin}")

    def get_origin(self, key_path: str) -> str | None:
        """
        Get the origin file for a specific configuration key.

        Args:
            key_path: Dot-separated key path (e.g., ``"site.title"``).

        Returns:
            Origin identifier string, or ``None`` if the key was not tracked.

        Example:
            >>> tracker.get_origin("site.title")
            '_default/site.yaml'
            >>> tracker.get_origin("nonexistent.key")  # Returns None
        """
        return self.origins.get(key_path)
