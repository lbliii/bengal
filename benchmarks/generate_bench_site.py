#!/usr/bin/env python3
"""
Generate a deterministic large site fixture for end-to-end build benchmarking.

Issue #350, saga S8. The Phase-1 benchmarking was unreliable for three reasons,
all of which this generator fixes:

1. **Nondeterministic output.** The default theme's ``random_posts`` widget uses
   an unseeded ``| sample`` filter, so the same build differs run-to-run — which
   makes byte-parity (thread vs shard) comparisons vacuous. This generator writes
   a local ``templates/page.html`` override that drops that one widget (copied
   from the default theme so all other blocks stay intact), making builds
   byte-reproducible.
2. **No realistic large fixture.** Generates N deterministic content pages across
   several sections, with a fixed tag pool, dated frontmatter, headings, code
   blocks, and internal links — representative render cost, zero randomness.
3. **Cycled-heap microbench bias.** A real fixture of N *distinct* pages exercises
   the full parsed-corpus heap a real cold build holds (the thing that made
   Phase-1 fork regress), unlike cycling a handful of warm pages.

Usage
-----
    PYTHONPATH=. python benchmarks/generate_bench_site.py <out_dir> --pages 800

Then build/benchmark with benchmarks/bench_build_ab.py.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SECTIONS = ("docs", "guides", "api", "tutorials", "reference")
_TAG_POOL = (
    "python",
    "rendering",
    "performance",
    "config",
    "templates",
    "cli",
    "testing",
    "async",
    "caching",
    "search",
)
_THEME_PAGE = Path("bengal/themes/default/templates/page.html")


def _frontmatter(i: int, section: str) -> str:
    # Deterministic tags: 2-3 per page chosen by index (no RNG).
    tags = [_TAG_POOL[i % len(_TAG_POOL)], _TAG_POOL[(i * 7 + 3) % len(_TAG_POOL)]]
    if i % 3 == 0:
        tags.append(_TAG_POOL[(i * 13 + 5) % len(_TAG_POOL)])
    tags = sorted(set(tags))
    # Deterministic date spread across 2024-2025.
    month = (i % 12) + 1
    day = (i % 28) + 1
    year = 2024 + (i % 2)
    return (
        "---\n"
        f"title: {section.title()} Page {i}\n"
        f"date: {year}-{month:02d}-{day:02d}\n"
        f"tags: [{', '.join(tags)}]\n"
        "---\n"
    )


def _body(i: int, section: str, total: int) -> str:
    # Internal links to a few other pages (deterministic cross-references).
    links = []
    for k in (1, 7, 23):
        j = (i + k) % total
        sec = _SECTIONS[j % len(_SECTIONS)]
        links.append(f"- [{sec.title()} Page {j}](/{sec}/page-{j}/)")
    link_block = "\n".join(links)
    return f"""# {section.title()} Page {i}

This is deterministic benchmark content for page {i} in the {section} section.
It exists to exercise the markdown parser and the render pipeline with a
realistic amount of work — headings, prose, a code block, a list, and links.

## Overview

Bengal renders this page through the full template pipeline. The content is
fixed so the build is byte-reproducible run to run.

```python
def example_{i}(x: int) -> int:
    # representative code block for the highlighter
    return x * {i} + sum(range({i % 17 + 1}))
```

## Details

Some more prose to give the parser and renderer non-trivial work. Lists:

1. First item for page {i}
2. Second item referencing the {section} section
3. Third item

## Related

{link_block}
"""


def _page_html_override() -> str | None:
    """Default theme's page.html with the random_posts widget removed."""
    if not _THEME_PAGE.exists():
        return None
    lines = _THEME_PAGE.read_text(encoding="utf-8").splitlines(keepends=True)
    kept = [
        ln
        for ln in lines
        if "random_posts" not in ln  # drops the import line and the call line
    ]
    return "".join(kept)


def generate(out_dir: Path, pages: int) -> int:
    content = out_dir / "content"
    content.mkdir(parents=True, exist_ok=True)

    (out_dir / "bengal.toml").write_text(
        '[site]\ntitle = "Bench Site"\nbaseurl = "/"\n\n'
        '[build]\ncontent_dir = "content"\noutput_dir = "public"\ntheme = "default"\n\n'
        '[markdown]\nparser = "patitas"\n',
        encoding="utf-8",
    )

    # Local template override to drop the nondeterministic random_posts widget.
    override = _page_html_override()
    if override is not None:
        tpl = out_dir / "templates"
        tpl.mkdir(parents=True, exist_ok=True)
        (tpl / "page.html").write_text(override, encoding="utf-8")

    per_section = max(1, pages // len(_SECTIONS))
    written = 0
    idx = 0
    for section in _SECTIONS:
        sec_dir = content / section
        sec_dir.mkdir(parents=True, exist_ok=True)
        (sec_dir / "_index.md").write_text(
            f"---\ntitle: {section.title()}\n---\n\n# {section.title()}\n",
            encoding="utf-8",
        )
        for _ in range(per_section):
            if written >= pages:
                break
            page_md = _frontmatter(idx, section) + "\n" + _body(idx, section, pages)
            (sec_dir / f"page-{idx}.md").write_text(page_md, encoding="utf-8")
            written += 1
            idx += 1

    (content / "_index.md").write_text("---\ntitle: Home\n---\n\n# Home\n", encoding="utf-8")
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--pages", type=int, default=800)
    args = ap.parse_args()
    n = generate(args.out_dir, args.pages)
    print(f"Generated {n} deterministic content pages in {args.out_dir}")
    if not _THEME_PAGE.exists():
        print("WARNING: default theme page.html not found; random_posts widget not stripped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
