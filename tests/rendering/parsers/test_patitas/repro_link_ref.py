from bengal.parsing.backends.patitas import parse


def test_link_ref_first_wins():
    markdown = "[foo]\n\n[foo]: first\n[foo]: second\n"
    # Expected: <p><a href="first">foo</a></p>
    actual = parse(markdown)
    assert 'href="first"' in actual
    assert 'href="second"' not in actual


def test_link_ref_multi_line_url():
    markdown = "[foo]:\n/url\n\n[foo]\n"
    # Expected: <p><a href="/url">foo</a></p>
    actual = parse(markdown)
    assert '<a href="/url">foo</a>' in actual


def test_list_tab_continuation():
    markdown = "  - foo\n\n\tbar\n"
    # Expected: <ul><li><p>foo</p><p>bar</p></li></ul>
    actual = parse(markdown)
    assert "<p>foo</p>" in actual
    assert "<p>bar</p>" in actual
    assert "<code>" not in actual


def test_list_nested_tab():
    markdown = " - foo\n   - bar\n\t - baz\n"
    actual = parse(markdown)
    assert "<li>foo" in actual
    assert "<li>bar" in actual
    assert "<li>baz" in actual