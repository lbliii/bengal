"""
Test card directive with new options: description, badge.
"""


class TestCardDescriptionOption:
    """Test the :description: option for card directive."""

    def test_description_not_present_by_default(self, parser):
        """Test that no description is rendered by default."""
        content = """
:::{cards}
:::{card} My Card
Card content here.
:::
::::
"""
        result = parser.parse(content, {})

        assert "card-description" not in result

    def test_description_renders_below_header(self, parser):
        """Test that description is rendered below the header."""
        content = """
:::{cards}
:::{card} Getting Started
:description: Everything you need to get up and running
Detailed content here.
:::
::::
"""
        result = parser.parse(content, {})

        assert "card-description" in result
        assert "Everything you need to get up and running" in result

    def test_description_is_escaped(self, parser):
        """Test that description is HTML escaped."""
        content = """
:::{cards}
:::{card} Test
:description: Contains <script>alert('xss')</script>
Content
:::
::::
"""
        result = parser.parse(content, {})

        # HTML should be escaped
        assert "<script>" not in result
        assert "&lt;script&gt;" in result or "script" in result

    def test_description_separate_from_content(self, parser):
        """Test that description and content are separate."""
        content = """
:::{cards}
:::{card} API Reference
:description: Complete API documentation
This is the main content with **markdown** support.
:::
::::
"""
        result = parser.parse(content, {})

        assert "card-description" in result
        assert "Complete API documentation" in result
        assert "card-content" in result
        assert "<strong>markdown</strong>" in result


class TestCardBadgeOption:
    """Test the :badge: option for card directive."""

    def test_badge_not_present_by_default(self, parser):
        """Test that no badge is rendered by default."""
        content = """
:::{cards}
:::{card} Regular Card
Card content
:::
::::
"""
        result = parser.parse(content, {})

        assert "card-badge" not in result

    def test_badge_renders_in_header(self, parser):
        """Test that badge is rendered in card header."""
        content = """
:::{cards}
:::{card} New Feature
:badge: New
This is a new feature.
:::
::::
"""
        result = parser.parse(content, {})

        assert "card-badge" in result
        assert "New" in result

    def test_badge_updated(self, parser):
        """Test badge with 'Updated' text."""
        content = """
:::{cards}
:::{card} Documentation
:badge: Updated
Recently updated documentation.
:::
::::
"""
        result = parser.parse(content, {})

        assert "card-badge" in result
        assert "Updated" in result

    def test_badge_pro(self, parser):
        """Test badge with 'Pro' text."""
        content = """
:::{cards}
:::{card} Advanced Features
:badge: Pro
Premium features for Pro users.
:::
::::
"""
        result = parser.parse(content, {})

        assert "card-badge" in result
        assert "Pro" in result

    def test_badge_beta(self, parser):
        """Test badge with 'Beta' text."""
        content = """
:::{cards}
:::{card} Experimental
:badge: Beta
This feature is in beta.
:::
::::
"""
        result = parser.parse(content, {})

        assert "card-badge" in result
        assert "Beta" in result


class TestCardCombinedOptions:
    """Test combining description and badge with other options."""

    def test_description_and_badge(self, parser):
        """Test combining description and badge."""
        content = """
:::{cards}
:::{card} Getting Started
:description: Quick setup guide for new users
:badge: Updated
Detailed setup instructions.
:::
::::
"""
        result = parser.parse(content, {})

        assert "card-description" in result
        assert "Quick setup guide for new users" in result
        assert "card-badge" in result
        assert "Updated" in result

    def test_all_card_options(self, parser):
        """Test combining all card options."""
        content = """
:::{cards}
:::{card} API Reference
:icon: book
:link: /docs/api/
:description: Complete API documentation
:badge: New
:color: blue
Full API reference documentation with examples.
:::
::::
"""
        result = parser.parse(content, {})

        assert "card-icon" in result
        assert 'href="/docs/api/"' in result
        assert "card-description" in result
        assert "Complete API documentation" in result
        assert "card-badge" in result
        assert "New" in result
        assert "card-color-blue" in result

    def test_description_with_icon_no_title(self, parser):
        """Test description with icon but no title."""
        content = """
:::{cards}
:::{card}
:icon: rocket
:description: Launch your project
Launch content here.
:::
::::
"""
        result = parser.parse(content, {})

        assert "card-icon" in result
        assert "card-description" in result
        assert "Launch your project" in result


class TestCardBadgeWithPull:
    """Test that badge field can be pulled from linked pages."""

    def test_pull_badge_field(self, parser):
        """Test that pull option includes badge field."""
        content = """
:::{cards}
:::{card}
:link: docs/quickstart
:pull: title, description, badge
:::
::::
"""
        result = parser.parse(content, {})

        # Should render without error (badge pull gracefully degrades)
        assert "card" in result


class TestCardWithNamedClosers:
    """Test card options with named closer syntax."""

    def test_named_closers_with_description_and_badge(self, parser):
        """Test named closers with new options."""
        content = """
:::{cards}
:::{card} Feature One
:icon: star
:description: The first amazing feature
:badge: New
Feature details here.
:::{/card}
:::{card} Feature Two
:icon: rocket
:description: The second amazing feature
:badge: Updated
More details here.
:::{/card}
:::{/cards}
"""
        result = parser.parse(content, {})

        assert "Feature One" in result
        assert "Feature Two" in result
        assert "The first amazing feature" in result
        assert "The second amazing feature" in result
        assert "New" in result
        assert "Updated" in result
