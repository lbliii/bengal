"""Tests for fence title and diff rendering."""

from __future__ import annotations

from bengal.parsing import PatitasParser


class TestFenceTitleAndDiff:
    @staticmethod
    def _parser() -> PatitasParser:
        return PatitasParser(enable_highlighting=True)

    def test_fence_title_renders_label(self) -> None:
        content = """
```python title="app.py"
print("hello")
```
"""
        html = self._parser().parse(content, {})
        assert 'class="code-block-title">app.py</div>' in html

    def test_diff_fence_renders_added_removed_classes(self) -> None:
        content = """
```diff
-old
+new
 context
```
"""
        html = self._parser().parse(content, {})
        assert "syntax-added" in html or "syntax-removed" in html
