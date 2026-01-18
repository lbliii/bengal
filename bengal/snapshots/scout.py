"""
Scout thread for predictive cache warming.

Runs ahead of workers, warming caches for templates and partials that will
be needed soon. Reads from frozen snapshot (lock-free).

"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bengal.snapshots.types import SiteSnapshot, ScoutHint


class ScoutThread(threading.Thread):
    """
    Lookahead thread that warms caches ahead of workers.
    
    Reads from frozen snapshot (lock-free).
    Communicates via lock-free deque operations.
    """

    def __init__(
        self,
        snapshot: SiteSnapshot,
        template_engine: Any,  # TemplateEngineProtocol type
        lookahead_waves: int = 3,
    ):
        super().__init__(name="Bengal-Scout", daemon=True)
        self.snapshot = snapshot
        self.template_engine = template_engine
        self.lookahead_waves = lookahead_waves
        self._stop_event = threading.Event()

        # Progress tracking (for workers to know what's warm)
        self.warmed_templates: set[str] = set()
        self._current_wave = 0
        self._worker_wave = 0  # Set by workers

    def run(self) -> None:
        """Warm caches following pre-computed hints."""
        for hint in self.snapshot.scout_hints:
            if self._stop_event.is_set():
                break

            # 1. Warm primary template
            template_name = hint.template_path.name
            if template_name not in self.warmed_templates:
                self._warm_template(template_name)
                self.warmed_templates.add(template_name)

            # 2. Warm partials (recursive discovery via TemplateAnalyzer)
            for partial in hint.partial_paths:
                partial_name = partial.name
                if partial_name not in self.warmed_templates:
                    self._warm_template(partial_name)
                    self.warmed_templates.add(partial_name)

            self._current_wave += 1

            # Pace ourselves - don't get too far ahead
            while (
                self._current_wave > self.lookahead_waves + self._worker_wave
                and not self._stop_event.is_set()
            ):
                self._stop_event.wait(0.005)

    def _warm_template(self, template_name: str) -> None:
        """Execute non-blocking compile/load into shared engine cache."""
        try:
            # Try to get template (will compile/load if needed)
            # This warms the engine's internal cache
            if hasattr(self.template_engine, "template_exists"):
                # Check if template exists first (avoids exceptions)
                if not self.template_engine.template_exists(template_name):
                    return
            
            # Use render_template method if available (safest approach)
            if hasattr(self.template_engine, "render_template"):
                # Try to get template via environment
                if hasattr(self.template_engine, "_env"):
                    env = self.template_engine._env
                    if hasattr(env, "get_template"):
                        env.get_template(template_name)
                elif hasattr(self.template_engine, "env"):
                    env = self.template_engine.env
                    if hasattr(env, "get_template"):
                        env.get_template(template_name)
            elif hasattr(self.template_engine, "get_template"):
                self.template_engine.get_template(template_name)
        except Exception:
            # Scout failures are non-fatal; workers will compile on demand
            pass

    def stop(self) -> None:
        """Signal scout to stop."""
        self._stop_event.set()
