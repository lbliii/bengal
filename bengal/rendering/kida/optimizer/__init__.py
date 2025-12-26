"""Kida AST Optimization Pass.

Pure-Python AST optimizations applied before compilation to Python AST.

Default Behavior:
    **All optimizations are disabled by default.** Benchmarks show that
    optimization overhead exceeds render savings for single-render builds
    (static site generation).

    For multi-render scenarios (dev server with hot reload), enable
    optimizations with `OptimizationConfig.all_enabled()` to amortize
    the compile-time cost across multiple renders.

Available Optimizations:
    - **Data Coalescing**: Merge adjacent Data nodes
    - **Constant Folding**: Evaluate constant expressions at compile time
    - **Dead Code Elimination**: Remove statically unreachable code
    - **Filter Inlining**: Inline simple pure filters as direct method calls
    - **Buffer Estimation**: Estimate output size (informational only)

Thread-Safety:
    All optimizers are stateless and create new nodes, never mutating.
    Safe for concurrent use.

Example:
    >>> from bengal.rendering.kida.optimizer import ASTOptimizer, OptimizationConfig
    >>>
    >>> # Default: no optimizations (fastest for single-render builds)
    >>> optimizer = ASTOptimizer()
    >>> result = optimizer.optimize(ast)
    >>>
    >>> # Enable all optimizations for dev server (renders many times):
    >>> config = OptimizationConfig.all_enabled()
    >>> optimizer = ASTOptimizer(config)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bengal.rendering.kida.optimizer.buffer_estimator import BufferEstimator
from bengal.rendering.kida.optimizer.constant_folder import ConstantFolder
from bengal.rendering.kida.optimizer.data_coalescer import DataCoalescer
from bengal.rendering.kida.optimizer.dead_code_eliminator import DeadCodeEliminator
from bengal.rendering.kida.optimizer.filter_inliner import FilterInliner

if TYPE_CHECKING:
    from bengal.rendering.kida.nodes import Template


@dataclass
class OptimizationConfig:
    """Configuration for AST optimization passes.

    By default, **all optimizations are disabled**. Benchmarks show that
    optimization overhead exceeds render savings for single-render builds.

    For multi-render scenarios (dev server with hot reload), use
    `OptimizationConfig.all_enabled()` to amortize compile-time cost.
    """

    # Data coalescing: merge adjacent static strings to reduce _append() calls.
    data_coalescing: bool = False

    # Constant folding: evaluate constant expressions at compile time.
    constant_folding: bool = False

    # Dead code elimination: remove unreachable branches.
    dead_code_elimination: bool = False

    # Filter inlining: inline pure filters as direct method calls.
    filter_inlining: bool = False

    # Buffer estimation: calculate output size stats (informational only).
    estimate_buffer: bool = False

    @classmethod
    def all_enabled(cls) -> OptimizationConfig:
        """Enable all optimizations (for dev server/multi-render scenarios)."""
        return cls(
            data_coalescing=True,
            constant_folding=True,
            dead_code_elimination=True,
            filter_inlining=True,
            estimate_buffer=True,
        )


@dataclass
class OptimizationStats:
    """Statistics from optimization passes.

    Used for debugging and observability.
    """

    constants_folded: int = 0
    dead_blocks_removed: int = 0
    data_nodes_coalesced: int = 0
    filters_inlined: int = 0
    estimated_buffer_size: int = 256
    estimated_output_count: int = 0
    passes_applied: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Human-readable summary of optimizations applied."""
        parts = []
        if self.constants_folded:
            parts.append(f"{self.constants_folded} constants folded")
        if self.dead_blocks_removed:
            parts.append(f"{self.dead_blocks_removed} dead blocks removed")
        if self.data_nodes_coalesced:
            parts.append(f"{self.data_nodes_coalesced} data nodes merged")
        if self.filters_inlined:
            parts.append(f"{self.filters_inlined} filters inlined")
        return "; ".join(parts) if parts else "no optimizations applied"


