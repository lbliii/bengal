"""
CLI interface for template development tools.

Provides command-line access to template validation, debugging, and testing tools.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from bengal.autodoc.dev_tools import (
    create_development_tools,
)
from bengal.autodoc.template_safety import (
    SafeTemplateRenderer,
    TemplateValidator,
    create_safe_environment,
)
from bengal.utils.logger import get_logger

logger = get_logger(__name__)


@click.group()
@click.option(
    "--template-dir",
    multiple=True,
    type=click.Path(exists=True, path_type=Path),
    help="Template directories to use (can be specified multiple times)",
)
@click.option(
    "--config", type=click.Path(exists=True, path_type=Path), help="Configuration file path"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def template_dev(ctx: click.Context, template_dir: tuple[Path], config: Path | None, verbose: bool):
    """Template development and validation tools."""
    ctx.ensure_object(dict)

    # Setup template directories
    if template_dir:
        template_dirs = list(template_dir)
    else:
        # Default template directories
        template_dirs = [Path("templates/autodoc"), Path(__file__).parent / "templates"]
        template_dirs = [d for d in template_dirs if d.exists()]

    if not template_dirs:
        click.echo(
            "❌ No template directories found. Use --template-dir to specify directories.", err=True
        )
        sys.exit(1)

    # Load configuration
    config_data = {}
    if config and config.exists():
        try:
            if config.suffix == ".json":
                config_data = json.loads(config.read_text())
            else:
                # Assume YAML/TOML - would need proper parsing
                click.echo(
                    f"⚠️ Configuration file {config} format not fully supported, using defaults"
                )
        except Exception as e:
            click.echo(f"❌ Failed to load config {config}: {e}", err=True)
            sys.exit(1)

    # Create template environment and tools
    try:
        env = create_safe_environment(template_dirs)
        renderer = SafeTemplateRenderer(env)
        validator = TemplateValidator(env)

        ctx.obj.update(
            {
                "template_dirs": template_dirs,
                "config": config_data,
                "renderer": renderer,
                "validator": validator,
                "verbose": verbose,
                "dev_tools": create_development_tools(renderer, validator, template_dirs),
            }
        )

        if verbose:
            click.echo(f"📁 Template directories: {[str(d) for d in template_dirs]}")

    except Exception as e:
        click.echo(f"❌ Failed to initialize template system: {e}", err=True)
        sys.exit(1)


@template_dev.command()
@click.argument("template_name")
@click.option(
    "--output", "-o", type=click.Path(path_type=Path), help="Output file for validation report"
)
@click.pass_context
def validate(ctx: click.Context, template_name: str, output: Path | None):
    """Validate template syntax and structure."""
    validator = ctx.obj["validator"]

    click.echo(f"🔍 Validating template: {template_name}")

    try:
        issues = validator.validate_template(template_name)

        if not issues:
            click.echo("✅ Template validation passed - no issues found")
            return

        click.echo(f"❌ Template validation failed - {len(issues)} issues found:")
        for i, issue in enumerate(issues, 1):
            click.echo(f"  {i}. {issue}")

        if output:
            report = {
                "template": template_name,
                "validation_passed": False,
                "issues": issues,
                "timestamp": "now",
            }
            output.write_text(json.dumps(report, indent=2))
            click.echo(f"📄 Validation report saved to {output}")

    except Exception as e:
        click.echo(f"❌ Validation failed: {e}", err=True)
        sys.exit(1)


@template_dev.command()
@click.argument("template_name")
@click.option(
    "--element-type",
    type=click.Choice(["module", "class", "function", "command", "endpoint"]),
    default="module",
    help="Type of sample element to generate",
)
@click.option(
    "--output", "-o", type=click.Path(path_type=Path), help="Output file for debug report"
)
@click.option("--show-content", is_flag=True, help="Show rendered content preview")
@click.pass_context
def debug(
    ctx: click.Context,
    template_name: str,
    element_type: str,
    output: Path | None,
    show_content: bool,
):
    """Debug template rendering with sample data."""
    dev_tools = ctx.obj["dev_tools"]
    config = ctx.obj["config"]
    verbose = ctx.obj["verbose"]

    debugger = dev_tools["debugger"]
    sample_generator = dev_tools["sample_generator"]

    click.echo(f"🐛 Debugging template: {template_name}")
    click.echo(f"📊 Using sample {element_type} element")

    try:
        # Generate sample element
        if element_type == "module":
            element = sample_generator.generate_python_module()
        elif element_type == "class":
            module = sample_generator.generate_python_module()
            element = module.children[0]  # First class
        elif element_type == "function":
            module = sample_generator.generate_python_module()
            element = module.children[1]  # Function
        elif element_type == "command":
            element = sample_generator.generate_cli_command()
        elif element_type == "endpoint":
            element = sample_generator.generate_openapi_endpoint()
        else:
            raise ValueError(f"Unsupported element type: {element_type}")

        # Create context
        context = {
            "element": element,
            "config": config or sample_generator.generate_sample_config(),
        }

        # Debug template
        debug_info = debugger.debug_template(template_name, context)

        # Display results
        validation = debug_info["validation"]
        if validation["is_valid"]:
            click.echo("✅ Template validation: PASSED")
        else:
            click.echo(f"❌ Template validation: FAILED ({len(validation['issues'])} issues)")
            if verbose:
                for issue in validation["issues"]:
                    click.echo(f"    - {issue}")

        rendering = debug_info["rendering"]
        if rendering["success"]:
            click.echo(f"✅ Template rendering: SUCCESS ({rendering['render_time_ms']:.1f}ms)")
            click.echo(f"📏 Content size: {rendering['content_length']} characters")

            if show_content:
                click.echo("\n📄 Rendered content preview:")
                click.echo("-" * 50)
                click.echo(rendering["content_preview"])
                click.echo("-" * 50)
        else:
            click.echo("❌ Template rendering: FAILED")
            click.echo(f"🚨 Error: {rendering['error']}")

        if output:
            debugger.export_debug_session(len(debugger.debug_sessions) - 1, output)
            click.echo(f"📄 Debug report saved to {output}")

    except Exception as e:
        click.echo(f"❌ Debug failed: {e}", err=True)
        if verbose:
            import traceback

            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


@template_dev.command()
@click.argument("template_name")
@click.option("--iterations", "-n", default=10, help="Number of iterations to run")
@click.option(
    "--element-type",
    type=click.Choice(["module", "class", "function", "command", "endpoint"]),
    default="module",
    help="Type of sample element to generate",
)
@click.option(
    "--output", "-o", type=click.Path(path_type=Path), help="Output file for performance metrics"
)
@click.pass_context
def profile(
    ctx: click.Context, template_name: str, iterations: int, element_type: str, output: Path | None
):
    """Profile template rendering performance."""
    dev_tools = ctx.obj["dev_tools"]
    renderer = ctx.obj["renderer"]
    config = ctx.obj["config"]
    verbose = ctx.obj["verbose"]

    profiler = dev_tools["profiler"]
    sample_generator = dev_tools["sample_generator"]

    click.echo(f"⚡ Profiling template: {template_name}")
    click.echo(f"🔄 Running {iterations} iterations with {element_type} elements")

    try:
        # Generate sample element
        if element_type == "module":
            element = sample_generator.generate_python_module()
        elif element_type == "command":
            element = sample_generator.generate_cli_command()
        elif element_type == "endpoint":
            element = sample_generator.generate_openapi_endpoint()
        else:
            module = sample_generator.generate_python_module()
            element = module.children[0] if element_type == "class" else module.children[1]

        context = {
            "element": element,
            "config": config or sample_generator.generate_sample_config(),
        }

        # Run profiling iterations
        with click.progressbar(range(iterations), label="Profiling") as bar:
            for _ in bar:
                profiler.profile_template(template_name, renderer, context)

        # Display results
        summary = profiler.get_performance_summary()

        click.echo("\n📊 Performance Summary:")
        click.echo(f"  Average render time: {summary['avg_render_time_ms']:.2f}ms")
        click.echo(f"  Min render time: {summary['min_render_time_ms']:.2f}ms")
        click.echo(f"  Max render time: {summary['max_render_time_ms']:.2f}ms")
        click.echo(f"  Average content size: {summary['avg_content_size_bytes']:.0f} bytes")
        click.echo(f"  Total errors: {summary['total_errors']}")

        if output:
            profiler.export_metrics(output)
            click.echo(f"📄 Performance metrics saved to {output}")

    except Exception as e:
        click.echo(f"❌ Profiling failed: {e}", err=True)
        if verbose:
            import traceback

            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


@template_dev.command()
@click.option(
    "--element-type",
    type=click.Choice(["module", "command", "endpoint"]),
    default="module",
    help="Type of sample element to generate",
)
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output file for sample data")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml"]),
    default="json",
    help="Output format",
)
@click.pass_context
def generate_sample(ctx: click.Context, element_type: str, output: Path | None, output_format: str):
    """Generate sample data for template testing."""
    dev_tools = ctx.obj["dev_tools"]
    sample_generator = dev_tools["sample_generator"]

    click.echo(f"🎲 Generating sample {element_type} data")

    try:
        # Generate sample element
        if element_type == "module":
            element = sample_generator.generate_python_module()
        elif element_type == "command":
            element = sample_generator.generate_cli_command()
        elif element_type == "endpoint":
            element = sample_generator.generate_openapi_endpoint()
        else:
            raise ValueError(f"Unsupported element type: {element_type}")

        # Convert to dictionary
        sample_data = {
            "element": element.to_dict(),
            "config": sample_generator.generate_sample_config(),
            "generated_at": "now",
        }

        if output:
            if output_format == "json":
                output.write_text(json.dumps(sample_data, indent=2))
            else:
                # YAML output would require PyYAML
                click.echo("⚠️ YAML output not implemented, using JSON")
                output.write_text(json.dumps(sample_data, indent=2))

            click.echo(f"📄 Sample data saved to {output}")
        else:
            # Print to stdout
            click.echo(json.dumps(sample_data, indent=2))

    except Exception as e:
        click.echo(f"❌ Sample generation failed: {e}", err=True)
        sys.exit(1)


@template_dev.command()
@click.option("--check-interval", default=1.0, help="Check interval in seconds")
@click.option("--command", help="Command to run when templates change")
@click.pass_context
def watch(ctx: click.Context, check_interval: float, command: str | None):
    """Watch templates for changes and trigger reloads."""
    dev_tools = ctx.obj["dev_tools"]
    template_dirs = ctx.obj["template_dirs"]
    verbose = ctx.obj["verbose"]

    hot_reloader = dev_tools["hot_reloader"]

    click.echo(f"👀 Watching templates in: {[str(d) for d in template_dirs]}")
    click.echo(f"🔄 Check interval: {check_interval}s")

    if command:
        click.echo(f"🚀 Will run command on changes: {command}")

        def run_command(changed_files):
            import subprocess

            click.echo(f"🔄 Running command due to changes in: {changed_files}")
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    click.echo("✅ Command completed successfully")
                    if verbose and result.stdout:
                        click.echo(result.stdout)
                else:
                    click.echo(f"❌ Command failed with exit code {result.returncode}")
                    if result.stderr:
                        click.echo(result.stderr, err=True)
            except Exception as e:
                click.echo(f"❌ Failed to run command: {e}", err=True)

        hot_reloader.register_reload_callback(run_command)

    try:
        hot_reloader.start_watching(check_interval)
        click.echo("✅ Template watcher started. Press Ctrl+C to stop.")

        # Keep the main thread alive
        import time

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        click.echo("\n🛑 Template watcher stopped")
    except Exception as e:
        click.echo(f"❌ Watcher failed: {e}", err=True)
        sys.exit(1)


@template_dev.command()
@click.pass_context
def list_templates(ctx: click.Context):
    """List all available templates."""
    template_dirs = ctx.obj["template_dirs"]

    click.echo("📋 Available templates:")

    template_count = 0
    for template_dir in template_dirs:
        if not template_dir.exists():
            continue

        click.echo(f"\n📁 {template_dir}:")

        for template_file in sorted(template_dir.rglob("*.jinja2")):
            relative_path = template_file.relative_to(template_dir)
            click.echo(f"  📄 {relative_path}")
            template_count += 1

    click.echo(f"\n📊 Total templates found: {template_count}")


if __name__ == "__main__":
    template_dev()
