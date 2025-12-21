"""
Test checklist directive with new options: style, show-progress, compact.
"""


class TestChecklistDirective:
    """Test the checklist directive rendering."""

    def test_basic_checklist(self, parser):
        """Test basic checklist rendering."""
        content = """
:::{checklist} Prerequisites
- Item one
- Item two
- Item three
:::
"""
        result = parser.parse(content, {})

        assert "checklist" in result
        assert "Prerequisites" in result
        assert "Item one" in result
        assert "Item two" in result


class TestChecklistStyleOption:
    """Test the :style: option for checklists."""

    def test_default_style(self, parser):
        """Test default style (no extra class)."""
        content = """
:::{checklist} Items
- First
- Second
:::
"""
        result = parser.parse(content, {})

        assert 'class="checklist"' in result
        assert "checklist-numbered" not in result
        assert "checklist-minimal" not in result

    def test_numbered_style(self, parser):
        """Test numbered style adds checklist-numbered class."""
        content = """
:::{checklist} Steps
:style: numbered
- First step
- Second step
- Third step
:::
"""
        result = parser.parse(content, {})

        assert "checklist-numbered" in result
        assert "First step" in result

    def test_minimal_style(self, parser):
        """Test minimal style adds checklist-minimal class."""
        content = """
:::{checklist} Quick List
:style: minimal
- Item A
- Item B
:::
"""
        result = parser.parse(content, {})

        assert "checklist-minimal" in result
        assert "Item A" in result


class TestChecklistShowProgressOption:
    """Test the :show-progress: option for checklists."""

    def test_show_progress_disabled_by_default(self, parser):
        """Test that progress bar is not shown by default."""
        content = """
:::{checklist} Tasks
- [ ] Task one
- [x] Task two
:::
"""
        result = parser.parse(content, {})

        assert "checklist-progress" not in result

    def test_show_progress_enabled(self, parser):
        """Test that progress bar is shown when enabled."""
        content = """
:::{checklist} Tasks
:show-progress:
- [ ] Task one
- [x] Task two
:::
"""
        result = parser.parse(content, {})

        assert "checklist-progress" in result
        assert "checklist-progress-bar" in result
        assert "checklist-progress-text" in result
        # Should show 1/2 complete
        assert "1/2 complete" in result

    def test_show_progress_all_complete(self, parser):
        """Test progress bar with all tasks complete."""
        content = """
:::{checklist} Done
:show-progress:
- [x] Task one
- [x] Task two
:::
"""
        result = parser.parse(content, {})

        assert "2/2 complete" in result

    def test_show_progress_none_complete(self, parser):
        """Test progress bar with no tasks complete."""
        content = """
:::{checklist} Todo
:show-progress:
- [ ] Task one
- [ ] Task two
- [ ] Task three
:::
"""
        result = parser.parse(content, {})

        assert "0/3 complete" in result

    def test_show_progress_no_checkboxes(self, parser):
        """Test that progress bar is not shown for non-task lists."""
        content = """
:::{checklist} Regular List
:show-progress:
- Item one
- Item two
:::
"""
        result = parser.parse(content, {})

        # Should not show progress bar for regular bullet lists
        assert "checklist-progress" not in result


class TestChecklistCompactOption:
    """Test the :compact: option for checklists."""

    def test_compact_disabled_by_default(self, parser):
        """Test that compact class is not added by default."""
        content = """
:::{checklist} Items
- Item one
- Item two
:::
"""
        result = parser.parse(content, {})

        assert "checklist-compact" not in result

    def test_compact_enabled(self, parser):
        """Test that compact class is added when enabled."""
        content = """
:::{checklist} Quick Items
:compact:
- Item one
- Item two
- Item three
:::
"""
        result = parser.parse(content, {})

        assert "checklist-compact" in result


class TestChecklistCombinedOptions:
    """Test combining multiple checklist options."""

    def test_all_options_combined(self, parser):
        """Test combining style, show-progress, and compact."""
        content = """
:::{checklist} Prerequisites
:style: numbered
:show-progress:
:compact:
- [x] Python 3.14+
- [x] Bengal installed
- [ ] Git configured
- [ ] IDE ready
:::
"""
        result = parser.parse(content, {})

        # All classes should be present
        assert "checklist-numbered" in result
        assert "checklist-compact" in result
        assert "checklist-progress" in result
        # 2/4 complete
        assert "2/4 complete" in result

    def test_style_with_custom_class(self, parser):
        """Test style option combined with custom CSS class."""
        content = """
:::{checklist} Items
:style: minimal
:class: my-custom-class
- Item one
- Item two
:::
"""
        result = parser.parse(content, {})

        assert "checklist-minimal" in result
        assert "my-custom-class" in result


class TestChecklistWithNamedClosers:
    """Test checklist directive with named closers."""

    def test_named_closer_syntax(self, parser):
        """Test checklist with named closer syntax."""
        content = """
:::{checklist} Tasks
:style: numbered
:show-progress:
- [x] First task
- [ ] Second task
:::{/checklist}
"""
        result = parser.parse(content, {})

        assert "checklist-numbered" in result
        assert "checklist-progress" in result
        assert "1/2 complete" in result
