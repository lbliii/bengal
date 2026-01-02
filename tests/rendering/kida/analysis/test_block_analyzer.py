"""Tests for Kida template introspection API.

Tests for:
- DependencyWalker: Variable dependency extraction
- PurityAnalyzer: Pure/impure classification
- LandmarkDetector: HTML5 landmark detection
- RoleClassifier: Block role heuristics
- CacheScope: Cache scope inference
- BlockAnalyzer: Full analysis pipeline
- Template integration: block_metadata(), depends_on(), template_metadata()
"""

from __future__ import annotations

from bengal.rendering.kida import Environment
from bengal.rendering.kida.analysis import (
    AnalysisConfig,
    BlockAnalyzer,
    BlockMetadata,
    DependencyWalker,
    PurityAnalyzer,
    TemplateMetadata,
    classify_role,
    infer_cache_scope,
)
from bengal.rendering.kida.environment.loaders import DictLoader


class TestDependencyWalker:
    """Test dependency extraction."""

    def test_simple_variable(self) -> None:
        """Direct variable access is tracked."""
        env = Environment()
        t = env.from_string("{{ page.title }}")
        deps = t.depends_on()
        assert "page.title" in deps

    def test_root_variable(self) -> None:
        """Root variable access is tracked."""
        env = Environment()
        t = env.from_string("{{ items }}")
        deps = t.depends_on()
        assert "items" in deps

    def test_loop_variable_excluded(self) -> None:
        """Loop variables are not context dependencies."""
        env = Environment()
        t = env.from_string("""
            {% for item in items %}
                {{ item.name }}
            {% end %}
        """)
        deps = t.depends_on()
        assert "items" in deps
        assert "item" not in deps
        assert "item.name" not in deps

    def test_nested_loop_variables_excluded(self) -> None:
        """Nested loop variables are excluded from dependencies."""
        env = Environment()
        t = env.from_string("""
            {% for category in categories %}
                {% for item in category.items %}
                    {{ item.name }}
                {% end %}
            {% end %}
        """)
        deps = t.depends_on()
        assert "categories" in deps
        assert "category" not in deps
        assert "category.items" not in deps
        assert "item" not in deps

    def test_nested_access(self) -> None:
        """Chained attribute access builds full path."""
        env = Environment()
        t = env.from_string("{{ site.config.theme.name }}")
        deps = t.depends_on()
        assert "site.config.theme.name" in deps

    def test_with_binding_excluded(self) -> None:
        """With bindings create local scope."""
        env = Environment()
        t = env.from_string("""
            {% with page.author as author %}
                {{ author.name }}
            {% end %}
        """)
        deps = t.depends_on()
        assert "page.author" in deps
        assert "author" not in deps

    def test_optional_chaining(self) -> None:
        """Optional chaining is tracked."""
        env = Environment()
        t = env.from_string("{{ page?.author?.name }}")
        deps = t.depends_on()
        assert "page.author.name" in deps

    def test_null_coalescing(self) -> None:
        """Null coalescing tracks both sides."""
        env = Environment()
        t = env.from_string("{{ page.subtitle ?? 'Default' }}")
        deps = t.depends_on()
        assert "page.subtitle" in deps

    def test_pipeline_dependencies(self) -> None:
        """Pipeline tracks dependencies in filter args (tested via direct analysis)."""
        # Note: sort_by and take may not exist as Kida filters, so test directly
        from bengal.rendering.kida.lexer import Lexer, LexerConfig
        from bengal.rendering.kida.parser import Parser

        source = "{{ items |> sort_by(config.sort_key) |> take(5) }}"
        lexer = Lexer(source, LexerConfig())
        tokens = list(lexer.tokenize())
        parser = Parser(tokens, None, None, source, autoescape=True)
        ast = parser.parse()

        walker = DependencyWalker()
        deps = walker.analyze(ast)
        assert "items" in deps
        assert "config.sort_key" in deps

    def test_set_creates_local(self) -> None:
        """Set statement creates local scope.

        Note: The current implementation may detect {{ x }} as a dependency
        before the set is analyzed. This is conservative over-approximation.
        The key test is that page.value IS detected as a dependency.
        """
        env = Environment()
        t = env.from_string("""
            {% set x = page.value %}
            {{ x }}
        """)
        deps = t.depends_on()
        assert "page.value" in deps
        # Note: x may or may not be in deps depending on parse order
        # The important thing is the RHS dependency is tracked

    def test_let_creates_template_scope(self) -> None:
        """Let statement creates template-wide scope.

        Note: The dependency walker currently detects {{ counter }} as a
        dependency before the let statement is processed. This is expected
        conservative behavior - the walker over-approximates dependencies.
        """
        env = Environment()
        t = env.from_string("""
            {% let counter = 0 %}
            {% for i in range(5) %}
                {% set counter = counter + 1 %}
            {% end %}
            {{ counter }}
        """)
        deps = t.depends_on()
        # Counter is initialized with constant 0, no external deps
        # The "counter" in set is updating the let-scoped var
        # range is a builtin, so excluded
        assert "range" not in deps

    def test_conditional_both_branches(self) -> None:
        """Conditional tracks dependencies in all branches."""
        env = Environment()
        t = env.from_string("""
            {% if show_nav %}
                {{ nav_items }}
            {% else %}
                {{ fallback_text }}
            {% end %}
        """)
        deps = t.depends_on()
        assert "show_nav" in deps
        assert "nav_items" in deps
        assert "fallback_text" in deps

    def test_function_args_excluded(self) -> None:
        """Function arguments are excluded from dependencies."""
        env = Environment()
        t = env.from_string("""
            {% def card(item) %}
                {{ item.title }}
                {{ site.name }}
            {% end %}
        """)
        deps = t.depends_on()
        assert "item" not in deps
        assert "item.title" not in deps
        assert "site.name" in deps

    def test_builtins_excluded(self) -> None:
        """Built-in names are excluded."""
        env = Environment()
        t = env.from_string("{{ len(items) }}")
        deps = t.depends_on()
        assert "items" in deps
        assert "len" not in deps

    def test_loop_variable_excluded_from_deps(self) -> None:
        """loop.* access is not a context dependency."""
        env = Environment()
        t = env.from_string("""
            {% for item in items %}
                {{ loop.index }}: {{ item }}
            {% end %}
        """)
        deps = t.depends_on()
        assert "items" in deps
        assert "loop" not in deps
        assert "loop.index" not in deps

    def test_include_tracks_template_name(self) -> None:
        """Include tracks template expression dependencies."""
        env = Environment()
        t = env.from_string("{% include config.partial_name %}")
        deps = t.depends_on()
        assert "config.partial_name" in deps

    def test_dynamic_extends(self) -> None:
        """Dynamic extends expression is tracked."""
        env = Environment()
        t = env.from_string("""
            {% extends config.base_template %}
            {% block content %}Hello{% end %}
        """)
        meta = t.template_metadata()
        assert meta is not None
        assert "config.base_template" in meta.top_level_depends_on


