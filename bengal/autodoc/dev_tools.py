"""
Template development and validation tools.

Provides utilities for template development, testing, and debugging including
sample data generation, performance profiling, and hot-reloading support.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from bengal.autodoc.base import DocElement
from bengal.autodoc.template_safety import SafeTemplateRenderer, TemplateValidator
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TemplatePerformanceMetrics:
    """Performance metrics for template rendering."""

    template_name: str
    render_time_ms: float
    content_size_bytes: int
    cache_hit: bool
    error_count: int
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


class SampleDataGenerator:
    """Generate sample data for testing templates."""

    def __init__(self):
        self.sample_counter = 0

    def generate_python_module(self, name: str = "sample_module") -> DocElement:
        """Generate sample Python module element."""
        self.sample_counter += 1

        # Create sample module
        module = DocElement(
            name=name,
            element_type="module",
            qualified_name=f"sample.{name}",
            description=f"Sample module for testing template rendering. This is module #{self.sample_counter}.",
            source_file=f"sample/{name}.py",
            line_number=1,
        )

        # Add sample classes
        sample_class = DocElement(
            name="SampleClass",
            element_type="class",
            qualified_name=f"sample.{name}.SampleClass",
            description="A sample class for testing class documentation templates.",
            source_file=f"sample/{name}.py",
            line_number=10,
            metadata={"bases": ["BaseClass", "Mixin"], "is_dataclass": False, "aliases": ["SC"]},
        )

        # Add sample methods to class
        sample_method = DocElement(
            name="sample_method",
            element_type="method",
            qualified_name=f"sample.{name}.SampleClass.sample_method",
            description="A sample method with parameters and return value.",
            source_file=f"sample/{name}.py",
            line_number=15,
            metadata={
                "signature": "def sample_method(self, param1: str, param2: int = 42) -> bool:",
                "is_async": False,
                "is_classmethod": False,
                "is_staticmethod": False,
                "args": [
                    {
                        "name": "param1",
                        "type": "str",
                        "description": "First parameter description",
                        "default": None,
                    },
                    {
                        "name": "param2",
                        "type": "int",
                        "description": "Second parameter with default",
                        "default": "42",
                    },
                ],
                "returns": "bool",
                "parsed_doc": {
                    "returns": "True if successful, False otherwise",
                    "raises": [
                        {"type": "ValueError", "description": "If param1 is empty"},
                        {"type": "TypeError", "description": "If param2 is not an integer"},
                    ],
                    "examples": [
                        "result = obj.sample_method('hello', 123)",
                        "success = obj.sample_method('world')",
                    ],
                    "notes": ["This is a sample note about the method"],
                    "warnings": [],
                    "deprecated": None,
                },
            },
        )

        # Add sample property
        sample_property = DocElement(
            name="sample_property",
            element_type="method",
            qualified_name=f"sample.{name}.SampleClass.sample_property",
            description="A sample property with getter and setter.",
            source_file=f"sample/{name}.py",
            line_number=25,
            metadata={
                "signature": "@property\ndef sample_property(self) -> str:",
                "is_property": True,
            },
        )

        sample_class.children = [sample_method, sample_property]

        # Add sample function
        sample_function = DocElement(
            name="sample_function",
            element_type="function",
            qualified_name=f"sample.{name}.sample_function",
            description="A sample standalone function for testing function templates.",
            source_file=f"sample/{name}.py",
            line_number=35,
            metadata={
                "signature": "def sample_function(data: List[str]) -> Dict[str, int]:",
                "is_async": False,
                "args": [
                    {
                        "name": "data",
                        "type": "List[str]",
                        "description": "List of strings to process",
                        "default": None,
                    }
                ],
                "returns": "Dict[str, int]",
                "parsed_doc": {
                    "returns": "Dictionary mapping strings to their lengths",
                    "examples": ["result = sample_function(['hello', 'world'])"],
                },
            },
        )

        module.children = [sample_class, sample_function]
        return module

    def generate_cli_command(self, name: str = "sample-command") -> DocElement:
        """Generate sample CLI command element."""
        self.sample_counter += 1

        command = DocElement(
            name=name,
            element_type="command",
            qualified_name=name,
            description=f"Sample CLI command for testing command templates. Command #{self.sample_counter}.",
            source_file="cli/commands.py",
            line_number=50,
            metadata={
                "usage": f"{name} [OPTIONS] <input-file>",
                "aliases": [f"{name[:3]}", f"{name}-alt"],
                "deprecated": False,
                "experimental": False,
            },
        )

        # Add sample arguments
        input_arg = DocElement(
            name="input-file",
            element_type="argument",
            qualified_name=f"{name}.input-file",
            description="Input file to process",
            metadata={"type": "path", "required": True, "multiple": False},
        )

        # Add sample options
        verbose_option = DocElement(
            name="--verbose",
            element_type="option",
            qualified_name=f"{name}.--verbose",
            description="Enable verbose output",
            metadata={"short_name": "v", "type": "flag", "default": False, "required": False},
        )

        output_option = DocElement(
            name="--output",
            element_type="option",
            qualified_name=f"{name}.--output",
            description="Output file path",
            metadata={
                "short_name": "o",
                "type": "path",
                "default": "output.txt",
                "required": False,
            },
        )

        command.children = [input_arg, verbose_option, output_option]
        command.metadata["examples"] = [
            {
                "command": f"{name} input.txt",
                "description": "Process input.txt with default settings",
            },
            {
                "command": f"{name} --verbose --output result.txt input.txt",
                "description": "Process with verbose output to custom file",
            },
        ]

        return command

    def generate_openapi_endpoint(
        self, path: str = "/api/users", method: str = "GET"
    ) -> DocElement:
        """Generate sample OpenAPI endpoint element."""
        self.sample_counter += 1

        endpoint = DocElement(
            name=f"{method.upper()} {path}",
            element_type="endpoint",
            qualified_name=f"{method.lower()}_{path.replace('/', '_').strip('_')}",
            description=f"Sample API endpoint for testing OpenAPI templates. Endpoint #{self.sample_counter}.",
            source_file="api/openapi.yaml",
            line_number=100,
            metadata={
                "method": method.lower(),
                "path": path,
                "operation_id": f"{method.lower()}Users",
                "tags": ["users", "api"],
                "deprecated": False,
                "auth_required": True,
                "summary": f"{method.upper()} operation for users resource",
            },
        )

        # Add sample parameters
        if method.upper() == "GET":
            limit_param = DocElement(
                name="limit",
                element_type="parameter",
                qualified_name=f"{endpoint.qualified_name}.limit",
                description="Maximum number of users to return",
                metadata={
                    "in": "query",
                    "type": "integer",
                    "required": False,
                    "default": 10,
                    "minimum": 1,
                    "maximum": 100,
                },
            )
            endpoint.children = [limit_param]

        # Add sample request/response data
        endpoint.metadata.update(
            {
                "request_body": {
                    "description": "User data to create or update",
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "User's full name"},
                                    "email": {"type": "string", "format": "email"},
                                    "age": {"type": "integer", "minimum": 0},
                                },
                                "required": ["name", "email"],
                            },
                            "example": {"name": "John Doe", "email": "john@example.com", "age": 30},
                        }
                    },
                }
                if method.upper() in ["POST", "PUT"]
                else None,
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "name": {"type": "string"},
                                        "email": {"type": "string"},
                                    },
                                },
                                "example": {
                                    "id": 123,
                                    "name": "John Doe",
                                    "email": "john@example.com",
                                },
                            }
                        },
                    },
                    "400": {
                        "description": "Bad request",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {"type": "string"},
                                        "message": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                },
                "examples": [
                    {
                        "request": f"{method.upper()} {path}\nContent-Type: application/json\n\n"
                        + json.dumps({"name": "John Doe", "email": "john@example.com"}, indent=2),
                        "response": "HTTP/1.1 200 OK\nContent-Type: application/json\n\n"
                        + json.dumps(
                            {"id": 123, "name": "John Doe", "email": "john@example.com"}, indent=2
                        ),
                    }
                ],
            }
        )

        return endpoint

    def generate_sample_config(self) -> dict[str, Any]:
        """Generate sample configuration for template testing."""
        return {
            "autodoc": {
                "template_safety": {
                    "error_boundaries": True,
                    "fallback_content": True,
                    "debug_mode": True,
                    "validate_templates": True,
                }
            },
            "project": {
                "name": "Sample Project",
                "version": "1.0.0",
                "description": "A sample project for template testing",
            },
        }


class TemplateDebugger:
    """Debug template rendering with detailed error information."""

    def __init__(self, renderer: SafeTemplateRenderer, validator: TemplateValidator):
        self.renderer = renderer
        self.validator = validator
        self.debug_sessions: list[dict[str, Any]] = []

    def debug_template(self, template_name: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Debug template rendering with comprehensive information.

        Args:
            template_name: Name of template to debug
            context: Template context

        Returns:
            Debug information including validation, rendering results, and errors
        """
        debug_info = {
            "template_name": template_name,
            "timestamp": datetime.now().isoformat(),
            "validation": {},
            "rendering": {},
            "context_analysis": {},
        }

        # Validate template syntax
        validation_issues = self.validator.validate_template(template_name)
        debug_info["validation"] = {
            "issues": validation_issues,
            "is_valid": len(validation_issues) == 0,
        }

        # Analyze context
        element = context.get("element")
        debug_info["context_analysis"] = {
            "keys": list(context.keys()),
            "element_type": getattr(element, "element_type", "Unknown") if element else "Unknown",
            "element_name": getattr(element, "name", "Unknown") if element else "Unknown",
            "context_size": len(str(context)),
        }

        # Attempt rendering with error capture
        start_time = time.time()
        try:
            content = self.renderer.render_with_boundaries(template_name, context)
            render_time = (time.time() - start_time) * 1000

            debug_info["rendering"] = {
                "success": True,
                "content_length": len(content),
                "render_time_ms": render_time,
                "content_preview": content[:200] + "..." if len(content) > 200 else content,
                "errors": [],
            }

        except Exception as e:
            render_time = (time.time() - start_time) * 1000
            debug_info["rendering"] = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "render_time_ms": render_time,
                "content_length": 0,
            }

        # Collect renderer errors
        if self.renderer.errors:
            debug_info["rendering"]["errors"] = self.renderer.errors.copy()
            self.renderer.clear_errors()

        self.debug_sessions.append(debug_info)
        return debug_info

    def get_debug_report(self) -> str:
        """Generate human-readable debug report."""
        if not self.debug_sessions:
            return "No debug sessions recorded."

        lines = []
        lines.append("🔍 Template Debug Report")
        lines.append("=" * 50)
        lines.append("")

        for i, session in enumerate(self.debug_sessions, 1):
            lines.append(f"Debug Session #{i}: {session['template_name']}")
            lines.append(f"  Timestamp: {session['timestamp']}")

            # Validation info
            validation = session["validation"]
            if validation["is_valid"]:
                lines.append("  ✅ Template validation: PASSED")
            else:
                lines.append(
                    f"  ❌ Template validation: FAILED ({len(validation['issues'])} issues)"
                )
                for issue in validation["issues"][:3]:
                    lines.append(f"    - {issue}")

            # Context info
            context = session["context_analysis"]
            lines.append(
                f"  📊 Context: {context['element_type']} '{context['element_name']}' ({len(context['keys'])} keys)"
            )

            # Rendering info
            rendering = session["rendering"]
            if rendering["success"]:
                lines.append(
                    f"  ✅ Rendering: SUCCESS ({rendering['render_time_ms']:.1f}ms, {rendering['content_length']} chars)"
                )
            else:
                lines.append(
                    f"  ❌ Rendering: FAILED ({rendering['error_type']}: {rendering['error']})"
                )

            lines.append("")

        return "\n".join(lines)

    def export_debug_session(self, session_index: int, output_path: Path) -> None:
        """Export debug session to JSON file."""
        if 0 <= session_index < len(self.debug_sessions):
            session = self.debug_sessions[session_index]
            output_path.write_text(json.dumps(session, indent=2))
            logger.info("debug_session_exported", path=str(output_path), session=session_index)


