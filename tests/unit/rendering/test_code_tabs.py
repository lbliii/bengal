"""Tests for code-tabs directive rendering and sync-key uniqueness."""

from __future__ import annotations

from bengal.parsing.backends.patitas.directives.builtins.code_tabs import (
    CodeTabItem,
    _unique_sync_values,
)


class TestUniqueSyncValues:
    """Regression: duplicate tab labels must not share the same sync key."""

    def test_distinct_labels_unchanged(self) -> None:
        tabs = (
            CodeTabItem(lang="Python", code="a", filename="", hl_lines=(), code_lang="python"),
            CodeTabItem(
                lang="JavaScript", code="b", filename="", hl_lines=(), code_lang="javascript"
            ),
        )
        assert _unique_sync_values(tabs) == ("python", "javascript")

    def test_duplicate_labels_get_suffix(self) -> None:
        tabs = (
            CodeTabItem(lang="Python", code="a", filename="", hl_lines=(), code_lang="python"),
            CodeTabItem(lang="Python", code="b", filename="", hl_lines=(), code_lang="python"),
            CodeTabItem(lang="Python", code="c", filename="", hl_lines=(), code_lang="python"),
        )
        assert _unique_sync_values(tabs) == ("python", "python-2", "python-3")

    def test_duplicate_after_distinct(self) -> None:
        tabs = (
            CodeTabItem(lang="Python", code="a", filename="", hl_lines=(), code_lang="python"),
            CodeTabItem(lang="Bash", code="b", filename="", hl_lines=(), code_lang="bash"),
            CodeTabItem(lang="Bash", code="c", filename="", hl_lines=(), code_lang="bash"),
        )
        assert _unique_sync_values(tabs) == ("python", "bash", "bash-2")


class TestCodeTabsDirective:
    """Integration tests for code-tabs HTML output."""

    def test_duplicate_python_tabs_have_unique_sync_values(self, parser) -> None:
        content = """
:::{code-tabs}

```python
def sync_handler(): ...
```

```python
async def async_handler(): ...
```

:::
"""
        result = parser.parse(content, {})

        assert result.count('data-sync-value="python"') == 1
        assert 'data-sync-value="python-2"' in result
        assert result.count('class="tab-pane active"') == 1
        assert 'data-tab-target="' in result

    def test_distinct_languages_keep_canonical_sync_keys(self, parser) -> None:
        content = """
:::{code-tabs}

```python
print("py")
```

```javascript
console.log("js");
```

:::
"""
        result = parser.parse(content, {})

        assert 'data-sync-value="python"' in result
        assert 'data-sync-value="javascript"' in result

    def test_sync_none_omits_sync_values(self, parser) -> None:
        content = """
:::{code-tabs}
:sync: none

```python
a = 1
```

```python
b = 2
```

:::
"""
        result = parser.parse(content, {})

        assert "data-sync-value" not in result

    def test_titles_preserve_distinct_sync_keys(self, parser) -> None:
        content = """
:::{code-tabs}

```python title="Sync handler"
def sync_handler(): ...
```

```python title="Async handler"
async def async_handler(): ...
```

:::
"""
        result = parser.parse(content, {})

        assert 'data-sync-value="sync-handler"' in result
        assert 'data-sync-value="async-handler"' in result

    def test_v2_fence_syntax_without_markers(self, parser) -> None:
        content = """
:::{code-tabs}

```python
first
```

```rust
second
```

:::
"""
        result = parser.parse(content, {})

        assert "Python" in result or "python" in result.lower()
        assert "Rust" in result or "rust" in result.lower()
        assert 'data-sync-value="python"' in result
        assert 'data-sync-value="rust"' in result