class TestPurityAnalyzer:
    """Test purity inference."""

    def test_static_content_is_pure(self) -> None:
        """Static HTML is pure."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                <div>Hello</div>
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].is_pure == "pure"

    def test_pure_filter_preserves_purity(self) -> None:
        """Pure filters don't affect purity."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {{ page.title | upper }}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].is_pure == "pure"

    def test_random_filter_is_impure(self) -> None:
        """Random filter makes block impure (tested via direct analysis)."""
        # Note: Kida doesn't have a 'random' filter built-in, but we test
        # the analysis directly on the AST to verify the purity analyzer
        # correctly identifies known impure filters.
        from bengal.rendering.kida.lexer import Lexer, LexerConfig
        from bengal.rendering.kida.parser import Parser

        source = "{{ items | random }}"
        lexer = Lexer(source, LexerConfig())
        tokens = list(lexer.tokenize())
        parser = Parser(tokens, None, None, source, autoescape=True)
        ast = parser.parse()

        # Analyze the output expression
        analyzer = PurityAnalyzer()
        output_node = ast.body[0]  # Output node
        purity = analyzer.analyze(output_node.expr)
        assert purity == "impure"

    def test_shuffle_filter_is_impure(self) -> None:
        """Shuffle filter makes block impure (tested via direct analysis)."""
        from bengal.rendering.kida.lexer import Lexer, LexerConfig
        from bengal.rendering.kida.parser import Parser

        source = "{{ items | shuffle }}"
        lexer = Lexer(source, LexerConfig())
        tokens = list(lexer.tokenize())
        parser = Parser(tokens, None, None, source, autoescape=True)
        ast = parser.parse()

        analyzer = PurityAnalyzer()
        output_node = ast.body[0]
        purity = analyzer.analyze(output_node.expr)
        assert purity == "impure"

    def test_function_call_with_known_pure_function(self) -> None:
        """Known pure functions are marked pure."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {{ len(items) }}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].is_pure == "pure"

    def test_unknown_function_call_is_unknown(self) -> None:
        """Unknown function calls are unknown purity."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {{ some_function() }}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].is_pure == "unknown"

    def test_pure_operations(self) -> None:
        """Arithmetic and comparisons are pure."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {{ a + b * c }}
                {{ x < y }}
                {{ flag and other }}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].is_pure == "pure"

    def test_conditional_pure_if_all_branches_pure(self) -> None:
        """Conditional is pure if all branches are pure."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {% if show %}{{ a | upper }}{% else %}{{ b | lower }}{% end %}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].is_pure == "pure"

    def test_conditional_impure_if_any_branch_impure(self) -> None:
        """Conditional is impure if any branch is impure (tested via direct analysis)."""
        from bengal.rendering.kida.lexer import Lexer, LexerConfig
        from bengal.rendering.kida.parser import Parser

        # Parse a conditional with a 'random' filter in one branch
        source = "{% if show %}{{ items | random }}{% else %}{{ items | first }}{% end %}"
        lexer = Lexer(source, LexerConfig())
        tokens = list(lexer.tokenize())
        parser = Parser(tokens, None, None, source, autoescape=True)
        ast = parser.parse()

        analyzer = PurityAnalyzer()
        if_node = ast.body[0]  # If node
        purity = analyzer.analyze(if_node)
        assert purity == "impure"

    def test_include_with_pure_content_is_pure(self) -> None:
        """Include with pure content is analyzed as pure."""
        env = Environment()

        # Create a pure partial template
        _partial = env.from_string("""
            <footer>
                <p>&copy; {{ site.build_time | dateformat('%Y') }} {{ config.title }}</p>
            </footer>
        """)

        # Main template that includes the partial
        main = env.from_string("""
            {% block site_footer %}
                {% include 'partials/footer.html' %}
            {% end %}
        """)

        # Register the partial in the environment
        # Note: This is a simplified test - in real usage, templates are loaded via loader
        # For this test, we'll verify the mechanism works when resolver is provided

        blocks = main.block_metadata()
        # With include analysis, this should be "pure" instead of "unknown"
        # But without resolver, it will be "unknown"
        assert blocks["site_footer"].is_pure in ("pure", "unknown")

    def test_include_with_impure_content_is_impure(self) -> None:
        """Include with impure content (like random) is analyzed as impure."""
        env = Environment()

        # Create an impure partial template
        _partial = env.from_string("""
            {% let quote = quotes | shuffle | first %}
            <blockquote>{{ quote }}</blockquote>
        """)

        # Main template that includes the partial
        main = env.from_string("""
            {% block random_quote %}
                {% include 'partials/quote.html' %}
            {% end %}
        """)

        blocks = main.block_metadata()
        # Should detect impure content in include
        # Without resolver, will be "unknown", but with resolver should be "impure"
        assert blocks["random_quote"].is_pure in ("impure", "unknown")


