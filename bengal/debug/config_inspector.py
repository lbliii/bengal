"""
Configuration Inspector and Diff Tool.

Advanced configuration comparison and analysis beyond the basic
`bengal config diff` command. Provides deep comparison between config
sources, explains how effective values are resolved through the layer
system, and identifies potential configuration issues.

Key Features:
    - ConfigDiff: Single configuration key difference
    - ConfigComparisonResult: Complete diff between two sources
    - KeyExplanation: Resolution chain for a specific key
    - ConfigInspector: Debug tool combining all capabilities

Use Cases:
    - Compare local vs production configuration
    - Understand why a config key has a specific value
    - Detect configuration drift between environments
    - Find deprecated or suspicious configuration

Example:
    >>> from bengal.debug.config_inspector import ConfigInspector
    >>> inspector = ConfigInspector(site)
    >>> diff = inspector.compare("local", "production")
    >>> print(diff.format_detailed())
    Comparing: local → production
      Added: 1
      Removed: 0
      Changed: 3

    >>> explanation = inspector.explain_key("site.baseurl")
    >>> print(explanation.format())
    site.baseurl: https://example.com
      Source: environments/production.yaml
      Resolution chain:
        ○ _default: /
        → environments/production: https://example.com

Related Modules:
    - bengal.config.directory_loader: Config loading and layering
    - bengal.config.environment: Environment detection
    - bengal.debug.base: Debug tool infrastructure

See Also:
    - bengal/cli/commands/config.py: CLI integration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from bengal.debug.base import DebugFinding, DebugReport, DebugTool, Severity
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ConfigDiff:
    """
    A single configuration key difference between two sources.

    Attributes:
        path: Dot-separated key path (e.g., "site.title", "build.parallel").
        type: Type of change: "added", "removed", or "changed".
        old_value: Previous value (None for added keys).
        new_value: New value (None for removed keys).
        old_origin: Source file where old value came from.
        new_origin: Source file where new value comes from.
        impact: Potential impact description of this change.

    Example:
        >>> diff = ConfigDiff(
        ...     path="site.baseurl",
        ...     type="changed",
        ...     old_value="/",
        ...     new_value="https://example.com",
        ...     impact="Changes output URLs and may break links",
        ... )
    """

    path: str
    type: Literal["added", "removed", "changed"]
    old_value: Any = None
    new_value: Any = None
    old_origin: str | None = None
    new_origin: str | None = None
    impact: str | None = None

    def format(self) -> str:
        """
        Format the diff for display.

        Returns:
            Single line like "+ key: value" or "~ key: old → new"
        """
        if self.type == "added":
            return f"+ {self.path}: {self.new_value}"
        elif self.type == "removed":
            return f"- {self.path}: {self.old_value}"
        else:
            return f"~ {self.path}: {self.old_value} → {self.new_value}"


@dataclass
class ConfigComparisonResult:
    """
    Complete result of comparing two configuration sources.

    Contains all differences found, categorized by type, with the
    full configuration dictionaries for reference.

    Attributes:
        source1: Name of first (earlier/base) configuration source.
        source2: Name of second (later/target) configuration source.
        diffs: List of all ConfigDiff instances found.
        config1: Complete configuration dictionary from source1.
        config2: Complete configuration dictionary from source2.

    Example:
        >>> result = inspector.compare("local", "production")
        >>> if result.has_changes:
        ...     print(f"{len(result.changed)} keys changed")
    """

    source1: str
    source2: str
    diffs: list[ConfigDiff] = field(default_factory=list)
    config1: dict[str, Any] = field(default_factory=dict)
    config2: dict[str, Any] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        """Check if there are any differences."""
        return len(self.diffs) > 0

    @property
    def added(self) -> list[ConfigDiff]:
        """Get keys that were added in source2."""
        return [d for d in self.diffs if d.type == "added"]

    @property
    def removed(self) -> list[ConfigDiff]:
        """Get keys that were removed from source1."""
        return [d for d in self.diffs if d.type == "removed"]

    @property
    def changed(self) -> list[ConfigDiff]:
        """Get keys with different values between sources."""
        return [d for d in self.diffs if d.type == "changed"]

    def format_summary(self) -> str:
        """
        Format a brief summary of differences.

        Returns:
            Multi-line summary with counts by change type.
        """
        lines = [
            f"Comparing: {self.source1} → {self.source2}",
            f"  Added: {len(self.added)}",
            f"  Removed: {len(self.removed)}",
            f"  Changed: {len(self.changed)}",
        ]
        return "\n".join(lines)

    def format_detailed(self) -> str:
        """
        Format detailed diff output with all changes.

        Shows added, removed, and changed keys with their values
        and origin files.

        Returns:
            Multi-line detailed diff output.
        """
        lines = [self.format_summary(), ""]

        if self.added:
            lines.append("Added:")
            for diff in self.added:
                origin_info = f" (from {diff.new_origin})" if diff.new_origin else ""
                lines.append(f"  + {diff.path}: {diff.new_value}{origin_info}")
            lines.append("")

        if self.removed:
            lines.append("Removed:")
            for diff in self.removed:
                origin_info = f" (was from {diff.old_origin})" if diff.old_origin else ""
                lines.append(f"  - {diff.path}: {diff.old_value}{origin_info}")
            lines.append("")

        if self.changed:
            lines.append("Changed:")
            for diff in self.changed:
                lines.append(f"  {diff.path}:")
                old_origin = f" ({diff.old_origin})" if diff.old_origin else ""
                new_origin = f" ({diff.new_origin})" if diff.new_origin else ""
                lines.append(f"    - {diff.old_value}{old_origin}")
                lines.append(f"    + {diff.new_value}{new_origin}")
                if diff.impact:
                    lines.append(f"    ⚠️  {diff.impact}")
            lines.append("")

        return "\n".join(lines)


@dataclass
class KeyExplanation:
    """
    Explanation of how a configuration key got its effective value.

    Shows the complete resolution chain through defaults, environment,
    and profile layers, indicating which layer provided the final value.

    Attributes:
        key_path: Dot-separated key path (e.g., "site.baseurl").
        effective_value: The final resolved value for this key.
        origin: Source file where the effective value came from.
        layer_values: Resolution chain as (source, value) tuples.
        is_default: Whether the value comes from _default layer.
        deprecated: Whether this key is deprecated.
        deprecation_message: Message explaining deprecation.

    Example:
        >>> explanation = inspector.explain_key("build.parallel")
        >>> print(explanation.format())
        build.parallel: True
          Source: environments/production.yaml
          Resolution chain:
            ○ _default: False
            → environments/production: True
    """

    key_path: str
    effective_value: Any
    origin: str | None = None
    layer_values: list[tuple[str, Any]] = field(default_factory=list)
    is_default: bool = False
    deprecated: bool = False
    deprecation_message: str | None = None

    def format(self) -> str:
        """
        Format the explanation for display.

        Shows key, value, origin, and full resolution chain.

        Returns:
            Multi-line formatted explanation.
        """
        lines = [f"{self.key_path}: {self.effective_value}"]

        if self.origin:
            lines.append(f"  Source: {self.origin}")

        if self.layer_values:
            lines.append("  Resolution chain:")
            for source, value in self.layer_values:
                marker = "→" if value == self.effective_value else "○"
                lines.append(f"    {marker} {source}: {value}")

        if self.is_default:
            lines.append("  (using default value)")

        if self.deprecated:
            lines.append(f"  ⚠️  DEPRECATED: {self.deprecation_message}")

        return "\n".join(lines)


class ConfigInspector(DebugTool):
    """
    Advanced configuration inspector and diff tool.

    Provides deep comparison between configuration sources (environments,
    profiles), explains how values are resolved through the layer system,
    and identifies potential configuration issues.

    Capabilities:
        - Deep comparison between any config sources
        - Origin tracking for each value
        - Impact analysis for configuration changes
        - Key-level explanation of value resolution
        - Default value detection
        - Deprecation warnings
        - Issue detection (missing protocols, trailing slashes)

    Creation:
        Instantiate with a Site instance:
            inspector = ConfigInspector(site)

    Example:
        >>> inspector = ConfigInspector(site)
        >>> diff = inspector.compare("local", "production")
        >>> print(diff.format_detailed())
        >>>
        >>> explanation = inspector.explain_key("site.baseurl")
        >>> print(explanation.format())
    """

    name: str = "config"
    description: str = "Inspect and compare configuration with origin tracking and impact analysis."

    # Known impact patterns
    IMPACT_PATTERNS: dict[str, str] = {
        "baseurl": "Changes output URLs and may break links",
        "theme": "Changes site appearance and available templates",
        "parallel": "Affects build performance",
        "incremental": "Affects build performance and caching behavior",
        "strict_mode": "Affects error handling during builds",
        "minify_html": "Affects output size and readability",
        "debug": "Affects logging verbosity and error details",
    }

    def __init__(self, site: Any) -> None:
        """
        Initialize inspector.

        Args:
            site: Site instance
        """
        self.site = site
        self._config_dir = Path(site.root) / "config" if site else None

    def run(
        self,
        compare_to: str | None = None,
        explain_key: str | None = None,
        list_sources: bool = False,
        **kwargs: Any,
    ) -> DebugReport:
        """
        Run config inspection.

        Args:
            compare_to: Source to compare against (environment or profile)
            explain_key: Specific key to explain
            list_sources: List available config sources
            **kwargs: Additional arguments

        Returns:
            DebugReport with findings
        """
        report = DebugReport(tool_name=self.name)

        if list_sources:
            sources = self._list_available_sources()
            report.add_finding(
                title="Available config sources",
                description=f"Found sources: {', '.join(sources)}",
                severity=Severity.INFO,
                metadata={"sources": sources},
            )
            return report

        if explain_key:
            explanation = self.explain_key(explain_key)
            if explanation:
                report.add_finding(
                    title=f"Key explanation: {explain_key}",
                    description=f"Value: {explanation.effective_value}",
                    severity=Severity.INFO,
                    metadata={
                        "value": explanation.effective_value,
                        "origin": explanation.origin,
                        "is_default": explanation.is_default,
                    },
                )
                report.metadata["explanation"] = explanation.format()
            else:
                report.add_finding(
                    title=f"Key not found: {explain_key}",
                    description="The requested configuration key does not exist",
                    severity=Severity.WARNING,
                )
            return report

        if compare_to:
            # Get current environment
            from bengal.config.environment import detect_environment

            current_env = detect_environment()
            comparison = self.compare(current_env, compare_to)

            if comparison.has_changes:
                for diff in comparison.diffs:
                    severity = Severity.WARNING if diff.impact else Severity.INFO
                    report.add_finding(
                        title=f"Config diff: {diff.path}",
                        description=diff.format(),
                        severity=severity,
                        metadata={
                            "type": diff.type,
                            "path": diff.path,
                            "impact": diff.impact,
                        },
                    )
            else:
                report.add_finding(
                    title="No configuration differences",
                    description=f"No differences between {current_env} and {compare_to}",
                    severity=Severity.INFO,
                )

            report.metadata["comparison"] = comparison.format_detailed()
            return report

        # Default: show current config summary
        report.add_finding(
            title="No analysis parameters",
            description="Use --compare-to, --explain-key, or --list-sources",
            severity=Severity.INFO,
        )
        return report

    def analyze(self) -> DebugReport:
        """
        Perform analysis and return report.

        This is the abstract method required by DebugTool.
        For parameterized analysis, use run() instead.
        """
        report = self.create_report()
        report.add_finding(
            title="No analysis parameters provided",
            description="Use run() method with compare_to, explain_key, or list_sources parameters",
            severity=Severity.INFO,
        )
        return report

    def _list_available_sources(self) -> list[str]:
        """List available configuration sources."""
        sources = []

        if self._config_dir and self._config_dir.exists():
            # Environments
            env_dir = self._config_dir / "environments"
            if env_dir.exists():
                for f in env_dir.glob("*.yaml"):
                    sources.append(f"env:{f.stem}")

            # Profiles
            profile_dir = self._config_dir / "profiles"
            if profile_dir.exists():
                for f in profile_dir.glob("*.yaml"):
                    sources.append(f"profile:{f.stem}")

        # Always include standard environments
        for env in ["local", "preview", "production"]:
            if f"env:{env}" not in sources:
                sources.append(f"env:{env}")

        return sorted(sources)

    def compare(
        self,
        source1: str,
        source2: str,
        track_origins: bool = True,
    ) -> ConfigComparisonResult:
        """
        Compare two configuration sources.

        Args:
            source1: First source (environment name, "profile:name", or file path)
            source2: Second source
            track_origins: Track origin of each value

        Returns:
            ConfigComparisonResult with all differences
        """
        config1, origins1 = self._load_config_source(source1, track_origins)
        config2, origins2 = self._load_config_source(source2, track_origins)

        result = ConfigComparisonResult(
            source1=source1,
            source2=source2,
            config1=config1,
            config2=config2,
        )

        # Compute diffs recursively
        self._compute_diffs(
            config1,
            config2,
            origins1,
            origins2,
            [],
            result.diffs,
        )

        return result

    def _load_config_source(
        self,
        source: str,
        track_origins: bool = True,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """
        Load configuration from a source.

        Args:
            source: Source identifier
            track_origins: Whether to track origins

        Returns:
            Tuple of (config_dict, origins_dict)
        """
        from bengal.config.directory_loader import ConfigDirectoryLoader

        if not self._config_dir or not self._config_dir.exists():
            return {}, {}

        # Parse source type
        if source.startswith("profile:"):
            profile_name = source[8:]
            loader = ConfigDirectoryLoader(track_origins=track_origins)
            config = loader.load(self._config_dir, profile=profile_name)
            origins = loader.origin_tracker.origins if loader.origin_tracker else {}
            return config, origins

        elif source.startswith("env:"):
            env_name = source[4:]
            loader = ConfigDirectoryLoader(track_origins=track_origins)
            config = loader.load(self._config_dir, environment=env_name)
            origins = loader.origin_tracker.origins if loader.origin_tracker else {}
            return config, origins

        else:
            # Treat as environment name
            loader = ConfigDirectoryLoader(track_origins=track_origins)
            config = loader.load(self._config_dir, environment=source)
            origins = loader.origin_tracker.origins if loader.origin_tracker else {}
            return config, origins

    def _compute_diffs(
        self,
        config1: dict[str, Any],
        config2: dict[str, Any],
        origins1: dict[str, str],
        origins2: dict[str, str],
        path: list[str],
        diffs: list[ConfigDiff],
    ) -> None:
        """Recursively compute diffs between configs."""
        all_keys = set(config1.keys()) | set(config2.keys())

        for key in sorted(all_keys):
            key_path = ".".join(path + [key])

            in_config1 = key in config1
            in_config2 = key in config2

            if not in_config1 and in_config2:
                # Added in config2
                diffs.append(
                    ConfigDiff(
                        path=key_path,
                        type="added",
                        new_value=config2[key],
                        new_origin=origins2.get(key_path),
                        impact=self._get_impact(key),
                    )
                )
            elif in_config1 and not in_config2:
                # Removed in config2
                diffs.append(
                    ConfigDiff(
                        path=key_path,
                        type="removed",
                        old_value=config1[key],
                        old_origin=origins1.get(key_path),
                        impact=self._get_impact(key),
                    )
                )
            elif config1[key] != config2[key]:
                # Value changed
                if isinstance(config1[key], dict) and isinstance(config2[key], dict):
                    # Recurse into nested dicts
                    self._compute_diffs(
                        config1[key],
                        config2[key],
                        origins1,
                        origins2,
                        path + [key],
                        diffs,
                    )
                else:
                    diffs.append(
                        ConfigDiff(
                            path=key_path,
                            type="changed",
                            old_value=config1[key],
                            new_value=config2[key],
                            old_origin=origins1.get(key_path),
                            new_origin=origins2.get(key_path),
                            impact=self._get_impact(key),
                        )
                    )

    def _get_impact(self, key: str) -> str | None:
        """Get potential impact description for a config key."""
        for pattern, impact in self.IMPACT_PATTERNS.items():
            if pattern in key.lower():
                return impact
        return None

    def explain_key(self, key_path: str) -> KeyExplanation | None:
        """
        Explain how a config key got its effective value.

        Shows the resolution chain through defaults → environment → profile.

        Args:
            key_path: Dot-separated key path (e.g., "site.title")

        Returns:
            KeyExplanation or None if key not found
        """
        if not self._config_dir or not self._config_dir.exists():
            return None

        from bengal.config.directory_loader import ConfigDirectoryLoader
        from bengal.config.environment import detect_environment

        # Load config with origin tracking
        loader = ConfigDirectoryLoader(track_origins=True)
        current_env = detect_environment()
        config = loader.load(self._config_dir, environment=current_env)

        # Get value
        value = self._get_nested_value(config, key_path)
        if value is None:
            return None

        # Get origin
        origin = loader.origin_tracker.origins.get(key_path) if loader.origin_tracker else None

        # Build layer values by loading each layer separately
        layer_values: list[tuple[str, Any]] = []

        # Layer 1: Defaults
        try:
            defaults_dir = self._config_dir / "_default"
            if defaults_dir.exists():
                # Load just defaults by not specifying environment
                default_config = self._load_defaults_only(defaults_dir)
                default_value = self._get_nested_value(default_config, key_path)
                if default_value is not None:
                    layer_values.append(("_default", default_value))
        except Exception as e:
            logger.debug(
                "debug_config_defaults_load_failed",
                key_path=key_path,
                error=str(e),
                error_type=type(e).__name__,
                action="skipping_defaults_layer",
            )

        # Layer 2: Environment
        try:
            env_file = self._config_dir / "environments" / f"{current_env}.yaml"
            if env_file.exists():
                import yaml

                env_config = yaml.safe_load(env_file.read_text()) or {}
                env_value = self._get_nested_value(env_config, key_path)
                if env_value is not None:
                    layer_values.append((f"environments/{current_env}", env_value))
        except Exception as e:
            logger.debug(
                "debug_config_env_load_failed",
                key_path=key_path,
                environment=current_env,
                error=str(e),
                error_type=type(e).__name__,
                action="skipping_environment_layer",
            )

        return KeyExplanation(
            key_path=key_path,
            effective_value=value,
            origin=origin,
            layer_values=layer_values,
            is_default=bool(origin and "_default" in origin),
            deprecated=False,
            deprecation_message=None,
        )

    def _load_defaults_only(self, defaults_dir: Path) -> dict[str, Any]:
        """Load only the _default config files."""
        import yaml

        from bengal.config.merge import deep_merge

        config: dict[str, Any] = {}
        for yaml_file in sorted(defaults_dir.glob("*.yaml")):
            try:
                file_config = yaml.safe_load(yaml_file.read_text()) or {}
                config = deep_merge(config, file_config)
            except Exception as e:
                logger.debug(
                    "debug_config_yaml_parse_failed",
                    file=str(yaml_file),
                    error=str(e),
                    error_type=type(e).__name__,
                    action="skipping_file",
                )
        return config

    def _get_nested_value(self, config: dict[str, Any], key_path: str) -> Any:
        """Get a value from nested dict using dot-separated path."""
        keys = key_path.split(".")
        current = config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def find_issues(self) -> list[DebugFinding]:
        """
        Find potential configuration issues.

        Checks for:
        - Deprecated keys
        - Missing required keys
        - Type mismatches
        - Suspicious values

        Returns:
            List of findings
        """
        findings: list[DebugFinding] = []

        if not self.site:
            return findings

        config = getattr(self.site, "config", {})
        if not config:
            return findings

        # Check for common issues
        baseurl = config.get("baseurl", "")
        if baseurl and not baseurl.startswith(("http://", "https://")):
            findings.append(
                DebugFinding(
                    title=f"baseurl should start with http:// or https://: {baseurl}",
                    description="The baseurl should include the protocol prefix",
                    severity=Severity.WARNING,
                    suggestion="Add protocol to baseurl",
                )
            )

        if baseurl and baseurl.endswith("/"):
            findings.append(
                DebugFinding(
                    title="baseurl ends with trailing slash",
                    description="Trailing slash can cause URL concatenation issues",
                    severity=Severity.INFO,
                    suggestion="Consider removing trailing slash for consistency",
                )
            )

        return findings
