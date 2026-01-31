"""
Tests for media embed directives.

Tests YouTube, Vimeo, self-hosted video, Gist, CodePen, CodeSandbox,
StackBlitz, Asciinema, Figure, and Audio directives.

Related:
- RFC: plan/implemented/rfc-media-embed-directives.md
- Docs: site/content/docs/reference/directives/media.md
- bengal/rendering/plugins/directives/video.py
- bengal/rendering/plugins/directives/embed.py
- bengal/rendering/plugins/directives/terminal.py
- bengal/rendering/plugins/directives/figure.py

"""

from __future__ import annotations

import pytest

from bengal.parsing import PatitasParser


class TestYouTubeDirective:
    """Test YouTube directive rendering and validation."""

    @pytest.fixture
    def parser(self) -> PatitasParser:
        """Create a Mistune parser instance."""
        return PatitasParser()

    def test_basic_embed(self, parser: PatitasParser) -> None:
        """Test basic YouTube embed with required title."""
        markdown = """\
:::{youtube} dQw4w9WgXcQ
:title: Test Video
:::
"""
        result = parser.parse(markdown, {})
        assert "youtube-nocookie.com" in result  # Privacy default
        assert 'title="Test Video"' in result
        assert 'loading="lazy"' in result
        assert "video-embed" in result
        assert "youtube" in result

    def test_privacy_disabled(self, parser: PatitasParser) -> None:
        """Test YouTube embed with privacy mode disabled."""
        markdown = """\
:::{youtube} dQw4w9WgXcQ
:title: Test Video
:privacy: false
:::
"""
        result = parser.parse(markdown, {})
        assert "youtube.com/embed" in result
        assert "youtube-nocookie.com" not in result

    def test_start_time(self, parser: PatitasParser) -> None:
        """Test YouTube embed with start time."""
        markdown = """\
:::{youtube} dQw4w9WgXcQ
:title: Test Video
:start: 30
:::
"""
        result = parser.parse(markdown, {})
        assert "start=30" in result

    def test_end_time(self, parser: PatitasParser) -> None:
        """Test YouTube embed with end time."""
        markdown = """\
:::{youtube} dQw4w9WgXcQ
:title: Test Video
:end: 60
:::
"""
        result = parser.parse(markdown, {})
        assert "end=60" in result

    def test_autoplay_with_mute(self, parser: PatitasParser) -> None:
        """Test YouTube embed with autoplay and mute."""
        markdown = """\
:::{youtube} dQw4w9WgXcQ
:title: Test Video
:autoplay: true
:muted: true
:::
"""
        result = parser.parse(markdown, {})
        assert "autoplay=1" in result
        assert "mute=1" in result

    def test_loop(self, parser: PatitasParser) -> None:
        """Test YouTube embed with loop."""
        markdown = """\
:::{youtube} dQw4w9WgXcQ
:title: Test Video
:loop: true
:::
"""
        result = parser.parse(markdown, {})
        assert "loop=1" in result
        assert "playlist=dQw4w9WgXcQ" in result

    def test_no_controls(self, parser: PatitasParser) -> None:
        """Test YouTube embed without controls."""
        markdown = """\
:::{youtube} dQw4w9WgXcQ
:title: Test Video
:controls: false
:::
"""
        result = parser.parse(markdown, {})
        assert "controls=0" in result

    def test_custom_aspect(self, parser: PatitasParser) -> None:
        """Test YouTube embed with custom aspect ratio."""
        markdown = """\
:::{youtube} dQw4w9WgXcQ
:title: Test Video
:aspect: 4/3
:::
"""
        result = parser.parse(markdown, {})
        assert 'data-aspect="4/3"' in result

    def test_invalid_id_shows_error(self, parser: PatitasParser) -> None:
        """Test that invalid YouTube IDs show error message."""
        markdown = """\
:::{youtube} invalid
:title: Test
:::
"""
        result = parser.parse(markdown, {})
        assert "video-error" in result
        assert "Invalid YouTube video ID" in result

    def test_missing_title_shows_error(self, parser: PatitasParser) -> None:
        """Test that missing title produces error."""
        markdown = """\
:::{youtube} dQw4w9WgXcQ
:::
"""
        result = parser.parse(markdown, {})
        assert "video-error" in result
        assert "Missing required :title:" in result

    def test_noscript_fallback(self, parser: PatitasParser) -> None:
        """Test that noscript fallback is included."""
        markdown = """\
:::{youtube} dQw4w9WgXcQ
:title: Test Video
:::
"""
        result = parser.parse(markdown, {})
        assert "<noscript>" in result
        assert "youtube.com/watch" in result


