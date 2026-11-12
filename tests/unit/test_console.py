import logging
from unittest.mock import patch

import pytest
import typer

from qemulab.utils import console


# We patch the logger inside the console module to verify it receives calls
@patch("qemulab.utils.console._logger")
def test_info_logging(mock_logger):
    """Test that console.info logs to INFO level and strips markup for raw_message."""
    console.info("Hello [bold]World[/]")

    # Check that it logged
    mock_logger.log.assert_called_once()

    # Unpack arguments
    args, kwargs = mock_logger.log.call_args
    level, message = args
    extra_data = kwargs["extra"]["extra_data"]

    assert level == logging.INFO
    # The message sent to console (stdout) should keep markup
    assert "[*]" in message
    assert "Hello [bold]World[/]" in message

    # The raw message sent to file (via extra_data) should be stripped
    assert extra_data["raw_message"] == "Hello World"


@patch("qemulab.utils.console._logger")
def test_error_logging(mock_logger):
    """Test that console.error logs to ERROR level."""
    console.error("Something failed")

    args, _ = mock_logger.log.call_args
    assert args[0] == logging.ERROR
    assert "Something failed" in args[1]


@patch("qemulab.utils.console._logger")
def test_fatal_exits(mock_logger):
    """Test that console.fatal logs CRITICAL and raises Exit."""
    with pytest.raises(typer.Exit) as excinfo:
        console.fatal("Critical Failure", exit_code=99)

    assert excinfo.value.exit_code == 99

    # Verify it logged before dying
    args, _ = mock_logger.log.call_args
    assert args[0] == logging.CRITICAL
    assert "FATAL: Critical Failure" in args[1]


@patch("qemulab.utils.console._logger")
def test_section_header_console_only(mock_logger):
    """
    Test that visual separators (sections) are marked as console_only
    so they don't pollute the JSON log file.
    """
    console.section("Test Section")

    # Section makes two log calls (blank line + header)
    # Check the last call
    args, kwargs = mock_logger.info.call_args

    assert "console_only" in kwargs["extra"]
    assert kwargs["extra"]["console_only"] is True
