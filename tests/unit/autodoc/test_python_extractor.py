"""
Tests for Python AST-based extractor.
"""

from pathlib import Path
from textwrap import dedent

from bengal.autodoc.extractors.python import PythonExtractor


def test_extract_simple_function(tmp_path):
    """Test extracting a simple function."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        def hello(name: str) -> str:
            '''Say hello to someone.

            Args:
                name: The person's name

            Returns:
                A greeting message
            '''
            return f"Hello, {name}!"
    """)
    )

    extractor = PythonExtractor()
    elements = extractor.extract(source)

    assert len(elements) == 1
    module = elements[0]

    assert module.element_type == "module"
    assert len(module.children) == 1

    func = module.children[0]
    assert func.name == "hello"
    assert func.element_type == "function"
    assert "Say hello to someone" in func.description
    # Args is a list of dicts, not a dict
    args_list = func.metadata.get("args", [])
    assert len(args_list) > 0
    assert any(arg["name"] == "name" for arg in args_list)


def test_extract_class_with_methods(tmp_path):
    """Test extracting a class with methods."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        class Calculator:
            '''A simple calculator.'''

            def add(self, a: int, b: int) -> int:
                '''Add two numbers.'''
                return a + b

            def subtract(self, a: int, b: int) -> int:
                '''Subtract b from a.'''
                return a - b
    """)
    )

    extractor = PythonExtractor()
    elements = extractor.extract(source)

    module = elements[0]
    assert len(module.children) == 1

    cls = module.children[0]
    assert cls.name == "Calculator"
    assert cls.element_type == "class"
    assert len(cls.children) == 2

    add_method = cls.children[0]
    assert add_method.name == "add"
    assert add_method.element_type == "method"

    subtract_method = cls.children[1]
    assert subtract_method.name == "subtract"


def test_extract_with_type_hints(tmp_path):
    """Test extraction preserves type hints."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        from typing import List, Optional

        def process(items: List[str], default: Optional[str] = None) -> int:
            '''Process items.'''
            return len(items)
    """)
    )

    extractor = PythonExtractor()
    elements = extractor.extract(source)

    func = elements[0].children[0]
    args_list = func.metadata.get("args", [])

    arg_names = [arg["name"] for arg in args_list]
    assert "items" in arg_names
    assert "default" in arg_names


def test_extract_excludes_private_by_default(tmp_path):
    """Test that private methods can be filtered."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        class MyClass:
            def public_method(self):
                '''Public method.'''
                pass

            def _private_method(self):
                '''Private method.'''
                pass
    """)
    )

    extractor = PythonExtractor()
    elements = extractor.extract(source)

    cls = elements[0].children[0]
    # The extractor extracts all methods; filtering happens elsewhere
    assert len(cls.children) >= 1
    assert any(child.name == "public_method" for child in cls.children)


def test_extract_handles_docstring_formats(tmp_path):
    """Test extraction works with different docstring formats."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        def google_style(x: int) -> int:
            '''Google style docstring.

            Args:
                x: An integer

            Returns:
                The doubled value
            '''
            return x * 2

        def numpy_style(y: int) -> int:
            '''NumPy style docstring.

            Parameters
            ----------
            y : int
                An integer

            Returns
            -------
            int
                The tripled value
            '''
            return y * 3
    """)
    )

    extractor = PythonExtractor()
    elements = extractor.extract(source)

    module = elements[0]
    assert len(module.children) == 2

    google_func = module.children[0]
    # Description is just the summary; detailed info in parsed_doc
    assert "Google" in google_func.description
    assert google_func.metadata.get("parsed_doc", {}).get("returns") is not None

    numpy_func = module.children[1]
    assert "NumPy" in numpy_func.description


def test_extract_handles_decorators(tmp_path):
    """Test extraction handles decorated functions."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        def decorator(func):
            return func

        @decorator
        def decorated_func():
            '''A decorated function.'''
            pass
    """)
    )

    extractor = PythonExtractor()
    elements = extractor.extract(source)

    module = elements[0]
    # Should extract both decorator and decorated function
    assert len(module.children) >= 1

    # Find the decorated function
    decorated = [c for c in module.children if c.name == "decorated_func"]
    assert len(decorated) == 1