class TemplateProfiler:
    """Profile template rendering performance."""

    def __init__(self):
        self.metrics: list[TemplatePerformanceMetrics] = []

    def profile_template(
        self,
        template_name: str,
        renderer: SafeTemplateRenderer,
        context: dict[str, Any],
        cache_hit: bool = False,
    ) -> TemplatePerformanceMetrics:
        """
        Profile template rendering performance.

        Args:
            template_name: Name of template to profile
            renderer: Template renderer
            context: Template context
            cache_hit: Whether this was a cache hit

        Returns:
            Performance metrics
        """
        start_time = time.time()
        error_count_before = renderer.error_count

        try:
            content = renderer.render_with_boundaries(template_name, context)
            content_size = len(content.encode("utf-8"))
        except Exception:
            content_size = 0

        render_time = (time.time() - start_time) * 1000
        error_count = renderer.error_count - error_count_before

        metrics = TemplatePerformanceMetrics(
            template_name=template_name,
            render_time_ms=render_time,
            content_size_bytes=content_size,
            cache_hit=cache_hit,
            error_count=error_count,
            timestamp=datetime.now().isoformat(),
        )

        self.metrics.append(metrics)
        return metrics

    def get_performance_summary(self) -> dict[str, Any]:
        """Get performance summary statistics."""
        if not self.metrics:
            return {"message": "No performance data collected"}

        render_times = [m.render_time_ms for m in self.metrics]
        content_sizes = [m.content_size_bytes for m in self.metrics]

        return {
            "total_renders": len(self.metrics),
            "avg_render_time_ms": sum(render_times) / len(render_times),
            "min_render_time_ms": min(render_times),
            "max_render_time_ms": max(render_times),
            "avg_content_size_bytes": sum(content_sizes) / len(content_sizes),
            "total_errors": sum(m.error_count for m in self.metrics),
            "cache_hit_rate": sum(1 for m in self.metrics if m.cache_hit) / len(self.metrics),
            "templates_profiled": len(set(m.template_name for m in self.metrics)),
        }

    def export_metrics(self, output_path: Path) -> None:
        """Export performance metrics to JSON file."""
        data = {
            "summary": self.get_performance_summary(),
            "metrics": [m.to_dict() for m in self.metrics],
            "exported_at": datetime.now().isoformat(),
        }

        output_path.write_text(json.dumps(data, indent=2))
        logger.info(
            "performance_metrics_exported", path=str(output_path), metric_count=len(self.metrics)
        )


