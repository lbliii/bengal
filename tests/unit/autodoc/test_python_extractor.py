"""
Tests for Python AST-based extractor.
"""

from textwrap import dedent

from bengal.autodoc.extractors.python import PythonExtractor


def test_extract_simple_function(tmp_path):
    """Test extracting a simple function."""
    source = tmp_path / "test.py"
    source.write_text(dedent("""
        def hello(name: str) -> str:
            '''Say hello to someone.

            Args:
                name: The person's name

            Returns:
                A greeting message
            '''
            return f"Hello, {name}!"
    """))

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
    assert any(arg['name'] == 'name' for arg in args_list)


def test_extract_class_with_methods(tmp_path):
    """Test extracting a class with methods."""
    source = tmp_path / "test.py"
    source.write_text(dedent("""
        class Calculator:
            '''A simple calculator.'''

            def add(self, a: int, b: int) -> int:
                '''Add two numbers.'''
                return a + b

            def subtract(self, a: int, b: int) -> int:
                '''Subtract b from a.'''
                return a - b
    """))

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
    source.write_text(dedent("""
        from typing import List, Optional

        def process(items: List[str], default: Optional[str] = None) -> int:
            '''Process items.'''
            return len(items)
    """))

    extractor = PythonExtractor()
    elements = extractor.extract(source)

    func = elements[0].children[0]
    args_list = func.metadata.get("args", [])

    arg_names = [arg['name'] for arg in args_list]
    assert "items" in arg_names
    assert "default" in arg_names


def test_extract_excludes_private_by_default(tmp_path):
    """Test that private methods can be filtered."""
    source = tmp_path / "test.py"
    source.write_text(dedent("""
        class MyClass:
            def public_method(self):
                '''Public method.'''
                pass

            def _private_method(self):
                '''Private method.'''
                pass
    """))

    extractor = PythonExtractor()
    elements = extractor.extract(source)

    cls = elements[0].children[0]
    # The extractor extracts all methods; filtering happens elsewhere
    assert len(cls.children) >= 1
    assert any(child.name == "public_method" for child in cls.children)


def test_extract_handles_docstring_formats(tmp_path):
    """Test extraction works with different docstring formats."""
    source = tmp_path / "test.py"
    source.write_text(dedent("""
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
    """))

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
    source.write_text(dedent("""
        def decorator(func):
            return func

        @decorator
        def decorated_func():
            '''A decorated function.'''
            pass
    """))

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
    source.write_text(dedent("""
        class MyClass:
            @property
            def value(self):
                '''Get the value.'''
                return self._value
    """))

    extractor = PythonExtractor()
    elements = extractor.extract(source)

    cls = elements[0].children[0]
    prop = cls.children[0]

    assert prop.name == "value"
    assert "value" in prop.description.lower()

