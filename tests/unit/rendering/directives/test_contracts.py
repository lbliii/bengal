"""
Tests for DirectiveContract validation system.

Tests contract definitions and ContractValidator for parent-child validation.
"""

from __future__ import annotations

import pytest

from bengal.rendering.plugins.directives import (
    CARD_CONTRACT,
    CARDS_CONTRACT,
    CODE_TABS_CONTRACT,
    ContractValidator,
    ContractViolation,
    DirectiveContract,
    STEP_CONTRACT,
    STEPS_CONTRACT,
    TAB_ITEM_CONTRACT,
    TAB_SET_CONTRACT,
)


# =============================================================================
# DirectiveContract Tests
# =============================================================================


class TestDirectiveContract:
    """Tests for DirectiveContract dataclass."""

    def test_basic_contract(self) -> None:
        """Test creating a basic contract."""
        contract = DirectiveContract(
            requires_parent=("steps",),
        )

        assert contract.requires_parent == ("steps",)
        assert contract.requires_children == ()
        assert contract.min_children == 0

    def test_contract_with_children(self) -> None:
        """Test contract with child requirements."""
        contract = DirectiveContract(
            requires_children=("step",),
            min_children=1,
            allowed_children=("step",),
        )

        assert contract.requires_children == ("step",)
        assert contract.min_children == 1
        assert contract.allowed_children == ("step",)

    def test_has_parent_requirement(self) -> None:
        """Test has_parent_requirement property."""
        with_parent = DirectiveContract(requires_parent=("steps",))
        without_parent = DirectiveContract()

        assert with_parent.has_parent_requirement is True
        assert without_parent.has_parent_requirement is False

    def test_has_child_requirement(self) -> None:
        """Test has_child_requirement property."""
        with_required_children = DirectiveContract(requires_children=("step",))
        with_min_children = DirectiveContract(min_children=1)
        without_children = DirectiveContract()

        assert with_required_children.has_child_requirement is True
        assert with_min_children.has_child_requirement is True
        assert without_children.has_child_requirement is False

    def test_frozen_contract(self) -> None:
        """Test that contract is immutable (frozen)."""
        contract = DirectiveContract(requires_parent=("steps",))

        with pytest.raises(Exception):  # FrozenInstanceError
            contract.requires_parent = ("other",)  # type: ignore

    def test_invalid_min_children(self) -> None:
        """Test that negative min_children raises error."""
        with pytest.raises(ValueError, match="min_children must be >= 0"):
            DirectiveContract(min_children=-1)

    def test_invalid_max_children(self) -> None:
        """Test that negative max_children raises error."""
        with pytest.raises(ValueError, match="max_children must be >= 0"):
            DirectiveContract(max_children=-1)


# =============================================================================
# ContractViolation Tests
# =============================================================================


class TestContractViolation:
    """Tests for ContractViolation dataclass."""

    def test_basic_violation(self) -> None:
        """Test creating a basic violation."""
        violation = ContractViolation(
            directive="step",
            violation_type="directive_invalid_parent",
            message="step must be inside steps",
        )

        assert violation.directive == "step"
        assert violation.violation_type == "directive_invalid_parent"
        assert violation.message == "step must be inside steps"

    def test_violation_with_details(self) -> None:
        """Test violation with all details."""
        violation = ContractViolation(
            directive="step",
            violation_type="directive_invalid_parent",
            message="step must be inside steps",
            expected=["steps"],
            found="(root)",
            location="content/guide.md:45",
        )

        assert violation.expected == ["steps"]
        assert violation.found == "(root)"
        assert violation.location == "content/guide.md:45"

    def test_to_log_dict_basic(self) -> None:
        """Test conversion to log dict with minimal fields."""
        violation = ContractViolation(
            directive="step",
            violation_type="directive_invalid_parent",
            message="step must be inside steps",
        )

        result = violation.to_log_dict()

        assert result == {
            "directive": "step",
            "violation": "directive_invalid_parent",
            "message": "step must be inside steps",
        }

    def test_to_log_dict_full(self) -> None:
        """Test conversion to log dict with all fields."""
        violation = ContractViolation(
            directive="step",
            violation_type="directive_invalid_parent",
            message="step must be inside steps",
            expected=["steps"],
            found="(root)",
            location="content/guide.md",
        )

        result = violation.to_log_dict()

        assert result["expected"] == ["steps"]
        assert result["found"] == "(root)"
        assert result["location"] == "content/guide.md"


