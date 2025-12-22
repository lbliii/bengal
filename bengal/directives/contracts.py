"""Directive contract system for nesting validation.

This module provides ``DirectiveContract`` to define valid parent-child
relationships between directives. Contracts are validated at parse time,
catching invalid nesting early with helpful warnings rather than producing
silent failures or broken HTML.

Key Classes:
    - ``DirectiveContract``: Define valid nesting relationships.
    - ``ContractViolation``: Represent a detected validation issue.
    - ``ContractValidator``: Validate directives against contracts.

Pre-defined Contracts:
    - ``STEPS_CONTRACT``, ``STEP_CONTRACT``: Steps container validation.
    - ``TAB_SET_CONTRACT``, ``TAB_ITEM_CONTRACT``: Tabs validation.
    - ``CARDS_CONTRACT``, ``CARD_CONTRACT``: Cards container validation.
    - ``CODE_TABS_CONTRACT``: Code tabs validation.

Example:
    Define a directive that must be inside a parent::

        class StepDirective(BengalDirective):
            CONTRACT = DirectiveContract(requires_parent=("steps",))

    Invalid usage produces a warning at parse time::

        :::{step}
        Orphaned step - not inside :::{steps}
        :::
        # Warning: step must be inside ['steps'], found: (root)

Architecture:
    Contracts are defined as ``CONTRACT`` class attributes on
    ``BengalDirective`` subclasses. The base class validates contracts
    automatically during ``parse()``, emitting structured warnings
    via the logger for violations.

See Also:
    - ``bengal.directives.base``: ``BengalDirective`` validates contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bengal.errors import BengalRenderingError


@dataclass(frozen=True)
class DirectiveContract:
    """Define valid nesting relationships for a directive.

    Contracts specify which parent directives are allowed, which children
    are required, and constraints on child types and counts. Invalid
    nesting is detected at parse time with helpful warning messages.

    Attributes:
        requires_parent: Tuple of allowed parent directive types. The directive
            must be nested inside one of these. Empty tuple means root-level is OK.
        requires_children: Tuple of required child directive types. At least one
            child of these types must be present. Empty tuple means no requirement.
        min_children: Minimum count of ``requires_children`` types required.
        max_children: Maximum total children allowed (0 means unlimited).
        allowed_children: Whitelist of allowed child types. Empty tuple allows any.
        disallowed_children: Blacklist of forbidden child types. Takes precedence
            over ``allowed_children``.

    Example:
        Child directive that must be inside a parent::

            CONTRACT = DirectiveContract(
                requires_parent=("steps",),
            )

        Parent directive that must contain specific children::

            CONTRACT = DirectiveContract(
                requires_children=("step",),
                min_children=1,
                allowed_children=("step", "blank_line"),
            )

        Tabs with required items::

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
        """Validate contract configuration on initialization.

        Raises:
            BengalRenderingError: If ``min_children`` or ``max_children`` is negative.
        """
        if self.min_children < 0:
            raise BengalRenderingError(
                "min_children must be >= 0",
                suggestion="Set min_children to 0 or greater in directive contract",
            )
        if self.max_children < 0:
            raise BengalRenderingError(
                "max_children must be >= 0",
                suggestion="Set max_children to 0 or greater in directive contract",
            )

    @property
    def has_parent_requirement(self) -> bool:
        """Return ``True`` if this contract specifies a required parent."""
        return len(self.requires_parent) > 0

    @property
    def has_child_requirement(self) -> bool:
        """Return ``True`` if this contract specifies child requirements."""
        return len(self.requires_children) > 0 or self.min_children > 0


@dataclass
class ContractViolation:
    """Represent a contract violation detected during parsing.

    Violations capture details about invalid nesting for:
        - Logging as warnings (default behavior)
        - Raising as errors (strict mode)
        - Reporting in health checks

    Attributes:
        directive: The directive type that was validated (e.g., ``"step"``).
        violation_type: Type identifier for structured logging (e.g.,
            ``"directive_invalid_parent"``).
        message: Human-readable description of the violation.
        expected: What was expected (list of types, count, or description).
        found: What was actually found (type name, list, or count).
        location: Source file location (e.g., ``"content/guide.md"``).
    """

    directive: str
    violation_type: str  # "invalid_parent", "missing_children", etc.
    message: str
    expected: list[str] | int | None = None
    found: list[str] | str | int | None = None
    location: str | None = None

    def to_log_dict(self) -> dict[str, Any]:
        """Convert the violation to a structured logging dictionary.

        Creates a dict suitable for passing as kwargs to ``logger.warning()``.
        Uses ``"detail"`` instead of ``"message"`` to avoid conflict with
        BengalLogger's positional message argument.

        Returns:
            Dictionary with ``directive``, ``violation``, ``detail``, and
            optionally ``expected``, ``found``, ``location``.
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
    """Validate directive nesting against contracts.

    Provides static methods for validating parent context and child
    requirements. Used by ``BengalDirective.parse()`` to enforce
    contracts during markdown parsing.

    Validation Checks:
        1. **Parent validation**: Verify the directive is inside an allowed parent.
        2. **Required children**: Verify required child types are present.
        3. **Child count**: Verify ``min_children`` and ``max_children`` constraints.
        4. **Allowed children**: Verify children are in the whitelist (if specified).
        5. **Disallowed children**: Verify no blacklisted children are present.

    Example:
        Using the validator in a directive's parse method::

            def parse(self, block, m, state):
                # Validate parent context
                if self.CONTRACT and self.CONTRACT.has_parent_requirement:
                    parent_type = self._get_parent_directive_type(state)
                    violations = ContractValidator.validate_parent(
                        self.CONTRACT, self.TOKEN_TYPE, parent_type
                    )
                    for v in violations:
                        self.logger.warning(v.violation_type, **v.to_log_dict())

                # ... parse children ...

                # Validate children
                if self.CONTRACT and self.CONTRACT.has_child_requirement:
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
        """Validate that the directive is inside an allowed parent.

        Args:
            contract: The directive's contract specifying ``requires_parent``.
            directive_type: The directive being validated (e.g., ``"step"``).
            parent_type: The parent directive type, or ``None`` if at document root.
            location: Source file path for error messages.

        Returns:
            List of ``ContractViolation`` objects (empty if valid).
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
        """Validate that children meet contract requirements.

        Checks required children, child counts, and allowed/disallowed types.

        Args:
            contract: The directive's contract specifying child requirements.
            directive_type: The directive being validated (e.g., ``"steps"``).
            children: List of parsed child tokens as dictionaries.
            location: Source file path for error messages.

        Returns:
            List of ``ContractViolation`` objects (empty if all valid).
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