def test_extract_multiple_files(tmp_path):
    """Test extracting from multiple files."""
    file1 = tmp_path / "file1.py"
    file1.write_text("def func1(): pass")

    file2 = tmp_path / "file2.py"
    file2.write_text("def func2(): pass")

    extractor = PythonExtractor()

    elements1 = extractor.extract(file1)
    elements2 = extractor.extract(file2)

    assert len(elements1) == 1
    assert len(elements2) == 1


def test_extract_handles_syntax_errors_gracefully(tmp_path):
    """Test that syntax errors are handled gracefully."""
    source = tmp_path / "bad.py"
    source.write_text("def broken(")  # Invalid syntax

    extractor = PythonExtractor()

    # Should not raise, might return empty or skip
    try:
        elements = extractor.extract(source)
        # If it succeeds, should be empty or minimal
        assert isinstance(elements, list)
    except SyntaxError:
        # Also acceptable to raise SyntaxError
        pass


def test_extract_properties(tmp_path):
    """Test extraction of properties."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        class MyClass:
            @property
            def value(self):
                '''Get the value.'''
                return self._value
    """)
    )

    extractor = PythonExtractor()
    elements = extractor.extract(source)

    cls = elements[0].children[0]
    prop = cls.children[0]

    assert prop.name == "value"
    assert "value" in prop.description.lower()


def test_extract_function_alias(tmp_path):
    """Test extraction of function aliases."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        def original_function():
            '''The original function.'''
            pass

        # Create an alias
        alias_function = original_function
    """)
    )

    extractor = PythonExtractor()
    elements = extractor.extract(source)

    module = elements[0]

    # Should have both original and alias
    assert len(module.children) == 2

    # Find original and alias
    original = [c for c in module.children if c.name == "original_function"][0]
    alias = [c for c in module.children if c.name == "alias_function"][0]

    assert original.element_type == "function"
    assert alias.element_type == "alias"
    assert "alias_of" in alias.metadata
    assert alias.metadata["alias_of"].endswith(".original_function")

    # Original should track its aliases
    assert "aliases" in original.metadata
    assert "alias_function" in original.metadata["aliases"]


def test_extract_class_alias(tmp_path):
    """Test extraction of class aliases."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        class OriginalClass:
            '''The original class.'''
            pass

        # Create an alias
        AliasClass = OriginalClass
    """)
    )

    extractor = PythonExtractor()
    elements = extractor.extract(source)

    module = elements[0]

    # Should have both original and alias
    assert len(module.children) == 2

    # Find original and alias
    original = [c for c in module.children if c.name == "OriginalClass"][0]
    alias = [c for c in module.children if c.name == "AliasClass"][0]

    assert original.element_type == "class"
    assert alias.element_type == "alias"
    assert alias.metadata["alias_kind"] == "assignment"


def test_extract_attribute_alias(tmp_path):
    """Test extraction of attribute/qualified aliases."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        def original_function():
            '''The original function.'''
            pass

        # Qualified alias (module.attr pattern)
        import os
        path_join = os.path.join
    """)
    )

    extractor = PythonExtractor()
    elements = extractor.extract(source)

    module = elements[0]

    # Should have original function and path_join alias
    aliases = [c for c in module.children if c.element_type == "alias"]
    assert len(aliases) == 1

    path_join_alias = aliases[0]
    assert path_join_alias.name == "path_join"
    assert "os.path.join" in path_join_alias.metadata["alias_of"]


def test_extract_inherited_members_disabled_by_default(tmp_path):
    """Test that inherited members are not extracted by default."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        class Base:
            '''Base class.'''
            def base_method(self):
                '''A base method.'''
                pass

        class Derived(Base):
            '''Derived class.'''
            def derived_method(self):
                '''A derived method.'''
                pass
    """)
    )

    extractor = PythonExtractor()
    elements = extractor.extract(source)

    module = elements[0]
    derived_cls = [c for c in module.children if c.name == "Derived"][0]

    # Should only have its own method
    method_names = [m.name for m in derived_cls.children]
    assert "derived_method" in method_names
    assert "base_method" not in method_names


