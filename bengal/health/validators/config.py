"""
Configuration validator wrapper.

Integrates the existing ConfigValidator into the health check system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult
from bengal.utils.concurrency.workers import WorkloadType, get_optimal_workers

if TYPE_CHECKING:
    from bengal.config.accessor import Config
    from bengal.orchestration.build_context import BuildContext
    from bengal.protocols import SiteLike

# Type for config that supports dict-like access
ConfigLike = "Config | dict[str, Any]"


class ConfigValidatorWrapper(BaseValidator):
    """
    Wrapper for config validation.

    Note: Config validation happens at load time, so by the time we get to
    health checks, the config has already been validated. This validator
    confirms that validation occurred and reports any config-related concerns.

    """

    name = "Configuration"
    description = "Validates site configuration"
    enabled_by_default = True

    @override
    def validate(
        self, site: SiteLike, build_context: BuildContext | Any | None = None
    ) -> list[CheckResult]:
        """Validate configuration."""
        results = []

        # Config is already validated at load time, so we just do sanity checks
        config = site.config

        # Check essential fields are present
        results.extend(self._check_essential_fields(config))

        # Check for common misconfigurations
        results.extend(self._check_common_issues(config))

        return results

    def _check_essential_fields(self, config: Config | dict[str, Any]) -> list[CheckResult]:
        """Check that essential config fields are present."""
        results = []

        # These fields should always be present (with defaults)
        essential_fields = ["output_dir", "theme"]

        missing = [f for f in essential_fields if f not in config]

        if missing:
            results.append(
                CheckResult.warning(
                    f"Missing configuration fields: {', '.join(missing)}",
                    code="H010",
                    recommendation="Add these fields to your bengal.toml for better control.",
                )
            )
        # No success message - if fields are present, silence is golden

        return results

    def _check_common_issues(self, config: Config | dict[str, Any]) -> list[CheckResult]:
        """Check for common configuration issues."""
        results = []

        # Check baseurl configuration issues
        results.extend(self._check_baseurl_issues(config))

        # Check if max_workers is very high
        # Use a typical workload estimate to see what workers would be used
        # Access from build section (supports both Config and dict)
        build_section = getattr(config, "build", None)
        if build_section is not None and hasattr(build_section, "max_workers"):
            max_workers_override = getattr(build_section, "max_workers", None)
            incremental = getattr(build_section, "incremental", None)
            parallel = getattr(build_section, "parallel", True)
        else:
            build_dict = config.get("build", {}) if hasattr(config, "get") else {}
            if isinstance(build_dict, dict):
                max_workers_override = build_dict.get("max_workers")
                incremental = build_dict.get("incremental")
                parallel = build_dict.get("parallel", True)
                # Fall back to top-level if not present in build.*
                if max_workers_override is None:
                    max_workers_override = config.get("max_workers") if hasattr(config, "get") else None
                if incremental is None:
                    incremental = config.get("incremental") if hasattr(config, "get") else None
                if "parallel" not in build_dict and hasattr(config, "get"):
                    parallel = config.get("parallel", parallel)
            else:
                # Fallback to flat access for backward compatibility
                max_workers_override = config.get("max_workers") if hasattr(config, "get") else None
                incremental = config.get("incremental") if hasattr(config, "get") else None
                parallel = config.get("parallel", True) if hasattr(config, "get") else True

        max_workers = get_optimal_workers(
            100,
            workload_type=WorkloadType.MIXED,
            config_override=max_workers_override,
        )
        if max_workers > 20:
            results.append(
                CheckResult.warning(
                    f"max_workers is very high ({max_workers})",
                    code="H011",
                    recommendation="Very high worker counts may cause resource exhaustion. Consider reducing to 8-12.",
                )
            )

        # Check if incremental build is enabled without parallel
        if incremental and not parallel:
            results.append(
                CheckResult.info(
                    "Incremental builds work best with parallel processing",
                    recommendation="Consider enabling parallel=true for faster incremental builds.",
                )
            )

        # No success message - if no problems found, silence is golden

        return results

    def _check_baseurl_issues(self, config: dict[str, Any]) -> list[CheckResult]:
        """Check for common baseurl configuration issues.

        Common problems:
        - Trailing slash causing double-slash URLs
        - GitHub Pages project sites need baseurl set to /repo-name
        - Missing baseurl when deploying to subdirectory
        """
        results = []

        baseurl = config.get("baseurl", "")
        site_url = config.get("url", "")

        # Check for trailing slash
        if baseurl and baseurl.endswith("/"):
            results.append(
                CheckResult.info(
                    "Base URL has trailing slash",
                    recommendation=(
                        "Trailing slashes in baseurl can cause double-slash issues in URLs. "
                        "Consider removing it: baseurl = '/myrepo' not '/myrepo/'"
                    ),
                )
            )

        # Check for GitHub Pages project sites without baseurl
        if site_url and "github.io" in site_url.lower():
            # Parse the URL to check structure
            # Pattern: https://username.github.io/repo-name -> needs baseurl = "/repo-name"
            # Pattern: https://username.github.io -> no baseurl needed
            parts = site_url.rstrip("/").split("/")
            # After split: ['https:', '', 'username.github.io', 'repo-name']
            if len(parts) > 3 and parts[3]:
                # Has a path component - likely a project site
                expected_baseurl = f"/{parts[3]}"
                if not baseurl:
                    results.append(
                        CheckResult.warning(
                            "GitHub Pages project site may need baseurl",
                            code="H012",
                            recommendation=(
                                f"Your site URL suggests a project site: {site_url}\n"
                                f"Project sites need baseurl set to the repo name:\n"
                                f"  baseurl = '{expected_baseurl}'\n"
                                "Without this, assets and links may 404 on GitHub Pages."
                            ),
                        )
                    )
                elif baseurl != expected_baseurl:
                    results.append(
                        CheckResult.info(
                            "Verify baseurl matches repository name",
                            recommendation=(
                                f"Your site URL: {site_url}\n"
                                f"Your baseurl: '{baseurl}'\n"
                                f"Expected baseurl: '{expected_baseurl}'\n"
                                "Mismatched baseurl will cause broken links on GitHub Pages."
                            ),
                        )
                    )

        # Check for baseurl without leading slash
        if baseurl and not baseurl.startswith("/"):
            results.append(
                CheckResult.warning(
                    "Base URL should start with '/'",
                    code="H013",
                    recommendation=(
                        f"baseurl = '{baseurl}' should be '/{baseurl}'\n"
                        "Without the leading slash, URL resolution may fail."
                    ),
                )
            )

        return results