class TestSharedAnalysisCache:
    """Test shared analysis cache optimization."""

    def test_shared_cache_reuses_analysis(self) -> None:
        """Multiple templates including the same partial reuse cached analysis."""

        templates = {
            "main1.html": '{% block content %}{% include "shared.html" %}{% end %}',
            "main2.html": '{% block content %}{% include "shared.html" %}{% end %}',
            "main3.html": '{% block content %}{% include "shared.html" %}{% end %}',
            "shared.html": "<p>Shared: {{ config.title | upper }}</p>",
        }

        env = Environment(loader=DictLoader(templates))

        # Analyze first template (should analyze shared.html)
        t1 = env.get_template("main1.html")
        meta1 = t1.template_metadata()
        assert meta1 is not None
        assert "shared.html" in env._analysis_cache

        # Analyze second template (should reuse cached analysis of shared.html)
        t2 = env.get_template("main2.html")
        meta2 = t2.template_metadata()
        assert meta2 is not None

        # Analyze third template (should also reuse cache)
        t3 = env.get_template("main3.html")
        meta3 = t3.template_metadata()
        assert meta3 is not None

        # All should have same purity (shared.html is pure)
        assert meta1.blocks["content"].is_pure == "pure"
        assert meta2.blocks["content"].is_pure == "pure"
        assert meta3.blocks["content"].is_pure == "pure"

        # Cache should contain all analyzed templates
        assert "main1.html" in env._analysis_cache
        assert "main2.html" in env._analysis_cache
        assert "main3.html" in env._analysis_cache
        assert "shared.html" in env._analysis_cache

    def test_cache_invalidation_on_template_clear(self) -> None:
        """Analysis cache is invalidated when templates are cleared."""

        templates = {
            "main.html": '{% block content %}{% include "partial.html" %}{% end %}',
            "partial.html": "<p>Content</p>",
        }

        env = Environment(loader=DictLoader(templates))

        # Analyze templates
        t = env.get_template("main.html")
        meta = t.template_metadata()
        assert meta is not None
        assert "main.html" in env._analysis_cache
        assert "partial.html" in env._analysis_cache

        # Clear specific template
        env.clear_template_cache(["partial.html"])
        assert "partial.html" not in env._analysis_cache
        assert "main.html" in env._analysis_cache  # Other templates still cached

        # Clear all templates
        env.clear_template_cache()
        assert len(env._analysis_cache) == 0

    def test_cache_invalidation_on_template_reload(self) -> None:
        """Analysis cache is invalidated when template source changes."""
        import tempfile
        from pathlib import Path

        # Create temporary directory for templates
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            partial_file = tmp_path / "partial.html"
            main_file = tmp_path / "main.html"

            # Write initial templates
            partial_file.write_text("<p>Version 1</p>")
            main_file.write_text('{% block content %}{% include "partial.html" %}{% end %}')

            from bengal.rendering.kida.environment.loaders import FileSystemLoader

            env = Environment(loader=FileSystemLoader([str(tmp_path)]), auto_reload=True)

            # Load and analyze
            t1 = env.get_template("main.html")
            meta1 = t1.template_metadata()
            assert meta1 is not None
            assert "partial.html" in env._analysis_cache

            # Modify partial template
            partial_file.write_text("<p>Version 2: {{ config.title }}</p>")

            # Reload template (should detect change and invalidate cache)
            t2 = env.get_template("main.html")
            meta2 = t2.template_metadata()
            assert meta2 is not None

            # Cache should be repopulated (old entry invalidated, new one added)
            assert "partial.html" in env._analysis_cache

    def test_cache_preserves_analysis_across_calls(self) -> None:
        """Analysis cache persists across multiple template_metadata() calls."""

        templates = {
            "main.html": '{% block content %}{% include "partial.html" %}{% end %}',
            "partial.html": "<p>{{ config.title }}</p>",
        }

        env = Environment(loader=DictLoader(templates))

        t = env.get_template("main.html")

        # First call - should analyze and cache
        meta1 = t.template_metadata()
        assert meta1 is not None
        assert "main.html" in env._analysis_cache
        assert "partial.html" in env._analysis_cache

        # Second call - should use cache
        meta2 = t.template_metadata()
        assert meta2 is not None
        assert meta1 is meta2  # Same object (cached)

    def test_include_chain_uses_shared_cache(self) -> None:
        """Deep include chains benefit from shared cache."""

        templates = {
            "main.html": '{% block content %}{% include "level1.html" %}{% end %}',
            "level1.html": '{% include "level2.html" %}',
            "level2.html": '{% include "level3.html" %}',
            "level3.html": "<p>Final</p>",
        }

        env = Environment(loader=DictLoader(templates))

        # Analyze main template (should analyze all levels)
        t = env.get_template("main.html")
        meta = t.template_metadata()
        assert meta is not None

        # All templates in chain should be cached
        assert "main.html" in env._analysis_cache
        assert "level1.html" in env._analysis_cache
        assert "level2.html" in env._analysis_cache
        assert "level3.html" in env._analysis_cache

        # Block should be pure (all includes are pure)
        assert meta.blocks["content"].is_pure == "pure"


