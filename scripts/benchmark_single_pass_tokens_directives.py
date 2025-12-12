from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ABResult:
    pages: int
    mode: str
    runs: int
    avg_ms_off: float
    avg_ms_on: float

    @property
    def savings_ms(self) -> float:
        return self.avg_ms_off - self.avg_ms_on

    @property
    def savings_pct(self) -> float:
        if self.avg_ms_off <= 0:
            return 0.0
        return (self.savings_ms / self.avg_ms_off) * 100.0


def _write_site_config(site_root: Path, enabled: bool) -> None:
    (site_root / "bengal.toml").write_text(
        f"""[site]
title = "Directive Benchmark Site"
base_url = "https://example.com"

[build]
output_dir = "output"

[output_formats]
enabled = false

[markdown]
parser = "mistune"

[markdown.ast_cache]
single_pass_tokens = {str(enabled).lower()}
persist_tokens = false
""",
        encoding="utf-8",
    )


def generate_directive_site(num_pages: int, tmp_root: Path, enabled: bool) -> Path:
    site_root = tmp_root / f"directive_site_{num_pages}"
    site_root.mkdir(parents=True, exist_ok=True)

    content_dir = site_root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    _write_site_config(site_root, enabled=enabled)

    # Minimal index page
    (content_dir / "index.md").write_text(
        """---
title: Home
---

# Home

Welcome to the directive benchmark.
""",
        encoding="utf-8",
    )

    # Directive-heavy content with variable substitution to hit preprocess path.
    directive_block = """
## Section

:::{note} Title
This is **bold** and a variable: {{ page.title }}.
:::

:::{dropdown} More
Hidden *content* with a link: [x](https://example.com).
:::

:::{tab-set}
:::{tab-item} Python
```python
print("hello")
```
:::
:::{tab-item} JavaScript
```js
console.log("hello")
```
:::
:::

:::{code-tabs}
### Tab: Python
```python
def f():
    return 1
```
### Tab: JavaScript
```js
function f(){ return 1 }
```
:::
""".strip()

    for i in range(num_pages):
        (content_dir / f"page{i:04d}.md").write_text(
            f"""---
title: Page {i}
tags: ["bench", "directives"]
---

# Page {i}

{directive_block}
""",
            encoding="utf-8",
        )

    return site_root


def _clean(site_root: Path) -> None:
    for d in (site_root / ".bengal", site_root / "output"):
        if d.exists():
            shutil.rmtree(d)


def _run_build(site_root: Path, mode: str) -> float:
    _clean(site_root)
    if mode == "no-parallel":
        cmd = ["bengal", "build", "--no-parallel", "."]
    elif mode == "default":
        cmd = ["bengal", "build", "."]
    else:
        raise ValueError(f"Unknown mode: {mode}")

    t0 = time.perf_counter()
    subprocess.run(
        cmd, cwd=site_root, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    t1 = time.perf_counter()
    return (t1 - t0) * 1000.0


def run_ab(pages: int, mode: str, runs: int) -> ABResult:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        site_off = generate_directive_site(pages, tmp, enabled=False)
        site_on = generate_directive_site(pages, tmp, enabled=True)

        # Warmup each once
        _run_build(site_off, mode)
        _run_build(site_on, mode)

        off_times = [_run_build(site_off, mode) for _ in range(runs)]
        on_times = [_run_build(site_on, mode) for _ in range(runs)]

        return ABResult(
            pages=pages,
            mode=mode,
            runs=runs,
            avg_ms_off=sum(off_times) / len(off_times),
            avg_ms_on=sum(on_times) / len(on_times),
        )


def main() -> None:
    for pages in (500, 1000):
        result = run_ab(pages=pages, mode="no-parallel", runs=3)
        print(
            f"pages={result.pages} mode={result.mode} runs={result.runs} "
            f"avg_ms_off={result.avg_ms_off:.1f} avg_ms_on={result.avg_ms_on:.1f} "
            f"savings_ms={result.savings_ms:.1f} savings_pct={result.savings_pct:.2f}%"
        )


if __name__ == "__main__":
    main()