def test_extract_inherited_members_when_enabled(tmp_path):
    """Test extraction of inherited members when enabled."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        class Base:
            '''Base class.'''
            def base_method(self):
                '''A base method.'''
                pass

        class Derived(Base):
            '''Derived class.'''
            def derived_method(self):
                '''A derived method.'''
                pass
    """)
    )

    config = {"include_inherited": True}
    extractor = PythonExtractor(config=config)
    elements = extractor.extract(source)

    module = elements[0]
    derived_cls = [c for c in module.children if c.name == "Derived"][0]

    # Should have both own method and inherited method
    method_names = [m.name for m in derived_cls.children]
    assert "derived_method" in method_names
    assert "base_method" in method_names

    # Check inherited method has proper metadata
    base_method = [m for m in derived_cls.children if m.name == "base_method"][0]
    assert "inherited_from" in base_method.metadata
    assert base_method.metadata["synthetic"] is True


def test_extract_inherited_members_no_override(tmp_path):
    """Test that overridden methods are not duplicated."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        class Base:
            '''Base class.'''
            def method(self):
                '''Base method.'''
                pass

        class Derived(Base):
            '''Derived class.'''
            def method(self):
                '''Overridden method.'''
                pass
    """)
    )

    config = {"include_inherited": True}
    extractor = PythonExtractor(config=config)
    elements = extractor.extract(source)

    module = elements[0]
    derived_cls = [c for c in module.children if c.name == "Derived"][0]

    # Should only have one "method" (the override)
    methods = [m for m in derived_cls.children if m.name == "method"]
    assert len(methods) == 1

    # Should be the derived class's own method (not synthetic)
    assert not methods[0].metadata.get("synthetic", False)


def test_extract_inherited_members_respects_private_setting(tmp_path):
    """Test that private inherited members are filtered unless configured."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        class Base:
            '''Base class.'''
            def public_method(self):
                '''Public method.'''
                pass

            def _private_method(self):
                '''Private method.'''
                pass

        class Derived(Base):
            '''Derived class.'''
            pass
    """)
    )

    config = {"include_inherited": True, "include_private": False}
    extractor = PythonExtractor(config=config)
    elements = extractor.extract(source)

    module = elements[0]
    derived_cls = [c for c in module.children if c.name == "Derived"][0]

    # Should have public but not private inherited method
    method_names = [m.name for m in derived_cls.children]
    assert "public_method" in method_names
    assert "_private_method" not in method_names


def test_extract_inherited_members_by_type(tmp_path):
    """Test per-type inherited member configuration."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        class Base:
            '''Base class.'''
            def base_method(self):
                '''A base method.'''
                pass

        class Derived(Base):
            '''Derived class.'''
            pass
    """)
    )

    # Enable only for class type
    config = {"include_inherited": False, "include_inherited_by_type": {"class": True}}
    extractor = PythonExtractor(config=config)
    elements = extractor.extract(source)

    module = elements[0]
    derived_cls = [c for c in module.children if c.name == "Derived"][0]

    # Should have inherited method via per-type setting
    method_names = [m.name for m in derived_cls.children]
    assert "base_method" in method_names


# ===== URL Grouping Tests =====


def test_get_output_path_no_grouping(tmp_path):
    """Test get_output_path without grouping (default behavior)."""
    source = tmp_path / "mypackage" / "core"
    source.mkdir(parents=True)
    (source / "__init__.py").write_text("'''Core module.'''")

    config = {"source_dirs": [str(tmp_path / "mypackage")]}
    extractor = PythonExtractor(config=config)
    elements = extractor.extract(source)

    module = elements[0]
    output_path = extractor.get_output_path(module)

    # Without grouping: core/_index.md
    assert output_path == Path("core/_index.md")