class TestVimeoDirective:
    """Test Vimeo directive rendering and validation."""

    @pytest.fixture
    def parser(self) -> PatitasParser:
        """Create a Mistune parser instance."""
        return PatitasParser()

    def test_basic_embed(self, parser: PatitasParser) -> None:
        """Test basic Vimeo embed with required title."""
        markdown = """\
:::{vimeo} 123456789
:title: My Vimeo Video
:::
"""
        result = parser.parse(markdown, {})
        assert "player.vimeo.com" in result
        assert 'title="My Vimeo Video"' in result
        assert "dnt=1" in result  # Privacy default
        assert "video-embed" in result
        assert "vimeo" in result

    def test_privacy_disabled(self, parser: PatitasParser) -> None:
        """Test Vimeo embed with DNT mode disabled."""
        markdown = """\
:::{vimeo} 123456789
:title: My Vimeo Video
:dnt: false
:::
"""
        result = parser.parse(markdown, {})
        assert "dnt=1" not in result

    def test_custom_color(self, parser: PatitasParser) -> None:
        """Test Vimeo embed with custom color."""
        markdown = """\
:::{vimeo} 123456789
:title: My Vimeo Video
:color: ff0000
:::
"""
        result = parser.parse(markdown, {})
        assert "color=ff0000" in result

    def test_background_mode(self, parser: PatitasParser) -> None:
        """Test Vimeo embed in background mode."""
        markdown = """\
:::{vimeo} 123456789
:title: My Vimeo Video
:background: true
:::
"""
        result = parser.parse(markdown, {})
        assert "background=1" in result

    def test_invalid_id_shows_error(self, parser: PatitasParser) -> None:
        """Test that invalid Vimeo IDs show error message."""
        markdown = """\
:::{vimeo} invalid
:title: Test
:::
"""
        result = parser.parse(markdown, {})
        assert "video-error" in result
        assert "Invalid Vimeo video ID" in result

    def test_missing_title_shows_error(self, parser: PatitasParser) -> None:
        """Test that missing title produces error."""
        markdown = """\
:::{vimeo} 123456789
:::
"""
        result = parser.parse(markdown, {})
        assert "video-error" in result
        assert "Missing required :title:" in result


class TestSelfHostedVideoDirective:
    """Test self-hosted video directive rendering and validation."""

    @pytest.fixture
    def parser(self) -> PatitasParser:
        """Create a Mistune parser instance."""
        return PatitasParser()

    def test_basic_embed(self, parser: PatitasParser) -> None:
        """Test basic self-hosted video embed."""
        markdown = """\
:::{video} /assets/demo.mp4
:title: Product Demo
:::
"""
        result = parser.parse(markdown, {})
        assert "<video" in result
        assert '<source src="/assets/demo.mp4"' in result
        assert 'type="video/mp4"' in result
        assert 'title="Product Demo"' in result
        assert "controls" in result
        assert "video-embed" in result
        assert "self-hosted" in result

    def test_with_poster(self, parser: PatitasParser) -> None:
        """Test self-hosted video with poster image."""
        markdown = """\
:::{video} /assets/demo.mp4
:title: Product Demo
:poster: /assets/poster.jpg
:::
"""
        result = parser.parse(markdown, {})
        assert 'poster="/assets/poster.jpg"' in result

    def test_autoplay_with_mute(self, parser: PatitasParser) -> None:
        """Test self-hosted video with autoplay and mute."""
        markdown = """\
:::{video} /assets/demo.mp4
:title: Product Demo
:autoplay: true
:muted: true
:::
"""
        result = parser.parse(markdown, {})
        assert "autoplay" in result
        assert "muted" in result

    def test_no_controls(self, parser: PatitasParser) -> None:
        """Test self-hosted video without controls."""
        markdown = """\
:::{video} /assets/demo.mp4
:title: Product Demo
:controls: false
:::
"""
        result = parser.parse(markdown, {})
        # controls should not appear as an attribute
        assert "controls" not in result or 'controls="' not in result

    def test_webm_format(self, parser: PatitasParser) -> None:
        """Test self-hosted video with WebM format."""
        markdown = """\
:::{video} /assets/demo.webm
:title: Product Demo
:::
"""
        result = parser.parse(markdown, {})
        assert 'type="video/webm"' in result

    def test_invalid_path_shows_error(self, parser: PatitasParser) -> None:
        """Test that invalid video paths show error message."""
        markdown = """\
:::{video} invalid.txt
:title: Test
:::
"""
        result = parser.parse(markdown, {})
        assert "video-error" in result
        assert "Invalid video path" in result

    def test_missing_title_shows_error(self, parser: PatitasParser) -> None:
        """Test that missing title produces error."""
        markdown = """\
:::{video} /assets/demo.mp4
:::
"""
        result = parser.parse(markdown, {})
        assert "video-error" in result
        assert "Missing required :title:" in result

    def test_fallback_content(self, parser: PatitasParser) -> None:
        """Test that fallback content is included."""
        markdown = """\
:::{video} /assets/demo.mp4
:title: Product Demo
:::
"""
        result = parser.parse(markdown, {})
        assert "Download the video" in result
        assert "<a href=" in result


