"""Tests for custom Jinja2 template tests."""


from datetime import datetime, timedelta

from jinja2 import Environment

from bengal.core.section import Section
from bengal.rendering import template_tests
from bengal.rendering.template_tests import register
from tests._testing.mocks import MockPage


class TestDraftTest:
    """Test the 'draft' template test."""

    def test_draft_true(self):
        """Test page marked as draft."""
        page = MockPage(metadata={"draft": True})
        assert template_tests.test_draft(page) is True

    def test_draft_false(self):
        """Test page not marked as draft."""
        page = MockPage(metadata={"draft": False})
        assert template_tests.test_draft(page) is False

    def test_draft_missing(self):
        """Test page with no draft field."""
        page = MockPage(metadata={})
        assert template_tests.test_draft(page) is False

    def test_no_metadata(self):
        """Test page with no metadata."""
        page = MockPage()
        assert template_tests.test_draft(page) is False

    def test_metadata_is_none(self):
        """Test page with None metadata."""
        page = MockPage(metadata=None)
        assert template_tests.test_draft(page) is False

    def test_draft_string_value(self):
        """Test draft field with string value (should be False)."""
        page = MockPage(metadata={"draft": "true"})
        # String "true" is truthy but not boolean True
        assert template_tests.test_draft(page) == "true"


class TestFeaturedTest:
    """Test the 'featured' template test."""

    def test_featured_tag_present(self):
        """Test page with 'featured' tag."""
        page = MockPage(tags=["python", "featured", "tutorial"])
        assert template_tests.test_featured(page) is True

    def test_featured_tag_absent(self):
        """Test page without 'featured' tag."""
        page = MockPage(tags=["python", "tutorial"])
        assert template_tests.test_featured(page) is False

    def test_empty_tags(self):
        """Test page with empty tags list."""
        page = MockPage(tags=[])
        assert template_tests.test_featured(page) is False

    def test_no_tags_attribute(self):
        """Test page without tags attribute."""
        page = MockPage()
        assert template_tests.test_featured(page) is False

    def test_tags_is_none(self):
        """Test page with None tags."""
        page = MockPage(tags=None)
        assert template_tests.test_featured(page) is False

    def test_case_sensitive(self):
        """Test that tag matching is case-sensitive."""
        page = MockPage(tags=["Featured", "FEATURED"])
        # Should be case-sensitive
        assert template_tests.test_featured(page) is False


class TestOutdatedTest:
    """Test the 'outdated' template test."""

    def test_page_older_than_default_days(self):
        """Test page older than 90 days (default)."""
        old_date = datetime.now() - timedelta(days=100)
        page = MockPage(date=old_date)
        assert template_tests.test_outdated(page) is True

    def test_page_newer_than_default_days(self):
        """Test page newer than 90 days."""
        recent_date = datetime.now() - timedelta(days=50)
        page = MockPage(date=recent_date)
        assert template_tests.test_outdated(page) is False

    def test_page_exactly_90_days(self):
        """Test page exactly 90 days old."""
        date_90_days = datetime.now() - timedelta(days=90)
        page = MockPage(date=date_90_days)
        # Should be False because > 90, not >= 90
        assert template_tests.test_outdated(page) is False

    def test_custom_days_threshold(self):
        """Test with custom days threshold."""
        date = datetime.now() - timedelta(days=40)
        page = MockPage(date=date)

        # 40 days old, threshold 30 -> outdated
        assert template_tests.test_outdated(page, days=30) is True

        # 40 days old, threshold 50 -> not outdated
        assert template_tests.test_outdated(page, days=50) is False

    def test_very_recent_page(self):
        """Test page from today."""
        today = datetime.now()
        page = MockPage(date=today)
        assert template_tests.test_outdated(page) is False

    def test_no_date_attribute(self):
        """Test page without date attribute."""
        page = MockPage()
        assert template_tests.test_outdated(page) is False

    def test_date_is_none(self):
        """Test page with None date."""
        page = MockPage(date=None)
        assert template_tests.test_outdated(page) is False

    def test_invalid_date_type(self):
        """Test page with invalid date type."""
        page = MockPage(date="not a date")
        assert template_tests.test_outdated(page) is False

    def test_future_date(self):
        """Test page with future date."""
        future_date = datetime.now() + timedelta(days=30)
        page = MockPage(date=future_date)
        # Future dates have negative age, so not outdated
        assert template_tests.test_outdated(page) is False

    def test_zero_days_threshold(self):
        """Test with zero days threshold."""
        yesterday = datetime.now() - timedelta(days=1)
        page = MockPage(date=yesterday)
        # 1 day old > 0 days
        assert template_tests.test_outdated(page, days=0) is True


