"""Parity tests: the fast asset-extraction scanner must match the reference parser.

``extract_assets_from_html`` was reimplemented as a single-pass scanner (replacing
a slow ``HTMLParser`` subclass that was ~24% of cold-build render time). The set it
returns feeds the incremental dependency map, so it must be byte-identical to the
old parser. The golden is the LIVE reference parser (``AssetExtractorParser``), never
hand-written values — so the test cannot encode a wrong expectation.

The corpus encodes every divergence the design + adversarial critique surfaced:
comments, conditional comments, <script>/<style> CDATA, @import, '>' inside quoted
attrs, rel substring matching, srcset (incl. the empty-candidate abort), self-closing,
case, unquoted values, HTML-entity unescaping across contexts, duplicate attrs
(last-wins), fake-close-in-string, bogus comments, intra-tag whitespace, and
malformed/truncated input.
"""

from __future__ import annotations

import pytest

from bengal.rendering.asset_extractor import AssetExtractorParser, extract_assets_from_html

# HTML inputs only — the reference parser supplies the expected set.
CORPUS = [
    # comments & declarations
    '<!-- <img src="/HIDDEN.png"> --><img src="/REAL.png">',
    '<!--[if IE]><img src="/ie.png"><![endif]--><img src="/real2.png">',
    "<!notacomment><img src=/decl.png>",
    "<!-->oops<img src=/abrupt.png>",
    "<!doctype html><img src=/doc.png>",
    "<?xml version='1.0'?><img src=/pi.png>",
    # script / style CDATA
    '<script>var x = "<img src=\'/INSCRIPT.png\'>";</script><img src="/REAL.png">',
    '<script src="/app.js">document.write(\'<img src="/INLINE.png">\')</script>',
    "<script>var s='</scr'+'ipt>'</script><img src='/after.png'>",
    "<script src='/a.js'></script  ><img src='/aftws.png'>",
    '<style>/* <img src="/INSTYLE.png"> */ @import url(/imp.css);</style>',
    "<style>@import url('/q1.css'); @import url(\"/q2.css\"); @import url(/q3.css);</style>",
    "<style>@import url(/s.css);</style ><img src='/y.png'>",
    # attribute edge cases
    '<img alt="a > b" src="/REAL.png">',
    '<img data-foo="<bar>" src="/REAL2.png">',
    '<link rel="alternate stylesheet" href="/alt.css"><link rel="canonical" href="/no.css">',
    '<link rel="preload" href="/p.woff2" as="font"><link rel="prefetch" href="/pf.js">',
    '<link rel="icon" href="/favicon.ico">',
    '<img src="/sc.png"/><source srcset="/a.png 1x, /b.png 2x">',
    '<IMG SRC="/CASE.png"><SCRIPT SRC="/case.js"></SCRIPT>',
    '<img srcset="/x.png 480w, /y.png 800w">',
    "<img src=/unq.png>",
    '<iframe src="/embed.html"></iframe>',
    '<source src="/movie.mp4" type="video/mp4">',
    "<img\n src='/nl.png'>",
    "<img\tsrc='/tab.png'>",
    "<img src = '/eqws.png'>",
    "<img    src='/multi.png'   alt=x>",
    "<img src=''>",
    "<img src='   '>",
    "<img src='/first.png' src='/second.png'>",  # duplicate -> last wins
    # entity unescaping across contexts (parser unescapes attr values)
    '<img src="/a.css?x=1&amp;y=2">',
    "<img src=/a&amp;b.png>",
    "<img srcset='/a&amp;b.png 1x'>",
    "<img src=/a&#47;b.png>",
    "<img src=/a&#x2F;b.png>",
    # data / absolute URLs
    '<img src="data:image/png;base64,AAAA">',
    '<script src="https://cdn.example.com/x.js"></script>',
    # srcset abort (empty candidate) — parity must replicate the partial result
    "<img srcset=', /a 1x'><img src='/SECOND.png'>",
    "<img src='/FIRST.png'><img srcset=', /a 1x'>",
    "<source srcset=', /a 1x'><img src='/SRC2.png'>",
    # malformed / truncated
    "",
    '<!-- unterminated comment <img src="/never.png">',
    '<script>unterminated <img src="/never.png">',
    "<img src='/open.png'",  # unterminated tag
    "plain text no tags",
]


def _reference(html: str) -> set[str]:
    return AssetExtractorParser().feed(html).get_assets()


@pytest.mark.parametrize("html", CORPUS)
def test_scanner_matches_reference_parser(html: str) -> None:
    assert extract_assets_from_html(html) == _reference(html), (
        f"scanner diverged from reference parser on: {html!r}\n"
        f"  scanner:   {sorted(extract_assets_from_html(html))}\n"
        f"  reference: {sorted(_reference(html))}"
    )


def test_scanner_matches_reference_on_real_build_html(tmp_path):
    """Build a real site and assert scanner == parser on every output page."""
    import random

    # Reuse the benchmark fixture generator for realistic, directive-free HTML.
    import sys

    from bengal.core.site import Site
    from bengal.orchestration.build.options import BuildOptions

    sys.path.insert(0, "benchmarks")
    from benchmark_gil_speedup import create_site

    random.seed(42)
    root = tmp_path / "site"
    create_site("blog", 40, root)
    site = Site.from_config(root)
    site.build(BuildOptions(force_sequential=True, incremental=False, verbose=False, quiet=True))

    html_files = list(site.output_dir.rglob("*.html"))
    assert html_files, "build produced no HTML to compare"
    for path in html_files:
        html = path.read_text(encoding="utf-8")
        assert extract_assets_from_html(html) == _reference(html), (
            f"scanner diverged from reference parser on output file: {path}"
        )
