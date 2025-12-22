"""
Main health check orchestrator.

This module provides HealthCheck, the central coordinator for running health
validators and producing unified reports. It supports parallel execution for
improved performance and tiered validation for different use cases.

Key Features:
    - Automatic registration of 20+ built-in validators
    - Parallel execution with configurable worker count
    - Tiered validation (build/full/ci) for speed vs thoroughness tradeoffs
    - Incremental validation of changed files only
    - Build context sharing for expensive artifact reuse (knowledge graph)

Execution Tiers:
    - build: Fast validators only (<100ms) for development feedback
    - full: Includes knowledge graph validators (~500ms)
    - ci: All validators including external link checks (~30s)

Architecture:
    HealthCheck follows the orchestrator pattern. It coordinates validators
    but does not perform validation logic itself. Validators run in isolation
    and return CheckResult objects, which are aggregated into a HealthReport.

Related:
    - bengal.health.base: BaseValidator interface
    - bengal.health.report: HealthReport and result types
    - bengal.health.validators: Built-in validators

Example:
    >>> health = HealthCheck(site)
    >>> report = health.run(tier="build", verbose=True)
    >>> if report.has_errors():
    ...     print(report.format_console())
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bengal.health.base import BaseValidator
from bengal.health.report import CheckResult, HealthReport, ValidatorReport

if TYPE_CHECKING:
    from bengal.core.site import Site
    from bengal.utils.build_context import BuildContext
    from bengal.utils.profile import BuildProfile


@dataclass
class HealthCheckStats:
    """
    Statistics about health check execution.

    Provides observability into parallel execution performance, useful for
    diagnosing slow builds and validating that parallelization is effective.

    Attributes:
        total_duration_ms: Wall-clock time for entire health check run
        execution_mode: Either 'parallel' or 'sequential'
        validator_count: Number of validators that ran
        worker_count: Number of worker threads used (1 for sequential)
        cpu_count: Available CPU cores on system
        sum_validator_duration_ms: Sum of individual validator durations
    """

    total_duration_ms: float
    execution_mode: str
    validator_count: int
    worker_count: int
    cpu_count: int
    sum_validator_duration_ms: float

    @property
    def speedup(self) -> float:
        """
        Calculate speedup from parallel execution.

        Returns ratio of sum(individual durations) / total duration.
        A speedup of 2.0 means parallel was 2x faster than sequential would be.
        """
        if self.total_duration_ms == 0:
            return 1.0
        return self.sum_validator_duration_ms / self.total_duration_ms

    @property
    def efficiency(self) -> float:
        """
        Calculate parallel efficiency (0.0 to 1.0).

        efficiency = speedup / worker_count
        1.0 = perfect scaling, 0.5 = 50% efficiency
        """
        if self.worker_count == 0:
            return 0.0
        return self.speedup / self.worker_count

    def format_summary(self) -> str:
        """Format a human-readable summary."""
        from bengal.output.icons import get_icon_set
        from bengal.utils.rich_console import should_use_emoji

        icons = get_icon_set(should_use_emoji())
        mode_icon = icons.success if self.execution_mode == "parallel" else icons.info
        lines = [
            f"   {mode_icon} {self.validator_count} validators, {self.worker_count} workers, {self.speedup:.1f}x speedup",
        ]
        return "\n".join(lines)


class HealthCheck:
    """
    Orchestrates health check validators and produces unified health reports.

    By default, registers all standard validators. You can disable auto-registration
    by passing auto_register=False, then manually register validators.

    Usage:
        # Default: auto-registers all validators
        health = HealthCheck(site)
        report = health.run()
        print(report.format_console())

        # Manual registration:
        health = HealthCheck(site, auto_register=False)
        health.register(ConfigValidator())
        health.register(OutputValidator())
        report = health.run()
    """

    def __init__(self, site: Site, auto_register: bool = True):
        """
        Initialize health check system.

        Args:
            site: The Site object to validate
            auto_register: Whether to automatically register all default validators
        """
        self.site = site
        self.validators: list[BaseValidator] = []

        if auto_register:
            self._register_default_validators()

    def _register_default_validators(self) -> None:
        """Register all default validators."""
        from bengal.health.validators import (
            AnchorValidator,
            AssetValidator,
            CacheValidator,
            ConfigValidatorWrapper,
            ConnectivityValidator,
            DirectiveValidator,
            FontValidator,
            LinkValidatorWrapper,
            MenuValidator,
            NavigationValidator,
            OutputValidator,
            OwnershipPolicyValidator,
            PerformanceValidator,
            RenderingValidator,
            RSSValidator,
            SitemapValidator,
            TaxonomyValidator,
            TrackValidator,
            URLCollisionValidator,
        )

        # Register in logical order (fast validators first)
        # Phase 1: Basic validation
        self.register(ConfigValidatorWrapper())
        self.register(OutputValidator())
        self.register(URLCollisionValidator())  # Catch URL collisions early
        self.register(OwnershipPolicyValidator())  # Validate namespace ownership policy

        # Phase 2: Content validation
        self.register(RenderingValidator())
        self.register(DirectiveValidator())
        self.register(NavigationValidator())
        self.register(MenuValidator())
        self.register(TaxonomyValidator())
        self.register(TrackValidator())
        self.register(LinkValidatorWrapper())
        self.register(AnchorValidator())  # Explicit anchors and [[#anchor]] references

        # Phase 3: Advanced validation
        self.register(CacheValidator())
        self.register(PerformanceValidator())

        # Phase 4: Production-ready validation
        self.register(RSSValidator())
        self.register(SitemapValidator())
        self.register(FontValidator())
        self.register(AssetValidator())

        # Phase 5: Knowledge graph validation
        self.register(ConnectivityValidator())

    def register(self, validator: BaseValidator) -> None:
        """
        Register a validator to be run.

        Args:
            validator: Validator instance to register
        """
        self.validators.append(validator)

    # Threshold for parallel execution - avoid thread overhead for small workloads
    PARALLEL_THRESHOLD = 3

    # Last execution statistics (for observability)
    last_stats: HealthCheckStats | None = None

    def _get_optimal_workers(self, validator_count: int) -> int:
        """
        Calculate optimal worker count based on system resources and workload.

        Auto-scales based on:
        - Available CPU cores (uses ~50% to leave headroom)
        - Number of validators (no point having more workers than tasks)
        - Minimum of 2 workers (for any parallelism benefit)
        - Maximum of 8 workers (diminishing returns beyond this)

        Args:
            validator_count: Number of validators to run

        Returns:
            Optimal number of worker threads
        """
        cpu_count = os.cpu_count() or 4
        # Use ~50% of cores, minimum 2, maximum 8
        optimal = max(2, min(8, cpu_count // 2))
        # Don't use more workers than validators
        return min(optimal, validator_count)

    def run(
        self,
        build_stats: dict[str, Any] | None = None,
        verbose: bool = False,
        profile: BuildProfile | None = None,
        incremental: bool = False,
        context: list[Path] | None = None,
        cache: Any = None,
        build_context: Any = None,
        tier: str = "build",
    ) -> HealthReport:
        """
        Run all registered validators and produce a health report.

        Validators run in parallel when there are 3+ enabled validators,
        falling back to sequential execution for smaller workloads.

        Args:
            build_stats: Optional build statistics to include in report
            verbose: Whether to show verbose output during validation
            profile: Build profile to use for filtering validators
            incremental: If True, only validate changed files (requires cache)
            context: Optional list of specific file paths to validate (overrides incremental)
            cache: Optional BuildCache instance for incremental validation and result caching
            build_context: Optional BuildContext with cached artifacts (e.g., knowledge graph,
                          cached content) that validators can use to avoid redundant computation.
                          When build_context has cached content, validators like DirectiveValidator
                          skip disk I/O, reducing health check time from ~4.6s to <100ms.
            tier: Validation tier to run:
                  - "build": Fast validators only (<100ms) - default
                  - "full": + Knowledge graph validators (~500ms)
                  - "ci": All validators including external checks (~30s)

        Returns:
            HealthReport with results from all validators
        """
        overall_start = time.time()
        report = HealthReport(build_stats=build_stats)

        # Filter to enabled validators based on tier
        enabled_validators = [
            v
            for v in self.validators
            if self._is_validator_enabled(v, profile, verbose)
            and self._is_validator_in_tier(v, tier)
        ]

        # Determine which files to validate (for file-specific validators)
        files_to_validate = self._get_files_to_validate(context, incremental, cache)

        # Track execution mode and workers for stats
        cpu_count = os.cpu_count() or 4
        execution_mode: str
        worker_count: int

        # Choose execution strategy based on validator count
        if len(enabled_validators) >= self.PARALLEL_THRESHOLD:
            worker_count = self._get_optimal_workers(len(enabled_validators))
            execution_mode = "parallel"
            if verbose:
                print(
                    f"  ⚡ Running {len(enabled_validators)} validators in parallel ({worker_count} workers)"
                )
            self._run_validators_parallel(
                enabled_validators,
                report,
                build_context,
                verbose,
                cache,
                files_to_validate,
                worker_count,
            )
        else:
            worker_count = 1
            execution_mode = "sequential"
            if verbose and len(enabled_validators) > 0:
                print(f"  📝 Running {len(enabled_validators)} validators sequentially")
            self._run_validators_sequential(
                enabled_validators, report, build_context, verbose, cache, files_to_validate
            )

        # Calculate and store stats
        total_duration_ms = (time.time() - overall_start) * 1000
        sum_validator_duration = sum(vr.duration_ms for vr in report.validator_reports)

        self.last_stats = HealthCheckStats(
            total_duration_ms=total_duration_ms,
            execution_mode=execution_mode,
            validator_count=len(enabled_validators),
            worker_count=worker_count,
            cpu_count=cpu_count,
            sum_validator_duration_ms=sum_validator_duration,
        )

        if verbose:
            print(self.last_stats.format_summary())

        return report

    def _is_validator_in_tier(self, validator: BaseValidator, tier: str) -> bool:
        """
        Check if a validator should run based on the validation tier.

        Tiered validation allows fast builds by default with thorough checks
        available when needed.

        Tiers (cumulative):
            - "build": Fast validators only (<100ms)
            - "full": + Knowledge graph validators (~500ms)
            - "ci": All validators including external checks (~30s)

        Args:
            validator: The validator to check
            tier: One of "build", "full", or "ci"

        Returns:
            True if validator should run for this tier
        """
        from bengal.config.defaults import get_feature_config

        health_config = get_feature_config(self.site.config, "health_check")

        # Get tier validator lists
        build_validators = health_config.get("build_validators", [])
        full_validators = health_config.get("full_validators", [])
        ci_validators = health_config.get("ci_validators", [])

        # Normalize validator name for comparison
        validator_key = validator.name.lower().replace(" ", "_")

        # Determine which tiers this validator belongs to
        in_build = validator_key in [v.lower() for v in build_validators]
        in_full = validator_key in [v.lower() for v in full_validators]
        in_ci = validator_key in [v.lower() for v in ci_validators]

        # If validator is not in any tier list, include it by default (backward compat)
        if not in_build and not in_full and not in_ci:
            return True

        # Check if validator should run for requested tier (dict lookup avoids consecutive if)
        tier_checks = {
            "build": in_build,
            "full": in_build or in_full,
            "ci": True,  # All validators run in CI tier
        }
        return tier_checks.get(tier, in_build)  # Unknown tier defaults to build

    def _is_validator_enabled(
        self, validator: BaseValidator, profile: BuildProfile | None, verbose: bool
    ) -> bool:
        """
        Check if a validator should run based on profile and config.

        Args:
            validator: The validator to check
            profile: Optional build profile for filtering
            verbose: Whether to show skip messages

        Returns:
            True if validator should run
        """
        from bengal.utils.profile import is_validator_enabled

        if profile:
            # Check if profile allows this validator (uses global profile state)
            profile_allows = is_validator_enabled(validator.name)

            # Check config for explicit override (normalized to handle bool/dict)
            from bengal.config.defaults import get_feature_config

            health_config = get_feature_config(self.site.config, "health_check")
            validators_config = health_config.get("validators", {})
            validator_key = validator.name.lower().replace(" ", "_")
            config_explicit = validator_key in validators_config
            config_value = validators_config.get(validator_key) if config_explicit else None

            if profile_allows:
                # Profile allows it - check if config explicitly disables
                if config_explicit and config_value is False:
                    if verbose:
                        print(f"  Skipping {validator.name} (disabled in config)")
                    return False
                # Profile allows and config doesn't disable - run it
                return True
            else:
                # Profile disables it - only run if config explicitly enables (True)
                if config_explicit and config_value is True:
                    # Config explicitly enables - override profile
                    return True
                else:
                    # Profile disables and config doesn't override - skip
                    if verbose:
                        print(f"  Skipping {validator.name} (disabled by profile)")
                    return False
        else:
            # No profile - use config/default
            if not validator.is_enabled(self.site.config):
                if verbose:
                    print(f"  Skipping {validator.name} (disabled in config)")
                return False
            return True

    def _get_files_to_validate(
        self, context: list[Path] | None, incremental: bool, cache: Any
    ) -> set[Path] | None:
        """
        Determine which files to validate for incremental/context modes.

        Args:
            context: Optional explicit file list
            incremental: Whether incremental mode is enabled
            cache: BuildCache instance

        Returns:
            Set of paths to validate, or None for full validation
        """
        if context:
            # Explicit context provided - validate only these files
            return set(Path(p) for p in context)
        elif incremental and cache:
            # Incremental mode - find changed files
            files_to_validate: set[Path] = set()
            for page in self.site.pages:
                if page.source_path and cache.is_changed(page.source_path):
                    files_to_validate.add(page.source_path)
            return files_to_validate
        return None

    def _run_single_validator(
        self,
        validator: BaseValidator,
        build_context: BuildContext | Any | None,
        cache: Any,
        files_to_validate: set[Path] | None,
    ) -> ValidatorReport:
        """
        Run a single validator and return its report.

        This method is used by both sequential and parallel execution.

        Args:
            validator: The validator to run
            build_context: Optional BuildContext with cached artifacts
            cache: Optional BuildCache for result caching
            files_to_validate: Set of files to validate (for incremental mode)

        Returns:
            ValidatorReport with results and timing
        """
        # File-specific validators that can benefit from incremental validation
        FILE_SPECIFIC_VALIDATORS = {"Directives", "Links"}

        # Check if we can use cached results (for file-specific validators)
        use_cache = (
            cache is not None
            and validator.name in FILE_SPECIFIC_VALIDATORS
            and files_to_validate is not None
            and len(files_to_validate) < len(self.site.pages)  # Only cache if subset
        )

        cached_results: list[CheckResult] = []
        if use_cache:
            # Try to get cached results for unchanged files
            for page in self.site.pages:
                if not page.source_path or (
                    files_to_validate is not None and page.source_path in files_to_validate
                ):
                    continue  # Skip changed files or pages without source

                cached = cache.get_cached_validation_results(page.source_path, validator.name)
                if cached:
                    # Deserialize cached results
                    cached_results.extend([CheckResult.from_cache_dict(r) for r in cached])

        # Run validator and time it
        start_time = time.time()

        try:
            # Pass build_context so validators can use cached artifacts
            results = validator.validate(self.site, build_context=build_context)

            # Set validator name on all results
            for result in results:
                if not result.validator:
                    result.validator = validator.name

        except Exception as e:
            # If validator crashes, record as error
            results = [
                CheckResult.error(
                    f"Validator crashed: {e}",
                    recommendation="This is a bug in the health check system. Please report it.",
                    validator=validator.name,
                )
            ]

        duration_ms = (time.time() - start_time) * 1000

        # Capture stats from validator if available (observability)
        validator_stats = getattr(validator, "last_stats", None)

        return ValidatorReport(
            validator_name=validator.name,
            results=results,
            duration_ms=duration_ms,
            stats=validator_stats,
        )

    def _run_validators_sequential(
        self,
        validators: list[BaseValidator],
        report: HealthReport,
        build_context: BuildContext | Any | None,
        verbose: bool,
        cache: Any,
        files_to_validate: set[Path] | None,
    ) -> None:
        """
        Run validators sequentially (for small workloads).

        Args:
            validators: List of validators to run
            report: HealthReport to add results to
            build_context: Optional BuildContext with cached artifacts
            verbose: Whether to show per-validator output
            cache: Optional BuildCache for result caching
            files_to_validate: Set of files to validate (for incremental mode)
        """
        for validator in validators:
            validator_report = self._run_single_validator(
                validator, build_context, cache, files_to_validate
            )
            report.validator_reports.append(validator_report)

            if verbose:
                status = "✅" if not validator_report.has_problems else "⚠️"
                print(
                    f"  {status} {validator.name}: "
                    f"{len(validator_report.results)} checks in {validator_report.duration_ms:.1f}ms"
                )

    def _run_validators_parallel(
        self,
        validators: list[BaseValidator],
        report: HealthReport,
        build_context: BuildContext | Any | None,
        verbose: bool,
        cache: Any,
        files_to_validate: set[Path] | None,
        worker_count: int | None = None,
    ) -> None:
        """
        Run validators in parallel using ThreadPoolExecutor.

        Uses as_completed() to process results as they finish, providing
        better UX for verbose mode. Output is printed in the main thread
        to prevent garbled console output.

        Args:
            validators: List of validators to run
            report: HealthReport to add results to
            build_context: Optional BuildContext with cached artifacts
            verbose: Whether to show per-validator output
            cache: Optional BuildCache for result caching
            files_to_validate: Set of files to validate (for incremental mode)
            worker_count: Number of worker threads (auto-detected if None)
        """
        # Use provided worker count or auto-detect
        max_workers = worker_count or self._get_optimal_workers(len(validators))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all validators for parallel execution
            futures = {
                executor.submit(
                    self._run_single_validator, v, build_context, cache, files_to_validate
                ): v
                for v in validators
            }

            # Process results as they complete
            for future in as_completed(futures):
                validator = futures[future]
                try:
                    validator_report = future.result()
                    report.validator_reports.append(validator_report)

                    if verbose:
                        status = "✅" if not validator_report.has_problems else "⚠️"
                        print(
                            f"  {status} {validator.name}: "
                            f"{len(validator_report.results)} checks in "
                            f"{validator_report.duration_ms:.1f}ms"
                        )
                except Exception as e:
                    # Future itself failed (shouldn't happen with our error handling)
                    validator_report = ValidatorReport(
                        validator_name=validator.name,
                        results=[CheckResult.error(f"Validator execution failed: {e}")],
                        duration_ms=0,
                    )
                    report.validator_reports.append(validator_report)

                    if verbose:
                        print(f"  ❌ {validator.name}: execution failed - {e}")

    def run_and_print(
        self, build_stats: dict[str, Any] | None = None, verbose: bool = False
    ) -> HealthReport:
        """
        Run health checks and print console output.

        Args:
            build_stats: Optional build statistics
            verbose: Whether to show all checks (not just problems)

        Returns:
            HealthReport
        """
        report = self.run(build_stats=build_stats, verbose=verbose)
        print(report.format_console(verbose=verbose))
        return report

    def __repr__(self) -> str:
        return f"<HealthCheck: {len(self.validators)} validators>"