class TestGistDirective:
    """Test GitHub Gist directive rendering and validation."""

    @pytest.fixture
    def parser(self) -> PatitasParser:
        """Create a Mistune parser instance."""
        return PatitasParser()

    def test_basic_embed(self, parser: PatitasParser) -> None:
        """Test basic Gist embed."""
        markdown = """\
:::{gist} octocat/12345678901234567890123456789012
:::
"""
        result = parser.parse(markdown, {})
        assert "gist.github.com" in result
        assert "gist-embed" in result
        assert "<script" in result

    def test_with_file(self, parser: PatitasParser) -> None:
        """Test Gist embed with specific file."""
        markdown = """\
:::{gist} octocat/12345678901234567890123456789012
:file: example.py
:::
"""
        result = parser.parse(markdown, {})
        assert "file=example.py" in result

    def test_noscript_fallback(self, parser: PatitasParser) -> None:
        """Test that noscript fallback is included."""
        markdown = """\
:::{gist} octocat/12345678901234567890123456789012
:::
"""
        result = parser.parse(markdown, {})
        assert "<noscript>" in result
        assert "View gist:" in result

    def test_invalid_format_shows_error(self, parser: PatitasParser) -> None:
        """Test that invalid gist format shows error."""
        markdown = """\
:::{gist} invalid
:::
"""
        result = parser.parse(markdown, {})
        assert "gist-error" in result
        assert "Invalid gist reference" in result


class TestCodePenDirective:
    """Test CodePen directive rendering and validation."""

    @pytest.fixture
    def parser(self) -> PatitasParser:
        """Create a Mistune parser instance."""
        return PatitasParser()

    def test_basic_embed(self, parser: PatitasParser) -> None:
        """Test basic CodePen embed."""
        markdown = """\
:::{codepen} chriscoyier/pen/abc123
:title: CSS Grid Example
:::
"""
        result = parser.parse(markdown, {})
        assert "codepen.io" in result
        assert 'title="CSS Grid Example"' in result
        assert "code-embed" in result
        assert "codepen" in result

    def test_default_tab(self, parser: PatitasParser) -> None:
        """Test CodePen embed with custom default tab."""
        markdown = """\
:::{codepen} chriscoyier/abc123
:title: Example
:default-tab: html
:::
"""
        result = parser.parse(markdown, {})
        assert "default-tab=html" in result

    def test_custom_height(self, parser: PatitasParser) -> None:
        """Test CodePen embed with custom height."""
        markdown = """\
:::{codepen} chriscoyier/abc123
:title: Example
:height: 500
:::
"""
        result = parser.parse(markdown, {})
        assert "height: 500px" in result

    def test_missing_title_shows_error(self, parser: PatitasParser) -> None:
        """Test that missing title produces error."""
        markdown = """\
:::{codepen} chriscoyier/abc123
:::
"""
        result = parser.parse(markdown, {})
        assert "code-error" in result
        assert "Missing required :title:" in result


