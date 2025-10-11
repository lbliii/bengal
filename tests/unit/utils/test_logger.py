"""Tests for structured logging system."""

import json

import pytest

from bengal.utils.logger import (
    BengalLogger,
    LogEvent,
    LogLevel,
    close_all_loggers,
    configure_logging,
    get_logger,
)


@pytest.fixture
def logger(tmp_path):
    """Create a test logger."""
    log_file = tmp_path / "test.log"
    logger = BengalLogger(
        name="test_logger",
        level=LogLevel.DEBUG,
        log_file=log_file,
        verbose=False
    )
    yield logger
    logger.close()


@pytest.fixture
def verbose_logger(tmp_path):
    """Create a verbose test logger."""
    log_file = tmp_path / "test.log"
    logger = BengalLogger(
        name="test_logger",
        level=LogLevel.DEBUG,
        log_file=log_file,
        verbose=True
    )
    yield logger
    logger.close()


def test_basic_logging(logger, capsys):
    """Test basic log emission."""
    logger.info("test_message", key="value")

    captured = capsys.readouterr()
    assert "test_message" in captured.out

    events = logger.get_events()
    assert len(events) == 1
    assert events[0].message == "test_message"
    assert events[0].context["key"] == "value"


def test_log_levels(logger, capsys):
    """Test different log levels."""
    logger.debug("debug msg")
    logger.info("info msg")
    logger.warning("warning msg")
    logger.error("error msg")
    logger.critical("critical msg")

    events = logger.get_events()
    assert len(events) == 5
    assert events[0].level == "DEBUG"
    assert events[1].level == "INFO"
    assert events[2].level == "WARNING"
    assert events[3].level == "ERROR"
    assert events[4].level == "CRITICAL"


def test_log_level_filtering():
    """Test that log level filtering works."""
    logger = BengalLogger(name="test", level=LogLevel.WARNING)

    logger.debug("should not appear")
    logger.info("should not appear")
    logger.warning("should appear")
    logger.error("should appear")

    events = logger.get_events()
    assert len(events) == 2
    assert all(e.level in ("WARNING", "ERROR") for e in events)


def test_phase_tracking(logger, capsys):
    """Test phase context manager."""
    with logger.phase("test_phase", count=42):
        logger.info("inside_phase")

    events = logger.get_events()

    # Should have: phase_start, inside_phase, phase_complete
    assert len(events) == 3

    # Check phase_start
    assert events[0].event_type == "phase_start"
    assert events[0].phase == "test_phase"
    assert events[0].context["phase_name"] == "test_phase"
    assert events[0].context["count"] == 42

    # Check inside_phase
    assert events[1].message == "inside_phase"
    assert events[1].phase == "test_phase"
    assert events[1].context["count"] == 42  # Context propagated

    # Check phase_complete
    assert events[2].event_type == "phase_complete"
    assert events[2].duration_ms is not None
    assert events[2].duration_ms >= 0


def test_nested_phases(logger):
    """Test nested phase tracking."""
    with logger.phase("outer"):
        logger.info("outer_msg")
        with logger.phase("inner"):
            logger.info("inner_msg")
        logger.info("outer_msg_2")

    events = logger.get_events()

    # Find the inner_msg event
    inner_event = next(e for e in events if e.message == "inner_msg")
    assert inner_event.phase == "inner"
    assert inner_event.phase_depth == 2  # Nested 2 levels deep

    # Find outer_msg_2 (after inner phase closed)
    outer_event = next(e for e in events if e.message == "outer_msg_2")
    assert outer_event.phase == "outer"
    assert outer_event.phase_depth == 1


def test_phase_timing(logger):
    """Test that phase timing is captured."""
    import time

    with logger.phase("timed_phase"):
        time.sleep(0.01)  # 10ms

    timings = logger.get_phase_timings()
    assert "timed_phase" in timings
    assert timings["timed_phase"] >= 10  # At least 10ms


def test_phase_error_handling(logger):
    """Test that phase errors are logged."""
    with pytest.raises(ValueError), logger.phase("error_phase"):
        raise ValueError("test error")

    events = logger.get_events()

    # Should have phase_start and phase_error
    error_event = next(e for e in events if e.event_type == "phase_error")
    assert error_event.level == "ERROR"
    assert "test error" in error_event.context["error"]


