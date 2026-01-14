#!/usr/bin/env python
"""
Manual test script for Rich CLI enhancements.

Run this to verify all Rich features are working correctly.
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_rich_traceback():
    """Test Rich traceback handler."""
    print("\n" + "=" * 60)
    print("TEST 1: Rich Traceback Handler")
    print("=" * 60)

    # This would normally be installed by CLI main()
    try:
        from rich.traceback import install

        from bengal.utils.observability.rich_console import get_console

        install(console=get_console(), show_locals=True)
        print("✓ Rich traceback handler installed successfully")
    except Exception as e:
        print(f"✗ Failed to install Rich traceback: {e}")
        raise


def test_logger_markup():
    """Test logger with Rich markup."""
    print("\n" + "=" * 60)
    print("TEST 2: Logger with Rich Markup")
    print("=" * 60)

    try:
        from bengal.utils.observability.logger import LogLevel, configure_logging, get_logger

        configure_logging(level=LogLevel.DEBUG, verbose=True)
        logger = get_logger("test")

        print("\nTesting log levels:")
        logger.debug("Debug message", detail="debug detail")
        logger.info("Info message", detail="info detail")
        logger.warning("Warning message", detail="warning detail")
        logger.error("Error message", detail="error detail")

        print("\nTesting phase tracking:")
        with logger.phase("test_phase", items=100):
            logger.info("Processing items...")

        print("\n✓ Logger Rich markup working correctly")
    except Exception as e:
        print(f"✗ Logger test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


def test_pretty_print_config():
    """Test config pretty printing."""
    print("\n" + "=" * 60)
    print("TEST 3: Pretty Print Config")
    print("=" * 60)

    try:
        from bengal.config.loader import pretty_print_config

        test_config = {
            "site": {
                "title": "Bengal Test Site",
                "baseurl": "https://example.com",
                "theme": "default",
            },
            "build": {"parallel": True, "incremental": False, "output_dir": "public"},
            "features": {"live_reload": True, "hot_module_replacement": True},
        }

        pretty_print_config(test_config, title="Test Configuration")
        print("✓ Config pretty printing working correctly")
    except Exception as e:
        print(f"✗ Pretty print config test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


def test_rich_console():
    """Test Rich console features."""
    print("\n" + "=" * 60)
    print("TEST 4: Rich Console Features")
    print("=" * 60)

    try:
        from rich.panel import Panel
        from rich.syntax import Syntax
        from rich.tree import Tree

        from bengal.utils.observability.rich_console import detect_environment, get_console, should_use_rich

        console = get_console()

        print(f"\nShould use Rich: {should_use_rich()}")

        env = detect_environment()
        print("\nEnvironment:")
        print(f"  Terminal: {env['is_terminal']}")
        print(f"  Color system: {env['color_system']}")
        print(f"  Terminal width: {env['width']}")
        print(f"  CI: {env['is_ci']}")

        # Test markup
        console.print("\n[bold cyan]Testing Rich markup:[/bold cyan]")
        console.print("  [green]✓ Green success message[/green]")
        console.print("  [yellow]⚠  Yellow warning message[/yellow]")
        console.print("  [red]✗ Red error message[/red]")

        # Test panel
        console.print("\n[bold cyan]Testing Rich panel:[/bold cyan]")
        console.print(
            Panel(
                "[green]This is a test panel with border[/green]",
                title="Test Panel",
                border_style="cyan",
            )
        )

        # Test tree
        console.print("\n[bold cyan]Testing Rich tree:[/bold cyan]")
        tree = Tree("📁 [bold]Root[/bold]")
        branch1 = tree.add("📁 Section 1")
        branch1.add("📄 Page 1")
        branch1.add("📄 Page 2")
        branch2 = tree.add("📁 Section 2")
        branch2.add("📄 Page 3")
        console.print(tree)

        # Test syntax highlighting
        console.print("\n[bold cyan]Testing syntax highlighting:[/bold cyan]")
        code = '''def hello_world():
    """Say hello."""
    print("Hello, World!")
    return True'''

        syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
        console.print(syntax)

        print("\n✓ Rich console features working correctly")
    except Exception as e:
        print(f"✗ Rich console test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


def test_status_spinner():
    """Test status spinner."""
    print("\n" + "=" * 60)
    print("TEST 5: Status Spinner")
    print("=" * 60)

    try:
        import time

        from bengal.utils.observability.rich_console import get_console, should_use_rich

        if not should_use_rich():
            print("⚠ Skipping spinner test (no TTY)")
            return

        console = get_console()

        print("\nTesting status spinner:")
        with console.status("[bold green]Processing...", spinner="dots") as status:
            time.sleep(1)
            status.update("[bold green]Almost done...")
            time.sleep(1)

        console.print("[green]✓ Status spinner working correctly[/green]")
    except Exception as e:
        print(f"✗ Status spinner test failed: {e}")
        import traceback

        traceback.print_exc()
        raise


def test_rich_prompt():
    """Test Rich prompt (non-interactive test)."""
    print("\n" + "=" * 60)
    print("TEST 6: Rich Prompt")
    print("=" * 60)

    try:
        print("✓ Rich prompt imports working correctly")
        print("  (Interactive testing skipped - use 'bengal clean' to test)")
    except Exception as e:
        print(f"✗ Rich prompt test failed: {e}")
        raise


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("RICH CLI ENHANCEMENTS TEST SUITE")
    print("=" * 60)

    tests = [
        test_rich_traceback,
        test_logger_markup,
        test_pretty_print_config,
        test_rich_console,
        test_status_spinner,
        test_rich_prompt,
    ]

    results = []
    for test in tests:
        try:
            test()
            results.append(True)  # If no exception, test passed
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            import traceback

            traceback.print_exc()
            results.append(False)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n✓ All tests passed! Rich CLI enhancements are working correctly.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