# =============================================================================
# ContractValidator.validate_parent Tests
# =============================================================================


class TestValidateParent:
    """Tests for ContractValidator.validate_parent."""

    def test_valid_parent(self) -> None:
        """Test valid parent - no violations."""
        violations = ContractValidator.validate_parent(
            contract=STEP_CONTRACT,
            directive_type="step",
            parent_type="steps",
        )

        assert violations == []

    def test_invalid_parent_root(self) -> None:
        """Test invalid parent - at root level."""
        violations = ContractValidator.validate_parent(
            contract=STEP_CONTRACT,
            directive_type="step",
            parent_type=None,
        )

        assert len(violations) == 1
        assert violations[0].violation_type == "directive_invalid_parent"
        assert violations[0].found == "(root)"
        assert "steps" in str(violations[0].expected)

    def test_invalid_parent_wrong_type(self) -> None:
        """Test invalid parent - wrong type."""
        violations = ContractValidator.validate_parent(
            contract=STEP_CONTRACT,
            directive_type="step",
            parent_type="tabs",
        )

        assert len(violations) == 1
        assert violations[0].found == "tabs"

    def test_no_parent_requirement(self) -> None:
        """Test directive with no parent requirement."""
        contract = DirectiveContract()  # No requires_parent

        violations = ContractValidator.validate_parent(
            contract=contract,
            directive_type="note",
            parent_type=None,
        )

        assert violations == []

    def test_violation_includes_location(self) -> None:
        """Test that violation includes source location."""
        violations = ContractValidator.validate_parent(
            contract=STEP_CONTRACT,
            directive_type="step",
            parent_type=None,
            location="content/guide.md:45",
        )

        assert violations[0].location == "content/guide.md:45"

    def test_multiple_valid_parents(self) -> None:
        """Test directive with multiple valid parents."""
        violations = ContractValidator.validate_parent(
            contract=TAB_ITEM_CONTRACT,
            directive_type="tab_item",
            parent_type="tab_set",
        )

        assert violations == []

        violations = ContractValidator.validate_parent(
            contract=TAB_ITEM_CONTRACT,
            directive_type="tab_item",
            parent_type="legacy_tabs",
        )

        assert violations == []


# =============================================================================
# ContractValidator.validate_children Tests
# =============================================================================


