from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest

from bengal.rendering.engines.kida import KidaTemplateEngine


def test_kida_thread_safety_parallel_contexts():
    """Verify Kida engine handles parallel renders with different contexts safely."""
    # Mock site and config
    site = MagicMock()
    site.config = {"template_engine": "kida"}
    site.root_path = MagicMock()  # Required for BytecodeCache
    site.theme_config = MagicMock()

    # Initialize engine
    engine = KidaTemplateEngine(site)

    # Shared results
    errors: list[str] = []

    def render_task(user_id: int):
        try:
            # Each thread has a unique context
            context = {
                "user": f"User_{user_id}",
                "page": MagicMock(source_path=f"page_{user_id}.md"),
            }
            # Template string that uses the context
            template = "Hello {{ user }} from {{ page.source_path }}!"

            # Render multiple times to increase race chance
            for _ in range(50):
                rendered = engine.render_string(template, context)
                if rendered != f"Hello User_{user_id} from page_{user_id}.md!":
                    errors.append(f"Thread {user_id} got wrong output: {rendered}")
        except Exception as e:
            errors.append(f"Thread {user_id} failed: {e}")

    # Run in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(render_task, i) for i in range(10)]
        for f in futures:
            f.result()

    assert not errors, f"Thread-safety violations detected: {errors}"


def test_kida_no_globals_leakage():
    """Verify that variables from one render don't leak into the global environment."""
    site = MagicMock()
    site.config = {}
    site.root_path = MagicMock()
    engine = KidaTemplateEngine(site)

    # 1. Render with a variable
    engine.render_string("{{ secret }}", {"secret": "X"})

    # 2. Render WITHOUT the variable - should fail/be empty, not "X"
    # Kida by default is strict, so it should raise or be empty if strict=False
    with pytest.raises((KeyError, NameError, LookupError)):  # Kida is strict by default
        engine.render_string("{{ secret }}", {})
