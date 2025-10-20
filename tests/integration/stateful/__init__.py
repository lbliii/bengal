import pytest

# Auto-apply the stateful marker to tests in this package
pytestmark = pytest.mark.stateful

"""
Stateful integration tests using Hypothesis.

These tests simulate real user workflows with multiple steps,
verifying that Bengal maintains invariants across sequences of operations.
"""