class TestCodeSandboxDirective:
    """Test CodeSandbox directive rendering and validation."""

    @pytest.fixture
    def parser(self) -> PatitasParser:
        """Create a Mistune parser instance."""
        return PatitasParser()

    def test_basic_embed(self, parser: PatitasParser) -> None:
        """Test basic CodeSandbox embed."""
        markdown = """\
:::{codesandbox} abcde12345
:title: React Example
:::
"""
        result = parser.parse(markdown, {})
        assert "codesandbox.io" in result
        assert 'title="React Example"' in result
        assert "code-embed" in result
        assert "codesandbox" in result

    def test_with_module(self, parser: PatitasParser) -> None:
        """Test CodeSandbox embed with specific module."""
        markdown = """\
:::{codesandbox} abcde12345
:title: React Example
:module: /src/App.js
:::
"""
        result = parser.parse(markdown, {})
        assert "module=/src/App.js" in result

    def test_view_option(self, parser: PatitasParser) -> None:
        """Test CodeSandbox embed with view option."""
        markdown = """\
:::{codesandbox} abcde12345
:title: React Example
:view: preview
:::
"""
        result = parser.parse(markdown, {})
        assert "view=preview" in result

    def test_missing_title_shows_error(self, parser: PatitasParser) -> None:
        """Test that missing title produces error."""
        markdown = """\
:::{codesandbox} abcde12345
:::
"""
        result = parser.parse(markdown, {})
        assert "code-error" in result
        assert "Missing required :title:" in result


class TestStackBlitzDirective:
    """Test StackBlitz directive rendering and validation."""

    @pytest.fixture
    def parser(self) -> PatitasParser:
        """Create a Mistune parser instance."""
        return PatitasParser()

    def test_basic_embed(self, parser: PatitasParser) -> None:
        """Test basic StackBlitz embed."""
        markdown = """\
:::{stackblitz} angular-quickstart
:title: Angular Demo
:::
"""
        result = parser.parse(markdown, {})
        assert "stackblitz.com" in result
        assert 'title="Angular Demo"' in result
        assert "code-embed" in result
        assert "stackblitz" in result

    def test_with_file(self, parser: PatitasParser) -> None:
        """Test StackBlitz embed with specific file."""
        markdown = """\
:::{stackblitz} angular-quickstart
:title: Angular Demo
:file: src/app.component.ts
:::
"""
        result = parser.parse(markdown, {})
        assert "file=src/app.component.ts" in result

    def test_view_option(self, parser: PatitasParser) -> None:
        """Test StackBlitz embed with view option."""
        markdown = """\
:::{stackblitz} angular-quickstart
:title: Angular Demo
:view: preview
:::
"""
        result = parser.parse(markdown, {})
        assert "view=preview" in result

    def test_missing_title_shows_error(self, parser: PatitasParser) -> None:
        """Test that missing title produces error."""
        markdown = """\
:::{stackblitz} angular-quickstart
:::
"""
        result = parser.parse(markdown, {})
        assert "code-error" in result
        assert "Missing required :title:" in result


class TestAsciinemaDirective:
    """Test Asciinema directive rendering and validation."""

    @pytest.fixture
    def parser(self) -> PatitasParser:
        """Create a Mistune parser instance."""
        return PatitasParser()

    def test_basic_embed(self, parser: PatitasParser) -> None:
        """Test basic Asciinema embed."""
        markdown = """\
:::{asciinema} 590029
:title: Installation Demo
:::
"""
        result = parser.parse(markdown, {})
        assert "asciinema.org" in result
        assert 'aria-label="Installation Demo"' in result
        assert "terminal-embed" in result
        assert "asciinema" in result
        assert 'role="img"' in result

    def test_custom_size(self, parser: PatitasParser) -> None:
        """Test Asciinema embed with custom size."""
        markdown = """\
:::{asciinema} 590029
:title: Installation Demo
:cols: 120
:rows: 30
:::
"""
        result = parser.parse(markdown, {})
        assert 'data-cols="120"' in result
        assert 'data-rows="30"' in result

    def test_playback_options(self, parser: PatitasParser) -> None:
        """Test Asciinema embed with playback options."""
        markdown = """\
:::{asciinema} 590029
:title: Installation Demo
:speed: 2.0
:autoplay: true
:loop: true
:::
"""
        result = parser.parse(markdown, {})
        assert 'data-speed="2.0"' in result
        assert 'data-autoplay="true"' in result
        assert 'data-loop="true"' in result

    def test_noscript_fallback(self, parser: PatitasParser) -> None:
        """Test that noscript fallback is included."""
        markdown = """\
:::{asciinema} 590029
:title: Installation Demo
:::
"""
        result = parser.parse(markdown, {})
        assert "<noscript>" in result
        assert "View recording:" in result

    def test_invalid_id_shows_error(self, parser: PatitasParser) -> None:
        """Test that invalid recording IDs show error."""
        markdown = """\
:::{asciinema} invalid
:title: Test
:::
"""
        result = parser.parse(markdown, {})
        assert "terminal-error" in result
        assert "Invalid Asciinema recording ID" in result

    def test_missing_title_shows_error(self, parser: PatitasParser) -> None:
        """Test that missing title produces error."""
        markdown = """\
:::{asciinema} 590029
:::
"""
        result = parser.parse(markdown, {})
        assert "terminal-error" in result
        assert "Missing required :title:" in result