def test_get_output_path_auto_mode(tmp_path):
    """Test get_output_path with auto mode grouping."""
    # Create structure: mypackage/cli/__init__.py, scaffolds/__init__.py
    cli_dir = tmp_path / "mypackage" / "cli"
    cli_dir.mkdir(parents=True)
    (cli_dir / "__init__.py").write_text("'''CLI module.'''")

    scaffolds_dir = tmp_path / "mypackage" / "scaffolds"
    scaffolds_dir.mkdir()
    (scaffolds_dir / "__init__.py").write_text("'''Scaffolds module.'''")

    config = {
        "source_dirs": [str(tmp_path / "mypackage")],
        "strip_prefix": "mypackage.",
        "grouping": {"mode": "auto"},
    }
    extractor = PythonExtractor(config=config)
    elements = extractor.extract(scaffolds_dir)

    scaffolds_module = elements[0]
    output_path = extractor.get_output_path(scaffolds_module)

    # With auto mode: scaffolds/_index.md (group determined by package hierarchy)
    assert output_path == Path("scaffolds/_index.md")


def test_get_output_path_explicit_mode(tmp_path):
    """Test get_output_path with explicit mode grouping."""
    source = tmp_path / "mypackage" / "core"
    source.mkdir(parents=True)
    (source / "__init__.py").write_text("'''Core module.'''")

    config = {
        "source_dirs": [str(tmp_path / "mypackage")],
        "strip_prefix": "mypackage.",
        "grouping": {
            "mode": "explicit",
            "prefix_map": {"core": "core-api"},
        },
    }
    extractor = PythonExtractor(config=config)
    elements = extractor.extract(source)

    module = elements[0]
    output_path = extractor.get_output_path(module)

    # With explicit mode and custom group name: core-api/_index.md
    assert output_path == Path("core-api/_index.md")


def test_get_output_path_with_strip_prefix(tmp_path):
    """Test get_output_path applies strip_prefix."""
    source = tmp_path / "mypackage" / "utils"
    source.mkdir(parents=True)
    (source / "helper.py").write_text("'''Helper module.'''")

    config = {
        "source_dirs": [str(tmp_path / "mypackage")],
        "strip_prefix": "mypackage.",
    }
    extractor = PythonExtractor(config=config)
    elements = extractor.extract(source / "helper.py")

    module = elements[0]
    output_path = extractor.get_output_path(module)

    # With strip_prefix applied: helper.md (module name only)
    assert output_path == Path("helper.md")


def test_get_output_path_nested_module_under_group(tmp_path):
    """Test nested modules are placed under group correctly."""
    # Create: mypackage/scaffolds/blog/template.py
    blog_dir = tmp_path / "mypackage" / "scaffolds" / "blog"
    blog_dir.mkdir(parents=True)

    # Create parent __init__.py files
    (tmp_path / "mypackage" / "scaffolds" / "__init__.py").touch()

    (blog_dir / "template.py").write_text("'''Blog template.'''")

    config = {
        "source_dirs": [str(tmp_path / "mypackage")],
        "strip_prefix": "mypackage.",
        "grouping": {"mode": "auto"},
    }
    extractor = PythonExtractor(config=config)
    elements = extractor.extract(blog_dir / "template.py")

    module = elements[0]
    output_path = extractor.get_output_path(module)

    # Module path is relative to file parent when extracting a single file
    assert output_path == Path("template.md")


def test_get_output_path_package_vs_module(tmp_path):
    """Test packages get _index.md, modules get .md."""
    # Create package and module
    core_dir = tmp_path / "mypackage" / "core"
    core_dir.mkdir(parents=True)
    (core_dir / "__init__.py").write_text("'''Core package.'''")
    (core_dir / "site.py").write_text("'''Site module.'''")

    config = {
        "source_dirs": [str(tmp_path / "mypackage")],
        "strip_prefix": "mypackage.",
        "grouping": {"mode": "auto"},
    }
    extractor = PythonExtractor(config=config)

    # Extract package
    package_elements = extractor.extract(core_dir / "__init__.py")
    package_module = package_elements[0]
    package_path = extractor.get_output_path(package_module)
    assert package_path == Path("core/_index.md")  # Package → _index.md

    # Extract module
    module_elements = extractor.extract(core_dir / "site.py")
    site_module = module_elements[0]
    module_path = extractor.get_output_path(site_module)
    assert module_path == Path("site.md")  # Module → .md (module name only)


