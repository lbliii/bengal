"""
Origin tracking for config introspection.

Tracks which file contributed each configuration key for debugging
and the `bengal config show --origin` command.
"""

from __future__ import annotations

from typing import Any


class ConfigWithOrigin:
    """
    Configuration with origin tracking.

    Tracks which file (or source) contributed each configuration key
    for introspection and debugging.

    Examples:
        >>> tracker = ConfigWithOrigin()
        >>> tracker.merge({"site": {"title": "Test"}}, "_default/site.yaml")
        >>> tracker.merge({"site": {"baseurl": "https://example.com"}}, "environments/production.yaml")
        >>> tracker.config
        {"site": {"title": "Test", "baseurl": "https://example.com"}}
        >>> tracker.origins["site.title"]
        "_default/site.yaml"
        >>> tracker.origins["site.baseurl"]
        "environments/production.yaml"
    """

    def __init__(self) -> None:
        """Initialize empty config with origin tracking."""
        self.config: dict[str, Any] = {}
        self.origins: dict[str, str] = {}  # key_path → file_path

    def merge(self, other: dict[str, Any], origin: str) -> None:
        """
        Merge config and track origin.

        Args:
            other: Config dict to merge in
            origin: Source identifier (e.g., "_default/site.yaml")
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
        Recursively merge and track origins.

        Args:
            base: Base dict (mutated)
            override: Override dict
            origin: Source identifier
            path: Current key path (for tracking)
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
        Format config with origin annotations.

        Args:
            indent: Starting indentation level

        Returns:
            Formatted string with origins as comments

        Examples:
            >>> tracker.show_with_origin()
            site:
              title: Test  # _default/site.yaml
              baseurl: https://example.com  # environments/production.yaml
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
        Recursively format config with origins.

        Args:
            config: Config dict
            lines: Output lines (appended to)
            path: Current key path
            indent: Current indentation level
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
        Get origin for a specific key path.

        Args:
            key_path: Dot-separated key path (e.g., "site.title")

        Returns:
            Origin string, or None if not found
        """
        return self.origins.get(key_path)
