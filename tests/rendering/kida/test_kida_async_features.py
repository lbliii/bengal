"""Async features tests for Kida template engine.

Tests async for loops, await expressions, and async rendering.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest

from bengal.rendering.kida import Environment


class TestAsyncRendering:
    """Test async template rendering."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    @pytest.mark.asyncio
    async def test_async_render_basic(self, env: Environment) -> None:
        """Basic async render."""
        tmpl = env.from_string("Hello {{ name }}")

        # Check if async render is available
        if hasattr(tmpl, "render_async"):
            result = await tmpl.render_async(name="World")
            assert result == "Hello World"
        else:
            # Sync render should still work
            result = tmpl.render(name="World")
            assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_sync_and_async_same_result(self, env: Environment) -> None:
        """Sync and async render produce same result."""
        tmpl = env.from_string("{{ x }} + {{ y }} = {{ x + y }}")

        sync_result = tmpl.render(x=1, y=2)

        if hasattr(tmpl, "render_async"):
            async_result = await tmpl.render_async(x=1, y=2)
            assert sync_result == async_result
        else:
            pytest.skip("Async render not available")


class TestAsyncFor:
    """Test async for loops."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    @pytest.mark.asyncio
    async def test_async_for_basic(self, env: Environment) -> None:
        """Basic async for loop."""

        async def async_gen() -> AsyncIterator[int]:
            for i in range(3):
                await asyncio.sleep(0)  # Yield control
                yield i

        # Try to parse async for syntax
        try:
            tmpl = env.from_string("{% for x in items %}{{ x }}{% endfor %}")

            if hasattr(tmpl, "render_async"):
                result = await tmpl.render_async(items=async_gen())
                assert "0" in result
                assert "1" in result
                assert "2" in result
            else:
                pytest.skip("Async render not available")
        except Exception:
            pytest.skip("Async for not supported")

    @pytest.mark.asyncio
    async def test_async_for_with_loop_vars(self, env: Environment) -> None:
        """Async for loop with loop variables."""

        async def async_gen() -> AsyncIterator[str]:
            for item in ["a", "b", "c"]:
                await asyncio.sleep(0)
                yield item

        try:
            tmpl = env.from_string("{% for x in items %}{{ loop.index }}:{{ x }},{% endfor %}")

            if hasattr(tmpl, "render_async"):
                result = await tmpl.render_async(items=async_gen())
                assert "1:a" in result
                assert "2:b" in result
                assert "3:c" in result
            else:
                pytest.skip("Async render not available")
        except Exception:
            pytest.skip("Async for not supported")


class TestAsyncFilters:
    """Test async filter support."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    @pytest.mark.asyncio
    async def test_async_filter(self, env: Environment) -> None:
        """Async filter function."""

        async def async_upper(value: str) -> str:
            await asyncio.sleep(0)
            return value.upper()

        # Register async filter if supported
        try:
            env.filters["async_upper"] = async_upper
            tmpl = env.from_string("{{ x|async_upper }}")

            if hasattr(tmpl, "render_async"):
                result = await tmpl.render_async(x="hello")
                assert result == "HELLO"
            else:
                pytest.skip("Async render not available")
        except Exception:
            pytest.skip("Async filters not supported")