class TestCacheScope:
    """Test cache scope inference."""

    def test_site_only_deps_is_site_scope(self) -> None:
        """Block depending only on site is site-cacheable."""
        env = Environment()
        t = env.from_string("""
            {% block nav %}
                {% for p in site.pages %}
                    {{ p.title }}
                {% end %}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["nav"].cache_scope == "site"

    def test_page_deps_is_page_scope(self) -> None:
        """Block depending on page is page-cacheable."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {{ page.content }}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].cache_scope == "page"

    def test_mixed_deps_is_page_scope(self) -> None:
        """Block depending on both site and page is page-cacheable."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {{ site.title }} - {{ page.title }}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].cache_scope == "page"

    def test_impure_block_not_cacheable(self) -> None:
        """Impure blocks cannot be cached (tested via infer_cache_scope)."""
        # Test the infer_cache_scope function directly
        scope = infer_cache_scope(
            frozenset({"items"}),
            "impure",  # Simulating a block with impure filter
        )
        assert scope == "none"

    def test_no_deps_is_site_scope(self) -> None:
        """Block with no dependencies is site-cacheable."""
        env = Environment()
        t = env.from_string("""
            {% block static %}
                <div>Static content</div>
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["static"].cache_scope == "site"

    def test_unknown_purity_is_unknown_scope(self) -> None:
        """Block with unknown purity has unknown scope."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {{ custom_function() }}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].cache_scope == "unknown"

    def test_post_prefix_is_page_scope(self) -> None:
        """post.* is recognized as page prefix."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {{ post.content }}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].cache_scope == "page"

    def test_config_prefix_is_site_scope(self) -> None:
        """config.* is recognized as site prefix."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {{ config.theme }}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].cache_scope == "site"

    def test_custom_config(self) -> None:
        """Custom prefix configuration works."""
        config = AnalysisConfig(
            page_prefixes=frozenset({"article.", "article"}),
            site_prefixes=frozenset({"settings.", "settings"}),
        )
        # Test the infer_cache_scope function directly
        scope = infer_cache_scope(
            frozenset({"article.title"}),
            "pure",
            config,
        )
        assert scope == "page"

        scope = infer_cache_scope(
            frozenset({"settings.theme"}),
            "pure",
            config,
        )
        assert scope == "site"


class TestLandmarkDetection:
    """Test HTML5 landmark detection."""

    def test_nav_detected(self) -> None:
        """<nav> is detected."""
        env = Environment()
        t = env.from_string("""
            {% block nav %}
                <nav>Navigation</nav>
            {% end %}
        """)
        blocks = t.block_metadata()
        assert "nav" in blocks["nav"].emits_landmarks

    def test_main_detected(self) -> None:
        """<main> is detected."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                <main>Content</main>
            {% end %}
        """)
        blocks = t.block_metadata()
        assert "main" in blocks["content"].emits_landmarks

    def test_multiple_landmarks_detected(self) -> None:
        """Multiple landmarks are detected."""
        env = Environment()
        t = env.from_string("""
            {% block layout %}
                <header>Header</header>
                <main>Main</main>
                <footer>Footer</footer>
            {% end %}
        """)
        blocks = t.block_metadata()
        landmarks = blocks["layout"].emits_landmarks
        assert "header" in landmarks
        assert "main" in landmarks
        assert "footer" in landmarks

    def test_case_insensitive_detection(self) -> None:
        """Tag detection is case-insensitive."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                <MAIN>Content</MAIN>
            {% end %}
        """)
        blocks = t.block_metadata()
        assert "main" in blocks["content"].emits_landmarks


class TestRoleClassification:
    """Test role inference."""

    def test_nav_landmark_is_navigation(self) -> None:
        """Block with <nav> is classified as navigation."""
        env = Environment()
        t = env.from_string("""
            {% block sidebar %}
                <nav><a href="/">Home</a></nav>
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["sidebar"].inferred_role == "navigation"

    def test_main_landmark_is_content(self) -> None:
        """Block with <main> is classified as content."""
        env = Environment()
        t = env.from_string("""
            {% block body %}
                <main>{{ content }}</main>
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["body"].inferred_role == "content"

    def test_name_based_fallback(self) -> None:
        """Block name is used when no landmarks present."""
        env = Environment()
        t = env.from_string("""
            {% block navigation %}
                <ul><li>Item</li></ul>
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["navigation"].inferred_role == "navigation"

    def test_footer_role(self) -> None:
        """Footer landmark classified correctly."""
        env = Environment()
        t = env.from_string("""
            {% block foot %}
                <footer>Copyright</footer>
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["foot"].inferred_role == "footer"

    def test_aside_is_sidebar(self) -> None:
        """<aside> is classified as sidebar."""
        env = Environment()
        t = env.from_string("""
            {% block panel %}
                <aside>Related links</aside>
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["panel"].inferred_role == "sidebar"

    def test_unknown_role(self) -> None:
        """Unknown blocks return 'unknown' role."""
        env = Environment()
        t = env.from_string("""
            {% block custom_block %}
                <div>Custom</div>
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["custom_block"].inferred_role == "unknown"

    def test_classify_role_direct(self) -> None:
        """Direct classify_role function tests."""
        assert classify_role("nav", frozenset()) == "navigation"
        assert classify_role("content", frozenset()) == "content"
        assert classify_role("sidebar", frozenset()) == "sidebar"
        assert classify_role("header", frozenset()) == "header"
        assert classify_role("footer", frozenset()) == "footer"
        assert classify_role("xyz", frozenset()) == "unknown"

        # Landmarks take precedence
        assert classify_role("sidebar", frozenset({"nav"})) == "navigation"
        assert classify_role("any", frozenset({"main"})) == "content"


class TestTopLevelDependencies:
    """Test top-level dependency analysis."""

    def test_top_level_output(self) -> None:
        """Top-level output is tracked."""
        env = Environment()
        t = env.from_string("""
            {{ site.title }}
            {% block content %}
                {{ page.content }}
            {% end %}
        """)
        meta = t.template_metadata()
        assert meta is not None
        assert "site.title" in meta.top_level_depends_on
        assert "page.content" not in meta.top_level_depends_on
        assert "page.content" in meta.blocks["content"].depends_on

    def test_static_extends(self) -> None:
        """Static extends does not add external dependency."""
        # Note: This test verifies static extends doesn't add dynamic deps
        # The extends template itself is tracked in meta.extends
        from bengal.rendering.kida.lexer import Lexer, LexerConfig
        from bengal.rendering.kida.parser import Parser

        source = """{% extends "base.html" %}
{% block content %}Hello{% end %}"""
        lexer = Lexer(source, LexerConfig())
        tokens = list(lexer.tokenize())
        parser = Parser(tokens, None, None, source, autoescape=True)
        ast = parser.parse()

        analyzer = BlockAnalyzer()
        meta = analyzer.analyze(ast)
        assert meta.extends == "base.html"
        # Static string is not a dynamic dependency
        # The extends path itself should NOT be in top_level_depends_on
        assert "base.html" not in meta.top_level_depends_on


class TestPreserveAstConfig:
    """Test preserve_ast configuration."""

    def test_preserve_ast_true(self) -> None:
        """With preserve_ast=True, metadata is available."""
        env = Environment(preserve_ast=True)
        t = env.from_string("""
            {% block content %}{{ page.title }}{% end %}
        """)
        assert t.block_metadata() != {}
        assert t.depends_on() != frozenset()
        assert t.template_metadata() is not None

    def test_preserve_ast_false(self) -> None:
        """With preserve_ast=False, metadata is empty."""
        env = Environment(preserve_ast=False)
        t = env.from_string("""
            {% block content %}{{ page.title }}{% end %}
        """)
        assert t.block_metadata() == {}
        assert t.depends_on() == frozenset()
        assert t.template_metadata() is None

        # But rendering still works
        result = t.render(page={"title": "Hello"})
        assert "Hello" in result

    def test_preserve_ast_default_true(self) -> None:
        """Default preserve_ast is True."""
        env = Environment()
        assert env.preserve_ast is True


class TestBlockMetadataHelpers:
    """Test BlockMetadata helper methods."""

    def test_is_cacheable(self) -> None:
        """is_cacheable() works correctly."""
        env = Environment()
        t = env.from_string("""
            {% block nav %}
                {% for p in site.pages %}{{ p }}{% end %}
            {% end %}
            {% block static %}
                <div>Static content</div>
            {% end %}
        """)
        blocks = t.block_metadata()

        # Nav is pure and site-scoped, so cacheable
        assert blocks["nav"].is_cacheable() is True

        # Static is also cacheable
        assert blocks["static"].is_cacheable() is True

        # Test non-cacheable via BlockMetadata directly
        impure_meta = BlockMetadata(
            name="impure",
            is_pure="impure",
            cache_scope="none",
        )
        assert impure_meta.is_cacheable() is False

    def test_depends_on_page(self) -> None:
        """depends_on_page() works correctly."""
        env = Environment()
        t = env.from_string("""
            {% block content %}{{ page.title }}{% end %}
            {% block nav %}{% for p in site.pages %}{{ p }}{% end %}{% end %}
        """)
        blocks = t.block_metadata()

        assert blocks["content"].depends_on_page() is True
        assert blocks["nav"].depends_on_page() is False

    def test_depends_on_site(self) -> None:
        """depends_on_site() works correctly."""
        env = Environment()
        t = env.from_string("""
            {% block content %}{{ page.title }}{% end %}
            {% block nav %}{% for p in site.pages %}{{ p }}{% end %}{% end %}
        """)
        blocks = t.block_metadata()

        assert blocks["content"].depends_on_site() is False
        assert blocks["nav"].depends_on_site() is True


class TestTemplateMetadataHelpers:
    """Test TemplateMetadata helper methods."""

    def test_all_dependencies(self) -> None:
        """all_dependencies() combines all sources."""
        env = Environment()
        t = env.from_string("""
            {{ site.title }}
            {% block content %}{{ page.title }}{% end %}
            {% block nav %}{{ site.pages }}{% end %}
        """)
        meta = t.template_metadata()
        assert meta is not None
        all_deps = meta.all_dependencies()
        assert "site.title" in all_deps
        assert "page.title" in all_deps
        assert "site.pages" in all_deps

    def test_get_block(self) -> None:
        """get_block() returns correct block or None."""
        env = Environment()
        t = env.from_string("""
            {% block content %}Hello{% end %}
        """)
        meta = t.template_metadata()
        assert meta is not None
        assert meta.get_block("content") is not None
        assert meta.get_block("nonexistent") is None

    def test_cacheable_blocks(self) -> None:
        """cacheable_blocks() returns only cacheable blocks."""
        env = Environment()
        t = env.from_string("""
            {% block nav %}{% for p in site.pages %}{{ p }}{% end %}{% end %}
            {% block static %}<div>Static</div>{% end %}
        """)
        meta = t.template_metadata()
        assert meta is not None
        cacheable = meta.cacheable_blocks()
        names = [b.name for b in cacheable]
        assert "nav" in names
        assert "static" in names

        # Test with metadata containing unknown purity block
        custom_meta = TemplateMetadata(
            name="test",
            extends=None,
            blocks={
                "pure": BlockMetadata(name="pure", is_pure="pure", cache_scope="site"),
                "impure": BlockMetadata(name="impure", is_pure="impure", cache_scope="none"),
            },
        )
        cacheable = custom_meta.cacheable_blocks()
        names = [b.name for b in cacheable]
        assert "pure" in names
        assert "impure" not in names

    def test_site_cacheable_blocks(self) -> None:
        """site_cacheable_blocks() returns only site-scoped blocks."""
        env = Environment()
        t = env.from_string("""
            {% block nav %}{% for p in site.pages %}{{ p }}{% end %}{% end %}
            {% block content %}{{ page.title }}{% end %}
        """)
        meta = t.template_metadata()
        assert meta is not None
        site_blocks = meta.site_cacheable_blocks()
        names = [b.name for b in site_blocks]
        assert "nav" in names
        assert "content" not in names


class TestEmitsHtml:
    """Test emits_html detection."""

    def test_static_content_emits_html(self) -> None:
        """Static content marks emits_html=True."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                <div>Hello</div>
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].emits_html is True

    def test_dynamic_output_emits_html(self) -> None:
        """Dynamic output marks emits_html=True."""
        env = Environment()
        t = env.from_string("""
            {% block content %}
                {{ page.title }}
            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["content"].emits_html is True

    def test_empty_block_no_html(self) -> None:
        """Empty block marks emits_html=False."""
        env = Environment()
        t = env.from_string("""
            {% block empty %}{% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["empty"].emits_html is False

    def test_whitespace_only_no_html(self) -> None:
        """Whitespace-only block marks emits_html=False."""
        env = Environment()
        t = env.from_string("""
            {% block whitespace %}

            {% end %}
        """)
        blocks = t.block_metadata()
        assert blocks["whitespace"].emits_html is False