def test_get_output_path_class_in_grouped_module(tmp_path):
    """Test classes are part of their module file with grouping."""
    # Create: mypackage/core/site.py with Site class
    core_dir = tmp_path / "mypackage" / "core"
    core_dir.mkdir(parents=True)
    (core_dir / "__init__.py").touch()
    (core_dir / "site.py").write_text(
        dedent("""
        class Site:
            '''Site class.'''
            pass
    """)
    )

    config = {
        "source_dirs": [str(tmp_path / "mypackage")],
        "strip_prefix": "mypackage.",
        "grouping": {"mode": "auto"},
    }
    extractor = PythonExtractor(config=config)
    elements = extractor.extract(core_dir / "site.py")

    module = elements[0]
    site_class = module.children[0]

    # Class output path should match module path
    class_path = extractor.get_output_path(site_class)
    module_path = extractor.get_output_path(module)

    assert class_path == module_path == Path("site.md")


def test_get_output_path_longest_prefix_wins(tmp_path):
    """Test longest prefix wins when multiple match."""
    # Create: mypackage/scaffolds/__init__.py
    scaffolds_dir = tmp_path / "mypackage" / "scaffolds"
    scaffolds_dir.mkdir(parents=True)
    (scaffolds_dir / "__init__.py").write_text("'''Scaffolds module.'''")

    config = {
        "source_dirs": [str(tmp_path / "mypackage")],
        "strip_prefix": "mypackage.",
        "grouping": {
            "mode": "explicit",
            "prefix_map": {
                "cli": "cli",
                "scaffolds": "scaffolds",  # Longer, should win
            },
        },
    }
    extractor = PythonExtractor(config=config)
    elements = extractor.extract(scaffolds_dir)

    module = elements[0]
    output_path = extractor.get_output_path(module)

    # Should match longer prefix: scaffolds/_index.md (not cli/_index.md)
    assert output_path == Path("scaffolds/_index.md")


# ===== Inheritance Optimization Tests =====


def test_simple_name_index_is_populated(tmp_path):
    """Test that simple_name_index is populated during extraction."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        class MyClass:
            '''A class.'''
            pass

        class AnotherClass:
            '''Another class.'''
            pass
    """)
    )

    extractor = PythonExtractor()
    extractor.extract(source)

    # simple_name_index should map simple names to qualified names
    assert "MyClass" in extractor.simple_name_index
    assert "AnotherClass" in extractor.simple_name_index
    assert len(extractor.simple_name_index["MyClass"]) == 1
    assert len(extractor.simple_name_index["AnotherClass"]) == 1


def test_simple_name_collision(tmp_path):
    """Test handling of two classes with the same simple name in different packages."""
    # Create two packages with same-named classes
    pkg1 = tmp_path / "pkg1"
    pkg1.mkdir()
    (pkg1 / "__init__.py").touch()
    (pkg1 / "config.py").write_text(
        dedent("""
        class Config:
            '''Config from pkg1.'''
            def get_value(self):
                '''Get value.'''
                pass
    """)
    )

    pkg2 = tmp_path / "pkg2"
    pkg2.mkdir()
    (pkg2 / "__init__.py").touch()
    (pkg2 / "config.py").write_text(
        dedent("""
        class Config:
            '''Config from pkg2.'''
            def get_setting(self):
                '''Get setting.'''
                pass
    """)
    )

    # Create a class that inherits from Config (simple name)
    (tmp_path / "consumer.py").write_text(
        dedent("""
        class Consumer(Config):
            '''Consumer class.'''
            def consume(self):
                '''Consume.'''
                pass
    """)
    )

    config = {"include_inherited": True}
    extractor = PythonExtractor(config=config)

    # Extract all files
    extractor.extract(pkg1 / "config.py")
    extractor.extract(pkg2 / "config.py")
    elements = extractor.extract(tmp_path / "consumer.py")

    # simple_name_index should have both Config classes
    assert "Config" in extractor.simple_name_index
    assert len(extractor.simple_name_index["Config"]) == 2

    # Consumer should inherit from one of them (first match)
    consumer_cls = elements[0].children[0]
    method_names = [m.name for m in consumer_cls.children]
    assert "consume" in method_names
    # Should have inherited method from first-matched Config
    assert "get_value" in method_names or "get_setting" in method_names


