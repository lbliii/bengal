"""Kida AST Optimization Pass.

Pure-Python AST optimizations applied before compilation to Python AST.
Achieves 10-30% faster rendering without external dependencies.

Optimizations:
    - **Constant Folding**: Evaluate constant expressions at compile time
    - **Dead Code Elimination**: Remove statically unreachable code
    - **Data Coalescing**: Merge adjacent Data nodes to reduce _append() calls
    - **Filter Inlining**: Inline simple pure filters as direct method calls
    - **Buffer Estimation**: Estimate output size for pre-allocation

Thread-Safety:
    All optimizers are stateless and create new nodes, never mutating.
    Safe for concurrent use.

Example:
    >>> from bengal.rendering.kida.optimizer import ASTOptimizer, OptimizationConfig
    >>>
    >>> optimizer = ASTOptimizer()
    >>> result = optimizer.optimize(ast)
    >>>
    >>> print(result.stats.summary())
    "3 constants folded; 1 dead blocks removed; 5 data nodes merged"

    >>> optimized_ast = result.ast
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

    All optimizations are enabled by default except filter_inlining,
    which is disabled because users can override built-in filters.
    Disable individual passes for debugging or when a specific
    optimization causes issues.
    """

    constant_folding: bool = True
    dead_code_elimination: bool = True
    data_coalescing: bool = True
    # Filter inlining is disabled by default because it bypasses the
    # filter registry, preventing user overrides of built-in filters
    filter_inlining: bool = False
    estimate_buffer: bool = True


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

        # Initialize passes
        self._constant_folder = ConstantFolder()
        self._dead_code_eliminator = DeadCodeEliminator()
        self._data_coalescer = DataCoalescer()
        self._filter_inliner = FilterInliner()
        self._buffer_estimator = BufferEstimator()

    def optimize(self, ast: Template) -> OptimizationResult:
        """Apply all enabled optimization passes.

        Pass order:
            1. Constant folding (enables dead code detection)
            2. Dead code elimination (reduces AST size)
            3. Data coalescing (merges adjacent static content)
            4. Filter inlining (simplifies filter calls)
            5. Buffer estimation (calculates pre-allocation size)
        """
        stats = OptimizationStats()

        # Pass 1: Constant folding
        if self._config.constant_folding:
            ast, count = self._constant_folder.fold(ast)
            stats.constants_folded = count
            stats.passes_applied.append("constant_folding")

        # Pass 2: Dead code elimination
        if self._config.dead_code_elimination:
            ast, count = self._dead_code_eliminator.eliminate(ast)
            stats.dead_blocks_removed = count
            stats.passes_applied.append("dead_code_elimination")

        # Pass 3: Data coalescing
        if self._config.data_coalescing:
            ast, count = self._data_coalescer.coalesce(ast)
            stats.data_nodes_coalesced = count
            stats.passes_applied.append("data_coalescing")

        # Pass 4: Filter inlining
        if self._config.filter_inlining:
            ast, count = self._filter_inliner.inline(ast)
            stats.filters_inlined = count
            stats.passes_applied.append("filter_inlining")

        # Pass 5: Buffer estimation
        if self._config.estimate_buffer:
            stats.estimated_buffer_size = self._buffer_estimator.estimate(ast)
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
