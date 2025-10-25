import sys

from bengal.utils.error_handlers import get_context_aware_help


def test_import_error_suggests_exports(monkeypatch):
    # Create a fake module with exports
    module_name = "_fake_mod_for_bengal_tests"
    fake_module = type("M", (), {})()
    fake_module.__all__ = ["Alpha", "Beta", "Gamma"]
    monkeypatch.setitem(sys.modules, module_name, fake_module)

    try:
        # Simulate ImportError message shape
        err = ImportError(f"cannot import name 'Alph' from '{module_name}' (/tmp/x.py)")
        help_info = get_context_aware_help(err)
        assert help_info is not None
        assert any("Alpha" in line for line in help_info.lines)
    finally:
        sys.modules.pop(module_name, None)


def test_attribute_error_dict_hint():
    err = AttributeError("'dict' object has no attribute 'slug'")
    help_info = get_context_aware_help(err)
    assert help_info is not None
    assert any("dict.get" in line for line in help_info.lines)


def test_type_error_generic_guidance():
    err = TypeError("foo() takes 2 positional arguments but 3 were given")
    help_info = get_context_aware_help(err)
    assert help_info is not None
    assert any("positional/keyword" in line for line in help_info.lines)