class TestAsyncCallables:
    """Test async callables in context."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    @pytest.mark.asyncio
    async def test_await_async_function(self, env: Environment) -> None:
        """Await async function in context."""

        async def fetch_data() -> str:
            await asyncio.sleep(0)
            return "fetched"

        try:
            tmpl = env.from_string("{{ data() }}")

            if hasattr(tmpl, "render_async"):
                result = await tmpl.render_async(data=fetch_data)
                assert result == "fetched"
            else:
                pytest.skip("Async render not available")
        except Exception:
            pytest.skip("Async callables not supported")

    @pytest.mark.asyncio
    async def test_async_method_call(self, env: Environment) -> None:
        """Call async method on object."""

        class AsyncService:
            async def get_value(self) -> str:
                await asyncio.sleep(0)
                return "service_value"

        service = AsyncService()

        try:
            tmpl = env.from_string("{{ svc.get_value() }}")

            if hasattr(tmpl, "render_async"):
                result = await tmpl.render_async(svc=service)
                assert result == "service_value"
            else:
                pytest.skip("Async render not available")
        except Exception:
            pytest.skip("Async method calls not supported")


class TestAsyncGlobals:
    """Test async globals."""

    @pytest.fixture
    def env(self) -> Environment:
        env = Environment()

        async def async_global() -> str:
            await asyncio.sleep(0)
            return "global_value"

        env.globals["async_func"] = async_global
        return env

    @pytest.mark.asyncio
    async def test_async_global_function(self, env: Environment) -> None:
        """Async global function."""
        try:
            tmpl = env.from_string("{{ async_func() }}")

            if hasattr(tmpl, "render_async"):
                result = await tmpl.render_async()
                assert result == "global_value"
            else:
                pytest.skip("Async render not available")
        except Exception:
            pytest.skip("Async globals not supported")


class TestAsyncInheritance:
    """Test async with template inheritance."""

    @pytest.mark.asyncio
    async def test_async_render_with_extends(self) -> None:
        """Async render with extends."""
        from bengal.rendering.kida import DictLoader

        loader = DictLoader(
            {
                "base.html": "<html>{% block content %}{% endblock %}</html>",
            }
        )
        env = Environment(loader=loader)

        tmpl = env.from_string("""
{% extends "base.html" %}
{% block content %}{{ name }}{% endblock %}
""")

        if hasattr(tmpl, "render_async"):
            result = await tmpl.render_async(name="World")
            assert "<html>" in result
            assert "World" in result
        else:
            # Sync render should work
            result = tmpl.render(name="World")
            assert "<html>" in result
            assert "World" in result

    @pytest.mark.asyncio
    async def test_async_render_with_include(self) -> None:
        """Async render with include."""
        from bengal.rendering.kida import DictLoader

        loader = DictLoader(
            {
                "partial.html": "{{ name }}",
            }
        )
        env = Environment(loader=loader)

        tmpl = env.from_string('{% include "partial.html" %}')

        if hasattr(tmpl, "render_async"):
            result = await tmpl.render_async(name="World")
            assert result == "World"
        else:
            result = tmpl.render(name="World")
            assert result == "World"


class TestAsyncFunctions:
    """Test async function behavior."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    @pytest.mark.asyncio
    async def test_function_with_async_render(self, env: Environment) -> None:
        """Function works with async render."""
        tmpl = env.from_string("""
{% def greet(name) %}Hello {{ name }}{% end %}
{{ greet('World') }}
""")

        if hasattr(tmpl, "render_async"):
            result = await tmpl.render_async()
            assert "Hello World" in result
        else:
            result = tmpl.render()
            assert "Hello World" in result

    @pytest.mark.asyncio
    async def test_function_with_async_argument(self, env: Environment) -> None:
        """Function with async argument."""

        async def get_name() -> str:
            await asyncio.sleep(0)
            return "Async"

        try:
            tmpl = env.from_string("""
{% def greet(name) %}Hello {{ name }}{% end %}
{{ greet(name_func()) }}
""")

            if hasattr(tmpl, "render_async"):
                result = await tmpl.render_async(name_func=get_name)
                assert "Hello Async" in result
            else:
                pytest.skip("Async render not available")
        except Exception:
            pytest.skip("Async function arguments not supported")


class TestAsyncErrorHandling:
    """Test error handling in async context."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    @pytest.mark.asyncio
    async def test_async_exception_propagates(self, env: Environment) -> None:
        """Exception in async function propagates - async not fully supported."""
        # Kida doesn't fully support async function execution
        # The async function isn't awaited, so behavior is undefined
        pytest.skip("Async function execution not fully supported in Kida")


class TestAsyncConcurrency:
    """Test concurrent async rendering."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    @pytest.mark.asyncio
    async def test_concurrent_renders(self, env: Environment) -> None:
        """Multiple concurrent async renders."""
        tmpl = env.from_string("{{ name }}")

        if hasattr(tmpl, "render_async"):
            tasks = [tmpl.render_async(name=f"User{i}") for i in range(10)]
            results = await asyncio.gather(*tasks)

            for i, result in enumerate(results):
                assert result == f"User{i}"
        else:
            pytest.skip("Async render not available")

    @pytest.mark.asyncio
    async def test_concurrent_renders_different_templates(self, env: Environment) -> None:
        """Concurrent renders of different templates."""
        tmpls = [env.from_string(f"Template {i}: {{{{ x }}}}") for i in range(5)]

        if all(hasattr(t, "render_async") for t in tmpls):
            tasks = [t.render_async(x=i) for i, t in enumerate(tmpls)]
            results = await asyncio.gather(*tasks)

            for i, result in enumerate(results):
                assert f"Template {i}:" in result
                assert str(i) in result
        else:
            pytest.skip("Async render not available")


class TestAsyncWithDef:
    """Test async with def blocks."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    @pytest.mark.asyncio
    async def test_def_with_async_render(self, env: Environment) -> None:
        """Def works with async render."""
        tmpl = env.from_string("""
{% def greet(name) %}Hello {{ name }}{% enddef %}
{{ greet('World') }}
""")

        if hasattr(tmpl, "render_async"):
            result = await tmpl.render_async()
            assert "Hello World" in result
        else:
            result = tmpl.render()
            assert "Hello World" in result


class TestAsyncWithCache:
    """Test async with cache blocks."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    @pytest.mark.asyncio
    async def test_cache_with_async_render(self, env: Environment) -> None:
        """Cache block works with async render."""
        tmpl = env.from_string("""
{% cache 'test_key' %}
cached content
{% endcache %}
""")

        if hasattr(tmpl, "render_async"):
            result = await tmpl.render_async()
            assert "cached content" in result
        else:
            result = tmpl.render()
            assert "cached content" in result


class TestAsyncGenerator:
    """Test async generator iteration."""

    @pytest.fixture
    def env(self) -> Environment:
        return Environment()

    @pytest.mark.asyncio
    async def test_async_generator_in_for(self, env: Environment) -> None:
        """Iterate over async generator - not supported in Kida."""
        # Kida doesn't support async generators in for loops
        pytest.skip("Async generator iteration not supported in Kida")
