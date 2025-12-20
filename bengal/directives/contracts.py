"""
Directive contract system for nesting validation.

Provides DirectiveContract to define valid parent-child relationships
between directives, catching invalid nesting at parse time rather than
producing silent failures or broken HTML.

Architecture:
    Contracts are defined as class-level constants on BengalDirective
    subclasses. The base class validates contracts automatically during
    parsing, emitting warnings for violations.

Related:
    - bengal/directives/base.py: BengalDirective validates contracts

Example:

```python
class StepDirective(BengalDirective):
    CONTRACT = DirectiveContract(requires_parent=("steps",))

# This produces a warning at parse time:
# :::{step}
# Orphaned step - not inside :::{steps}
# :::
```
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DirectiveContract:
    """
    Defines valid nesting relationships for a directive.

    This is the KEY FEATURE that solves the nested directive validation problem.
    Contracts are checked at parse time to catch invalid nesting early.

    Attributes:
        requires_parent: This directive MUST be inside one of these parent types.
                        Empty tuple means can appear anywhere (root-level OK).

        requires_children: This directive MUST contain at least one of these types.
                          Empty tuple means no required children.

        allowed_children: Only these child types are allowed (whitelist).
                         Empty tuple means any children allowed.

        disallowed_children: These child types are NOT allowed (blacklist).
                            Takes precedence over allowed_children.

        min_children: Minimum count of required_children types.

        max_children: Maximum children (0 = unlimited).

    Example - StepDirective (must be inside steps):
        CONTRACT = DirectiveContract(
            requires_parent=("steps",),
        )

    Example - StepsDirective (must contain steps):
        CONTRACT = DirectiveContract(
            requires_children=("step",),
            min_children=1,
            allowed_children=("step",),
        )

    Example - TabSetDirective (tabs with items):
        CONTRACT = DirectiveContract(
            requires_children=("tab_item",),
            min_children=1,
        )
    """

    # Parent requirements
    requires_parent: tuple[str, ...] = ()

    # Child requirements
    requires_children: tuple[str, ...] = ()
    min_children: int = 0
    max_children: int = 0  # 0 = unlimited

    # Child filtering
    allowed_children: tuple[str, ...] = ()  # Empty = allow all
    disallowed_children: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate contract configuration."""
        if self.min_children < 0:
            raise ValueError("min_children must be >= 0")
        if self.max_children < 0:
            raise ValueError("max_children must be >= 0")

    @property
    def has_parent_requirement(self) -> bool:
        """True if this directive requires a specific parent."""
        return len(self.requires_parent) > 0

    @property
    def has_child_requirement(self) -> bool:
        """True if this directive requires specific children."""
        return len(self.requires_children) > 0 or self.min_children > 0


@dataclass
class ContractViolation:
    """
    Represents a contract violation found during parsing.

    Collected violations can be:
    - Logged as warnings (default)
    - Raised as errors (strict mode)
    - Reported in health checks

    Attributes:
        directive: The directive type that was validated
        violation_type: Type of violation (for structured logging)
        message: Human-readable description
        expected: What was expected (list, int, or description)
        found: What was actually found
        location: Source location (e.g., "content/guide.md:45")
    """

    directive: str
    violation_type: str  # "invalid_parent", "missing_children", etc.
    message: str
    expected: list[str] | int | None = None
    found: list[str] | str | int | None = None
    location: str | None = None

    def to_log_dict(self) -> dict[str, Any]:
        """
        Convert to structured log format.

        Note: Uses 'detail' instead of 'message' to avoid conflict
        with BengalLogger's positional 'message' argument.

        Returns:
            Dict suitable for structured logging kwargs
        """
        result: dict[str, Any] = {
            "directive": self.directive,
            "violation": self.violation_type,
            "detail": self.message,  # 'detail' not 'message' to avoid kwarg conflict
        }
        if self.expected is not None:
            result["expected"] = self.expected
        if self.found is not None:
            result["found"] = self.found
        if self.location:
            result["location"] = self.location
        return result


