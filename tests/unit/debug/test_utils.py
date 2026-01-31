"""
Unit tests for bengal.debug.utils module.

Tests the shared utility functions used across debug tools.
"""

from __future__ import annotations

import pytest

from bengal.debug.utils import (
    FILE_TYPE_EXTENSIONS,
    FILE_TYPE_ICONS,
    PERFORMANCE_EMOJI,
    SEVERITY_EMOJI,
    STATUS_EMOJI,
    TreeFormatter,
    classify_file,
    find_similar_strings,
    format_bytes_human,
    format_time_change,
    format_time_ms,
    format_tree,
    get_file_icon,
    get_nested_value,
    get_severity_emoji,
    get_status_emoji,
    levenshtein_distance,
    set_nested_value,
    slugify,
    truncate_list,
    truncate_string,
)


class TestFormatBytesHuman:
    """Tests for format_bytes_human function."""

    def test_none_input(self):
        """None input returns None."""
        assert format_bytes_human(None) is None

    def test_bytes(self):
        """Small sizes show as bytes."""
        assert format_bytes_human(0) == "0 B"
        assert format_bytes_human(512) == "512 B"
        assert format_bytes_human(1023) == "1023 B"

    def test_kilobytes(self):
        """Medium sizes show as KB."""
        assert format_bytes_human(1024) == "1.0 KB"
        assert format_bytes_human(2048) == "2.0 KB"
        assert format_bytes_human(1536) == "1.5 KB"

    def test_megabytes(self):
        """Large sizes show as MB."""
        assert format_bytes_human(1024 * 1024) == "1.0 MB"
        assert format_bytes_human(1572864) == "1.5 MB"


class TestEmojiMappings:
    """Tests for emoji mapping functions."""

    def test_status_emoji_hit(self):
        """HIT status shows checkmark."""
        assert get_status_emoji("HIT") == "✅"
        assert get_status_emoji("hit") == "✅"

    def test_status_emoji_miss(self):
        """MISS status shows X."""
        assert get_status_emoji("MISS") == "❌"
        assert get_status_emoji("miss") == "❌"

    def test_status_emoji_stale(self):
        """STALE status shows warning."""
        assert get_status_emoji("STALE") == "⚠️"
        assert get_status_emoji("stale") == "⚠️"

    def test_status_emoji_unknown(self):
        """Unknown status shows question mark."""
        assert get_status_emoji("UNKNOWN") == "❓"
        assert get_status_emoji("random") == "❓"

    def test_severity_emoji_info(self):
        """Info severity shows info icon."""
        assert get_severity_emoji("info") == "ℹ️"
        assert get_severity_emoji("INFO") == "ℹ️"

    def test_severity_emoji_warning(self):
        """Warning severity shows warning icon."""
        assert get_severity_emoji("warning") == "⚠️"
        assert get_severity_emoji("WARNING") == "⚠️"

    def test_severity_emoji_error(self):
        """Error severity shows X."""
        assert get_severity_emoji("error") == "❌"
        assert get_severity_emoji("ERROR") == "❌"

    def test_severity_emoji_critical(self):
        """Critical severity shows red circle."""
        assert get_severity_emoji("critical") == "🔴"
        assert get_severity_emoji("CRITICAL") == "🔴"


