from bengal.rendering.parsers.patitas import create_markdown


def test_lexer_window_variable_substitution():
    """Verify variables are substituted in the Lexer Window."""
    md = create_markdown()
    context = {"user": "Bengal", "level": "###"}

    # 1. Simple inline substitution
    source = "Hello {{ user }}!"
    # We need to use the wrapper logic or simulate it.
    # In Bengal, PatitasParser.parse_with_context handles the plugin setup.
    from bengal.rendering.plugins import VariableSubstitutionPlugin

    var_plugin = VariableSubstitutionPlugin(context)

    html = md(source, text_transformer=var_plugin.substitute_variables)
    assert "Hello Bengal!" in html


def test_lexer_window_block_elevation():
    """Verify variables can contain block markers (Elevation)."""
    md = create_markdown()
    context = {"heading": "# Elevated Heading"}
    from bengal.rendering.plugins import VariableSubstitutionPlugin

    var_plugin = VariableSubstitutionPlugin(context)

    source = "{{ heading }}"
    html = md(source, text_transformer=var_plugin.substitute_variables)

    # If the window thing works, the Lexer sees "# Elevated Heading"
    # and produces a Heading token, not a Paragraph with text.
    assert "<h1>Elevated Heading</h1>" in html
    assert "<p>" not in html


def test_lexer_window_list_elevation():
    """Verify variables can contain list markers."""
    md = create_markdown()
    context = {"items": "- Item 1\n- Item 2"}
    from bengal.rendering.plugins import VariableSubstitutionPlugin

    var_plugin = VariableSubstitutionPlugin(context)

    source = "{{ items }}"
    html = md(source, text_transformer=var_plugin.substitute_variables)

    assert "<ul>" in html
    assert "<li>Item 1</li>" in html
    assert "<li>Item 2</li>" in html
