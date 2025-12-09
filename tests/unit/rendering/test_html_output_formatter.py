import pytest

from bengal.postprocess.html_output import format_html_output


@pytest.mark.parametrize("mode", ["pretty", "minify"])
def test_preserves_pre_and_code(mode: str) -> None:
    src = "<html>\n<body>\n<pre>  a  \n   b</pre>\n<code>  x  y  </code>\n</body>\n</html>\n"
    out = format_html_output(src, mode=mode)
    assert "<pre>  a  \n   b</pre>" in out
    assert "<code>  x  y  </code>" in out


def test_collapse_blank_lines_pretty() -> None:
    src = "<div>\n\n\n<p>hi</p>\n\n\n</div>\n"
    out = format_html_output(src, mode="pretty")
    # No triple blank lines
    assert "\n\n\n" not in out
    # Ends with single newline
    assert out.endswith("\n")


def test_minify_collapses_intertag_whitespace() -> None:
    src = '<head>\n    <meta charset="utf-8">    </head>\n<div>   </div>    <span> x </span>\n\n\n'
    out = format_html_output(src, mode="minify")
    # inter-tag gap collapsed (space or preserved newline)
    assert "> <" in out or ">\n<" in out
    assert "\n\n\n" not in out


def test_option_remove_comments() -> None:
    src = "<div><!-- comment --><p>ok</p><!--[if IE]>keep<![endif]--></div>\n"
    out = format_html_output(src, mode="minify", options={"remove_comments": True})
    assert "<!-- comment -->" not in out
    assert "<!--[if IE]>keep<![endif]-->" in out


def test_idempotent_behavior() -> None:
    src = "<div>\n\n<p>hi</p>\n\n</div>\n"
    once = format_html_output(src, mode="pretty")
    twice = format_html_output(once, mode="pretty")
    assert once == twice