class TestSectionTest:
    """Test the 'section' template test."""

    def test_section_object(self):
        """Test actual Section instance."""
        section = Section(name="blog", path="/blog")
        assert template_tests.test_section(section) is True

    def test_non_section_object(self):
        """Test non-Section objects."""
        page = MockPage(name="page")
        assert template_tests.test_section(page) is False

    def test_dict_object(self):
        """Test dict object."""
        data = {"name": "blog"}
        assert template_tests.test_section(data) is False

    def test_none(self):
        """Test None value."""
        assert template_tests.test_section(None) is False

    def test_string(self):
        """Test string value."""
        assert template_tests.test_section("blog") is False

    def test_list(self):
        """Test list value."""
        assert template_tests.test_section([]) is False


class TestTranslatedTest:
    """Test the 'translated' template test."""

    def test_page_with_translations(self):
        """Test page with translations."""
        page = MockPage(translations={"es": "/es/page", "fr": "/fr/page"})
        assert template_tests.test_translated(page) is True

    def test_page_without_translations(self):
        """Test page with empty translations."""
        page = MockPage(translations={})
        assert template_tests.test_translated(page) is False

    def test_page_with_none_translations(self):
        """Test page with None translations."""
        page = MockPage(translations=None)
        assert template_tests.test_translated(page) is False

    def test_no_translations_attribute(self):
        """Test page without translations attribute."""
        page = MockPage()
        assert template_tests.test_translated(page) is False

    def test_translations_list(self):
        """Test page with translations as list."""
        page = MockPage(translations=["es", "fr"])
        # List is truthy, so should return True
        assert template_tests.test_translated(page) is True

    def test_translations_empty_list(self):
        """Test page with empty translations list."""
        page = MockPage(translations=[])
        assert template_tests.test_translated(page) is False


class TestRegistration:
    """Test registration of custom tests with Jinja2."""

    def test_register_adds_tests_to_environment(self):
        """Test that register() adds all tests to Jinja2 environment."""
        from bengal.core.site import Site

        env = Environment()
        site = Site(root_path=".")

        # Register tests
        register(env, site)

        # Check all tests are registered
        assert "draft" in env.tests
        assert "featured" in env.tests
        assert "outdated" in env.tests
        assert "section" in env.tests
        assert "translated" in env.tests

    def test_template_can_use_draft_test(self):
        """Test using 'draft' test in actual template."""
        from bengal.core.site import Site

        env = Environment()
        site = Site(root_path=".")
        register(env, site)

        # Create template
        template = env.from_string("{% if page is draft %}DRAFT{% else %}PUBLISHED{% endif %}")

        # Test with draft page
        page = MockPage(metadata={"draft": True})
        result = template.render(page=page)
        assert result == "DRAFT"

        # Test with published page
        page = MockPage(metadata={"draft": False})
        result = template.render(page=page)
        assert result == "PUBLISHED"

    def test_template_can_use_featured_test(self):
        """Test using 'featured' test in actual template."""
        from bengal.core.site import Site

        env = Environment()
        site = Site(root_path=".")
        register(env, site)

        template = env.from_string("{% if page is featured %}⭐{% endif %}")

        page = MockPage(tags=["python", "featured"])
        result = template.render(page=page)
        assert result == "⭐"

        page = MockPage(tags=["python"])
        result = template.render(page=page)
        assert result == ""

    def test_template_can_use_outdated_test(self):
        """Test using 'outdated' test in actual template."""
        from bengal.core.site import Site

        env = Environment()
        site = Site(root_path=".")
        register(env, site)

        template = env.from_string(
            "{% if page is outdated %}OLD{% elif page is outdated(30) %}RECENT{% else %}NEW{% endif %}"
        )

        # Very old page
        old_page = MockPage(date=datetime.now() - timedelta(days=100))
        result = template.render(page=old_page)
        assert result == "OLD"

        # Recent page
        recent_page = MockPage(date=datetime.now() - timedelta(days=10))
        result = template.render(page=recent_page)
        assert result == "NEW"

    def test_template_can_use_negated_test(self):
        """Test using 'is not' with custom tests."""
        from bengal.core.site import Site

        env = Environment()
        site = Site(root_path=".")
        register(env, site)

        template = env.from_string("{% if page is not draft %}VISIBLE{% endif %}")

        page = MockPage(metadata={"draft": False})
        result = template.render(page=page)
        assert result == "VISIBLE"

        page = MockPage(metadata={"draft": True})
        result = template.render(page=page)
        assert result == ""

    def test_template_can_use_section_test(self):
        """Test using 'section' test in actual template."""
        from bengal.core.site import Site

        env = Environment()
        site = Site(root_path=".")
        register(env, site)

        template = env.from_string("{% if obj is section %}SECTION{% else %}PAGE{% endif %}")

        section = Section(name="blog", path="/blog")
        result = template.render(obj=section)
        assert result == "SECTION"

        page = MockPage()
        result = template.render(obj=page)
        assert result == "PAGE"

    def test_template_can_use_translated_test(self):
        """Test using 'translated' test in actual template."""
        from bengal.core.site import Site

        env = Environment()
        site = Site(root_path=".")
        register(env, site)

        template = env.from_string("{% if page is translated %}🌐{% endif %}")

        page = MockPage(translations={"es": "/es/page"})
        result = template.render(page=page)
        assert result == "🌐"

        page = MockPage(translations={})
        result = template.render(page=page)
        assert result == ""