class TestFigureDirective:
    """Test Figure directive rendering and validation."""

    @pytest.fixture
    def parser(self) -> PatitasParser:
        """Create a Mistune parser instance."""
        return PatitasParser()

    def test_basic_figure(self, parser: PatitasParser) -> None:
        """Test basic figure with alt text."""
        markdown = """\
:::{figure} /images/test.png
:alt: Test image description
:::
"""
        result = parser.parse(markdown, {})
        assert "<figure" in result
        assert 'alt="Test image description"' in result
        assert 'loading="lazy"' in result
        assert "</figure>" in result

    def test_figure_with_caption(self, parser: PatitasParser) -> None:
        """Test figure with caption renders figcaption."""
        markdown = """\
:::{figure} /images/test.png
:alt: Test image
:caption: This is the caption text
:::
"""
        result = parser.parse(markdown, {})
        assert "<figcaption>" in result
        assert "This is the caption text" in result
        assert "</figcaption>" in result

    def test_decorative_image(self, parser: PatitasParser) -> None:
        """Test decorative image with empty alt."""
        markdown = """\
:::{figure} /images/decorative.png
:alt: 
:::
"""
        result = parser.parse(markdown, {})
        assert 'alt=""' in result

    def test_alignment(self, parser: PatitasParser) -> None:
        """Test figure alignment classes."""
        markdown = """\
:::{figure} /images/test.png
:alt: Test
:align: center
:::
"""
        result = parser.parse(markdown, {})
        assert "align-center" in result

    def test_width(self, parser: PatitasParser) -> None:
        """Test figure with width."""
        markdown = """\
:::{figure} /images/test.png
:alt: Test
:width: 80%
:::
"""
        result = parser.parse(markdown, {})
        assert "width: 80%" in result

    def test_with_link(self, parser: PatitasParser) -> None:
        """Test figure with link."""
        markdown = """\
:::{figure} /images/test.png
:alt: Test
:link: https://example.com
:::
"""
        result = parser.parse(markdown, {})
        assert '<a href="https://example.com"' in result
        assert "</a>" in result

    def test_link_with_blank_target(self, parser: PatitasParser) -> None:
        """Test figure link with blank target."""
        markdown = """\
:::{figure} /images/test.png
:alt: Test
:link: https://example.com
:target: _blank
:::
"""
        result = parser.parse(markdown, {})
        assert 'target="_blank"' in result
        assert 'rel="noopener noreferrer"' in result

    def test_invalid_path_shows_error(self, parser: PatitasParser) -> None:
        """Test that invalid image paths show error."""
        markdown = """\
:::{figure} invalid.txt
:alt: Test
:::
"""
        result = parser.parse(markdown, {})
        assert "figure-error" in result
        assert "Invalid image path" in result


