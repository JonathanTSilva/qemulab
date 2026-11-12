import json
import logging
import logging.handlers

import qemulab.utils.logging as logging_module
from qemulab.utils.logging import ConsoleOnlyFilter, JSONFormatter, setup_logging


def test_json_formatter_strips_markup():
    """Ensure JSONFormatter removes Rich style tags and produces valid JSON."""
    formatter = JSONFormatter()

    # Create a dummy record with Rich markup
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="[bold red]Error[/] occurred [blue]here[/]",
        args=(),
        exc_info=None,
    )

    json_output = formatter.format(record)

    # Validate structure
    data = json.loads(json_output)
    assert data["message"] == "Error occurred here"  # Markup stripped?
    assert data["level"] == "INFO"
    assert "timestamp" in data


def test_json_formatter_handles_exceptions():
    """Ensure exceptions are formatted into the JSON object."""
    formatter = JSONFormatter()
    try:
        _ = 1 / 0
    except ZeroDivisionError:
        import sys

        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="t.py",
        lineno=1,
        msg="Crash",
        args=(),
        exc_info=exc_info,
    )

    json_output = formatter.format(record)
    data = json.loads(json_output)
    assert "exception" in data
    assert "ZeroDivisionError" in data["exception"]


def test_console_only_filter():
    """Ensure the filter blocks records marked as console_only."""
    filt = ConsoleOnlyFilter()

    # Case 1: Record meant for console only -> Should be blocked (False)
    rec_console = logging.LogRecord("name", logging.INFO, "p", 1, "m", (), None)
    rec_console.console_only = True
    assert filt.filter(rec_console) is False

    # Case 2: Standard record -> Should pass (True)
    rec_standard = logging.LogRecord("name", logging.INFO, "p", 1, "m", (), None)
    assert filt.filter(rec_standard) is True


def test_setup_logging_initialization(tmp_path):
    """
    Smoke test to ensure setup_logging wires the QueueHandler correctly.
    We patch the default config to write to a temp file.
    """
    temp_log_file = tmp_path / "test_qemulab.log"

    # Temporarily modify the global default config
    original_config = logging_module.DEFAULT_LOGGING_CONFIG
    test_config = original_config.copy()
    test_config["handlers"]["file"]["filename"] = str(temp_log_file)

    # Monkeypatch
    logging_module.DEFAULT_LOGGING_CONFIG = test_config

    try:
        setup_logging(default_level="DEBUG")

        root = logging.getLogger()
        # Verify root logger has QueueHandler (Async)
        handlers = [h for h in root.handlers if isinstance(h, logging.handlers.QueueHandler)]
        assert len(handlers) > 0, "Root logger should have an async QueueHandler attached"

    finally:
        # Restore
        logging_module.DEFAULT_LOGGING_CONFIG = original_config