class TestComplexTemplateScenarios:
    """Test complex real-world template scenarios."""

    def test_filtering_draft_and_featured_posts(self):
        """Test filtering posts by draft status and featured tag."""
        from bengal.core.site import Site

        env = Environment()
        site = Site(root_path=".")
        register(env, site)

        template = env.from_string(
            """
            {%- for post in posts if post is not draft -%}
            {{ post.title }}{% if post is featured %}*{% endif %}
            {% endfor -%}
            """
        )

        posts = [
            MockPage(title="Post 1", metadata={"draft": False}, tags=["python"]),
            MockPage(title="Post 2", metadata={"draft": False}, tags=["featured", "python"]),
            MockPage(title="Post 3", metadata={"draft": True}, tags=["python"]),
            MockPage(title="Post 4", metadata={"draft": False}, tags=[]),
        ]

        result = template.render(posts=posts)
        assert "Post 1" in result
        assert "Post 2*" in result
        assert "Post 3" not in result
        assert "Post 4" in result

    def test_show_outdated_warning(self):
        """Test showing warning for outdated content."""
        from bengal.core.site import Site

        env = Environment()
        site = Site(root_path=".")
        register(env, site)

        template = env.from_string(
            """
            {%- if page is outdated(180) -%}
            ⚠️ This content is over 6 months old
            {%- endif -%}
            """
        )

        # Old page
        old_page = MockPage(date=datetime.now() - timedelta(days=200))
        result = template.render(page=old_page)
        assert "⚠️" in result

        # Recent page
        recent_page = MockPage(date=datetime.now() - timedelta(days=30))
        result = template.render(page=recent_page)
        assert "⚠️" not in result

    def test_language_switcher_for_translated_pages(self):
        """Test rendering language switcher for translated pages."""
        from bengal.core.site import Site

        env = Environment()
        site = Site(root_path=".")
        register(env, site)

        template = env.from_string(
            """
            {%- if page is translated -%}
            Languages: {% for lang, url in page.translations.items() %}{{ lang }}{% endfor %}
            {%- endif -%}
            """
        )

        page = MockPage(translations={"es": "/es/page", "fr": "/fr/page"})
        result = template.render(page=page)
        assert "Languages:" in result
        assert "es" in result
        assert "fr" in result

    def test_combined_filters(self):
        """Test combining multiple custom tests."""
        from bengal.core.site import Site

        env = Environment()
        site = Site(root_path=".")
        register(env, site)

        template = env.from_string(
            """
            {%- for post in posts if post is not draft and post is featured and post is not outdated(60) -%}
            {{ post.title }}
            {% endfor -%}
            """
        )

        posts = [
            MockPage(
                title="Featured Recent",
                metadata={"draft": False},
                tags=["featured"],
                date=datetime.now() - timedelta(days=30),
            ),
            MockPage(
                title="Featured Old",
                metadata={"draft": False},
                tags=["featured"],
                date=datetime.now() - timedelta(days=100),
            ),
            MockPage(
                title="Draft Featured",
                metadata={"draft": True},
                tags=["featured"],
                date=datetime.now() - timedelta(days=30),
            ),
            MockPage(
                title="Not Featured",
                metadata={"draft": False},
                tags=[],
                date=datetime.now() - timedelta(days=30),
            ),
        ]

        result = template.render(posts=posts)
        assert "Featured Recent" in result
        assert "Featured Old" not in result
        assert "Draft Featured" not in result
        assert "Not Featured" not in result