class TestAudioDirective:
    """Test Audio directive rendering and validation."""

    @pytest.fixture
    def parser(self) -> PatitasParser:
        """Create a Mistune parser instance."""
        return PatitasParser()

    def test_basic_audio(self, parser: PatitasParser) -> None:
        """Test basic audio embed."""
        markdown = """\
:::{audio} /assets/podcast.mp3
:title: Episode 1
:::
"""
        result = parser.parse(markdown, {})
        assert "<audio" in result
        assert '<source src="/assets/podcast.mp3"' in result
        assert 'type="audio/mpeg"' in result
        assert 'title="Episode 1"' in result
        assert "controls" in result
        assert "audio-embed" in result

    def test_no_controls(self, parser: PatitasParser) -> None:
        """Test audio without controls."""
        markdown = """\
:::{audio} /assets/podcast.mp3
:title: Episode 1
:controls: false
:::
"""
        result = parser.parse(markdown, {})
        # controls should not appear as an attribute
        assert result.count("controls") == 0 or "controls=" not in result

    def test_ogg_format(self, parser: PatitasParser) -> None:
        """Test audio with OGG format."""
        markdown = """\
:::{audio} /assets/podcast.ogg
:title: Episode 1
:::
"""
        result = parser.parse(markdown, {})
        assert 'type="audio/ogg"' in result

    def test_fallback_content(self, parser: PatitasParser) -> None:
        """Test that fallback content is included."""
        markdown = """\
:::{audio} /assets/podcast.mp3
:title: Episode 1
:::
"""
        result = parser.parse(markdown, {})
        assert "Download the audio" in result

    def test_invalid_path_shows_error(self, parser: PatitasParser) -> None:
        """Test that invalid audio paths show error."""
        markdown = """\
:::{audio} invalid.txt
:title: Test
:::
"""
        result = parser.parse(markdown, {})
        assert "audio-error" in result
        assert "Invalid audio path" in result

    def test_missing_title_shows_error(self, parser: PatitasParser) -> None:
        """Test that missing title produces error."""
        markdown = """\
:::{audio} /assets/podcast.mp3
:::
"""
        result = parser.parse(markdown, {})
        assert "audio-error" in result
        assert "Missing required :title:" in result


class TestMediaDirectivesSecurity:
    """Security tests for media embed directives."""

    @pytest.fixture
    def parser(self) -> PatitasParser:
        """Create a Mistune parser instance."""
        return PatitasParser()

    @pytest.mark.parametrize(
        "malicious_id",
        [
            "dQw4w9WgXcQ<script>",
            'dQw4w9WgXcQ"><img onerror=alert(1)>',
            "../../../etc/passwd",
            "javascript:alert(1)",
            "dQw4w9WgXcQ&autoplay=1&mute=1",  # URL injection
        ],
    )
    def test_youtube_id_sanitization(self, parser: PatitasParser, malicious_id: str) -> None:
        """Test that malicious YouTube IDs are rejected or sanitized."""
        markdown = f"""\
:::{{youtube}} {malicious_id}
:title: Test
:::
"""
        result = parser.parse(markdown, {})
        # Should show error (invalid ID), not render an actual embed
        assert "video-error" in result
        assert "Invalid YouTube video ID" in result
        # Should not have an actual iframe src with the malicious content
        assert "src=" not in result or "youtube" not in result.split("src=")[1].split(">")[0]

    @pytest.mark.parametrize(
        "malicious_path",
        [
            "/images/../../../etc/passwd.png",
            "javascript:alert(1).png",
            "<script>alert(1)</script>.png",
        ],
    )
    def test_figure_path_sanitization(self, parser: PatitasParser, malicious_path: str) -> None:
        """Test that malicious image paths are rejected."""
        markdown = f"""\
:::{{figure}} {malicious_path}
:alt: Test
:::
"""
        result = parser.parse(markdown, {})
        # Should show error (invalid path), not render an actual image
        assert "figure-error" in result
        assert "Invalid image path" in result
        # Should not have an actual img src with the malicious content
        assert "<img src=" not in result


