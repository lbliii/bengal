"""
Worker pool auto-tuning utilities.

Provides workload-aware worker count calculation for ThreadPoolExecutor usage.
Calibrated via benchmarks per RFC: rfc-unified-worker-autotune.md

Key Features:
- Environment detection (CI vs local vs production)
- Workload type profiles (CPU-bound, I/O-bound, mixed)
- Auto-weight detection for pages based on content
- User config override support

Example:
    >>> from bengal.utils.concurrency.workers import get_optimal_workers, should_parallelize
    >>> if should_parallelize(len(pages), workload_type=WorkloadType.MIXED):
    ...     workers = get_optimal_workers(len(pages), workload_type=WorkloadType.MIXED)
    ...     with ThreadPoolExecutor(max_workers=workers) as executor:
    ...         results = list(executor.map(process, pages))

See Also:
- RFC: rfc-unified-worker-autotune.md for design rationale
- bengal/config/defaults.py for legacy get_max_workers (deprecated)

"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.core.page import Page


class WorkloadType(Enum):
    """Workload characteristics for auto-tuning.
    
    Different workload types have different optimal worker counts due to
    their resource usage patterns:
    
    Attributes:
        CPU_BOUND: CPU-intensive work (parsing, rendering, similarity).
            Limited by GIL in standard Python; benefits from few workers.
        IO_BOUND: I/O-intensive work (file stats, asset copying).
            Can use more workers as threads wait on I/O.
        MIXED: Combined I/O and CPU work (template rendering).
            Moderate worker counts work best.
        
    """

    CPU_BOUND = "cpu_bound"
    IO_BOUND = "io_bound"
    MIXED = "mixed"


class Environment(Enum):
    """Execution environment for tuning profiles.
    
    Different environments have different resource constraints:
    
    Attributes:
        CI: Constrained CI runner (typically 2-4 vCPU).
            Use minimal workers to avoid resource contention.
        LOCAL: Developer machine (typically 8-16 cores).
            Use moderate workers for good performance.
        PRODUCTION: Server deployment (16+ cores).
            Can use more workers for high throughput.
        
    """

    CI = "ci"
    LOCAL = "local"
    PRODUCTION = "production"


@dataclass(frozen=True)
class WorkloadProfile:
    """Tuning profile for a workload type.
    
    Attributes:
        parallel_threshold: Minimum tasks before parallelizing.
            Below this, thread overhead exceeds benefit.
        min_workers: Floor for worker count.
        max_workers: Ceiling for worker count.
        cpu_fraction: Fraction of cores to use (0.0-1.0).
        
    """

    parallel_threshold: int
    min_workers: int
    max_workers: int
    cpu_fraction: float


# Calibrated profiles per workload type and environment
# Based on benchmark data from rfc-benchmark-refresh-and-worker-optimization.md
_PROFILES: dict[tuple[WorkloadType, Environment], WorkloadProfile] = {
    # CPU-bound workloads (parsing, similarity, graph building)
    # Conservative because GIL limits parallelism
    (WorkloadType.CPU_BOUND, Environment.CI): WorkloadProfile(5, 2, 2, 1.0),
    (WorkloadType.CPU_BOUND, Environment.LOCAL): WorkloadProfile(5, 2, 4, 0.5),
    (WorkloadType.CPU_BOUND, Environment.PRODUCTION): WorkloadProfile(5, 2, 8, 0.5),
    # I/O-bound workloads (file stats, asset copying)
    # Can use more workers as they wait on I/O
    (WorkloadType.IO_BOUND, Environment.CI): WorkloadProfile(20, 2, 4, 1.0),
    (WorkloadType.IO_BOUND, Environment.LOCAL): WorkloadProfile(20, 2, 8, 0.75),
    (WorkloadType.IO_BOUND, Environment.PRODUCTION): WorkloadProfile(20, 2, 10, 0.75),
    # Mixed workloads (template rendering: I/O + CPU)
    # Balance between CPU and I/O constraints
    (WorkloadType.MIXED, Environment.CI): WorkloadProfile(5, 2, 2, 1.0),
    (WorkloadType.MIXED, Environment.LOCAL): WorkloadProfile(5, 2, 6, 0.5),
    (WorkloadType.MIXED, Environment.PRODUCTION): WorkloadProfile(5, 2, 10, 0.5),
}


def detect_environment() -> Environment:
    """
    Auto-detect execution environment for tuning.
    
    Detection order:
        1. Explicit BENGAL_ENV environment variable
        2. CI environment variables (GitHub Actions, GitLab CI, etc.)
        3. Default to LOCAL
    
    Returns:
        Detected Environment enum value
    
    Examples:
            >>> import os
            >>> os.environ["CI"] = "true"
            >>> detect_environment()
        <Environment.CI: 'ci'>
    
            >>> os.environ["BENGAL_ENV"] = "production"
            >>> detect_environment()
        <Environment.PRODUCTION: 'production'>
        
    """
    # Explicit override takes highest priority
    env_value = os.environ.get("BENGAL_ENV", "").lower()
    if env_value == "ci":
        return Environment.CI
    if env_value == "production":
        return Environment.PRODUCTION
    if env_value == "local":
        return Environment.LOCAL

    # CI detection (common CI environment variables)
    ci_indicators = [
        "CI",  # Generic CI
        "GITHUB_ACTIONS",  # GitHub Actions
        "GITLAB_CI",  # GitLab CI
        "CIRCLECI",  # CircleCI
        "TRAVIS",  # Travis CI
        "JENKINS_URL",  # Jenkins
        "BUILDKITE",  # Buildkite
        "CODEBUILD_BUILD_ID",  # AWS CodeBuild
        "AZURE_PIPELINES",  # Azure Pipelines
        "TF_BUILD",  # Azure DevOps
    ]
    for indicator in ci_indicators:
        if os.environ.get(indicator):
            return Environment.CI

    return Environment.LOCAL


def get_optimal_workers(
    task_count: int,
    *,
    workload_type: WorkloadType = WorkloadType.CPU_BOUND,
    environment: Environment | None = None,
    config_override: int | None = None,
    task_weight: float = 1.0,
) -> int:
    """
    Calculate optimal worker count based on workload characteristics.
    
    Auto-scales based on:
        - Workload type (CPU-bound vs I/O-bound)
        - Environment (CI vs local vs production)
        - Available CPU cores (fraction based on workload)
        - Task count (no point having more workers than tasks)
        - Optional task weight for heavy/light work estimation
    
    Args:
        task_count: Number of tasks to process
        workload_type: Type of work (CPU_BOUND, IO_BOUND, MIXED)
        environment: Execution environment (auto-detected if None)
        config_override: User-configured value (bypasses auto-tune if > 0)
        task_weight: Multiplier for task count (>1 for heavy tasks)
    
    Returns:
        Optimal number of worker threads (always >= 1)
    
    Examples:
            >>> get_optimal_workers(10, workload_type=WorkloadType.CPU_BOUND)
        2  # Conservative for CPU-bound on local
    
            >>> get_optimal_workers(100, workload_type=WorkloadType.IO_BOUND)
        6  # More workers for I/O
    
            >>> get_optimal_workers(5, config_override=16)
        16  # User override respected
    
            >>> import os
            >>> os.environ["CI"] = "true"
            >>> get_optimal_workers(100, workload_type=WorkloadType.MIXED)
        2  # CI mode caps at 2
        
    """
    # User override takes precedence
    if config_override is not None and config_override > 0:
        return config_override

    # Auto-detect environment if not specified
    if environment is None:
        environment = detect_environment()

    # Get profile for workload type + environment
    profile = _PROFILES[(workload_type, environment)]

    # Calculate CPU-based optimal
    cpu_count = os.cpu_count() or 2
    cpu_optimal = max(profile.min_workers, int(cpu_count * profile.cpu_fraction))
    cpu_optimal = min(cpu_optimal, profile.max_workers)

    # Adjust for task count (weighted)
    effective_tasks = int(task_count * task_weight)

    # Don't use more workers than tasks, but always at least 1
    return min(cpu_optimal, max(1, effective_tasks))


def should_parallelize(
    task_count: int,
    *,
    workload_type: WorkloadType = WorkloadType.CPU_BOUND,
    environment: Environment | None = None,
    total_work_estimate: int | None = None,
) -> bool:
    """
    Determine if parallelization is worthwhile for this workload.
    
    Thread pool overhead (~1-2ms per task) only pays off above threshold.
    This function helps avoid the overhead for small workloads.
    
    Args:
        task_count: Number of tasks to process
        workload_type: Type of work
        environment: Execution environment (auto-detected if None)
        total_work_estimate: Optional size estimate (bytes for parsing, etc.)
    
    Returns:
        True if parallelization is recommended
    
    Examples:
            >>> should_parallelize(3, workload_type=WorkloadType.CPU_BOUND)
        False  # Below threshold
    
            >>> should_parallelize(10, workload_type=WorkloadType.CPU_BOUND)
        True  # Above threshold
    
            >>> should_parallelize(100, total_work_estimate=1000)
        False  # Work estimate too small (< 5KB)
        
    """
    if environment is None:
        environment = detect_environment()

    profile = _PROFILES[(workload_type, environment)]

    # Fast path: below task threshold
    if task_count < profile.parallel_threshold:
        return False

    # Optional: check work size estimate (like patitas does)
    # 5KB is the threshold where thread overhead pays off
    return not (total_work_estimate is not None and total_work_estimate < 5000)


def estimate_page_weight(page: Page) -> float:
    """
    Estimate relative complexity of a page for worker scheduling.
    
    Heavy pages (autodoc, many code blocks) get higher weights,
    causing them to be scheduled earlier to avoid straggler effect.
    
    Weight factors:
        - Content size: +0.5 per 10KB above 10KB threshold
        - Code blocks: +0.1 per block above 5
        - Directives: +0.05 per directive above 10
        - Autodoc flag: +1.0 bonus
    
    Args:
        page: Page instance to estimate
    
    Returns:
        Weight multiplier (1.0 = average, >1 = heavy, <1 = light).
        Capped at 5.0 to avoid outlier distortion.
    
    Examples:
            >>> estimate_page_weight(simple_page)
        1.0
    
            >>> estimate_page_weight(autodoc_page)
        2.5  # Autodoc bonus + code blocks
        
    """
    weight = 1.0
    content = page.raw_content
    content_len = len(content)

    # Size factor (logarithmic, >10KB starts adding weight)
    if content_len > 10000:
        weight += (content_len - 10000) / 20000  # +0.5 per 10KB above threshold

    # Code block factor (each adds ~50ms render time)
    code_blocks = content.count("```")
    if code_blocks > 5:
        weight += (code_blocks - 5) * 0.1  # +0.1 per block above 5

    # Directive factor (custom directives are expensive)
    directives = content.count("::")
    if directives > 10:
        weight += (directives - 10) * 0.05  # +0.05 per directive above 10

    # Autodoc pages are consistently heavy
    if page.metadata.get("is_autodoc") or page.metadata.get("autodoc"):
        weight += 1.0

    return min(weight, 5.0)  # Cap at 5x to avoid outlier distortion


def order_by_complexity(pages: list[Page], *, descending: bool = True) -> list[Page]:
    """
    Order pages by estimated complexity for optimal worker utilization.
    
    Scheduling heavy pages first reduces the "straggler effect" where
    one slow page delays overall completion. This is a common optimization
    for parallel workloads with variable task sizes.
    
    Args:
        pages: List of pages to order
        descending: If True, heaviest first (default for parallel execution)
    
    Returns:
        Sorted list of pages (new list, does not mutate input)
    
    Examples:
            >>> ordered = order_by_complexity(pages)
            >>> # Heavy autodoc pages now at front
    
            >>> ordered = order_by_complexity(pages, descending=False)
            >>> # Light pages first (for testing/debugging)
        
    """
    return sorted(
        pages,
        key=estimate_page_weight,
        reverse=descending,
    )


def get_profile(
    workload_type: WorkloadType,
    environment: Environment | None = None,
) -> WorkloadProfile:
    """
    Get the workload profile for inspection or testing.
    
    Args:
        workload_type: Type of work
        environment: Execution environment (auto-detected if None)
    
    Returns:
        WorkloadProfile with threshold and worker settings
    
    Examples:
            >>> profile = get_profile(WorkloadType.CPU_BOUND)
            >>> profile.parallel_threshold
        5
            >>> profile.max_workers
        4
        
    """
    if environment is None:
        environment = detect_environment()
    return _PROFILES[(workload_type, environment)]