@dataclass
class OptimizationResult:
    """Result of optimization pass."""

    ast: Template
    stats: OptimizationStats = field(default_factory=OptimizationStats)


class ASTOptimizer:
    """Unified AST optimization pass.

    Applies a sequence of pure-Python optimizations to the Kida AST
    before compilation to Python AST.

    Thread-safe: Stateless, creates new nodes.

    Example:
        >>> optimizer = ASTOptimizer()
        >>> result = optimizer.optimize(ast)
        >>> optimized_ast = result.ast
        >>> buffer_size = result.stats.estimated_buffer_size
    """

    def __init__(self, config: OptimizationConfig | None = None):
        self._config = config or OptimizationConfig()

        # Lazy-init passes only when enabled
        self._constant_folder: ConstantFolder | None = None
        self._dead_code_eliminator: DeadCodeEliminator | None = None
        self._data_coalescer: DataCoalescer | None = None
        self._filter_inliner: FilterInliner | None = None
        self._buffer_estimator: BufferEstimator | None = None

    def _any_enabled(self) -> bool:
        """Check if any optimization pass is enabled."""
        c = self._config
        return (
            c.constant_folding
            or c.dead_code_elimination
            or c.data_coalescing
            or c.filter_inlining
            or c.estimate_buffer
        )

    def optimize(self, ast: Template) -> OptimizationResult:
        """Apply all enabled optimization passes.

        Pass order:
            1. Constant folding (enables dead code detection)
            2. Dead code elimination (reduces AST size)
            3. Data coalescing (merges adjacent static content)
            4. Filter inlining (simplifies filter calls)
            5. Buffer estimation (informational only)

        Returns:
            OptimizationResult with (possibly unchanged) AST and stats.
        """
        # Fast path: skip if no optimizations enabled
        if not self._any_enabled():
            return OptimizationResult(ast=ast, stats=OptimizationStats())

        stats = OptimizationStats()

        # Pass 1: Constant folding
        if self._config.constant_folding:
            if self._constant_folder is None:
                self._constant_folder = ConstantFolder()
            ast, count = self._constant_folder.fold(ast)
            stats.constants_folded = count
            stats.passes_applied.append("constant_folding")

        # Pass 2: Dead code elimination
        if self._config.dead_code_elimination:
            if self._dead_code_eliminator is None:
                self._dead_code_eliminator = DeadCodeEliminator()
            ast, count = self._dead_code_eliminator.eliminate(ast)
            stats.dead_blocks_removed = count
            stats.passes_applied.append("dead_code_elimination")

        # Pass 3: Data coalescing
        if self._config.data_coalescing:
            if self._data_coalescer is None:
                self._data_coalescer = DataCoalescer()
            ast, count = self._data_coalescer.coalesce(ast)
            stats.data_nodes_coalesced = count
            stats.passes_applied.append("data_coalescing")

        # Pass 4: Filter inlining
        if self._config.filter_inlining:
            if self._filter_inliner is None:
                self._filter_inliner = FilterInliner()
            ast, count = self._filter_inliner.inline(ast)
            stats.filters_inlined = count
            stats.passes_applied.append("filter_inlining")

        # Pass 5: Buffer estimation
        if self._config.estimate_buffer:
            if self._buffer_estimator is None:
                self._buffer_estimator = BufferEstimator()
            stats.estimated_buffer_size = self._buffer_estimator.estimate(ast)
            stats.estimated_output_count = self._buffer_estimator.count_output_operations(ast)
            stats.passes_applied.append("buffer_estimation")

        return OptimizationResult(ast=ast, stats=stats)


__all__ = [
    "ASTOptimizer",
    "OptimizationConfig",
    "OptimizationResult",
    "OptimizationStats",
    "ConstantFolder",
    "DeadCodeEliminator",
    "DataCoalescer",
    "FilterInliner",
    "BufferEstimator",
]