class TestMediaDirectivesIntegration:
    """Integration tests for media directives in documents."""

    @pytest.fixture
    def parser(self) -> PatitasParser:
        """Create a Mistune parser instance."""
        return PatitasParser()

    def test_multiple_embeds_in_document(self, parser: PatitasParser) -> None:
        """Test multiple different embeds in one document."""
        markdown = """\
# Media Demo

:::{youtube} dQw4w9WgXcQ
:title: YouTube Video
:::

:::{figure} /images/test.png
:alt: Test Image
:caption: A test image
:::

:::{audio} /assets/podcast.mp3
:title: Podcast Episode
:::
"""
        result = parser.parse(markdown, {})

        # All directives should be rendered
        assert "youtube-nocookie.com" in result
        assert "<figure" in result
        assert "<audio" in result

        # No raw directive syntax should remain
        assert ":::{youtube}" not in result
        assert ":::{figure}" not in result
        assert ":::{audio}" not in result

    def test_embeds_in_admonitions(self, parser: PatitasParser) -> None:
        """Test embeds nested in admonitions."""
        markdown = """\
:::{note}
Check out this video:

:::{youtube} dQw4w9WgXcQ
:title: Demo Video
:::
:::
"""
        result = parser.parse(markdown, {})

        # Both admonition and video should render
        assert "admonition" in result
        assert "youtube-nocookie.com" in result

    def test_embeds_in_tabs(self, parser: PatitasParser) -> None:
        """Test embeds nested in tabs."""
        markdown = """\
::::{tab-set}

:::{tab-item} Video
:::{youtube} dQw4w9WgXcQ
:title: Demo Video
:::
:::

:::{tab-item} Image
:::{figure} /images/test.png
:alt: Test Image
:::
:::

::::
"""
        result = parser.parse(markdown, {})

        # Both tabs and media should render
        assert "youtube-nocookie.com" in result
        assert "<figure" in result

    def test_embeds_in_cards(self, parser: PatitasParser) -> None:
        """Test embeds nested in cards."""
        markdown = """\
::::{cards}

:::{card} Video Card
:::{youtube} dQw4w9WgXcQ
:title: Demo Video
:::
:::

::::
"""
        result = parser.parse(markdown, {})

        # Both card and video should render
        assert "youtube-nocookie.com" in result