class ContractValidator:
    """
    Validates directive nesting against contracts.

    Used by BengalDirective.parse() to check:
    1. Parent context is valid (if requires_parent specified)
    2. Children meet requirements (if requires_children specified)
    3. Children types are allowed (if allowed_children specified)

    Example usage in BengalDirective:
        def parse(self, block, m, state):
            # ... parse content ...

            # Validate parent
            if self.CONTRACT:
                parent_type = self._get_parent_type(state)
                violations = ContractValidator.validate_parent(
                    self.CONTRACT, self.TOKEN_TYPE, parent_type
                )
                for v in violations:
                    self.logger.warning(v.violation_type, **v.to_log_dict())

            # ... parse children ...

            # Validate children
            if self.CONTRACT:
                violations = ContractValidator.validate_children(
                    self.CONTRACT, self.TOKEN_TYPE, children
                )
                for v in violations:
                    self.logger.warning(v.violation_type, **v.to_log_dict())
    """

    @staticmethod
    def validate_parent(
        contract: DirectiveContract,
        directive_type: str,
        parent_type: str | None,
        location: str | None = None,
    ) -> list[ContractViolation]:
        """
        Validate that the directive is inside a valid parent.

        Args:
            contract: The directive's contract
            directive_type: The directive being validated (e.g., "step")
            parent_type: The parent directive type (None if at root)
            location: Source location for error messages

        Returns:
            List of violations (empty if valid)
        """
        violations = []

        if contract.requires_parent and parent_type not in contract.requires_parent:
            violations.append(
                ContractViolation(
                    directive=directive_type,
                    violation_type="directive_invalid_parent",
                    message=(
                        f"{directive_type} must be inside {list(contract.requires_parent)}, "
                        f"found: {parent_type or '(root)'}"
                    ),
                    expected=list(contract.requires_parent),
                    found=parent_type or "(root)",
                    location=location,
                )
            )

        return violations

    @staticmethod
    def validate_children(
        contract: DirectiveContract,
        directive_type: str,
        children: list[dict[str, Any]],
        location: str | None = None,
    ) -> list[ContractViolation]:
        """
        Validate that children meet contract requirements.

        Args:
            contract: The directive's contract
            directive_type: The directive being validated (e.g., "steps")
            children: Parsed child tokens
            location: Source location for error messages

        Returns:
            List of violations (empty if valid)
        """
        violations = []

        # Extract child types
        child_types = [c.get("type") for c in children if isinstance(c, dict) and c.get("type")]

        # Check required children exist
        if contract.requires_children:
            required_found = [t for t in child_types if t in contract.requires_children]

            if not required_found:
                violations.append(
                    ContractViolation(
                        directive=directive_type,
                        violation_type="directive_missing_required_children",
                        message=(
                            f"{directive_type} requires at least one of "
                            f"{list(contract.requires_children)}"
                        ),
                        expected=list(contract.requires_children),
                        found=child_types,
                        location=location,
                    )
                )
            elif len(required_found) < contract.min_children:
                violations.append(
                    ContractViolation(
                        directive=directive_type,
                        violation_type="directive_insufficient_children",
                        message=(
                            f"{directive_type} requires at least {contract.min_children} "
                            f"{list(contract.requires_children)}, found {len(required_found)}"
                        ),
                        expected=contract.min_children,
                        found=len(required_found),
                        location=location,
                    )
                )

        # Check max children
        if contract.max_children > 0 and len(child_types) > contract.max_children:
            violations.append(
                ContractViolation(
                    directive=directive_type,
                    violation_type="directive_too_many_children",
                    message=(
                        f"{directive_type} allows max {contract.max_children} children, "
                        f"found {len(child_types)}"
                    ),
                    expected=contract.max_children,
                    found=len(child_types),
                    location=location,
                )
            )

        # Check allowed children (whitelist)
        if contract.allowed_children:
            invalid = [t for t in child_types if t and t not in contract.allowed_children]
            if invalid:
                violations.append(
                    ContractViolation(
                        directive=directive_type,
                        violation_type="directive_invalid_child_types",
                        message=f"{directive_type} does not allow children of type {invalid}",
                        expected=list(contract.allowed_children),
                        found=invalid,
                        location=location,
                    )
                )

        # Check disallowed children (blacklist)
        if contract.disallowed_children:
            invalid = [t for t in child_types if t in contract.disallowed_children]
            if invalid:
                violations.append(
                    ContractViolation(
                        directive=directive_type,
                        violation_type="directive_disallowed_child_types",
                        message=f"{directive_type} does not allow children of type {invalid}",
                        expected=f"not {list(contract.disallowed_children)}",
                        found=invalid,
                        location=location,
                    )
                )

        return violations


# =============================================================================
# Pre-defined Contracts for Bengal Directives
# =============================================================================

# Steps directives
# Note: blank_line is allowed for readability between steps
STEPS_CONTRACT = DirectiveContract(
    requires_children=("step",),
    min_children=1,
    allowed_children=("step", "blank_line"),
)

STEP_CONTRACT = DirectiveContract(
    requires_parent=("steps",),
)

# Tabs directives
TAB_SET_CONTRACT = DirectiveContract(
    requires_children=("tab_item",),
    min_children=1,
)

TAB_ITEM_CONTRACT = DirectiveContract(
    requires_parent=("tab_set",),
)

# Cards directives
# Note: blank_line allowed for readability between cards
CARDS_CONTRACT = DirectiveContract(
    # Cards can have card children, but they're optional (child-cards auto-generates)
    allowed_children=("card", "blank_line"),
)

CARD_CONTRACT = DirectiveContract(
    requires_parent=("cards_grid", "grid"),
)

# Code tabs
CODE_TABS_CONTRACT = DirectiveContract(
    # Requires code block children
    min_children=1,
)
