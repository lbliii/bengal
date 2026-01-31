"""
Normalized config accessors mixin.

Provides properties that normalize config values supporting multiple formats
(bool, dict, None) into consistent dictionaries with all defaults applied.
"""

from __future__ import annotations

from typing import Any


class SiteNormalizedConfigMixin:
    """
    Mixin providing normalized config accessor properties for Site.

    These properties normalize config values that support multiple formats
    (bool, dict, None) into consistent dictionaries with all defaults applied.
    Templates use these instead of manual .get() chains with fallbacks.
    """

    # This attribute is defined on the Site dataclass
    config: Any

    @property
    def build_badge(self) -> dict[str, Any]:
        """
        Get normalized build badge configuration.

        Handles all supported formats:
        - None/False: disabled
        - True: enabled with defaults
        - dict: enabled with custom settings

        Returns:
            Normalized dict with keys: enabled, dir_name, label, label_color, message_color

        Example:
            {% if site.build_badge.enabled %}
                <span>{{ site.build_badge.label }}</span>
            {% endif %}
        """
        value = self.config.get("build_badge")

        if value is None or value is False:
            return {
                "enabled": False,
                "dir_name": "bengal",
                "label": "built in",
                "label_color": "#555",
                "message_color": "#4c1d95",
            }

        if value is True:
            return {
                "enabled": True,
                "dir_name": "bengal",
                "label": "built in",
                "label_color": "#555",
                "message_color": "#4c1d95",
            }

        if isinstance(value, dict):
            return {
                "enabled": bool(value.get("enabled", True)),
                "dir_name": str(value.get("dir_name", "bengal")),
                "label": str(value.get("label", "built in")),
                "label_color": str(value.get("label_color", "#555")),
                "message_color": str(value.get("message_color", "#4c1d95")),
            }

        # Unknown type: treat as disabled
        return {
            "enabled": False,
            "dir_name": "bengal",
            "label": "built in",
            "label_color": "#555",
            "message_color": "#4c1d95",
        }

    @property
    def document_application(self) -> dict[str, Any]:
        """
        Get normalized document application configuration.

        Document Application enables modern browser-native features:
        - View Transitions API for smooth page transitions
        - Speculation Rules for prefetching/prerendering
        - Native <dialog>, popover, and CSS state machines

        Returns:
            Normalized dict with enabled flag and all sub-configs with defaults applied

        Example:
            {% if site.document_application.enabled %}
            {% if site.document_application.navigation.view_transitions %}
                <meta name="view-transition" content="same-origin">
            {% endif %}
            {% endif %}
        """
        from bengal.config.defaults import DEFAULTS

        defaults = DEFAULTS["document_application"]
        value = self.config.get("document_application", {})

        if not isinstance(value, dict):
            # If not a dict (e.g., False), return defaults with enabled=False
            result = {
                "enabled": False,
                "navigation": dict(defaults["navigation"]),
                "speculation": dict(defaults["speculation"]),
                "interactivity": dict(defaults["interactivity"]),
                "features": {},
            }
            return result

        # Merge with defaults
        navigation = value.get("navigation", {})
        speculation = value.get("speculation", {})
        interactivity = value.get("interactivity", {})

        return {
            "enabled": bool(value.get("enabled", defaults["enabled"])),
            "navigation": {
                "view_transitions": navigation.get(
                    "view_transitions", defaults["navigation"]["view_transitions"]
                ),
                "transition_style": navigation.get(
                    "transition_style", defaults["navigation"]["transition_style"]
                ),
                "scroll_restoration": navigation.get(
                    "scroll_restoration", defaults["navigation"]["scroll_restoration"]
                ),
            },
            "speculation": {
                "enabled": speculation.get("enabled", defaults["speculation"]["enabled"]),
                "prerender": {
                    "eagerness": speculation.get("prerender", {}).get(
                        "eagerness", defaults["speculation"]["prerender"]["eagerness"]
                    ),
                    "patterns": speculation.get("prerender", {}).get(
                        "patterns", defaults["speculation"]["prerender"]["patterns"]
                    ),
                },
                "prefetch": {
                    "eagerness": speculation.get("prefetch", {}).get(
                        "eagerness", defaults["speculation"]["prefetch"]["eagerness"]
                    ),
                    "patterns": speculation.get("prefetch", {}).get(
                        "patterns", defaults["speculation"]["prefetch"]["patterns"]
                    ),
                },
                "auto_generate": speculation.get(
                    "auto_generate", defaults["speculation"]["auto_generate"]
                ),
                "exclude_patterns": speculation.get(
                    "exclude_patterns", defaults["speculation"]["exclude_patterns"]
                ),
            },
            "interactivity": {
                "tabs": interactivity.get("tabs", defaults["interactivity"]["tabs"]),
                "accordions": interactivity.get(
                    "accordions", defaults["interactivity"]["accordions"]
                ),
                "modals": interactivity.get("modals", defaults["interactivity"]["modals"]),
                "tooltips": interactivity.get("tooltips", defaults["interactivity"]["tooltips"]),
                "dropdowns": interactivity.get("dropdowns", defaults["interactivity"]["dropdowns"]),
                "code_copy": interactivity.get("code_copy", defaults["interactivity"]["code_copy"]),
            },
            # Feature flags with defaults (all enabled by default)
            "features": {
                "speculation_rules": True,
                "view_transitions_meta": True,
                **value.get("features", {}),
            },
        }

    @property
    def link_previews(self) -> dict[str, Any]:
        """
        Get normalized link previews configuration.

        Link Previews provide Wikipedia-style hover cards for internal links,
        showing page title, excerpt, reading time, and tags. Requires per-page
        JSON generation to be enabled.

        Cross-site previews can be enabled for trusted hosts via allowed_hosts.
        See: plan/rfc-cross-site-xref-link-previews.md

        Returns:
            Normalized dict with enabled flag and all display options

        Example:
            {% if site.link_previews.enabled %}
                {# Include link preview script and config bridge #}
            {% endif %}
        """
        from bengal.config.defaults import DEFAULTS

        defaults = DEFAULTS["link_previews"]
        value = self.config.get("link_previews", {})

        if not isinstance(value, dict):
            # If not a dict (e.g., False), return defaults with enabled=False
            if value is False:
                return {
                    "enabled": False,
                    "hover_delay": defaults["hover_delay"],
                    "hide_delay": defaults["hide_delay"],
                    "show_section": defaults["show_section"],
                    "show_reading_time": defaults["show_reading_time"],
                    "show_word_count": defaults["show_word_count"],
                    "show_date": defaults["show_date"],
                    "show_tags": defaults["show_tags"],
                    "max_tags": defaults["max_tags"],
                    "include_selectors": defaults["include_selectors"],
                    "exclude_selectors": defaults["exclude_selectors"],
                    # Cross-site preview defaults
                    "allowed_hosts": defaults["allowed_hosts"],
                    "allowed_schemes": defaults["allowed_schemes"],
                    "host_failure_threshold": defaults["host_failure_threshold"],
                    "show_dead_links": defaults["show_dead_links"],
                }
            # True or None: use defaults with enabled=True
            return dict(defaults)

        # Merge with defaults
        return {
            "enabled": bool(value.get("enabled", defaults["enabled"])),
            "hover_delay": value.get("hover_delay", defaults["hover_delay"]),
            "hide_delay": value.get("hide_delay", defaults["hide_delay"]),
            "show_section": value.get("show_section", defaults["show_section"]),
            "show_reading_time": value.get("show_reading_time", defaults["show_reading_time"]),
            "show_word_count": value.get("show_word_count", defaults["show_word_count"]),
            "show_date": value.get("show_date", defaults["show_date"]),
            "show_tags": value.get("show_tags", defaults["show_tags"]),
            "max_tags": value.get("max_tags", defaults["max_tags"]),
            "include_selectors": value.get("include_selectors", defaults["include_selectors"]),
            "exclude_selectors": value.get("exclude_selectors", defaults["exclude_selectors"]),
            # Cross-site preview configuration (RFC: Cross-Site Link Previews)
            "allowed_hosts": value.get("allowed_hosts", defaults["allowed_hosts"]),
            "allowed_schemes": value.get("allowed_schemes", defaults["allowed_schemes"]),
            "host_failure_threshold": value.get(
                "host_failure_threshold", defaults["host_failure_threshold"]
            ),
            "show_dead_links": value.get("show_dead_links", defaults["show_dead_links"]),
        }
