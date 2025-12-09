"""
Tests for analysis result dataclasses.

Tests dataclass creation, field access, and tuple unpacking backward compatibility.
"""

from bengal.analysis.results import PageLayers


class TestPageLayers:
    """Tests for PageLayers dataclass."""

    def test_creates_with_fields(self):
        """Test creating PageLayers with fields."""
        page1 = object()
        page2 = object()
        page3 = object()

        layers = PageLayers(
            hubs=[page1],
            mid_tier=[page2],
            leaves=[page3],
        )

        assert layers.hubs == [page1]
        assert layers.mid_tier == [page2]
        assert layers.leaves == [page3]

    def test_tuple_unpacking_backward_compatibility(self):
        """Test that tuple unpacking still works for backward compatibility."""
        page1 = object()
        page2 = object()
        page3 = object()

        layers = PageLayers(
            hubs=[page1],
            mid_tier=[page2],
            leaves=[page3],
        )

        hubs, mid_tier, leaves = layers

        assert hubs == [page1]
        assert mid_tier == [page2]
        assert leaves == [page3]

    def test_empty_layers(self):
        """Test PageLayers with empty lists."""
        layers = PageLayers(hubs=[], mid_tier=[], leaves=[])

        assert layers.hubs == []
        assert layers.mid_tier == []
        assert layers.leaves == []

        # Tuple unpacking should work with empty lists
        hubs, mid_tier, leaves = layers
        assert hubs == []
        assert mid_tier == []
        assert leaves == []