class TestClassifyFile:
    """Tests for classify_file function."""

    def test_markdown_files(self):
        """Markdown files classified as page."""
        assert classify_file("content/post.md") == "page"
        assert classify_file("docs/guide.markdown") == "page"
        assert classify_file("content/index.rst") == "page"

    def test_template_files(self):
        """HTML and Jinja files classified as template."""
        assert classify_file("templates/base.html") == "template"
        assert classify_file("templates/page.jinja2") == "template"

    def test_data_files(self):
        """YAML/JSON files classified as data."""
        assert classify_file("data/authors.yaml") == "data"
        assert classify_file("data/settings.yml") == "data"
        assert classify_file("data/items.json") == "data"

    def test_config_files(self):
        """Config files classified as config."""
        assert classify_file("config/site.yaml") == "config"
        assert classify_file("config/settings.yml") == "config"

    def test_partial_files(self):
        """Partial/include files classified as partial."""
        assert classify_file("partials/header.html") == "partial"
        assert classify_file("includes/footer.html") == "partial"

    def test_style_files(self):
        """CSS files classified as style."""
        assert classify_file("styles/main.css") == "style"
        assert classify_file("assets/theme.scss") == "style"

    def test_script_files(self):
        """JS/TS files classified as script."""
        assert classify_file("scripts/main.js") == "script"
        assert classify_file("src/utils.ts") == "script"

    def test_unknown_files(self):
        """Unknown extensions classified as unknown."""
        assert classify_file("data.bin") == "unknown"
        assert classify_file("Makefile") == "unknown"


class TestGetFileIcon:
    """Tests for get_file_icon function."""

    def test_page_icon(self):
        """Pages get document icon."""
        assert get_file_icon("docs/guide.md") == "📄"

    def test_template_icon(self):
        """Templates get palette icon."""
        assert get_file_icon("templates/page.html") == "🎨"

    def test_data_icon(self):
        """Data files get chart icon."""
        assert get_file_icon("data/authors.yaml") == "📊"


class TestSlugify:
    """Tests for slugify function."""

    def test_basic_text(self):
        """Basic text converts to lowercase hyphenated."""
        assert slugify("Hello World") == "hello-world"
        assert slugify("API Reference Guide") == "api-reference-guide"

    def test_special_characters(self):
        """Special characters are removed."""
        assert slugify("Hello, World!") == "hello-world"
        assert slugify("C++ Code") == "c-code"

    def test_multiple_spaces(self):
        """Multiple spaces collapse to single hyphen."""
        assert slugify("Multiple   Spaces") == "multiple-spaces"

    def test_underscores(self):
        """Underscores convert to hyphens."""
        assert slugify("snake_case_text") == "snake-case-text"

    def test_leading_trailing_hyphens(self):
        """Leading/trailing hyphens are removed."""
        assert slugify("  trimmed  ") == "trimmed"
        assert slugify("---dashes---") == "dashes"


class TestTruncateList:
    """Tests for truncate_list function."""

    def test_no_truncation_needed(self):
        """Short lists return unchanged."""
        items, more = truncate_list([1, 2, 3], max_items=5)
        assert items == [1, 2, 3]
        assert more is None

    def test_truncation(self):
        """Long lists are truncated with indicator."""
        items, more = truncate_list([1, 2, 3, 4, 5, 6, 7], max_items=3)
        assert items == [1, 2, 3]
        assert more == "... +4 more"

    def test_custom_formatter(self):
        """Custom format string is used."""
        items, more = truncate_list([1, 2, 3, 4, 5], max_items=2, formatter="and {count} others")
        assert items == [1, 2]
        assert more == "and 3 others"


class TestTruncateString:
    """Tests for truncate_string function."""

    def test_no_truncation_needed(self):
        """Short strings return unchanged."""
        assert truncate_string("Short", max_length=10) == "Short"

    def test_truncation(self):
        """Long strings are truncated with suffix."""
        assert truncate_string("Hello World", max_length=8) == "Hello..."

    def test_custom_suffix(self):
        """Custom suffix is used."""
        assert truncate_string("Hello World", max_length=8, suffix="…") == "Hello W…"


class TestGetNestedValue:
    """Tests for get_nested_value function."""

    def test_simple_key(self):
        """Simple key returns value."""
        data = {"key": "value"}
        assert get_nested_value(data, "key") == "value"

    def test_nested_key(self):
        """Nested key path returns deep value."""
        data = {"site": {"config": {"theme": "dark"}}}
        assert get_nested_value(data, "site.config.theme") == "dark"

    def test_missing_key(self):
        """Missing key returns default."""
        data = {"key": "value"}
        assert get_nested_value(data, "missing") is None
        assert get_nested_value(data, "missing", "default") == "default"

    def test_partial_path(self):
        """Missing intermediate key returns default."""
        data = {"site": {"config": {}}}
        assert get_nested_value(data, "site.config.missing") is None


