from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

from bengal.core.site import Site
from bengal.rendering.parsers.mistune import MistuneParser


@dataclass(frozen=True)
class CompareResult:
    files: int
    html_mismatches: int
    toc_mismatches: int
    empty_token_failures: int
    old_total_s: float
    new_total_s: float
    mismatch_examples: list[str]

    @property
    def old_ms_per_file(self) -> float:
        return (self.old_total_s * 1000.0) / max(self.files, 1)

    @property
    def new_ms_per_file(self) -> float:
        return (self.new_total_s * 1000.0) / max(self.files, 1)

    @property
    def savings_ms_per_file(self) -> float:
        return self.old_ms_per_file - self.new_ms_per_file


def _iter_md_files(root: Path) -> list[Path]:
    files = [p for p in root.rglob("*.md") if p.is_file()]
    return sorted(files)


_NONDETERMINISTIC_ID_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Directives currently generate IDs based on `id(text)`, which differs depending
    # on object identity. Normalize these for equivalence testing.
    (re.compile(r"\btabs-\d+\b"), "tabs-<id>"),
    (re.compile(r"\bcode-tabs-\d+\b"), "code-tabs-<id>"),
]


def _normalize_html_for_compare(html: str) -> str:
    if not html:
        return html
    out = html
    for pat, repl in _NONDETERMINISTIC_ID_PATTERNS:
        out = pat.sub(repl, out)
    return out


def compare_site_content(root: Path) -> CompareResult:
    parser = MistuneParser(enable_highlighting=False)
    # Use a real Site to give directives the context they expect (data paths, theme, etc.).
    site_root = root.parent
    site = Site.from_config(site_root)

    files = _iter_md_files(root)
    html_mismatches = 0
    toc_mismatches = 0
    empty_token_failures = 0

    # Warm-up
    if files:
        p0 = files[0]
        content0 = p0.read_text(encoding="utf-8")
        page0 = SimpleNamespace(title=p0.stem, metadata={}, source_path=p0)
        ctx0 = {"page": page0, "site": site, "config": site.config}
        parser.parse_with_toc_and_context(content0, {}, ctx0)
        parser.parse_with_toc_and_context_and_tokens(content0, {}, ctx0)
        parser.parse_to_ast(content0, {})

    # OLD: parse HTML/TOC + separately parse_to_ast (matches current pipeline shape)
    t0 = perf_counter()
    old_outputs: dict[Path, tuple[str, str]] = {}
    for p in files:
        content = p.read_text(encoding="utf-8")
        page = SimpleNamespace(title=p.stem, metadata={}, source_path=p)
        ctx = {"page": page, "site": site, "config": site.config}
        html, toc = parser.parse_with_toc_and_context(content, {}, ctx)
        _ = parser.parse_to_ast(content, {})
        old_outputs[p] = (_normalize_html_for_compare(html), toc)
    t1 = perf_counter()

    # NEW: parse HTML/TOC + tokens from a single parse
    t2 = perf_counter()
    mismatch_examples: list[str] = []
    for p in files:
        content = p.read_text(encoding="utf-8")
        page = SimpleNamespace(title=p.stem, metadata={}, source_path=p)
        ctx = {"page": page, "site": site, "config": site.config}
        html, toc, tokens = parser.parse_with_toc_and_context_and_tokens(content, {}, ctx)

        # Quick sanity: tokens should usually be non-empty for non-empty markdown
        if content.strip() and not tokens:
            empty_token_failures += 1
            continue

        old_html, old_toc = old_outputs[p]
        html_norm = _normalize_html_for_compare(html)
        if html_norm != old_html:
            html_mismatches += 1
            if len(mismatch_examples) < 5:
                diff = "\n".join(
                    difflib.unified_diff(
                        old_html.splitlines(),
                        html_norm.splitlines(),
                        fromfile=f"old:{p}",
                        tofile=f"new:{p}",
                        lineterm="",
                        n=2,
                    )
                )
                mismatch_examples.append(diff or f"(no diff lines) {p}")
        if toc != old_toc:
            toc_mismatches += 1
    t3 = perf_counter()

    return CompareResult(
        files=len(files),
        html_mismatches=html_mismatches,
        toc_mismatches=toc_mismatches,
        empty_token_failures=empty_token_failures,
        old_total_s=(t1 - t0),
        new_total_s=(t3 - t2),
        mismatch_examples=mismatch_examples,
    )


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    content_root = repo_root / "site" / "content"
    if not content_root.exists():
        raise SystemExit(f"site content dir not found: {content_root}")

    result = compare_site_content(content_root)
    print("spike: mistune single-pass token capture (site/content)")
    print(f"files={result.files}")
    print(f"html_mismatches={result.html_mismatches}")
    print(f"toc_mismatches={result.toc_mismatches}")
    print(f"empty_token_failures={result.empty_token_failures}")
    print(f"old_total_s={result.old_total_s:.3f}")
    print(f"new_total_s={result.new_total_s:.3f}")
    print(f"old_ms_per_file={result.old_ms_per_file:.3f}")
    print(f"new_ms_per_file={result.new_ms_per_file:.3f}")
    print(f"savings_ms_per_file={result.savings_ms_per_file:.3f}")
    if result.mismatch_examples:
        print("---- mismatch examples (first 5) ----")
        for d in result.mismatch_examples:
            print(d)
            print("----")


if __name__ == "__main__":
    main()
