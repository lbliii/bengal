"""Immutable build state for sharing across build phases.

Provides BuildState frozen dataclass for passing immutable build configuration
between phases. Lower-layer modules can import this without depending on
orchestration.

This module was created to fix layer violations where lower layers
(discovery, rendering, postprocess) were importing BuildContext from
orchestration. BuildState contains only the immutable configuration
that doesn't change during a build.

Related Modules:
- bengal.orchestration.build_context: Full BuildContext with mutable state
- bengal.orchestration.build: Build orchestration using BuildContext

See Also:
- plan/rfc-remaining-coupling-fixes.md: Architecture decision documentation

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass(frozen=True)
class BuildState:
    """
    Immutable build configuration passed across build phases.

    This is a frozen dataclass containing only the configuration values
    that don't change during a build. Lower-layer modules can depend on
    this instead of the full BuildContext.

    The full BuildContext wraps BuildState and adds mutable tracking state.

    Attributes:
        parallel: Whether to use parallel processing
        incremental: Whether this is an incremental build
        strict: Whether to fail on warnings
        verbose: Whether to show verbose output
        quiet: Whether to suppress output
        memory_optimized: Whether to optimize for memory usage
        full_output: Whether to produce full output
        profile: Build profile name (Writer, Theme-Dev, Developer)
        profile_templates: Whether to profile template rendering

    Example:
        # Lower-layer module can use BuildState
        def process_content(state: BuildState) -> None:
            if state.parallel:
                use_threadpool()
            if state.strict:
                fail_on_warning()

    Relationships:
        - Used by: discovery, rendering, postprocess modules
        - Wrapped by: orchestration.build_context.BuildContext

    """

    parallel: bool = True
    incremental: bool = False
    strict: bool = False
    verbose: bool = False
    quiet: bool = False
    memory_optimized: bool = False
    full_output: bool = False
    profile: str | None = None
    profile_templates: bool = False

    def __post_init__(self) -> None:
        """Validate state after creation."""
        # Frozen dataclass, so no modifications allowed after creation

    @classmethod
    def from_build_options(
        cls,
        parallel: bool = True,
        incremental: bool = False,
        strict: bool = False,
        verbose: bool = False,
        quiet: bool = False,
        memory_optimized: bool = False,
        full_output: bool = False,
        profile: str | None = None,
        profile_templates: bool = False,
    ) -> BuildState:
        """Create BuildState from build options.

        Convenience factory method for creating BuildState from
        individual options.

        Args:
            parallel: Whether to use parallel processing
            incremental: Whether this is an incremental build
            strict: Whether to fail on warnings
            verbose: Whether to show verbose output
            quiet: Whether to suppress output
            memory_optimized: Whether to optimize for memory usage
            full_output: Whether to produce full output
            profile: Build profile name
            profile_templates: Whether to profile template rendering

        Returns:
            BuildState instance
        """
        return cls(
            parallel=parallel,
            incremental=incremental,
            strict=strict,
            verbose=verbose,
            quiet=quiet,
            memory_optimized=memory_optimized,
            full_output=full_output,
            profile=profile,
            profile_templates=profile_templates,
        )