class TestSetNestedValue:
    """Tests for set_nested_value function."""

    def test_simple_key(self):
        """Simple key sets value."""
        data: dict = {}
        set_nested_value(data, "key", "value")
        assert data == {"key": "value"}

    def test_nested_key(self):
        """Nested key creates intermediate dicts."""
        data: dict = {}
        set_nested_value(data, "site.config.theme", "dark")
        assert data == {"site": {"config": {"theme": "dark"}}}

    def test_existing_intermediate(self):
        """Existing intermediate dicts are preserved."""
        data = {"site": {"title": "Test"}}
        set_nested_value(data, "site.config.theme", "dark")
        assert data == {"site": {"title": "Test", "config": {"theme": "dark"}}}


class TestLevenshteinDistance:
    """Tests for levenshtein_distance function."""

    def test_identical_strings(self):
        """Identical strings have distance 0."""
        assert levenshtein_distance("abc", "abc") == 0
        assert levenshtein_distance("", "") == 0

    def test_one_edit(self):
        """Single edit has distance 1."""
        assert levenshtein_distance("abc", "abd") == 1  # substitution
        assert levenshtein_distance("abc", "abcd") == 1  # insertion
        assert levenshtein_distance("abcd", "abc") == 1  # deletion

    def test_multiple_edits(self):
        """Multiple edits have correct distance."""
        assert levenshtein_distance("abc", "xyz") == 3
        assert levenshtein_distance("kitten", "sitting") == 3

    def test_empty_string(self):
        """Empty string distance is length of other."""
        assert levenshtein_distance("", "abc") == 3
        assert levenshtein_distance("abc", "") == 3


class TestFindSimilarStrings:
    """Tests for find_similar_strings function."""

    def test_typo_detection(self):
        """Close typos are found."""
        known = frozenset(["note", "tip", "warning"])
        assert "note" in find_similar_strings("notee", known)
        assert "warning" in find_similar_strings("warnign", known)

    def test_no_match(self):
        """Distant strings not matched."""
        known = frozenset(["note", "tip", "warning"])
        assert find_similar_strings("xyzabc", known) == []

    def test_max_results(self):
        """Results limited to max_results."""
        known = frozenset(["aa", "ab", "ac", "ad", "ae"])
        similar = find_similar_strings("a", known, max_distance=2, max_results=2)
        assert len(similar) <= 2


class TestTreeFormatter:
    """Tests for TreeFormatter class."""

    def test_format_item(self):
        """Items formatted with correct connectors."""
        fmt = TreeFormatter()
        assert "├─" in fmt.format_item("item", is_last=False)
        assert "└─" in fmt.format_item("item", is_last=True)

    def test_child_prefix(self):
        """Child prefix extends properly."""
        fmt = TreeFormatter()
        prefix = fmt.get_child_prefix("", parent_is_last=False)
        assert "│" in prefix
        prefix = fmt.get_child_prefix("", parent_is_last=True)
        assert "│" not in prefix


class TestFormatTime:
    """Tests for time formatting functions."""

    def test_format_time_ms_small(self):
        """Small times show as ms."""
        assert format_time_ms(150) == "150ms"
        assert format_time_ms(0.5) == "0ms"

    def test_format_time_ms_large(self):
        """Large times show as seconds."""
        assert format_time_ms(2500) == "2.50s"
        assert format_time_ms(1000) == "1.00s"

    def test_format_time_change_positive(self):
        """Positive changes show slow emoji."""
        result = format_time_change(150, 12)
        assert "+150ms" in result
        assert "🐌" in result

    def test_format_time_change_negative(self):
        """Negative changes show fast emoji."""
        result = format_time_change(-50, -10)
        assert "-50ms" in result
        assert "🚀" in result

    def test_format_time_change_small_pct(self):
        """Small percentage changes don't show emoji."""
        result = format_time_change(10, 2)
        assert "🐌" not in result
        assert "🚀" not in result
