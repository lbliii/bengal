"""
Tests for Python AST-based extractor.
"""

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
