"""Nesting validation contracts for directives.

Contracts define valid nesting relationships between directives,
catching structural errors at parse time rather than runtime.

Thread Safety:
Contract is frozen (immutable). Safe to share across threads.

Example:
    >>> STEPS_CONTRACT = DirectiveContract(
    ...     requires_children=("step",),
    ...     allows_children=("step",),
    ... )
    >>> STEP_CONTRACT = DirectiveContract(
    ...     requires_parent=("steps",),
    ... )

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from patitas.nodes import Directive


@dataclass(frozen=True, slots=True)
class DirectiveContract:
    """Validation rules for directive nesting.

    Use contracts to enforce structural requirements like "step must
    be inside steps" or "tab-item can only contain certain content".

    Violations emit warnings rather than raising exceptions, allowing
    graceful degradation of invalid markup.

    Attributes:
        requires_parent: This directive must be inside one of these parents.
        requires_children: This directive must contain at least one of these.
        allows_children: Only these child directive types are allowed.
        max_children: Maximum number of children allowed.
        forbids_children: These directive types are forbidden as children.

    Example:
            >>> # tab-item must be inside tab-set
            >>> TAB_ITEM_CONTRACT = DirectiveContract(
            ...     requires_parent=("tab-set",),
            ... )
            >>>
            >>> # tab-set must contain tab-item children
            >>> TAB_SET_CONTRACT = DirectiveContract(
            ...     requires_children=("tab-item",),
            ...     allows_children=("tab-item",),
            ... )

    """

    requires_parent: tuple[str, ...] | None = None
    """This directive must be inside one of these parent directives.
    Violations are considered errors in strict mode."""

    allows_parent: tuple[str, ...] | None = None
    """This directive is intended to be inside one of these parents.
    Violations are always just warnings."""

    requires_children: tuple[str, ...] | None = None
    """This directive must contain at least one of these child directives."""

    allows_children: tuple[str, ...] | None = None
    """Only these child directive types are allowed (None = any allowed)."""

    max_children: int | None = None
    """Maximum number of children allowed (None = unlimited)."""

    forbids_children: tuple[str, ...] | None = None
    """These directive types are forbidden as children."""

    @property
    def has_parent_requirement(self) -> bool:
        """Check if this contract has parent requirements."""
        return self.requires_parent is not None

    @property
    def has_child_requirement(self) -> bool:
        """Check if this contract has child requirements."""
        return (
            self.requires_children is not None
            or self.allows_children is not None
            or self.forbids_children is not None
        )

    def validate_parent(
        self,
        directive_name: str,
        parent_name: str | None,
    ) -> ContractViolation | None:
        """Validate that directive has required or allowed parent.

        Args:
            directive_name: Name of the directive being validated
            parent_name: Name of parent directive (None if no parent)

        Returns:
            ContractViolation if invalid, None if valid
        """
        # 1. Check strict requirements
        if self.requires_parent is not None:
            if parent_name is None:
                return ContractViolation(
                    directive=directive_name,
                    violation_type="missing_parent",
                    message=f"'{directive_name}' must be inside: {', '.join(self.requires_parent)}",
                    expected=self.requires_parent,
                    actual=None,
                )

            if parent_name not in self.requires_parent:
                return ContractViolation(
                    directive=directive_name,
                    violation_type="wrong_parent",
                    message=f"'{directive_name}' must be inside {', '.join(self.requires_parent)}, not '{parent_name}'",
                    expected=self.requires_parent,
                    actual=parent_name,
                )

        # 2. Check soft suggestions
        if self.allows_parent is not None and (
            parent_name is None or parent_name not in self.allows_parent
        ):
            return ContractViolation(
                directive=directive_name,
                violation_type="suggested_parent",
                message=f"'{directive_name}' is intended to be inside: {', '.join(self.allows_parent)}",
                expected=self.allows_parent,
                actual=parent_name,
            )

        return None

    def validate_children(
        self,
        directive_name: str,
        children: Sequence[Directive],
    ) -> list[ContractViolation]:
        """Validate directive children against contract.

        Args:
            directive_name: Name of the directive being validated
            children: Sequence of child Directive nodes

        Returns:
            List of violations (empty if valid)
        """
        violations: list[ContractViolation] = []

        # Get child directive names
        child_names = [c.name for c in children if hasattr(c, "name")]

        # Check requires_children
        if self.requires_children is not None:
            has_required = any(name in self.requires_children for name in child_names)
            if not has_required and children:
                violations.append(
                    ContractViolation(
                        directive=directive_name,
                        violation_type="missing_required_child",
                        message=f"'{directive_name}' requires at least one of: {', '.join(self.requires_children)}",
                        expected=self.requires_children,
                        actual=tuple(child_names),
                    )
                )

        # Check allows_children
        if self.allows_children is not None:
            for name in child_names:
                if name not in self.allows_children:
                    violations.append(
                        ContractViolation(
                            directive=directive_name,
                            violation_type="forbidden_child",
                            message=f"'{name}' is not allowed inside '{directive_name}'",
                            expected=self.allows_children,
                            actual=name,
                        )
                    )

        # Check forbids_children
        if self.forbids_children is not None:
            for name in child_names:
                if name in self.forbids_children:
                    violations.append(
                        ContractViolation(
                            directive=directive_name,
                            violation_type="forbidden_child",
                            message=f"'{name}' is forbidden inside '{directive_name}'",
                            expected=None,
                            actual=name,
                        )
                    )

        # Check max_children
        if self.max_children is not None and len(children) > self.max_children:
            violations.append(
                ContractViolation(
                    directive=directive_name,
                    violation_type="too_many_children",
                    message=f"'{directive_name}' allows max {self.max_children} children, got {len(children)}",
                    expected=self.max_children,
                    actual=len(children),
                )
            )

        return violations


@dataclass(frozen=True, slots=True)
class ContractViolation:
    """Record of a contract violation.

    Contains information about what went wrong and suggestions for fixes.

    """

    directive: str
    """Name of the directive that violated the contract."""

    violation_type: str
    """Type of violation: missing_parent, wrong_parent, missing_required_child, etc."""

    message: str
    """Human-readable error message."""

    expected: tuple[str, ...] | str | int | None
    """What was expected."""

    actual: tuple[str, ...] | str | int | None
    """What was found."""

    @property
    def suggestion(self) -> str | None:
        """Generate a fix suggestion based on violation type."""
        if self.violation_type == "missing_parent" and isinstance(self.expected, tuple):
            parent = self.expected[0]
            return f"Wrap '{self.directive}' inside a ':::{{{parent}}}' block"

        if self.violation_type == "missing_required_child" and isinstance(self.expected, tuple):
            child = self.expected[0]
            return f"Add at least one ':::{{{child}}}' inside '{self.directive}'"

        return None


# =============================================================================
# Pre-defined contracts for common patterns
# =============================================================================

# Steps container must have step children
STEPS_CONTRACT = DirectiveContract(
    allows_children=("step",),
)

# Step must be inside steps
STEP_CONTRACT = DirectiveContract(
    allows_parent=("steps",),
)

# Tab container must have tab-item children
TAB_SET_CONTRACT = DirectiveContract(
    allows_children=("tab-item", "tab"),
)

# Tab item must be inside tab-set
TAB_ITEM_CONTRACT = DirectiveContract(
    requires_parent=("tab-set", "tabs"),
)

# Dropdown has no restrictions
DROPDOWN_CONTRACT = DirectiveContract()

# Grid/card layouts
GRID_CONTRACT = DirectiveContract(
    requires_children=("grid-item", "card"),
)

GRID_ITEM_CONTRACT = DirectiveContract(
    requires_parent=("grid",),
)

# Cards grid container
CARDS_CONTRACT = DirectiveContract(
    # Cards can contain card children (but not required - could be empty)
    allows_children=("card",),
)

# Individual card
CARD_CONTRACT = DirectiveContract(
    # Card can be inside cards grid, but also allowed standalone
    requires_parent=None,
)

# Definition list
DEFINITION_LIST_CONTRACT = DirectiveContract(
    requires_children=("definition",),
    allows_children=("definition",),
)

DEFINITION_CONTRACT = DirectiveContract(
    requires_parent=("definition-list",),
)
