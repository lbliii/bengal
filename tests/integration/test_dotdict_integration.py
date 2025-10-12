"""Integration test for DotDict with real-world usage patterns."""

import pytest

from bengal.utils.dotdict import DotDict, wrap_data


def test_jinja2_template_data_pattern():
    """Test typical Jinja2 template data pattern."""
    # Simulate site.data structure
    site_data = DotDict.from_dict(
        {
            "authors": [
                {
                    "name": "Alice Johnson",
                    "bio": "Python developer",
                    "social": {"github": "alice", "twitter": "@alice"},
                },
                {
                    "name": "Bob Smith",
                    "bio": "Go developer",
                    "social": {"github": "bob", "twitter": "@bob"},
                },
            ],
            "config": {
                "site_name": "My Blog",
                "theme": {"colors": {"primary": "#007bff", "secondary": "#6c757d"}},
            },
        }
    )

    # Simulate template access patterns
    # Template: {% for author in site.data.authors %}
    for author in site_data.authors:
        assert hasattr(author, "name")
        assert hasattr(author, "social")
        assert author.social.github is not None

    # Verify deep nesting works
    assert site_data.config.theme.colors.primary == "#007bff"

    # Verify caching (same object returned)
    config1 = site_data.config
    config2 = site_data.config
    assert config1 is config2  # Cached

    theme1 = site_data.config.theme
    theme2 = site_data.config.theme
    assert theme1 is theme2  # Cached


def test_page_metadata_pattern():
    """Test page metadata access pattern."""
    # Simulate page.metadata structure
    page_metadata = DotDict.from_dict(
        {
            "title": "Getting Started",
            "description": "A guide to getting started",
            "author": {"name": "Alice", "email": "alice@example.com"},
            "tags": ["tutorial", "beginner"],
            "seo": {
                "meta": {"keywords": ["guide", "tutorial"], "robots": "index,follow"},
                "og": {"title": "Getting Started Guide", "image": "/images/og-image.png"},
            },
        }
    )

    # Access patterns from templates
    assert page_metadata.title == "Getting Started"
    assert page_metadata.author.name == "Alice"
    assert "tutorial" in page_metadata.tags
    assert page_metadata.seo.meta.robots == "index,follow"
    assert page_metadata.seo.og.image == "/images/og-image.png"


def test_yaml_data_file_pattern():
    """Test YAML data file loading pattern."""
    # Simulate loading YAML like:
    # data/team.yaml
    yaml_content = {
        "departments": [
            {
                "name": "Engineering",
                "lead": {"name": "Alice", "title": "VP Engineering"},
                "members": [
                    {"name": "Bob", "role": "Senior Dev"},
                    {"name": "Charlie", "role": "Dev"},
                ],
            },
            {
                "name": "Design",
                "lead": {"name": "Diana", "title": "Design Director"},
                "members": [{"name": "Eve", "role": "Senior Designer"}],
            },
        ]
    }

    team_data = wrap_data(yaml_content)

    # Template: {% for dept in site.data.team.departments %}
    eng_dept = team_data.departments[0]
    assert eng_dept.name == "Engineering"
    assert eng_dept.lead.name == "Alice"
    assert len(eng_dept.members) == 2
    assert eng_dept.members[0].name == "Bob"


def test_nested_loops_performance():
    """Test nested loops don't create excessive objects."""
    # Simulate a complex nested data structure
    data = DotDict.from_dict(
        {
            "categories": [
                {
                    "name": "Tech",
                    "subcategories": [
                        {
                            "name": "Programming",
                            "posts": [
                                {"title": "Post 1", "views": 100},
                                {"title": "Post 2", "views": 200},
                            ],
                        }
                    ],
                }
            ]
        }
    )

    # Simulate nested loop in template
    # {% for category in data.categories %}
    #   {% for subcategory in category.subcategories %}
    #     {% for post in subcategory.posts %}
    total_views = 0
    for category in data.categories:
        for subcategory in category.subcategories:
            for post in subcategory.posts:
                total_views += post.views

    assert total_views == 300

    # Verify caching works across loop iterations
    category1 = data.categories[0]
    category2 = data.categories[0]
    # Note: categories is a list, so items aren't cached,
    # but nested dicts within them should be
    assert category1 is category2  # List returns same object


def test_mutation_invalidates_cache():
    """Test that mutations properly invalidate cache."""
    data = DotDict({"user": {"name": "Alice", "age": 30}})

    # Access and cache
    user1 = data.user
    assert user1.name == "Alice"

    # Mutate
    data.user = {"name": "Bob", "age": 25}

    # Should return new wrapped object
    user2 = data.user
    assert user2.name == "Bob"
    assert user1 is not user2  # Cache was invalidated


def test_field_named_items_in_template():
    """Test the items field gotcha that DotDict solves."""
    # This is the key problem DotDict solves for Jinja2
    skills_data = DotDict.from_dict(
        {
            "skills": [
                {
                    "category": "Programming",
                    "items": ["Python", "Go", "Rust"],  # Field named "items"
                },
                {"category": "Tools", "items": ["Git", "Docker"]},
            ]
        }
    )

    # In Jinja2 template: {{ skill.items }}
    # With regular dict: would access .items() method ❌
    # With DotDict: accesses "items" field ✅
    for skill in skills_data.skills:
        assert isinstance(skill.items, list)  # Field, not method!
        assert len(skill.items) > 0


def test_safe_none_access():
    """Test safe None access for Jinja2 conditionals."""
    data = DotDict({"name": "Alice"})

    # In Jinja2: {% if user.email %}
    # Should not raise AttributeError, should return None
    assert data.email is None
    assert data.nonexistent is None

    # Note: Chaining through None (data.deeply.nested.path) would raise AttributeError
    # This is expected - in real Jinja2 templates you check at each level:
    # {% if data.deeply %} {% if data.deeply.nested %} ... {% endif %} {% endif %}

    # Safe conditionals
    if data.name:
        assert True  # Has name

    if not data.email:
        assert True  # No email

    # Test optional nested access pattern
    user_data = DotDict({"name": "Bob", "profile": {"bio": "Developer"}})

    # Safe: check before accessing nested
    if user_data.profile:
        assert user_data.profile.bio == "Developer"

    # Safe: missing nested returns None
    assert user_data.settings is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