def test_context_merging(logger):
    """Test that context is properly merged."""
    with logger.phase("phase1", global_key="global"):
        logger.info("msg", local_key="local")

    events = logger.get_events()
    msg_event = next(e for e in events if e.message == "msg")

    # Should have both global and local context
    assert msg_event.context["global_key"] == "global"
    assert msg_event.context["local_key"] == "local"


def test_context_override(logger):
    """Test that local context overrides phase context."""
    with logger.phase("phase1", key="phase_value"):
        logger.info("msg", key="local_value")

    events = logger.get_events()
    msg_event = next(e for e in events if e.message == "msg")

    # Local should override
    assert msg_event.context["key"] == "local_value"


def test_log_file_output(tmp_path):
    """Test that logs are written to file in JSON format."""
    log_file = tmp_path / "test.log"
    logger = BengalLogger(name="test", log_file=log_file)

    logger.info("test_message", key="value")
    logger.close()

    # Read log file
    with open(log_file) as f:
        lines = f.readlines()

    assert len(lines) == 1

    # Parse JSON
    event_dict = json.loads(lines[0])
    assert event_dict["message"] == "test_message"
    assert event_dict["context"]["key"] == "value"
    assert "timestamp" in event_dict


def test_console_format_basic(logger):
    """Test console output formatting."""
    event = LogEvent(
        timestamp="2025-10-04T12:00:00",
        level="INFO",
        logger_name="test",
        event_type="test",
        message="Test message",
    )

    output = event.format_console(verbose=False)
    assert "Test message" in output
    assert "●" in output  # Bullet point


def test_console_format_verbose(logger):
    """Test verbose console output."""
    event = LogEvent(
        timestamp="2025-10-04T12:00:00",
        level="INFO",
        logger_name="test",
        event_type="test",
        message="Test message",
        context={"key": "value"},
    )

    output = event.format_console(verbose=True)
    assert "Test message" in output
    assert "key=value" in output
    assert "12:00:00" in output  # Timestamp


def test_console_format_with_phase(logger):
    """Test console output with phase."""
    event = LogEvent(
        timestamp="2025-10-04T12:00:00",
        level="INFO",
        logger_name="test",
        event_type="test",
        message="Test message",
        phase="discovery",
        phase_depth=1,
    )

    output = event.format_console(verbose=False)
    assert "[discovery]" in output


def test_console_format_with_timing(logger):
    """Test console output with timing."""
    event = LogEvent(
        timestamp="2025-10-04T12:00:00",
        level="INFO",
        logger_name="test",
        event_type="test",
        message="Test message",
        duration_ms=123.4,
    )

    output = event.format_console(verbose=False)
    assert "123.4ms" in output


def test_get_logger():
    """Test global logger registry."""
    logger1 = get_logger("test.module1")
    logger2 = get_logger("test.module1")
    logger3 = get_logger("test.module2")

    # Same name should return same instance
    assert logger1 is logger2

    # Different name should return different instance
    assert logger1 is not logger3

    close_all_loggers()


def test_configure_logging():
    """Test global configuration."""
    configure_logging(level=LogLevel.WARNING, verbose=True)

    logger = get_logger("test.config")
    assert logger.level == LogLevel.WARNING
    assert logger.verbose is True

    # Reset
    configure_logging(level=LogLevel.INFO, verbose=False)
    close_all_loggers()


def test_print_summary(logger, capsys):
    """Test summary printing."""
    with logger.phase("phase1"):
        pass
    with logger.phase("phase2"):
        pass

    logger.print_summary()

    captured = capsys.readouterr()
    # Check for summary content (heading changed to "Performance" to include memory)
    assert ("Build Phase Timings" in captured.out or "Build Phase Performance" in captured.out)
    assert "phase1" in captured.out
    assert "phase2" in captured.out
    assert "TOTAL" in captured.out


def test_context_manager(tmp_path):
    """Test logger as context manager."""
    log_file = tmp_path / "test.log"

    with BengalLogger(name="test", log_file=log_file) as logger:
        logger.info("test")

    # File should be closed
    assert logger._file_handle is None


def test_get_phase_timings_empty():
    """Test phase timings with no phases."""
    logger = BengalLogger(name="test")
    timings = logger.get_phase_timings()
    assert timings == {}


def test_multiple_phases_same_name(logger):
    """Test multiple phases with the same name."""
    with logger.phase("repeated"):
        pass
    with logger.phase("repeated"):
        pass

    timings = logger.get_phase_timings()
    # Should have timing for the last occurrence
    assert "repeated" in timings