class TemplateHotReloader:
    """Hot-reload templates during development."""

    def __init__(self, template_dirs: list[Path]):
        self.template_dirs = template_dirs
        self.file_timestamps: dict[str, float] = {}
        self.reload_callbacks: list[callable] = []

    def register_reload_callback(self, callback: callable) -> None:
        """Register callback to be called when templates are reloaded."""
        self.reload_callbacks.append(callback)

    def check_for_changes(self) -> list[str]:
        """
        Check for template file changes.

        Returns:
            List of changed template files
        """
        changed_files = []

        for template_dir in self.template_dirs:
            if not template_dir.exists():
                continue

            for template_file in template_dir.rglob("*.jinja2"):
                file_path = str(template_file)
                current_mtime = template_file.stat().st_mtime

                if file_path not in self.file_timestamps:
                    self.file_timestamps[file_path] = current_mtime
                elif self.file_timestamps[file_path] < current_mtime:
                    self.file_timestamps[file_path] = current_mtime
                    changed_files.append(file_path)

        return changed_files

    def trigger_reload(self, changed_files: list[str]) -> None:
        """Trigger reload callbacks for changed files."""
        if changed_files:
            logger.info("template_files_changed", files=changed_files, count=len(changed_files))

            for callback in self.reload_callbacks:
                try:
                    callback(changed_files)
                except Exception as e:
                    logger.error("reload_callback_failed", error=str(e), callback=str(callback))

    def start_watching(self, check_interval: float = 1.0) -> None:
        """
        Start watching for template changes.

        Args:
            check_interval: How often to check for changes (seconds)
        """
        import threading
        import time

        def watch_loop():
            while True:
                try:
                    changed_files = self.check_for_changes()
                    if changed_files:
                        self.trigger_reload(changed_files)
                    time.sleep(check_interval)
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error("template_watcher_error", error=str(e))
                    time.sleep(check_interval)

        watcher_thread = threading.Thread(target=watch_loop, daemon=True)
        watcher_thread.start()
        logger.info("template_hot_reloader_started", dirs=[str(d) for d in self.template_dirs])


def create_development_tools(
    renderer: SafeTemplateRenderer, validator: TemplateValidator, template_dirs: list[Path]
) -> dict[str, Any]:
    """
    Create complete set of development tools.

    Args:
        renderer: Safe template renderer
        validator: Template validator
        template_dirs: Template directories to watch

    Returns:
        Dictionary of development tools
    """
    return {
        "sample_generator": SampleDataGenerator(),
        "debugger": TemplateDebugger(renderer, validator),
        "profiler": TemplateProfiler(),
        "hot_reloader": TemplateHotReloader(template_dirs),
    }