class TestMediaDirectivesEdgeCases:
    """Edge case tests for media directives."""

    @pytest.fixture
    def parser(self) -> PatitasParser:
        """Create a Mistune parser instance."""
        return PatitasParser()

    def test_youtube_short_url_format(self, parser: PatitasParser) -> None:
        """Test YouTube with short URL video ID."""
        markdown = """\
:::{youtube} dQw4w9WgXcQ
:title: Short URL Test
:::
"""
        result = parser.parse(markdown, {})
        assert "dQw4w9WgXcQ" in result
        assert "youtube-nocookie.com" in result

    def test_youtube_all_options_combined(self, parser: PatitasParser) -> None:
        """Test YouTube with all options enabled."""
        markdown = """\
:::{youtube} dQw4w9WgXcQ
:title: Full Options Test
:privacy: true
:start: 10
:end: 60
:autoplay: true
:muted: true
:loop: true
:controls: true
:aspect: 21/9
:class: custom-class
:::
"""
        result = parser.parse(markdown, {})
        assert "youtube-nocookie.com" in result
        assert "start=10" in result
        assert "end=60" in result
        assert "autoplay=1" in result
        assert "mute=1" in result
        assert "loop=1" in result
        assert 'data-aspect="21/9"' in result
        assert "custom-class" in result

    def test_vimeo_all_options_combined(self, parser: PatitasParser) -> None:
        """Test Vimeo with all options enabled."""
        markdown = """\
:::{vimeo} 123456789
:title: Full Options Test
:dnt: true
:color: ff5500
:background: true
:autoplay: true
:muted: true
:loop: true
:::
"""
        result = parser.parse(markdown, {})
        assert "player.vimeo.com" in result
        assert "dnt=1" in result
        assert "color=ff5500" in result
        assert "background=1" in result

    def test_figure_webp_format(self, parser: PatitasParser) -> None:
        """Test figure with WebP format."""
        markdown = """\
:::{figure} /images/test.webp
:alt: WebP Image
:::
"""
        result = parser.parse(markdown, {})
        assert "/images/test.webp" in result

    def test_figure_svg_format(self, parser: PatitasParser) -> None:
        """Test figure with SVG format."""
        markdown = """\
:::{figure} /images/diagram.svg
:alt: SVG Diagram
:::
"""
        result = parser.parse(markdown, {})
        assert "/images/diagram.svg" in result

    def test_figure_avif_format(self, parser: PatitasParser) -> None:
        """Test figure with AVIF format."""
        markdown = """\
:::{figure} /images/test.avif
:alt: AVIF Image
:::
"""
        result = parser.parse(markdown, {})
        assert "/images/test.avif" in result

    def test_figure_external_url(self, parser: PatitasParser) -> None:
        """Test figure with external HTTPS URL."""
        markdown = """\
:::{figure} https://example.com/image.png
:alt: External Image
:::
"""
        result = parser.parse(markdown, {})
        assert "https://example.com/image.png" in result

    def test_figure_relative_path(self, parser: PatitasParser) -> None:
        """Test figure with relative path."""
        markdown = """\
:::{figure} ./images/local.png
:alt: Local Image
:::
"""
        result = parser.parse(markdown, {})
        assert "./images/local.png" in result

    def test_video_mov_format(self, parser: PatitasParser) -> None:
        """Test video with MOV format."""
        markdown = """\
:::{video} /assets/demo.mov
:title: MOV Video
:::
"""
        result = parser.parse(markdown, {})
        assert '/assets/demo.mov"' in result

    def test_audio_wav_format(self, parser: PatitasParser) -> None:
        """Test audio with WAV format."""
        markdown = """\
:::{audio} /assets/sound.wav
:title: WAV Audio
:::
"""
        result = parser.parse(markdown, {})
        assert 'type="audio/wav"' in result

    def test_audio_m4a_format(self, parser: PatitasParser) -> None:
        """Test audio with M4A format."""
        markdown = """\
:::{audio} /assets/podcast.m4a
:title: M4A Audio
:::
"""
        result = parser.parse(markdown, {})
        assert "/assets/podcast.m4a" in result

    def test_gist_with_special_characters_in_filename(self, parser: PatitasParser) -> None:
        """Test gist with special characters in filename."""
        markdown = """\
:::{gist} octocat/12345678901234567890123456789012
:file: test-file_v1.2.py
:::
"""
        result = parser.parse(markdown, {})
        assert "file=test-file_v1.2.py" in result

    def test_codesandbox_editor_view(self, parser: PatitasParser) -> None:
        """Test CodeSandbox with editor-only view."""
        markdown = """\
:::{codesandbox} abcde12345
:title: Editor Only
:view: editor
:::
"""
        result = parser.parse(markdown, {})
        assert "view=editor" in result

    def test_stackblitz_preview_view(self, parser: PatitasParser) -> None:
        """Test StackBlitz with preview-only view."""
        markdown = """\
:::{stackblitz} react-starter
:title: Preview Only
:view: preview
:::
"""
        result = parser.parse(markdown, {})
        assert "view=preview" in result

    def test_asciinema_with_playback_options(self, parser: PatitasParser) -> None:
        """Test Asciinema with playback options."""
        markdown = """\
:::{asciinema} 590029
:title: Themed Recording
:speed: 1.5
:loop: true
:::
"""
        result = parser.parse(markdown, {})
        assert 'data-speed="1.5"' in result
        assert 'data-loop="true"' in result

    def test_youtube_aspect_ratio_4_3(self, parser: PatitasParser) -> None:
        """Test YouTube with 4:3 aspect ratio."""
        markdown = """\
:::{youtube} dQw4w9WgXcQ
:title: Test Video
:aspect: 4/3
:::
"""
        result = parser.parse(markdown, {})
        assert 'data-aspect="4/3"' in result

    def test_youtube_aspect_ratio_1_1(self, parser: PatitasParser) -> None:
        """Test YouTube with 1:1 aspect ratio."""
        markdown = """\
:::{youtube} dQw4w9WgXcQ
:title: Test Video
:aspect: 1/1
:::
"""
        result = parser.parse(markdown, {})
        assert 'data-aspect="1/1"' in result

    def test_figure_all_options(self, parser: PatitasParser) -> None:
        """Test figure with all options."""
        markdown = """\
:::{figure} /images/test.png
:alt: Full Options Image
:caption: This is a detailed caption
:width: 600px
:height: 400px
:align: center
:link: https://example.com
:target: _blank
:loading: eager
:class: featured-image
:::
"""
        result = parser.parse(markdown, {})
        assert 'alt="Full Options Image"' in result
        assert "This is a detailed caption" in result
        assert "width: 600px" in result
        assert "height: 400px" in result
        assert "align-center" in result
        assert 'href="https://example.com"' in result
        assert 'target="_blank"' in result
        assert 'rel="noopener noreferrer"' in result
        assert 'loading="eager"' in result
        assert "featured-image" in result

    def test_special_characters_in_title_escaped(self, parser: PatitasParser) -> None:
        """Test that special characters in title are properly escaped."""
        markdown = """\
:::{youtube} dQw4w9WgXcQ
:title: Test <script> & "quotes"
:::
"""
        result = parser.parse(markdown, {})
        # Title should be escaped to prevent XSS
        assert "<script>" not in result
        assert "&lt;script&gt;" in result or "Test" in result