class TestValidateChildren:
    """Tests for ContractValidator.validate_children."""

    def test_valid_children(self) -> None:
        """Test valid children - no violations."""
        children = [
            {"type": "step"},
            {"type": "step"},
        ]

        violations = ContractValidator.validate_children(
            contract=STEPS_CONTRACT,
            directive_type="steps",
            children=children,
        )

        assert violations == []

    def test_missing_required_children(self) -> None:
        """Test missing required children."""
        children = [
            {"type": "paragraph"},
        ]

        violations = ContractValidator.validate_children(
            contract=STEPS_CONTRACT,
            directive_type="steps",
            children=children,
        )

        assert len(violations) == 2  # missing_required AND invalid_child_types
        violation_types = [v.violation_type for v in violations]
        assert "directive_missing_required_children" in violation_types

    def test_empty_children(self) -> None:
        """Test empty children when required."""
        violations = ContractValidator.validate_children(
            contract=STEPS_CONTRACT,
            directive_type="steps",
            children=[],
        )

        assert len(violations) == 1
        assert violations[0].violation_type == "directive_missing_required_children"

    def test_insufficient_children(self) -> None:
        """Test insufficient children count."""
        contract = DirectiveContract(
            requires_children=("step",),
            min_children=3,
        )
        children = [
            {"type": "step"},
            {"type": "step"},
        ]

        violations = ContractValidator.validate_children(
            contract=contract,
            directive_type="steps",
            children=children,
        )

        assert len(violations) == 1
        assert violations[0].violation_type == "directive_insufficient_children"
        assert violations[0].expected == 3
        assert violations[0].found == 2

    def test_too_many_children(self) -> None:
        """Test too many children."""
        contract = DirectiveContract(
            max_children=2,
        )
        children = [
            {"type": "item"},
            {"type": "item"},
            {"type": "item"},
        ]

        violations = ContractValidator.validate_children(
            contract=contract,
            directive_type="test",
            children=children,
        )

        assert len(violations) == 1
        assert violations[0].violation_type == "directive_too_many_children"

    def test_invalid_child_types(self) -> None:
        """Test invalid child types (whitelist)."""
        children = [
            {"type": "step"},
            {"type": "paragraph"},  # Not allowed
        ]

        violations = ContractValidator.validate_children(
            contract=STEPS_CONTRACT,
            directive_type="steps",
            children=children,
        )

        assert any(v.violation_type == "directive_invalid_child_types" for v in violations)

    def test_disallowed_child_types(self) -> None:
        """Test disallowed child types (blacklist)."""
        contract = DirectiveContract(
            disallowed_children=("script",),
        )
        children = [
            {"type": "paragraph"},
            {"type": "script"},  # Blacklisted
        ]

        violations = ContractValidator.validate_children(
            contract=contract,
            directive_type="container",
            children=children,
        )

        assert len(violations) == 1
        assert violations[0].violation_type == "directive_disallowed_child_types"
        assert "script" in violations[0].found

    def test_no_child_requirement(self) -> None:
        """Test directive with no child requirements."""
        contract = DirectiveContract()

        violations = ContractValidator.validate_children(
            contract=contract,
            directive_type="note",
            children=[],
        )

        assert violations == []

    def test_handles_non_dict_children(self) -> None:
        """Test handling of non-dict children (edge case)."""
        children = [
            {"type": "step"},
            "raw string",  # Non-dict
            None,  # None
        ]

        # Should not raise, should handle gracefully
        violations = ContractValidator.validate_children(
            contract=STEPS_CONTRACT,
            directive_type="steps",
            children=children,  # type: ignore
        )

        # Should find step, count 1
        assert isinstance(violations, list)


# =============================================================================
# Preset Contract Tests
# =============================================================================


class TestPresetContracts:
    """Tests for preset contract definitions."""

    def test_steps_contract(self) -> None:
        """Test STEPS_CONTRACT configuration."""
        assert STEPS_CONTRACT.requires_children == ("step",)
        assert STEPS_CONTRACT.min_children == 1
        assert STEPS_CONTRACT.allowed_children == ("step",)
        assert STEPS_CONTRACT.requires_parent == ()

    def test_step_contract(self) -> None:
        """Test STEP_CONTRACT configuration."""
        assert STEP_CONTRACT.requires_parent == ("steps",)
        assert STEP_CONTRACT.requires_children == ()

    def test_tab_set_contract(self) -> None:
        """Test TAB_SET_CONTRACT configuration."""
        assert TAB_SET_CONTRACT.requires_children == ("tab_item",)
        assert TAB_SET_CONTRACT.min_children == 1

    def test_tab_item_contract(self) -> None:
        """Test TAB_ITEM_CONTRACT configuration."""
        assert "tab_set" in TAB_ITEM_CONTRACT.requires_parent
        assert "legacy_tabs" in TAB_ITEM_CONTRACT.requires_parent

    def test_cards_contract(self) -> None:
        """Test CARDS_CONTRACT configuration."""
        assert CARDS_CONTRACT.allowed_children == ("card",)
        # Cards don't require children (child-cards can auto-generate)
        assert CARDS_CONTRACT.requires_children == ()

    def test_card_contract(self) -> None:
        """Test CARD_CONTRACT configuration."""
        assert "cards_grid" in CARD_CONTRACT.requires_parent
        assert "grid" in CARD_CONTRACT.requires_parent

    def test_code_tabs_contract(self) -> None:
        """Test CODE_TABS_CONTRACT configuration."""
        assert CODE_TABS_CONTRACT.min_children == 1

