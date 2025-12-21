import builtins

from bengal.errors.traceback import CompactTracebackRenderer, MinimalTracebackRenderer


def test_compact_renderer_importerror_hint_shown(monkeypatch, capsys):
    # Force plain output (no rich) for predictable capture
    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setenv("CI", "1")

    module_name = "_fake_mod_for_renderer"

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == module_name:
            # Fake module with exports similar to __all__ behavior
            mod = type("M", (), {})()
            mod.__all__ = ["Alpha", "Beta", "Gamma"]
            return mod
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    renderer = CompactTracebackRenderer(config=None)
    try:
        raise ImportError(f"cannot import name 'Alph' from '{module_name}' (/tmp/x.py)")
    except Exception as e:
        renderer.display_exception(e)

    out = capsys.readouterr().out
    # Should include a context-aware tip and suggestions listing Alpha
    assert "Did you mean" in out or "Hint" in out
    assert "Alpha" in out


def test_minimal_renderer_attributeerror_hint(monkeypatch, capsys):
    # Force plain output
    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setenv("CI", "1")

    renderer = MinimalTracebackRenderer(config=None)
    try:
        d = {}
        # Trigger AttributeError on dict access without useless expression
        _ = d.slug  # type: ignore[attr-defined]
    except Exception as e:
        renderer.display_exception(e)

    out = capsys.readouterr().out
    # Minimal should include a one-line "Hint:" with guidance
    assert "Hint:" in out
    assert "dict.get" in out