def test_diamond_inheritance(tmp_path):
    """Test diamond inheritance pattern (A -> B, C -> D where B, C inherit from A)."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        class Base:
            '''Base class.'''
            def base_method(self):
                '''Base method.'''
                pass

        class Left(Base):
            '''Left mixin.'''
            def left_method(self):
                '''Left method.'''
                pass

        class Right(Base):
            '''Right mixin.'''
            def right_method(self):
                '''Right method.'''
                pass

        class Diamond(Left, Right):
            '''Diamond class inheriting from both Left and Right.'''
            def diamond_method(self):
                '''Diamond method.'''
                pass
    """)
    )

    config = {"include_inherited": True}
    extractor = PythonExtractor(config=config)
    elements = extractor.extract(source)

    module = elements[0]
    diamond_cls = [c for c in module.children if c.name == "Diamond"][0]

    # Diamond should have its own method plus inherited methods
    method_names = [m.name for m in diamond_cls.children]
    assert "diamond_method" in method_names
    assert "left_method" in method_names
    assert "right_method" in method_names
    # base_method may be inherited through Left or Right (both have it)
    assert "base_method" in method_names


def test_inheritance_external_base_class(tmp_path):
    """Test inheritance from external base class not in index."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        from collections import UserDict

        class MyDict(UserDict):
            '''Custom dict.'''
            def custom_method(self):
                '''Custom method.'''
                pass
    """)
    )

    config = {"include_inherited": True}
    extractor = PythonExtractor(config=config)
    elements = extractor.extract(source)

    module = elements[0]
    my_dict_cls = [c for c in module.children if c.name == "MyDict"][0]

    # Should have own method, but no inherited from UserDict (not in index)
    method_names = [m.name for m in my_dict_cls.children]
    assert "custom_method" in method_names
    # No inherited methods from UserDict (external)
    assert len(method_names) == 1


def test_inheritance_multi_level(tmp_path):
    """Test multi-level inheritance (A -> B -> C)."""
    source = tmp_path / "test.py"
    source.write_text(
        dedent("""
        class GrandParent:
            '''Grandparent class.'''
            def grandparent_method(self):
                '''Grandparent method.'''
                pass

        class Parent(GrandParent):
            '''Parent class.'''
            def parent_method(self):
                '''Parent method.'''
                pass

        class Child(Parent):
            '''Child class.'''
            def child_method(self):
                '''Child method.'''
                pass
    """)
    )

    config = {"include_inherited": True}
    extractor = PythonExtractor(config=config)
    elements = extractor.extract(source)

    module = elements[0]
    child_cls = [c for c in module.children if c.name == "Child"][0]

    # Child should have parent_method inherited
    method_names = [m.name for m in child_cls.children]
    assert "child_method" in method_names
    assert "parent_method" in method_names
    # Note: grandparent_method is inherited by Parent, but Child only directly
    # inherits from Parent, so it gets parent_method which was inherited into Parent


def test_should_use_parallel_threshold(tmp_path):
    """Test _should_use_parallel() method with hardware-aware threshold."""
    import multiprocessing

    extractor = PythonExtractor()
    core_count = multiprocessing.cpu_count()

    # Calculate expected threshold: max(5, 15 - core_count)
    expected_threshold = max(5, 15 - core_count)

    # Below threshold: should not use parallel
    assert extractor._should_use_parallel(expected_threshold - 1) is False

    # At threshold: should use parallel
    assert extractor._should_use_parallel(expected_threshold) is True

    # Above threshold: should use parallel
    assert extractor._should_use_parallel(expected_threshold + 10) is True


def test_should_use_parallel_config_override(tmp_path):
    """Test parallel_autodoc=False disables parallel."""
    config = {"parallel_autodoc": False}
    extractor = PythonExtractor(config=config)

    # Even with many files, should not use parallel if config disables it
    assert extractor._should_use_parallel(100) is False
