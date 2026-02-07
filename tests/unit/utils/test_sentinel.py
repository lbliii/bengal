"""Unit tests for sentinel values."""

import pickle

from bengal.utils.primitives.sentinel import MISSING, is_missing


def test_missing_is_singleton():
    """Test that MISSING is a singleton."""
    from bengal.utils.primitives.sentinel import _MissingType

    assert MISSING is MISSING
    assert isinstance(MISSING, _MissingType)

    # Check that another instance cannot be created easily if we use the same class
    new_missing = _MissingType()
    assert new_missing is MISSING


def test_is_missing_helper():
    """Test the is_missing helper function."""
    assert is_missing(MISSING) is True
    assert is_missing(None) is False
    assert is_missing("") is False
    assert is_missing(0) is False


def test_missing_repr():
    """Test the string representation of MISSING."""
    assert repr(MISSING) == "MISSING"


def test_missing_pickle():
    """Test that MISSING can be pickled and remains a singleton."""
    pickled = pickle.dumps(MISSING)
    unpickled = pickle.loads(pickled)
    assert unpickled is MISSING
